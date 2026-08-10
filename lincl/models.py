"""Structured command execution values."""

import os
from dataclasses import dataclass
from typing import Generic, Mapping, TypeVar

Output = TypeVar("Output")


@dataclass(frozen=True, slots=True)
class CommandResult(Generic[Output]):
    """The complete, immutable outcome of a successful command."""

    args: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str
    value: Output

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
