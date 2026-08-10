"""Build Python help for dynamically imported commands."""

import os
import re
import shutil
import subprocess
from functools import lru_cache

_ANSI_ESCAPE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
_OVERSTRIKE = re.compile(r".\x08")


def _plain_text(output: str) -> str:
    while "\x08" in output:
        output = _OVERSTRIKE.sub("", output)
    return _ANSI_ESCAPE.sub("", output).strip()


@lru_cache(maxsize=128)
def _read_manual(command_name: str) -> str | None:
    man = shutil.which("man")
    if man is None:
        return None
    environment = os.environ.copy()
    environment.update(
        {
            "MANPAGER": "cat",
            "MANWIDTH": "88",
            "PAGER": "cat",
        }
    )
    try:
        completed = subprocess.run(
            (man, "--", command_name),
            capture_output=True,
            check=False,
            encoding="utf-8",
            env=environment,
            errors="surrogateescape",
            input="",
            shell=False,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0 or not completed.stdout.strip():
        return None
    return _plain_text(completed.stdout)


def command_doc(
    command_name: str,
    executable: str,
    *,
    include_manual: bool = True,
) -> str:
    manual = _read_manual(command_name) if include_manual else None
    if manual:
        manual_text = manual
    elif include_manual:
        manual_text = (
            f"No local manual entry was found. Run `man {command_name}` on a "
            "system that provides one."
        )
    else:
        manual_text = (
            "See the parent command's manual for subcommand-specific usage."
        )
    return f"""Run the installed `{command_name}` command as a Python callable.

Python usage:
    {command_name}(*arguments, **options) -> CommandResult

`arguments` are passed positionally. Keyword names become command options:
`a=True` becomes `-a`, `all=True` becomes `--all`, and underscores become
hyphens. False and None omit an option. The default result value is the
unchanged stdout string.

The result behaves like its parsed value and also exposes `args`, `returncode`,
`stdout`, and `stderr`. Use `.value` when the concrete parsed type is required.
Use `result.parser(callable)` for one result, or `command.configure(parser=...)`
to create a reusable parsed command.
Use `command.subcommand(arg)` or `command.arg` when options belong after a
subcommand, for example `git.clone(url, destination, depth=1)`.
Use `command.configure(execution=ExecutionOptions(...))` for explicit timeouts,
input, environment variables, working directories, and decoding controls.
Project defaults for encoding, decoding errors, and timeout can be set in
`[tool.lincl]` in `pyproject.toml`. Attributes such as `.run` are always
subcommands rather than reserved lincl methods.

Executable:
    {executable}

System manual:
{manual_text}
"""
