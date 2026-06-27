#!/usr/bin/env python3
"""Restore the Athena Investment Intelligence build onto this host.

EXPLICIT, OPT-IN. Athena does NOT run this automatically — nothing scans this
folder at launch. Run it by hand (or ask Athena to) to rehydrate the work into
~/.athena on a new server.

Usage:
    python restore.py            # restore (refuses to overwrite existing files)
    python restore.py --force    # overwrite existing files
    python restore.py --dry-run  # show what would happen, change nothing

What it does NOT do:
    - It does NOT write any secrets (~/.athena/.env is yours to populate).
    - It does NOT transfer OAuth tokens (they were never exported; re-consent).
    - It does NOT create cron jobs (see MANIFEST.json cron_jobs_to_recreate).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _athena_home() -> Path:
    env = os.getenv("ATHENA_HOME")
    return Path(env) if env else Path.home() / ".athena"


# (export subdir, restore-to relative to ATHENA_HOME)
COMPONENTS = [
    ("athena_invest", "athena_invest"),
    ("plugins/schwab_marketdata", "plugins/schwab_marketdata"),
    ("scripts", "scripts"),
]


def restore(force: bool, dry_run: bool) -> int:
    home = _athena_home()
    print(f"Target ATHENA_HOME: {home}")
    if dry_run:
        print("(dry-run — no changes will be made)\n")

    total, skipped, written = 0, 0, 0
    for src_rel, dst_rel in COMPONENTS:
        src = HERE / src_rel
        if not src.exists():
            print(f"  ! missing in export: {src_rel}")
            continue
        for root, _dirs, files in os.walk(src):
            rel = Path(root).relative_to(src)
            for f in files:
                total += 1
                s = Path(root) / f
                d = home / dst_rel / rel / f
                if d.exists() and not force:
                    skipped += 1
                    continue
                if dry_run:
                    print(f"  would write {d}")
                    written += 1
                    continue
                d.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(s, d)
                # keep the watchdog script executable
                if f.endswith(".py") and dst_rel == "scripts":
                    os.chmod(d, 0o755)
                written += 1

    print(f"\nFiles: {total} total | {written} {'planned' if dry_run else 'written'} "
          f"| {skipped} skipped (exist; use --force to overwrite)")

    man = HERE / "MANIFEST.json"
    if man.exists():
        m = json.loads(man.read_text())
        print("\n--- POST-RESTORE CHECKLIST ---")
        for step in m.get("post_restore_checklist", []):
            print(f"  [ ] {step}")
        print("\nSecrets needed in ~/.athena/.env:",
              ", ".join(m.get("secrets_required_after_restore", {}).get("keys", [])))
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Restore Athena Investment build.")
    ap.add_argument("--force", action="store_true", help="overwrite existing files")
    ap.add_argument("--dry-run", action="store_true", help="preview only")
    args = ap.parse_args()
    sys.exit(restore(force=args.force, dry_run=args.dry_run))
