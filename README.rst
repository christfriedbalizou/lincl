lincl
=====

|CI| |CodeQL| |PyPI| |Python|

Linux commands, with a Python-shaped interface.

If you have ever reached for ``subprocess`` just to copy a file or ask a tool
for its version, ``lincl`` is for you. It turns programs already installed on
your machine into Python callables:

.. code-block:: python

   from lincl import cp

   stdout, stderr = cp(
       "notes.txt",
       "notes.backup.txt",
       preserve="mode,timestamps",
   )

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

   stdout, stderr = echo("Hello from lincl")

   assert stdout == "Hello from lincl\n"
   assert stderr == ""

You can also resolve a command at runtime:

.. code-block:: python

   from lincl import command

   git = command("git")
   stdout, stderr = git("version")

How arguments are translated
----------------------------

Positional arguments stay positional. Keyword arguments become command-line
options and are placed before them:

- ``v=True`` becomes ``-v``.
- ``recursive=True`` becomes ``--recursive``.
- ``show_tabs=True`` becomes ``--show-tabs``.
- ``output="report.txt"`` becomes ``--output=report.txt``.
- ``include=["curl", "git"]`` becomes ``--include=curl,git``.

For example:

.. code-block:: python

   from lincl import debootstrap

   stdout, stderr = debootstrap(
       "stable",
       "/srv/chroot",
       variant="buildd",
       include=["ca-certificates", "curl"],
   )

This produces:

.. code-block:: console

   debootstrap --variant=buildd --include=ca-certificates,curl stable /srv/chroot

Successful commands return ``(stdout, stderr)`` as text. If a command exits
with a non-zero status, ``lincl`` raises ``RuntimeError`` with the command and
captured standard error. Importing a command that is not installed raises
``ImportError``.

Project status
--------------

``lincl`` is small and usable, but its execution API is still evolving. Before
using it in production or with untrusted input, keep these current limitations
in mind:

- ``False`` still emits a boolean option. Omit the keyword when you do not want
  the flag.
- Lists are comma-separated. Repeated options and space-separated list formats
  are not supported yet.
- Arguments must be strings where required by ``subprocess``. Convert numbers
  and ``pathlib.Path`` objects before passing them.
- Output is captured in memory and decoded as text. Streaming and bytes modes
  do not have public APIs yet.
- Timeouts, cancellation, input, environment overrides, and working-directory
  controls do not have public APIs yet.
- Execution failures use ``RuntimeError`` rather than a structured exception.
- Importing a missing command prints a diagnostic before raising
  ``ImportError``.
- ``from lincl import *`` is intentionally unsupported because the available
  commands depend on the host system.

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
