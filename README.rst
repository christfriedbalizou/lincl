lincl
=====

|CI| |CodeQL| |PyPI| |Python|

Shell fluency, Python control.

``lincl`` turns the Linux programs you already know into Python callables. You
keep familiar command names and options, while gaining Python's types, control
flow, exceptions, and testability. There is no shell interpolation: ``lincl``
builds an argument vector, captures output, and turns failures into structured
exceptions.

A real automation script
------------------------

Suppose a bootstrap script must work across Debian, Ubuntu, Fedora, Rocky
Linux, and older RHEL-family systems. It needs to identify the distribution,
select ``apt-get``, ``dnf``, or ``yum``, install Git and curl, and make a
shallow checkout. This is a complete script, not pseudocode:

.. code-block:: python

   #!/usr/bin/env python3
   import os
   import platform
   import shutil
   from pathlib import Path

   import lincl

   REPOSITORY = "https://github.com/example/service.git"
   DESTINATION = Path.home() / "src" / "service"
   REQUIRED_PACKAGES = ("git", "curl")


   def select_package_manager():
       release = platform.freedesktop_os_release()
       family = {
           release.get("ID", ""),
           *release.get("ID_LIKE", "").split(),
       }

       if family & {"debian", "ubuntu"}:
           return "apt-get", {"yes": True}
       if shutil.which("dnf"):
           return "dnf", {"assumeyes": True}
       if shutil.which("yum"):
           return "yum", {"assumeyes": True}
       raise RuntimeError(f"unsupported Linux family: {sorted(family)}")


   manager_name, install_options = select_package_manager()
   manager = getattr(lincl, manager_name)

   if os.geteuid() != 0:
       manager = lincl.sudo.subcommand(manager_name)

   if manager_name == "apt-get":
       manager.update()
   manager.install(*REQUIRED_PACKAGES, **install_options)

   DESTINATION.parent.mkdir(parents=True, exist_ok=True)
   lincl.git.clone(REPOSITORY, DESTINATION, depth=1)

Side by side
~~~~~~~~~~~~

The three approaches perform the same work. The difference is how much
process machinery stays in your application code:

.. list-table::
   :header-rows: 1
   :widths: 18 27 27 28

   * - Task
     - lincl
     - Bash
     - ``subprocess``
   * - Install packages
     - ``manager.install(*packages, yes=True)``
     - ``sudo apt-get install --yes "${packages[@]}"``
     - Build and pass a complete argument list to ``subprocess.run``.
   * - Clone
     - ``lincl.git.clone(url, destination, depth=1)``
     - ``git clone --depth=1 "$url" "$destination"``
     - ``subprocess.run(["git", "clone", "--depth=1", ...])``
   * - Branch by distribution
     - Normal Python sets, mappings, and functions.
     - ``case`` or compound ``[[ ... ]]`` expressions.
     - Normal Python sets, mappings, and functions.
   * - Failure handling
     - Typed exceptions carrying status, stdout, and stderr.
     - Exit codes, traps, and explicitly captured streams.
     - ``CalledProcessError`` plus repeated capture and decoding policy.
   * - Argument safety
     - Argument vectors with ``shell=False``.
     - Correct quoting and array usage are the author's responsibility.
     - Safe with argument vectors; unsafe if callers opt into a shell.
   * - Best fit
     - Linux automation that benefits from Python without subprocess noise.
     - Small, shell-native workflows.
     - Low-level or highly customized process management.

The last operations become the commands you would write by hand:

.. code-block:: console

   sudo apt-get update
   sudo apt-get install --yes git curl
   git clone --depth=1 https://github.com/example/service.git ~/src/service

On Fedora or Rocky Linux, the same Python script naturally emits ``dnf install
--assumeyes git curl`` instead. If the process already runs as root, it omits
``sudo``. A rejected package transaction or failed clone raises a typed lincl
exception retaining the exit status, stdout, and stderr; a missing executable
raises a specific ``CommandNotFoundError``.

Why not just Bash?
~~~~~~~~~~~~~~~~~~

The equivalent Bash is compact, but distribution parsing, branching, quoting,
and error reporting quickly become the script's responsibility:

.. code-block:: bash

   #!/usr/bin/env bash
   set -euo pipefail

   . /etc/os-release
   family="${ID} ${ID_LIKE:-}"
   prefix=()
   if (( EUID != 0 )); then
     prefix=(sudo)
   fi

   if [[ " ${family} " == *" debian "* ||
         " ${family} " == *" ubuntu "* ]]; then
     "${prefix[@]}" apt-get update
     "${prefix[@]}" apt-get install --yes git curl
   elif command -v dnf >/dev/null 2>&1; then
     "${prefix[@]}" dnf install --assumeyes git curl
   elif command -v yum >/dev/null 2>&1; then
     "${prefix[@]}" yum install --assumeyes git curl
   else
     printf 'unsupported Linux family: %s\n' "${family}" >&2
     exit 1
   fi

   mkdir -p "${HOME}/src"
   git clone --depth=1 \
     https://github.com/example/service.git "${HOME}/src/service"

Bash remains excellent when a shell is the right abstraction. ``lincl`` earns
its place when the workflow needs Python libraries, richer data structures,
unit tests, concurrency, or structured recovery without wrapping every command
in repetitive process-management code.

Why not plain ``subprocess``?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The standard library is the foundation underneath lincl and is the right
choice when you need complete low-level control. Here is the complete Python
equivalent:

.. code-block:: python

   #!/usr/bin/env python3
   import os
   import platform
   import shutil
   import subprocess
   from pathlib import Path

   REPOSITORY = "https://github.com/example/service.git"
   DESTINATION = Path.home() / "src" / "service"
   REQUIRED_PACKAGES = ("git", "curl")


   def execute(*arguments):
       return subprocess.run(
           arguments,
           check=True,
           capture_output=True,
           text=True,
       )


   release = platform.freedesktop_os_release()
   family = {
       release.get("ID", ""),
       *release.get("ID_LIKE", "").split(),
   }

   if family & {"debian", "ubuntu"}:
       manager = "apt-get"
       install_option = "--yes"
   elif shutil.which("dnf"):
       manager = "dnf"
       install_option = "--assumeyes"
   elif shutil.which("yum"):
       manager = "yum"
       install_option = "--assumeyes"
   else:
       raise RuntimeError(f"unsupported Linux family: {sorted(family)}")

   prefix = () if os.geteuid() == 0 else ("sudo",)
   if manager == "apt-get":
       execute(*prefix, manager, "update")
   execute(
       *prefix,
       manager,
       "install",
       install_option,
       *REQUIRED_PACKAGES,
   )

   DESTINATION.parent.mkdir(parents=True, exist_ok=True)
   execute(
       "git",
       "clone",
       "--depth=1",
       REPOSITORY,
       str(DESTINATION),
   )

With lincl, the command structure remains visible without repeating capture,
decoding, exit checking, and error adaptation at every call site.

Quick start
-----------

``lincl`` requires Linux, Python 3.10 or newer, and the command you want to use
on ``PATH``.

.. code-block:: console

   python -m pip install lincl

Import a command by name and call it like a function:

.. code-block:: python

   from lincl import echo

   result = echo("Hello from lincl")

   assert result.stdout == "Hello from lincl\n"
   assert result.stderr == ""
   assert result.value == "Hello from lincl\n"

Import aliases work as you would expect:

.. code-block:: python

   from lincl import git as version_control

   result = version_control("version")
   print(result.stdout, end="")

Commands with subcommands support attribute chaining. Options are placed after
the selected subcommand, where tools such as Git expect them:

.. code-block:: python

   from lincl import git

   result = git.clone(repository_url, destination, depth=1)

That call runs ``git clone --depth=1 REPOSITORY_URL DESTINATION``. Use the
explicit ``git.subcommand("clone")`` form when a subcommand conflicts with a
``lincl`` API attribute such as ``configure`` or ``executable``. ``run`` is not
reserved: ``docker.run(...)`` executes the real Docker ``run`` subcommand.

Python help, backed by the system manual
----------------------------------------

Dynamic commands are callable objects with useful interactive help:

.. code-block:: pycon

   >>> from lincl import ls
   >>> help(ls)
   Help on CommandCallable in module lincl:

   ls(*arguments, **options)
       Run the installed `ls` command as a Python callable.
       ...

The help begins with the Python argument, parser, result, and process-control
conventions, then includes the locally installed ``man`` page. Manual lookup is
non-interactive and bounded by a short timeout. If ``man`` or the command's
manual entry is unavailable, the Python help remains available with a clear
fallback message. ``lincl`` reads documentation through ``man``; it never runs
an arbitrary command with ``--help`` while importing it.

How arguments are translated
----------------------------

Positional arguments stay positional. Keyword arguments become command-line
options and are placed before them:

- ``v=True`` becomes ``-v``.
- ``recursive=True`` becomes ``--recursive``.
- ``show_tabs=True`` becomes ``--show-tabs``.
- ``color=False`` and ``color=None`` are omitted.
- ``output="report.txt"`` becomes ``--output=report.txt``.
- ``include=["curl", "git"]`` becomes ``--include=curl,git``.

Text, numbers, and text-based ``pathlib.Path`` values are accepted as
arguments. Boolean positional arguments, bytes, and other ambiguous values are
rejected before the process starts.

For example:

.. code-block:: python

   from lincl import debootstrap

   result = debootstrap(
       "stable",
       "/srv/chroot",
       variant="buildd",
       include=["ca-certificates", "curl"],
   )

This produces:

.. code-block:: console

   debootstrap --variant=buildd --include=ca-certificates,curl stable /srv/chroot

Working with results
--------------------

Every successful call returns an immutable ``CommandResult`` with ``args``,
``returncode``, ``stdout``, ``stderr``, and ``value``. By default, ``value`` is
the unchanged stdout string.

Call ``parser()`` on one result to transform that call's captured stdout:

.. code-block:: python

   from lincl import ls

   entries = ls("./").parser(str.splitlines)
   entries.append("another-entry")
   entries = entries + ["one-more-entry"]

   for line in entries:
       print(line)

   assert entries.returncode == 0

``CommandResult`` forwards common value operations, indexing, iteration, and
attribute access to its parsed value. Operators such as ``+`` return another
result carrying the same process metadata. The original text remains available
as ``entries.stdout`` even if the parsed list is later changed.

The result behaves like its value but is not an instance of the value's type.
Use the explicit ``value`` attribute when an API or type check requires the
concrete object:

.. code-block:: python

   assert not isinstance(entries, list)
   assert isinstance(entries.value, list)

A parser receives stdout only and runs only after the command exits
successfully. If parsing fails, ``OutputParseError`` retains the textual result
on ``error.result`` and chains the parser's exception as its cause.

For repeated calls, create a configured command. Commands are immutable, so
the original remains unchanged and safe for concurrent callers:

.. code-block:: python

   parsed_ls = ls.configure(parser=str.splitlines)
   entries = parsed_ls("./")

Reassignment is also valid when every following call in the current scope
should use that parser:

.. code-block:: python

   ls = ls.configure(parser=str.splitlines)
   entries = ls("./")

``str.splitlines`` only splits display output; it does not understand the
command's data format. In particular, Unix filenames may contain newlines. Use
``pathlib.Path.iterdir()`` when you need actual directory entries, and parse a
command's machine-readable format when correctness depends on its structure.

For a numeric command such as ``wc``, convert the documented output explicitly
instead of relying on command-name magic:

.. code-block:: python

   from lincl import wc

   def parse_count(output):
       return int(output.split()[0])

   count_words = wc.configure(parser=parse_count)
   word_count = count_words("-w", "README.rst").value

Failures you can catch
----------------------

All library errors inherit from ``CommandError``. A non-zero exit raises
``CommandExecutionError`` and keeps the complete ``CommandResult`` on
``error.result``:

.. code-block:: python

   from lincl import CommandExecutionError, grep

   try:
       result = grep("needle", "missing.txt")
   except CommandExecutionError as error:
       print(f"exit status: {error.returncode}")
       print(error.stderr, end="")

``CommandNotFoundError`` is also an ``ImportError`` for compatibility with
normal imports. ``CommandLaunchError`` reports operating-system failures that
happen while starting a resolved executable. ``CommandTimeoutError`` includes
the deadline and any output captured before termination. Exception messages
describe the executable without repeating command arguments, which may contain
secrets. Their structured attributes are intended for program logic; handle
those values and captured stderr with the same care as the original input.

Process controls
----------------

Timeouts, input, environments, working directories, and decoding belong to an
``ExecutionOptions`` value. They are deliberately separate from the keyword
arguments translated into command-line options:

.. code-block:: python

   from lincl import ExecutionOptions, python3

   configured_python = python3.configure(
       execution=ExecutionOptions(
           timeout=5,
           cwd="/tmp",
           input="hello",
       ),
   )
   result = configured_python(
       "-c",
       "import os, sys; print(os.getcwd(), sys.stdin.read())",
   )

Pass command options to the explicit API with ``options={...}`` when you also
need process controls. ``env`` replaces the child environment, matching
``subprocess.run``; copy ``os.environ`` first when you want to add or override
only a few variables. Output is decoded as UTF-8 with ``surrogateescape`` by
default so unexpected bytes can be round-tripped. Both settings are
configurable.

Every keyword passed directly to a command belongs to that command. ``lincl``
does not reserve ``parser`` or silently remove it from the argument vector.

Project defaults
----------------

Safe execution defaults can be stored in the nearest project configuration
file. For new projects, use the standard tool table in ``pyproject.toml``:

.. code-block:: toml

   [tool.lincl]
   encoding = "utf-8"
   errors = "surrogateescape"
   timeout = 1

``setup.cfg`` and ``tox.ini`` are also supported for established projects:

.. code-block:: ini

   [lincl]
   encoding = utf-8
   errors = surrogateescape
   timeout = 1

``lincl`` searches the current directory and then its parents. The nearest
configuration wins; within one directory, precedence is ``pyproject.toml``,
``setup.cfg``, then ``tox.ini``. An explicitly supplied ``ExecutionOptions``
replaces project defaults for that call.

Only ``encoding``, ``errors``, and ``timeout`` are configurable. Working
directories, environments, and input are request-specific and remain explicit.
Output capture, exit checking, and ``shell=False`` are safety and result-model
invariants and cannot be weakened by project configuration. Unknown or invalid
settings raise ``ConfigurationError`` with the source path.

Security
--------

``lincl`` invokes commands with an argument vector rather than interpolating
arguments into a shell command. That removes a common source of shell
injection, but it does not make every command or option safe.

Validate command names, options, paths, and input that come from users or
external systems. Be especially careful with commands running as root:
``lincl`` does not bypass permissions, and it cannot protect you from a
dangerous option accepted by the program you invoke.

Getting help
------------

Found a bug or have an idea? Open an issue in the `GitHub issue tracker`_. A
small reproduction, the Python version, Linux distribution, command version,
and full error output make problems much easier to diagnose.

Please search existing issues before opening a new one. For larger changes,
start with an issue so the design can be discussed before anyone invests a lot
of time in an implementation.

Contributing
------------

Contributions are welcome—bug fixes, tests, documentation, and careful API
improvements all help.

Create a virtual environment, then install the locked development toolchain:

.. code-block:: console

   git clone https://github.com/christfriedbalizou/lincl.git
   cd lincl
   python -m venv .venv
   . .venv/bin/activate
   python -m pip install --require-hashes -r requirements-dev.txt
   python -m pip install -e .
   pre-commit install --install-hooks

Run the same checks used by CI before opening a pull request:

.. code-block:: console

   make lint
   make test
   make check-dist

Runtime dependencies belong in ``requirements.in``; development and test
dependencies belong in ``requirements-dev.in``. Run ``make upgrade-reqs`` to
rebuild both hashed lockfiles after changing either input file.

CI tests Python 3.10 through 3.14, exercises source installation on Debian,
Ubuntu, and Rocky Linux, audits dependencies, runs CodeQL, and verifies both
the wheel and source distribution.

License
-------

``lincl`` is available under the `MIT License`_.

.. _GitHub issue tracker: https://github.com/christfriedbalizou/lincl/issues
.. _MIT License: https://github.com/christfriedbalizou/lincl/blob/main/LICENSE

.. |CI| image:: https://img.shields.io/github/actions/workflow/status/christfriedbalizou/lincl/ci.yml?branch=main&style=for-the-badge&label=CI
   :target: https://github.com/christfriedbalizou/lincl/actions/workflows/ci.yml
   :alt: CI status
.. |CodeQL| image:: https://img.shields.io/github/actions/workflow/status/christfriedbalizou/lincl/codeql.yml?branch=main&style=for-the-badge&label=CodeQL
   :target: https://github.com/christfriedbalizou/lincl/actions/workflows/codeql.yml
   :alt: CodeQL status
.. |PyPI| image:: https://img.shields.io/pypi/v/lincl.svg?style=for-the-badge&cacheSeconds=300
   :target: https://pypi.org/project/lincl/
   :alt: PyPI version
.. |Python| image:: https://img.shields.io/pypi/pyversions/lincl.svg?style=for-the-badge
   :target: https://pypi.org/project/lincl/
   :alt: Supported Python versions
