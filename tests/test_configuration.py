import sys

import pytest

from lincl import CommandTimeoutError, ConfigurationError, ExecutionOptions
from lincl.configuration import load_execution_options
from lincl.core import _resolve_command


@pytest.fixture(autouse=True)
def clear_configuration_cache():
    from lincl import configuration

    configuration._read_values_at_version.cache_clear()


def test_pyproject_configuration_is_discovered_from_parent(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        "[tool.lincl]\nencoding = 'utf8'\nerrors = 'replace'\ntimeout = 1\n"
    )
    nested = tmp_path / "src" / "package"
    nested.mkdir(parents=True)

    options = load_execution_options(nested)

    assert options.encoding == "utf8"
    assert options.errors == "replace"
    assert options.timeout == 1


@pytest.mark.parametrize("filename", ["setup.cfg", "tox.ini"])
def test_ini_configuration_is_supported(tmp_path, filename):
    (tmp_path / filename).write_text(
        "[lincl]\nencoding = latin-1\nerrors = strict\ntimeout = 2.5\n"
    )

    options = load_execution_options(tmp_path)

    assert options.encoding == "latin-1"
    assert options.errors == "strict"
    assert options.timeout == 2.5


def test_nearest_configuration_wins(tmp_path):
    (tmp_path / "setup.cfg").write_text("[lincl]\ntimeout = 5\n")
    nested = tmp_path / "project"
    nested.mkdir()
    (nested / "pyproject.toml").write_text("[tool.lincl]\ntimeout = 1\n")

    assert load_execution_options(nested).timeout == 1


def test_invalid_configuration_identifies_file(tmp_path):
    path = tmp_path / "pyproject.toml"
    path.write_text("[tool.lincl]\nshell = true\n")

    with pytest.raises(
        ConfigurationError, match="unsupported option.*shell"
    ) as raised:
        load_execution_options(tmp_path)

    assert raised.value.path == path


def test_project_timeout_applies_automatically(tmp_path, monkeypatch):
    (tmp_path / "pyproject.toml").write_text("[tool.lincl]\ntimeout = 0.05\n")
    monkeypatch.chdir(tmp_path)
    python = _resolve_command(sys.executable)

    with pytest.raises(CommandTimeoutError):
        python("-c", "import time; time.sleep(1)")


def test_explicit_execution_options_replace_project_defaults(
    tmp_path, monkeypatch
):
    (tmp_path / "pyproject.toml").write_text("[tool.lincl]\ntimeout = 0.01\n")
    monkeypatch.chdir(tmp_path)
    python = _resolve_command(sys.executable)

    result = python._with_execution(ExecutionOptions(timeout=1))(
        "-c", "print('finished')"
    )

    assert result.stdout == "finished\n"


def test_configured_encoding_decodes_output(tmp_path, monkeypatch):
    (tmp_path / "tox.ini").write_text("[lincl]\nencoding = latin-1\n")
    monkeypatch.chdir(tmp_path)
    python = _resolve_command(sys.executable)

    result = python("-c", "import sys; sys.stdout.buffer.write(b'\\xff')")

    assert result.stdout == "ÿ"


def test_execution_options_validate_codec_names():
    with pytest.raises(ValueError, match="unknown encoding"):
        ExecutionOptions(encoding="not-a-real-codec")


@pytest.mark.parametrize("timeout", [True, "1"])
def test_execution_options_reject_non_numeric_timeouts(timeout):
    with pytest.raises(TypeError, match="number or None"):
        ExecutionOptions(timeout=timeout)


@pytest.mark.parametrize("timeout", [float("inf"), float("nan")])
def test_execution_options_reject_non_finite_timeouts(timeout):
    with pytest.raises(ValueError, match="finite positive number"):
        ExecutionOptions(timeout=timeout)
