"""Command discovery, argument translation, and execution."""

import os
import shutil
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TypeAlias

from lincl.exceptions import (
    CommandExecutionError,
    CommandLaunchError,
    CommandNotFoundError,
    CommandTimeoutError,
)
from lincl.models import CommandResult, ExecutionOptions

ScalarArgument: TypeAlias = str | int | float | os.PathLike[str]
OptionValue: TypeAlias = (
    ScalarArgument | Sequence[ScalarArgument] | bool | None
)


def _stringify(value: ScalarArgument, description: str) -> str:
    if isinstance(value, bool):
        raise TypeError(f"{description} must not be a boolean")
    if isinstance(value, os.PathLike):
        rendered = os.fspath(value)
        if not isinstance(rendered, str):
            raise TypeError(f"{description} must not resolve to bytes")
        return rendered
    if isinstance(value, (str, int, float)):
        return str(value)
    raise TypeError(
        f"{description} must be text, a number, or a text path, "
        f"not {type(value).__name__}"
    )


def _option_name(name: str) -> str:
    if not isinstance(name, str) or not name or name.startswith("-"):
        raise ValueError(f"invalid command option name: {name!r}")
    normalized = name.replace("_", "-")
    prefix = "-" if len(normalized) == 1 else "--"
    return f"{prefix}{normalized}"


def _serialize_option(name: str, value: OptionValue) -> list[str]:
    option = _option_name(name)
    if value is True:
        return [option]
    if value is False or value is None:
        return []
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        rendered = [
            _stringify(item, f"item in option {name!r}") for item in value
        ]
        return [f"{option}={','.join(rendered)}"]
    rendered = _stringify(value, f"value for option {name!r}")
    return [f"{option}={rendered}"]


def transcribe(
    *arguments: ScalarArgument,
    **options: OptionValue,
) -> list[str]:
    """Translate Python arguments into the documented command-line form."""
    command_arguments: list[str] = []
    for name, value in options.items():
        command_arguments.extend(_serialize_option(name, value))
    command_arguments.extend(
        _stringify(argument, "positional argument") for argument in arguments
    )
    return command_arguments


def _normalize_timeout_output(
    output: str | bytes | None,
    execution: ExecutionOptions,
) -> str:
    if output is None:
        return ""
    if isinstance(output, bytes):
        return output.decode(execution.encoding, execution.errors)
    return output


@dataclass(frozen=True, slots=True)
class Command:
    """A resolved executable that can be called repeatedly."""

    executable: str

    def __call__(
        self,
        *arguments: ScalarArgument,
        **options: OptionValue,
    ) -> CommandResult:
        return self.run(*arguments, options=options)

    def run(
        self,
        *arguments: ScalarArgument,
        options: Mapping[str, OptionValue] | None = None,
        execution: ExecutionOptions | None = None,
    ) -> CommandResult:
        """Run with explicit command options and process controls."""
        process_options = execution or ExecutionOptions()
        command_options = dict(options or {})
        args = (
            self.executable,
            *transcribe(*arguments, **command_options),
        )
        environment = (
            dict(process_options.env)
            if process_options.env is not None
            else None
        )
        try:
            completed = subprocess.run(
                args,
                capture_output=True,
                check=False,
                cwd=process_options.cwd,
                encoding=process_options.encoding,
                env=environment,
                errors=process_options.errors,
                input=process_options.input,
                shell=False,
                timeout=process_options.timeout,
            )
        except subprocess.TimeoutExpired as error:
            timeout = process_options.timeout
            if timeout is None:
                raise
            raise CommandTimeoutError(
                args,
                timeout,
                _normalize_timeout_output(error.stdout, process_options),
                _normalize_timeout_output(error.stderr, process_options),
            ) from error
        except OSError as error:
            raise CommandLaunchError(args, error) from error

        result = CommandResult(
            args=args,
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
        if not result.ok:
            raise CommandExecutionError(result)
        return result


def command(name: str | os.PathLike[str]) -> Command:
    """Resolve an executable by name or path and cache its absolute path."""
    command_name = _stringify(name, "command name")
    if not command_name:
        raise ValueError("command name must not be empty")
    executable = shutil.which(command_name, mode=os.X_OK)
    if executable is None:
        raise CommandNotFoundError(command_name)
    return Command(executable=os.path.abspath(executable))
