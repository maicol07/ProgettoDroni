import typing


def get_command(msg: typing.Union[str, bytes]) -> tuple[str | None, ...]:
    if type(msg) == bytes:
        msg = msg.decode()
    command_parts: typing.List[typing.Union[str, None]] = msg.split(" ")
    if len(command_parts) == 1:
        command_parts.append(None)

    return tuple(command_parts)
