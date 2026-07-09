# Changelog

## 0.1.16

- Prevents ChatBridge startup from replaying stale WeCom or Lark chat-command tasks.
- Persists UV IM connector cursor state and bootstraps missing cursors to the latest connector sequence.
- Moves Docker deploy smoke release-gate execution to the dedicated m2 Docker runner.
- Keeps Docker builds on configured Go proxy fallbacks so release gates do not depend on the publisher's local Docker Desktop.

## 0.1.14

- Adds scoped runtime agent `prefix_args` so lanes can use supported agents with explicit model/runtime arguments.
- Documents Codex `gpt-5.4-mini` high-reasoning MR review/followup configuration.
- Preserves scoped prefix arguments across review, followup, issue execution, post-check, self-heal, and command lanes without leaking parent-lane settings into child runs.
- Fixes MR review trigger/update handling around ready transitions and commit detection.
- Improves ChatBridge runtime resume behavior for IM-driven work.

## 0.1.9

- Fixes status log polling pressure for active work item aggregation.
- Fixes agent session full log display in the status UI.
- Fixes unattended cron contract to require explicit runtime delegation for repo-pre-push review and allow managed workspace metadata.
- Documents the no-meaningless-wrapper review rule.

## 0.1.8

- Adds runtime agent enable, disable, and fallback order controls.
- Keeps agent selection in the canonical runtime config used by new work.
- Fixes the release E2E gate for canonical runtime agent config.

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
