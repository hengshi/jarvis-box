# Configure Jarvis Box by intent

Use this index to find a small part of the matching release's configuration contract. The authoritative field definitions are `docs/configuration.md`, `config/env.jarvis-box.sample`, `deploy/production/*.example` and the relevant integration document in that release. A field listed here is not permission to enable an unrelated capability.

## IM messages, assistant name and notifications

These fields belong to Jarvis Box's effective runtime env, not connector provider credentials. Read `docs/integrations/im.md` for the target release. Changing these server settings requires restart/recreate through the selected deployment's normal lifecycle.

| Customer intent | Setting | Contract |
| --- | --- | --- |
| Rename the assistant across IM, prompts, comments and Status | `JARVIS_BRAND_NAME` | Default `Jarvis`; display name only, not product commands/paths. Reject quotes, backtick, backslash, `<`, `>`, `&`, `%` and control characters |
| Change how users address the assistant | `JARVIS_MENTION_NAMES` | Comma-separated triggers; first entry is used by the default help text. Coordinate with the actual bot mention identity; changing display name alone does not rename a provider bot |
| Change “task accepted / started” reply | `JARVIS_CHAT_LAUNCH_REPLY_TEMPLATE` | Exactly one `%s`: Run id |
| Change “received but waiting” reply | `JARVIS_CHAT_QUEUED_REPLY_TEMPLATE` | Exactly two `%s`: wait reason, Task id |
| Change the “not addressed / how to invoke” hint | `JARVIS_CHAT_HELP_REPLY_TEMPLATE` | Exactly two `%s`: assistant display name, first trigger word |
| Change the completion notification's first line | `JARVIS_COMMAND_NOTIFY_COMPLETED_TEMPLATE` | Plain text title; no format substitution. Does not replace the Agent's answer or the whole final message |
| Enable/disable proactive completion notifications | `JARVIS_COMMAND_NOTIFY_ENABLED` | Boolean; separate from normal ChatBridge replies |
| Select notification transport | `JARVIS_NOTIFY_PROVIDER`, `JARVIS_NOTIFY_CONNECTOR` | Provider plus optional connector instance; resolve connector metadata when several exist. Do not use legacy `*_CHANNEL` variables |
| Select completion recipients | `JARVIS_COMMAND_NOTIFY_RECIPIENT_MODE` | Inspect the matching release's supported values; default `trigger_author`. Do not guess recipient IDs or send a probe without an authorized target |
| Restrict IM users/chats or require a mention | `JARVIS_CHAT_ALLOWED_USERS`, `JARVIS_CHAT_ALLOWED_CONVERSATIONS`, `JARVIS_CHAT_REQUIRE_MENTION` | Use provider/connector-scoped identities; do not widen access as a side effect of changing wording |
| Enable the connector | `JARVIS_CONNECTOR_PROFILE` | Empty or `uvim`; retaining only a URL does not enable it |
| Connect Jarvis Box to UVIM | `JARVIS_UV_IM_CONNECTOR_URL`, `JARVIS_UV_IM_CONNECTOR_TOKEN`, `JARVIS_UV_IM_CONNECTOR_NAME` | Jarvis-to-connector access. Native provider credentials remain in the connector's env |

Empty template values restore built-in defaults. The three `JARVIS_CHAT_*_REPLY_TEMPLATE` fields use Go formatting: preserve the required `%s` slots in order, and write a literal percent as `%%`. Extra/missing slots, stray `%`, or other format verbs fail startup. The completion title is different: `%s` would remain literal text there.

IM sends an acceptance or waiting receipt, then the final result. Running progress is available on Status; this release does not support an IM progress-reply template.

For “把开始处理的提示改成：收到，我来处理，并保留任务编号”, select the launch reply and show both:

```text
JARVIS_CHAT_LAUNCH_REPLY_TEMPLATE='收到，我来处理。运行编号：%s'
Rendered: 收到，我来处理。运行编号：r_EXAMPLE
```

For “完成通知改成：分析已完成”, select only:

```text
JARVIS_COMMAND_NOTIFY_COMPLETED_TEMPLATE='分析已完成'
Rendered first line: 分析已完成
```

These are env-file values, not instructions to export shell variables as the durable configuration. Preserve literal text through the target release's env parser. If requested copy contains apostrophes, quotes, dollar signs, backslashes, backticks or line breaks, verify that parser's supported encoding before writing; do not interpolate customer text into a shell command. Do not edit a current template by blindly replacing every occurrence of the assistant name.

## Other common goals

| Goal | First supported surface / fields | Read next |
| --- | --- | --- |
| Change default Agent | `jarvis-box agent current`, `agent list`, `agent set <agent>` | `docs/runtime-agents.md`, `jarvis-box agent --help` |
| Change models or an Agent's launch arguments | Agent-native configuration; selected Agent's command/prefix-argument fields in the matching env sample | `docs/runtime-agents.md`, Agent's own help; Agent name does not identify its billing provider |
| Use a separate Agent for delivery analysis | `agent set --scope delivery-metrics <agent>` / `agent unset --scope delivery-metrics` | `docs/cli.md` |
| Stop starting new delivery analyses | `JARVIS_DELIVERY_METRICS_ENABLED` | `docs/delivery-metrics.md`; existing Runs/Continue are separate |
| Add GitLab repositories/review scope | `GITLAB_HOST`, `GITLAB_PROJECTS`, `REVIEW_GITLAB_PROJECTS` | `docs/integrations/gitlab.md`; provider identity remains the runtime user's CLI authentication |
| Add GitHub repositories/review scope | `GITHUB_REPOSITORIES`, `REVIEW_GITHUB_REPOSITORIES`, `JARVIS_GITHUB_WEBHOOK_ENABLED` | `docs/integrations/github.md`; workspace-only access need not enable webhook intake |
| Connect Jira or Feishu Project | `JIRA_*`, `FEISHU_PROJECT_*`, `MEEGLE_*` candidates from the release sample | Corresponding integration guide; distinguish CLI identity, webhook authentication and plugin backend |
| Connect ZenTao 21 work items | `ZENTAO_BASE_URL`, `ZENTAO_ACCOUNT`, `ZENTAO_API_TOKEN`, `JARVIS_ZENTAO_WEBHOOK_SECRET`, `ZENTAO_ALLOWED_SCOPES`, `ZENTAO_ALLOWED_USERS` | `docs/integrations/zentao.md`; scopes are `product:<id>` for bugs/stories/cases and `execution:<id>` for tasks |
| Associate a work item with repositories | `JARVIS_WORK_ITEM_REPOSITORIES` | `docs/configuration.md`; retain provider scope and allowlists |
| Disable runtime-owned provider writeback | `JARVIS_PROVIDER_WRITEBACK_ENABLED` | `docs/configuration.md`; does not sandbox an Agent's own CLI credentials |
| Enable issue post-check / merged-change self-improvement | `JARVIS_ISSUE_POST_CHECK_ENABLED`, `JARVIS_SELF_SKILLS_IMPROVE_ENABLED` and documented scope subsets | Install the Company/repo workflow first; a switch does not provide a workflow |
| Add a customer executable | `JARVIS_USER_TOOL_BIN`, `jarvis-box tools path/status` | `docs/cli.md`; use a derived Docker image for OS libraries/compiler packages |
| Use an automation browser | `AGENT_BROWSER_EXECUTABLE_PATH` | `docs/configuration.md`; managed browser/socket belong to a Run, never desktop Chrome |
| Update Company skills before a new Task's Agent starts | `JARVIS_AGENT_RUNTIME_PREPARE_COMMAND`, `JARVIS_AGENT_RUNTIME_PREPARE_TIMEOUT_SECONDS` | Company Runtime Foundation owns the executable, repo/ref, locking and discovery roots |
| Configure dependency sharing | `JARVIS_DEPENDENCY_CACHE_ROOT`, optional `JARVIS_WORKSPACE_DEPENDENCY_CONFIGURER` | `docs/storage-model.md`; caches are separate from Task cleanup |
| Change disk admission threshold | `JARVIS_TASK_STORE_MIN_FREE_GB` | `docs/configuration.md`; distinguish storage-wait from Agent failure |
| Change cleanup timing | `JARVIS_TASK_WORKSPACE_CLEANUP_DELAY_MINUTES` | `docs/task-external-resource-lifecycle.md`; artifact retention is a different operation |
| Change Docker port, bind address, image or instance | `JARVIS_PORT`, `JARVIS_BIND_ADDRESS`, `JARVIS_IMAGE`, `JARVIS_DEPLOYMENT_NAME` in `deployment.env` | `docs/deployment.md`, `docs/multi-instance.md`; preserve the deployment home |
| Activate or renew a license | `jarvis-box license status/activate/request/import` | `docs/cli.md`, `CUSTOMER-OPERATIONS.md`; release license server is compiled in, not a customer URL setting |

The index is a route, not a complete variable registry. Verify candidate fields in the installed version before writing. Runtime env is canonical through `JARVIS_ENV_FILE`; Docker Compose additionally owns its injected runtime paths. Do not redefine Compose-owned paths in `runtime.env`. Native service env and an interactive shell can differ; shell `printenv` alone is not proof of the service's effective configuration.

## ZenTao onboarding and event diagnosis

Use the matching release's `docs/integrations/zentao.md` for the native webhook and CLI setup. ZenTao OSS 21 uses official `zentao-cli` 0.2.0 with SDK 0.4.1; do not upgrade it to a CLI requiring another server version. Use the Token-owning service account, never store its password in runtime configuration, and keep webhook credentials out of Agent context.

The native webhook must include the stable action `id`, use the configured HTTP Basic identity, and enable the relevant creation/comment notifications. ZenTao's product/execution sender filters and Jarvis Box's explicit allowed scopes both apply. New bugs, stories, tasks and test cases enter automatic post-check when enabled; visible `@jarvis` comments enter the command lane. Confirm full history/attachments with the documented native API because CLI detail output may omit history. Server-owned result publication preserves work-item status and keeps retry metadata hidden in the note.

In System Settings > Integrations, use the source directory to see the supported-source total and effective states, then select ZenTao or Common Settings. Switching sources preserves unsaved inputs; saving writes configuration, and activation requires the selected deployment's normal restart procedure. A configured source, a received webhook, a started Agent and a successfully posted result are separate checks. Use an explicitly authorized target for a real creation/comment probe.
