---
sidebar_position: 1
title: "CLI Commands Reference"
description: "Authoritative reference for Athena terminal commands and command families"
---

# CLI Commands Reference

This page covers the **terminal commands** you run from your shell.

For in-chat slash commands, see [Slash Commands Reference](./slash-commands.md).

## Global entrypoint

```bash
athena [global-options] <command> [subcommand/options]
```

### Global options

| Option | Description |
|--------|-------------|
| `--version`, `-V` | Show version and exit. |
| `--profile <name>`, `-p <name>` | Select which Athena profile to use for this invocation. Overrides the sticky default set by `athena profile use`. |
| `--resume <session>`, `-r <session>` | Resume a previous session by ID or title. The keyword `latest` resumes the most recent session (workspace-scoped, same lookup as `-c`). |
| `--continue [name]`, `-c [name]` | Resume the most recent session, or the most recent session matching a title. |
| `--in <dir>` | Change into `<dir>` before starting or resuming. Scopes `--resume latest` / `-c` lookups to that directory's workspace and keeps the session there (skips the recorded-cwd restore). |
| `--worktree`, `-w` | Start in an isolated git worktree for parallel-agent workflows. |
| `--yolo` | Bypass dangerous-command approval prompts. |
| `--pass-session-id` | Include the session ID in the agent's system prompt. |
| `--ignore-user-config` | Ignore `~/.athena/config.yaml` and fall back to built-in defaults. Credentials in `.env` are still loaded. |
| `--ignore-rules` | Skip auto-injection of `AGENTS.md`, `SOUL.md`, `.cursorrules`, memory, and preloaded skills. |
| `--tui` | Launch the [TUI](../user-guide/tui.md) instead of the classic CLI. Equivalent to `ATHENA_TUI=1`. Always wins over `display.interface`. |
| `--cli` | Force the classic prompt_toolkit REPL. Use this to override `display.interface: tui` for a single invocation. |
| `--dev` | With `--tui`: run the TypeScript sources directly via `tsx` instead of the prebuilt bundle (for TUI contributors). |

## Top-level commands

| Command | Purpose |
|---------|---------|
| `athena chat` | Interactive or one-shot chat with the agent. |
| `athena model` | Interactively choose the default provider and model. |
| `athena moa` | Configure named Mixture of Agents presets selectable from the model picker. |
| `athena fallback` | Manage fallback providers tried when the primary model errors. |
| `athena gateway` | Run or manage the messaging gateway service. |
| `athena proxy` | Local OpenAI-compatible proxy that attaches OAuth provider credentials. See [Subscription Proxy](../user-guide/features/subscription-proxy.md). |
| `athena egress` | Outbound credential-injection firewall for remote terminal sandboxes (iron-proxy). Disabled by default. See [Egress proxy](../user-guide/egress/iron-proxy.md). |
| `athena lsp` | Manage Language Server Protocol integration (semantic diagnostics for write_file/patch). |
| `athena setup` | Interactive setup wizard for all or part of the configuration. |
| `athena whatsapp` | Configure and pair the WhatsApp bridge. |
| `athena whatsapp-cloud` | Configure the official Meta WhatsApp Business Cloud API adapter (Business account + public webhook required). Distinct from `athena whatsapp` (Baileys personal-account bridge). |
| `athena slack` | Slack helpers (currently: generate the app manifest with every command as a native slash). |
| `athena auth` | Manage credentials — add, list, remove, reset, status, logout. Handles OAuth flows for Codex/Nous/Anthropic. |
| `athena login` / `logout` | **Deprecated** — use `athena auth` instead. |
| `athena send` | Send a one-shot message to a configured messaging platform (Telegram, Discord, Slack, Signal, SMS, …). Useful from shell scripts, cron jobs, CI hooks, and monitoring daemons — no agent loop, no LLM. |
| `athena peer` | Register peer Athena gateways on other machines and DM their agents' canonical Bot Chats (`athena peer dm <peer>[/<agent>] "…"`). The transport behind cross-machine bot-to-bot messaging. |
| `athena secrets` | Manage external secret sources (currently Bitwarden Secrets Manager) for pulling API keys at process startup instead of from `~/.athena/.env`. |
| `athena migrate` | Diagnose and (optionally) rewrite `config.yaml` to replace references to retired models or deprecated settings (e.g. `migrate xai`). |
| `athena status` | Show agent, auth, and platform status. |
| `athena cron` | Inspect and tick the cron scheduler. |
| `athena kanban` | Multi-profile collaboration board (tasks, links, dispatcher). |
| `athena project` | Manage named, multi-folder workspaces (projects). Anchors desktop session grouping and, when bound to a kanban board, gives tasks a deterministic worktree + branch convention. State is per-profile. |
| `athena webhook` | Manage dynamic webhook subscriptions for event-driven activation. |
| `athena hooks` | Inspect, approve, or remove shell-script hooks declared in `config.yaml`. |
| `athena doctor` | Diagnose config and dependency issues. |
| `athena security audit` | On-demand supply-chain audit (OSV.dev) for the venv, plugin requirements, and pinned MCP servers. |
| `athena approvals` | Approval-prompt tools — mine approval history into allowlist proposals. |
| `athena dump` | Copy-pasteable setup summary for support/debugging. |
| `athena prompt-size` | Show a byte breakdown of the system prompt + tool schemas (skills index, memory, profile). Runs offline. |
| `athena debug` | Debug tools — upload logs and system info for support. |
| `athena backup` | Back up Athena home directory to a zip file. |
| `athena checkpoints` | Inspect / prune / clear `~/.athena/checkpoints/` (the shadow store used by `/rollback`). Run with no args for a status overview. |
| `athena import` | Restore a Athena backup from a zip file. |
| `athena logs` | View, tail, and filter agent/gateway/error log files. |
| `athena config` | Show, edit, migrate, and query configuration files. |
| `athena skin` | List, switch, and tweak display skins. |
| `athena console` | Open the safe Athena command console. |
| `athena pairing` | Approve or revoke messaging pairing codes. |
| `athena skills` | Browse, install, publish, audit, and configure skills. |
| `athena bundles` | Group several skills under a single `/<name>` slash command. See [Skill Bundles](../user-guide/features/skills.md#skill-bundles). |
| `athena curator` | Background skill maintenance — status, run, pause, pin. See [Curator](../user-guide/features/curator.md). |
| `athena journey` (aliases `learning`, `memory-graph`) | Timeline of learned skills + memories over time. |
| `athena memory` | Configure external memory provider. Plugin-specific subcommands (e.g. `athena honcho`) register automatically when their provider is active. |
| `athena acp` | Run Athena as an ACP server for editor integration. |
| `athena mcp` | Manage MCP server configurations and run Athena as an MCP server. |
| `athena plugins` | Manage Athena Agent plugins (install, enable, disable, remove). |
| `athena portal` | Nous Portal status, subscription link, and Tool Gateway routing. See [Tool Gateway](../user-guide/features/tool-gateway.md). |
| `athena tools` | Configure enabled tools per platform. |
| `athena computer-use` | Install or check the Computer Use (cua-driver) backend (macOS/Windows/Linux). |
| `athena pets` | Browse, install, and select [petdex](../user-guide/features/pets.md) animated pets shown across the CLI, TUI, and desktop app. Subcommands: `list`, `install`, `select`, `show`, `off`, `scale`, `remove`, `doctor`. |
| `athena sessions` | Browse, export, prune, rename, and delete sessions. |
| `athena insights` | Show token/cost/activity analytics. |
| `athena claw` | OpenClaw migration helpers. |
| `athena import-agent` | Import a Claude Code (`~/.claude`) or Codex CLI (`~/.codex`) setup. |
| `athena dashboard` | Launch the web dashboard for managing config, API keys, and sessions. |
| `athena serve` | Start the Athena backend server (headless; powers the desktop app and remote backends). |
| `athena desktop` (alias `gui`) | Build and launch the native Electron desktop app. |
| `athena profile` | Manage profiles — multiple isolated Athena instances. |
| `athena completion` | Print shell completion scripts (bash/zsh/fish). |
| `athena --version` | Show version information. |
| `athena update` | Pull latest code and reinstall dependencies. `--check` previews without installing; `--backup` takes a pre-pull `ATHENA_HOME` snapshot. |
| `athena uninstall` | Remove Athena from the system. |

## `athena chat`

```bash
athena chat [options]
```

Common options:

| Option | Description |
|--------|-------------|
| `-q`, `--query "..."` | Seed the session with a prompt. On a real TTY the prompt is submitted **literally** as the first turn of a normal interactive session (it is never parsed as a slash command or `!` shell escape) and the session stays open — ideal for OS launchers and desktop integrations. With `--oneshot`, `-Q`, or non-TTY stdio it answers and exits. |
| `--query-file PATH` | Read the query from a file (`-` = stdin). Nothing is shell-interpreted, so quotes, `$(...)`, and backticks arrive verbatim — use this for programmatic or untrusted message bodies (Bot Mode teammate DMs use it). Mutually exclusive with `-q`. |
| `--oneshot` | With `-q`/`--query-file`: answer the query and exit (the pre-0.21 single-query behavior) instead of seeding an interactive session. Implied on non-TTY stdio and by `-Q`. |
| `-m`, `--model <model>` | Override the model for this run. |
| `-t`, `--toolsets <csv>` | Enable a comma-separated set of toolsets. |
| `--provider <provider>` | Force a provider: `auto`, `openrouter`, `nous`, `openai-codex`, `copilot-acp`, `copilot`, `anthropic`, `gemini`, `huggingface`, `novita` (aliases `novita-ai`, `novitaai`), `openai-api`, `zai`, `kimi-coding`, `kimi-coding-cn`, `minimax`, `minimax-cn`, `minimax-oauth`, `kilocode`, `xiaomi`, `arcee`, `gmi`, `upstage` (alias `solar`), `alibaba`, `alibaba-cn`, `alibaba-coding-plan` (alias `alibaba_coding`), `alibaba-coding-plan-cn`, `alibaba-token-plan`, `alibaba-token-plan-cn`, `deepseek`, `nvidia`, `ollama-cloud`, `xai` (alias `grok`), `xai-oauth` (alias `grok-oauth`), `qwen-oauth`, `bedrock`, `opencode-zen`, `opencode-go`, `opencode-free` (aliases `free`, `opencode_free`; keyless), `commandcode`, `commandcode-anthropic`, `ai-gateway`, `azure-foundry`, `lmstudio`, `stepfun`, `tencent-tokenhub` (alias `tencent`, `tokenhub`), `router` (aliases `ramp-router`, `ramp`), `nebius-token-factory` (aliases `nebius`, `nebius-tf`, `tokenfactory`), `tencent-tokenplan` (aliases `tokenplan`, `tencent-lkeap`). |
| `-s`, `--skills <name>` | Preload one or more skills for the session (can be repeated or comma-separated). |
| `-v`, `--verbose` | Verbose output. |
| `-Q`, `--quiet` | Programmatic mode: suppress banner/spinner/tool previews. |
| `--image <path>` | Attach a local image to a single query. |
| `--resume <session>` / `--continue [name]` | Resume a session directly from `chat`. |
| `--worktree` | Create an isolated git worktree for this run. |
| `--checkpoints` | Enable filesystem checkpoints before destructive file changes. |
| `--yolo` | Skip approval prompts. |
| `--pass-session-id` | Pass the session ID into the system prompt. |
| `--ignore-user-config` | Ignore `~/.athena/config.yaml` and use built-in defaults. Credentials in `.env` are still loaded. Useful for isolated CI runs, reproducible bug reports, and third-party integrations. |
| `--ignore-rules` | Skip auto-injection of `AGENTS.md`, `SOUL.md`, `.cursorrules`, persistent memory, and preloaded skills. Combine with `--ignore-user-config` for a fully isolated run. |
| `--safe-mode` | Troubleshooting mode: disable ALL customizations — user config, rules/memory injection, plugins, shell hooks, and MCP servers (implies `--ignore-user-config` and `--ignore-rules`). Use to isolate whether a problem comes from your setup or from Athena itself. |
| `--source <tag>` | Session source tag for filtering (default: `cli`). Use `tool` for third-party integrations that should not appear in user session lists. |
| `--max-turns <N>` | Maximum tool-calling iterations per conversation turn (default: 500, or `agent.max_turns` in config). |

Examples:

```bash
athena
athena chat -q "Summarize the latest PRs"          # seeds an interactive session
athena chat --oneshot -q "Summarize the latest PRs"  # answer and exit
athena chat --provider openrouter --model anthropic/claude-sonnet-4.6
athena chat --toolsets web,terminal,skills
athena chat --quiet -q "Return only JSON"
athena chat --worktree -q "Review this repo and open a PR"
athena chat --ignore-user-config --ignore-rules -q "Repro without my personal setup"
athena chat --safe-mode -q "Is this bug mine or Athena'?"
```

#### Delegation in finite chat runs

When chat answers and exits (`-Q`, `chat --oneshot`, or a query with non-TTY
stdio), `delegate_task` waits for its children and returns their results to the
parent in the same turn. Batch children still run in parallel, subject to
`delegation.max_concurrent_children`. The parent can use those results in its
final response before the CLI exits.

- **Automatic joining:** no opt-in or background-mode override is needed.
  Interactive TTY chat and messaging sessions keep background delegation.
- **Existing safeguards:** delegation limits, timeouts, cancellation, and
  `approvals.single_query_mode` still apply. Joining does not auto-approve commands
  or guarantee successful child outcomes. Inspect results and verify artifacts.
- **Terminal completions:** this does not change background terminal notification
  behavior or the bounded `terminal.oneshot_completion_wait_seconds` exit wait.
  That setting is not a delegation timeout.

Delegation remains process-local. Interrupting or terminating the parent can
cancel unfinished children. Use a durable scheduler for work that must survive
the initiating process.

### `athena -z <prompt>` — scripted one-shot

For programmatic callers (shell scripts, CI, cron, parent processes piping in a prompt), `athena -z` is the purest one-shot entry point: **single prompt in, final response text out, nothing else on stdout or stderr.** No banner, no spinner, no tool previews, no `Session:` line — just the agent's final reply as plain text.

```bash
athena -z "What's the capital of France?"
# → Paris.

# Parent scripts can cleanly capture the response:
answer=$(athena -z "summarize this" < /path/to/file.txt)
```

Per-run overrides (no mutation to `~/.athena/config.yaml`):

| Flag | Equivalent env var | Purpose |
|---|---|---|
| `-m` / `--model <model>` | `ATHENA_INFERENCE_MODEL` | Override the model for this run |
| `--provider <provider>` | _(none)_ | Override the provider for this run |
| `--usage-file <path>` | _(none)_ | Write a JSON usage report after the run (see below) |

```bash
athena -z "…" --provider openrouter --model openai/gpt-5.5
# or:
ATHENA_INFERENCE_MODEL=anthropic/claude-sonnet-4.6 athena -z "…"
```

Same agent, same tools, same skills — just strips every interactive / cosmetic layer. If you need tool output in the transcript too, use `athena chat --oneshot -q` instead; `-z` is explicitly for "I only want the final answer".

#### `--usage-file` — JSON usage report for pipelines

`athena -z "…" --usage-file /path/report.json` writes a machine-readable usage report after the run: `estimated_cost_usd`, `input_tokens` / `output_tokens` / `cache_read_tokens` / `cache_write_tokens` / `reasoning_tokens` / `total_tokens`, `api_calls`, `model`, `provider`, `session_id`, `service_tier`, and `completed` / `failed` flags. The report is written **even when the run fails**, so batch pipelines can always account for spend. It has no effect outside `-z`/`--oneshot`, and a broken usage write never masks the run's own outcome.

```bash
athena -z "summarize this repo" --usage-file /tmp/usage.json
jq .estimated_cost_usd /tmp/usage.json
```

## `athena model`

Interactive provider + model selector. **This is the command for adding new providers, setting up API keys, and running OAuth flows.** Run it from your terminal — not from inside an active Athena chat session.

```bash
athena model
```

Use this when you want to:
- **add a new provider** (OpenRouter, Anthropic, Copilot, DeepSeek, custom, etc.)
- log into OAuth-backed providers (Anthropic, Copilot, Codex, Nous Portal)
- enter or update API keys
- pick from provider-specific model lists
- configure a custom/self-hosted endpoint
- save the new default into config

:::warning athena model vs /model — know the difference
**`athena model`** (run from your terminal, outside any Athena session) is the **full provider setup wizard**. It can add new providers, run OAuth flows, prompt for API keys, and configure endpoints.

**`/model`** (typed inside an active Athena chat session) can only **switch between providers and models you've already set up**. It cannot add new providers, run OAuth, or prompt for API keys.

**If you need to add a new provider:** Exit your Athena session first (`Ctrl+C` or `/quit`), then run `athena model` from your terminal prompt.
:::

### `/model` slash command (mid-session)

Switch between already-configured models without leaving a session:

```
/model                              # Show current model and available options
/model claude-sonnet-4              # Switch model (auto-detects provider)
/model zai:glm-5                    # Switch provider and model
/model custom:qwen-2.5              # Use model on your custom endpoint
/model custom                       # Auto-detect model from custom endpoint
/model custom:local:qwen-2.5        # Use a named custom provider
/model openrouter:anthropic/claude-sonnet-4  # Switch back to cloud
```

By default, `/model` changes apply **to the current session only**. Add `--global` to persist the change to `config.yaml` (or set `model.persist_switch_by_default: true` to make every switch persist):

```
/model claude-sonnet-4 --global     # Switch and save as new default
```

:::info What if I only see OpenRouter models?
If you've only configured OpenRouter, `/model` will only show OpenRouter models. To add another provider (Anthropic, DeepSeek, Copilot, etc.), exit your session and run `athena model` from the terminal.
:::

On a `--global` switch, provider and base URL changes are persisted to `config.yaml` alongside the model. When switching away from a custom endpoint, the stale base URL is cleared to prevent it leaking into other providers.

## `athena gateway`

```bash
athena gateway <subcommand>
```

Subcommands:

| Subcommand | Description |
|------------|-------------|
| `run` | Run the gateway in the foreground. Recommended for WSL, Docker, and Termux. |
| `start` | Start the installed systemd/launchd background service. |
| `stop` | Stop the service (or foreground process). |
| `restart` | Restart the service. |
| `status` | Show service status. |
| `list` | List **all profiles** and whether each profile's gateway is currently running (with PID where available). Handy when you run multiple profiles side-by-side and want a single overview. |
| `install` | Install as a systemd (Linux) or launchd (macOS) background service. |
| `uninstall` | Remove the installed service. |
| `setup` | Interactive messaging-platform setup. |
| `migrate-legacy` | Remove legacy `athena.service` units left over from pre-rename installs. Profile units (`athena-gateway-<profile>.service`) and unrelated services are never touched. Flags: `--dry-run`, `-y`/`--yes`. |
| `enroll` | Experimental: enroll this gateway with a relay connector and save relay credentials for connector-backed platforms. See [Athena Relay](/user-guide/messaging/relay). |

Options:

| Option | Description |
|--------|-------------|
| `--all` | On `start` / `restart` / `stop`: act on **every profile's** gateway, not just the active `ATHENA_HOME`. Useful if you run multiple profiles side-by-side and want to restart them all after `athena update`. |
| `--no-supervise` | On `run`: inside the s6-overlay Docker image, opt out of auto-supervision and use pre-s6 foreground semantics — gateway runs as the container's main process with no auto-restart. No-op outside the s6 image. Equivalent to setting `ATHENA_GATEWAY_NO_SUPERVISE=1`. |
| `--external-supervisor` | On `run`: declare that a wrapper-provided process manager owns the foreground gateway. Use this when `sudo`, `env -i`, or another wrapper strips launchd/systemd's native environment marker. In-chat restarts and updates exit back to that manager instead of spawning a detached replacement. |

`--external-supervisor` is a restart-policy contract: an in-chat restart or
service-restart update exits with status `75`, so the wrapper's supervisor must
relaunch the gateway after that nonzero exit. For systemd, use
`Restart=on-failure` or `Restart=always` and do not include `75` in
`RestartPreventExitStatus`; for launchd, configure `KeepAlive` to relaunch after
unsuccessful exits. Without that policy, a requested restart leaves the gateway
stopped.

`athena gateway enroll` accepts `--token`, `--connector-url`, `--gateway-id`, and `--wake-url`. It exchanges the enrollment token with the connector and writes the resulting `GATEWAY_RELAY_ID`, `GATEWAY_RELAY_SECRET`, `GATEWAY_RELAY_DELIVERY_KEY`, optional `GATEWAY_RELAY_URL`, and (when `--wake-url` is given) `GATEWAY_RELAY_WAKE_URL` values to the active profile's `.env`.

:::tip WSL users
Use `athena gateway run` instead of `athena gateway start` — WSL's systemd support is unreliable. Wrap it in tmux for persistence: `tmux new -s athena 'athena gateway run'`. See [WSL FAQ](/reference/faq#wsl-gateway-keeps-disconnecting-or-athena-gateway-start-fails) for details.
:::

## `athena lsp`

```bash
athena lsp <subcommand>
```

Manage the Language Server Protocol integration. LSP runs real
language servers (pyright, gopls, rust-analyzer, …) in the
background and feeds their diagnostics into the post-write check
used by `write_file` and `patch`. Gated on git workspace detection
— LSP only runs when the cwd or edited file is inside a git
worktree.

Subcommands:

| Subcommand | Description |
|------------|-------------|
| `status` | Show service state, configured servers, install status. |
| `list` | Print the registry of supported servers. Pass `--installed-only` to skip missing ones. |
| `install <id>` | Eagerly install one server's binary. |
| `install-all` | Install every server with a known auto-install recipe. |
| `restart` | Tear down running clients so the next edit re-spawns. |
| `which <id>` | Print the resolved binary path for one server. |

See [LSP — Semantic Diagnostics](/user-guide/features/lsp) for
the full guide, supported languages, and configuration knobs.

## `athena setup`

```bash
athena setup [model|tts|terminal|gateway|tools|agent] [--non-interactive] [--reset] [--quick] [--reconfigure] [--portal]
```

**Easiest path:** `athena setup --portal` — OAuth into Nous Portal and opt into the [Tool Gateway](../user-guide/features/tool-gateway.md) in one shot.

**First run:** launches the first-time wizard.

**Returning user (already configured):** drops straight into the full reconfigure wizard — every prompt shows your current value as its default, press Enter to keep or type a new value. No menu.

Jump into one section instead of the full wizard:

| Section | Description |
|---------|-------------|
| `model` | Provider and model setup. |
| `terminal` | Terminal backend and sandbox setup. |
| `gateway` | Messaging platform setup. |
| `tools` | Enable/disable tools per platform. |
| `agent` | Agent behavior settings. |

Options:

| Option | Description |
|--------|-------------|
| `--quick` | On returning-user runs: only prompt for items that are missing or unset. Skip items you already have configured. |
| `--non-interactive` | Use defaults / environment values without prompts. |
| `--reset` | Reset configuration to defaults before setup. |
| `--reconfigure` | Backwards-compat alias — bare `athena setup` on an existing install now does this by default. |
| `--portal` | One-shot Nous Portal setup: log in via OAuth, set Nous as the inference provider, and opt into the [Tool Gateway](../user-guide/features/tool-gateway.md). Skips the rest of the wizard. |

## `athena portal`

```bash
athena portal [status|open|tools]
```

Inspect Nous Portal auth, Tool Gateway routing, and reach the subscription page. Subcommand-less invocation runs `status`.

| Subcommand | Description |
|------------|-------------|
| `status` (default) | Portal auth state + per-tool Tool Gateway routing summary. Also shown when no subcommand is given. |
| `open` | Open `portal.nousresearch.com/manage-subscription` in your default browser. |
| `tools` | List every Tool Gateway partner (Firecrawl, FAL, OpenAI TTS, Browser Use, Modal) and which are routed via Nous. |

For configuration of the gateway itself, see [Tool Gateway](../user-guide/features/tool-gateway.md). For the one-shot setup path, see `athena setup --portal` above.

## `athena whatsapp`

```bash
athena whatsapp
```

Runs the WhatsApp pairing/setup flow, including mode selection and QR-code pairing.

## `athena slack`

```bash
athena slack manifest              # print manifest to stdout
athena slack manifest --write      # write to ~/.athena/slack-manifest.json
athena slack manifest --long-description-file AGENTS.md --write
athena slack manifest --slashes-only  # just the features.slash_commands array
```

Generates a Slack app manifest that registers every gateway command in
`COMMAND_REGISTRY` (`/btw`, `/stop`, `/model`, …) as a first-class
Slack slash command — matching Discord and Telegram parity. Paste the
output into your Slack app config at
[https://api.slack.com/apps](https://api.slack.com/apps) → your app →
**Features → App Manifest → Edit**, then **Save**. Slack prompts for
reinstall if scopes or slash commands changed.

| Flag | Default | Purpose |
|------|---------|---------|
| `--write [PATH]` | stdout | Write to a file instead of stdout. Bare `--write` writes `$ATHENA_HOME/slack-manifest.json`. |
| `--name NAME` | `Athena` | Bot display name in Slack. |
| `--description DESC` | default blurb | Bot description shown in the Slack app directory. |
| `--long-description TEXT` | unset | Set `display_information.long_description` inline (175–4,000 characters). Incompatible with `--slashes-only`. |
| `--long-description-file PATH` | unset | Read the long description from a UTF-8 text file, preserving its contents exactly. Mutually exclusive with `--long-description` and incompatible with `--slashes-only`. |
| `--slashes-only` | off | Emit only `features.slash_commands` for merging into a manually-maintained manifest. |

Run `athena slack manifest --write` again after `athena update` to pick
up any new commands.


## `athena send`

```bash
athena send --to <target> "message text"
athena send --to <target> --file <path>
echo "message" | athena send --to <target>
athena send --list [platform]
```

Send a one-shot message to a configured messaging platform without spinning up an agent or gateway loop. Reuses the gateway's already-configured credentials (`~/.athena/.env` + `~/.athena/config.yaml`) so ops scripts, cron jobs, CI hooks, and monitoring daemons can post status updates without reimplementing each platform's REST client.

For bot-token platforms (Telegram, Discord, Slack, Signal, SMS, WhatsApp-CloudAPI) no running gateway is required — `athena send` talks directly to the platform's REST endpoint. Plugin platforms that need a persistent adapter still require a live gateway.

| Option | Description |
|--------|-------------|
| `-t`, `--to <TARGET>` | Delivery target. Formats: `platform` (uses home channel), `platform:chat_id`, `platform:chat_id:thread_id`, or `platform:#channel-name`. Examples: `telegram`, `telegram:-1001234567890`, `discord:#ops`, `slack:C0123ABCD`, `signal:+15551234567`. |
| `-f`, `--file <PATH>` | Read the message body from `PATH` (text files only — logs, reports, markdown). Pass `-` to force reading from stdin. To send an image or other binary file, use `MEDIA:<path>` (see below). |
| `-s`, `--subject <LINE>` | Prepend a subject/header line before the message body. |
| `-l`, `--list [platform]` | List configured targets across all platforms (or only the given platform). |
| `-q`, `--quiet` | Suppress stdout on success — useful in scripts (rely on exit code only). |
| `--json` | Emit raw JSON result instead of human-readable output. |

If neither a positional `message` argument nor `--file` is provided, `athena send` reads from stdin when it is not a TTY. Exit codes: `0` on success, `1` on delivery/backend failure, `2` on usage errors.

### Sending images and other media

`--file` is for *text* bodies only. To deliver an image, document, video, or audio file as a native platform attachment, reference it inside the message text with the `MEDIA:<local_path>` directive:

```bash
athena send --to telegram "MEDIA:/tmp/screenshot.png"
athena send --to telegram "Build chart for today MEDIA:/tmp/chart.png"   # with caption
athena send --to discord:#ops "MEDIA:/tmp/report.pdf"
```

By default, image files are sent as photos (platforms like Telegram recompress these). Add `[[as_document]]` to the message to deliver them as uncompressed file attachments instead:

```bash
athena send --to telegram "[[as_document]] MEDIA:/tmp/screenshot.png"
```

Examples:

```bash
athena send --to telegram "deploy finished"
echo "RAM 92%" | athena send --to telegram:-1001234567890
athena send --to discord:#ops --file /tmp/report.md
athena send --to slack:#eng --subject "[CI]" --file build.log
athena send --list                  # all platforms
athena send --list telegram         # filter by platform
```



## `athena peer`

```bash
athena peer add <name> --url http://host:port --key <API_SERVER_KEY>
athena peer list
athena peer dm <peer>[/<agent>] "message"
athena peer run <peer>[/<agent>] --idempotency-key <key> "message"
athena peer status <peer>[/<agent>] <run_id>
athena peer stop <peer>[/<agent>] <run_id>
athena peer remove <name>
```

Bot-to-bot DMs across machines. Register another Athena gateway (any machine
running the `api_server` platform) as a *peer*, then message its agents:
`athena peer dm` resolves the remote agent's canonical **Bot Chat** session
over the peer's API server, runs one agent turn there, and prints the reply
on stdout — the cross-machine twin of the local
`athena -p <bot> chat --in ~ -c "Bot Chat" …` bot-messaging command.

`<peer>` alone targets the peer gateway's main agent;
`<peer>/<agent>` targets a named profile on a multiplexed peer (routed via
its `/p/<profile>/` mirror).

| Subcommand | Description |
|--------|-------------|
| `add <name> --url <URL> [--key <KEY>] [--note TEXT]` | Register or update a peer. The URL goes to `config.yaml` (`bot_peers`); the key is stored as `ATHENA_PEER_<NAME>_KEY` in `~/.athena/.env`. |
| `list` | List peers and whether each has a key configured. |
| `dm <peer>[/<agent>] [message]` | Message the peer agent's canonical Bot Chat and print the reply (`--json` for machine-readable output; message falls back to stdin). |
| `run <peer>[/<agent>] [message]` | Start a long canonical Bot Chat turn asynchronously and return its `run_id`, session ID, and idempotency key (`--json` supported). Reuse `--idempotency-key` when retrying the same request. |
| `status <peer>[/<agent>] <run_id>` | Poll an asynchronous peer run and print its final output when complete (`--json` supported). |
| `stop <peer>[/<agent>] <run_id>` | Stop the exact asynchronous peer run without targeting another turn (`--json` supported). |
| `remove <name>` | Remove a peer from the registry (the `.env` key entry is left in place). |

When at least one peer is registered, the Bot Mode messaging protocol
(`agent.bot_mode_protocol`) taught to every canonical Bot Chat automatically
includes the peer roster and the `athena peer dm` pattern, so agents discover
cross-machine teammates without SOUL edits. See
[Bot Mode](../user-guide/bot-mode.md).

Exit codes: `0` on success, `1` on delivery/peer failure, `2` on usage errors.

## `athena secrets`

```bash
athena secrets bitwarden <subcommand>
athena secrets bw <subcommand>          # short alias
```

Pull API keys from an external secret manager at process startup instead of storing them in `~/.athena/.env`. Currently supports **Bitwarden Secrets Manager**. See the full guide: [Bitwarden integration](../user-guide/secrets/bitwarden.md).

`bitwarden` (alias `bw`) subcommands:

| Subcommand | Description |
|------------|-------------|
| `setup` | Interactive wizard: install the pinned `bws` binary, store an access token, and pick a project. Accepts `--project-id`, `--access-token`, and `--server-url` for non-interactive use. |
| `status` | Show current config, binary path/version, and token validation status. |
| `token` | Rotate the access token: validates the new token against Bitwarden before storing it in `.env` (a rejected token changes nothing). Accepts `--access-token` for non-interactive use and `--no-verify` to skip the probe. |
| `sync` | Fetch secrets now and report what changed. Add `--apply` to actually export the secrets into the current shell's environment (default is dry-run). |
| `install` | Download and verify the pinned `bws` binary. `--force` re-downloads even if a managed copy already exists. |
| `disable` | Turn off the Bitwarden integration. |


## `athena migrate`

```bash
athena migrate <type>
```

Diagnose and (optionally) rewrite the active `config.yaml` to replace references to retired models or deprecated settings. A timestamped backup of the original `config.yaml` is taken before any rewrite (skip with `--no-backup`).

| Subcommand | Description |
|------------|-------------|
| `xai` | Scan `config.yaml` for references to xAI models scheduled for retirement on May 15, 2026 and (with `--apply`) rewrite them in-place to the official replacements per the xAI migration guide. Defaults to dry-run. |

Common flags for migration subcommands:

| Flag | Description |
|------|-------------|
| `--apply` | Rewrite `config.yaml` in-place (default: dry-run, no writes). |
| `--no-backup` | Skip the timestamped backup of `config.yaml` when applying. |

> Not to be confused with `athena claw migrate` (one-shot import of OpenClaw configuration into Athena) — `athena migrate` is the top-level config-rewrite command.


## `athena proxy`

```bash
athena proxy <subcommand>
```

Run a local OpenAI-compatible HTTP server that forwards requests to an OAuth-authenticated upstream provider (e.g. Nous Portal, xAI). External apps can point at the proxy with any bearer token; the proxy attaches your real OAuth credentials on the way out. See [Subscription Proxy](../user-guide/features/subscription-proxy.md) for the full guide.

| Subcommand | Description |
|------------|-------------|
| `start` | Run the proxy in the foreground. Flags: `--provider <nous\|xai>` (default `nous`), `--host <addr>` (default `127.0.0.1`; use `0.0.0.0` to expose on LAN), `--port <int>` (default `8645`). |
| `status` | Show which proxy upstreams are ready (credentials present, OAuth valid). |
| `providers` | List available proxy upstream providers. |


## `athena security`

```bash
athena security <subcommand>
```

On-demand vulnerability scan against [OSV.dev](https://osv.dev). Covers the Athena venv (installed PyPI distributions), Python dependencies declared by plugins under `~/.athena/plugins/`, and pinned `npx`/`uvx` MCP servers in `config.yaml`. Does NOT scan globally-installed packages or editor/browser extensions.

| Subcommand | Description |
|------------|-------------|
| `audit` | Run a one-shot supply-chain audit. |

`audit` flags:

| Flag | Default | Description |
|------|---------|-------------|
| `--json` | off | Emit machine-readable JSON instead of human-readable text. |
| `--fail-on <level>` | `critical` | Exit non-zero when any finding meets this severity (`low`, `moderate`, `high`, `critical`). |
| `--skip-venv` | off | Skip scanning the Athena Python venv. |
| `--skip-plugins` | off | Skip scanning plugin requirements files. |
| `--skip-mcp` | off | Skip scanning pinned MCP servers in `config.yaml`. |


## `athena login` / `athena logout` *(Deprecated)*

:::caution
`athena login` has been removed. Use `athena auth` to manage OAuth credentials, `athena model` to select a provider, or `athena setup` for full interactive setup.
:::

## `athena auth`

Manage credential pools for same-provider key rotation. See [Credential Pools](/user-guide/features/credential-pools) for full documentation.

```bash
athena auth                                              # Interactive wizard
athena auth list                                         # Show all pools
athena auth list openrouter                              # Show specific provider
athena auth add openrouter --api-key sk-or-v1-xxx        # Add API key
athena auth add anthropic --type oauth                   # Add OAuth credential
athena auth add openai-codex --type oauth --priority 0   # Add an account and try it first
athena auth remove openrouter 2                          # Remove by index
athena auth priority openrouter backup-key 0             # Move a credential to the front of fill_first order
athena auth reset openrouter                             # Clear cooldowns
athena auth reset openrouter 2                           # Clear the cooldown on one credential
athena auth refresh openai-codex work                    # Refresh one OAuth credential and clear its cooldown
athena auth status anthropic                             # Show auth status for a provider
athena auth logout anthropic                             # Log out and clear stored auth state
athena auth spotify                                      # Authenticate Athena with Spotify via PKCE
```

Subcommands: `add`, `list`, `remove`, `reset`, `priority`, `refresh`, `status`, `logout`, `spotify`. When called with no subcommand, launches the interactive management wizard.

## `athena status`

```bash
athena status [--all] [--deep]
```

| Option | Description |
|--------|-------------|
| `--all` | Show all details in a shareable redacted format. |
| `--deep` | Run deeper checks that may take longer. |

## `athena cron`

```bash
athena cron <list|create|edit|pause|resume|run|remove|status|runs|incidents|doctor|tick>
```

| Subcommand | Description |
|------------|-------------|
| `list` | Show scheduled jobs. |
| `create` / `add` | Create a scheduled job from a prompt, optionally attaching one or more skills via repeated `--skill`. Supports a per-job reasoning pin via `--reasoning-effort <none\|minimal\|low\|medium\|high\|xhigh\|max\|ultra>`. |
| `edit` | Update a job's schedule, prompt, name, delivery, repeat count, or attached skills. Supports `--clear-skills`, `--add-skill`, and `--remove-skill`, plus `--reasoning-effort` (empty string clears the pin). |
| `pause` | Pause a job without deleting it. |
| `resume` | Resume a paused job and compute its next future run. |
| `run` | Trigger a job on the next scheduler tick. |
| `remove` | Delete a scheduled job. |
| `status` | Check whether the cron scheduler is running. |
| `doctor` | Read-only fleet health check: failed runs, failed deliveries, overdue/missing `next_run_at`, missing scripts or workdirs. Exits non-zero when issues are found. |
| `tick` | Run due jobs once and exit. |

The cron **trigger** is pluggable via the `cron.provider` config key. Empty
(the default) uses the built-in in-process ticker. Set it to `chronos` (the
NAS-managed provider for scale-to-zero hosted gateways) — configured via the
`cron.chronos.*` keys (`portal_url`, `callback_url`, `expected_audience`,
`nas_jwks_url`) — or name a custom provider under `plugins/cron/<name>/` or
`$ATHENA_HOME/plugins/<name>/`. An unknown or unavailable provider falls back to
the built-in, so cron is never left without a trigger. See the
[cron internals](../developer-guide/cron-internals.md#gateway-integration) doc.

## `athena kanban`

```bash
athena kanban [--board <slug>] <action> [options]
```

Multi-profile, multi-project collaboration board. Each install can host many boards (one per project, repo, or domain); each board is a standalone queue with its own SQLite DB and dispatcher scope. New installs start with one board called `default`, whose DB is `~/.athena/kanban.db` for back-compat; additional boards live at `~/.athena/kanban/boards/<slug>/kanban.db`. The gateway-embedded dispatcher sweeps every board per tick.

**Global flags (apply to every action below):**

| Flag | Purpose |
|------|---------|
| `--board <slug>` | Operate on a specific board. Defaults to the current board (set via `athena kanban boards switch`, the `ATHENA_KANBAN_BOARD` env var, or `default`). |

**This is the human / scripting surface.** Agent workers spawned by the dispatcher drive the board through a dedicated `kanban_*` [toolset](/user-guide/features/kanban#how-workers-interact-with-the-board) (`kanban_show`, `kanban_complete`, `kanban_request_review`, `kanban_request_changes`, `kanban_block`, `kanban_create`, `kanban_link`, `kanban_comment`, `kanban_heartbeat`; orchestrator profiles also get `kanban_list` and `kanban_unblock`) instead of shelling to `athena kanban`. Workers have `ATHENA_KANBAN_BOARD` pinned in their env so they physically cannot see other boards.

| Action | Purpose |
|--------|---------|
| `init` | Create `kanban.db` if missing. Idempotent. |
| `boards list` / `boards ls` | List all boards with task counts. `--json`, `--all` (include archived). |
| `boards create <slug>` | Create a new board. Flags: `--name`, `--description`, `--icon`, `--color`, `--switch` (make active). Slug is kebab-case, auto-downcased. |
| `boards switch <slug>` / `boards use` | Persist `<slug>` as the active board (writes `~/.athena/kanban/current`). |
| `boards show` / `boards current` | Print the currently-active board's name, DB path, and task counts. |
| `boards rename <slug> "<name>"` | Change a board's display name. Slug is immutable. |
| `boards rm <slug>` | Archive (default) or hard-delete a board. `--delete` skips the archive step. Archived boards move to `boards/_archived/<slug>-<ts>/`. Refused for `default`. |
| `create "<title>"` | Create a new task on the active board. Flags: `--body`, `--assignee`, `--parent` (repeatable), `--workspace scratch\|worktree\|dir:<path>`, `--tenant`, `--priority`, `--triage`, `--idempotency-key`, `--max-runtime`, `--max-retries`, `--skill` (repeatable). |
| `list` / `ls` | List tasks on the active board. Filter with `--mine`, `--assignee`, `--status`, `--tenant`, `--archived`, `--json`. |
| `show <id>` | Show a task with comments and events. `--json` for machine output. |
| `assign <id> <profile>` | Assign or reassign. Use `none` to unassign. Refused while task is running. |
| `link <parent> <child>` | Add a dependency. Cycle-detected. Both tasks must be on the same board. |
| `unlink <parent> <child>` | Remove a dependency. |
| `claim <id>` | Atomically claim a ready task. Prints resolved workspace path. |
| `comment <id> "<text>"` | Append a comment. The next worker that claims the task reads it as part of its `kanban_show()` response. |
| `complete <id>` | Mark task done. Flags: `--result`, `--summary`, `--metadata`. |
| `block <id> "<reason>"` | Mark task blocked for human input. Also appends the reason as a comment. |
| `request-review <id>` | Move a task to `review` with a reviewer handoff — NOT a block. Flags: `--summary`, `--metadata`, `--reviewer` (reassigns before review dispatch). |
| `request-changes <id> <reason>` | Reviewer verdict for an active review run: close the review attempt and route the task back to its original implementer. |
| `reopen-review <id>...` | Send review task(s) back for changes (`review` → ready/todo). Flag: `--reason` (appended as a comment). |
| `schedule <id> "<reason>"` | Park time-delay/follow-up work in `scheduled` so it is not shown as a human blocker. |
| `unblock <id>` | Restore a blocked task to its source phase (`review` or `ready`), or `todo` while dependencies remain open. |
| `archive <id>` | Hide from default list. `gc` will remove scratch workspaces. |
| `tail <id>` | Follow a task's event stream. |
| `dispatch` | One dispatcher pass on the active board. Flags: `--dry-run`, `--max N`, `--failure-limit N`, `--json`. |
| `context <id>` | Print the full context a worker would see (title + body + parent results + comments). |
| `specify <id>` / `specify --all` | Flesh out a triage-column task into a concrete spec (title + body with goal, approach, acceptance criteria) via the auxiliary LLM, then promote it to `todo`. Flags: `--tenant` (scope `--all` to one tenant), `--author`, `--json`. Configure the model under `auxiliary.triage_specifier` in `config.yaml`. |
| `decompose <id>` / `decompose --all` | Fan a triage-column task out into a graph of child tasks routed to specialist profiles by description. Falls back to specify-style single-task promotion when the LLM decides the task doesn't benefit from fan-out. Same flags as `specify`. Configure the decomposer model under `auxiliary.kanban_decomposer` in `config.yaml`; `kanban.orchestrator_profile` only controls who owns the root/orchestration task after fan-out. Also runs automatically every dispatcher tick when `kanban.auto_decompose: true` (the default). See [Auto vs Manual orchestration](/user-guide/features/kanban#auto-vs-manual-orchestration). |
| `gc` | Remove scratch workspaces for archived tasks. |

Examples:

```bash
# Create a second board and put a task on it without switching away.
athena kanban boards create atm10-server --name "ATM10 Server" --icon 🎮
athena kanban --board atm10-server create "Restart server" --assignee ops

# Switch the active board for subsequent calls.
athena kanban boards switch atm10-server
athena kanban list                  # shows atm10-server tasks

# Archive a board (recoverable) or hard-delete it.
athena kanban boards rm atm10-server
athena kanban boards rm atm10-server --delete
```

Board resolution order (highest precedence first): `--board <slug>` flag → `ATHENA_KANBAN_BOARD` env var → `~/.athena/kanban/current` file → `default`.

All actions are also available as a slash command in the gateway (`/kanban …`), with the same argument surface — including `boards` subcommands and the `--board` flag.

For the full design — comparison with Cline Kanban / Paperclip / NanoClaw / Gemini Enterprise, eight collaboration patterns, four user stories, concurrency correctness proof — see `docs/athena-kanban-v1-spec.pdf` in the repository or the [Kanban user guide](/user-guide/features/kanban).

## `athena egress`

Outbound credential-injection firewall for remote terminal sandboxes. Wraps the [iron-proxy](https://github.com/ironsh/iron-proxy) daemon — a TLS-intercepting proxy that swaps opaque proxy tokens for real upstream API credentials at the network boundary, so sandboxes never hold real keys. Disabled by default; see the full [Egress proxy](../user-guide/egress/iron-proxy.md) page for setup + architecture.

```bash
athena egress install                  # download the pinned iron-proxy binary
athena egress install --force          # re-download even if already installed

athena egress setup                    # interactive wizard: CA, mappings, config
athena egress setup --tunnel-port N    # override the tunnel listener port (default 9090)
athena egress setup --from-bitwarden   # use Bitwarden Secrets Manager as credential source
athena egress setup --no-bitwarden     # explicitly switch back to env-based credentials
athena egress setup --rotate-tokens    # mint fresh proxy tokens (default preserves existing)

athena egress start                    # spawn the managed proxy daemon
athena egress stop                     # SIGTERM (then SIGKILL after 5s grace)
athena egress restart                  # stop (if running) then start — needed for secret changes
athena egress reload                   # hot-reload the ruleset in-place (no restart, no dropped
                                       #   connections) via the loopback management API

athena egress status                   # binary + config + pid + listening + mappings
athena egress status --show-tokens     # print proxy tokens in full (default: redacted)

athena egress disable                  # flip proxy.enabled = false (does not stop a running proxy)
athena egress config                   # print the path to proxy.yaml for inspection
```

### Common flows

```bash
# First-time setup
export OPENROUTER_API_KEY=…
athena egress setup && athena egress start
athena config set terminal.backend docker   # if not already

# Switching credential source after the fact
athena egress setup --from-bitwarden       # env → bitwarden
athena egress setup --no-bitwarden         # bitwarden → env
# (just `setup` without either flag preserves the existing mode)

# Rotating all tokens (e.g. after a suspected token leak)
athena egress setup --rotate-tokens    # setup offers to restart the running daemon for you
# (running sandboxes still hold old tokens; restart them too)

# Adding a new upstream
# Edit ~/.athena/config.yaml proxy.extra_allowed_hosts: [api.example.com]
athena egress setup
athena egress restart                  # one-command apply (stop + start)
```

### Diagnostic shortcuts

```bash
athena egress status                     # current state in one view
cat ~/.athena/proxy/proxy.yaml           # the rendered iron-proxy config
tail -20 ~/.athena/proxy/iron-proxy.log  # daemon-level diagnostics
tail -f ~/.athena/proxy/iron-proxy.log | jq  # daemon + per-request log (line-delimited JSON; v0.39 combines both streams)
```

Common failure modes + recovery are covered in [Egress proxy → Troubleshooting](../user-guide/egress/iron-proxy.md#troubleshooting).

## `athena project`

```bash
athena project <create|list|show|add-folder|remove-folder|rename|set-primary|use|archive|restore|bind-board>
```

Projects are human-named workspaces that can span multiple folders / repos. They anchor desktop session grouping and, when bound to a kanban board, give tasks a deterministic worktree + branch convention. State is per-profile.

| Subcommand | Description |
|------------|-------------|
| `create` | Create a new project. |
| `list` (alias `ls`) | List projects. |
| `show` | Show a project's details. |
| `add-folder` | Add a folder / repo to a project. |
| `remove-folder` | Remove a folder from a project. |
| `rename` | Rename a project. |
| `set-primary` | Set the primary folder. |
| `use` | Set the active project. |
| `archive` | Archive a project (recoverable). |
| `restore` | Restore an archived project. |
| `bind-board` | Bind a kanban board to this project. |

## `athena webhook`

```bash
athena webhook <subscribe|list|remove|test>
```

Manage dynamic webhook subscriptions for event-driven agent activation. Requires the webhook platform to be enabled in config — if not configured, prints setup instructions.

| Subcommand | Description |
|------------|-------------|
| `subscribe` / `add` | Create a webhook route. Returns the URL and HMAC secret to configure on your service. |
| `list` / `ls` | Show all agent-created subscriptions. |
| `remove` / `rm` | Delete a dynamic subscription. Static routes from config.yaml are not affected. |
| `test` | Send a test POST to verify a subscription is working. |

### `athena webhook subscribe`

```bash
athena webhook subscribe <name> [options]
```

| Option | Description |
|--------|-------------|
| `--prompt` | Prompt template with `{dot.notation}` payload references. |
| `--events` | Comma-separated event types to accept (e.g. `issues,pull_request`). Empty = all. |
| `--description` | Human-readable description. |
| `--skills` | Comma-separated skill names to load for the agent run. |
| `--deliver` | Delivery target: `log` (default), `telegram`, `discord`, `slack`, `github_comment`. |
| `--deliver-chat-id` | Target chat/channel ID for cross-platform delivery. |
| `--secret` | Custom HMAC secret. Auto-generated if omitted. |
| `--deliver-only` | Skip the agent — deliver the rendered `--prompt` as the literal message. Zero LLM cost, sub-second delivery. Requires `--deliver` to be a real target (not `log`). |
| `--script` | Filter/transform script under `~/.athena/scripts/`. The webhook payload is passed as JSON on stdin; JSON stdout replaces the payload, and empty stdout, `[SILENT]`, or a nonzero exit code ignores the webhook. See [Script Filters and Transforms](../user-guide/messaging/webhooks.md#script-filters-and-transforms). |

Subscriptions persist to `~/.athena/webhook_subscriptions.json` and are hot-reloaded by the webhook adapter without a gateway restart.

## `athena doctor`

```bash
athena doctor [--fix]
```

| Option | Description |
|--------|-------------|
| `--fix` | Attempt automatic repairs where possible. |

## `athena dump`

```bash
athena dump [--show-keys]
```

Outputs a compact, plain-text summary of your entire Athena setup. Designed to be copy-pasted into Discord, GitHub issues, or Telegram when asking for support — no ANSI colors, no special formatting, just data.

| Option | Description |
|--------|-------------|
| `--show-keys` | Show redacted API key prefixes (first and last 4 characters) instead of just `set`/`not set`. |

### What it includes

| Section | Details |
|---------|---------|
| **Header** | Athena version, release date, git commit hash |
| **Environment** | OS, Python version, OpenAI SDK version |
| **Identity** | Active profile name, ATHENA_HOME path |
| **Model** | Configured default model and provider |
| **Terminal** | Backend type (local, docker, ssh, etc.) |
| **API keys** | Presence check for all 22 provider/tool API keys |
| **Features** | Enabled toolsets, MCP server count, memory provider |
| **Services** | Gateway status, configured messaging platforms |
| **Workload** | Cron job counts, installed skill count |
| **Config overrides** | Any config values that differ from defaults |

### Example output

```
--- athena dump ---
version:          0.8.0 (2026.4.8) [af4abd2f]
os:               Linux 6.14.0-37-generic x86_64
python:           3.11.14
openai_sdk:       2.24.0
profile:          default
athena_home:      ~/.athena
model:            anthropic/claude-opus-4.6
provider:         openrouter
terminal:         local

api_keys:
  openrouter           set
  openai               not set
  anthropic            set
  nous                 not set
  firecrawl            set
  ...

features:
  toolsets:           all
  mcp_servers:        0
  memory_provider:    built-in
  gateway:            running (systemd)
  platforms:          telegram, discord
  cron_jobs:          3 active / 5 total
  skills:             42

config_overrides:
  agent.max_turns: 250
  compression.threshold: 0.85
  display.streaming: True
--- end dump ---
```

### When to use

- Reporting a bug on GitHub — paste the dump into your issue
- Asking for help in Discord — share it in a code block
- Comparing your setup to someone else's
- Quick sanity check when something isn't working

:::tip
`athena dump` is specifically designed for sharing. For interactive diagnostics, use `athena doctor`. For a visual overview, use `athena status`.
:::

## `athena debug`

```bash
athena debug share [options]
```

Upload a debug report (system info + recent logs) to a paste service and get a shareable URL. Useful for quick support requests — includes everything a helper needs to diagnose your issue.

| Option | Description |
|--------|-------------|
| `--lines <N>` | Number of log lines to include per log file (default: 200). |
| `--expire <days>` | Paste expiry in days (default: 7). |
| `--nous` | Upload to Nous-internal diagnostics storage instead of a public paste service. Use this when Nous support asks for a private diagnostic bundle. |
| `--local` | Print the report locally instead of uploading. |
| `--no-redact` | Disable upload-time secret redaction. By default, uploads are redacted. |

The report includes system info (OS, Python version, Athena version), recent agent, gateway, GUI/dashboard, and desktop logs (512 KB limit per file), and redacted API key status. By default, uploads are redacted so secrets are not included.

Default uploads use public paste services tried in order: paste.rs, dpaste.com. `--nous` uploads the same debug bundle to private Nous diagnostics storage instead; the returned viewer link is for the Nous team and auto-deletes after 14 days.

### Examples

```bash
athena debug share              # Upload debug report, print URL
athena debug share --lines 500  # Include more log lines
athena debug share --expire 30  # Keep paste for 30 days
athena debug share --nous       # Upload a private diagnostics bundle for Nous support
athena debug share --local      # Print report to terminal (no upload)
```

## `athena backup`

```bash
athena backup [options]
```

Create a zip archive of your Athena configuration, skills, sessions, and data. The backup excludes the athena-agent codebase itself, and it does not nest earlier backup artifacts (`backups/`, `state-snapshots/`) — each of those already contains its own copy of `state.db`.

| Option | Description |
|--------|-------------|
| `-o`, `--output <path>` | Output path for the zip file (default: `~/athena-backup-<timestamp>.zip`). |
| `-q`, `--quick` | Quick snapshot: only critical state files (config.yaml, state.db, .env, auth, cron jobs). Much faster than a full backup. |
| `-l`, `--label <name>` | Label for the snapshot (only used with `--quick`). |
| `-k`, `--keep <N>` | After a full backup, delete older `athena-backup-*.zip` files in the output directory beyond the newest N (default 3; `0` keeps everything). Custom-named zips are never touched. |

The backup uses SQLite's `backup()` API for safe copying, so it works correctly even when Athena is running (WAL-mode safe).

**What's excluded from the zip:**

- `*.db-wal`, `*.db-shm`, `*.db-journal` — SQLite's WAL / shared-memory / journal sidecars. The `*.db` file already got a consistent snapshot via `sqlite3.backup()`; shipping the live sidecars alongside it would let a restore see a half-committed state.
- `checkpoints/` — per-session trajectory caches. Hash-keyed and regenerated per session; wouldn't port cleanly to another install anyway.
- The `athena-agent` code itself (this is a user-data backup, not a repo snapshot).

### Examples

```bash
athena backup                           # Full backup to ~/athena-backup-*.zip
athena backup -o /tmp/athena.zip        # Full backup to specific path
athena backup --quick                   # Quick state-only snapshot
athena backup --quick --label "pre-upgrade"  # Quick snapshot with label
```

## `athena checkpoints`

```bash
athena checkpoints [COMMAND]
```

Inspect and manage the shadow git store at `~/.athena/checkpoints/` — the storage layer behind the in-session `/rollback` command. Safe to run any time; does not require the agent to be running.

| Subcommand | Description |
|------------|-------------|
| `status` (default) | Show total size, project count, and per-project breakdown. Bare `athena checkpoints` is equivalent. |
| `list` | Alias for `status`. |
| `prune` | Force a cleanup sweep — delete orphan and stale projects, GC the store, enforce the size cap. Ignores the 24h idempotency marker. |
| `clear` | Delete the entire checkpoint base. Irreversible; asks for confirmation unless `-f`. |
| `clear-legacy` | Delete only the `legacy-<timestamp>/` archives produced by the v1→v2 migration. |

### Options

| Option | Subcommand | Description |
|--------|------------|-------------|
| `--limit N` | `status`, `list` | Max projects to list (default 20). |
| `--retention-days N` | `prune` | Drop projects whose `last_touch` is older than N days (default 7). |
| `--max-size-mb N` | `prune` | After the orphan/stale pass, drop the oldest commit per project until total store size ≤ N MB (default 500). |
| `--keep-orphans` | `prune` | Skip deleting projects whose working directory no longer exists. |
| `-f`, `--force` | `clear`, `clear-legacy` | Skip the confirmation prompt. |

### Examples

```bash
athena checkpoints                                  # status overview
athena checkpoints prune --retention-days 3         # aggressive cleanup
athena checkpoints prune --max-size-mb 200          # tighten size cap once
athena checkpoints clear-legacy -f                  # drop v1 archive dirs
athena checkpoints clear -f                         # wipe everything
```

See [Checkpoints and `/rollback`](../user-guide/checkpoints-and-rollback.md) for the full architecture and the in-session commands.

## `athena import`

```bash
athena import <zipfile> [options]
```

Restore a previously created Athena backup into your Athena home directory. All files in the archive overwrite existing files in your Athena home; `--force` only skips the confirmation prompt that fires when the target already has a Athena installation.

| Option | Description |
|--------|-------------|
| `-f`, `--force` | Skip the existing-installation confirmation prompt. |

:::warning
Stop the gateway before importing to avoid conflicts with running processes.
:::

### SQLite databases

`.db` members (`state.db`, `kanban.db`, `response_store.db`, …) are not published with a rename like ordinary files. Renaming would replace the file's inode while a gateway, dashboard, or WebUI process still holds the old one open: that process would keep reading pre-import pages and keep writing sessions nobody else can see, and those sessions would simply be absent from the database everyone opens next — with nothing logged. Instead the imported pages are written **into the existing database file**, the same way `/snapshot restore` does it, so every open connection converges on the imported data.

If the live database cannot be replaced safely — the page copy failed *and* another process still holds the file open — the import leaves that database untouched and lists it under `Warnings (N files skipped)`. Stop the holding processes and re-run.

Importing an older backup over newer work is still allowed, but it is no longer silent. When the imported `state.db` holds fewer messages than the one it replaced, the summary reports it:

```
  ⚠ Session data replaced by older backup contents:
    state.db: 12 session(s) / 8912 message(s) -> 3 / 24
    Anything recorded after the backup was taken is not in it.
    Recover from a newer backup or snapshot: athena snapshot list
```

### Examples
```bash
athena import ~/athena-backup-20260423.zip           # Prompts before overwriting existing config
athena import ~/athena-backup-20260423.zip --force   # Overwrite without prompting
```

## `athena logs`

```bash
athena logs [log_name] [options]
```

View, tail, and filter Athena log files. All logs are stored in `~/.athena/logs/` (or `<profile>/logs/` for non-default profiles).

### Log files

| Name | File | What it captures |
|------|------|-----------------|
| `agent` (default) | `agent.log` | All agent activity — API calls, tool dispatch, session lifecycle (INFO and above) |
| `errors` | `errors.log` | Warnings and errors only — a filtered subset of agent.log |
| `gateway` | `gateway.log` | Messaging gateway activity — platform connections, message dispatch, webhook events |
| `gui` | `gui.log` | Dashboard / TUI-gateway / PTY-bridge / websocket events |
| `desktop` | `desktop.log` | Electron desktop app — boot, backend spawn output, and recent Python tracebacks |

### Options

| Option | Description |
|--------|-------------|
| `log_name` | Which log to view: `agent` (default), `errors`, `gateway`, or `list` to show available files with sizes. |
| `-n`, `--lines <N>` | Number of lines to show (default: 50). |
| `-f`, `--follow` | Follow the log in real time, like `tail -f`. Press Ctrl+C to stop. |
| `--level <LEVEL>` | Minimum log level to show: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. |
| `--session <ID>` | Filter lines containing a session ID substring. |
| `--since <TIME>` | Show lines from a relative time ago: `30m`, `1h`, `2d`, etc. Supports `s` (seconds), `m` (minutes), `h` (hours), `d` (days). |
| `--component <NAME>` | Filter by component: `gateway`, `agent`, `tools`, `cli`, `cron`. |

### Examples

```bash
# View the last 50 lines of agent.log (default)
athena logs

# Follow agent.log in real time
athena logs -f

# View the last 100 lines of gateway.log
athena logs gateway -n 100

# Show only warnings and errors from the last hour
athena logs --level WARNING --since 1h

# Filter by a specific session
athena logs --session abc123

# Follow errors.log, starting from 30 minutes ago
athena logs errors --since 30m -f

# List all log files with their sizes
athena logs list
```

### Filtering

Filters can be combined. When multiple filters are active, a log line must pass **all** of them to be shown:

```bash
# WARNING+ lines from the last 2 hours containing session "tg-12345"
athena logs --level WARNING --since 2h --session tg-12345
```

Lines without a parseable timestamp are included when `--since` is active (they may be continuation lines from a multi-line log entry). Lines without a detectable level are included when `--level` is active.

### Log rotation

Athena uses Python's `RotatingFileHandler`. Old logs are rotated automatically — look for `agent.log.1`, `agent.log.2`, etc. The `athena logs list` subcommand shows all log files including rotated ones.


## `athena prompt-size`

```bash
athena prompt-size [--platform <name>] [--json]
```

Reports the fixed prompt budget for a fresh session — what gets sent on every
API call *before* any conversation content. Useful when a downstream adapter or
proxy has a tighter prompt budget than the model's context window, or when you
want to see which block (skills index, memory, profile) dominates.

It builds the same system prompt the agent would, then breaks it down:

- **System prompt total** — full assembled prompt (identity, guidance, skills
  index, context files, memory, profile, timestamp).
- **Skills index** — the `<available_skills>` block. This is often the largest
  single block when many skills are installed.
- **Memory** and **user profile** — your `MEMORY.md` / `USER.md` snapshots.
- **Prompt tiers** — stable / context / volatile, matching how Athena layers
  the prompt for cache-friendliness.
- **Tool schemas** — the JSON for all enabled tools (the other half of the
  fixed per-call payload).

Runs entirely offline — no API call, works with no credentials configured.

```bash
# Human-readable breakdown for the CLI platform (default)
athena prompt-size

# Simulate a messaging platform's prompt (different platform hint)
athena prompt-size --platform telegram

# Machine-readable output for scripts
athena prompt-size --json
```

:::tip
The skills index and tool schemas scale with how many skills and tools you have
enabled. To shrink the prompt, disable unused toolsets (`athena tools`) or
uninstall skills you don't need (`athena skills`). Context files (AGENTS.md,
.cursorrules) in your current directory also count toward the total.
:::

## `athena config`

```bash
athena config <subcommand>
```

Subcommands:

| Subcommand | Description |
|------------|-------------|
| `show` | Show current config values. |
| `edit` | Open `config.yaml` in your editor. |
| `get <key> [--json]` | Print a single config value by dotted key (e.g. `athena config get model.default`). `--json` emits machine-readable output. |
| `set <key> <value>` | Set a config value. |
| `unset <key>` | Remove a config key, reverting it to the built-in default. |
| `path` | Print the config file path. |
| `env-path` | Print the `.env` file path. |
| `check` | Check for missing or stale config. |
| `migrate` | Add newly introduced options interactively. |

### Dots inside key names

`athena config set/get/unset` use `.` as the nesting separator, but many real
key names contain literal dots — model IDs (`grok-4.6`, `glm-5.3-flash`),
Matrix room IDs (`!room:example.org`), versioned provider names. Two rules
make these addressable:

- **Existing keys just work.** When navigating an existing mapping, an
  existing literal key that matches the dotted remainder is preferred over
  splitting. `athena config set providers.p.models.grok-4.6.supports_vision true`
  updates the real `grok-4.6` entry (and `get`/`unset` resolve the same way).
- **Creating a new dotted key requires escaping.** Escape literal dots with a
  backslash: `athena config set 'providers.p.models.grok-4\.7.context_length' 128000`
  creates the literal `grok-4.7` key. (Quote the key so your shell keeps the
  backslash.)

If an unescaped write would create a nested mapping that shadows an existing
dotted sibling (e.g. creating `grok-4` next to an existing `grok-4.6`), the
command fails with an error instead of silently writing a phantom entry the
runtime would never read.

## `athena pairing`

```bash
athena pairing <list|approve|revoke|clear-pending>
```

| Subcommand | Description |
|------------|-------------|
| `list` | Show pending and approved users. |
| `approve <platform> <code>` | Approve a pairing code. |
| `revoke <platform> <user-id>` | Revoke a user's access. |
| `clear-pending` | Clear pending pairing codes. |

## `athena skills`

```bash
athena skills <subcommand>
```

Subcommands:

| Subcommand | Description |
|------------|-------------|
| `browse` | Paginated browser for skill registries. |
| `search` | Search skill registries. |
| `install` | Install a skill. |
| `inspect` | Preview a skill without installing it. |
| `list` | List installed skills. |
| `check` | Check installed hub skills for upstream updates. |
| `update` | Reinstall hub skills with upstream changes when available. |
| `audit` | Re-scan installed hub skills. |
| `uninstall` | Remove a hub-installed skill. |
| `reset` | Un-stick a bundled skill flagged as `user_modified` by clearing its manifest entry. With `--restore`, also replaces the user copy with the bundled version. |
| `opt-out` | Stop bundled skills from being seeded into the active profile. Writes a `.no-bundled-skills` marker so the installer, `athena update`, and any sync skip bundled-skill seeding. Safe by default — nothing on disk is touched. With `--remove`, also deletes already-present bundled skills that are **unmodified** (user-edited, hub-installed, and hand-written skills are never removed; previews and confirms first, `--yes` to skip). |
| `opt-in` | Undo `opt-out` by removing the `.no-bundled-skills` marker so bundled skills are seeded again on the next `athena update`. With `--sync`, re-seed immediately. |
| `publish` | Publish a skill to a registry. |
| `snapshot` | Export/import skill configurations. |
| `tap` | Manage custom skill sources. |
| `config` | Interactive enable/disable configuration for skills by platform. |

Common examples:

```bash
athena skills browse
athena skills browse --source official
athena skills search react --source skills-sh
athena skills search https://mintlify.com/docs --source well-known
athena skills inspect official/security/1password
athena skills inspect skills-sh/vercel-labs/json-render/json-render-react
athena skills install official/migration/openclaw-migration
athena skills install skills-sh/anthropics/skills/pdf --force
athena skills install https://sharethis.chat/SKILL.md                     # Direct URL (+ referenced support files)
athena skills install https://example.com/SKILL.md --name my-skill        # Override name when frontmatter has none
athena skills check
athena skills update
athena skills config
athena skills reset google-workspace
athena skills reset google-workspace --restore --yes
athena skills opt-out                  # stop future bundled-skill seeding (nothing deleted)
athena skills opt-out --remove --yes   # also delete UNMODIFIED bundled skills
athena skills opt-in --sync            # undo: remove marker and re-seed now
```

Notes:
- `--force` can override non-dangerous policy blocks for third-party/community skills.
- `--force` does not override a `dangerous` scan verdict.
- `--source skills-sh` searches the public `skills.sh` directory.
- `--source well-known` lets you point Athena at a site exposing `/.well-known/skills/index.json`.
- `--source browse-sh` searches [browse.sh](https://browse.sh)'s catalog of 200+ site-specific browser-automation skills. Identifiers look like `browse-sh/airbnb.com/search-listings-ddgioa`.
- Passing an `http(s)://…/*.md` URL installs `SKILL.md` plus explicitly referenced files under `references/`, `templates/`, `scripts/`, `assets/`, and `examples/`. When frontmatter has no `name:` and the URL slug isn't a valid identifier, an interactive terminal prompts for a name; non-interactive surfaces (`/skills install` inside the TUI, gateway platforms) require `--name <x>` instead.

## `athena bundles`

```bash
athena bundles <subcommand>
```

Skill bundles group several skills under one `/<bundle-name>` slash command. Invoking the bundle loads every referenced skill into a single combined user message. Storage: `~/.athena/skill-bundles/<slug>.yaml`. See [Skill Bundles](../user-guide/features/skills.md#skill-bundles) for the YAML schema and behavior.

Subcommands:

| Subcommand | Description |
|------------|-------------|
| `list` | List installed bundles (default when no subcommand given) |
| `show <name>` | Show one bundle's name, description, skills, and file path |
| `create <name>` | Create a new bundle. Pass `--skill <id>` (repeat) or omit for interactive entry. `--description`, `--instruction`, `--force` available. |
| `delete <name>` | Remove a bundle file |
| `reload` | Re-scan `~/.athena/skill-bundles/` and report added/removed bundles |

Examples:

```bash
athena bundles create backend-dev \
  --skill github-code-review \
  --skill test-driven-development \
  --skill github-pr-workflow \
  -d "Backend feature work"

athena bundles list
athena bundles show backend-dev
athena bundles delete backend-dev
```

In a chat session, `/bundles` lists installed bundles and `/<bundle-name>` loads one.

## `athena curator`

```bash
athena curator <subcommand>
```

The curator is an auxiliary-model background task that periodically reviews agent-created skills, prunes stale ones, consolidates overlaps, and archives obsolete skills. Bundled and hub-installed skills are never touched. Archives are recoverable; auto-deletion never happens.

| Subcommand | Description |
|------------|-------------|
| `status` | Show curator status and skill stats |
| `run` | Trigger a curator review now (blocks until the LLM pass finishes) |
| `run --background` | Start the LLM pass in a background thread and return immediately |
| `run --dry-run` | Preview only — produce the review report with no mutations |
| `backup` | Take a manual tar.gz snapshot of `~/.athena/skills/` (curator also snapshots automatically before every real run) |
| `rollback` | Restore `~/.athena/skills/` from a snapshot (defaults to newest) |
| `rollback --list` | List available snapshots |
| `rollback --id <ts>` | Restore a specific snapshot by id |
| `rollback -y` | Skip the confirmation prompt |
| `pause` | Pause the curator until resumed |
| `resume` | Resume a paused curator |
| `pin <skill>` | Pin a skill so the curator never auto-transitions it |
| `unpin <skill>` | Unpin a skill |
| `restore <skill>` | Restore an archived skill |
| `archive <skill>` | Archive a skill manually |
| `prune` | Manually prune skills the curator would normally clean up |
| `list-archived` | List archived skills (recoverable via `restore`) |

On a fresh install the first scheduled pass is deferred by one full `interval_hours` (7 days by default) — the gateway will not curate immediately on the first tick after `athena update`. Use `athena curator run --dry-run` to preview before that happens.

See [Curator](../user-guide/features/curator.md) for behavior and config.

## `athena moa`

Configure named Mixture of Agents presets. Presets appear as selectable models under a `Mixture of Agents` provider in every model picker; `/moa <prompt>` runs one prompt through the default preset.

```bash
athena moa list
athena moa configure [name]
athena moa delete <name>
```

`athena moa configure` reuses Athena' provider → model picker for each reference model and the aggregator. A preset is an execution-mode configuration, not a primary model or provider.

## `athena fallback`

```bash
athena fallback <subcommand>
```

Manage the fallback provider chain. Fallback providers are tried in order when the primary model fails with rate-limit, overload, or connection errors.

| Subcommand | Description |
|------------|-------------|
| `list` (alias: `ls`) | Show the current fallback chain (default when no subcommand) |
| `add` | Pick a provider + model (same picker as `athena model`) and append to the chain |
| `remove` (alias: `rm`) | Pick an entry to delete from the chain |
| `clear` | Remove all fallback entries |

See [Fallback Providers](../user-guide/features/fallback-providers.md).

## `athena hooks`

```bash
athena hooks <subcommand>
```

Inspect shell-script hooks declared in `~/.athena/config.yaml`, test them against synthetic payloads, and manage the first-use consent allowlist at `~/.athena/shell-hooks-allowlist.json`.

| Subcommand | Description |
|------------|-------------|
| `list` (alias: `ls`) | List configured hooks with matcher, timeout, and consent status |
| `test <event>` | Fire every hook matching `<event>` against a synthetic payload |
| `revoke` (aliases: `remove`, `rm`) | Remove a command's allowlist entries (takes effect on next restart) |
| `doctor` | Check each configured hook: exec bit, allowlist, mtime drift, JSON validity, and synthetic run timing |

See [Hooks](../user-guide/features/hooks.md) for event signatures and payload shapes.

## `athena memory`

```bash
athena memory <subcommand>
```

Set up and manage external memory provider plugins. Available providers: honcho, openviking, mem0, hindsight, holographic, retaindb, byterover, supermemory. Only one external provider can be active at a time. Built-in memory (MEMORY.md/USER.md) is always active.

Subcommands:

| Subcommand | Description |
|------------|-------------|
| `setup` | Interactive provider selection and configuration. |
| `status` | Show current memory provider config. |
| `off` | Disable external provider (built-in only). |

:::info Provider-specific subcommands
When an external memory provider is active, it may register its own top-level `athena <provider>` command for provider-specific management (e.g. `athena honcho` when Honcho is active). Inactive providers do not expose their subcommands. Run `athena --help` to see what's currently wired in.
:::

## `athena acp`

```bash
athena acp
```

Starts Athena as an ACP (Agent Client Protocol) stdio server for editor integration.

Related entrypoints:

```bash
athena-acp
python -m acp_adapter
```

Install support first:

```bash
cd ~/.athena/athena-agent && uv pip install -e '.[acp]'
```

See [ACP Editor Integration](../user-guide/features/acp.md) and [ACP Internals](../developer-guide/acp-internals.md).

## `athena mcp`

```bash
athena mcp <subcommand>
```

Manage MCP (Model Context Protocol) server configurations and run Athena as an MCP server.

| Subcommand | Description |
|------------|-------------|
| *(none)* or `picker` | Interactive catalog picker — browse Nous-approved MCPs and install/enable/disable. |
| `catalog` | List Nous-approved MCPs (plain text, scriptable). |
| `install <name>` | Install a catalog entry (e.g. `athena mcp install n8n`). |
| `serve [-v\|--verbose]` | Run Athena as an MCP server — expose conversations to other agents. |
| `add <name> [--url URL] [--command CMD] [--auth oauth\|header] [--args ...]` | Add a custom MCP server with automatic tool discovery. `--args` passes the remaining argv to the stdio command, so put it last. |
| `remove <name>` (alias: `rm`) | Remove an MCP server from config. |
| `list` (alias: `ls`) | List configured MCP servers. |
| `test <name>` | Test connection to an MCP server. |
| `configure <name>` (alias: `config`) | Toggle tool selection for a server. |
| `login <name>` | Force re-authentication for an OAuth-based MCP server. |

See [MCP Config Reference](./mcp-config-reference.md), [Use MCP with Athena](../guides/use-mcp-with-athena.md), and [MCP Server Mode](../user-guide/features/mcp.md#running-athena-as-an-mcp-server).

## `athena plugins`

```bash
athena plugins [subcommand]
```

Unified plugin management — general plugins, memory providers, and context engines in one place. Running `athena plugins` with no subcommand opens a composite interactive screen with two sections:

- **General Plugins** — multi-select checkboxes to enable/disable installed plugins
- **Provider Plugins** — single-select configuration for Memory Provider and Context Engine. Press ENTER on a category to open a radio picker.

| Subcommand | Description |
|------------|-------------|
| *(none)* | Composite interactive UI — general plugin toggles + provider plugin configuration. |
| `install <identifier> [--force] [--ref COMMIT_SHA] [--allow-removed]` | Install a plugin from the Athena plugin catalog (bare entry name), a Git URL, or `owner/repo` shorthand. Catalog names resolve to the entry's repo at its pinned 40-hex commit SHA, show the declared capability summary, and record catalog provenance in a `.athena-catalog.json` sidecar. Raw URLs are flagged as custom (unreviewed) sources; `--ref` (full 40-character commit SHA) pins them. `--allow-removed` (DANGEROUS) bypasses the removed-plugin blocklist. |
| `search [term] [--json]` | Search the Athena plugin catalog (matches entry names, descriptions, and declared tools; omit `term` to list everything). The catalog is curated in-repo (`plugin-catalog/`), refreshed from the live repo with a 6-hour cache, and falls back to the in-tree copy offline. Cataloged ≠ audited — admission reviews the entry, not the code. |
| `update <name>` | Pull latest changes for an unpinned installed plugin. Pinned plugins must be reinstalled with `--force --ref <new-commit>` to move. |
| `remove <name>` (aliases: `rm`, `uninstall`) | Remove an installed plugin. |
| `enable <name>` | Enable a disabled plugin. |
| `disable <name>` | Disable a plugin without removing it. |
| `list` (alias: `ls`) | List installed plugins with enabled/disabled status. |
| `doctor [path-or-id] [--ci]` | Validate a native plugin through the real manifest parser, loader, and registration path. `--ci` exits 1 on errors. |
| `pack install <path-or-url> [--force]` | Install a plugin pack (`athena-pack.yaml`) — a declarative set of plugins each pinned to an exact 40-character commit SHA. Shows a mandatory review screen (every plugin, source, pinned ref, declared capabilities), asks one confirmation for the pack contents, then runs ordinary pinned installs. Each plugin's declared capabilities still go through the standard per-plugin consent — a pack never bulk-grants. Partial failures are reported per plugin; exits non-zero when any plugin failed. Interactive only (no `--yes`). |
| `pack export [--enabled-only] [--name NAME]` | Emit a pack YAML on stdout from the current install: repo + exact SHA of each git-installed plugin plus sanitized non-secret `plugins.entries` config. Local-only plugins (no git provenance) are listed as warning comments, never as installable entries. Secrets, capability grants, and `allow_*` gates are always stripped. |
| `pack show <path-or-url>` | Dry-run: parse, validate, and display a pack without installing anything. |

Provider plugin selections are saved to `config.yaml`:
- `memory.provider` — active memory provider (empty = built-in only)
- `context.engine` — active context engine (`"compressor"` = built-in default)

General plugin disabled list is stored in `config.yaml` under `plugins.disabled`.
Git installs also record only their canonical source, exact installed revision, and
pin status in the profile-local `plugins/.install-metadata.json` sidecar. It does
not contain plugin config, environment values, secrets, or capability grants.

See [Plugins](../user-guide/features/plugins.md) and [Build a Athena Plugin](../developer-guide/plugins/index.md).

## `athena tools`

```bash
athena tools [--summary]
```

| Option | Description |
|--------|-------------|
| `--summary` | Print the current enabled-tools summary and exit. |

Without `--summary`, this launches the interactive per-platform tool configuration UI.

## `athena computer-use`

```bash
athena computer-use <subcommand>
```

Subcommands:

| Subcommand | Description |
|------------|-------------|
| `install` | Run the upstream cua-driver installer (macOS, Windows, and Linux). |
| `install --upgrade` | Re-run the installer even if cua-driver is already on PATH. The upstream script always pulls the latest release, so this performs an in-place upgrade. |
| `status` | Print whether `cua-driver` is on `$PATH` and which version is installed. |
| `doctor [--include CHECK] [--skip CHECK] [--json]` | Run cua-driver's health report and show its platform checks. |
| `permissions status [--json]` | Report macOS Accessibility and Screen Recording grants. |
| `permissions grant` | Ask macOS to grant Accessibility and Screen Recording to Cua Driver. |

`athena computer-use install` is the stable entry point for installing the
[cua-driver](https://github.com/trycua/cua) binary used by the
`computer_use` toolset. It runs the same upstream installer that
`athena tools` invokes when you first enable Computer Use, so it's safe
to use for re-running the install if the toolset toggle didn't trigger
it (for example, on returning-user setups).

If cua-driver is already present, Athena checks its version and runtime
manifest. A compatible 0.20.0 or newer installation is left in place. An old or
incomplete standard installation is repaired with the current upstream
installer. Athena never replaces a custom binary selected through
`ATHENA_CUA_DRIVER_CMD`; update that binary directly or remove the override.
`athena computer-use status` reports when repair is required.

The built-in `computer_use` toolset is the recommended Athena integration.
Registering raw Cua MCP tools is an alternative when you need Cua's low-level
tool vocabulary. `cua-driver skills install` detects Athena and links Cua's
skill pack into the Athena skills directory automatically.

Permission mode and capability-manifest approval
belong to runtime launch. In bounded mode Athena passes Cua's canonical
`--capability-manifest` and `--approve-capability-manifest` flags. Every MCP
transport owns a private lifecycle session inside its runtime. Public session
names label cursor and session state; they do not own or share the runtime.

`athena update` automatically re-runs the upstream installer at the end
of the update if cua-driver is on PATH, so most users will not need to
call `--upgrade` manually. Use it when upstream ships a fix you want
right now without waiting for the next Athena update.

## `athena pets`

```bash
athena pets <list|install|select|show|off|scale|remove|doctor>
```

[Petdex](https://github.com/crafter-station/petdex) is a public gallery of animated sprite pets for coding agents. Install one and Athena shows it reacting to agent activity across the CLI, TUI, and desktop app.

| Subcommand | Description |
|------------|-------------|
| `list` | Browse the petdex gallery. |
| `install` | Install a pet from the gallery. |
| `select` | Set the active pet (writes `display.pet.*`). |
| `show` | Animate the active pet in the terminal. |
| `off` | Disable the pet display. |
| `scale` | Resize the pet everywhere (`display.pet.scale`). |
| `remove` | Delete an installed pet. |
| `doctor` | Check pet setup + terminal graphics support. |

You can also generate a brand-new pet from a text description with the `/hatch` slash command. See [Pets](../user-guide/features/pets.md).

## `athena sessions`

```bash
athena sessions <subcommand>
```

Subcommands:

| Subcommand | Description |
|------------|-------------|
| `list` | List recent sessions. |
| `browse` | Interactive session picker with search and resume. Each row shows a lifecycle status tag (`done` / `intr` / `err` / `empty`, derived from the session's final message) and its message count. Press `d` on a highlighted row (while the search filter is empty) to delete that session after a y/N confirmation; while a filter is active, `d` types into the search instead. |
| `export <output> [--session-id ID]` | Export sessions to JSONL. |
| `delete <session-id>` | Delete one session. |
| `prune` | Delete sessions matching filters: time bounds `--older-than`/`--newer-than`/`--before`/`--after` (durations like `5h`/`2d`, bare days, or ISO timestamps); attributes `--source`, `--title`, `--model`, `--provider`, `--branch`, `--end-reason`, `--user`, `--chat-id`, `--chat-type`, `--cwd`; numeric bounds `--min/--max-messages`, `--min/--max-tokens`, `--min/--max-cost`, `--min/--max-tool-calls`; plus `--include-archived`, `--dry-run`, `--yes`. Default: older than 90 days. |
| `archive` | Bulk-archive (soft-hide, no deletion) sessions matching the same filters as `prune`. Requires at least one filter. |
| `stats` | Show session-store statistics. |
| `rename <session-id> <title>` | Set or change a session title. |
| `optimize` | Reclaim disk space: merge FTS5 index segments + VACUUM. Non-destructive — no session data changes. |
| `optimize-storage` | Migrate the full-text search index to the compact v23 external-content layout; on large databases this reclaims a large fraction of `state.db`. |
| `repair` | Repair a malformed `state.db` schema (e.g. `table messages_fts already exists`) so hidden sessions reappear; a backup is made first. |
| `repair-routing` | Re-attach gateway conversations stranded in session rows that lost their routing identity (a chat "jumping back in time" after a restart). Dry-run by default; `--apply` performs the adoptions (stop the gateway first); `--max-gap-seconds N` tunes the contiguity window. Only unambiguous cases are repaired. See [Sessions → Repair Stranded Gateway Sessions](../user-guide/sessions.md#repair-stranded-gateway-sessions). |
| `recover` | Offline, non-destructive recovery of a damaged `state.db` into a separate clean database. |
| `retitle-skills` | Regenerate titles for sessions opened with a `/skill`, using what the user actually typed; lists changes unless `--apply` is passed. |

## `athena insights`

```bash
athena insights [--days N] [--source platform]
```

| Option | Description |
|--------|-------------|
| `--days <n>` | Analyze the last `n` days (default: 30). |
| `--source <platform>` | Filter by source such as `cli`, `telegram`, or `discord`. |

## `athena claw`

```bash
athena claw migrate [options]
```

Migrate your OpenClaw setup to Athena. Reads from `~/.openclaw` (or a custom path) and writes to `~/.athena`. Automatically detects legacy directory names (`~/.clawdbot`, `~/.moltbot`) and config filenames (`clawdbot.json`, `moltbot.json`).

| Option | Description |
|--------|-------------|
| `--dry-run` | Preview what would be migrated without writing anything. |
| `--preset <name>` | Migration preset: `full` (all compatible settings) or `user-data` (excludes infrastructure config). Neither preset imports secrets — pass `--migrate-secrets` explicitly. |
| `--overwrite` | Overwrite existing Athena files on conflicts (default: refuse to apply when the plan has conflicts). |
| `--migrate-secrets` | Include API keys in migration. Required even under `--preset full`. |
| `--no-backup` | Skip the pre-migration zip snapshot of `~/.athena/` (by default a single restore-point archive is written to `~/.athena/backups/pre-migration-*.zip` before apply; restorable with `athena import`). |
| `--source <path>` | Custom OpenClaw directory (default: `~/.openclaw`). |
| `--workspace-target <path>` | Target directory for workspace instructions (AGENTS.md). |
| `--skill-conflict <mode>` | Handle skill name collisions: `skip` (default), `overwrite`, or `rename`. |
| `--yes` | Skip the confirmation prompt. |

### What gets migrated

The migration covers 30+ categories across persona, memory, skills, model providers, messaging platforms, agent behavior, session policies, MCP servers, TTS, and more. Items are either **directly imported** into Athena equivalents or **archived** for manual review.

**Directly imported:** SOUL.md, MEMORY.md, USER.md, AGENTS.md, skills (4 source directories), default model, custom providers, MCP servers, messaging platform tokens and allowlists (Telegram, Discord, Slack, WhatsApp, Signal, Matrix, Mattermost), agent defaults (reasoning effort, compression, human delay, timezone, sandbox), approval rules, TTS config, browser settings, tool settings, exec timeout, command allowlist, gateway config, and API keys from 3 sources.

**Archived for manual review:** Cron jobs, plugins, hooks/webhooks, memory backend (QMD), skills registry config, UI/identity, logging, multi-agent setup, channel bindings, IDENTITY.md, TOOLS.md, HEARTBEAT.md, BOOTSTRAP.md.

**API key resolution** checks three sources in priority order: config values → `~/.openclaw/.env` → `auth-profiles.json`. All token fields handle plain strings, env templates (`${VAR}`), and SecretRef objects.

For the complete config key mapping, SecretRef handling details, and post-migration checklist, see the **[full migration guide](../guides/migrate-from-openclaw.md)**.

### Examples

```bash
# Preview what would be migrated
athena claw migrate --dry-run

# Full migration (all compatible settings, no secrets)
athena claw migrate --preset full

# Full migration including API keys
athena claw migrate --preset full --migrate-secrets

# Migrate user data only (no secrets), overwrite conflicts
athena claw migrate --preset user-data --overwrite

# Migrate from a custom OpenClaw path
athena claw migrate --source /home/user/old-openclaw
```

## `athena import-agent`

```bash
athena import-agent [claude-code|codex] [options]
```

Import a **Claude Code** (`~/.claude`) or **OpenAI Codex CLI** (`~/.codex`) setup into Athena. Maps `CLAUDE.md`/`AGENTS.md` instructions to memory entries, `Bash(...)` permission allow/deny rules to `command_allowlist`/`approvals.deny`, MCP servers to `mcp_servers` in `config.yaml`, and skill directories into `~/.athena/skills/`. Always previews before applying; API keys and credentials are never imported.

| Option | Description |
| --- | --- |
| `agent` | `claude-code` or `codex` (default: auto-detect). |
| `--source <path>` | Custom source directory (default: `~/.claude` or `~/.codex`). |
| `--dry-run` | Preview only — write nothing. |
| `--overwrite` | Replace conflicting MCP servers / skills (default: skip). |
| `--yes`, `-y` | Skip confirmation prompts. |

See the **[import guide](../user-guide/import-from-other-agents.md)** for the full mapping tables.

## `athena serve`

```bash
athena serve [options]
```

Start the Athena **backend server** — the JSON-RPC/WebSocket gateway the [desktop app](/user-guide/desktop) and remote clients connect to. It is the same server `athena dashboard` runs, but **headless**: it never opens a browser UI. The desktop app launches its own `athena serve` backend; use this command directly when you want a headless backend on a remote host. Accepts the same `--host` / `--port` / `--insecure` / `--skip-build` / `--stop` / `--status` options as `athena dashboard` below (a non-loopback bind engages the same auth gate). Requires the `[web]` extra; the embedded Chat socket additionally needs `[pty]` on a POSIX host.

**Port conflicts:** if the requested port (default `9119`) is already held by another process (e.g. a second `athena serve` or the gateway), the command prints a machine-readable sentinel line `BACKEND_PORT_IN_USE port=<port>` to stdout, a human hint naming the likely holder, and exits with code **75** (`EX_TEMPFAIL`) instead of a generic error — so scripts and the desktop app can tell "port occupied" apart from "backend broken". Pass `--port 0` to bind a free ephemeral port (the successful boot announces the chosen port via `ATHENA_BACKEND_READY port=<port>`).

## `athena dashboard`

```bash
athena dashboard [options]
```

Launch the web dashboard — a browser-based UI for managing configuration, API keys, and monitoring sessions. (For a headless backend with no browser UI — e.g. what the desktop app spawns — use [`athena serve`](#athena-serve) above.) Requires `cd ~/.athena/athena-agent && uv pip install -e ".[web]"` (FastAPI + Uvicorn). The embedded browser Chat tab is always available and additionally needs the `pty` extra (`cd ~/.athena/athena-agent && uv pip install -e ".[web,pty]"`) plus a POSIX PTY environment such as Linux, macOS, or WSL2. See [Web Dashboard](/user-guide/features/web-dashboard) for full documentation.

| Option | Default | Description |
|--------|---------|-------------|
| `--port` | `9119` | Port to run the web server on |
| `--host` | `127.0.0.1` | Bind address |
| `--no-open` | — | Don't auto-open the browser |
| `--insecure` | off | **Deprecated / no-op.** Formerly bypassed auth on a non-loopback bind. Since the June 2026 hardening a public bind *always* requires an auth provider (password or OAuth). Bind `127.0.0.1` and tunnel to keep it local. |
| `--skip-build` | off | Skip the web UI build step and serve the existing `dist` directly. Useful for non-interactive contexts (Windows Scheduled Tasks, CI) where npm isn't available. Pre-build with `cd web && npm run build`. |
| `--isolated` | off | When launched from a named profile (`worker dashboard`), run a dedicated per-profile server instead of routing to the machine dashboard. |
| `--stop` | — | Stop running `athena dashboard` processes and exit. |
| `--status` | — | List running `athena dashboard` processes and exit. |

### `athena dashboard register`

Register this install as a self-hosted dashboard with your Nous Portal account. Creates an OAuth client, writes `ATHENA_DASHBOARD_OAUTH_CLIENT_ID` into `~/.athena/.env`, and prints how to engage the login gate. Requires being logged in (`athena setup`).

| Option | Description |
|--------|-------------|
| `--name` | Human-readable label for the dashboard (default: auto-generated). |
| `--redirect-uri` | Public HTTPS OAuth redirect URI (e.g. `https://athena.example.com/auth/callback`). Omit for localhost-only use. |
| `--portal-url` | Override the Nous Portal base URL for registration (default: the portal you logged into). Also settable via `ATHENA_DASHBOARD_PORTAL_URL`. |

```bash
# Default — opens browser to http://127.0.0.1:9119
athena dashboard

# Custom port, no browser
athena dashboard --port 8080 --no-open

# From a profile alias — routes to the machine dashboard with the
# profile preselected in the sidebar switcher (attach if running)
worker dashboard
```

## `athena profile`

```bash
athena profile <subcommand>
```

Manage profiles — multiple isolated Athena instances, each with its own config, sessions, skills, and home directory.

| Subcommand | Description |
|------------|-------------|
| `list` | List all profiles. |
| `use <name>` | Set a sticky default profile. |
| `create <name> [--clone] [--clone-all] [--clone-from <source>] [--no-alias]` | Create a new profile. `--clone` copies config, `.env`, `SOUL.md`, and skills from the active profile. `--clone-all` copies all state. `--clone-from` specifies a source profile and implies config clone unless paired with `--clone-all`. |
| `delete <name> [-y]` | Delete a profile. |
| `show <name>` | Show profile details (home directory, config, etc.). |
| `alias <name> [--remove] [--name NAME]` | Manage wrapper scripts for quick profile access. |
| `rename <old> <new>` | Rename a profile. |
| `export <name> [-o FILE]` | Export a profile to a `.tar.gz` archive (local backup). |
| `import <archive> [--name NAME]` | Import a profile from a `.tar.gz` archive (local restore). |
| `install <source> [--name N] [--alias] [--force] [-y]` | Install a profile distribution from a git URL or local directory. |
| `update <name> [--force-config] [-y]` | Re-pull a distribution; preserves user data (memories, sessions, auth). |
| `info <name>` | Show a profile's distribution manifest (version, requirements, source). |

Examples:

```bash
athena profile list
athena profile create work --clone
athena profile use work
athena profile alias work --name h-work
athena profile export work -o work-backup.tar.gz
athena profile import work-backup.tar.gz --name restored
athena profile install github.com/user/my-distro --alias
athena profile update work
athena -p work chat -q "Hello from work profile"
```

## `athena completion`

```bash
athena completion [bash|zsh|fish]
```

Print a shell completion script to stdout. Source the output in your shell profile for tab-completion of Athena commands, subcommands, and profile names.

Examples:

```bash
# Bash
athena completion bash >> ~/.bashrc

# Zsh
athena completion zsh >> ~/.zshrc

# Fish
athena completion fish > ~/.config/fish/completions/athena.fish
```

## `athena update`

```bash
athena update [--gateway] [--check] [--plan] [--no-backup] [--backup] [--yes]
```

Pulls the latest `athena-agent` code and reinstalls dependencies in the managed venv, then re-runs the post-install hooks (MCP servers, skills sync, completion install). Safe to run on a live install. Use `--check` to see whether your checkout is behind `origin/main` without installing.

`athena update` pulls the configured update branch (default: `main`). If your checkout is on another branch, Athena may check out the update branch before pulling. Commit branch work before updating when you want to keep it outside the update autostash flow.

| Option | Description |
|--------|-------------|
| `--gateway` | Internal mode used by the messaging `/update` command. Uses file-based IPC for prompts and progress streaming instead of reading from terminal stdin. Not a gateway restart flag. |
| `--check` | Check whether an update is available without pulling, installing dependencies, or restarting anything. |
| `--plan` | Print the update plan and exit without changing anything: install kind (git/Docker/Nix/apt), every running Athena service across all profiles with its supervisor and running code version, and how each will be restarted. On image- or package-managed installs, reports the correct external update command instead. Read-only. |
| `--no-backup` | Skip all pre-update backups for this run (both the quick state snapshot and the full zip), regardless of `updates.pre_update_backup`. |
| `--backup` | Force a **full** pre-update backup for this run: the quick state snapshot plus a complete zip of `ATHENA_HOME` (config, auth, sessions, skills, pairing data). The default mode is `quick` — a lightweight state snapshot only. Set the permanent mode via `updates.pre_update_backup: quick | full | off` in `config.yaml`. |
| `--yes`, `-y` | Assume yes for interactive prompts such as config migration and stash restore. API-key entry is skipped; run `athena config migrate` separately for those. |

Additional behavior:

- **Gateway restart.** After a successful update, Athena attempts to restart all running gateway profiles automatically so they pick up the new code. Use `athena gateway restart` when you want to restart a gateway without applying an update.
- **Restart-phase recovery.** If the in-process restart phase aborts while importing the freshly pulled tree, supervised gateway profiles are retried through a clean Python process. Only restarts independently confirmed by systemd (`systemctl --user is-active`) are reported as verified; a relaunch that merely exited 0 is recorded as `relaunch_attempted` and still fails the update conservatively. Manual gateways and serve/dashboard runtimes are never killed without a relaunch authority; they are recorded as skipped with a reason and remain in the incomplete-update report with the exact restart command.
- **Update receipts + fleet version check.** Every run writes a machine-readable receipt to `~/.athena/logs/update_receipts/` (pre-update fleet plan, steps, skips with reasons, restart outcome; `latest.json` points at the newest). After the restart phase the updater verifies each live gateway's running code against the updated checkout and prints a per-profile version matrix; a gateway still on pre-update code fails the update (exit 1) with the exact restart command.
- **Local source changes.** For git installs, dirty tracked files and untracked files are auto-stashed before branch checkout or pull (`git stash push --include-untracked`). Interactive terminal updates ask before restoring the stash. Non-interactive updates restore it by default; set `updates.non_interactive_local_changes: discard` only on managed installs where local source edits should be thrown away after a successful pull. If stash restore conflicts or the pull fails, the stash is left in place for manual recovery.
- **npm lockfile churn.** Before stashing or switching branches, Athena makes a best-effort cleanup of tracked `package-lock.json` diffs produced by npm install/build steps. Commit or manually stash intentional lockfile edits before running `athena update`.
- **Pairing data snapshot.** Even when `--backup` is off, `athena update` takes a lightweight snapshot of `~/.athena/pairing/` and the Feishu comment rules before `git pull`. You can roll it back with `athena backup restore --state pre-update` if a pull rewrites a file you were editing.
- **Legacy `athena.service` warning.** If Athena detects a pre-rename `athena.service` systemd unit (instead of the current `athena-gateway.service`), it prints a one-time migration hint so you can avoid flap-loop issues.
- **Exit codes.** `0` on success, `1` on pull/install/post-install errors, `2` on unexpected working-tree changes that block `git pull`.

## Maintenance commands

| Command | Description |
|---------|-------------|
| `athena --version` | Print version information. |
| `athena update` | Pull latest changes and reinstall dependencies. |

| `athena uninstall [--full] [--gui] [--dry-run] [--yes]` | Remove Athena, optionally deleting all config/data. `--gui` removes only the desktop Chat GUI, leaving the agent intact; `--full` also deletes config/data; `--dry-run` prints what would be removed without changing anything; `--yes` skips prompts. |

## See also

- [Slash Commands Reference](./slash-commands.md)
- [CLI Interface](../user-guide/cli.md)
- [Sessions](../user-guide/sessions.md)
- [Skills System](../user-guide/features/skills.md)
- [Skins & Themes](../user-guide/features/skins.md)
