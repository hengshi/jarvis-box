# Tasks, recovery and monitoring

Prefer typed lifecycle output to directory/process guesses:

```bash
jarvis-box tasks list
jarvis-box tasks json --all --limit 50
jarvis-box tasks show <task-id>
jarvis-box tasks events <task-id>
jarvis-box tasks verify
```

For diagnosis, use `tasks verify` for artifact integrity findings, then `tasks show <task-id>` and `tasks events <task-id>` for the affected Task's state and event history.

`list/json` without `--all` show current lifecycle blockers, not all historical tasks. Use an explicit time window for a monitoring report and paginate/expand the inspected set before claiming totals. Resolve `runs_dir`, `workspace_root` and `log_dir` from effective status. If passing a runs directory explicitly for artifact inspection, use the reported value, not `state/runs` reconstructed from a default. Service logs use `jarvis-box logs` or the selected Docker deployment's service logs; connector logs are separate.

Report actual status, phase, current/latest Run, lane, safe source identity, error and `next_action`. Include waiting/storage-wait/duplicate-wait, ci-wait, finalizing, needs-attention, recovery-required, completed, cancelled and supersession when returned. Historical `failed-terminal`/`retry-exhausted` can project as needs-attention. Do not treat a living low-CPU/idle Agent as lost merely because it is waiting for network, CI or a model.

Agent completion, provider delivery and workspace disposal are separate facts. A completed Task can have `phase=writeback-failed` and `next_action=retry-writeback`. Inspect structured `writeback_failure`: category, retryability and delivery certainty; an outer connector HTTP 502 is not proof of the provider's own HTTP status. Unknown delivery must not be blindly replayed.

## Choose the actual Continue strategy

Read `tasks show` and `tasks continue --help` before recommending or executing an action:

| Strategy | CLI input | Effect |
| --- | --- | --- |
| agent | `--agent <agent> --message <new-message>` together | Continue the same Task with a new Run; do not omit one parameter |
| recover | Neither `--agent` nor `--message` | Recover the selected recovery-required Task according to runtime ownership |
| writeback | Neither `--agent` nor `--message` | Replay already prepared delivery; does not run the Agent or create another Run |

Start/Continue/Cancel are mutations. A report-only monitor must not execute them, reconnect a connector, reap processes or run real cleanup. Diagnose with existing artifacts and read-only probes first. If recovery needs a real send, honor the customer's authorized target and duplicate-delivery constraints.

## Cleanup and scheduled work

`tasks clean --older-than 30 --dry-run` previews retained terminal Task Artifact deletion; choose retention from the customer's request rather than silently making 30 days policy. Real deletion requires completed/cancelled Tasks with workspace disposal complete. Workspace cleanup follows the registered `workspaces[]` owner, leases and configured delay. Do not scan arbitrary directories for orphans or delete caches/logs to repair a Task.

Custom host-scheduled prompt jobs start a fresh Task on every firing:

```bash
jarvis-box tasks start --prompt '<full job prompt>' \
  --lane custom-user-task --job-id customer-daily-report \
  --reason scheduled-customer-daily-report
```

`lane` is the behavior class; `job_id` is the stable custom-job identity. Arbitrary lane names are rejected; the same active job id prevents concurrent starts. Do not schedule repeated Continue of an old Task. Built-in Company cognition lanes use the service's internal route and remain owned by Company Runtime Foundation. `read-only` mode does not grant custom prompt jobs an exception.

## Metrics and IM

Observe ChatBridge connected/degraded reasons from health/status and connector diagnostics. Account/model quota is best-effort evidence; unavailable quota does not by itself mean an Agent is unusable. Delivery Metrics runs in the ordinary `delivery-metrics` Task lane. Machine Task Run trends, retained Task counts and provider delivery quality measure different things; do not combine them into one total.

The automatic repair funnel includes ZenTao original work items alongside the other supported work-item providers. Count automatic post-check intake by the complete typed Subject; ZenTao bug/story/task/case with the same number remain distinct. An ad-hoc comment command does not establish intake, and a task is not automatically classified as a Bug. Submitted/merged repair stages require the associated GitLab MR or GitHub PR evidence; a closed ZenTao item alone does not prove a merged repair.

Opening Status/value APIs can initiate pending Delivery Metrics analysis on versions where that behavior is enabled. A strictly observational monitor should prefer existing CLI artifacts and avoid those initiating reads. Use current-Run `outbox/` for explicitly requested outbound files; a path mentioned in an answer is not an attachment delivery instruction.
