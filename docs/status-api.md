# Status 与 Server API

`/status` 是团队可见工作的界面和 API；`/server` 是主机维护界面。两者不得混用权限或数据。

## Status 读模型

`GET /status/api/work-items` 返回：

- `items` / `count`：当前分页窗口。
- `total` / `counts`：整个 public projection 的统计，不受分页 `limit` 影响。
- 每个 item 的 `status_group` 是服务端确定的页面筛选分组，取值为 `doing`、`needs-human`、`failed`、`completed` 或 `all`；Status 页面不得从状态文本重复推断分组。

分组时 lifecycle 事实优先于 feed kind：`waiting`、`stopped` 和 `needs-attention` 进入 `needs-human`，失败终态进入 `failed`，`completed` 和 `cancelled` 进入 `completed`；`progress_checkpoint` 等 kind 不得把这些状态重新归入 `doing`。历史持久化状态 `failed-terminal` 和 `retry-exhausted` 在读取时兼容投影为 `needs-attention`，仍按失败终态分组，不会被旧的 `monitor_status=active` 覆盖。

`GET /status/api/tasks` 和单 Task detail 返回 public projection。默认读路径可以读取 Task state 和 bounded Artifact metadata，但不得读取 native AgentSession、private resume handle value、raw payload 或任意主机路径。

单 Task 查询接受 Task id、当前/最新 Run id，也接受仍保留 `run-state.json` 的历史 Run id。使用 Run id 查询时返回其所属 Task；Run id 不会被当成 Task identity。

单 Task detail 的 `workspace_locations` 是主机路径规则的唯一例外，用于建立 Task 与可清理工作目录的明确关联。每项只包含服务端生成的 opaque id、显示标签、绝对目录、存在状态、删除资格和原因；其他任意 Workspace、Run 或日志路径仍不得进入 public projection。

Run 从被 claim 到 Agent 进程真正启动之间，Task detail 公开准备进度：`preparation_started_at`、`preparation_elapsed_ms`、`current_operation`、`current_operation_started_at`、`current_operation_elapsed_ms`、`current_operation_attempt`、`current_operation_max_attempts` 和 `current_operation_detail`。Status 页面必须优先显示当前操作、已耗时和重试次数，不能只显示笼统的“Run created”或“执行中”。准备成功、失败、取消或进入 recovery 时清空 `current_operation`，并把 `preparation_elapsed_ms` 冻结为最终耗时；历史 Task 没有这些字段时保持兼容。

长期在线约束：

- 首屏读取一次 list/work-items，后续通过一条 SSE 连接接收变化。
- 未变化的 SSE tick 不得全量扫描 `runs_dir`。
- 只对选中的 Task 读取 bounded event/log tail。
- Artifact 内容只在用户显式打开时读取。
- 多个浏览器标签共享服务端 projection/cache。

## 三个生命周期操作

Task response 的 `actions` 恰好使用以下 key：

```json
{
  "start": {"enabled": true, "reason": "inactive-source-task"},
  "continue": {
    "enabled": true,
    "reason": "task-ready",
    "strategy": "agent",
    "requires_input": true
  },
  "cancel": {"enabled": false, "reason": "terminal-task"}
}
```

后端 policy 是唯一授权来源。UI 和 CLI 不自行推断 enabled 状态。所有 mutation 写入 audit event；`read-only` serve mode 统一拒绝。

### Start

`POST /status/api/tasks/{task_id}/start?reason=...`

- 选中的 Task 只是 source。
- 创建新 Task、新 AgentConversation 和首个 Run。
- 成功结果中的 `task_id` 是新 Task，`run_id` 是它的首个 Run；两者不能混用。
- 原 Task、Run 和 Artifact 不变。
- source active、`needs-attention`、完成但仍缺产物/写回、进程 ownership 未解决或 lane 不支持时返回 `409` 和明确 reason；先 Continue 或 Cancel 原 Task。

### Continue

`POST /status/api/tasks/{task_id}/continue?reason=...`

```json
{
  "agent": "copilot",
  "message": "继续调查网络恢复后的失败"
}
```

- `actions.continue.strategy` 是服务端选择的内部策略：
  - `agent`：`agent` 与 `message` 必须同时提供；在同一 Task 创建新 Run，复用全部已登记 Workspace，并以 primary 作为默认 `cwd`。
  - `recover`：不接受 agent/message；为 `recovery-required` Task 创建恢复 Run。
  - `writeback`：不接受 agent/message；只重试已有 comment/reply delivery，不创建 Run。
- agent strategy 下，同 agent 且 private handle 有效时使用 native resume；其他情况创建 child AgentConversation。
- mutation result 使用 `strategy=agent|recover|writeback`；agent strategy 另以 `agent_strategy=native-resume|new-agent-conversation` 说明 runtime conversation 选择。
- agent strategy 遇到 active Run 时，服务端先同步解决旧 Run ownership，再创建后续 Run；失败返回 `409 run-stop-failed`。
- recover strategy 只来自进程观察链与终态证据不一致；正常 idle、等待 CI、网络或模型响应不能触发。
- writeback strategy 只在 provider-ready 内容存在且 delivery pending/failed 时启用。
- Task identity 始终不变；持久化 prompt 只包含本次输入或服务端生成的恢复 prompt。

### Cancel

`POST /status/api/tasks/{task_id}/cancel?reason=...`

- 终结 Task，状态变为 `cancelled`。
- 存在 active Run 时先解决其进程 ownership；对应 Run 进入 `stopped`。
- `recovery-required` 且没有可用 pid/pgid 时，服务端以状态 ownership fence 固定旧 Run，再取消 Task。
- 无法证明进程已停止时记录 `reaping_failed`，返回冲突，不把 Task 伪装成已取消。
- 干净 completed 或已经 cancelled 的 Task 返回 terminal/no-op；完成但仍缺产物/写回的 Task 可以 Cancel，表示放弃剩余工作。
- Task Artifact 按保留策略继续存在。

## 工作目录清理

Task workspace 只有一条归属链：append-only 的 `task-state.workspaces[]`。一个 Task 可以登记多个仓库目录；每项有稳定的 Task-local `id`、服务端分配的绝对 `path` 和可选 repository metadata。已有项不可换 id、路径或仓库；恰好一个 `primary=true` 只负责选择 Run 的默认 `cwd`，不限制 Task 的工作区数量。

TaskService 在首个 Run claim 之前一次登记 Task identity 和初始工作区，然后才检查容量并逐项创建、clone 或 checkout。容量不足时 Status 显示 `storage-wait / wait-for-storage`；此时可以 Cancel，但 Continue 由自动恢复取代。Runner 向每个 runtime agent 注入相同的 Workspace ownership contract；运行中的 zero-workspace Task 必须以 `jarvis-box workspace create --id primary` 建立第一个仓库，非空 registry 后续增加仓库时使用普通 stable id。Agent 不得绕过该命令创建、替换或物化 `JARVIS_WORKSPACE_ROOT` 的任何直接子项。该命令先验证当前 Run 仍持有 Task，并在原子 state mutation 中追加登记，登记落盘后才创建目录。Status detail、Continue、自动清理和手工清理都只读取 `task-state.workspaces[]`；`cwd`、`workdir`、`run-context.json`、artifact 文件和目录扫描都不是 workspace 归属来源。

所有 lane 使用同一规则，不设客户工作流白名单。Task 成功或取消时先持久化 terminalization intent，再遍历并清理全部登记项，最后发布 completed/cancelled。若最终状态写入或清理遇到 ENOSPC/瞬时故障，Status 显示 `finalizing` 和 `retry-finalization`；服务在磁盘恢复后按 intent 自动重放，并发 Continue 不能越过该边界。

Task 创建时会把 GitLab/GitHub/Jira 外部工作对象登记成规范化 `task-state.subject`。GitLab issue `close`、MR `close/merge`，GitHub issue `closed`、PR closed/merged，以及 Jira issue 进入 Done category 或被删除时，provider adapter 调用同一个终态入口：非终态 Task 先停止并转为 cancelled，再清理全部登记目录；已有终态只重试清理。首次处理 terminal delivery 时，服务先把当时精确匹配到的 `task_dir` 集合原子写入 receipt，再做任何取消或清理；部分失败、进程退出或磁盘故障后的 retry 只重放这份快照，不重新扫描 Task。关联只来自创建时的 subject 登记，不从 `issue_or_mr` 文本、workspace 路径、Artifact、branch 或 lane 反推。

`POST /status/api/tasks/{task_id}/delete-workspace`

```json
{
  "workspace_id": "f3a91c5e16c27b42"
}
```

该接口是 Status 页面提供的主机维护动作；每次只删除用户选中的一个已登记工作区，不改变 Task lifecycle：

- 客户端只能回传最近一次 Task detail 中服务端签发的 `workspace_id`，不能提交任意路径。
- 仅允许清理没有 active Run 的 completed/cancelled Task。
- 服务端在执行前持有 Task state mutation lock，重新确认 Task 仍为终态、目录仍在登记表中，再解析目录；只接受配置 Workspace root 下的真实直接子目录，root 本身、root 外路径、符号链接和服务当前工作目录均拒绝。
- Status 手动删除和定时回收调用同一套 TaskService finalizer 和锁。只有显式登记在 `external_resources[]` 的类型化资源才触发 Docker finalizer；文件名、目录名和 repository 名不能创建资源所有权。Docker 不可用时保留资源记录与 Workspace，并写入稳定失败签名和持久化退避。完整契约见 [Task external resource lifecycle](task-external-resource-lifecycle.md)。
- 已登记目录即使已经不存在也保持删除资格；重复调用返回成功并标记 `already_absent=true`，不会把幂等重试误报为冲突。
- 删除结果写入 Task audit event；`read-only` serve mode 统一拒绝。

## Public Projection

允许：

- safe Target key/hash、标题和 provider label
- Task id、`current_run_id`、`latest_run_id`、Run sequence、状态、时间、safe agent name
- Run 启动前的当前准备操作、实时/最终准备耗时、重试次数和 safe transport detail
- `actions`、`safe_actions`、`inspect_actions`
- safe lifecycle/blocker/action summary
- opaque safe Artifact ref
- Task detail 中显式建模的 `workspace_locations`，包括该 Task 工作目录的绝对 `location`

禁止：

- `task_dir`、`run_dir`、log 路径，以及 `workspace_locations[].location` 之外的任意 Workspace 绝对路径
- native AgentSession id/file
- private resume handle value
- cross-agent source ref
- raw payload、provider token、reply token、prompt/history
- process command、argv、env、pid/pgid

Public Artifact endpoint 只解析经过授权的 safe ref。它拒绝 `payload.json`、`meta.json`、`run-context.json`、`prompt.txt`、`task-state.json`、`task-events.jsonl` 和 runtime logs，并在返回文本前执行 redaction。

## Server 边界

`/server` 和 local-admin CLI 才能展示或操作：

- jarvis-box 服务、内部 server loop、部署和主机健康
- jarvis-box service/runtime logs；不包含宿主 scheduler 或 Runtime Foundation logs
- runtime agent 安装与配置诊断
- `workspace_locations` 契约之外的文件系统路径、cleanup dry-run、reap 和其他主机维护

服务重启会恢复服务能力、RuntimeAgentRouter cooldown timer，并自动重放已经持久化的 terminalization intent；它不会自动 Continue、重新启动 agent，或把失联 Run 当成成功。执行态恢复仍由用户选择 Continue/Cancel。

## 安全与审计

- `/status` 必须部署在可信团队边界；更强身份认证由反向代理或上游网关提供。
- lifecycle mutation 前先做 public visibility 和 action policy 检查；工作目录清理按终态和目录边界检查。
- response 再经过 public projection，不能因 mutation 暴露私有路径。
- audit event 至少记录 operation、Task、Run（如有）、actor/reason、结果和时间。

## 历史任务取代状态

Task 的持久化 `status`、`phase` 和失败原因属于审计记录，不会因后续任务成功而改写。状态 API 会在存在可靠闭环证据时额外返回：

- `effective_status=superseded`
- `monitor_status=superseded`
- `next_action=none`
- `superseded_by=<后继 Task ID>`
- `supersession_evidence=<lineage 字段或 operator-reconcile>`

此类 Task 不计入 `needs-attention`，也不允许执行 Continue 或 Cancel。详情仍保留原始失败原因，并显示“历史任务已被后续成功任务取代，无需处理”。

系统只接受显式任务关系作为证据，包括 `supersedes_task_id`、`source_task_id`、`parent_task_id`、`trigger_task_id`，或操作人员通过 `jarvis-box tasks supersede <旧 Task> --by <成功 Task>` 建立的关系。仅 subject 相同不会触发取代。
