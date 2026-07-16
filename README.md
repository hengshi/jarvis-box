# jarvis-box

jarvis-box is a host runtime for agent-driven engineering work. It receives GitLab webhooks, Jira issue events, IM messages, status actions, CLI requests, and scheduled maintenance jobs; launches configured runtime agents; stores task artifacts; and exposes operator controls for service health and task lifecycle.

The 0.1 line is the Host Runtime release. It is not a full enterprise avatar platform and does not include customer memory bootstrap, connector marketplace packaging, or multi-node orchestration.

Current public baseline: `v0.1.25 (v2026.7.16)`. Install pin: `JARVIS_VERSION=0.1.25`.

## Install

Ubuntu 22.04 and 24.04 LTS with systemd are supported for public installs.

```bash
curl -fsSL https://raw.githubusercontent.com/hengshi/jarvis-box/main/install.sh | sudo bash
```

Pinned install:

```bash
curl -fsSL https://raw.githubusercontent.com/hengshi/jarvis-box/main/install.sh |
  sudo JARVIS_VERSION=0.1.25 bash
```

The installer downloads a versioned release artifact, verifies `SHA256SUMS`, installs the `jarvis-box` CLI, writes a systemd service, and starts the service.

macOS launchd artifacts exist for Hengshi-managed reference boxes. Public 0.1 installs target Ubuntu systemd.

## Basic Commands

```bash
jarvis-box status --smart
jarvis-box doctor
jarvis-box monitor
jarvis-box start
jarvis-box stop
jarvis-box restart
```

## Configure GitLab Projects

Authenticate the GitLab CLI with an access token that can manage project webhooks:

```bash
jarvis-box setup gitlab --auth-only
```

Then reconcile webhook configuration:

```bash
GITLAB_HOST=gitlab.example.com \
GITLAB_PROJECTS=group/project \
JARVIS_PUBLIC_URL=https://jarvis.example.com \
jarvis-box setup gitlab --non-interactive
```

Release artifacts include `config/env.jarvis-box.sample`; the installer copies it to `/etc/jarvis-box/env.jarvis-box.sample` as the starting point for runtime configuration.

## Runtime Agents

jarvis-box is a thin orchestration layer. Runtime agents own reasoning, conversation history, native resume, and context compaction. jarvis-box records Task/Run state and artifacts; its Task lifecycle has exactly three operations: Start, Continue, and Cancel. Active-Run replacement, recovery, native resume, cross-agent continuation, and writeback retry are internal Continue/Cancel strategies rather than additional product operations. It does not replay old conversation turns into new prompts.

The 0.1 adapter registry includes:

- Codex
- Claude Code
- Copilot CLI
- Gemini
- Opencode
- Hermes
- OpenClaw

Adapter availability depends on the CLI tools installed on the host.

## Release Channels

Public release surfaces are published at:

- `https://github.com/hengshi/jarvis-box`
- `https://download.hengshi.com/jarvis-box/install.sh`
- `https://download.hengshi.com/jarvis-box/latest.json`
- `https://download.hengshi.com/jarvis-box/releases/v<version>/`

Public GitHub releases are selected stable versions. Internal Hengshi releases may be more frequent than public releases.

## License

jarvis-box is distributed under the HENGSHI Commercial License. It is not licensed as open source software.
