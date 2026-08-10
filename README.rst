lincl
=====

|CI| |CodeQL| |PyPI| |Python|

Use installed Linux commands as small, readable Python callables without
writing the same ``subprocess`` boilerplate in every project.

``lincl`` resolves a command from ``PATH``, converts Python arguments to a
command-line argument vector, runs it without a shell, captures standard
output and standard error, and checks the exit status.

.. code-block:: python

   from lincl import cp as copy

   stdout, stderr = copy("source.txt", "destination.txt", force=True)

The call above executes the equivalent of:

.. code-block:: console

   cp --force source.txt destination.txt

Project status
--------------

The current release provides the original, intentionally small command
wrapper. Work is planned on stricter argument handling, typed execution
errors, timeouts, safer process controls, and richer Python help. Until those
features land, read `Current behavior and limitations`_ before using
``lincl`` with untrusted input or privileged commands.

Requirements
------------

- Linux with the command you want to invoke installed and available on
  ``PATH``.
- Python 3.10 or newer.
- The permissions required by the invoked command. ``lincl`` does not grant
  privileges or bypass normal operating-system controls.

Installation
------------

Install the latest release from PyPI:

.. code-block:: console

   python -m pip install lincl

For local development, clone the repository and install the locked tools:

.. code-block:: console

   git clone https://github.com/christfriedbalizou/lincl.git
   cd lincl
   python -m pip install --require-hashes -r requirements-dev.txt
   python -m pip install -e .
   pre-commit install --install-hooks

Usage
-----

Import any executable by its command name. Importing fails immediately with
``ImportError`` if the executable cannot be found:

.. code-block:: python

   from lincl import echo
   from lincl import command

   stdout, stderr = echo("Hello from lincl")
   git = command("git")
   version_stdout, version_stderr = git("version")

Positional arguments are appended to the command. Keyword arguments are
placed before positional arguments and converted to options:

- One-character names use a single dash: ``v=True`` becomes ``-v``.
- Longer names use two dashes: ``recursive=True`` becomes ``--recursive``.
- Underscores become dashes: ``show_tabs=True`` becomes ``--show-tabs``.
- Non-boolean values use ``--option=value``.
- Lists become comma-separated values: ``include=["A", "B"]`` becomes
  ``--include=A,B``.

For example:

.. code-block:: python

   from lincl import debootstrap

   stdout, stderr = debootstrap(
       "stable",
       "/srv/chroot",
       variant="buildd",
       include=["ca-certificates", "curl"],
   )

This produces the argument vector represented by:

.. code-block:: console

   debootstrap --variant=buildd --include=ca-certificates,curl stable /srv/chroot

Successful commands return a ``(stdout, stderr)`` tuple containing text. A
non-zero exit raises ``RuntimeError`` with the rendered command and captured
standard error.

Current behavior and limitations
--------------------------------

- Boolean values currently emit their option regardless of whether the value
  is ``True`` or ``False``. Omit a keyword to omit its flag.
- List values are joined with commas; repeated options and space-separated
  list conventions are not yet supported.
- Arguments must currently be strings where the underlying implementation
  requires strings. Convert ``pathlib.Path`` and numeric values explicitly.
- Output is captured in memory and decoded as text. There is no streaming or
  bytes-mode public API yet.
- There is no public timeout, cancellation, environment, input, or working
  directory API yet.
- Failures currently use ``RuntimeError`` rather than a typed exception with
  structured exit details.
- A missing dynamically imported command currently prints a diagnostic before
  raising ``ImportError``. Library logging behavior will be corrected with the
  core error model.
- ``from lincl import *`` is intentionally unsupported because available
  commands depend on the host.
- Command availability and option syntax vary by Linux distribution and
  installed command version. ``lincl`` does not install or emulate commands.
- Do not construct command names or arguments from untrusted input without
  validating them. Although execution uses an argument vector rather than a
  shell, the invoked program can still interpret dangerous options or paths.

Development
-----------

The committed lockfiles are the source of truth for development tools. Common
commands are:

.. code-block:: console

   make sync
   make lint
   make test
   make build
   make check-dist

Add runtime dependencies to ``requirements.in`` and test/development
dependencies to ``requirements-dev.in``. Run ``make upgrade-reqs`` to refresh
the hashed lockfiles. Pre-commit runs the same formatting and lint checks as
CI.

CI tests every supported Python version on Ubuntu and smoke-tests the package
on Debian, Ubuntu, and Rocky Linux. It also runs pre-commit, dependency audits,
CodeQL analysis, package builds, metadata checks, and installation tests for
both wheel and source distributions.

Releasing
---------

Version numbers come from ``lincl.__version__``. Create a release commit and
tag with one of:

.. code-block:: console

   bumpversion patch
   bumpversion minor
   bumpversion major

Push the commit and tag, then create a GitHub Release for that tag. The release
workflow verifies that the tag matches ``lincl.__version__``, runs the full
test and build path, attests the artifacts, and publishes the exact artifacts
to PyPI through Trusted Publishing. The ``pypi`` GitHub environment and PyPI
trusted publisher must be configured before the first release; no PyPI token
is required in repository secrets.

License
-------

``lincl`` is released under the MIT License. See ``LICENSE``.

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
