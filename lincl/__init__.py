"""Expose installed executables as Python callables."""

from typing import Any

from lincl.core import Command, CommandCallable, _load_command, transcribe
from lincl.exceptions import (
    CommandError,
    CommandExecutionError,
    CommandLaunchError,
    CommandNotFoundError,
    CommandTimeoutError,
    OutputParseError,
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
    "CommandCallable",
    "ExecutionOptions",
    "OutputParseError",
    "transcribe",
]


def __getattr__(name: str) -> Any:
    if name.startswith("_"):
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return _load_command(name)


def __dir__() -> list[str]:
    return sorted(__all__)
