from pathlib import Path
import tomllib

import athena_constants


REPO_ROOT = Path(__file__).resolve().parents[1]


def _old_brand_terms() -> tuple[str, ...]:
    lower = "her" + "mes"
    title = "Her" + "mes"
    upper = "HER" + "MES"
    return (
        lower,
        title,
        upper,
        f"{lower}-agent",
        f"{title}-Agent",
        f".{lower}",
    )


def test_project_metadata_exposes_athena_entrypoints_only():
    data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert data["project"]["name"] == "athena-agent"
    assert data["project"]["scripts"] == {
        "athena": "athena_cli.main:main",
        "athena-agent": "run_agent:main",
        "athena-acp": "acp_adapter.entry:main",
    }
    assert all(
        not script.startswith(_old_brand_terms()[0])
        for script in data["project"]["scripts"]
    )


def test_runtime_defaults_use_athena_paths_and_env(monkeypatch, tmp_path):
    monkeypatch.delenv("ATHENA_HOME", raising=False)
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setattr(athena_constants.sys, "platform", "linux")

    assert athena_constants.get_athena_home() == tmp_path / ".athena"

    custom_home = tmp_path / "custom-athena"
    monkeypatch.setenv("ATHENA_HOME", str(custom_home))
    assert athena_constants.get_athena_home() == custom_home


def test_no_old_brand_references_remain_in_project_files():
    skipped_dirs = {
        ".git",
        ".venv",
        ".pytest_cache",
        ".ruff_cache",
        "venv",
        "node_modules",
        "__pycache__",
    }
    forbidden = _old_brand_terms()
    offenders: list[str] = []

    for path in REPO_ROOT.rglob("*"):
        relative_parts = path.relative_to(REPO_ROOT).parts
        if any(part in skipped_dirs for part in relative_parts):
            continue
        if relative_parts and relative_parts[0] in {"build", "dist"}:
            continue
        if any(term in path.name for term in forbidden):
            offenders.append(str(path.relative_to(REPO_ROOT)))
            continue
        if not path.is_file() or path.is_symlink():
            continue
        data = path.read_bytes()
        if b"\0" in data:
            continue
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            continue
        if any(term in text for term in forbidden):
            offenders.append(str(path.relative_to(REPO_ROOT)))

    assert not offenders
