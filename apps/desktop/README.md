# Athena Desktop ☤

<p align="center">
  <a href="https://github.com/pavel4ai/athena/releases"><img src="https://img.shields.io/badge/Download-macOS%20%C2%B7%20Windows%20%C2%B7%20Linux-FFD700?style=for-the-badge" alt="Download"></a>
  <a href="https://github.com/pavel4ai/athena/docs/"><img src="https://img.shields.io/badge/Docs-futurebnd.com-FFD700?style=for-the-badge" alt="Documentation"></a>
  <a href="https://futurebnd.com"><img src="https://img.shields.io/badge/Discord-5865F2?style=for-the-badge&logo=discord&logoColor=white" alt="Discord"></a>
  <a href="https://github.com/pavel4ai/athena/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License: MIT"></a>
</p>

**The native desktop app for [Athena Agent](../../README.md) — the self-improving AI agent from [Futurebound Corp.](https://futurebnd.com).** Same agent, same skills, same memory as the CLI and gateway, in a polished native window — chat with streaming tool output, side-by-side previews, a file browser, voice, and settings, no terminal required. Available for **macOS, Windows, and Linux**.

<table>
<tr><td><b>Chat with the full agent</b></td><td>Streaming responses, live tool activity, structured tool summaries, and the same conversation history as every other Athena surface.</td></tr>
<tr><td><b>Side-by-side previews</b></td><td>Render web pages, files, and tool outputs in a right-hand pane while you keep chatting.</td></tr>
<tr><td><b>File browser</b></td><td>Explore and preview the working directory without leaving the app.</td></tr>
<tr><td><b>Voice</b></td><td>Talk to Athena and hear it back.</td></tr>
<tr><td><b>Settings & onboarding</b></td><td>Manage providers, models, tools, and credentials from a real UI. First-run setup gets you to your first message in seconds.</td></tr>
<tr><td><b>Stays current</b></td><td>Built-in updates pull the latest agent and rebuild the app in place.</td></tr>
</table>

---

## Install

### Install with Athena (recommended)

Already have the Athena CLI? Just run:

```bash
athena desktop
```

It builds and launches the GUI against your existing install — same config, keys, sessions, and skills. On first launch Athena walks you through picking a provider and model; nothing else to configure.

### Prebuilt installers

Prebuilt installers are built and distributed via [the Athena Desktop website.](https://github.com/pavel4ai/athena/).

---

## Updating

The app checks for updates in the background and offers a one-click update when one is ready. You can also update any time from the CLI:

```bash
athena update
```

---

## Requirements

The installer handles everything for you (Python 3.11+, a portable Git, ripgrep).

---

## Development

Want to hack on the app itself? Install workspace deps from the repo root once, then run the dev server from this directory:

```bash
npm install          # from repo root — links apps/desktop, web, apps/shared
cd apps/desktop
npm run dev          # Vite renderer + Electron, which boots the Python backend
```

Point the app at a specific source checkout, or sandbox it away from your real config:

```bash
ATHENA_DESKTOP_ATHENA_ROOT=/path/to/clone npm run dev
ATHENA_HOME=/tmp/throwaway npm run dev
npm run dev:fake-boot   # exercise the startup overlay with deterministic delays
```

### Building installers

```bash
npm run dist:mac     # DMG + zip
npm run dist:win     # NSIS + MSI
npm run dist:linux   # AppImage + deb + rpm
npm run pack         # unpacked app under release/ (no installer)
```

Installers are built and uploaded to GitHub Releases manually. macOS/Windows signing & notarization happen automatically when the relevant credentials are present in the environment (`CSC_LINK` / `CSC_KEY_PASSWORD` / `APPLE_*` for macOS, `WIN_CSC_*` for Windows).

### How it works

The packaged app ships the Electron shell and a native React chat surface. On first launch it can install the Athena Agent runtime into `ATHENA_HOME` (`~/.athena`, or `%LOCALAPPDATA%\athena` on Windows) — the **same layout a CLI install uses**, so the two are interchangeable. Backend resolution first honours `ATHENA_DESKTOP_ATHENA_ROOT`, then a completed managed install, then a probed `athena` on `PATH` (unless `ATHENA_DESKTOP_IGNORE_EXISTING=1` is set), and finally an explicit `ATHENA_DESKTOP_ATHENA` command override for packagers/troubleshooting. The renderer (React, in `src/`) talks to a `athena dashboard` backend over the `tui_gateway`/dashboard APIs and reuses the agent runtime rather than embedding `athena --tui`. The install, backend-resolution, and self-update logic all live in `electron/main.cjs`.

### Verification

Run before opening a PR (lint may surface pre-existing warnings but must exit cleanly):

```bash
npm run fix
npm run typecheck
npm run lint
npm run test:desktop:all
```

### Troubleshooting

Boot logs land in `ATHENA_HOME/logs/desktop.log` (includes backend output and recent Python tracebacks) — check it first if the app reports a boot failure.

**macOS / Linux:**

```bash
# Force a clean first-launch setup
rm "$HOME/.athena/athena-agent/.athena-bootstrap-complete"
# Rebuild a broken Python venv
rm -rf "$HOME/.athena/athena-agent/venv"
# Reset a stuck macOS microphone prompt (macOS only)
tccutil reset Microphone com.nousresearch.athena
```

**Windows (PowerShell):**

```powershell
# Force a clean first-launch setup
Remove-Item "$env:LOCALAPPDATA\athena\athena-agent\.athena-bootstrap-complete"
# Rebuild a broken Python venv
Remove-Item -Recurse -Force "$env:LOCALAPPDATA\athena\athena-agent\venv"
```

> The default Athena home on Windows is `%LOCALAPPDATA%\athena`. Set the `ATHENA_HOME` env var if you've relocated it.

---

## Community

- 💬 [Discord](https://futurebnd.com)
- 📖 [Documentation](https://github.com/pavel4ai/athena/docs/)
- 🐛 [Issues](https://github.com/pavel4ai/athena/issues)

---

## License

MIT — see [LICENSE](../../LICENSE).

Built by [Futurebound Corp.](https://futurebnd.com).
