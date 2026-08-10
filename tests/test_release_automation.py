import json
from pathlib import Path

import lincl

ROOT = Path(__file__).resolve().parents[1]


def test_release_manifest_matches_package_version():
    manifest = json.loads((ROOT / ".release-please-manifest.json").read_text())

    assert manifest["."] == lincl.__version__


def test_release_please_uses_python_strategy():
    config = json.loads((ROOT / "release-please-config.json").read_text())
    package = config["packages"]["."]

    assert package["release-type"] == "python"
    assert package["package-name"] == "lincl"
    assert package["include-component-in-tag"] is False


def test_release_automation_watches_package_inputs():
    workflow = (ROOT / ".github/workflows/release-please.yml").read_text()

    assert "lincl/**" in workflow
    assert "requirements.in" in workflow
    assert "requirements-dev.in" in workflow
    assert "README.md" in workflow
    assert "setup.cfg" in workflow
    assert "BOT_APP_PRIVATE_KEY" in workflow
    assert "googleapis/release-please-action@" in workflow
