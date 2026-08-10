"""Load validated project defaults for command execution."""

import configparser
import os
from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

from lincl.exceptions import ConfigurationError
from lincl.models import ExecutionOptions

_SUPPORTED_OPTIONS = frozenset({"encoding", "errors", "timeout"})


def _find_config(start: Path) -> tuple[Path, str] | None:
    for directory in (start, *start.parents):
        candidates = (
            (directory / "pyproject.toml", "toml"),
            (directory / "setup.cfg", "ini"),
            (directory / "tox.ini", "ini"),
        )
        for path, format_name in candidates:
            if path.is_file() and _read_values(path, format_name):
                return path, format_name
    return None


def _read_values(path: Path, format_name: str) -> dict[str, Any]:
    try:
        modified = path.stat().st_mtime_ns
    except OSError as error:
        raise ConfigurationError(path, str(error)) from error
    return _read_values_at_version(path, format_name, modified)


@lru_cache(maxsize=128)
def _read_values_at_version(
    path: Path,
    format_name: str,
    modified: int,
) -> dict[str, Any]:
    try:
        if format_name == "toml":
            with path.open("rb") as config_file:
                document = tomllib.load(config_file)
            tools = document.get("tool", {})
            if not isinstance(tools, Mapping):
                raise ConfigurationError(path, "tool must be a table")
            values = tools.get("lincl", {})
        else:
            parser = configparser.ConfigParser(interpolation=None)
            with path.open(encoding="utf-8") as config_file:
                parser.read_file(config_file)
            values = (
                dict(parser["lincl"]) if parser.has_section("lincl") else {}
            )
    except (OSError, configparser.Error, tomllib.TOMLDecodeError) as error:
        raise ConfigurationError(path, str(error)) from error
    if not isinstance(values, Mapping):
        raise ConfigurationError(path, "lincl configuration must be a table")
    return dict(values)


def _parse_timeout(value: Any, path: Path) -> float:
    if isinstance(value, bool):
        raise ConfigurationError(path, "timeout must be a positive number")
    try:
        timeout = float(value)
    except (TypeError, ValueError) as error:
        raise ConfigurationError(
            path, "timeout must be a positive number"
        ) from error
    if timeout <= 0:
        raise ConfigurationError(path, "timeout must be a positive number")
    return timeout


def _validated_options(
    values: Mapping[str, Any], path: Path
) -> ExecutionOptions:
    unknown = sorted(set(values) - _SUPPORTED_OPTIONS)
    if unknown:
        names = ", ".join(unknown)
        raise ConfigurationError(path, f"unsupported option(s): {names}")
    options: dict[str, Any] = {}
    if "timeout" in values:
        options["timeout"] = _parse_timeout(values["timeout"], path)
    for name in ("encoding", "errors"):
        if name in values:
            value = values[name]
            if not isinstance(value, str) or not value:
                raise ConfigurationError(path, f"{name} must be text")
            options[name] = value
    try:
        return ExecutionOptions(**options)
    except ValueError as error:
        raise ConfigurationError(path, str(error)) from error


def load_execution_options(
    start: str | os.PathLike[str] | None = None,
) -> ExecutionOptions:
    directory = Path.cwd() if start is None else Path(start)
    location = _find_config(directory.resolve())
    if location is None:
        return ExecutionOptions()
    path, format_name = location
    return _validated_options(_read_values(path, format_name), path)
