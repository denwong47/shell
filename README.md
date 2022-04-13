# shell
Pythonic implementation of shell commands in Linux and macOS.

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


# Methods

## shell.run
*Alias of shell.bin.run*
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
The return value is identical to **ShellCommand.result**; see below.

## shell.ShellCommandExists
*Alias of shell.bin.ShellCommandExists*
Check if shell command returns exit code 127.
```
def shell.check_command_exists(
    command: Union[
        List[str],
        str
    ],
)
```

# Classes

## shell.ShellPipe
*Alias of shell.classes.ShellPipe*
An abstract base class representing members of a unix shell pipe.

Example of a shell pipe:
```
 ShellPipe(_source) | ShellCommand("ffmpeg -f mp3 -i pipe:0 -f s16le pipe:1") | ShellPipe(_dest)
```
Each of these elements are instances of ShellPipe subtypes. These include:
- `ShellBytesPipe` - A simple wrapper around a `bytes` object. Generally used at the head or tail of a pipe.
- `ShellStrPipe` - A simple wrapper around a `str` object. Generally used at the head or tail of a pipe.
- `ShellFunctionPipe` - A python function as part of a pipe. Function should have syntax `func(stdin:bytes) -> bytes`. Use `shell.bytify(str_func)` to decorate string functions.
- `ShellIOPipe` - An IO like object that supports `.read()` and/or `.write()`. When used upstream in a pipe, `.read()` will be called as `stdin` for the next segment; when used downstream, `.write(stdout)` will be called using the `stdout` from the previous segment.
- `ShellCommand` - A single shell command. `stdin` and `stdout` will be treated just like a unix pipe. *See further usages below.*

You do not need to construct directly using these subclasses.
The constructor for `ShellPipe` will select the most appropriate subtype for `obj` when `ShellPipe(obj)` is called.

Each pipe segment when called in this syntax is blocking, as one segment depends on the previous one for its output.


## shell.ShellCommand
*Alias of shell.classes.ShellCommand*
*Subtype of ShellPipe*
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

### Execute the command and wait for completion in blocking mode
```
_command.run(
    stdin:bytes,
)->Union[
    bytes,
    str,
    ShellReturnedFailure
]
```
If the command hasn't been run, this will cause execution to begin, with `stdin` being fed into the process as `pipe:0`.

This will be blocking until the process exits, or `timeout` is reached, whichever earlier.

The return value is identical to **ShellCommand.result**; see below.

### Execution result
```
_command.result
```
Returns either
- A `bytes` object by default, if exit code is `0` or is in `ignore_codes`.
- A `str` object if `output` is `str` and exit code is `0` or is in `ignore_codes`.
- A `shell.exceptions.ShellReturnedFailure` object instance if exit code is anything else; this object
    - is a subclass of `RuntimeError`.
    - contains the following attributes:
        - `.exit_code` - `int`, the return code from the shell process.
        - `.command` - `List[str]`, the command executed producing the error.
        - `.stdout` - `bytes`, `stdout` from the process.
        - `.stderr` - `bytes`, `stderr` from the process.
        - `.time_used` - `float`, time taken for process to exit, in seconds.

### Iterative streaming of bytes from stdout
```
with shell.ShellCommand("command with streaming stdout") as _command:
    for _chunk in _command.iter_stdout():
        do_something_with_chunk(_chunk)
```


### Non-blocking background thread stdout streaming with callback
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


