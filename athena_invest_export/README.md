# Athena Investment Intelligence — Portable Export

A self-contained, **opt-in** snapshot of the Athena Investment Intelligence
build. It lives in the repo so it travels with your code, but **Athena does NOT
load it automatically** — nothing scans this folder at launch. You rehydrate it
deliberately, only when you want to.

## What's inside
```
athena_invest_export/
├── MANIFEST.json        # what this is, where each piece restores to, post-restore steps
├── restore.py           # explicit restore script (opt-in; never auto-run)
├── README.md            # this file
├── athena_invest/       # → ~/.athena/athena_invest  (reference, agents, mandate, PROGRESS.md)
├── plugins/
│   └── schwab_marketdata/  # → ~/.athena/plugins/schwab_marketdata  (the Schwab plugin)
└── scripts/
    └── schwab_token_health_check.py  # → ~/.athena/scripts
```

## What is deliberately NOT here (security)
- **No secrets.** `~/.athena/.env` (Schwab Client ID/Secret) is never exported.
- **No OAuth tokens.** The live `tokens.json` is excluded — tokens are host- and
  time-bound; you re-run the consent flow on the new host.
- **No `__pycache__` / `.pyc`.**

## Why it isn't loaded by default
Athena discovers plugins from `~/.athena/plugins/`, skills from
`~/.athena/skills/`, etc. This export sits under `~/Code/athena/` (the repo) —
**outside every Athena discovery path** — so a fresh Athena instance ignores it
entirely until you run `restore.py`, which copies the pieces into `~/.athena/`.

## Restore on a new server
```bash
cd ~/Code/athena/athena_invest_export
python restore.py --dry-run     # preview
python restore.py               # restore (won't overwrite existing files)
python restore.py --force       # overwrite if re-restoring
```
Then complete the post-restore checklist (also printed by restore.py and in
MANIFEST.json):
1. Add Schwab secrets to `~/.athena/.env` (chmod 600):
   `SCHWAB_APP_KEY`, `SCHWAB_APP_SECRET`, `SCHWAB_CALLBACK_URL`.
2. Run the OAuth consent flow — see
   `~/.athena/plugins/schwab_marketdata/README.md` — to mint fresh tokens.
3. Verify: `python -m pytest ~/.athena/plugins/schwab_marketdata/ -q --asyncio-mode=auto`
4. Recreate the token-health cron (definition in MANIFEST.json).
5. Read `~/.athena/athena_invest/PROGRESS.md` for remaining TODOs.

## Refreshing this export (from the source host)
Re-run the snapshot step in Athena, or manually copy the three components back
here, excluding `tokens.json`, `.env`, and `__pycache__`.
