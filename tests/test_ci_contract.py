import json
import re
from pathlib import Path

import pytest

from scripts.verify_installation import verify_installation

ROOT = Path(__file__).resolve().parents[1]
SMOKE_SCRIPT = "scripts/verify_installation.py"


def test_installation_smoke_contract():
    verify_installation()


def test_delivery_commands_share_the_smoke_contract():
    ci = (ROOT / ".github/workflows/ci.yml").read_text()
    release = (ROOT / ".github/workflows/release.yml").read_text()
    makefile = (ROOT / "Makefile").read_text()

    assert ci.count(SMOKE_SCRIPT) == 3
    assert release.count(SMOKE_SCRIPT) == 2
    assert makefile.count(SMOKE_SCRIPT) == 2
    assert "output, error = echo" not in ci
    assert "output, error = echo" not in release


def test_renovate_dispatch_uses_the_repository_app_and_tracks_the_run():
    workflow = (ROOT / ".github/workflows/renovate.yaml").read_text()

    assert "secrets.BOT_APP_ID" in workflow
    assert "secrets.BOT_CLIENT_ID" not in workflow
    assert '--field "distinct_id=${DISTINCT_ID}"' in workflow
    assert 'case "${run_id}" in' in workflow


@pytest.mark.parametrize(
    "filename, expected",
    [
        ("requirements.txt", True),
        ("requirements-dev.txt", True),
        ("requirements.in", False),
        ("requirements-dev.in", False),
        ("other-requirements.txt", False),
    ],
)
def test_renovate_resolves_generated_lockfiles(filename, expected):
    configuration = json.loads(
        (ROOT / ".renovaterc.json5").read_text(encoding="utf-8")
    )
    patterns = configuration["pip-compile"]["managerFilePatterns"]

    assert (
        any(re.search(pattern[1:-1], filename) for pattern in patterns)
        is expected
    )
    assert configuration["pip_requirements"]["enabled"] is False
    if expected:
        header = (ROOT / filename).read_text().splitlines()[:6]
        assert any("pip-compile " in line for line in header)
        assert any(filename.replace(".txt", ".in") in line for line in header)
