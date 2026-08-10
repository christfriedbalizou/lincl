# AGENTS.md

## Mission

`lincl` exposes installed Linux executables as safe, predictable Python
callables. Preserve the Pythonic interface while representing command
execution faithfully, including failures, timeouts, signals, output, and
platform differences.

These instructions apply to the entire repository.

## Ownership and working method

- Work as a senior Python, Linux, and shell engineer. Verify repository state
  and authoritative Python, subprocess, Linux command, packaging, and CI
  documentation before selecting APIs, versions, or configuration. Do not
  guess.
- Take ownership of the complete outcome. Include code, tests, documentation,
  packaging, and release behavior needed for the requested feature.
- Prefer the simplest production-ready design. Never simplify away
  correctness, security, data integrity, compatibility, or useful command
  diagnostics.
- Make routine technical decisions from evidence instead of returning an
  arbitrary list of options to the user.
- Before implementation, inspect relevant source, tests, configuration,
  workflows, supported platforms, and dependency constraints. Consult primary
  documentation when behavior is external or version-sensitive.
- Consider successful execution, invalid arguments, missing executables,
  permission failures, non-zero exits, timeouts, signals, output handling, and
  concurrent callers.
- Implement coherent vertical slices and complete the active phase's tests and
  exit criteria before stopping.
- Stop early only for missing authority, unavailable required access, an unsafe
  or destructive decision, failed required infrastructure, or a material scope
  or architecture change. Exhaust safe investigation, then ask one precise
  question.
- Never claim completion from inspection alone. Run relevant verification and
  report the commands and results. State clearly when an unavailable platform
  or service prevents a check.
- Keep changes focused. Preserve unrelated user changes in a dirty worktree.

## Code style — pre-commit is the law

### Code priorities

When code qualities conflict, resolve them in this order. Never silently trade
a higher priority for a lower one:

1. **Correctness** — the code does what it claims, including edge cases,
   failure paths, and concurrency. Nothing below justifies wrong results.
2. **Security and data integrity** — validate inputs, never leak secrets, and
   never lose or corrupt data. Do not sacrifice these properties for speed or
   elegance.
3. **Simplicity and readability** — choose the simplest design that fully
   satisfies the requirements and that the next engineer can understand
   without explanation.
4. **Performance** — treat performance as a requirement, not an afterthought.
   Avoid repeated executable lookups, unnecessary subprocesses, needless data
   copies, and materializing large command output when an explicitly streaming
   API would satisfy the requirement. Optimize further only when measurements
   show a hot path, and never at the expense of priorities 1–3 without a
   recorded decision.

Record any unavoidable tradeoff in the relevant issue, pull request, or
architecture documentation.

## Command-execution contract

- Treat every executable name, argument, option, environment value, working
  directory, and input stream as untrusted.
- Use argument vectors with `shell=False`. Never interpolate user-controlled
  values into shell source. A feature that intentionally invokes a shell must
  have a documented need, an explicit API boundary, validation, and adversarial
  tests.
- Resolve executables predictably and fail with a specific error when a command
  is absent or not executable. A typo such as `cpr(...)` must identify the
  missing executable without hiding the original cause.
- Keep command options separate from process-control options. Reserved Python
  controls such as timeout, environment, working directory, input, capture,
  and encoding must never leak into the child command accidentally.
- Define ordering and serialization for positional arguments, short options,
  long options, booleans, repeated options, sequences, empty values, paths,
  bytes, and `--`. Reject ambiguous or unsupported values early.
- Do not log secrets or blindly log complete arguments or environments. Provide
  explicit redaction and safe structured logging.
- Avoid deadlocks by using supported subprocess communication APIs. Handle
  large stdout/stderr, text and bytes modes, invalid encodings, timeout cleanup,
  cancellation, and child termination deliberately.
- Raise a typed, structured exception for non-zero exits and launch failures.
  Preserve at least the executable/argument vector in redacted form, exit code
  or terminating signal, stdout, stderr, timeout state, and the Python
  exception chain. Do not invent a Bash stack trace; retain shell diagnostics
  only when an invoked shell actually provides them.
- Test argument boundaries and adversarial values such as whitespace, quotes,
  glob characters, newlines, leading dashes, Unicode, empty strings, large
  output, missing executables, permission errors, non-zero exits, signals, and
  timeouts.

## Python design and style

- Support only Python and operating-system versions declared by package
  metadata and CI. When changing support, update metadata, lockfiles,
  documentation, and the test matrix together.
- Add type hints to all public functions. Prefer dataclasses or other explicit
  typed models over passing loosely structured dictionaries.
- Give every function one responsibility at one abstraction level. Split a
  function whose accurate name requires “and”.
- Use explicit names. Avoid `a`, `b`, `c`, `tmp`, `data`, `obj`, `res`, and
  single-letter names except conventional indices in short comprehensions.
- Prefer code that explains itself. First rename, extract, or simplify instead
  of adding a comment. Comments are reserved for external constraints,
  non-obvious business rules, or links to upstream specifications and bugs.
- Docstrings document behavioral contracts and rationale, not a restatement of
  the implementation.
- Never use `print()` in library code. Use
  `logger = logging.getLogger(__name__)`, and keep normal library operation
  quiet unless the caller configures logging.
- Preserve exception context with explicit chaining. Do not catch broad
  exceptions unless adding meaningful context and re-raising safely.

## Tests and verification

- Every behavior change requires tests at the lowest useful level and an
  end-to-end command execution test where applicable. A small function should
  normally have direct unit coverage; prioritize behavior and failure paths
  over mechanical one-test-per-function counting.
- Tests must be deterministic, isolated, non-interactive, and safe without
  root. Use temporary directories and controlled fixture executables instead
  of mutating host files or depending on distro-specific command output.
- Run the narrow tests while iterating, then the complete test suite and all
  pre-commit hooks before completion.
- Security-sensitive execution changes require injection, redaction, timeout,
  resource-handling, and error-shape regression tests.

## Pre-commit is the style authority

Maintain `.pre-commit-config.yaml` with hooks in this order:

1. `absolufy-imports` for absolute imports.
2. `black` with line length 79.
3. `pre-commit-hooks`: `trailing-whitespace`, `end-of-file-fixer`, and
   `debug-statements`.
4. `isort` with `--profile black` and line length 79.
5. `yesqa` to remove obsolete `# noqa` directives.
6. `flake8`, configured in `setup.cfg` with `max-line-length = 80`,
   `max-complexity = 20`, the project's documented shared ignore list, and
   `tests/*: E501` per-file ignores.

Set `fail_fast: true`. Install locally with
`pre-commit install --install-hooks`. CI must run the same hooks, and no change
is complete while they or tests are red.

## Dependencies and packaging

- Put direct runtime dependencies in `requirements.in` and development/test
  dependencies in `requirements-dev.in`.
- Compile lockfiles with `pip-tools` using
  `pip-compile --allow-unsafe --generate-hashes --no-emit-index-url` and commit
  them. Install development environments with
  `pip-sync requirements.txt requirements-dev.txt`.
- Never install a project dependency ad hoc. Add it to the appropriate `.in`
  file and recompile. Use `make upgrade-reqs` for intentional upgrades once
  that target exists.
- Keep the package editable-installable with `python -m pip install -e .`.
  `setup.py` may remain while compatibility requires it, but new packaging
  behavior should follow current PyPA standards verified from official docs.
- Maintain a single canonical `__version__` source. Package metadata,
  artifacts, tags, and releases must agree with it.

## Versioning, CI, and releases

- Use `bumpversion`/`bump2version` from checked-in configuration so patch,
  minor, and major releases update the canonical `__version__`, packaging
  metadata where needed, and release tag consistently.
- A release pipeline must test the exact commit and version, build sdist and
  wheel with the standards-based build frontend, inspect artifacts, install
  and smoke-test both artifacts, and publish only immutable successful
  artifacts.
- Publish to PyPI with GitHub Actions trusted publishing (OIDC) and protected
  environments. Do not store PyPI passwords or long-lived upload tokens.
- Test supported Python versions and representative Linux distributions in a
  documented matrix. Keep the matrix aligned with package classifiers and
  `python_requires`; do not claim an untested combination.
- Configure dependency updates for Python packages and GitHub Actions.
  Automatic merging, including major updates, is allowed only after the full
  required matrix, security checks, compatibility tests, and repository branch
  protections pass. Never bypass protections or auto-merge a breaking update
  merely because a bot opened it.
- A failed publish must be safely retryable without silently rebuilding
  different bytes for the same version. Document recovery for partial release
  failures; never overwrite an existing PyPI release.

## Git conventions

Use Conventional Commits:

- `feat:` adds or removes an application or feature.
- `fix:` corrects a defect.
- `chore:` performs maintenance such as dependency or formatting updates; do
  not use it for adding or removing features.

Commit completed changes automatically using the conventions above. Before
every commit, run the full pre-commit suite, inspect the staged diff, and
confirm no secrets, generated junk, or unrelated changes are included. Do not
commit while pre-commit or applicable tests are failing. Push only when the
user explicitly requests it. Never force-push or rewrite shared history without
explicit instruction.

## Documentation and completion report

- Keep README examples executable and aligned with the public API. Document
  supported systems, Python versions, security boundaries, exception shapes,
  command behavior, and release procedure when they change.
- At handoff, summarize the outcome, important design decisions, files changed,
  verification evidence, and any remaining risk or check that could not run.
  Do not describe planned work as implemented.
