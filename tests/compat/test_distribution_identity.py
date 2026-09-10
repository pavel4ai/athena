"""Distribution identity contracts that must survive an upstream sync."""

from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _json(path: str) -> dict:
    return json.loads((REPO_ROOT / path).read_text(encoding="utf-8"))


def test_desktop_identity_and_protocol_remain_athena():
    package = _json("apps/desktop/package.json")
    build = package["build"]

    assert package["name"] == "athena"
    assert package["productName"] == "Athena"
    assert build["productName"] == "Athena"
    assert build["executableName"] == "Athena"
    assert build["artifactName"].startswith("Athena-")
    assert build["protocols"] == [
        {"name": "Athena Protocol", "schemes": ["athena"]}
    ]


def test_desktop_bundle_ids_remain_upgrade_compatible():
    desktop = _json("apps/desktop/package.json")
    installer = _json("apps/bootstrap-installer/src-tauri/tauri.conf.json")

    assert desktop["build"]["appId"] == "com.nousresearch.athena"
    assert installer["identifier"] == "com.nousresearch.athena.setup"


def test_bootstrap_installer_is_futurebound_branded():
    installer = _json("apps/bootstrap-installer/src-tauri/tauri.conf.json")

    assert installer["productName"] == "Athena"
    assert installer["bundle"]["publisher"] == "Futurebound Corp."
    assert "Athena Agent" in installer["bundle"]["longDescription"]


def test_acp_distribution_uses_athena_package_and_command():
    manifest = _json("acp_registry/agent.json")

    assert manifest["id"] == "athena-agent"
    assert manifest["repository"] == "https://github.com/pavel4ai/athena"
    assert manifest["distribution"]["uvx"]["package"].startswith("athena-agent[acp]")
    assert manifest["distribution"]["uvx"]["args"] == ["athena-acp"]
