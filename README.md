# shell
Pythonic implementation of shell commands in Linux and macOS>

The primary purpose of this module is to use subprocess to run shell commands, including unix piping.

For example:
```
# shell
df | grep tmpfs | sort
```
can be written in Python as:
```
# Python
from shell import ShellCommand
(ShellCommand("df") | ShellCommand("grep tmpfs") | ShellCommand("sort")).result
```
and giving a bytes object as an output.


It is also possible to add Python functions and objects into the pipe.

For example:
```
# Streaming mp3 data into ffmpeg, then piping it to another object for playback such as wave
from shell import ShellCommand, ShellPipe
with some_mp3_streaming_io() as _source:
    with some_audio_wav_device() as _dest:
        ShellPipe(_source) | ShellCommand("ffmpeg -f mp3 -i pipe:0 -f s16le pipe:1") | ShellPipe(_dest)
```

```
# Print all disk data in capital, and save it into ./result.txt

#     Note: bytify() is a decorator function that converts input from bytes to str before feeding it to the underlying function. If its return is str, then it encodes it before returning.
#           It is useful to wrap built-in functions like str.upper before sending to ShellPipe().

from shell import ShellCommand, ShellPipe, bytify
ShellCommand("df") | ShellPipe(bytify(str.upper)) > "result.txt"
```


## shell.run
Simple method to run a shell command in blocking mode.
```
def shell.run(
    command:Union[
        str,
        list
    ],
    stdin:Union[
        str,
        bytes
    ]                   = None,
    output:type         = str,
    ignore_codes:list   = [],
    timeout:float       = None,
)->Union[
    bytes,
    str,
    ShellReturnedFailure
]
```

## shell.ShellCommand
Class for advanced Shell operations.
```
class shell.ShellCommand(
    command:Union[
        str,
        list
    ],
    output:type         = bytes,
    ignore_codes:list   = [],
    timeout:float       = None,
)
```

### Run in blocking mode
```
_command.run(
    stdin:bytes,
)->Union[
    bytes,
    str,
    ShellReturnedFailure
]
```

### Get excecution result
```
_command.result->Union[
    bytes,
    str,
    ShellReturnedFailure
]
```

### Iterative streaming of bytes from stdout
```
with shell.ShellCommand("command with streaming stdout") as _command:
    for _chunk in _command.iter_stdout():
        do_something_with_chunk(_chunk)
```


### Background thread stdout streaming with callback
```
def _callback(
    command:ShellCommand,
    bytes_total:int,
    *args,
    **kwargs,
):
    do_something(bytes_total)

with shell.ShellCommand("command with streaming stdout") as _command:
    # Non-blocking stdout stream with background thread
    _command.stream_stdout(
        fHnd = _some_streaming_io_supporting_write_method,
        callback = _callback,
    )
```

### Iterative streaming of bytes into stdin
```
with shell.ShellCommand("command with streaming stdin") as _command:
    for _chunk in _data_chunks:
        _command.stream_stdin(_chunk)
```


## shell.ShellCommandExists
Check if shell command returns exit code 127.
```
def shell.check_command_exists(
    command: Union[
        List[str],
        str
    ],
)
```