"""Verify the installed package's public execution contract."""


def verify_installation() -> None:
    from lincl import CommandResult, echo

    result = echo("lincl")
    assert isinstance(result, CommandResult)
    assert result.value == "lincl\n"
    assert result.stdout == "lincl\n"
    assert result.stderr == ""
    assert result.returncode == 0

    parsed = echo("first\nsecond").with_parser(parser=str.splitlines)
    assert parsed.value == ["first", "second"]
    assert parsed.returncode == 0


if __name__ == "__main__":
    verify_installation()
