from pathlib import Path
import re
import subprocess
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


def _allowed_external_brand_terms() -> dict[str, tuple[str, ...]]:
    lower = _old_brand_terms()[0]
    return {
        "package-lock.json": (
            f"{lower}-parser",
            f"{lower}-estree",
        ),
    }


def _strip_allowed_external_references(text: str, relative: Path) -> str:
    lower, title, upper = _old_brand_terms()[:3]
    for allowed in _allowed_external_brand_terms().get(
        relative.as_posix(),
        (),
    ):
        text = text.replace(allowed, "")

    text = text.replace(f"{lower}.shared_metrics", "")
    history_url = re.compile(
        r"https://github\.com/NousResearch/"
        + re.escape(f"{title}-Agent")
        + r"/(?:issues|pull|commit|compare)/[^\s)\]>'\"]+",
        re.IGNORECASE,
    )
    text = history_url.sub("", text)

    external_model = re.compile(
        rf"(?<![A-Za-z0-9])(?:{title}|{lower}|{upper})"
        r"(?:-Agent-Thinking|[-_ ](?:3|4)|3)"
        r"[A-Za-z0-9._:/-]*"
    )
    return external_model.sub("", text)


def _tracked_project_files() -> list[Path]:
    output = subprocess.check_output(
        ["git", "ls-files", "-z"],
        cwd=REPO_ROOT,
    )
    return [
        REPO_ROOT / raw.decode("utf-8")
        for raw in output.split(b"\0")
        if raw
    ]


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
    forbidden = _old_brand_terms()
    offenders: list[str] = []

    for path in _tracked_project_files():
        relative = path.relative_to(REPO_ROOT)
        if any(term in relative.as_posix() for term in forbidden):
            if f"{forbidden[0]}.shared_metrics" not in relative.as_posix():
                offenders.append(str(relative))
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
        text = _strip_allowed_external_references(text, relative)
        if any(term in text for term in forbidden):
            offenders.append(str(relative))

    assert not offenders
