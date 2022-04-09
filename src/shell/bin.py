#!/usr/bin/env python3

import subprocess
import shlex
from typing import Any, Dict, Iterable, List, Union

from execute_timer import execute_timer

from shell.exceptions import ShellReturnedFailure

def run(
    command:list,
    stdin:Union[str, bytes] = None,
    output:type = str,
    safe_mode:bool=True, # Protect against shell injection
    ignore_codes:list=[],
    timeout:float=None,
):
    """
    Old functional implementation of shell command execution.
    
    TODO rewrite using ShellCommand.
    """

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

