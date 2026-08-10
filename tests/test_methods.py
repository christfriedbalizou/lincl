import os
import signal
import subprocess
import sys
from pathlib import Path

import pytest

from lincl import (
    CommandExecutionError,
    CommandLaunchError,
    CommandResult,
    CommandTimeoutError,
    ExecutionOptions,
    OutputParseError,
)
from lincl.core import _resolve_command, _transcribe


@pytest.fixture
def python_command():
    return _resolve_command(sys.executable)


def test_success_returns_structured_result(python_command):
    result = python_command("-c", "print('first'); print('second')")

    assert isinstance(result, CommandResult)
    assert result.args[0] == os.path.abspath(sys.executable)
    assert result.returncode == 0
    assert result.stdout == "first\nsecond\n"
    assert result.stderr == ""
    assert result.value == result.stdout
    assert result.ok is True


def test_arguments_are_passed_without_shell_interpretation(python_command):
    value = "$(touch should-not-exist); * 'quoted'"
    result = python_command("-c", "import sys; print(sys.argv[1])", value)

    assert result.stdout.splitlines() == [value]
    assert not Path("should-not-exist").exists()


def test_nonzero_exit_preserves_complete_result(python_command):
    with pytest.raises(CommandExecutionError) as raised:
        python_command(
            "-c",
            "import sys; print('partial'); "
            "print('bad input', file=sys.stderr); sys.exit(7)",
        )

    error = raised.value
    assert error.returncode == 7
    assert error.stdout == "partial\n"
    assert error.stderr == "bad input\n"
    assert error.result.ok is False
    assert "exited with status 7" in str(error)
    assert "stderr: bad input" in str(error)


def test_large_stdout_and_stderr_do_not_deadlock(python_command):
    size = 1_000_000
    result = python_command(
        "-c",
        "import sys; size=int(sys.argv[1]); "
        "sys.stdout.write('o' * size); sys.stderr.write('e' * size)",
        size,
    )

    assert len(result.stdout) == size
    assert len(result.stderr) == size


@pytest.mark.skipif(os.name != "posix", reason="signals require POSIX")
def test_signal_exit_is_described(python_command):
    with pytest.raises(CommandExecutionError) as raised:
        python_command(
            "-c",
            f"import os; os.kill(os.getpid(), {signal.SIGTERM})",
        )

    assert raised.value.returncode == -signal.SIGTERM
    assert "terminated by signal" in str(raised.value)


def test_timeout_preserves_partial_output(python_command):
    execution = ExecutionOptions(timeout=0.2)

    with pytest.raises(CommandTimeoutError) as raised:
        python_command.run(
            "-c",
            "import time; print('started', flush=True); time.sleep(5)",
            execution=execution,
        )

    assert raised.value.timeout == 0.2
    assert raised.value.stdout == "started\n"
    assert isinstance(raised.value.__cause__, subprocess.TimeoutExpired)
    assert "timed out after 0.2 seconds" in str(raised.value)


def test_execution_options_support_input_cwd_and_environment(
    python_command, tmp_path
):
    execution = ExecutionOptions(
        cwd=tmp_path,
        env={"LINCL_TEST_VALUE": "present"},
        input="hello",
    )
    result = python_command.run(
        "-c",
        "import os, pathlib, sys; "
        "print(pathlib.Path.cwd()); "
        "print(os.environ['LINCL_TEST_VALUE']); "
        "print(sys.stdin.read())",
        execution=execution,
    )

    assert result.stdout.splitlines() == [str(tmp_path), "present", "hello"]


def test_launch_error_is_typed(python_command):
    missing_executable = f"{python_command.executable}.missing"
    missing_command = type(python_command)(missing_executable, str)

    with pytest.raises(CommandLaunchError) as raised:
        missing_command()

    assert raised.value.args_vector == (missing_executable,)
    assert isinstance(raised.value.reason, OSError)


def test_configure_returns_typed_value_and_keeps_raw_output(python_command):
    parsed_command = python_command.configure(parser=str.splitlines)

    result = parsed_command("-c", "print('first'); print('second')")

    assert result.value == ["first", "second"]
    assert result.stdout == "first\nsecond\n"
    assert parsed_command is not python_command
    assert python_command("-c", "print('raw')").value == "raw\n"


def test_subcommand_places_options_after_subcommand(monkeypatch):
    from lincl import git

    completed = subprocess.CompletedProcess(
        args=(), returncode=0, stdout="", stderr=""
    )
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: completed)

    result = git.clone("URL", "DESTINATION", depth=1)

    assert result.args == (
        git.executable,
        "clone",
        "--depth=1",
        "URL",
        "DESTINATION",
    )


def test_subcommands_can_be_nested_and_configured(monkeypatch):
    from lincl import git

    completed = subprocess.CompletedProcess(
        args=(), returncode=0, stdout="one\ntwo\n", stderr=""
    )
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: completed)

    command = (
        git.subcommand("remote")
        .subcommand("show")
        .configure(parser=str.splitlines)
    )
    result = command("origin", verbose=True)

    assert result.args == (
        git.executable,
        "remote",
        "show",
        "--verbose",
        "origin",
    )
    assert result.value == ["one", "two"]


def test_per_call_parser_returns_value_proxy_with_metadata(python_command):
    entries = python_command("-c", "print('a.txt'); print('b.txt')").parser(
        str.splitlines
    )

    assert isinstance(entries, list) is False
    assert isinstance(entries.value, list) is True
    assert list(entries) == ["a.txt", "b.txt"]
    assert entries[0] == "a.txt"
    assert "b.txt" in entries
    assert len(entries) == 2
    assert entries == ["a.txt", "b.txt"]
    assert entries.returncode == 0


def test_mutation_and_addition_preserve_result_metadata(python_command):
    entries = python_command("-c", "print('a.txt'); print('b.txt')").parser(
        str.splitlines
    )

    entries.append("c.txt")
    extended = entries + ["d.txt"]

    assert entries.value == ["a.txt", "b.txt", "c.txt"]
    assert extended.value == ["a.txt", "b.txt", "c.txt", "d.txt"]
    assert extended.returncode == 0
    assert extended.stdout == "a.txt\nb.txt\n"


def test_parser_failure_preserves_raw_result(python_command):
    result = python_command("-c", "print('not-an-integer')")

    with pytest.raises(OutputParseError) as raised:
        result.parser(int)

    assert raised.value.result.stdout == "not-an-integer\n"
    assert raised.value.result.value == "not-an-integer\n"
    assert isinstance(raised.value.reason, ValueError)
    assert raised.value.__cause__ is raised.value.reason


def test_parser_does_not_run_for_failed_command(python_command):
    parser_called = False

    def parser(output):
        nonlocal parser_called
        parser_called = True
        return output

    parsed_command = python_command.configure(parser=parser)

    with pytest.raises(CommandExecutionError):
        parsed_command("-c", "raise SystemExit(2)")

    assert parser_called is False


def test_parser_configuration_rejects_non_callable(python_command):
    with pytest.raises(TypeError, match="parser must be callable"):
        python_command.configure(parser=None)

    result = python_command("-c", "print('raw')")
    with pytest.raises(TypeError, match="parser must be callable"):
        result.parser(None)
    with pytest.raises(TypeError, match="positional-only"):
        result.parser(parser=str.splitlines)


@pytest.mark.parametrize(
    ("arguments", "options", "expected"),
    [
        (("start",), {"v": True}, ["-v", "start"]),
        ((), {"recursive": False, "color": None}, []),
        ((), {"output": Path("report.txt")}, ["--output=report.txt"]),
        ((), {"parser": "native"}, ["--parser=native"]),
        ((), {"include": ["curl", "git"]}, ["--include=curl,git"]),
        ((42, 1.5), {}, ["42", "1.5"]),
    ],
)
def test_transcribe(arguments, options, expected):
    assert _transcribe(*arguments, **options) == expected


@pytest.mark.parametrize(
    ("arguments", "options", "error", "message"),
    [
        ((True,), {}, TypeError, "must not be a boolean"),
        ((b"bytes",), {}, TypeError, "must be text"),
        ((), {"": "value"}, ValueError, "invalid command option"),
        ((), {"items": [object()]}, TypeError, "item in option"),
    ],
)
def test_transcribe_rejects_ambiguous_values(
    arguments, options, error, message
):
    with pytest.raises(error, match=message):
        _transcribe(*arguments, **options)


def test_execution_options_reject_invalid_timeout():
    with pytest.raises(ValueError, match="finite positive number"):
        ExecutionOptions(timeout=0)
