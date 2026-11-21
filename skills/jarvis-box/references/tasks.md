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

Report the current Task's four-state status (running, completed, failed or cancelled), lifecycle stage, next actor, blocker, current/latest Run, safe source identity and available action. A technical failure means the current request did not finish; it is not a request for an administrator. An acknowledged business question does not keep a Task waiting: valid execution and required delivery complete the Task while its business outcome and question remain available for later input. Preserve old Run errors as history when a successor has completed. Do not treat a living low-CPU/idle Agent as lost merely because it is waiting for network, CI or a model.

Agent completion, provider delivery and workspace disposal are separate facts. A succeeded Run does not mean required delivery finished: the Task can still be running while finalizing, running a bounded delivery retry, or failed after recovery stops. Inspect structured `writeback_failure`: category, retryability and delivery certainty; an outer connector HTTP 502 is not proof of the provider's own HTTP status. Unknown delivery must not be blindly replayed. An acknowledged send followed by an index repair does not authorize a second send.

## Choose the actual Continue strategy

Read `tasks show` and `tasks continue --help` before recommending or executing an action:

| Strategy | CLI input | Effect |
| --- | --- | --- |
| agent | `--agent <agent> --message <new-message>` together | Continue the same Task with a new Run; do not omit one parameter |
| recover | Neither `--agent` nor `--message` | Recover the selected recovery-required Task according to runtime ownership |
| writeback | Neither `--agent` nor `--message` | Replay already prepared delivery; does not run the Agent or create another Run |

Start/Continue/Stop are mutations. Stop preserves the Task and native conversation; workspaces and unfinished files remain until the configured cleanup deadline. Continue before expiry cancels the old cleanup schedule; send a new message with Continue to resume. Use `tasks stop <task-id>`; the released `tasks cancel` spelling is an alias. In IM, /stop preserves the current Task binding so the next ordinary message continues it. Already stopped Runs stay terminal, and automatic recovery does not restart them. A report-only monitor must not execute them, reconnect a connector, reap processes or run real cleanup. Diagnose with existing artifacts and read-only probes first. If recovery needs a real send, honor the customer's authorized target and duplicate-delivery constraints.

## Webhook accepted but no Task started

Use the installed version's `jarvis-box webhooks --help`. Resolve the selected
runtime with `status --smart`, then run `webhooks list` and `webhooks show
<receipt_id>`. These are read-only. Report the provider delivery ID, Jarvis
receipt ID, phase, exact Task/Run IDs when present, and concrete dependency error.
`pending-comment` identifies an accepted review comment still awaiting debounce
or the original Task. If its launch stopped, recover that receipt; the service
submits only that original comment and does not replay consumed comments.
Do not interpret `admission_outcome_unknown` as missing customer configuration.
It denotes an interrupted dispatch receipt, not proof that no Task was created.

For an authorized recovery, run `jarvis-box webhooks retry <receipt_id>`, then
`show` again. HTTP 202 means recovery was requested, not that the task completed.
The service first reconciles the original Task and resumes only the original
safe admission; never delete deduplication records or edit private JSON. If
`task_id` is returned, inspect that Task instead of creating another one.

Fix a reported authentication, license, network or storage dependency and
verify it with `doctor` before retrying. A disabled provider requires restoring
that provider's existing configuration. A runtime mismatch requires selecting
the correct canonical runtime. If an older receipt lacks the original input,
resend that same event from the source platform's webhook delivery history,
then retry its receipt ID. For a definite pre-launch failure, each explicit
retry authorizes one new attempt while preserving the previous failure.
Upgrades and ordinary redeliveries never automatically replay an old interrupted
receipt without recovery protocol proof. Its explicit retry is required. If
detail identifies an imported historical deduplication record, retain it: retry
cannot authorize historical re-execution. New work requires a new `@jarvis`
instruction on the original work item, not deletion of old data.
For unreadable storage, preserve the original record and repair the reported
path/permissions/volume; deleting it can lose duplicate-execution protection.
The corresponding customer procedure is in `docs/cli.md` under webhook recovery.

## Cleanup and scheduled work

`tasks clean --older-than 30 --dry-run` previews retained terminal Task Artifact deletion; choose retention from the customer's request rather than silently making 30 days policy. Real deletion requires completed/cancelled Tasks with workspace disposal complete. Workspace cleanup follows the registered `workspaces[]` owner, leases and configured delay. Do not scan arbitrary directories for orphans or delete caches/logs to repair a Task.

Custom host-scheduled prompt jobs start a fresh Task on every firing:

```bash
jarvis-box tasks start --prompt '<full job prompt>' \
  --lane custom-user-task --job-id customer-daily-report \
  --reason scheduled-customer-daily-report \
  --notify-target direct:<provider-native-user-id>
```

`lane` is the behavior class; `job_id` is the stable custom-job identity. Arbitrary lane names are rejected; the same active job id prevents concurrent starts. Do not schedule repeated Continue of an old Task. Job definitions, schedules and recipients belong to the customer or its Runtime Foundation. Optional `--notify-target direct:<id>|group:<id>` sends the successful Run final answer through the existing configured IM channel; omit it for no notification. Admission fixes the route, and waiting/restart/Continue preserve it. Unknown sends are not retried. Use the runtime receipt as delivery evidence, and do not ask the Agent to send the same answer separately. Published pre-generic scheduler inputs remain compatibility-only; new jobs use this generic interface. `read-only` mode does not grant custom prompt jobs an exception.

## Metrics and IM

Observe ChatBridge connected/degraded reasons from health/status and connector diagnostics. Account/model quota is best-effort evidence; unavailable quota does not by itself mean an Agent is unusable. Delivery Metrics runs in the ordinary `delivery-metrics` Task lane. Machine Task Run trends, retained Task counts and provider delivery quality measure different things; do not combine them into one total.

The automatic repair funnel includes ZenTao original work items alongside the other supported work-item providers. Count automatic post-check intake by the complete typed Subject; ZenTao bug/story/task/case with the same number remain distinct. An ad-hoc comment command does not establish intake, and a task is not automatically classified as a Bug. Submitted/merged repair stages require the associated GitLab MR or GitHub PR evidence; a closed ZenTao item alone does not prove a merged repair.

Delivery Metrics advances in the background from startup, merge events, task completion and periodic reconciliation; current Status/value reads do not start analysis. For an older installed release, check its matching contract before assuming the same read behavior. Use current-Run `outbox/` for explicitly requested outbound files; a path mentioned in an answer is not an attachment delivery instruction.
