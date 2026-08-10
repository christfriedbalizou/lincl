"""Command discovery, argument translation, and execution."""

import os
import shutil
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Callable, Generic, TypeAlias, TypeVar, overload

from lincl.exceptions import (
    CommandExecutionError,
    CommandLaunchError,
    CommandNotFoundError,
    CommandTimeoutError,
    OutputParseError,
)
from lincl.models import CommandResult, ExecutionOptions

ScalarArgument: TypeAlias = str | int | float | os.PathLike[str]
OptionValue: TypeAlias = (
    ScalarArgument | Sequence[ScalarArgument] | bool | None
)
Output = TypeVar("Output")
ParsedOutput = TypeVar("ParsedOutput")


def _identity(output: str) -> str:
    return output


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
class Command(Generic[Output]):
    """A resolved executable that can be called repeatedly."""

    executable: str
    parser: Callable[[str], Output]

    @overload
    def __call__(
        self,
        *arguments: ScalarArgument,
        parser: None = None,
        **options: OptionValue,
    ) -> CommandResult[Output]: ...

    @overload
    def __call__(
        self,
        *arguments: ScalarArgument,
        parser: Callable[[str], ParsedOutput],
        **options: OptionValue,
    ) -> CommandResult[ParsedOutput]: ...

    def __call__(
        self,
        *arguments: ScalarArgument,
        parser: Callable[[str], Any] | None = None,
        **options: OptionValue,
    ) -> CommandResult[Any]:
        if parser is not None:
            return self.with_parser(parser).run(*arguments, options=options)
        return self.run(*arguments, options=options)

    def run(
        self,
        *arguments: ScalarArgument,
        options: Mapping[str, OptionValue] | None = None,
        execution: ExecutionOptions | None = None,
    ) -> CommandResult[Output]:
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

        raw_result = CommandResult(
            args=args,
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            value=completed.stdout,
        )
        if not raw_result.ok:
            raise CommandExecutionError(raw_result)
        try:
            value = self.parser(raw_result.stdout)
        except Exception as error:
            raise OutputParseError(raw_result, error) from error
        return CommandResult(
            args=raw_result.args,
            returncode=raw_result.returncode,
            stdout=raw_result.stdout,
            stderr=raw_result.stderr,
            value=value,
        )

    def with_parser(
        self,
        parser: Callable[[str], ParsedOutput],
    ) -> "Command[ParsedOutput]":
        """Return a new command configured with an output parser."""
        if not callable(parser):
            raise TypeError("parser must be callable")
        return Command(executable=self.executable, parser=parser)


def _resolve_command(name: str | os.PathLike[str]) -> Command[str]:
    """Resolve an executable by name or path and cache its absolute path."""
    command_name = _stringify(name, "command name")
    if not command_name:
        raise ValueError("command name must not be empty")
    executable = shutil.which(command_name, mode=os.X_OK)
    if executable is None:
        raise CommandNotFoundError(command_name)
    return Command(executable=os.path.abspath(executable), parser=_identity)
