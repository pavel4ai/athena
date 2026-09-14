"""Behavior contracts for the repeatable Athena identity transform."""

from __future__ import annotations

import importlib.util
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "athena_rebrand.py"


def _load_transform():
    spec = importlib.util.spec_from_file_location(
        "athena_rebrand_test_subject",
        SCRIPT_PATH,
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_internal_paths_are_renamed():
    transform = _load_transform()
    old = transform.OLD_LOWER

    assert transform._target_relative_path(
        Path(f"{old}_cli/main.py")
    ) == Path("athena_cli/main.py")
    assert transform._target_relative_path(
        Path(f"{old}_constants.py")
    ) == Path("athena_constants.py")


def test_shared_metrics_wire_identifier_is_preserved():
    transform = _load_transform()
    wire = f"{transform.OLD_LOWER}.shared_metrics"

    assert transform._target_relative_path(
        Path(f"{transform.OLD_LOWER}_cli/observability/schemas/{wire}.v2.schema.json")
    ) == Path(f"athena_cli/observability/schemas/{wire}.v2.schema.json")
    assert transform._transform_text(
        f'{{"schema_version":"{wire}.v2"}}'
    ) == f'{{"schema_version":"{wire}.v2"}}'


def test_external_parser_packages_are_preserved():
    transform = _load_transform()

    source = (
        f"{transform.OLD_LOWER}-parser "
        f"{transform.OLD_LOWER}-estree"
    )

    assert transform._transform_text(source) == source


def test_historical_upstream_links_are_preserved():
    transform = _load_transform()
    repository = f"{transform.OLD_TITLE}-Agent"
    source = (
        f"https://github.com/NousResearch/{repository}/issues/123 "
        f"https://github.com/NousResearch/{repository}/pull/456"
    )

    assert transform._transform_text(source) == source


def test_external_model_identifiers_are_preserved():
    transform = _load_transform()
    source = (
        f"NousResearch/{transform.OLD_TITLE}-3-Llama-3.1-70B "
        f"nousresearch/{transform.OLD_LOWER}-4-405b "
        f"FP16_{transform.OLD_TITLE}_4.5 "
        f"{transform.OLD_TITLE}-Agent-Thinking-GLM-4.7-SFT2"
    )

    assert transform._transform_text(source) == source


def test_product_repository_urls_move_to_athena_origin():
    transform = _load_transform()
    repository = f"NousResearch/{transform.OLD_TITLE}-Agent"
    source = f"https://github.com/{repository}.git"

    assert transform._transform_text(source) == (
        "https://github.com/pavel4ai/athena.git"
    )


def test_user_interface_publisher_moves_to_futurebound():
    transform = _load_transform()

    assert transform._transform_text(
        'footer: { org: "Futurebound Corp." }'
    ) == 'footer: { org: "Futurebound Corp." }'


def test_repair_restores_external_model_ids_after_legacy_transform():
    transform = _load_transform()
    source = (
        "NousResearch/Hermes-3-Llama-3.1-70B "
        "nousresearch/hermes-4-405b "
        "Hermes-Agent-Thinking-GLM-4.7-SFT2"
    )

    assert transform._repair_external_model_text(source) == (
        "NousResearch/Hermes-3-Llama-3.1-70B "
        "nousresearch/hermes-4-405b "
        "Hermes-Agent-Thinking-GLM-4.7-SFT2"
    )


def test_product_identity_and_runtime_names_are_replaced():
    transform = _load_transform()
    source = (
        f"{transform.OLD_TITLE} {transform.OLD_UPPER}_HOME "
        f"~/.{transform.OLD_LOWER} "
        f"from {transform.OLD_LOWER}_cli import main"
    )

    assert transform._transform_text(source) == (
        "Athena ATHENA_HOME ~/.athena from athena_cli import main"
    )
