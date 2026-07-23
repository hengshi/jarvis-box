# Changelog

## 0.1.31

- Aligns status filter E2E coverage with the simplified status summary/metrics UI (`历史受理记录` + `正在处理`) and current user/task search flows.

## 0.1.30

- Ensures `stop --force` ends runtime sessions and closes agent-browser children for terminal cleanup paths, so resources are not left behind.
- Closes task-scoped `agent-browser` sessions when a task enters terminal transition, and records closure failure with a dedicated reason.
- Preserves immediate cleanup for completed tasks while keeping completed-workspace retention for continue use configurable (now default 60 minutes).
- Adds status-page support for one-click cleanup of completed workspaces and a leaner `historical_accepted`/`processing` metric surface.
- Exposes real continuation/cancellation failure details on status pages to avoid generic “conflict” messages.

## 0.1.29

- Cleans due Task Workspaces when persisted PID or process-group evidence is stale, while still deferring cleanup for live process identities.
- Makes the post-Run Task Workspace retention window configurable in minutes with a 60-minute default, while Continue still reuses retained worktrees and Cancel remains immediate.
- Shows the specific structured failure when Continue cannot safely replace an active Run instead of collapsing it into a generic HTTP conflict.
- Surfaces the actual redacted runtime launch failure in Status progress so operators can diagnose missing runtime prerequisites directly.

## 0.1.28

- Recovers stale legacy IM task bindings safely and adds `/new` to reset the current chat session without routing back into invalid pre-registry task state.
- Preserves registered Task Workspaces for three hours after a Run ends so Continue can reuse worktrees, while Cancel and provider close/merge events still clean them immediately.
- Restricts execution workspace repositories to the Task's declared project set and keeps Workspace ownership, delayed cleanup, and recovery state durable across service restarts.
- Routes merge-request review writeback retries through the Task-scoped launcher and preserves canonical `storage-wait` results after post-claim capacity failures.
- Starts a new Task from the latest immutable Run context so declared project routing stays current while traversal-shaped Run identifiers remain contained.
- Migrates stale macOS `JARVIS_CLI` overrides to the canonical runtime binary so scheduled self-improvement remains runnable after upgrades.

## 0.1.27

- Cleans installer, glab fallback, release-gate, deploy-smoke, and macOS developer bootstrap temporary files without removing protected runtime paths.
- Preserves downloaded release artifacts across retryable install preflight failures, then removes the install download cache after a successful install.
- Canonicalizes GitLab merge-request and GitHub pull-request command workspace and dedupe paths while still recognizing legacy dedupe records.

## 0.1.26

- Recovers provider targets correctly after Continue so follow-up execution and writeback stay attached to the intended IM, GitLab, or GitHub surface.
- Fixes task-owned workspace lifecycle cleanup and MR review writeback fencing after completion callbacks.
- Improves storage-wait recovery by using a 10 GB default threshold and automatically admitting work once storage pressure clears.
- Classifies terminal and waiting status items more accurately, including legacy terminal results and stop-safety cases.
- Extends runtime agent wall timeout handling for longer-running agent work.

## 0.1.25

- Reduces the public Task lifecycle to exactly Start, Continue, and Cancel across providers, CLI, API, Status, and IM.
- Treats active-Run replacement, recovery, native resume, cross-agent continuation, and writeback retry as internal Continue/Cancel strategies.
- Removes the durable Task `waiting` transition after an operator stop; a stopped Run leaves its Task in `needs-attention` until Continue or Cancel.
- Preserves long-running IM and GitLab Issue completion writebacks across reply expiry, process recovery, and incomplete delivery retries.
- Uses uv-im-connector provider capabilities for proactive fallback, including safe recovery after a single-use reply token has already been consumed.
- Cleans completed disposable-lane workspaces after completion callbacks while retaining protected, failed, stopped, and explicitly persistent workspaces.
- Keeps the Status agent selector synchronized with the agent session that actually executes the Run.

## 0.1.24

- Delivers agent-generated IM task files through capable uv-im-connector providers while keeping host-local paths and unverified delivery claims out of fallback replies.
- Distinguishes the remote IM user, jarvis-box host, GitLab, and GitHub environments in agent delivery prompts.
- Restores the explicit `jarvis-box update` command with active-Run safety and installer-owned restart behavior.
- Cleans completed lane workspaces only after successful completion callbacks while preserving bugfix, jarvis-command, failed, and stopped workspaces.
- Preserves active Runs and continuation state across service operations and strengthens feature-prework impact-evidence gating.

## 0.1.23

- Recreates reclaimed workspaces during Continue while preserving recovery metadata if recreation fails.
- Removes competing age- and disk-based workspace deletion from jarvis-box and delegates cleanup to the canonical runtime path.
- Captures Codex thread-started session handles across stdout and stderr event ordering.
- Avoids full Task scans on Status progress hot paths.
- Installs Mole through the Hengshi-managed macOS developer bootstrap while keeping public cross-platform installation independent of Homebrew.

## 0.1.22

- Allows restart past old terminal `reaping_failed` records after their recorded process is no longer running.
- Keeps live `reaping_failed` evidence as a hard restart blocker.

## 0.1.21

- Narrows the restart guard to block live unsafe Run processes and `reaping_failed` evidence without blocking already-lost or terminal historical Task records.
- Keeps service restart safe for active Codex work while allowing release-gate and production restarts on long-lived reference boxes with retained Task history.

## 0.1.20

- Adds agent-aware Codex prefix-argument policy with a global default and a literal `bugfix` override.
- Recomputes or clears Codex-specific prefix arguments across runtime-agent failover without losing Run recovery context.
- Exposes effective runtime-agent policy through CLI and status surfaces.
- Blocks `jarvis-box restart` while active, unsafe, or recovery-required Task runs are present.
- Documents the canonical Codex model policy configuration for managed deployments.

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
