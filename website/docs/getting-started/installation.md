---
sidebar_position: 2
title: "Installation"
description: "Install Athena Agent on Linux, macOS, WSL2, native Windows, or Android via Termux"
---

# Installation

Get Athena Agent up and running in under two minutes!

## Quick Install
### With the Athena Desktop installer on macOS or Windows (recommended)
To easily install the command-line and desktop applications, [download the Athena Desktop installer](https://github.com/pavel4ai/athena/) from our website and run it.

### Without Athena Desktop:
For a command-line only install without Athena Desktop, run:

#### Linux / macOS / WSL2 / Android (Termux)
```bash
curl -fsSL https://github.com/pavel4ai/athena/install.sh | bash
```

#### Windows (native)

Run in powershell:
```powershell
iex (irm https://github.com/pavel4ai/athena/install.ps1) 
```

If you want to install & run Athena Desktop after a command-line only install, simply run
```bash
athena desktop
```

### What the Installer Does

The installer handles everything automatically — all dependencies (Python, Node.js, ripgrep, ffmpeg), the repo clone, virtual environment, global `athena` command setup, and LLM provider configuration. By the end, you're ready to chat.

#### Install Layout

Where the installer puts things depends on whether you're installing as a normal user or as root:

| Installer | Code lives at | `athena` binary | Data directory |
|---|---|---|---|
| pip install | Python site-packages | `~/.local/bin/athena` (console_scripts) | `~/.athena/` |
| Per-user (git installer) | `~/.athena/athena-agent/` | `~/.local/bin/athena` (symlink) | `~/.athena/` |
| Root-mode (`sudo curl … \| sudo bash`) | `/usr/local/lib/athena-agent/` | `/usr/local/bin/athena` | `/root/.athena/` (or `$ATHENA_HOME`) |

The root-mode **FHS layout** (`/usr/local/lib/…`, `/usr/local/bin/athena`) matches where other system-wide developer tools land on Linux. It's useful for shared-machine deployments where one system install should serve every user. Per-user config (auth, skills, sessions) still lives under each user's `~/.athena/` or explicit `ATHENA_HOME`.

### After Installation

Reload your shell and start chatting:

```bash
source ~/.bashrc   # or: source ~/.zshrc
athena             # Start chatting!
```

To reconfigure individual settings later, use the dedicated commands:

```bash
athena model          # Choose your LLM provider and model
athena tools          # Configure which tools are enabled
athena gateway setup  # Set up messaging platforms
athena config set     # Set individual config values
athena setup          # Or run the full setup wizard to configure everything at once
```

:::tip Fastest path: Nous Portal
One subscription covers 300+ models plus the [Tool Gateway](/user-guide/features/tool-gateway) (web search, image generation, TTS, cloud browser). Skip the per-tool key juggling:

```bash
athena setup --portal
```

That logs you in, sets Nous as your provider, and turns on the Tool Gateway in one command.
:::

---

## Prerequisites

**Installer:** On non-Windows platforms, the only prerequisite is **Git**. On Linux, also make sure `curl` and `xz-utils` are available (the installer downloads Node.js as a `.tar.xz` archive). The desktop app additionally requires `g++` (or `build-essential` on Debian/Ubuntu) to compile native modules. The installer automatically handles everything else:

- **uv** (fast Python package manager)
- **Python 3.11** (via uv, no sudo needed)
- **Node.js v22** (for browser automation and WhatsApp bridge)
- **ripgrep** (fast file search)
- **ffmpeg** (audio format conversion for TTS)

:::info
You do **not** need to install Python, Node.js, ripgrep, or ffmpeg manually. The installer detects what's missing and installs it for you. Just make sure `git` is available (`git --version`). On Linux, ensure `curl` and `xz-utils` are installed (`sudo apt install curl xz-utils` on Debian/Ubuntu). For the desktop app, also install `build-essential` (`sudo apt install build-essential`).
:::

:::tip Nix users
If you use Nix (on NixOS, macOS, or Linux), there's a dedicated setup path with a Nix flake, declarative NixOS module, and optional container mode. See the **[Nix & NixOS Setup](./nix-setup.md)** guide.
:::

---

## Manual / Developer Installation

If you want to clone the repo and install from source — for contributing, running from a specific branch, or having full control over the virtual environment — see the [Development Setup](../developer-guide/contributing.md#development-setup) section in the Contributing guide.

---

## Non-Sudo / System Service User Installs

Running Athena as a dedicated unprivileged user (e.g. a `athena` systemd service account, or any user without `sudo` access) is supported. The only thing on the install path that genuinely needs root is Playwright's `--with-deps` step, which `apt`-installs shared libraries (`libnss3`, `libxkbcommon`, etc.) used by Chromium. The installer detects whether sudo is available and gracefully degrades when it isn't — it will install the Chromium binary into the service user's own Playwright cache and print the exact command an administrator needs to run separately.

**Recommended split (Debian/Ubuntu):**

1. **One time, as an admin user with sudo**, install the system libraries Chromium needs:
   ```bash
   sudo npx playwright install-deps chromium
   ```
   (You can run this from anywhere — `npx` will fetch Playwright on the fly.)

2. **As the unprivileged service user**, run the regular installer. It will detect the missing sudo, skip `--with-deps`, and install Chromium into the user's local Playwright cache:
   ```bash
   curl -fsSL https://github.com/pavel4ai/athena/install.sh | bash
   ```

   If you want to skip the Playwright step entirely — for example because you're running headless and don't need browser automation — pass `--skip-browser`:
   ```bash
   curl -fsSL https://github.com/pavel4ai/athena/install.sh | bash -s -- --skip-browser
   ```

3. **Make `athena` available to the service user's shells.** The installer writes the launcher to `~/.local/bin/athena`. System service accounts often have a minimal PATH that doesn't include `~/.local/bin`. Either add it to the user's environment, or symlink the launcher into a system location:
   ```bash
   # Option A — add to the service user's profile
   echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc

   # Option B — symlink system-wide (run as an admin)
   sudo ln -s /home/athena/.athena/athena-agent/venv/bin/athena /usr/local/bin/athena
   ```

4. **Verify:** `athena doctor` should now run cleanly. If you get `ModuleNotFoundError: No module named 'dotenv'`, you're invoking the repo source `athena` file (`~/.athena/athena-agent/athena`) with system Python instead of the venv launcher (`~/.athena/athena-agent/venv/bin/athena`) — fix step 3.

The same pattern works on Arch (the installer uses pacman with the same sudo-detection logic), Fedora/RHEL, and openSUSE — those distros don't support `--with-deps` at all, so an administrator always installs the system libraries separately. The relevant `dnf`/`zypper` commands are printed by the installer.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `athena: command not found` | Reload your shell (`source ~/.bashrc`) or check PATH |
| `API key not set` | Run `athena model` to configure your provider, or `athena config set OPENROUTER_API_KEY your_key` |
| Missing config after update | Run `athena config check` then `athena config migrate` |

For more diagnostics, run `athena doctor` — it will tell you exactly what's missing and how to fix it.

## Install method auto-detection

Athena auto-detects whether it was installed via `pip`, the git installer, Homebrew, or NixOS, and `athena update` prints the matching update command for that path. There's no env var to set — the detection is based on the install layout (Python site-packages, `~/.athena/athena-agent/`, Homebrew prefix, or Nix store path). `athena doctor` also surfaces the detected method under its environment summary.
