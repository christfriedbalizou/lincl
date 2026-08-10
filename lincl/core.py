"""Command discovery, argument translation, and execution."""

from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from inspect import Parameter, Signature
from typing import (
    Callable,
    Generic,
    TypeAlias,
    TypeVar,
)

from lincl.configuration import load_execution_options
from lincl.documentation import command_doc
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
_HELP_SIGNATURE = Signature(
    parameters=(
        Parameter("arguments", Parameter.VAR_POSITIONAL),
        Parameter("options", Parameter.VAR_KEYWORD),
    )
)


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


def _transcribe(
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
    prefix: tuple[str, ...] = ()

    def __call__(
        self,
        *arguments: ScalarArgument,
        **options: OptionValue,
    ) -> CommandResult[Output]:
        return self.run(*arguments, options=options)

    def run(
        self,
        *arguments: ScalarArgument,
        options: Mapping[str, OptionValue] | None = None,
        execution: ExecutionOptions | None = None,
    ) -> CommandResult[Output]:
        """Run with explicit command options and process controls."""
        process_options = execution or load_execution_options()
        command_options = dict(options or {})
        args = (
            self.executable,
            *self.prefix,
            *_transcribe(*arguments, **command_options),
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

    def configure(
        self,
        *,
        parser: Callable[[str], ParsedOutput],
    ) -> "Command[ParsedOutput]":
        if not callable(parser):
            raise TypeError("parser must be callable")
        return Command(
            executable=self.executable,
            parser=parser,
            prefix=self.prefix,
        )

    def subcommand(self, name: str) -> "Command[Output]":
        rendered = _stringify(name, "subcommand name")
        if not rendered or rendered.startswith("-"):
            raise ValueError(f"invalid subcommand name: {name!r}")
        return Command(
            executable=self.executable,
            parser=self.parser,
            prefix=(*self.prefix, rendered),
        )


def _resolve_command(name: str | os.PathLike[str]) -> Command[str]:
    command_name = _stringify(name, "command name")
    if not command_name:
        raise ValueError("command name must not be empty")
    executable = shutil.which(command_name, mode=os.X_OK)
    if executable is None:
        raise CommandNotFoundError(command_name)
    return Command(executable=os.path.abspath(executable), parser=_identity)


def _as_callable(
    command_name: str,
    resolved: Command[Output],
) -> CommandCallable[Output]:
    return CommandCallable(command_name, resolved)


class CommandCallable(Generic[Output]):
    def __init__(self, command_name: str, resolved: Command[Output]) -> None:
        self._command_name = command_name
        self._resolved = resolved
        self.__name__ = command_name.rsplit(" ", 1)[-1]
        self.__qualname__ = command_name.replace(" ", ".")
        self.__module__ = "lincl"
        self.__doc__ = command_doc(
            command_name,
            resolved.executable,
            include_manual=not resolved.prefix,
        )
        self.__signature__ = _HELP_SIGNATURE

    @property
    def executable(self) -> str:
        return self._resolved.executable

    def __call__(
        self,
        *arguments: ScalarArgument,
        **options: OptionValue,
    ) -> CommandResult[Output]:
        return self._resolved(*arguments, **options)

    def run(
        self,
        *arguments: ScalarArgument,
        options: Mapping[str, OptionValue] | None = None,
        execution: ExecutionOptions | None = None,
    ) -> CommandResult[Output]:
        return self._resolved.run(
            *arguments,
            options=options,
            execution=execution,
        )

    def configure(
        self,
        *,
        parser: Callable[[str], ParsedOutput],
    ) -> CommandCallable[ParsedOutput]:
        return _as_callable(
            self._command_name,
            self._resolved.configure(parser=parser),
        )

    def subcommand(self, name: str, /) -> CommandCallable[Output]:
        return _as_callable(
            f"{self._command_name} {name}",
            self._resolved.subcommand(name),
        )

    def __getattr__(self, name: str) -> CommandCallable[Output]:
        if name.startswith("_"):
            raise AttributeError(
                f"{type(self).__name__!r} object has no attribute {name!r}"
            )
        return self.subcommand(name.replace("_", "-"))

    def __repr__(self) -> str:
        return f"<command {self._command_name!r} at {self.executable!r}>"


def _load_command(name: str) -> CommandCallable[str]:
    return _as_callable(name, _resolve_command(name))
