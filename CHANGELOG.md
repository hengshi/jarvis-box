# Changelog

## 0.1.19

- Unifies provider, CLI, API, and Status behavior around Start Task, Continue With Agent, Stop Run, Recover Lost Run, and Retry Writeback.
- Removes in-service update and restart activation so deployments remain external service operations.
- Applies model-usage-limit cooldowns globally, fails the current Task over immediately, and restores the primary runtime agent after refresh.
- Supports concurrent IM Tasks, quoted-message Task routing, Target-scoped `/stop <run-id>` and `/stop all`, and compact canonical Run IDs.
- Keeps IM Target bindings as default Task pointers while Run state and AgentConversation state remain authoritative in each Task.
- Serializes cross-process Run claims, publishes final output before Task completion, and prevents late delivery evidence from replacing a newer Run's projection.

## 0.1.18

- Keeps installed app manifests aligned with the packaged binary so app metadata reports the same version and commit.
- Honors the formal `/usr/local/bin/jarvis-box` macOS CLI path during service and scheduled-job execution.
- Splits GitHub command allowlists by provider and fixes GitHub command author matching.
- Keeps stale Task recovery explicit and operator-selected.
- Adds runtime self-improve review gates and clearer Task recovery evidence.

## 0.1.17

- Hardens GitHub issue and PR command triggers with immutable numeric GitHub user id allowlists.
- Unifies mention trigger configuration under `JARVIS_MENTION_NAMES` for ChatBridge, GitLab comments, and GitHub issue/PR comments.
- Supports both `@name` and `/name` command mentions for every configured GitLab/GitHub trigger name.
- Documents the production GitHub webhook setup path, ingress checks, user-id lookup, and public-repository security model.

## 0.1.16

- Prevents ChatBridge startup from replaying stale WeCom or Lark chat-command tasks.
- Persists UV IM connector cursor state and bootstraps missing cursors to the latest connector sequence.
- Adds and documents the GitHub provider loop and production ingress rollout path.
- Moves Docker deploy smoke release-gate execution to the dedicated m2 Docker runner.
- Keeps Docker builds on configured Go proxy fallbacks so release gates do not depend on the publisher's local Docker Desktop.

## 0.1.15

- Fixes transient MR review workspace git recovery and Stop Run controls.
- Hardens Codex native session-handle capture across stdout/stderr stream ordering and user-marker boundaries.
- Adds the scheduled session self-improve cron and fixes empty prefix-argument handling.
- Hardens follow-up resume launch failure handling and removes automatic self-heal paths.

## 0.1.14

- Adds scoped runtime agent `prefix_args` so lanes can use supported agents with explicit model/runtime arguments.
- Documents Codex `gpt-5.4-mini` high-reasoning MR review/followup configuration.
- Preserves scoped prefix arguments across review, followup, issue execution, post-check, self-heal, and command lanes without leaking parent-lane settings into child runs.
- Fixes MR review trigger/update handling around ready transitions and commit detection.
- Improves ChatBridge runtime resume behavior for IM-driven work.

## 0.1.13

- Fixes task recovery session IDs and real agent-session content rendering in the status page.
- Adds issue execution automation through the existing MR gate.
- Expands model-usage-limit classification to catch monthly quota wording from Copilot CLI.

## 0.1.12

- Folds continuation session JSONL into the status task session timeline.

## 0.1.11

- Preserves runtime-agent fallback behavior when usage-limit responses include reset hints.
- Adds `--force` support for `agent set` and `agent unset`, with CLI tests and docs.
- Improves UV IM connector final reply handling and Claude session display.
- Adds configurable terminal failure classification and effective lane-scope agent visibility.
- Fixes task session JSONL timeline reads.

## 0.1.10

- Integrates the UV IM connector as the ChatBridge provider surface.
- Adds UV IM readiness, health, timeout, reply recovery, and version-contract checks.
- Removes built-in IM providers in favor of the connector contract.
- Fixes Kubernetes config keys, ChatBridge allowlist surfaces, repro gate behavior, and issue comments.

## 0.1.9

- Fixes status log polling pressure for active work item aggregation.
- Fixes agent session full log display in the status UI.
- Fixes unattended cron contract to require explicit runtime delegation for repo-pre-push review and allow managed workspace metadata.
- Documents the no-meaningless-wrapper review rule.

## 0.1.8

- Adds runtime agent enable, disable, and fallback order controls.
- Keeps agent selection in the canonical runtime config used by new work.
- Fixes the release E2E gate for canonical runtime agent config.

## 0.1.7

- Adds IM attachment downloads and document attachment E2E coverage.
- Notifies ChatBridge trigger authors and fixes direct WeCom markdown messages.
- Fixes command-agent legacy override, active work-item aggregation, and runtime fallback ordering.
- Enhances runtime agent enable, disable, and ordering controls.

## 0.1.6

- Clarifies that unqualified jarvis-box release requests publish both internal and public release surfaces.
- Fixes maintenance runtime access for Codex-based maintenance paths.
- Fixes chatbridge retry replies and runtime status handling.

## 0.1.5

- Adds the post-merge self-improve lane for bugfix-related main-branch merges.
- Ships `config/env.jarvis-box.sample` in release artifacts and installer output.
- Keeps public installation pinned through `JARVIS_VERSION=0.1.5` or latest metadata.

## 0.1.4

- Prepares the public 0.1 distribution materials.

## 0.1.3

- Continues the Jarvis maintenance release line that fed the public 0.1 baseline.

## 0.1.2

jarvis-box 0.1.2 is the first public Host Runtime baseline.

### Highlights

- Installs a single-binary jarvis-box service on Ubuntu 22.04 and 24.04 systemd hosts.
- Provides release artifacts for Linux and macOS `amd64` and `arm64`.
- Supports GitLab webhook intake, Jira bug bridge intake, IM long-connection intake, `/status` actions, CLI task operations, and scheduled host maintenance.
- Uses the Target, Task, Run, AgentConversation, Workspace, and artifact lifecycle model.
- Continues conversations through runtime-native resume handles instead of replaying old prompt history.
- Supports the 0.1 adapter registry: Codex, Claude Code, Copilot CLI, Gemini, Opencode, Hermes, and OpenClaw.
- Exposes operator commands for status, doctor, monitor, release checks, task inspection, Stop Run, Recover Lost Run, and runtime agent checks.

### Public Scope

The 0.1 line is a host runtime release. It does not include full customer memory bootstrap, connector marketplace packaging, enterprise avatar maturity levels, or multi-node orchestration.

## 0.1.1

- Captures native resume handles for runtime-agent continuation.

## 0.1.0

- Establishes the initial jarvis-box 0.1 runtime line, including the Go binary product shape, task lifecycle, GitLab webhook intake, IM bridge, runtime-agent dispatch, Ubuntu/macOS install evidence, and public release contracts.
