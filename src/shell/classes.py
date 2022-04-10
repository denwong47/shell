#!/usr/bin/env python3
import io
import shlex
import subprocess
import threading
import time as timer
import warnings

from typing import Any, Callable, Dict, Iterable, List, Union
from xml.sax.handler import property_declaration_handler


from shell.exceptions import    InvalidParameterError, \
                                ShellReturnedFailure, \
                                ShellProcessInactive, \
                                ShellProcessAlreadyRunning

DEFAULT_STDOUT_CHUNK_SIZE = 2**20

class ShellCommand():

    process = None

    def __init__(
        self,
        command:list,
        output:type = bytes,
        ignore_codes:list=[],
        timeout:float=None,
    )->None:
        
        # Checking variables and putting them as attributes
        self.command = command

        if (output not in (bytes,str,)): raise InvalidParameterError(f"Either bytes or str expected for output, {type(output).__name__} found.")
        self.output = output

        if (not isinstance(ignore_codes, (list, range, tuple))):
            try:
                ignore_codes = list(ignore_codes)
            except TypeError as e:
                raise InvalidParameterError(f"list type expected for ignore_codes, {type(ignore_codes).__name__} found.")
        self.ignore_codes = ignore_codes

        if (not isinstance(timeout, (int, float, type(None)))): raise InvalidParameterError(f"Numeric types expected for timeout, {type(timeout).__name__} found.")
        self.timeout = timeout

        self.run_count = 0
        self.timer_start = None
        self.exit_code = None
        self.stdout = None
        self.stderr = None
        self.time_used = None

    def __repr__(
        self,
    )->str:
        return f"{type(self).__name__}(command={repr(self.command)}, output={self.output.__name__}, ignore_codes={repr(self.ignore_codes)}, timeout={repr(self.timeout)})"

    def __enter__(
        self,
    ):
        self.start()
        return self

    def __exit__(
        self,
        exception_type,
        exception_value,
        exception_traceback,
    ):
        if (exception_type is not None):
            self.kill()
        else:
            self.end() 

    @property
    def command(
        self,
    )->list:
        """
        command stored as a list
        """
        assert isinstance(self._command, list)
        return self._command

    @command.setter
    def command(
        self,
        value,
    ):
        """
        command.setter
        Protect against shell injection.

        DO NOT EVER SPLIT AGAINST | OPERATOR:
        the premise of a ShellCommand is that it should only be one single shell command;
        if the stdout needs to be piped into another process, another instance of ShellCommand should be created.

        If we split against | and execute all the commands anyway, this negates the shlex.split
        and make the command vulnerable to shell injection again.
        """

        if (isinstance(value, str)):
            value = shlex.split(value)

        if (not isinstance(value, list)):
            raise InvalidParameterError(f"str or list types expected for command, {type(value).__name__} found.")
        else:
            self._command = value

    @property
    def can_run(
        self,
    )->bool:
        """
        Check if the subprocess exists and can be run.
        """
        return isinstance(self.process, subprocess.Popen)

    @property
    def has_run(
        self,
    )->bool:
        """
        Check if the subprocess has ever been run.
        """
        return self.time_used is not None or self.timer_start is not None

    @property
    def alive(
        self,
    )->bool:
        """
        Check if the subprocess is initiated and alive
        """

        if (isinstance(self.process, subprocess.Popen)):
            if (self.process.poll() is None):
                return True
        
        return False

    # Decorator
    def alive_only(
        func,
    ):
        def wrapper(
            self,
            *args,
            **kwargs,
        ):
            if (self.alive):
                return func(self, *args, **kwargs)
            else:
                return ShellProcessInactive(f"Subprocess for {' '.join(self.command)} is inactive.")
        
        return wrapper

    def start(
        self,
    )->Union[subprocess.Popen, Exception]:
        """
        Start process
        """

        if (not self.alive):
            try:
                self.start_timer()
                self.process = subprocess.Popen(
                    self.command,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    shell=isinstance(self.command, str),    # always False in its current implementation
                )

                self.run_count += 1
                return self.process
            # when an unknown command is called, subprocess actually triggers
            # a FileNotFoundError instead of error code 127 like shell would
            except FileNotFoundError as e:
                self.set_result(
                    exit_code=127,
                    stdout=b"",
                    stderr=f"Shell command '{self.command[0]}' not found.".encode("utf-8"),
                )
                return self.result
        else:
            return ShellProcessAlreadyRunning(f"Subprocess for {' '.join(self.command)} is already running at PID {self.process.pid}.")

    def end(
        self,
        stdin:bytes=None,
    )->Union[bytes, str, ShellReturnedFailure]:
        """
        Pipe stdin in, and wait for the 
        """

        if (isinstance(stdin, str)):
            stdin = stdin.encode("utf-8")

        if (self.can_run):
            try:
                _stdout, _stderr = self.process.communicate(input=stdin, timeout=self.timeout)
            except subprocess.TimeoutExpired as e:
                return self.kill()

            return self.set_result(
                exit_code = self.process.returncode,
                stdout = _stdout,
                stderr = _stderr,
            )
        else:
            return self.result

    def run(
        self,
        stdin:bytes=None,
    )->Union[bytes, str, ShellReturnedFailure]:
        """
        Run the command once in blocking mode, then return the result.
        """

        if (isinstance(stdin, str)):
            stdin = stdin.encode("utf-8")

        if (not self.has_run):
            self.start()

        if (self.alive):
            self.end(stdin)

        return self.result

    def set_result(
        self,
        exit_code:int=None,
        stdout:bytes=None,
        stderr:bytes=None,
    )->Union[bytes, str, ShellReturnedFailure]:
        """
        Put all the results into attributes
        """
        time_used = self.lapsed
        self.end_timer()

        if (exit_code is None): exit_code = self.process.returncode
        self.exit_code = exit_code

        if (self.output is str):
            self.stdout = stdout.decode("utf-8")
            self.stderr = stderr.decode("utf-8")
        else:
            self.stdout = stdout
            self.stderr = stderr
            

        self.time_used = time_used

        return self.result

    @property
    def result(
        self,
    )->Union[bytes, str, ShellReturnedFailure]:
        """
        Construct a "simple" version of the results;
        - bytes or str stdout if run is successful, or
        - ShellReturnedFailure if not
        """

        if (self.exit_code is None):
            return ShellProcessInactive("Shell process have not returned any results.")
        elif (self.exit_code == 0 or \
            self.exit_code in self.ignore_codes):
            return self.stdout
        else:
            return ShellReturnedFailure(
                stderr = self.stderr,
                exit_code = self.exit_code,
                command = self.command,
                stdout = self.stdout,
                time_used = self.lapsed,
            )

    def start_timer(
        self,
    )->None:
        """
        Store perf_counter() as timer_start.
        """

        self.timer_start = timer.perf_counter()
        return None
    
    @property
    def lapsed(
        self,
    )->float:
        """
        Return the time lapsed since timer_start.
        """

        if (self.timer_start is None):
            return None
        else:
            return timer.perf_counter() - self.timer_start

    def end_timer(
        self,
    ):
        """
        Reset timer and return time lapsed.
        """

        _lapsed = self.lapsed
        self.timer_start = None

        return _lapsed

    @alive_only
    def kill(
        self,
        exit_code=None,
    )->Union[bytes, str, ShellReturnedFailure]:
        """
        Kill the process, and get the result.
        """

        self.process.kill()

        _stdout, _stderr = self.process.communicate()

        return self.set_result(
            exit_code = exit_code,
            stdout = _stdout,
            stderr = _stderr,
        )

    @alive_only
    def iter_stdout(
        self,
        chunk_size:int=DEFAULT_STDOUT_CHUNK_SIZE,
    )->Union[bytes, str]:
        """
        Iter over stdout
        """

        while (_data := self.process.stdout.read(chunk_size)):
            if (len(_data) <= 0):
                break

            yield _data

    @alive_only
    def stream_stdin(
        self,
        data:Union[bytes, str],
    )->None:
        """
        Write data to stdin pipe of the process.
        Usually used repeated in a loop to stream data.
        """

        if (isinstance(data, str)):
            data = data.encode("utf-8")

        self.process.stdin.write(data)

    @alive_only
    def stream_stdout(
        self,
        fHnd:io.IOBase,
        chunk_size:int=DEFAULT_STDOUT_CHUNK_SIZE,
        callback:Callable=None
    ):
        """
        Start a new thread pushing stdout data through to a IO object.
        Normally used when stdout from a program is also streamed from slow IO, like a network.

        Supports triggering a callback when everything is done, in the following format:
        def callback(
            command:ShellCommand,
            bytes_total:int,
            *args,
            **kwargs,
        )

        Using both *args and **kwargs are highly recommended, as it futureproofs against
        any new arguments being added.
        """

        def _push_data():
            _bytes_total = 0
            for _chunk in self.iter_stdout(chunk_size=chunk_size):
                _bytes_total += len(_chunk)
                # print (_bytes_total, len(_chunk))
                fHnd.write(_chunk)

            if (callback is not None):
                callback(
                    command=self,
                    bytes_total=_bytes_total,
                )

        threading.Thread(target=_push_data).start()

    def __or__(self, other):
        """
        Pipe the stdout from self into other.
        """

        if (isinstance(other, ShellCommand)):
            # If the command has not run, then run it without stdin.
            # If stdin is required, call the command first.
            if (not self.has_run):
                self.run()

            if (other.has_run and not other.alive):
                raise ShellProcessAlreadyRunning("stdout pipe destination process has already completed.")

            _result = self.result
            # Fetch own result
            
            if (not isinstance(_result, ShellReturnedFailure)):
                # Check result is valid
                if (isinstance(_result, str)):
                    _result = _result.encode("utf-8")

                # Start and end the other process
                other.run(
                    stdin = _result,
                )

                # Return the other process instance;
                # - This allows multiple |s to be chained together as per actual shell.
                return other
            else:
                # If the first command didn't succeed, then raise the Exception.
                raise _result
        else:
            # This is not a genuine method for logical operation.
            # If we are operating on something else, raise an error.
            return InvalidParameterError(f"| operator can only be used between two instances of ShellCommand, but {type(other).__name__} found.")

    def __gt__(self, path):
        """
        Pipe the stdout from self into a file.
        This replaces the contents of a file.
        Append operator is not supported.
        """
        
        if (not isinstance(path, str)):
            # This is not a genuine method for comparison.
            # If we are comparing something else, raise an error.
            return InvalidParameterError(f"> operator can only be used between from a ShellCommand on a str, but {type(path).__name__} found.")

        # If we haven't been run, the do so
        if (not self.has_run):
            self.run()

        # Get the stdout from self
        _result = self.result
        if (isinstance(_result, str)):
            _result = _result.encode("utf-8")
        elif (isinstance(_result, bytes)):
            pass
        else:
            raise _result
            return _result

        try:
            with open(path, "w+b") as _f:
                _f.write(_result)
            
            return True
        except (PermissionError,
                OSError,
                RuntimeError,
                ValueError,
                TypeError,
                ) as e:
            warnings.warn(
                RuntimeWarning(
                    f"Cannot pipe stdout to file: {str(e)}",
                )
            )
            return False
    