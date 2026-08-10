"""Exceptions raised by command discovery and execution."""

import shlex
from pathlib import Path

from lincl.models import CommandResult


def _render_command(args: tuple[str, ...]) -> str:
    executable = shlex.quote(args[0])
    argument_count = len(args) - 1
    if argument_count == 0:
        return executable
    suffix = "argument" if argument_count == 1 else "arguments"
    return f"{executable} ({argument_count} {suffix})"


class CommandError(Exception):
    """Base class for errors reported by lincl."""


class ConfigurationError(CommandError):
    """Raised when project execution defaults are invalid."""

    def __init__(self, path: Path, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(f"Invalid lincl configuration in {path}: {reason}")


class CommandNotFoundError(CommandError, ImportError):
    """Raised when an executable cannot be resolved on PATH."""

    def __init__(self, command_name: str) -> None:
        self.command_name = command_name
        super().__init__(f"Executable {command_name!r} was not found on PATH.")


class CommandExecutionError(CommandError):
    """Raised when a command starts but exits unsuccessfully."""

    def __init__(self, result: CommandResult[str]) -> None:
        self.result = result
        if result.returncode < 0:
            outcome = f"was terminated by signal {-result.returncode}"
        else:
            outcome = f"exited with status {result.returncode}"
        message = f"Command {_render_command(result.args)} {outcome}."
        diagnostic = result.stderr.strip()
        if diagnostic:
            message = f"{message}\nstderr: {diagnostic}"
        super().__init__(message)

    @property
    def args_vector(self) -> tuple[str, ...]:
        return self.result.args

    @property
    def returncode(self) -> int:
        return self.result.returncode

    @property
    def stdout(self) -> str:
        return self.result.stdout

    @property
    def stderr(self) -> str:
        return self.result.stderr


class OutputParseError(CommandError):
    """Raised when a parser cannot transform successful command output."""

    def __init__(
        self,
        result: CommandResult[str],
        reason: Exception,
    ) -> None:
        self.result = result
        self.reason = reason
        command = _render_command(result.args)
        super().__init__(
            f"Could not parse output from command {command}: {reason}"
        )


class CommandTimeoutError(CommandError):
    """Raised after a command exceeds its deadline and is terminated."""

    def __init__(
        self,
        args: tuple[str, ...],
        timeout: float,
        stdout: str,
        stderr: str,
    ) -> None:
        self.args_vector = args
        self.timeout = timeout
        self.stdout = stdout
        self.stderr = stderr
        command = _render_command(args)
        message = f"Command {command} timed out"
        super().__init__(f"{message} after {timeout:g} seconds.")


class CommandLaunchError(CommandError):
    """Raised when the operating system cannot start an executable."""

    def __init__(self, args: tuple[str, ...], reason: OSError) -> None:
        self.args_vector = args
        self.reason = reason
        super().__init__(
            f"Could not start command {_render_command(args)}: {reason}"
        )
