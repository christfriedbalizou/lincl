"""Structured command execution values."""

import codecs
import math
import os
from dataclasses import dataclass
from typing import Any, Callable, Generic, Iterator, Mapping, TypeVar, cast

Output = TypeVar("Output")
ParsedOutput = TypeVar("ParsedOutput")


@dataclass(frozen=True, slots=True)
class CommandResult(Generic[Output]):
    """A parsed value proxy with immutable process metadata."""

    args: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str
    value: Output

    def __getattr__(self, name: str) -> Any:
        return getattr(self.value, name)

    def __str__(self) -> str:
        return str(self.value)

    def __iter__(self) -> Iterator[Any]:
        return iter(cast(Any, self.value))

    def __len__(self) -> int:
        return len(cast(Any, self.value))

    def __getitem__(self, key: Any) -> Any:
        return cast(Any, self.value)[key]

    def __contains__(self, item: Any) -> bool:
        return item in cast(Any, self.value)

    def __bool__(self) -> bool:
        return bool(self.value)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, CommandResult):
            return self.value == other.value
        return self.value == other

    def __add__(self, other: Any) -> "CommandResult[Any]":
        other_value = (
            other.value if isinstance(other, CommandResult) else other
        )
        return self._replace_value(cast(Any, self.value) + other_value)

    def __radd__(self, other: Any) -> "CommandResult[Any]":
        other_value = (
            other.value if isinstance(other, CommandResult) else other
        )
        return self._replace_value(other_value + cast(Any, self.value))

    def __mul__(self, count: int) -> "CommandResult[Any]":
        return self._replace_value(cast(Any, self.value) * count)

    def __rmul__(self, count: int) -> "CommandResult[Any]":
        return self.__mul__(count)

    def _replace_value(self, value: Any) -> "CommandResult[Any]":
        return CommandResult(
            args=self.args,
            returncode=self.returncode,
            stdout=self.stdout,
            stderr=self.stderr,
            value=value,
        )

    def parser(
        self,
        parser: Callable[[str], ParsedOutput],
        /,
    ) -> "CommandResult[ParsedOutput]":
        if not callable(parser):
            raise TypeError("parser must be callable")
        raw_result = CommandResult(
            args=self.args,
            returncode=self.returncode,
            stdout=self.stdout,
            stderr=self.stderr,
            value=self.stdout,
        )
        try:
            value = parser(self.stdout)
        except Exception as error:
            from lincl.exceptions import OutputParseError

            raise OutputParseError(raw_result, error) from error
        return self._replace_value(value)

    @property
    def ok(self) -> bool:
        return self.returncode == 0


@dataclass(frozen=True, slots=True)
class ExecutionOptions:
    """Process controls kept separate from command-line options."""

    timeout: float | None = None
    cwd: str | os.PathLike[str] | None = None
    env: Mapping[str, str] | None = None
    input: str | None = None
    encoding: str = "utf-8"
    errors: str = "surrogateescape"

    def __post_init__(self) -> None:
        if self.timeout is not None:
            if isinstance(self.timeout, bool) or not isinstance(
                self.timeout, (int, float)
            ):
                raise TypeError("timeout must be a number or None")
            if not math.isfinite(self.timeout) or self.timeout <= 0:
                raise ValueError("timeout must be a finite positive number")
        if not self.encoding:
            raise ValueError("encoding must not be empty")
        if not self.errors:
            raise ValueError("errors must not be empty")
        try:
            codecs.lookup(self.encoding)
        except LookupError as error:
            raise ValueError(f"unknown encoding: {self.encoding}") from error
        try:
            codecs.lookup_error(self.errors)
        except LookupError as error:
            raise ValueError(
                f"unknown encoding error handler: {self.errors}"
            ) from error
