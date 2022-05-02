
from typing import Any, Dict, Iterable, List, Union

import shell.bin

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

        _command_str = " ".join(command) if (isinstance(command, (list, tuple))) else command

        _instance = cls._instances.get(
            _command_str,
            super().__new__(cls)
        )

        cls._instances[_command_str] = _instance

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
            self.exists = shell.bin.check_command_exists(command)

    def __bool__(
        self,
    ):
        """
        bool(self) will return whether the command exists
        """
        return self.exists

    __nonzero__ = __bool__

    def __repr__(
        self,
    ):
        return f"{type(self).__name__}(command={repr(self.command)}, exists={repr(self.exists)})"
