---
name: jarvis-box-monitor
description: Report recent Jarvis Box activity and actionable runtime problems across Tasks, Runs, delivery, IM, storage and cleanup without changing the deployment.
---

# Jarvis Box monitoring

Report only. Resolve the actual deployment and read the installed `jarvis-box` skill's [Task monitoring reference](../jarvis-box/references/tasks.md), or the matching release's `docs/cli.md`, `docs/execution-model.md` and `docs/storage-model.md` if unavailable.

Start with `status --smart`, `tasks list` for blockers, and `tasks json --all` with appropriate filters/limits for recent history. State the time window and inspected population. Follow returned Task/Run identity and typed status/phase/next_action; use `tasks show/events/logs` for the few actionable items. Do not assume that the five last directory names are the five most recent Runs or that default `tasks list` includes completed history.

Summarize recent sources and lanes, active/waiting/finalizing/recovery-required Tasks, execution failures, completed-but-undelivered results, deferred cleanup, license admission, storage and ChatBridge degraded/connected reasons. Keep historical machine Run trends distinct from retained Task counts and provider quality. Read service/connector logs from the selected deployment only when structured evidence is insufficient.

Do not Start/Continue/Cancel/reap/clean, reconnect, smoke-call an Agent, or open an API that initiates analysis. Cleanup can be previewed with `--dry-run` when requested. State the next action without executing it; include whether delivery would be retried or the Agent rerun. Report sampled/limited counts honestly and redact credentials, private resume handles and raw message payloads.

Webhook intake and writeback are separate stages. Use [release compatibility and delivery boundaries](../jarvis-box/references/release-contract.md) before interpreting `202`, a completed Task with `writeback-failed`, or an `outcome_unknown` receipt.

Depth and verification pointers: [skill-depth](../jarvis-box/references/skill-depth.md), [evals](../jarvis-box/evals/evals.json), and `scripts/audit_skill_depth.py` from the repository root.
