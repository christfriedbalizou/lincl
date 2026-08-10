import shutil

import pytest

import lincl
from lincl import Command, CommandNotFoundError


def test_missing_dynamic_command_raises_typed_import_error(capsys):
    command_name = "lincl-command-that-does-not-exist"

    with pytest.raises(CommandNotFoundError, match=command_name):
        getattr(lincl, command_name)

    assert capsys.readouterr() == ("", "")


def test_installed_command_is_resolved_once():
    executable = shutil.which("ls")
    assert executable is not None

    from lincl import ls

    assert isinstance(ls, Command)
    assert ls.executable == executable
    assert callable(ls)


def test_dynamic_command_can_be_aliased():
    from lincl import cp as copy

    assert isinstance(copy, Command)


def test_private_attributes_follow_normal_module_semantics():
    with pytest.raises(AttributeError, match="has no attribute"):
        getattr(lincl, "_missing")


def test_dir_contains_stable_public_api():
    assert "CommandResult" in dir(lincl)
    assert "command" in dir(lincl)
