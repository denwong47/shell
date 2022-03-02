import subprocess
import shlex

from execute_timer import execute_timer

class ShellReturnedFailure(RuntimeError):
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

    def __bool__(self):
        return False
    __nonzero__ = __bool__


def run(
    command:list,
    safe_mode:bool=True, # Protect against shell injection
    ignore_codes:list=[],
):
    if (isinstance(command, str) and safe_mode):
        command = shlex.split(command)

    if (not isinstance(ignore_codes, (list, range, tuple))):
        ignore_codes = []

    with execute_timer(echo=False) as _timer:
        _pipe = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=isinstance(command, str),
            )

    _stdout, _stderr = _pipe.communicate()

    if (_pipe.returncode != 0 and not _pipe.returncode in ignore_codes):
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
        _stdout = _stdout.decode("utf-8")

        return _stdout
