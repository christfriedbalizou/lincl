lincl
=====

|CI| |CodeQL| |PyPI| |Python|

Linux commands, with a Python-shaped interface.

If you have ever reached for ``subprocess`` just to copy a file or ask a tool
for its version, ``lincl`` is for you. It turns programs already installed on
your machine into Python callables:

.. code-block:: python

   from lincl import cp

   result = cp(
       "notes.txt",
       "notes.backup.txt",
       preserve="mode,timestamps",
   )

   assert result.returncode == 0

That call runs the equivalent of:

.. code-block:: console

   cp --preserve=mode,timestamps notes.txt notes.backup.txt

There is no shell involved. ``lincl`` builds an argument vector, starts the
command, captures its output, and checks its exit status.

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
   assert result.lines == ["Hello from lincl"]

You can also resolve a command at runtime:

.. code-block:: python

   from lincl import command

   git = command("git")
   result = git("version")
   print(result.stdout, end="")

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
``returncode``, ``stdout``, and ``stderr``. Its ``lines`` property is a handy
view for line-oriented output:

.. code-block:: python

   from lincl import ls

   result = ls()
   for line in result.lines:
       print(line)

``lines`` splits display output; it does not understand the command's data
format. In particular, Unix filenames may contain newlines. Use
``pathlib.Path.iterdir()`` when you need actual directory entries, and parse a
command's machine-readable format when correctness depends on its structure.

For a numeric command such as ``wc``, convert the documented output explicitly
instead of relying on command-name magic:

.. code-block:: python

   from lincl import wc

   word_count = int(wc("-w", "README.rst").stdout.split()[0])

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

   from lincl import ExecutionOptions, command

   python = command("python3")
   result = python.run(
       "-c",
       "import os, sys; print(os.getcwd(), sys.stdin.read())",
       execution=ExecutionOptions(
           timeout=5,
           cwd="/tmp",
           input="hello",
       ),
   )

Pass command options to the explicit API with ``options={...}`` when you also
need process controls. ``env`` replaces the child environment, matching
``subprocess.run``; copy ``os.environ`` first when you want to add or override
only a few variables. Output is decoded as UTF-8 with ``surrogateescape`` by
default so unexpected bytes can be round-tripped. Both settings are
configurable.

Project status
--------------

``lincl`` is small and usable, but its execution API is still evolving. It
captures stdout and stderr in memory, so it is not yet suitable for unbounded
or streaming output. Lists are comma-separated; repeated options and commands
that expect one flag followed by several values require positional arguments.
Bytes mode and cancellation do not have public APIs yet.

``from lincl import *`` imports the stable Python API, not every executable on
the host. Import commands by name or resolve them with ``command()``.

Command behavior also varies between distributions and command versions.
``lincl`` wraps what is installed; it does not install commands, emulate them,
or grant additional privileges.

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

Releasing
---------

This section is for maintainers. ``lincl.__version__`` is the canonical
version. Prepare a release commit and tag with one of:

.. code-block:: console

   bumpversion patch
   bumpversion minor
   bumpversion major

Push the release commit and tag, then publish a GitHub Release for that tag.
The release workflow checks the version, tests and builds the tagged commit,
attests the distributions, and sends those exact artifacts to PyPI through
Trusted Publishing.

The GitHub ``pypi`` environment and the matching PyPI Trusted Publisher must be
configured before the first release. The workflow does not use a stored PyPI
password or API token.

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
.. |PyPI| image:: https://img.shields.io/pypi/v/lincl.svg?style=for-the-badge
   :target: https://pypi.org/project/lincl/
   :alt: PyPI version
.. |Python| image:: https://img.shields.io/pypi/pyversions/lincl.svg?style=for-the-badge
   :target: https://pypi.org/project/lincl/
   :alt: Supported Python versions
