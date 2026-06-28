#!/usr/bin/env python3
"""Go-live: clean up all pre-flight mock state and switch Athena to live trading.

Run this when the real Schwab cohort accounts + trading app are ready and you
want to stop paper trading. It:
  1. Archives mock state (cohort files) to mock/.archive/<timestamp>/ (not deleted).
  2. Switches broker mode to "live".
  3. Prints a go-live checklist.

Usage:
    python go_live.py            # archive mock state + switch to live
    python go_live.py --dry-run  # show what would happen
    python go_live.py --purge    # delete mock state instead of archiving
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import time
from pathlib import Path


def _athena_home() -> Path:
    env = os.getenv("ATHENA_HOME")
    return Path(env) if env else Path.home() / ".athena"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--purge", action="store_true", help="delete mock state instead of archiving")
    args = ap.parse_args()

    home = _athena_home()
    mock_dir = home / "athena_invest" / "schwab" / "mock"
    # mock cohort files actually live under athena_invest/mock per MockBroker
    mock_dir = home / "athena_invest" / "mock"
    mode_path = home / "athena_invest" / "schwab" / "mode.json"

    mock_files = sorted(mock_dir.glob("*.json")) if mock_dir.exists() else []
    print(f"ATHENA_HOME: {home}")
    print(f"Mock cohort files: {[f.name for f in mock_files]}")

    if args.dry_run:
        print("(dry-run)")
        print(f"  would {'PURGE' if args.purge else 'archive'} {len(mock_files)} mock file(s)")
        print("  would set mode -> live")
        return 0

    if mock_files:
        if args.purge:
            for f in mock_files:
                f.unlink()
            print(f"  purged {len(mock_files)} mock file(s)")
        else:
            ts = time.strftime("%Y%m%d-%H%M%S")
            arch = mock_dir / ".archive" / ts
            arch.mkdir(parents=True, exist_ok=True)
            for f in mock_files:
                shutil.move(str(f), str(arch / f.name))
            print(f"  archived {len(mock_files)} mock file(s) -> {arch}")

    mode_path.parent.mkdir(parents=True, exist_ok=True)
    mode_path.write_text('{"mode": "live"}')
    print("  mode -> LIVE")

    print("\n--- GO-LIVE CHECKLIST ---")
    for step in [
        "Trading Schwab app created + subscribed to Trader API, creds in ~/.athena/.env.",
        "OAuth consent completed for the trading app (fresh tokens).",
        "Real cohort mandates created in ~/.athena/athena_invest/mandate/.",
        "schwab_accounts returns your REAL accounts (reconciliation works).",
        "Human-approval delivery (Telegram) is wired and tested.",
        "Re-read PROGRESS.md — confirm no remaining blockers.",
    ]:
        print(f"  [ ] {step}")
    print("\nAthena is now in LIVE mode. Orders will hit the real Trader API "
          "(after human approval).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
