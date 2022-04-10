# shell
Pythonic implementation of shell commands.

## This README is WIP.

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