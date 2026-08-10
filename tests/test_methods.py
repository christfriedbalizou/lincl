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
    command,
    transcribe,
)


@pytest.fixture
def python_command():
    return command(sys.executable)


def test_success_returns_structured_result(python_command):
    result = python_command("-c", "print('first'); print('second')")

    assert isinstance(result, CommandResult)
    assert result.args[0] == os.path.abspath(sys.executable)
    assert result.returncode == 0
    assert result.stdout == "first\nsecond\n"
    assert result.stderr == ""
    assert result.lines == ["first", "second"]
    assert result.ok is True


def test_arguments_are_passed_without_shell_interpretation(python_command):
    value = "$(touch should-not-exist); * 'quoted'"
    result = python_command("-c", "import sys; print(sys.argv[1])", value)

    assert result.lines == [value]
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

    assert result.lines == [str(tmp_path), "present", "hello"]


def test_launch_error_is_typed(python_command):
    missing_executable = f"{python_command.executable}.missing"
    missing_command = type(python_command)(missing_executable)

    with pytest.raises(CommandLaunchError) as raised:
        missing_command()

    assert raised.value.args_vector == (missing_executable,)
    assert isinstance(raised.value.reason, OSError)


@pytest.mark.parametrize(
    ("arguments", "options", "expected"),
    [
        (("start",), {"v": True}, ["-v", "start"]),
        ((), {"recursive": False, "color": None}, []),
        ((), {"output": Path("report.txt")}, ["--output=report.txt"]),
        ((), {"include": ["curl", "git"]}, ["--include=curl,git"]),
        ((42, 1.5), {}, ["42", "1.5"]),
    ],
)
def test_transcribe(arguments, options, expected):
    assert transcribe(*arguments, **options) == expected


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
        transcribe(*arguments, **options)


def test_execution_options_reject_invalid_timeout():
    with pytest.raises(ValueError, match="greater than zero"):
        ExecutionOptions(timeout=0)
