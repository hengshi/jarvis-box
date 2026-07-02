# Changelog

## 0.1.6

- Clarifies that unqualified jarvis-box release requests publish both internal and public release surfaces.
- Fixes maintenance runtime access for Codex-based maintenance paths.
- Fixes chatbridge retry replies and runtime status handling.

## 0.1.5

- Adds the post-merge self-improve lane for bugfix-related main-branch merges.
- Ships `config/env.jarvis-box.sample` in release artifacts and installer output.
- Keeps public installation pinned through `JARVIS_VERSION=0.1.5` or latest metadata.

## 0.1.2

jarvis-box 0.1.2 is the first public Host Runtime baseline.

### Highlights

- Installs a single-binary jarvis-box service on Ubuntu 22.04 and 24.04 systemd hosts.
- Provides release artifacts for Linux and macOS `amd64` and `arm64`.
- Supports GitLab webhook intake, Jira bug bridge intake, IM long-connection intake, `/status` actions, CLI task operations, and scheduled host maintenance.
- Uses the Target, Task, Run, AgentConversation, Workspace, and artifact lifecycle model.
- Continues conversations through runtime-native resume handles instead of replaying old prompt history.
- Supports the 0.1 adapter registry: Codex, Claude Code, Copilot CLI, Gemini, Opencode, Hermes, and OpenClaw.
- Exposes operator commands for status, doctor, monitor, update, task inspection, task cancel, task recovery, and runtime agent checks.

### Public Scope

The 0.1 line is a host runtime release. It does not include full customer memory bootstrap, connector marketplace packaging, enterprise avatar maturity levels, or multi-node orchestration.
