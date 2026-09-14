#!/usr/bin/env python3
"""Apply Athena's deterministic product-identity transform to an upstream tree."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import tempfile
from pathlib import Path


OLD_LOWER = "her" + "mes"
OLD_TITLE = "Her" + "mes"
OLD_UPPER = "HER" + "MES"

NEW_LOWER = "athena"
NEW_TITLE = "Athena"
NEW_UPPER = "ATHENA"

_PATH_WIRE_MARKER = "__ATHENA_SHARED_METRICS_WIRE__"
_TEXT_MARKER_PREFIX = "__ATHENA_PRESERVED_TERM_"

_EXACT_PROTECTED_TERMS = (
    f"{OLD_LOWER}-parser",
    f"{OLD_LOWER}-estree",
    f"{OLD_LOWER}.shared_metrics",
)

_EXTERNAL_MODEL_PREFIX = re.compile(
    rf"\b(?:{OLD_TITLE}|{OLD_LOWER}|{OLD_UPPER})"
    r"(?:-Agent-Thinking|[- ](?:3|4)|3)"
)

_PRODUCT_REPOSITORY_REPLACEMENTS = (
    (f"NousResearch/{NEW_TITLE}-Agent", "pavel4ai/athena"),
    (f"NousResearch/{NEW_LOWER}-agent", "pavel4ai/athena"),
    ('org: "Futurebound Corp."', 'org: "Futurebound Corp."'),
    ("org: 'Futurebound Corp.'", "org: 'Futurebound Corp.'"),
)

_EXTERNAL_MODEL_REPAIRS = (
    (f"{NEW_TITLE}-Agent-Thinking", f"{OLD_TITLE}-Agent-Thinking"),
    (f"{NEW_LOWER}-agent-thinking", f"{OLD_LOWER}-agent-thinking"),
    (f"{NEW_UPPER}-AGENT-THINKING", f"{OLD_UPPER}-AGENT-THINKING"),
    (f"{NEW_TITLE}-3", f"{OLD_TITLE}-3"),
    (f"{NEW_TITLE}-4", f"{OLD_TITLE}-4"),
    (f"{NEW_LOWER}-3", f"{OLD_LOWER}-3"),
    (f"{NEW_LOWER}-4", f"{OLD_LOWER}-4"),
    (f"{NEW_UPPER}-3", f"{OLD_UPPER}-3"),
    (f"{NEW_UPPER}-4", f"{OLD_UPPER}-4"),
    (f"{NEW_TITLE} 3", f"{OLD_TITLE} 3"),
    (f"{NEW_TITLE} 4", f"{OLD_TITLE} 4"),
    (f"{NEW_LOWER} 3", f"{OLD_LOWER} 3"),
    (f"{NEW_LOWER} 4", f"{OLD_LOWER} 4"),
    (f"{NEW_TITLE}3", f"{OLD_TITLE}3"),
    (f"{NEW_LOWER}3", f"{OLD_LOWER}3"),
)

_UPSTREAM_HISTORY_URL = re.compile(
    r"https://github\.com/NousResearch/"
    + re.escape(f"{OLD_TITLE}-Agent")
    + r"/(?:issues|pull|commit|compare)/[^\s)\]>'\"]+",
    re.IGNORECASE,
)


def _repo_root() -> Path:
    root = Path(
        subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            text=True,
        ).strip()
    )
    if not (root / "pyproject.toml").is_file():
        raise RuntimeError(f"Not an upstream agent checkout: {root}")
    return root


def _tracked_paths(root: Path) -> list[Path]:
    output = subprocess.check_output(
        ["git", "ls-files", "-z"],
        cwd=root,
    )
    return [
        root / raw.decode("utf-8")
        for raw in output.split(b"\0")
        if raw
    ]


def _replace_product_tokens(value: str) -> str:
    return (
        value.replace(OLD_UPPER, NEW_UPPER)
        .replace(OLD_TITLE, NEW_TITLE)
        .replace(OLD_LOWER, NEW_LOWER)
    )


def _target_relative_path(relative: Path) -> Path:
    value = relative.as_posix()
    value = value.replace(
        f"{OLD_LOWER}.shared_metrics",
        _PATH_WIRE_MARKER,
    )
    value = _replace_product_tokens(value)
    value = value.replace(
        _PATH_WIRE_MARKER,
        f"{OLD_LOWER}.shared_metrics",
    )
    return Path(value)


def _protect_text(text: str) -> tuple[str, list[tuple[str, str]]]:
    protected: list[tuple[str, str]] = []

    def preserve(value: str) -> str:
        marker = f"{_TEXT_MARKER_PREFIX}{len(protected)}__"
        protected.append((marker, value))
        return marker

    text = _UPSTREAM_HISTORY_URL.sub(
        lambda match: preserve(match.group(0)),
        text,
    )
    for term in _EXACT_PROTECTED_TERMS:
        text = text.replace(term, preserve(term))
    text = _EXTERNAL_MODEL_PREFIX.sub(
        lambda match: preserve(match.group(0)),
        text,
    )
    return text, protected


def _transform_text(text: str) -> str:
    protected_text, protected = _protect_text(text)
    transformed = _replace_product_tokens(protected_text)
    for source, target in _PRODUCT_REPOSITORY_REPLACEMENTS:
        transformed = transformed.replace(source, target)
    for marker, value in protected:
        transformed = transformed.replace(marker, value)
    return transformed


def _repair_external_model_text(text: str) -> str:
    repaired = text
    for source, target in _EXTERNAL_MODEL_REPAIRS:
        repaired = repaired.replace(source, target)
    return repaired


def _transformed_bytes(path: Path) -> bytes | None:
    if path.is_symlink():
        return None
    data = path.read_bytes()
    if b"\0" in data:
        return None
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return None
    transformed = _transform_text(text)
    if transformed == text:
        return None
    return transformed.encode("utf-8")


def _atomic_write(path: Path, data: bytes) -> None:
    mode = path.stat().st_mode
    with tempfile.NamedTemporaryFile(
        prefix=f".{path.name}.",
        suffix=".athena-rebrand",
        dir=path.parent,
        delete=False,
    ) as handle:
        temp_path = Path(handle.name)
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.chmod(temp_path, mode)
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


def _path_present(path: Path) -> bool:
    return path.exists() or path.is_symlink()


def _resolve_worktree_paths(
    root: Path,
    tracked: list[Path],
) -> tuple[dict[Path, Path], list[tuple[Path, Path]]]:
    effective: dict[Path, Path] = {}
    renames: list[tuple[Path, Path]] = []

    for source in tracked:
        target = root / _target_relative_path(source.relative_to(root))
        if source == target:
            if _path_present(source):
                effective[source] = source
        elif _path_present(source):
            effective[source] = target
            renames.append((source, target))
        elif _path_present(target):
            effective[source] = target
        else:
            raise RuntimeError(f"Tracked path is missing: {source}")

    return effective, renames


def _plan(root: Path) -> tuple[list[tuple[Path, Path]], list[Path]]:
    text_changes: list[Path] = []
    tracked = _tracked_paths(root)
    effective, renames = _resolve_worktree_paths(root, tracked)

    sources = {source for source, _target in renames}
    targets: set[Path] = set()
    for source, target in renames:
        if target in targets:
            raise RuntimeError(f"Multiple paths map to {target}")
        if target.exists() and target not in sources:
            raise RuntimeError(f"Rebrand target already exists: {target}")
        targets.add(target)

    for source in tracked:
        path = effective.get(source)
        if path is None:
            continue
        if _transformed_bytes(path) is not None:
            text_changes.append(path)

    return renames, text_changes


def _apply(root: Path) -> tuple[int, int]:
    tracked = _tracked_paths(root)
    effective, renames = _resolve_worktree_paths(root, tracked)

    sources = {source for source, _target in renames}
    targets: set[Path] = set()
    for _source, target in renames:
        if target in targets:
            raise RuntimeError(f"Multiple paths map to {target}")
        if target.exists() and target not in sources:
            raise RuntimeError(f"Rebrand target already exists: {target}")
        targets.add(target)

    for source, target in sorted(
        renames,
        key=lambda pair: len(pair[0].parts),
        reverse=True,
    ):
        target.parent.mkdir(parents=True, exist_ok=True)
        source.rename(target)

    changed = 0
    for source in tracked:
        path = effective.get(source)
        if path is None:
            continue
        transformed = _transformed_bytes(path)
        if transformed is None:
            continue
        _atomic_write(path, transformed)
        changed += 1

    return len(renames), changed


def _repair_external_model_ids(root: Path) -> int:
    tracked = _tracked_paths(root)
    effective, _renames = _resolve_worktree_paths(root, tracked)
    changed = 0
    for path in effective.values():
        if path.is_symlink():
            continue
        data = path.read_bytes()
        if b"\0" in data:
            continue
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            continue
        repaired = _repair_external_model_text(text)
        if repaired == text:
            continue
        _atomic_write(path, repaired.encode("utf-8"))
        changed += 1
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Apply or inspect the Athena product-identity transform.",
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--repair-external-model-ids", action="store_true")
    args = parser.parse_args()

    root = _repo_root()
    if args.check:
        renames, text_changes = _plan(root)
        print(
            f"planned path renames: {len(renames)}; "
            f"planned text changes: {len(text_changes)}"
        )
        return 1 if renames or text_changes else 0

    if args.repair_external_model_ids:
        changed = _repair_external_model_ids(root)
        print(f"repaired external model files: {changed}")
        return 0

    renamed, changed = _apply(root)
    print(f"renamed paths: {renamed}; changed text files: {changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
