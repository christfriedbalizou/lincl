import subprocess

from lincl import documentation


def test_plain_text_removes_manual_formatting():
    output = "L\bLS\bS\x1b[31m red\x1b[0m"

    assert documentation._plain_text(output) == "LS red"


def test_missing_man_uses_fallback(monkeypatch):
    documentation._read_manual.cache_clear()
    monkeypatch.setattr(documentation.shutil, "which", lambda name: None)

    result = documentation.command_doc("example", "/usr/bin/example")

    assert "Run `man example`" in result
    assert "/usr/bin/example" in result


def test_manual_timeout_uses_fallback(monkeypatch):
    documentation._read_manual.cache_clear()
    monkeypatch.setattr(
        documentation.shutil,
        "which",
        lambda name: "/usr/bin/man",
    )

    def time_out(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], kwargs["timeout"])

    monkeypatch.setattr(documentation.subprocess, "run", time_out)

    assert documentation._read_manual("example") is None
