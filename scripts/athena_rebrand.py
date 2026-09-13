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
    return text, protected


def _transform_text(text: str) -> str:
    protected_text, protected = _protect_text(text)
    transformed = _replace_product_tokens(protected_text)
    for marker, value in protected:
        transformed = transformed.replace(marker, value)
    return transformed


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


def _plan(root: Path) -> tuple[list[tuple[Path, Path]], list[Path]]:
    renames: list[tuple[Path, Path]] = []
    text_changes: list[Path] = []
    tracked = _tracked_paths(root)

    for source in tracked:
        relative = source.relative_to(root)
        target = root / _target_relative_path(relative)
        if source != target:
            renames.append((source, target))

    sources = {source for source, _target in renames}
    targets: set[Path] = set()
    for source, target in renames:
        if target in targets:
            raise RuntimeError(f"Multiple paths map to {target}")
        if target.exists() and target not in sources:
            raise RuntimeError(f"Rebrand target already exists: {target}")
        targets.add(target)

    target_for = dict(renames)
    for source in tracked:
        path = target_for.get(source, source)
        source_for_read = source if source.exists() else path
        if _transformed_bytes(source_for_read) is not None:
            text_changes.append(path)

    return renames, text_changes


def _apply(root: Path) -> tuple[int, int]:
    tracked = _tracked_paths(root)
    renames = [
        (source, root / _target_relative_path(source.relative_to(root)))
        for source in tracked
        if source != root / _target_relative_path(source.relative_to(root))
    ]

    sources = {source for source, _target in renames}
    targets: set[Path] = set()
    for _source, target in renames:
        if target in targets:
            raise RuntimeError(f"Multiple paths map to {target}")
        if target.exists() and target not in sources:
            raise RuntimeError(f"Rebrand target already exists: {target}")
        targets.add(target)

    target_for = dict(renames)
    for source, target in sorted(
        renames,
        key=lambda pair: len(pair[0].parts),
        reverse=True,
    ):
        target.parent.mkdir(parents=True, exist_ok=True)
        source.rename(target)

    changed = 0
    for source in tracked:
        path = target_for.get(source, source)
        transformed = _transformed_bytes(path)
        if transformed is None:
            continue
        _atomic_write(path, transformed)
        changed += 1

    return len(renames), changed


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Apply or inspect the Athena product-identity transform.",
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    root = _repo_root()
    if args.check:
        renames, text_changes = _plan(root)
        print(
            f"planned path renames: {len(renames)}; "
            f"planned text changes: {len(text_changes)}"
        )
        return 1 if renames or text_changes else 0

    renamed, changed = _apply(root)
    print(f"renamed paths: {renamed}; changed text files: {changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
