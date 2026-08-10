"""Structured command execution values."""

import os
from dataclasses import dataclass
from typing import Any, Generic, Iterator, Mapping, TypeVar, cast

Output = TypeVar("Output")


@dataclass(frozen=True, slots=True)
class CommandResult(Generic[Output]):
    """A parsed value proxy with immutable process metadata."""

    args: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str
    value: Output

    def __getattr__(self, name: str) -> Any:
        """Delegate value-specific attributes and methods."""
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

    @property
    def ok(self) -> bool:
        """Report whether the process exited successfully."""
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
        if self.timeout is not None and self.timeout <= 0:
            raise ValueError("timeout must be greater than zero")
        if not self.encoding:
            raise ValueError("encoding must not be empty")
        if not self.errors:
            raise ValueError("errors must not be empty")
