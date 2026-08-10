import inspect
import pydoc
import shutil

import pytest

import lincl
from lincl import CommandNotFoundError


def test_missing_dynamic_command_raises_typed_import_error(capsys):
    command_name = "lincl-command-that-does-not-exist"

    with pytest.raises(CommandNotFoundError, match=command_name):
        getattr(lincl, command_name)

    assert capsys.readouterr() == ("", "")


def test_installed_command_is_resolved_once():
    executable = shutil.which("ls")
    assert executable is not None

    from lincl import ls

    assert inspect.isfunction(ls)
    assert ls.executable == executable
    assert callable(ls)


def test_dynamic_command_can_be_aliased():
    from lincl import cp as copy

    assert inspect.isfunction(copy)
    assert copy.__name__ == "cp"


def test_dynamic_command_has_pythonic_help():
    from lincl import ls

    documentation = pydoc.render_doc(ls, renderer=pydoc.plaintext)

    assert "function ls in module lincl" in documentation
    assert "ls(*arguments, **options)" in documentation
    assert "CommandResult" in documentation
    assert "result.parser(callable)" in documentation
    assert "result.parse(" not in documentation
    assert "System manual:" in documentation
    assert "class Command" not in documentation


def test_private_attributes_follow_normal_module_semantics():
    with pytest.raises(AttributeError, match="has no attribute"):
        getattr(lincl, "_missing")


def test_dir_contains_stable_public_api():
    assert "CommandResult" in dir(lincl)
    assert "OutputParseError" in dir(lincl)
    assert "Command" not in dir(lincl)
    assert "command" not in dir(lincl)


def test_internal_command_type_is_not_importable():
    with pytest.raises(CommandNotFoundError, match="Command"):
        getattr(lincl, "Command")
