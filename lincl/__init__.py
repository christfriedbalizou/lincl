"""Expose installed executables as Python callables."""

from typing import Any

from lincl.core import Command, command, transcribe
from lincl.exceptions import (
    CommandError,
    CommandExecutionError,
    CommandLaunchError,
    CommandNotFoundError,
    CommandTimeoutError,
)
from lincl.models import CommandResult, ExecutionOptions

__title__ = "lincl"
__version__ = "1.0.0"
__author__ = "Christfried BALIZOU"

__all__ = [
    "Command",
    "CommandError",
    "CommandExecutionError",
    "CommandLaunchError",
    "CommandNotFoundError",
    "CommandResult",
    "CommandTimeoutError",
    "ExecutionOptions",
    "command",
    "transcribe",
]


def __getattr__(name: str) -> Any:
    """Resolve a missing public attribute as an installed executable."""
    if name.startswith("_"):
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return command(name)


def __dir__() -> list[str]:
    """Return the stable public API; host commands are resolved on demand."""
    return sorted(__all__)
