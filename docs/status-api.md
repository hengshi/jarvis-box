# Status API

`/status` 是 Jarvis Box 唯一的人类界面，工作状态与系统操作共用同一可信团队边界。Jarvis Box 不为人类观看者定义角色，也不根据 `RemoteAddr` 切换权限；反向代理或上游网关负责需要的身份认证。

## Status 读模型

`GET /status/api/work-items` 返回：

- `items` / `count`：当前分页窗口。
- `total` / `counts`：整个 Status task projection 的统计，不受分页 `limit` 影响。
- 可选 `provider=gitlab|github|jira|feishu-project|im` 在分页前筛选 Task 的规范化来源；`lark`、`wecom`、`dingtalk`、`uvim` 等消息来源归入 `im`。response 的 `provider` 返回实际筛选，未筛选时为 `all`。
- 分页游标绑定生成它的 Provider 范围；游标不能跨 Provider 重用，避免页间混入其他来源。
- 每个 item 的 `provider` 是 Task subject、run context 或 source URL 的保守规范化投影，不改变外部 Provider 的权威对象。
- 每个 item 的 `status_group` 是服务端确定的页面筛选分组，取值为 `doing`、`needs-human`、`failed`、`completed` 或 `all`；Status 页面不得从状态文本重复推断分组。

分组时 lifecycle 事实优先于 feed kind：`waiting`、`stopped` 和 `needs-attention` 进入 `needs-human`，失败终态进入 `failed`，`completed` 和 `cancelled` 进入 `completed`；`progress_checkpoint` 等 kind 不得把这些状态重新归入 `doing`。历史持久化状态 `failed-terminal` 和 `retry-exhausted` 在读取时兼容投影为 `needs-attention`，仍按失败终态分组，不会被旧的 `monitor_status=active` 覆盖。

`GET /status/api/tasks` 和单 Task detail 返回 Status task projection。默认读路径可以读取 Task state、bounded Artifact metadata，以及 Runner-owned RunTrace 中当前 Run 的 bounded、redacted Run 输入。Run 输入是真正交给 runtime agent 的当次指令：人机会话可以是用户原文，workflow lane 可以包含服务端生成的契约、运行上下文和主机路径。它不得包含可用 credential、private resume handle 或 raw provider secret，也不得从 `prompt.txt`、native AgentSession 或跨 Run history 补齐。

单 Task 查询接受 Task id、当前/最新 Run id，也接受仍保留 `run-state.json` 的历史 Run id。使用 Run id 查询时返回其所属 Task；Run id 不会被当成 Task identity。

单 Task detail 的 `workspace_locations` 是唯一个结构化工作区路径字段，用于建立 Task 与可清理工作目录的明确关联。每项只包含服务端生成的 opaque id、显示标签、绝对目录、存在状态、删除资格和原因；其他主机路径只能作为 bounded Run 输入文本或系统操作 response 出现，不得变成 Task 身份或 Workspace ownership 来源。

IM Agent Run 已成功但 final reply 未送达时，Task detail 保持 `status/monitor_status=completed`，并返回 `phase=writeback-failed`、`next_action=retry-writeback` 和 credential-safe `writeback_failure`。`writeback_failure` 包含 `kind=provider-delivery`、provider/connector、source、stage、attempts、category、retryable、delivery_state，以及可选的 upstream HTTP status、provider code、Retry-After 和 request id；不包含 raw provider body。此状态仍进入统一 Task/work-item projection，lifecycle stage/blocker 为 writeback；它不是新的任务类型，也不创建第四个生命周期操作。

Run 从被 claim 到 Agent 进程真正启动之间，Task detail 公开准备进度：`preparation_started_at`、`preparation_elapsed_ms`、`current_operation`、`current_operation_started_at`、`current_operation_elapsed_ms`、`current_operation_attempt`、`current_operation_max_attempts` 和 `current_operation_detail`。Status 页面必须优先显示当前操作、已耗时和重试次数，不能只显示笼统的“Run created”或“执行中”。准备成功、失败、取消或进入 recovery 时清空 `current_operation`，并把 `preparation_elapsed_ms` 冻结为最终耗时；历史 Task 没有这些字段时保持兼容。

长期在线约束：

- 首屏读取一次 list/work-items，后续通过一条 SSE 连接接收变化。
- 未变化的 SSE tick 不得全量扫描 `runs_dir`。
- 只对选中的 Task 读取 bounded event/log tail。
- Artifact 内容只在用户显式打开时读取。
- 多个浏览器标签共享服务端 projection/cache。

## GitLab / GitHub Provider-native Delivery Metrics 读模型

完整的查看、恢复和排障步骤见 [Delivery Metrics 历史基线操作手册](delivery-metrics.md)。Delivery Metrics 是 Status 服务维护的持久化读模型，不是 Task；`jarvis-box tasks list` 不会列出它。

`GET /status/api/value?provider=gitlab|github` 从所选 Provider 的已配置仓库生成 typed、只读的交付指标快照；缺省 Provider 为 `gitlab`。顶层 `configured` 表示该 Provider 是否配置了统计仓库。GitLab 与 GitHub 分别维护 snapshot、queue、evidence 和刷新状态，API 不返回跨 Provider 合计。

普通 GET 会读取持久化 snapshot、待分析队列和 cursor，并为未完成基线安排后台批次。追加 `refresh=1` 会跳过该 Provider 的 15 分钟 fresh TTL；已有刷新时，请求会加入同一轮刷新。fresh hit 仍会验证对应 CLI 的 authenticated principal，登录主体变化会使前一主体的 snapshot 和队列失效。

服务把派生状态写入 `JARVIS_STATE_DIR/status-value`。每批最多消费 5 个待分析 MR/PR，正常批次间隔 10 秒；429、5xx、timeout 和 Runtime Agent 失败会保留 pending 项并退避重试。MR/PR 的 SHA 或 `updated_at` 变化会产生新的证据键。Provider host、仓库集合、schema、判断合同或判断策略变化时，服务不会复用不兼容的 snapshot。

历史累计窗口从当前 `glab` 或 `gh` 登录账号的 `created_at` 开始，到本轮采集固定的 `generated_at` 为止。actor 直接读取对应 provider 的 authenticated-user endpoint，不需要独立账号环境变量，也不假设账号名是 `jarvis`。GitLab 优先使用带 `mergedAfter` / `mergedBefore` 的 GraphQL count fast path，并对 actor MR 取有界近期明细；不支持时才回退到稳定的 `merged_at` REST 排序分页。GitHub 使用 `UPDATED_AT DESC` GraphQL cursor 分页；两个 collector 都执行双边时间校验。按仓库返回：

- 窗口内全部已合并 MR/PR，以及其中由当前登录账号创建的 change request；
- 当前登录账号 MR/PR 中完全原样合并、自主修订后合并和发现人工纠正的数量；
- 判断未知、Provider 证据未知和待分析数量；
- 仓库覆盖率、证据覆盖率，以及每仓库最近 20 条当前登录账号 MR/PR 证据。

Provider merge 是 provider-native 工程交付 proxy，不代表终端客户业务验收。登录账号 change request 只按 author 识别，不涵盖该账号在其他作者 MR/PR 中的贡献；Jira、飞书项目、跨来源关联、聚合和去重均不在此 response 中。

后端从以下 classification 派生两个面向人的代码质量问题；Status UI 直接消费 typed count/rate：

- `unchanged`：change request 创建后未发现 source revision；
- `self-revised`：发生过 revision，但当前策略未判断为公开人类反馈促成；
- `human-corrected`：当前策略判断公开人类反馈促成了后续 revision；
- `judgment-unknown`：Provider evidence 完整，但 Runtime Agent 无法判断；
- `evidence-unknown`：Provider 时间线或参与者身份采集不完整；
- `pending`：历史基线尚待后台分析，不是最终分类。

`未发现人工纠正 = unchanged + self_revised`，`发现人工纠正 = human_corrected`。两者共享 `correction_known = unchanged + self_revised + human_corrected` 分母。`judgment_unknown`、`evidence_unknown` 和 `evidence_pending` 不进入比例分母。

首次建立历史基线时，merged counts 先显示，尚未分析的记录进入 `evidence_pending`。pending 归零前，聚合质量比例为 `null`。后台持续小批量补齐并复用落盘结果。

### 分析进度

快照存在或历史发现正在进行时，顶层 `analysis_progress` 返回：

- `phase`：`discovering_history`、`scheduled`、`collecting_evidence`、`judging`、`persisting`、`retry_wait` 或 `complete`；
- `agent`：当前 value-judge 使用的 Runtime Agent；
- `analyzed`、`pending`、`total`：历史基线数量；
- `current_batch`：当前批次的 Provider、仓库和 MR/PR number；
- `started_at`、`updated_at`、`next_attempt_at`：分析与重试时间；
- `last_error_code`：`judge_timeout`、`judge_failed`、`persistence_failed` 或 `evidence_retry`。

`current_batch` 和错误码是用户安全的 typed 状态。API 不返回 Agent 命令、stderr、Provider 正文或 state 路径。

### Response 状态

`status`、`freshness`、`completeness` 是三个独立维度：

- `status=ready|empty|unavailable`：是否有可展示快照，以及观察窗口内是否有 merged MR/PR。
- `freshness=fresh|stale|expired`：快照是否来自本轮或 24 小时内的上一次成功采集；stale response 同时返回从原 `generated_at` 计算的 `stale_age_seconds`。
- `completeness=complete|partial|unavailable`：配置范围是否全部可读；历史分析进度由 `evidence_pending` 独立表达。

所有结果使用 HTTP 200。客户端必须按 typed body 判断状态；`ok=false` 表示没有可用快照。partial 快照仍可展示已采集数量，但聚合 rate 为 `null`，不能把子集冒充完整范围。刷新失败时，24 小时内的旧快照以 `stale` 返回且保留原 `generated_at`；更旧快照不再返回。

```json
{
  "ok": true,
  "configured": true,
  "status": "ready",
  "freshness": "fresh",
  "completeness": "complete",
  "warnings": [],
  "analysis_progress": {
    "provider": "gitlab",
    "phase": "complete",
    "agent": "codex",
    "analyzed": 20,
    "pending": 0,
    "total": 20,
    "current_batch": [],
    "started_at": "2026-08-11T14:00:00Z",
    "updated_at": "2026-08-11T14:03:20Z"
  },
  "snapshot": {
    "schema_version": 6,
    "generated_at": "2026-08-11T14:00:00Z",
    "baseline_updated_at": "2026-08-11T14:03:20Z",
    "observed_from": "2026-06-09T07:34:53Z",
    "actor": {"username": "customer-agent", "name": "Customer Agent", "created_at": "2026-06-09T07:34:53Z"},
    "source": {"provider": "gitlab", "host": "gitlab.example.com"},
    "judgment": {"mode": "runtime-agent", "agent": "codex", "policy_digest": "sha256:..."},
    "repository_coverage": {"configured": 2, "succeeded": 2, "partial": 0, "failed": 0},
    "totals": {
      "merged_change_requests": 100,
      "actor_merged_change_requests": 20,
      "unchanged": 8,
      "self_revised": 7,
      "human_corrected": 2,
      "judgment_unknown": 2,
      "evidence_unknown": 1,
      "evidence_pending": 0,
      "correction_known": 17,
      "no_human_correction": 15,
      "no_human_correction_rate": 0.882353,
      "human_correction_rate": 0.117647,
      "evidence_coverage": 0.85
    },
    "repositories": []
  }
}
```

`evidence_coverage = correction_known / actor_merged_change_requests`。分母为零、聚合 completeness 为 partial，或 `evidence_pending > 0` 时 rate 返回 `null`。

响应只包含声明过的字段、固定 classification/evidence code 和用户安全 warning。MR/PR 外链只允许当前 provider host（含显式端口）上的 HTTPS URL；不符合时 URL 置空并返回 `unsafe_mr_url`。时间非法的 change request 以 `invalid_merged_at` 标记仓库 partial。raw provider object、note/review body、stderr、命令、token、环境变量和主机路径不得进入 delivery metrics projection。

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

后端 policy 是唯一授权来源。UI 和 CLI 不自行推断 enabled 状态。所有生命周期 mutation 写入 audit event；`read-only` serve mode 统一拒绝 public `/status` 生命周期 mutation。

### Start

`POST /status/api/tasks/{task_id}/start?reason=...`

- 选中的 Task 只是 source。
- 创建新 Task、新 AgentConversation 和首个 Run。
- 成功结果中的 `task_id` 是新 Task，`run_id` 是它的首个 Run；两者不能混用。
- 原 Task、Run 和 Artifact 不变。
- source active、`needs-attention`、完成但仍缺产物/写回、进程 ownership 未解决或 lane 不支持时返回 `409` 和明确 reason；先 Continue 或 Cancel 原 Task。

无 source 的原子 Start 使用 `POST /status/api/tasks/start`（人类 gateway，`jarvis-command`）或 loopback-only `POST /server/api/tasks/start`。JSON body 为 `prompt`、可选 `reason` 和 `lane`。服务端生成 Task identity、登记 intake、创建首 Run、启动并返回真实 Task/Run identities。Runtime Foundation 的 host scheduler 只从 loopback internal route 使用三个 allowlisted lane；`read-only` 权限由该路由与 lane 共同推导，普通 Task、远端调用和 provider lane不会继承。

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

GitLab/GitHub 的最终评论如果返回 HTTP 404，writeback owner 会用同一个 provider 身份检查目标项目或仓库。目标项目或仓库仍可访问，而 issue、MR 或 PR 已不存在时，Task 进入与 provider terminal event 相同的登记式清理流程；清理完成后状态为 `cancelled`，成功 Run 保持 `succeeded`。Workspace 或 typed external resource 仍需重试时，Status 显示 `finalizing / retry-finalization`，并保留 `terminalization_intent`；恢复器完成清理后才提交取消终态。项目/仓库不可访问、鉴权失败或配置错误仍显示普通 writeback failure，不会被转换成取消。

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

## Status task projection

允许：

- safe Target key/hash、标题和 provider label
- Task id、`current_run_id`、`latest_run_id`、Run sequence、状态、时间、safe agent name
- Run 启动前的当前准备操作、实时/最终准备耗时、重试次数和 safe transport detail
- Runner-owned RunTrace 中当前 Run 的 bounded、redacted Run 输入；该文本可以包含工作流契约、上下文和主机路径
- `actions`、`safe_actions`、`inspect_actions`
- safe lifecycle/blocker/action summary
- opaque safe Artifact ref
- Task detail 中显式建模的 `workspace_locations`，包括该 Task 工作目录的绝对 `location`

禁止：

- 作为结构化字段的 `task_dir`、`run_dir`、log 路径，以及 `workspace_locations[].location` 之外的任意 Workspace 绝对路径
- native AgentSession id/file
- private resume handle value
- cross-agent source ref
- raw payload、provider token、reply token、`prompt.txt` 原文或跨 Run prompt/history
- process command、argv、env、pid/pgid

Status Artifact endpoint 只解析经过授权的 safe ref。它拒绝 `payload.json`、`meta.json`、`run-context.json`、`prompt.txt`、`run-trace.jsonl`、`task-state.json`、`task-events.jsonl` 和 runtime logs，并在返回文本前执行 redaction。RunTrace 只能通过 Status timeline 的 bounded/redacted 投影读取，不能通过 base64 封装绕过文本 redaction。

## 系统操作 API

`/status/api/system/*` 为 topbar 系统操作面板提供：

- `GET overview|agents|doctor|crons`：实例、Agent、诊断、内部轮询与已脱敏配置；
- `POST agents/current`、`POST|DELETE agents/scopes/{scope}`：默认 Agent 和 lane scope；
- `POST chatbridge/reset`：重置 ChatBridge 连接；
- `POST tasks/clean`：按 dry-run、终态、lifecycle lock 和 disposal certificate 清理 Task Artifact；
- `POST tasks/start`：原子启动显式 operator prompt。

这些 endpoint 不再根据 loopback 切换人类权限。每个 mutation 仍执行输入校验、业务 owner 和 audit 契约；`read-only` 拒绝 Agent 配置、ChatBridge reset、operator prompt 和实际 clean，但允许 `POST tasks/clean?dry_run=1` 返回候选项且不删除数据。系统 response 可以展示当前主机路径和经脱敏的运行配置，但不得返回 credential、private resume handle 或 raw provider payload。

系统操作 UI 必须把这些 endpoint 解释成用户任务，而不是原样暴露 API 名称。默认 Agent 和 scope response 的成功只证明未来路由配置已保存，不代表 active Run 已切换；ChatBridge reset 的成功要继续以重新读取的 running/provider connected 状态为证据；operator prompt 的 `result.task_id` / `result.run_id` 是进入 Status 工作项跟踪的凭据；clean response 的 `status=dry-run|cleaned|deferred|error` 必须被汇总并保留逐项原因。

`GET|HEAD /server` 使用 permanent redirect 转到 `/status`。旧的人类 `/server/api/*` endpoint 不做 POST redirect；`POST /server/api/tasks/start` 是 loopback-only prompt admission，scheduled authority 只由 internal route 与当前 lane allowlist 推导。

服务重启会恢复服务能力、RuntimeAgentRouter cooldown timer，并自动重放已经持久化的 terminalization intent；它不会自动 Continue、重新启动 agent，或把失联 Run 当成成功。执行态恢复仍由用户选择 Continue/Cancel。

## 安全与审计

- `/status` 必须部署在可信团队边界；更强身份认证和浏览器跨站策略由反向代理或上游网关提供。
- lifecycle mutation 前先做 action policy 检查；工作目录清理按终态、签发的 workspace id 和目录边界检查。
- Task/API response 继续使用明确投影，系统 response 继续执行 secret redaction；同权限不等于 credential 可见。
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
