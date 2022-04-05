import subprocess
import shlex
from typing import Any, Dict, Iterable, List, Union

from execute_timer import execute_timer

class ShellError(Exception):
    def __bool__(self):
        return False
    __nonzero__ = __bool__

class ShellReturnedFailure(RuntimeError, ShellError):
    def __init__(
        self,
        message:str,
        exit_code:int=0,
        command:list=[],
        stdout:str="",
        time_used:float=0,
    ):
        super().__init__(message)

        self.exit_code = exit_code
        self.command = command
        self.stdout = stdout
        self.stderr = message
        self.time_used = time_used



def run(
    command:list,
    stdin:Union[str, bytes] = None,
    output:type = str,
    safe_mode:bool=True, # Protect against shell injection
    ignore_codes:list=[],
    timeout:float=None,
):
    if (isinstance(command, str) and safe_mode):
        command = shlex.split(command)

    if (not isinstance(ignore_codes, (list, range, tuple))):
        ignore_codes = []

    with execute_timer(echo=False) as _timer:
        try:
            _pipe = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=isinstance(command, str),
                )

        # when an unknown command is called, subprocess actually triggers
        # a FileNotFoundError instead of error code 127 like shell would
        except FileNotFoundError as e:
            return ShellReturnedFailure(
                "Shell command not found.",
                exit_code=127,
                command=command,
                stdout="",
                time_used=_timer.lapsed(),
            )

        timedout = False
        try:
            _stdout, _stderr = _pipe.communicate(input = stdin, timeout=timeout)
        except subprocess.TimeoutExpired as e:
            timedout = True
            _pipe.kill()
            _stdout, _stderr = _pipe.communicate()

    if (_pipe.returncode != 0 and not _pipe.returncode in ignore_codes or timedout):
        _stderr = _stderr.decode("utf-8")
        return ShellReturnedFailure("Shell command returned Code {:d}: {:s}".format(
            _pipe.returncode,
            _stderr.strip()
            ),
            exit_code=_pipe.returncode,
            command=command,
            stdout=_stdout,
            time_used=_timer.lapsed(),
        )
    else:
        if (output is str):
            _stdout = _stdout.decode("utf-8")

        return _stdout


def check_command_exists(
    command: Union[
        List[str],
        str
    ],
):
    """
    Check if a command returns a specific error code of 127,
    which is command not found.
    """

    _return = run(
        command,
        safe_mode = True,
    )

    if (isinstance(_return, ShellReturnedFailure)):
        if (_return.exit_code == 127):
            return False

    return True



class ShellCommandExists():
    """
    A psuedo-Singleton class that create only one instance of each unique 'command' value.
    This avoids spending time running subprocesses more than once.
    """

    _instances={}   # this dict is shared by all instances, do not create a new one

    exists = None

    def __new__(
        cls,
        command:Union[
            List[str],
            str
        ],
        *args,
        **kwargs,
    ):
        """
        Create new instance if cls(command) was not called before;
            otherwise return the instance that already exists.
        Put the instance back into the library.
        """

        _instance = cls._instances.get(
            command,
            super().__new__(cls)
        )

        cls._instances[command] = _instance

        return _instance
    
    def __init__(
        self,
        command:Union[
            List[str],
            str
        ],
        *args,
        **kwargs,
    ):
        """
        Check if command exists, then store it in self.exists.
        """

        self.command = command

        # Avoids running this twice if __new__() returned an existing instance
        if (self.exists is None):
            self.exists = check_command_exists(command)

    def __bool__(
        self,
    ):
        return self.exists

    __nonzero__ = __bool__

    def __repr__(
        self,
    ):
        return f"{type(self).__name__}(command={repr(self.command)}, exists={repr(self.exists)})"

