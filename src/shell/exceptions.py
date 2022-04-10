#!/usr/bin/env python3

class ShellError(Exception):
    def __bool__(self):
        return False
    __nonzero__ = __bool__

class InvalidParameterError(ValueError, ShellError):
    pass

class ShellReturnedFailure(RuntimeError, ShellError):
    def __init__(
        self,
        stderr:str,
        exit_code:int=0,
        command:list=[],
        stdout:str="",
        time_used:float=0,
    ):
        super().__init__(stderr)

        self.exit_code = exit_code
        self.command = command
        self.stdout = stdout
        self.stderr = stderr
        self.time_used = time_used

class ShellProcessInactive(OSError, ShellError):
    pass

class ShellProcessAlreadyRunning(OSError, ShellError):
    pass