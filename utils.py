import typing
# noinspection PyUnresolvedReferences
import readline

from rich.console import Console


def get_command(msg: typing.Union[str, bytes]) -> tuple[str | None, ...]:
    if type(msg) == bytes:
        msg = msg.decode()
    command_parts: typing.List[typing.Union[str, None]] = msg.split(" ")
    if len(command_parts) == 1:
        command_parts.append(None)

    return tuple(command_parts)


def unicode_input(console: Console, input: typing.Callable[[], str] | str) -> str:
    while True:
        try:
            return console.input(input) if type(input) == str else input()
        except UnicodeDecodeError:
            console.print("Invalid character detected (make sure you're using only UTF-8 characters)", style="red")
