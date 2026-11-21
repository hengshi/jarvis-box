# Status API

本文面向为 Jarvis Box 开发网页、自动化或外部集成的开发者。它说明 HTTP 接口、字段、读取版本、错误与重试方式；网页操作请读 [工作台使用说明](status-ui.md)，业务状态的定义见[执行模型](execution-model.md)。

`/status` 和 `/status/terminal` 使用同一服务和任务模型。接口应位于可信团队网络或访问网关之后：部署侧负责访问者认证，服务不会根据远端 IP 给观看者划分角色。文件内容与工作区浏览另有本机限制，见[安全与审计](#安全与审计)。

## 从一次读取开始

在有权访问的部署中，可以先读取任务列表并显式选择执行模型版本：

```bash
curl -H 'Accept: application/json; execution-model=2' \
  http://127.0.0.1:8787/status/api/tasks
```

将地址换成实际实例的受保护访问地址。部署网关要求的认证仍须随请求提供。

阅读后文前，区分几个贯穿接口的概念：

| 概念 | 客户端应怎样使用 |
| --- | --- |
| Task / Run | Task 是任务，Run 是其某次执行；不要把运行编号当成任务身份写回 |
| `lookup_id` | 服务返回的不透明任务定位符；按原样放入对应 URL，不自行拼接或解析 |
| `task_revision` | 单任务的读取版本；停止、清理和恢复交付使用所选版本，普通新指令不因版本变化拒收 |
| `task_view_revision` | 多任务目录观察的版本；与单任务版本用途不同 |
| `actions` | 当前允许的操作及条件；不从显示状态或错误文字推断权限 |
| `cursor` | 绑定查询和窗口的不透明翻页位置；原样回传，不用于另一查询 |

只读请求发生版本冲突时，重新读取所选任务再有界重试；修改请求不能自动重放。任务的执行结果、消息是否送达、数据能否读取是不同事实，不能从一个字段推断另一个。

JSON 错误响应保留 HTTP 状态和机器可读的 `error`。使用 `detail`、任务版本、Run 或收据标识核对出错的操作。可选的 `next_step` 提供排障检查，客户端仍以 HTTP 状态、错误码和已有收据判断是否处理或重试。有 `Retry-After` 时，按该响应头决定何时再次读取。

## 按需要查阅

| 目的 | 章节 |
| --- | --- |
| 选择版本、解释任务状态 | [执行模型版本](#执行模型版本) |
| 读取任务、结果、文件及公开字段 | [Status 读模型](#status-读模型)、[任务投影](#status-task-projection) |
| 做任务选择器和连续会话 | [终端目录与会话](#终端-task-目录与连续会话) |
| 发起、继续、停止或恢复交付 | [生命周期操作](#三个生命周期操作) |
| 查询代码交付与账号活动 | [代码交付指标](#gitlab--github-provider-native-delivery-metrics-读模型) |
| 读取系统设置、额度、更新与授权 | [系统设置 API](#系统设置-api)、[软件更新](#软件更新)、[授权检查](#授权检查) |

## 执行模型版本

Status API 默认使用已发布的执行模型版本 1。新客户端使用 `Accept: application/json; execution-model=2`，或查询参数 `execution_model=2`；SSE 使用同一查询参数。响应包含 `execution_model_version` 与 `X-Execution-Model`，按 Accept 区分缓存；冲突或不支持的版本返回 400。事件失效摘要按协议版本区分，Task/Run 身份和业务 revision 不因序列化版本改变。

版本 2 的 Task 状态为 `running`、`completed`、`failed`、`cancelled`，分组使用同一名称，只读历史额外使用 `historical`。Task 不设置 waiting：准入、准备与执行恢复属于 running 阶段；业务 blocked/needs-input、已送达问题或投递恢复不改变执行成功且输出有效的 completed。failed 仅表达执行或输出失败，不表示管理员需要操作。读取不完整的条目返回 `status=null`、`status_group=null`、`projection_availability=unavailable`，不虚构失败或人工责任，所有修改动作禁用。

版本 1 仅映射已封存的执行状态字段：尚无 Run 的机器准入、准备使用 accepted，已有 Run 的机器准备、执行恢复及真实执行或输出校验失败使用 needs-attention，运行收尾使用 finalizing，取消仍属于 completed 分组。它与版本 2 共享同一投影、计数、动作授权和 Run 事实，不保留旧状态机。成功执行且输出有效的业务结果，包括 blocked/needs-input 和已送达问题，在默认版本 1 中同样为 completed；业务卡点不重新映射成 Task 未完成。问题事实仍可从 user_input_wait 读取，业务结果保留在原 Run 产物中。两个版本的 SSE 都只传失效通知，客户端随后读取对应版本快照，不从事件推导另一套 Task 状态。

## Status 读模型

Task 的可选 `context_summary` 只返回 `source`、`status`、`rendered_count`、`has_more`，表示本轮实际带入的聊天材料及是否仍有更多材料。完整覆盖范围和失败原因保留在本轮材料说明中；摘要不返回原文、身份、查询条件、资源句柄或路径，也不授予历史读取权限。

### IM 问题与卡片摘要

Task 的可选 `interaction` 在公开列表、详情和 SSE 中仅返回 `task_revision`、`run_id`、`phase`、`question_delivery_state`。可选 `interaction_presentation` 仅返回已确认消息数量 `confirmed_count`、最近关闭更新结果 `last_update_state` 和待更新布尔值 `update_pending`；更新结果为 `delivered`、`not_attempted`、`failed_definite` 或 `unknown`，不改变 Task 状态。问题正文、选项、答案、恢复指令、opaque handle、原生消息 ID 和更新 operation ID 均不出现在公共摘要。

经既有系统认证的 `GET /status/api/system/tasks/<lookup>/interaction` 返回当前未决问题的只读详情：Task revision、问题身份 `question_id`、所属 `source_run_id`、投递状态、是否准备原生卡片、可用时的卡片操作期限 `card_expires_at`、prompt/help/options 和自由文字策略。问题仍由原请求人在原 IM 会话回答。不存在或已经被后续运行关闭的问题返回 404；读取期间 revision 变化返回 409。公共同路径返回 404。这个端点不签发按钮、答案或 Continue 权限；系统访问权、Task 已 completed、可见标题或普通会话 Continue 都不替代原请求人的 IM actor/target 核验。已启用的 `actions.continue` 仍可按普通会话规则接收新指令，但该请求不是网页答题、不会带入 QuestionID/答案或创建 QuestionResolution；其不兼容后继 Run 会使原问题过时。

### 发布与读取

服务共享一份由严格 Catalog 和唯一 TaskView/WorkItem projector 产生的内存读模型。Task 提交通知按 250 毫秒合并，只重读已知变更 Task；完整校准每 10 秒检查跨进程写入和新增注册，慢轮次之间保留间隔。历史台账指标由独立后台读取更新。HTTP 摘要、分页查询和 SSE 读取已发布结果，不等待扫描、台账或 Provider 采集，也不按浏览器数量创建采集器。

首次构建返回 `ok=false,status=preparing`；构建失败且没有结果时为 `unavailable`。已有结果遇到刷新或故障继续可读，并以 `freshness=stale` 标记，不能将未知内容替换成空列表或零指标。`built_at` 是本次发布的构建时间，`last_complete_reconcile_at` 是最近完整校准时间，`publication_revision` 表示对当前执行模型版本可见的发布内容。

派生读模型没有新的磁盘格式，不拥有状态、调度或操作权限。严格 Catalog 的缓存命中仍在 lifecycle lock 内比较源内容和 Run 成员；revision、mtime、TTL 和文件通知都不足以证明源未变。不可读条目保留不可用投影；全局身份冲突或不支持的 schema 阻止新发布。执行与修改始终回到原有严格 owner。

### 工作台分页查询

`GET /status/api/work-items/query` 是工作台列表入口，使用以下参数：

| 参数 | 含义 |
| --- | --- |
| `provider` | 已注册来源；省略表示全部来源，消息渠道归入 `im` |
| `keyword` | 在完整来源集合中搜索全文、Target、Task/Run 编号；完整身份先精确解析，再应用筛选 |
| `requester` | 按完整请求人展示名筛选 |
| `limit` | 默认 50，最大 100；实际窗口还受响应字节上限限制 |
| `cursor` | 原样传回的上一页或下一页游标，不可解析或修改 |
| `anchor` | 无游标重读时定位原工作项，找不到时 `anchor_missing=true` |
| `focus` | 所选 opaque Task lookup；可返回 `focus_revision` 提示，既不注册订阅也不授权操作 |
| `related_to` | opaque Task lookup；分页返回同一 Target 下的 Task 摘要，不与关键词或请求人组合 |

每个 `items[]` 只携带有界标题预览、身份、状态、分组、时间、来源及任务数量，不内嵌 Run、相关 Task 全图、文件、effect 或 action policy。标题预览最多 512 字符，`title_truncated` 表示需选中后读取原文。搜索仍使用完整标题及保留的历史 Run 编号。分组顺序优先执行中和待处理工作，同组按 canonical 业务活动顺序排列；历史增加不能截断未结束工作。

`server` 返回 build、当前支持的智能体名称和可选授权到期提醒，不在列表读取中探测版本或额度。response 包含 `count`、匹配总数 `total`、七组数量 `groups`、窗口位置 `begin/end`、`query_snapshot`、`previous_cursor/next_cursor`、`task_view_revision`、机器级 `metrics` 和上述发布信息。游标固定筛选、排序、执行模型版本与当轮列表；后台更新不改变正在翻阅的窗口。`freshness=stale` 也表示固定窗口落后于当前发布。`exact_match=true` 表示完整 Task/Run 编号命中唯一工作项；身份歧义返回 400，筛选排除精确 owner 时不返回相似编号。

单响应最多 100 KiB；单条过大或无法安全形成有界响应时返回 503。服务最多保留 64 份、估算 64 MiB 的查询快照，单份最长两分钟；最多两个不同查询同时构建，同一查询合并。容量忙返回 429 和 `Retry-After`；游标伪造或筛选不符返回 400，过期、服务重启或回收返回 `409 query_snapshot_expired`。客户端收到 409 后按原筛选和阅读锚点重建窗口，不能无限重试旧游标。

`GET /status/api/work-items/requesters` 从完整已发布索引产生请求人选项，支持 `provider`、名称子串 `name` 和不透明 `cursor`，每次最多 50 项。返回 `items[{name,count}]`、`total`、`query_name` 和前后游标；选项按数量及名称稳定排列，不受当前列表窗口限制。来源索引变化使选项游标返回 409，客户端重新读取当前名称查询。

### 兼容完整读取与指标

完整读取兼容入口会同步校验已登记 Task 的严格 Catalog，并读取本机工作台账；它们不提供工作台摘要、分页查询和事件流的不等待扫描保证，也不从未登记的运行目录推断 Task。

`GET /status/api/ledger` 提供本机工作台账的分页读取。`kind=accepted`、`started`、`completed`
分别选择受理、运行启动和完成事件，`limit` 控制每页窗口。response 包含 `ok`、`events`、
`has_more`、`next_before` 和读取时间 `ts`。继续读取时把 `next_before` 原样作为 `before`
参数传入，直到 `has_more=false`；游标是不透明值，不代表事件时间或业务身份。
事件包含 `event_id`、`kind`、`ts` 及相应观察字段；完成事件中的有效
`detail.runtime_duration_ms` 是已记录运行耗时，缺失不表示零。台账属于保留的历史观察，
其受理、启动和完成条数不必等于当前仍保留的 Task/Run 数。

`GET /status/api/work-items` 一次返回所选来源的全部工作项：

- `items`：所选来源的完整工作项集合。
- 可选 `include_tasks=0` 省略与 `items[].related_tasks` 重复的顶层 `tasks` 列表；默认仍返回 `tasks`，其他字段与 Catalog 版本语义不变。此兼容入口不受新分页窗口限制。
- `count` / `total`：该集合的工作项总数，与 `items` 长度一致。
- 可选 `provider` 筛选 Task 的规范化来源。支持值由服务端 provider 注册信息定义，与页面来源选项一致；包括 `gitlab`、`github`、`jira`、`feishu-project`、`tapd`、`zentao`、`yunxiao-projex`、`yunxiao-codeup`、`im` 和 `jarvis-box`，未注册的筛选值返回 HTTP 400；`lark`、`wecom`、`dingtalk`、`uvim` 等消息来源归入 `im`。response 的 `provider` 返回实际筛选，未筛选时为 `all`。
- `metrics.historical_accepted_count`、`metrics.started_run_count`、`metrics.active_task_count`、`metrics.task_run_trend` 和 `metrics.hour_of_day_distribution` 是本机指标；`provider` 筛选只改变工作项列表及其数量，不得改变这些机器级指标。`recorded_task_count` / `recorded_run_count` 只表示当前保留记录。
- 每个 item 的 `provider` 是 Task subject、run context 或 source URL 的保守规范化投影，不改变外部 Provider 的权威对象。
- IM item 可返回 `requester_display_name` 和 `conversation_display_name`。它们是入站消息时的可选展示快照，用于 Status 文案、搜索和按发起人筛选；缺失时继续使用 provider-scoped sender ID / Task ID，且永远不替代 Target、ACL、排重或回复路由使用的稳定 ID。
- 每个 item 的 `status_group` 来自同一 TaskView，状态拼写和不可用条目的表示遵循[执行模型版本](#执行模型版本)。`all` 仅表示筛选范围，客户端不得从状态或错误文案重算分组。
- `metrics.task_run_trend` 返回从首条运行记录到统计时区今日、按自然日聚合的 Agent Run started 趋势，来源为工作台账中的 `kind=started` 追加事件；无运行日期补零。该趋势是机器级口径，`provider` 筛选只影响 work items，不改变 trend 统计。
- `metrics.task_run_trend.runtime_duration_ms` 返回本机工作台账中已完成运行记录的耗时合计，来源为 `kind=completed` 事件携带的运行耗时字段。它是本机工作台账可观测口径，不代表机器在线时间，也不等同于当前保留 Task state 的 Agent 执行时长。
- `metrics.hour_of_day_distribution` 返回按小时的 Run 启动分布，使用本机工作台账的 `kind=started` 事实和经验证的覆盖起点；它与按日趋势共用请求的统计时区；浏览器传入自身的 IANA 时区，`provider` 筛选不改变机器级统计。字段和可用性语义见[按小时 Run 启动分布](#按小时-run-启动分布)。
- 历史受理、累计启动数和已完成耗时分别返回 `historical_accepted_metric`、`started_run_metric`、`completed_runtime_metric`，包含 `status`、`value` 和 `as_of`。账本不可完整读取时，Task 列表仍返回 HTTP 200；账本指标为 `unavailable`，数值兼容字段与 `as_of` 为 `null`，不把未知显示成零。当前没有持久化历史 rollup 回退。
- 完整可读账本中，部分完成记录缺少有效耗时时，`completed_runtime_metric` 返回 `status=partial`、已记录耗时合计和本次 `as_of`；两个耗时数值兼容字段返回相同下限。该值不能作为完整精确合计，页面以 `≥` 展示。全部完成记录都缺少有效耗时则为 `unavailable`；无完成记录为 `empty`、值为 0。单条缺少耗时不影响其他指标，也不触发历史任务重跑。
- `metrics.run_duration_statistics` 返回已结束 Run 的平均耗时、中位耗时、有效样本数、缺失耗时数及按 lane 拆分的同口径统计，详见[运行耗时统计](#运行耗时统计)。

分组、处理责任和完成条件由[执行模型](execution-model.md)统一决定。单条持久记录损坏时保留该条不可用投影，不暴露未经证明的 Run/Session，不提供修改动作，健康任务继续可读；不支持的存储 schema 拒绝整个读取。磁盘等待属于机器等待，取消不计成功交付，历史失败 Run 不覆盖后继运行结果；这些事实按请求的执行模型版本序列化。

`GET /status/api/tasks` 和单 Task detail 返回 Status task projection。默认读路径只读取 Task state 和 bounded Artifact metadata；单 Run progress 只在 exact `TaskView.runs[].prompt_artifact_id` 指向 canonical `prompt.txt` 时投影其 bounded、redacted Run 输入，并把 Runner-owned RunTrace 作为进程输出时间线。Run 输入是真正交给 runtime agent 的当次指令：人机会话可以是用户原文，workflow lane 可以包含服务端生成的契约、运行上下文和主机路径。它不得包含可用 credential、private resume handle 或 raw provider secret，也不得从 native AgentSession 或跨 Run history 补齐。

RunTrace 和结果产物的公开输出会脱敏原生会话、线程和恢复句柄以及凭证字段；原生 hook 或工具结果将 JSON 或逐行 JSON 嵌在字符串中时，内部字段同样脱敏。普通业务 ID（包括 UUID）和非敏感正文保留，不仅凭 UUID 格式判断敏感内容，私有原始日志不因此改写。

`GET /status/api/tasks/{task_id}/result` 读取所选 Run 的结果文件：MR/PR 评审读取已冻结的发布正文，其他运行读取 `result.json`，只读历史运行读取已登记的同名产物。没有该产物时返回 `503 task-result-unavailable`，不改变 Task 或 Run 的执行结果。普通聊天的最终文字通过 `progress` 输出时间线查看，其他产物通过文件接口查看；系统不把最后一条聊天文字伪装成结果文件。

单 Task 查询接受 Task id、当前/最新 Run id，也接受仍保留 `run-state.json` 的历史 Run id。使用 Run id 查询时返回其所属 Task；Run id 不会被当成 Task identity。

精确搜索先通过不绑定目录版本的严格单 Task GET 解析输入编号，取得当前 opaque lookup 与 Task 版本，再对详情和产物使用该 Task 的版本。解析不依赖旧目录快照；响应到达时搜索条件、来源或页面选择已改变则丢弃。精确搜索只改变 Task/Run 的详情焦点，不新增工作项或改变列表统计。页面中的精确搜索受当前来源筛选约束；编号所属来源不匹配时显示原因，不切换到该任务。

`GET /status/api/related-tasks?task_id={lookup_id}` 返回同一不可变 Target 的相关 TaskView，以及 `count` 和 `total`；可选 `limit` 默认20、最大50。使用 TaskView 的 opaque `lookup_id`，可同时传入已冻结的 `task_view_revision`。此列表与工作项内嵌 `related_tasks` 消费同一投影，不从相同标题或项目编号猜测归属。

Catalog 返回 `task_view_revision`，`snapshot_hash` 使用同一版本。单 Task、progress、result、events/logs 和 Artifact root/list/content GET 可使用 opaque `lookup_id` 配合该 Task 的 `task_revision`，成功与冲突 JSON 回显 `task_revision`；所选 Task 变化返回 `409 task_revision_changed`。其他 Task 更新不使该读取失效。related Tasks 等聚合读取继续携带 `task_view_revision`；只使用该参数的既有单 Task GET 仍严格校验整个 Catalog，不匹配返回 `409 task_view_revision_changed` 和当前版本。单 Task GET 同时提供两种版本时以 `task_revision` 为准；无效 Task 版本或非 opaque selector 返回 HTTP 400。浏览器仅对只读冲突刷新 Catalog 并重试一次，丢弃旧选择或错版本响应；停止、清理、投递裁定以及不含新输入的恢复操作仍校验请求携带的版本：旧 `task_view_revision` 返回 `409 task_view_revision_changed`，旧 `task_revision` 返回 `409 task_revision_changed`。普通 Continue 新指令只绑定不可变 Task 身份，不以这两种展示版本拒收。所有修改请求都不自动重放。除首次精确编号解析外，没有版本参数的读取用于非 Catalog 客户端。

工作台对上述只读 Task GET 显式使用 `read_model=published`，并提供 opaque lookup 与 `task_revision`：所选 Task 仍从严格 aggregate 读取，其位置与跨 Task overlay 使用最近一次完整成功 Catalog 的紧凑观察。观察为每个可定位的 Task 保留登记位置、revision 和关系摘要，目录增长或投影缓存淘汰不使已发布的会话定位和订阅失效。响应附 `X-Status-Peer-Revision` 与 `X-Status-Peer-As-Of`，表示其他 Task 事实的观察版本和时间，不声称所有 Task 在请求时同步读取。观察缺失返回 503，不退回全局扫描。省略此参数的既有读取保持完整严格 Catalog 语义；POST 不接受此模式，任何 action、Continue、Cancel 和清理都重新严格校验。

单 Task 详情包含同一版本的任务及工作区信息。组装期间所选 Task 变化时，固定 Task/Catalog 版本的请求返回相应 revision conflict；未固定版本的读取有界重读完整详情，不混合两个版本。持续变化或其他投影故障仍可返回不可用；读取重试不会重新提交任务动作。

同一选择的读取收到版本冲突，或成功响应到达时其版本已落后于浏览器通过并发读取取得的 Catalog，都共用一次刷新 Catalog、重试原请求的预算。focus Task、selected Run 或 UI generation 已变化时直接丢弃旧响应；不能把同一任务的版本推进误判为选择变化而静默停止更新。重试后仍过期时禁用所选任务操作，不自动跳到最新 Run。

HTTP 修改操作要求 TaskView 的 opaque `lookup_id`。CLI 的 `tasks start/continue/stop <task_id>` 会先读取严格 TaskView，冻结 `lookup_id`、`task_revision` 与操作所需 Run，再提交请求；普通 Continue 的新指令按该 Task 受理；停止、清理和恢复操作的所选归属变化时返回冲突，不重新选择另一个 Run。

单 Task detail 的 `workspace_locations` 是唯一个结构化工作区路径字段，用于建立 Task 与可清理工作目录的明确关联。每项只包含服务端生成的 opaque id、显示标签、绝对目录、存在状态、删除资格和原因；其他主机路径只能作为 bounded Run 输入文本或系统设置 response 出现，不得变成 Task 身份或 Workspace ownership 来源。

IM Agent Run 成功但 final reply 未送达时，Run 仍保持 `succeeded`；Task detail 从同一 exact Run typed effect receipt 投影 delivery 结果。Task 按执行结果保持 completed；definite `failed` 且 `retryable=true` 可由机器执行同 Run 有界发送重试，重试中、耗尽或失败均只影响独立交付事实；符合原回执策略时提供 `actions.retry_delivery.strategy=writeback`、`requires_input=false`；该 RetryDelivery 只恢复同一 Run 的 delivery effect，不创建新 Run、不读取公开 `reply-error.json` 授权重发。旧版本保存的 `chatbridge.reply / reply-handle-unavailable / not-attempted` 失败即使 `retryable=false`，也保留显式 writeback 恢复能力：原历史字段不改写，仍需同一 Run 的完整私有交付收据，实际发送前重新校验原回复权限。`unknown` 表示外部结果不可证明，系统不自动重发；对于普通发送的 unknown，policy 在 `actions.retry_delivery.attestations`（同时保留 `actions.continue.attestations` 协议字段）里列出 `delivered` / `not-delivered` 两个人工裁定，由人查证目标系统后经 attest-delivery 落成一条新的 effect attempt receipt。receipt 可包含 provider/connector、source、category、retryable、delivery_state、upstream HTTP status、provider code、Retry-After 和 request id 等脱敏字段；不包含 raw provider body。

普通 Task catalog、SSE 和 detail 只携带 `native_publication_indicator`：摘要状态、条目总数、已确认条目数和该投影 revision。存在该摘要的 Task 可通过受保护入口读取详情；是否有权读取仍由该入口验证。它不携带 batch id、ordinal、Agent manifest、operation key、随机 marker、原始 actor、目标 binding、仓库路径、source artifact/path/SHA、provider URL 或 provider evidence。既有 gateway-authenticated Status 读取面内的 `GET /status/api/system/tasks/{lookup_id}/native-publication` 使用相同 opaque selector、版本绑定与 strict aggregate 复核。可选 `run_id` 固定所选运行，省略时沿用产物读取的当前运行规则；没有该运行的 batch 返回 `404 native_publication_not_found`，不能替换成其他运行的成果。受保护 DTO 返回所属 `run_id`、最多 16 个当前条目及有界历史页：标题、逻辑名、规范化状态、claim 次数、safe reason、观察时间和已确认的目标 revision。只有与封存对象、目标和 provider 证明全等的已确认版本，才返回 `canonical_url`；Agent 提供的链接及无证明的同域 URL 不可用。其余私有计划字段不返回。 native 发布结果为 unknown 时不提供 RetryDelivery 或人工送达裁定；Status 只显示保守摘要，不能把部分确认当作全部发布完成，也不因详情读取启动后台 Observe。

历史 `history` 每页默认 16 条，`limit` 只能为 1–16；`history_count` 表示该运行的记录总数，非空 `next_cursor` 读取后续页。cursor 绑定完整 Task lookup、Run、Task revision 和页长；Task 变化或跨 Task/Run 使用返回 `409 task_revision_changed`，无效 cursor 或页长返回 `400 native_publication_page_invalid`。原生发布已全部确认的 IM Task 另有 `notice_delivery_state`，仅从相同 Run/batch 的独立通知回执投影；`pending` 表示尚无送达确认，不改变原生发布结果。读取和翻页不调用 provider、不发起 Observe、写回或 Agent。普通 `/status/api/tasks/{...}/native-publication` 一律返回 `404 native_publication_detail_not_public`。

附件已发出但超时未知时，Jarvis 在原 IM 会话询问是否收到；确认消息成功发送后，原交付回执继续保留未知结果，执行成功的 Task 保持 completed，不创建 Task 等待或管理员待办。明确收到只结算原 delivery receipt；明确未收到使用现有裁定与写回重试，不新建 Agent Run。附件超出渠道大小或图片尺寸限制时，原会话收到具体限制与交付位置询问，原交付回执保留附件限制原因。两者均不计入管理员需要处理数量。

原IM用户明确只缺未确认集合的一部分时，effect历史可包含`attestation=missing-attachments/v1`及`missing_attachments`文件名数组，表示只补这些文件、其余按原用户声明收到；它不等同于平台发送ACK。该选择保留在同一Run的裁定与交付历史中，内容再次核验后仅补缺少部分。Status的`attest-delivery`请求仍只接受policy列出的`delivered`/`not-delivered`，不从展示字段授予新发送权限，也不接受附件名单。

`runs[].failure` 保留启动失败原因与脱敏详情。尚未启动的 Run 不返回零值 `started_at`；客户端使用 `created_at` 展示创建时间，并标明“未启动”。typed `storage-wait` 为机器等待，磁盘恢复后自动启动并通知原 IM 用户；恢复仍使用同一个已准备 Run；旧运行的失败历史保留，已发布运行只按其既有恢复合同继续。

Execution model 要求 Run 从被 claim 到 Agent 进程真正启动之间公开
`preparation_started_at`、`preparation_elapsed_ms`、`current_operation`、
`current_operation_started_at`、`current_operation_elapsed_ms`、
`current_operation_attempt`、`current_operation_max_attempts` 和
`current_operation_detail`。TaskService 在 exact Run claim 中写入总准备起点，随后以同一
Task/Run fence 持久化 provider/run input、Agent runtime preparer 和 Agent dispatch
操作。工作区准备不在这个窗口里：Run 还没分配时做的物化（新建 Task 的准入路径）没有 Run
可挂，进展只体现为待准入状态，失败时停在 `workspace-materialization-wait` 按周期重试；
Run 已存在时（Continue 与 failover）物化在 claim 之后，`preparing-workspaces`、
`checking-out-workspace`、`refreshing-repo-cache`、`configuring-workspace-dependencies`
与其余阶段一样以同一 Task/Run fence 上报。读模型实时计算进行中的总耗时和操作耗时；Agent
启动、launch 失败、取消或 recovery 时冻结总耗时并清空当前操作。同一 Run 内 Workspace
clone 的瞬时重试、cache 回退以及 runtime preparer 的后续重试会在同一 Task event stream
留下 started、retrying 或 fallback 审计事件。
Status 只展示这些 typed progress 事实，不从 Run lifecycle、日志或错误文案合成操作和耗时。

### 实时通知与连接生命周期

空间状态页使用一条 `/status/api/events?execution_model=2` SSE 连接接收发布失效、系统与授权通知；设置面板复用它。通知提示客户端重新 GET 对应已发布内容，不携带全部 Task 图。心跳与每个订阅者的发送路径不扫描 Task 或台账。

上述全局事件流不登记每个观看者的焦点 Task。终端页面另使用所选任务的 `/status/api/tasks/{lookup_id}/watch`，以及任务选择器打开期间的 `/status/api/task-directory/watch`；两类连接的范围和上限见[终端接口](#终端会话与任务选择器)。旧工作项页面的焦点在浏览器本地管理：150 毫秒合并连续选择，取消过时请求，并按 Task、Run 与 UI generation 丢弃迟到结果。只对最终选中的 Task/Run 读取进展和输出；显式展开的 Task 读取其运行历史与目录，浏览器最多保留三个 Task 详情；文件内容只在显式打开时读取。

每个服务默认最多 320 条 Status SSE，可在[终端容量配置](configuration.md#终端容量)中调整，超出返回 503 和 `Retry-After`。单连接队列最多 32 条通知，溢出或写入超过十秒关闭连接；断开和服务停止释放订阅及队列。暂时断线由原生 EventSource 重连；HTTP 拒绝使其进入 CLOSED 时，页面使用唯一的有界退避计时器重试，隐藏或卸载同时取消。每次连接建立后重新读取列表发布、所选任务及漏斗摘要，补齐断线期间变化；协议不提供事件回放保证。页面隐藏或卸载关闭连接，恢复可见时重新连接和校准，不积累后台焦点或幽灵订阅。

授权面通过同一 SSE 连接的 `license` 事件更新。两个 Status SSE 端点的载荷均为 `license: {problem, expiry?}`，不包含安装、机器或授权身份字段表；连接建立、后台签到失败及每 15 秒心跳时读取本地快照，不扫描任务目录或访问授权服务。系统设置接到事件后通过 `GET /status/api/system/license` 重读完整授权面板，该读取不收集 Task 状态、不签到。页面只渲染服务端给出的结论，不从字段表重算授权。工作项首个响应的 `server.license_expiry` 同样承载可选顶栏提醒（`text`、`detail`、`level=warn|overdue` 和可选 RFC3339 `expires_at`），不依赖 SSE 可用。`expires_at` 是服务端已选定的到期时刻，浏览器只用它按自身时区展示提醒日期，不据此重新判定授权是否有效；API 时间保留原始时刻与时区信息。

### 本机指标时区

`GET /status/api/summary`、`/status/api/work-items/query`、`/status/api/events`、`/status/api/tasks`、`/status/api/work-items` 及对应的既有系统别名共用可选的 `timezone` 查询参数（IANA 时区名，例如 `America/Los_Angeles`）。网页始终发送浏览器的时区；`metrics.task_run_trend.timezone` 与 `metrics.hour_of_day_distribution.timezone` 回显同一有效时区。显式空值、重复参数、`Local` 或无效时区返回 HTTP 400，不静默改用服务器时区。未传参数的既有 API 调用保留服务进程时区语义。时区只影响统计日期与小时，不影响 Task/Run 状态、累计次数、运行耗时或 Provider 贡献日历的日期。

摘要与分页读取从已发布账本快照生成统计，不触发按请求的磁盘或 Task 全量扫描。`as_of` 保留快照读取前记录、成功验证后发布的观察边界，完整日边界也以此为准（见[执行模型](execution-model.md)）；后台观察跨过本时区午夜后，既有 SSE 心跳会通知页面重读，即使没有新启动记录。

### 运行耗时统计

`GET /status/api/tasks` 和 `GET /status/api/work-items` 的 `metrics.run_duration_statistics` 使用完整本机工作台账中的 `kind=completed` 记录。每条有效非负 `detail.runtime_duration_ms` 是一个 Run 样本，包括成功、失败、停止和取消；零耗时有效，进行中的运行不计入。同一 Task 的多次 Continue 分别计样本，两次运行之间的等待不计入。统计不受 Task 记录清理、来源筛选、运行趋势时间范围或异常高峰开关影响，也不剔除异常耗时。

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `status` | string | `ready`、`partial`、`empty` 或 `unavailable` |
| `sample_count` | number 或 null | 有效耗时样本数；完整可读账本中可以为 0 |
| `missing_duration_count` | number 或 null | 已结束但缺少有效耗时的记录数 |
| `mean_ms` | number 或 null | 有效耗时之和除以有效样本数，单位毫秒 |
| `median_ms` | number 或 null | 有效耗时排序后的中间值；偶数个样本取中间两值的平均值，单位毫秒 |
| `as_of` | RFC3339 时间或 null | 成功观察时间；`unavailable` 为 null |
| `lanes` | array | 各工作类型的统计，每项含 `lane` 和上述六个统计字段，不再嵌套 `lanes` |

平均值和中位数允许小数毫秒。每个 lane 独立判定可用性，总体按全部完成记录判定：

| 账本观察结果 | `status` | 数量字段 | `mean_ms` / `median_ms` | `as_of` |
| --- | --- | --- | --- | --- |
| 有有效样本且无缺失耗时 | `ready` | 已知数量 | 已知样本统计 | 观察时间 |
| 有有效样本且有缺失耗时 | `partial` | 已知数量 | 已知样本统计 | 观察时间 |
| 没有完成记录 | `empty` | 均为 0 | null | 观察时间 |
| 有完成记录但耗时均缺失 | `unavailable` | 样本数为 0，缺失数已知 | null | null |
| 账本不能完整读取 | `unavailable` | 均为 null | null | null |

`partial` 的平均值和中位数只描述已知样本，不能作为完整总体的下限，不使用 `≥`。无有效样本时页面显示 `—`，不把 null 转成零耗时。账本不能完整读取时 `lanes=[]`，Task 列表仍可正常返回。

`lanes` 只包含出现过完成记录的工作类型，按原始 lane 标识排序。新运行的启动、完成记录将 Task 的 lane 保存在 `detail.lane`。历史完成记录没有 lane 时使用 `lane=""`，页面显示“未记录工作类型”；这些记录的有效耗时仍计入总体与该行。缺少 lane 本身不使总体耗时统计成为 `partial`。历史行保持不变，不通过任务编号、名称或当前保留任务补猜归属。每个非空 lane 行同时显示中文名称与原始标识，单独展示缺失耗时数量。

### 按小时 Run 启动分布

上述读取的 `metrics.hour_of_day_distribution` 是本机 `Run` 启动量的独立统计，不是并发数、运行耗时或 CPU 负载。它只统计工作台账中 `kind=started` 的真实启动事实；同一 Task 的不同 Run 和真实再次启动都按既有启动事件语义分别计数，不按 Task 或 Run 去重。响应固定包含以下字段：

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `status` | string | `ready`、`empty` 或 `unavailable` |
| `source` | string | 固定为 `work-ledger:started` |
| `timezone` | string | 与每日趋势共用的有效统计时区，网页为浏览器 IANA 时区 |
| `as_of` | RFC3339 时间或 null | 最近一次成功观察时间；`unavailable` 为 null |
| `coverage_start` / `coverage_end` | ISO 日期或 null | 实际纳入统计的第一个/最后一个统计时区自然日；没有完整日或不可用时为 null |
| `sample_day_count` | number 或 null | 纳入的完整自然日数；`empty` 为 0，`unavailable` 为 null |
| `completeness` | string | `complete` 或 `unavailable`；`complete` 仅表示返回的覆盖日期区间由有效账本覆盖证据完整支持，不表示该区间之前的全部历史完整；不提供部分覆盖统计 |
| `reason` | string，可省略 | `unavailable` 的安全诊断码：`coverage_unknown`、`coverage_invalid`、`started_timestamp_invalid` 或 `timezone_unavailable` |
| `hours` | array | 固定按 `hour=0..23` 排序的 24 项；每项为 `{hour, mean, median}`，数值为 number 或 null。`mean`、`median` 是启动次数聚合，单位为“次”；`hour` 仅标识请求时区的本地小时区间，不表示运行耗时或速率单位 |

服务器从同一完整账本取得有效覆盖边界：不可变的服务启动 v1 标记，或者经严格校验的历史启动对账回执与该标记中较早的 UTC 时刻。历史回执只由 `jarvis-box metrics backfill` 的显式 `--coverage-from` 与 `--attest-complete` 建立；来源标签不进入本 API，也不证明目标或完整性。包含有效边界的统计时区当天和当前自然日都不参与统计；首个可计日期是边界后的下一个自然日，最后一个可计日期是观察时的昨日。每个完整日期都进入样本，即使整日没有启动，且每个日期的全部 24 小时都计入；因此 `ready` 可以包含全零的 24 个数值。早于有效边界的账本历史保留原样，可用于其原有的累计和每日趋势，却不能被补成零、推断成完整按小时历史或纳入本指标。

令 `C(d,h)` 为完整样本日 `d` 的 `[h:00,(h+1):00)` 当地时间内启动次数，`D` 为实际纳入日期集合。`mean(h) = sum(C(d,h)) / |D|`；`median(h)` 是全部 `C(d,h)` 的中位数，偶数样本取中间两个值的算术平均。数值不在 API 中预先取整，例如 `[0,2,10]` 得到 `mean=4`、`median=2`。浏览器显示服务端按其请求时区生成的桶，不从任务列表另行计算。夏令时重复的小时合计到同一个桶，缺失的小时为 0；每个完整自然日仍是一个样本。改变浏览器时区会重新投影按日与按小时统计，不改写 UTC 原始事实。

| 账本与覆盖观察结果 | `status` / `completeness` | 覆盖字段与小时值 | `as_of` |
| --- | --- | --- | --- |
| 有效覆盖边界，至少有一个完整日 | `ready` / `complete` | 实际日期、已知样本天数、24 个数值 | 观察时间 |
| 有效覆盖边界，但尚无完整日 | `empty` / `complete` | 日期为 null、样本天数 0、24 项数值均为 null | 观察时间 |
| v1 标记缺失、损坏或冲突；账本损坏；或 `started` 时间戳无法归桶 | `unavailable` / `unavailable` | 所有覆盖字段和小时数值为 null | null |

当前版本只统计有效覆盖边界之后的完整自然日。历史启动只能由受控 CLI 计划、应用和操作者完整区间裁定补入；Status 请求、浏览器和普通账本读取都不会创建、修复或扩大该范围。对账回执的前缀绑定或时间范围不再成立时，读取会丢弃该回执并退回仍有效的 v1 标记；有效 v1 标记本身足以继续提供按小时统计，而不是保留旧的更早覆盖日期。

## 终端 Task 目录与连续会话

Terminal 是独立页面，使用同一 Status API、SSE、严格 TaskView 和 TaskService。新目录及 conversation GET 明确协商执行模型 2，并使用 `read_model=published`；缺少版本返回 `400 terminal_execution_model_required`，读取模式缺失返回 `400 terminal_published_read_required`，非 GET 返回 405。旧接口默认版本与返回结构不变。

### 终端会话与任务选择器

终端使用执行模型版本 2，将当前会话、任务选择器和 Agent 选择能力分开读取。分工只影响公开视图、查询和订阅，不增加业务事实源；Task/Run、actions 和完整身份 fence 仍来自严格聚合、唯一 TaskView 与原有 TaskService。

| 接口 | 返回与读取范围 |
| --- | --- |
| `GET /status/api/agents/selection` | `supported_agents` 与 `default_agent`；只读取本地选择能力，不执行版本、额度或外部网络探测 |
| `GET /status/api/tasks/{lookup}/session-state` | `session_state`：当前 Task 的轻量状态、公开身份/revision、actions、计时与当前/最近 Run 摘要；无需先通过目录取得 revision |
| `GET /status/api/tasks/{lookup}/conversation` | 选定 Task 的有界正文、`page_runs`、前后游标与阅读锚点；必须校验 `task_revision`、完整注册及选定 Run |
| `GET /status/api/tasks/{lookup}/watch` | 单 Task 的 `session-invalidated`、`conversation-invalidated` 与必要系统失效通知；不传正文 |
| `GET /status/api/task-directory/groups` | 筛选后的归属组摘要、匹配数量、运行数、`activity_at`、组版本和快照坐标 |
| `GET /status/api/task-directory` | 指定归属组快照内的任务预览或有界范围；已有普通目录读取保持公开兼容合同 |
| `GET /status/api/task-directory/watch` | 目录版本的 `directory-invalidated` 通知；只在任务选择器打开时使用 |

目录与会话请求显式携带 `read_model=published`。`session-state` 直接核验 opaque Task lookup，读取所选 registration 及必要 peer 观察，不扫描目录引导当前会话，也不等待全部归属名称准备；不能绕过同 Target、取代和同组历史投影。可重复传递最多 16 个 `run_id` 获取阅读窗口中已有 Run 的状态摘要，每个 Run 仍须属于同一 Task 注册。完整历史、工作区和文件按需读取，不随状态更新反复返回完整 Run 图。

动作端点保持原有命令、策略和 fence。终端请求 `response_view=session` 时，返回 `result.session_state`、`result.run` 和 `result.affected_runs` 的紧凑回执；与状态 GET 共用同一公开字段选择。它不是完整 TaskView，也不改变默认公开回执。新建或 Continue 成功后可直接据已接受回执显示目标 Task/新 Run，读取尚未发布不得导致重复 POST。

归属组和组内 Task 按 `activity_at` 倒序，同时间按稳定身份排序。活动时间来自 Task 受理、Run 创建/开始/结束与交付 effect 完成时间；工作区维护、草稿编辑和概括标题更新不参与。组时间取匹配 Task 的最大值，未知保持未知。搜索先在完整索引中匹配完整的 `display_title`、保留的来源标题、归属或精确 Task/Run 编号，再分组和截取，不限于已读预览。

组查询支持 `provider`、`owner`、`owner_missing=1`、`keyword`、`running=1`，不兼容的组合拒绝。响应 `groups[]` 包含 `group_key`、`name`、`missing`、`task_count`、`history_count`、`total_rows`、`running_count`、`activity_at`、`revision`，并返回 `total_groups`、`total_tasks`、`query_snapshot`、`directory_revision`、`next_cursor` 和 `freshness`。真正缺失归属以 `missing=true` 区分，客户端显示“未记录归属（缺失）”；它与字面名称“未记录归属”是不同组，不能把占位文案作为真实 owner 值；历史条目计数不冒充可操作 Task 数量。

客户端按内部游标自动读取组摘要，界面不提供人工翻页。任务范围请求携带 `group_snapshot` 与 `group_key`，默认读取最新 10 条；完整浏览可使用 `offset` 与 `limit` 直接定位范围，或用 `anchor` 定位 Task。`limit` 最大 100，实际 `end` 仍受响应字节限制；`offset` 只能用于经验证的同 scope 快照，不能与 cursor/anchor 混用。普通目录、归属组、工作项和会话游标分命名空间，跨 scope、过期和超出范围不会退回其他查询。不同快照的范围不能拼接为同一连续列表。

会话与目录 SSE 都只发送失效提示。订阅先建立再取得初始观察；初始连接与重连要求重新核验相应可见状态，不把 Last-Event-ID 当持久事件重放保证。`conversation-invalidated` 只携带公开 `lookup_id`、`run_id`、`run_sequence` 与 `watermark`。通知合并后按既有正文尾部坐标读取；其他 Task 的变化不会使当前会话重读。peer 变化可能影响当前 actions 时仍须重新核验，不以自身 revision 未变化为由忽略。

目录通知只比较目录内容版本，不因历史统计、额度或图表变化刷新。版本 hash 按相等判断，不比较大小。客户端合并一次进行中的更新及一个待重读标记；换筛选取消旧 scope，迟到响应不能应用。ETag 可省去未变内容的传输，过期快照仍须重新取得，不能以 304 延长旧游标。

单响应继续限制为 100 KiB；目录查询沿用最多 2 个 builder、64 个快照、64 MiB 总预算和两分钟快照期限。正文读取默认最多同时接收 30 个请求，目录繁忙不占用这些名额。目录订阅默认最多 80 条，并计入服务的 SSE 总上限。容量不足保留普通查询与手动刷新。容量拒绝保留原有 HTTP 状态、错误码和 `Retry-After`。实时订阅和会话正文并发额度用尽时，响应还包含 `operation`、`stage`、`detail` 和提供只读检查的 `next_step`。订阅队列有界，慢读者溢出断开并在重连后重新核验。关闭选择器立即取消其请求、订阅、预取与列表渲染，当前会话独立继续工作；浏览器隐藏时暂停订阅，恢复后核验可见状态。

### Task 目录与任务归属

`GET /status/api/task-directory?execution_model=2&read_model=published` 从同一次后台 TaskView 发布结果读取每个 Task。它不使用 Target 的 PrimaryTask 代替全部会话，也不在 GET 扫描运行目录或请求平台身份。

| 查询参数 | 语义 |
| --- | --- |
| `provider` | 现有来源目录标识；IM 归入 `im` 并保留逐 Task 的 `im_provider` |
| `owner` | 完整任务归属展示名，精确字符串筛选；同名合组展示，不做跨平台身份匹配 |
| `owner_missing=1` | 无可核验归属的独立桶；与 `owner` 互斥，不占用真实中文姓名 |
| `keyword` | 完整 `display_title`、保留来源标题、来源与 Task / 保留 Run 编号搜索；精确编号歧义不选相似项 |
| `limit` | 默认 50，允许 1–100，响应仍受 100 KiB 限制 |
| `cursor` | 服务端签发的不透明分页游标，原样传回；不能用于旧 WorkItem 查询 |
| `anchor` | opaque Task lookup，初次重建窗口时定位；与 cursor 互斥 |

响应包含 `ok,status,execution_model_version,items,total_tasks,total_rows,query_snapshot,previous_cursor,next_cursor,begin,end,anchor_missing,freshness,built_at` 和安全的智能体名称目录。Task 与 `session_state` 的公开投影包含脱敏后的 `display_title` 及其 `display_title_source`，并提供可选的 `recap_status`。只有当前最新 Run 已取得有效标题才返回 `succeeded`。先前标题可以继续显示，字段省略时不要据此推断概括进度。已发布的历史结算仍可读取，旧记录只有开始事实时显示 `unknown`。源 Task 响应不内嵌概括任务的身份、输入或原生会话。概括任务本身作为普通 `task-recap` lane 任务出现在任务目录和执行指标中，尚无 Run 时只通过普通首次准入执行。目录 `row_kind=task` 的兼容字段 `title` 保留同一完整 `display_title`，视觉省略仅在客户端渲染时产生，旧版可选字段 `title_truncated` 仅在目录预览被单独裁剪时输出 `true`；当前直接提供完整展示值，因此省略该字段，既有消费者继续将省略视为 `false`。行还提供 `lookup_id,task_id,task_revision,revision,provider,im_provider,target_type,owner_display_name,owner_missing,requester_display_name,status,status_group,projection_availability,is_processing,created_at,updated_at,run_count` 及有限的来源展示信息，不内嵌 Run、动作、效果或文件树。客户端不得以 `title`、ID、执行 prompt 或状态另行选择标题。

已登记零 Run Task 是正常会话。`row_kind=pre_registration_history` 仅保留旧版元数据，`selectable=false,conversation_available=false`，无 lookup、Task revision 或假运行。无法核验身份时显示投影不可用，不将损坏记录伪装成登记前历史。

任务归属使用显式 `TaskView.owner_display_name`，缺省时只读解析经严格 Task / Run 身份核验的首次运行来源请求人，无法证明则 missing。分组键表示归属展示桶，相同名称跨来源合组，不是人员或账号 identity；归属名称与持久 Task / 来源账号身份的边界见[执行模型](execution-model.md)。原生 `requester_display_name` 独立保留，不从 assignee、commit author、当前浏览者、CLI 账号或身份匹配服务猜测。只读解析不改写旧 Task、Target、ACL 或交付地址。已核验结果（含 missing）按完整任务登记与运行代次复用；冷发布按可取消的有界工作单元继续，尚未完成时返回 preparing，不将未读取材料记作缺失。

`GET /status/api/task-directory/owners` 使用相同版本和读取模式，可携带 `provider,name,cursor`。每页最多 50 项，返回 `items[{name,task_count,missing:false}],missing_count,total_owner_groups,query_name,previous_cursor,next_cursor,freshness`。count 是 Task 数，不是旧 WorkItem 数；未记录桶单独返回。目录窗口之外的名称仍可检索。

目录游标绑定查询命名空间、筛选、页大小和不可变快照，在共享查询 owner 的 TTL / 容量内有效。旧快照可稳定翻页但标为 stale，不赋予动作权限；伪造与跨查询返回 400，失效返回 409，容量忙返回 429 并带 Retry-After。首次发布与投影不可用返回明确 503。分页快照及其查询索引共用全局查询容量，不按浏览器或用户另建缓存。

### Task 连续会话

`GET /status/api/tasks/{opaque_lookup}/conversation?execution_model=2&read_model=published&task_revision=...` 读取同一 Task 的保留会话；`limit` 默认 50、最多 100，编码响应最多 100 KiB。必须携带单 Task revision，其他 Task 更新不会改变此 fence。读取不触发 Agent、生命周期或交付。

无 cursor 时读取尾页，`entries` 内按执行顺序从旧到新排列。条目类别为 `run_boundary,input,message,output_gap`，每项有稳定的公开 `entry_id,run_id,run_sequence`；边界含智能体、状态与时间，正文只含安全投影后的公开字段。零输出 Run 仍有边界；未留存、损坏或超限材料以缺口解释，不从原生私有会话补齐。原生 stdout 语法可核验工具事实时，条目可附带 `tool={call_id,name,status,summary}`：`status` 为工具的 `running,completed,failed`，仅用于展示与同一 Run 内关联，不能授予生命周期或进程操作权限。调用编号最长256字节，超长时省略而不截断为另一个编号；名称最长80字节，摘要最多512个Unicode字符。字段与正文遵循同一脱敏规则，计入缓存和响应预算；未知语法或旧客户端不依赖该可选字段。

已登记的未启动失败 Run 即使没有 Agent trace，也可读取同一 Run 留存的公开输入产物。其尾页包含 `role=error` 的启动失败消息，详情取自 Run failure 的脱敏预览。

`page_runs` 说明本页条目的所属 Run，`previous_cursor,next_cursor` 用于连续翻页，`tail_cursor` 是签名的向前读取位置。`has_earlier,has_later,tail_complete` 描述读取水位，不是任务完成状态。`volatile_tail` 提供未完成消息的替换观察；完成条目的 `replaces_key` 将其升级为稳定记录，不重复追加。相同正文的两次合法执行保持两条，不能按正文哈希去重。

`cursor`、`resume_anchor` 与 `anchor_run_id` 互斥。Run 定位只接受本 Task 已登记的身份，不能改变动作来源。普通翻页游标有效期为两分钟，阅读锚点为 24 小时；二者均校验签名、有效期、完整 Task 登记与所属 Run，服务重启或只读历史选择失效仍可能使锚点不可用。Task revision 或目录变化返回 409，客户端先重新读取严格详情，再用当前阅读窗口对应方向的边缘锚点有界恢复；锚点不可核验时保留原位置并说明原因，由用户明确选择回到最新。POST 不因此自动重放。

保留的输入与输出正文在完整可安全解析与脱敏后，按 UTF-8 边界和 JSON 编码大小共同分片；标题和事件类型是有界预览。工具输出超过 8 KiB 时保留正文首尾各最多 4 KiB，按 UTF-8 边界截取，并标明省略的脱敏文本字节数；该预览不改变原始 trace、助手最终结果或后续消息。原始 trace 不作为公开下载文件。单条原始记录与跨记录的原生消息各受 4 MiB 解析上限约束，之后再应用展示正文预算；整份 trace 按有界步骤累积扫描，不以 4 MiB 作为总大小上限，不因工具结果超过展示长度就丢弃后续对话。`limit` 限制每页的输入和输出条目数，运行分界和启动失败诊断随对应页附带。是否读完以游标和水位标记为准。旧单 Run progress 的 12 KiB / 尾部上限不作为会话完整性证据。单原始记录、逻辑消息、逐次扫描、内存、FD 和并发读取受固定预算；准备尚未结束返回带 Retry-After 的 503，而不是成功空页。现有单 Run progress 接口保持兼容。

准备响应可附带 `preparation={phase,watermark}`：`phase=verification` 表示只读历史的摘要校验，`phase=projection` 表示会话扫描，`watermark` 是该阶段已处理的字节水位。它不含正文，不是分页游标、动作权限或完成证明。同一读取阶段水位前进才表示取得进展；进入下一阶段时重新计量。客户端可据此更新无进展超时，不能仅因总准备时长较长就停止仍在推进的读取。缺少进度、相同或回退水位不延长超时；缓存逐出或服务重启不保证水位保留，仍须有界重试。

默认仅包含 operational Run。严格 Task 详情的 `historical_read_only_runs` 提供已登记只读历史的选择信息；用户明确选择历史后，其完整 Run / certificate ref 纳入查询和签名。历史产物须在完整 manifest digest 核验成功前保持零正文，按有界步骤核验并保留受限 FD；只读选择的 TTL、逐出、取消与服务关闭释放读取资源，不创建磁盘缓存。证书、文件或身份漂移使选择失效，不能回退到同名目录或原生会话。

终端主体使用所选 Task 的 `/status/api/tasks/{lookup_id}/watch` 接收会话状态、正文和必要系统的失效提示。`conversation-invalidated` 只含公开 `lookup_id,run_id,run_sequence,watermark`，不是逐 token 输出，也不授予操作权限。任务选择器打开时另外订阅 `/status/api/task-directory/watch`，关闭即取消目录读取和订阅；当前会话独立继续工作。各连接共用服务的订阅配额，浏览器隐藏时暂停，恢复后重新读取真实状态；不承诺事件重放或跨标签草稿同步。

## 自动修复交付漏斗

`GET /status/api/issue-funnel` 聚合本机接入来源的自动 post-check 链路，统计范围固定为全部已接入工单，不受页面来源、账号或时间筛选影响。服务启动、工作项事件和每分钟补查触发后台更新；读取不启动 Agent 或改变 Task 状态。

禅道 `bug`、`story`、`task`、`case` 使用完整 Subject 身份分别统计，同号工作项不会合并。只有自动 post-check 受理计入入口，独立评论指令不增加受理数；识别为 Bug、开始修复及实际修复 MR/PR 的提交、合并仍分别要求对应证据，关闭禅道工作项不等于修复已合并。

| 读取方式 | 返回与刷新 |
| --- | --- |
| `view=summary`（工作台） | 立即返回已发布聚合，省略 `items`。首次为 `ok=false,status=loading`，无伪零计数；已有结果保持 `ready|partial|unavailable`，附 `refreshing` 和 `freshness=fresh|stale|unavailable`。过期结果保留原 `generated_at`。 |
| 省略 `view`（完整证据） | 返回 `items`；一分钟内复用快照，否则等待所需采集。 |

`refresh=1` 请求更新：摘要读取立即返回，完整证据读取等待；重叠请求合并为同一轮采集。完成后 SSE `server` 事件以 `action=issue-funnel-updated` 通知重读。采集属于服务，请求断开不取消；服务关闭取消并等待已有采集退出；台账锁等待和记录扫描都响应取消，不以后台 goroutine 代替可取消的实际锁获取。

- `scope=all-connected-work-items`；`generated_at` 是本轮同步时间。
- `items[].workflow_results` 保留同一完整工单身份的结构化 workflow 结论，包含 workflow type、`completed` / `blocked` / `needs-input`、Task/Run 世代及完成时间 `at`；`latest_bugfix_status` 是最近一次有完成时间的已记录 bugfix 结论，没有证据时为 `unknown`。它不是当前 Task/Run 状态，后续运行缺少报告时不推定其结论。客户 `outcome` 自由文本保持不透明，不从 Run 成功退出或评论发送成功推断修复完成。
- `items[].command_followups` 记录同一工单的独立指令启动。`business_outcomes` 按工单去重汇总：`bug_without_start` 为已识别 Bug 但无自动修复启动证据；`blocked_without_submission`、`needs_input_without_submission`、`completed_without_submission` 为最近已记录结论对应状态且尚无平台核验提交；`result_unknown` 为已自动启动但没有带时间的业务结论；`command_after_block` 为受阻或等待补充结论之后出现独立指令启动。最后一项是时间关联，可与后续提交、合并重叠，不证明人工纠正或交付，独立指令本身不增加任何自动漏斗阶段。这些都是已有台账的只读业务观察，不参与调度、重试、清理或 Task 状态转换。
- `stages` 依次为 `accepted`、`bug`、`bugfix`、`submitted`、`merged`，每层有去重工单数 `count`、记录是否完整的 `complete`、相对上一层的 `step_rate`、相对入口的 `total_rate`。`complete=false` 时 count 是已证实下限；分子或分母不完整、或分母为零时，相关比例为 `null`。Status 图表另外以已记录的 `count` 相除展示环节比例与总转化率，并明确标注按已记录数量计算；这些展示比例不表示完整历史转化率已确定。未知的零值或零分母仍显示 `—`。
- 身份包含 Provider、authority、project、kind（`issue` / `work_item`）、ID。代码仓库名称忽略大小写，其他工单项目保留稳定键；同编号的不同来源、实例或项目独立计数，同一工单的重试、多个修复和 backport 只计一次；任何一个实际关联修复合并即进入最后一层，不能据此声称全部版本修复完成。
- 原工单来源与修复代码平台独立：例如 Jira `APP-42` 或飞书项目稳定工作项可关联 GitLab MR / GitHub PR，不要求另建代码平台 issue。身份来自准入时保存的规范化 subject，不能用飞书 URL 的展示别名代替稳定项目键。工单关闭不等于代码修复合并。
- 入口按规范化工单身份合并平台留存的自动 post-check 回执与本机自动受理、post-check 启动/完成台账，支持 GitLab Issue Hook 的 `issues` 与 `work_items` URL；同一 issue 的 URL 写法和重试不重复计数。历史恢复必须独立发现平台回执，不能先以本机保留的 issue 集合限制平台查询。Bug 证据来自 workflow 的标准 metrics、post-check 已有 `workflow.start: bugfix` 建议，已发布 v1 post-check 评论中记录的明确处置，或实际 `workflow:bugfix` / 早期 `issue-execution` 启动/完成台账；自动修复必须有实际准入的子 Task或执行台账。历史结论只解析结论段中的既有 outcome / disposition，兼容 Markdown 加粗，不从证据段引用推导分类；明确的独立 command 启动记录不作为自动 bugfix 准入。查询从不启动分类任务。修复链接来自该 bugfix 的 metrics，或已发布 Task 级报告的明确交付字段；相关 feature 链接、本地准备、未推送补丁不算提交。匹配身份的平台记录可来自本机保留的 provider 读取产物，缺失时才查询目标平台。有效平台合并时间或带完整 host 身份的合并事件回执才计入合并；回执的 merge_observed_at 是本机收到事件的时间，不冒充 merged_at。独立 approve 不属于最后一层条件。
- `items` 返回原工单的 `subject`、`url`、已到达的 `stage` 与关联 `changes`（`url`、`verified`、`state`、`merged`），用于核对聚合结果。当前 Status 仅展示漏斗图、数量与转化率，不消费 `items` 或提供 issue/MR/PR 明细展开。不相关的 MR/PR、其他账号的独立提交不能补进该链路。
- `classification_unknown`、`repair_links_unknown`、`change_state_unknown` 分别表示 Bug 结论尚未确定（包括结果未留存或处置尚需证据）、自动修复尚无结构化修复链接（包括 metrics 缺失、空对象或空 change_requests 列表）、含任意未核验修复链接的 issue 数（即使同一 issue 已有其他修复合并，也保留该缺口）；这些缺口或 `business_outcomes.result_unknown` 非零时 `status=partial`，计数和比例表示已证实到达，不把等待或未知当成功。台账或任务读取失败时 `status=unavailable`，不返回伪零计数。
- 新运行观察以完整 Task/Run 世代去重，追加到已有工作台账的 `issue_funnel` 事件中；普通 Task 清理保留台账观察，删除台账则丢失相应历史。即时追加失败会记录警告；清理在固定的 Task 身份与锁内先从保留的 Run 产物幂等补齐观察，写入失败则返回清理错误并保留任务与产物。修复台账后重试普通清理即可，不重发 provider 动作或重新启动 Agent；dry-run 不写台账。清理保留同一 Task registration 已有受理观察的 identity；缺失时才以首个 Run 的身份补齐，尚无 Run 的 Task 使用空 Run 身份。历史基线复用既有自动受理/执行事件与保留 Task/Run 的 workflow 产物。离线回建从平台关联 MR 推导交付时，要求标题或关联议题字段明确引用该 issue，且具备修复分支，或同时具备对应 issue 的分支与明确修复标题，支持标准 `Issue / Issues / Related issue` 段中的完整工单引用及 URL，不能仅凭分支编号计入。原工单上可信自动执行后的明确修复回执可直接绑定其 MR/PR 字段，不依赖 MR 标题措辞；任意提及、背景链接或独立 command 回执不能建立交付关联。已有 feature MR 仍须有身份匹配的报告或原工单的明确交付回执记录本次修复已交付，且不能已在本次自动执行前合并。已发布 v1 存储的 Task 级 workflow 报告只在原始存储版本、Task 注册身份、workflow handle 与原工单身份及 URL 全部匹配时读取为历史观察，不创建 Run，不给现代 Task 增加根目录回退；已清理且无结构化证据的历史分类/修复链接无法还原。
- 离线工具消费已有台账、保留报告及已导出的规范化平台历史包；Jira/飞书项目历史只统计已留存或已导出的证据，不提供全历史自动采集。未留存的历史不能据此恢复成完整统计。
- 本机保留的平台记录按完整 provider/host/project/number 身份读取，可验证历史接入仓库的修复。实时 MR/PR 查询只允许当前配置的 GitLab host/projects 和 GitHub host/repositories，最多使用本轮 20 秒的查询预算；缺少本地证据且不可访问、身份不符或已移除配置的链接保持未知。

Workflow Runtime Contract 的 `workflow-result.json` 可报告以下独立于 opaque `outcome` 的观察字段：

```json
{"schema_version":2,"status":"completed","summary":"已提交修复","metrics":{"issue_type":"bug","change_requests":["https://github.com/owner/repo/pull/42"]},"actions":[]}
```

`metrics.issue_type` 为 `bug`、`other` 或 `unknown`；post-check 应报告分类，bugfix 应报告本次修复实际产出的 `metrics.change_requests`（最多 50 个）。已有 post-check 的标准结果/修复建议和真实执行台账可直接贡献统计，不要求历史任务补写 metrics；只有确实缺失的结果和修复链接保留证据缺口，不影响既有 workflow。metrics 不授予 provider action、workflow.start 或 lifecycle mutation 权限；runtime 不读取客户自定义 disposition、decision 文件或自然语言总结推断这些观察。离线历史恢复工具可将已发布 v1 评论的明确处置、身份匹配的 Task 报告交付字段与实际修复关联规范化为既有台账观察；它保留原始证据摘要、`snapshot_as_of` 与 `recovered_at`，不启动任务或重写源台账。恢复使用受信发布身份、版本化自动回执或绑定本 issue 的自动创建任务审计标记；普通评论提及、复制其他 issue 的结论、独立 command 重跑及当前 Bug 标签均不能建立自动受理入口。历史自动化发布账号可显式补充，不能只统计当前登录账号。平台已删除或未发布回执且本机记录也已丢失的历史无法证实，已记录入口数不等于保证完整的终身总数。已有 feature MR 只有明确记录本次修复已经交付到该 MR 才能贡献提交阶段。

Workflow 的 provider action 省略 `provider`、`project` 或 `subject_id` 时，从已校验的 `workflow-input.json` 原始 subject 补齐；显式不一致的目标仍拒绝。在执行任何 action 前发现结果格式不合法，属于明确未发送的本地预检失败，可修正结果后重试，不标记为投递结果未知。

<a id="gitlab--github-provider-native-delivery-metrics-读模型"></a>

## GitLab / GitHub Provider-native Delivery Metrics 读模型

### 账号贡献日历

`GET /status/api/account-activity?provider=gitlab|github` 返回当前服务用户的 `glab` / `gh` 登录账号贡献日历，必须指定平台。它读取账号可见范围，不使用交付质量的仓库列表，不创建 Task 或启动智能体。GitHub 使用官方 `contributionsCollection.contributionCalendar`，按 UTC 日期展示最近一年；GitLab 使用 `currentUser.events`，按 `currentUser.userPreferences.timezone` 汇总最近一年的贡献事件。GitLab 计入 push、评论、Issue / Work item 创建与关闭、MR 创建 / 关闭 / 合并 / 批准、Design 创建 / 更新 / 删除以及 Epic 创建 / 关闭 / 重开；项目成员加入、离开和普通项目创建不计入。API 权限和目标可见性可能使结果少于公开主页中主动公开的私有贡献。

响应包含 `status=loading|ready|unavailable`、`freshness=fresh|stale|expired`、`refreshing` 和可选安全说明 `warning`。`snapshot` 包含 `source`、`actor`、`profile_url`、`timezone`、`from` / `to`、`generated_at`、`full_sync_at`、`completeness=complete|partial`、`total` 和按日排序的 `days: [{date,count}]`。日期保持平台日历含义，不按浏览器时区再次换日；`count=null` 表示未覆盖或事件无法确认，`total` 只合计已确认日期，partial 时为下限。complete 表示完成 API 可见范围的采集，不保证平台权限之外的贡献可见。

GitLab 账号尚未设置时区或返回的时区无法识别时，卡片提示先在 GitLab 个人偏好中设置时区；服务不会猜测实例或浏览器时区来生成日计数。

首次读取立即返回 loading，后台启动有界采集。GitLab 每页最多 100 条，单次最多 2000 页、五分钟；没有跨调用保存的分页游标。每完成 20 页会展示已覆盖日期并继续同一轮采集；已有完整快照时保留它直到本轮完成。必须读完连接或跨过窗口起点才能证明全年覆盖，截断时边界日及更早未覆盖日期为 null。完整快照之后重算最近两天与当前日，每 24 小时重新采集全年以校准删除和权限变化。GitHub 每次读取完整原生日历，缺失日期或 GraphQL 错误不补成零。

活动快照位于 `JARVIS_STATE_DIR/status-value/account-activity`，每个平台一个派生文件，按 host 和账号身份验证后复用。十五分钟内复用快照；启动及后台每分钟检查刷新期限，页面关闭后仍同步。`refresh=1` 立即请求更新，重叠请求复用正在执行的采集；更新不会阻塞读取。失败重试间隔至少一分钟，旧数据最多展示 24 小时。每次读取及提交采集结果前都检查登录身份；身份不可确认时不返回旧快照，账号切换后从新身份重新采集。服务停止取消采集并等待退出。该缓存可重建，不改变已有 Task、Run 或交付质量存储格式。

完整的查看、恢复和排障步骤见 [Delivery Metrics 历史起点操作手册](delivery-metrics.md)。Delivery Metrics 的分析执行是普通 `delivery-metrics` lane Task；Status API 是读取 Task 结果后形成的持久化读模型。

`GET /status/api/value?provider=gitlab|github` 从所选 Provider 的已配置仓库生成 typed、只读的交付指标快照；缺省 Provider 为 `gitlab`。顶层 `configured` 表示该 Provider 是否配置了统计仓库。GitLab 与 GitHub 分别维护 snapshot、evidence 和刷新状态，API 不返回跨 Provider 合计。

`JARVIS_DELIVERY_METRICS_ENABLED=false` 时仍可读取已有指标和发现待分析证据，但不再接收新的 Delivery Metrics Task 启动请求；后台、手工 Start、尚未派发的 Start 恢复和 source-start 使用同一个 lane 准入限制，已有 Task 仍可显式 Continue 收尾。GitLab、GitHub 使用相同规则。开关经重启生效，服务维护对活动 Run 的中断和接续仍遵循普通生命周期。启用时，新 Run 按启动时的 canonical runtime env 选择 Agent、命令、模型与 prefix args，修改 Agent 不会使已有业务分析结果失效。

普通 GET 会复用该 Provider 的 15 分钟 fresh snapshot；fresh hit 仍会验证对应 CLI 的 authenticated principal，登录主体变化会使前一主体的 snapshot 失效。服务端在启动、MR/PR 关闭或合并、分析 Task 完成后主动同步，并每分钟补查；页面关闭不影响分析。GET 不提交分析 Start/Continue。Cancel 把该 canonical MR/PR 投影为最终 `judgment-unknown`，不自动创建替代 Task。追加 `refresh=1` 只跳过读取 TTL；已有刷新时，请求会加入同一轮刷新。

服务把派生状态写入 `JARVIS_STATE_DIR/status-value`，但分析过程只通过 Task 存在。后台每轮为每个 Provider 最多启动一个新的 `delivery-metrics` Task，同一 Provider 已有分析正在处理时等待其完成；没有全局 FIFO queue、私有分析状态或后台 cursor。已有 Task 的失败或无效结果保留给操作者明确 Continue。已有有效结论按原口径保留；相同 Provider、host、账号身份、仓库、MR/PR 和源 SHA 的历史证据可直接复用，不启动新的分析 Task。合并后的评论或元数据 `updated_at` 变化不会使结论失效；已发布的 schema 4/v7 证据键虽保留更新时间字段，已知格式的结果匹配不要求该字段相同。原 Task 已清理时，保留的有效证据仍可复用；账号、主体或源 SHA 不同不得串用。Provider host、仓库集合、schema 或 Delivery Metrics 合同变化时，服务不会复用不兼容的 snapshot。

历史累计窗口从当前 `glab` 或 `gh` 登录账号的 `created_at` 开始，到本轮采集固定的 `generated_at` 为止。actor 直接读取对应 provider 的 authenticated-user endpoint，不需要独立账号环境变量，也不假设账号名是 `jarvis`。GitLab 优先使用带 `mergedAfter` / `mergedBefore` 的 GraphQL count fast path，并对 actor MR 取有界近期明细；不支持时才回退到稳定的 `merged_at` REST 排序分页。GitHub 使用 `UPDATED_AT DESC` GraphQL cursor 分页；两个 collector 都执行双边时间校验。按仓库返回：

- 窗口内全部已合并 MR/PR，以及其中由当前登录账号创建的 change request；
- 当前登录账号 MR/PR 中完全原样合并、自主修订后合并和发现人工纠正的数量；
- 判断未知、Provider 证据未知和待分析数量；
- 仓库覆盖率、证据覆盖率，以及每仓库最近 20 条当前登录账号 MR/PR 证据。

可选字段 `snapshot.filtered` 与全量统计使用同一轮采集。其 `totals` 和 `repositories[].counts` 在当前账号的 MR/PR 中排除确认的自我改进和整条回迁，`excluded_self_improve` 和 `excluded_backport` 分别给出排除数量。`origin_pending` 是待复核的来源数，这些记录暂计入筛后统计。两组统计复用同一份人工纠正结论。`merged_change_requests` 仍表示配置范围内所有账号的合并总量。旧快照可省略 `filtered`。未保存待复核数的旧筛选结果不再展示，保留原全量统计直到重新采集。

新完成的分析可保存交付来源。管理员也可导入按平台、站点、账号、仓库、MR/PR 编号和源 SHA 绑定的本机复核记录。同一版本有复核记录时优先使用复核结论。当前账号的复核文件无法读取或校验时，响应包含 `delivery_origin_review_unavailable`，全量统计继续可用，筛选使用可核验的分析来源。标题和分支名不足以判定回迁，包含独立交付的 MR/PR 保留。GraphQL 批量同步不请求描述。GitLab REST 回退仍受原响应大小限制，筛选不读取响应正文来判断来源。读取或切换筛选沿用本机结论。导入步骤见 [历史交付来源](delivery-metrics.md#历史交付来源)。

Provider merge 是 provider-native 工程交付 proxy，不代表终端客户业务验收。登录账号 change request 只按 author 识别，不涵盖该账号在其他作者 MR/PR 中的贡献；Jira、飞书项目、跨来源关联、聚合和去重均不在此 response 中。

`runtime_token_usage` 是保留的兼容字段，当前版本不提供可用的 token 用量统计：`status=not_available`、`agents=[]`，各级会话数量和 token 数均为 0，Status 页面不展示这项 KPI。这些零值不是实际消耗为零的证明；Run 是否保存 token metadata 不影响接口可用性。

`window=retained-task-state` 表示该字段的范围是本机保留的运行记录，不是代码平台的合并历史。接口不返回价格、费用预测或原始会话，不从进程输出、全局会话目录或文件时间推测用量。未来可用的用量证据仍须满足[执行模型的指标约束](execution-model.md)，不能由客户端按现有空壳推断。

后端从以下 classification 派生两个面向人的代码质量问题；Status UI 直接消费 typed count/rate：

- `unchanged`：change request 创建后未发现 source revision；
- `self-revised`：发生过 revision，但 Agent 未判断为人类指正原 MR/PR 错误后促成；
- `human-corrected`：非 author、非 jarvis 的人类自己写出实质纠错内容，并促成后续 source revision；人类只转述、确认或要求 agent 按 bot/Jarvis review 修复不算；
- `judgment-unknown`：Delivery Metrics Task 无法按合同判断；
- `evidence-unknown`：Provider MR/PR 明细不完整；
- `pending`：历史起点尚待对应 lane Task 产出有效结果，不是最终分类。

成功 Run 的结果缺失、不可安全读取或不符合严格分析结果契约时，对应 MR/PR 保持 `pending`，其 `evidence` 包含固定代码 `analysis-result-invalid`。操作者可在原 Task 上明确 Continue；Cancel 是否可用由该 Task 的公开 `actions.cancel` 决定，已 completed 的 Task 不允许 Cancel。该原因不包含原始结果、文件路径或解析错误正文，后台不会因此自动重跑。

`未发现人工纠正 = unchanged + self_revised`，`发现人工纠正 = human_corrected`。两者共享 `correction_known = unchanged + self_revised + human_corrected` 分母。`judgment_unknown`、`evidence_unknown` 和 `evidence_pending` 不进入比例分母。

首次建立历史起点时，merged counts 先显示，尚未分析的记录进入 `evidence_pending`。pending 归零前，聚合质量比例为 `null`。后台自动为尚无 Task owner 的 pending 项启动普通分析 Task，并复用已落盘的有效结果；读取 API 不承担调度。

### 分析进度

快照存在或历史发现正在进行时，顶层 `analysis_progress` 返回：

- `phase`：`discovering_history`、`task-running` 或 `complete`；
- `lane`：固定为 `delivery-metrics`；
- `analyzed`、`pending`、`total`：历史起点数量；
- `current_batch`：当前已发现但还没有有效 Task 结果的 Provider、仓库和 MR/PR number；
- `started_at`、`updated_at`：分析时间。

`current_batch` 是用户安全的 typed 状态。API 不返回 Agent 命令、stderr、Provider 正文或 state 路径。

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
    "lane": "delivery-metrics",
    "analyzed": 20,
    "pending": 0,
    "total": 20,
    "current_batch": [],
    "started_at": "2026-08-11T14:00:00Z",
    "updated_at": "2026-08-11T14:03:20Z"
  },
  "snapshot": {
    "schema_version": 8,
    "generated_at": "2026-08-11T14:00:00Z",
    "baseline_updated_at": "2026-08-11T14:03:20Z",
    "observed_from": "2026-06-09T07:34:53Z",
    "actor": {"username": "customer-agent", "name": "Customer Agent", "created_at": "2026-06-09T07:34:53Z"},
    "source": {"provider": "gitlab", "host": "gitlab.example.com"},
    "delivery_metrics": {"mode": "lane-task", "lane": "delivery-metrics", "contract_version": "jarvis-box-delivery-metrics/v2", "enabled": true},
    "runtime_token_usage": {
      "status": "not_available",
      "window": "retained-task-state",
      "generated_at": "2026-08-11T14:00:00Z",
      "session_count": 0,
      "unknown_session_count": 0,
      "total": {"input_tokens": 0, "output_tokens": 0, "cached_tokens": 0, "reasoning_tokens": 0, "total_tokens": 0},
      "agents": []
    },
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

Task response 的 `actions` 使用以下 key：

```json
{
  "start": {"enabled": true, "reason": "inactive-source-task", "requires_input": false},
  "continue": {
    "enabled": true,
    "reason": "task-ready",
    "strategy": "agent",
    "requires_input": true
  },
  "cancel": {"enabled": false, "reason": "terminal-task", "requires_input": false},
  "retry_delivery": {"enabled": false, "reason": "", "requires_input": false}
}
```

Start、Continue、Stop 是三个用户操作；Stop 沿用已发布的 actions.cancel key，/cancel 与 /stop 调用同一策略，不增加第四个生命周期操作。所有 action key 一律带 `requires_input`，`false` 也上线、不省略：页面按 `requires_input !== false` 判，键缺失会被读成 true，于是把不收输入的操作当成要输入。`retry_delivery` 独立描述原结果的安全重试发送能力，仍由已有 Continue sealed writeback 操作执行，不新增 Task 生命周期操作。

后端 policy 是唯一授权来源。UI 和 CLI 不自行推断 enabled 状态。所有生命周期 mutation 写入 audit event。

### Start

`POST /status/api/tasks/{task_id}/start?reason=...`

- 选中的 Task 只是 source。
- 创建新 Task、新 AgentConversation 和首个 Run。
- 成功结果中的 `task_id` 是新 Task，`run_id` 是它的首个 Run；两者不能混用。
- 原 Task、Run 和 Artifact 不变。
- source active、本轮未完成、完成但仍缺产物/写回、进程 ownership 未解决或 lane 不支持时返回 `409` 和明确 reason；先 Continue 或 Stop 原 Task。

无 source 的原子 Start 使用 `POST /status/api/tasks/start`（人类 gateway，`jarvis-command`）或 loopback-only `POST /server/api/tasks/start`。JSON body 为 `prompt`、可选 `reason`、`lane`、`agent` 和 `owner_display_name`。归属字段仅在 Start 写入 Task，由统一 TaskView 返回；去除首尾空白，最多 256 个 Unicode 字符与 1024 个 UTF-8 字节，拒绝控制字符，非法时返回 `400 invalid_owner_display_name`，不创建 Task / Run。旧客户端省略时保持兼容，Terminal 创建界面要求填写。归属是工作组织展示名，不替代来源请求人或 Target，不赋予 IM 回复路由；网页创建默认在工作台读取结果。Continue / 恢复不接受改写归属。省略或留空 `agent` 时沿用工作类型配置；显式选择只绑定本次任务，不写全局或 scope 配置。所选 Agent 与该工作类型配置不同时，使用所选 Agent 自己的参数，不继承其他 Agent 的 scope 参数。未知 Agent 返回 `400 invalid_agent`，不创建 Task。服务端生成 Task identity、登记 intake、创建首 Run、启动并返回真实 Task/Run identities。定时作业统一使用 `custom-user-task + job_id`；loopback `/server/api/tasks/start` 额外接受可选 `notify_target=direct:<id>|group:<id>`，只投递成功 Run 的最终答复，公开 Status prompt 请求携带此字段返回 `403`。通道不可用或目标类型不支持时在创建 Task 前拒绝。结果投递语义见[执行模型](execution-model.md#completion)。v1.1.7 以前三个 scheduled lane 保留原 loopback 兼容边界，不扩大其他入口权限。

磁盘余量不足或存储故障锁存时，原子 Start 仍返回 `202`，`result.waiting=true`、
`result.wait_reason=storage-wait`，Task 保留为机器等待且尚无 Run；空间恢复后按原始输入自动重试，
也可取消该等待。普通成功启动返回 `result.waiting=false`。自定义和定时任务保留原有 Target 身份。

### Continue

`POST /status/api/tasks/{task_id}/continue?reason=...&run_id={source_run_id}`

评审 Task 的 Agent Continue 在创建后继 Run、停止原进程或重建工作区前，先用原平台身份核实 MR/PR 的当前状态。已合并或关闭时返回 `409`、`result.reason=subject-terminal`，不创建失败 Run、不拉取已删除分支，原成功运行和交付记录保持。平台鉴权或读取失败不能冒充对象终结；仍开放的评审继续使用原 Run 已受理的固定提交与分支身份。

```json
{
  "agent": "copilot",
  "message": "继续调查网络恢复后的失败"
}
```

- `actions.continue.strategy=agent` 且 `requires_input=true`；`agent` 与 `message` 必须同时提供，在同一 Task 创建新 Run，复用全部已登记 Workspace，并以 primary 作为默认 `cwd`。
- 普通 Continue 绑定完整 Task registration，服务端从当前严格聚合取得准备材料。页面选中的历史 Run、旧 `run_id`、`task_revision` 或 `task_view_revision` 不阻断本次新指令；历史选择只控制浏览。
- 普通 Continue POST 没有幂等键，重复提交不保证只执行一次，正文相同也不能证明是同一条输入。客户端不自动重放修改请求；响应结果未知时先查询该 Task 的待派发输入及 Run 历史，确认受理结果后再决定是否提交新指令。
- 自动恢复和不含新输入的交付重试沿用已封存的原输入及完整 Task/Run 归属。准备前后的来源变化使旧恢复失效，不把旧指令重新受理，也不停止或替换新的执行。已受理的待派发输入继续由原 Task 按序认领。
- 同 agent 且 private handle 有效时使用 native resume；其他情况创建 child AgentConversation，并以 `agent_strategy=native-resume|new-agent-conversation` 说明选择。
- 有效会话始终允许提交新指令，包括有已送达 IM 问题的会话；普通 Continue 仍只消费 `actions.continue`，不作为问题作答入口，也不创建 QuestionResolution。active Run 先停止再接续；启动、准备、收尾、替换或工作区清理过渡期间返回 `result.waiting=true`、`result.wait_reason=instruction-accepted`，表示指令已持久化接收。`pending_continue_count` 表示尚未创建 Run 的指令数；后台按原 lane 自动接续，客户端不需要重发。授权、存储或进程操作故障返回具体原因，不按执行状态禁用 Continue。普通新指令产生不兼容后继 Run 时，原问题按其 source Run 派生为过时，不改变 Task lifecycle。
- 丢失进程的自动恢复继续由原 sealed recovery plan 推进，不要求用户提供虚构的指令；用户独立提交的新输入仍使用普通 Agent Continue。
- `actions.retry_delivery.strategy=writeback` 且 `requires_input=false` 时，本端点提交 TaskService sealed retry plan，只重试当前 latest exact Run 中可恢复的确定失败 delivery receipt，包括上文限定的历史回复权限预检失败。服务端关闭写回产生的 `provider.comment` / `provider.workflow` 回执若明确为 `skipped/provider-writeback-disabled/not-attempted`，保有同样的显式恢复能力；重新开启写回后复用原结果，仍须完整私有回执和原产物，不改写跳过历史。其他 skipped 原因不因此开放重试。请求不得携带 `agent` 或 `message`；成功或失败都追加新的 effect attempt receipt，不创建 Run。
- 原生 GitHub 内容发布是独立 `actions.retry_delivery.strategy=writeback` 的闭集分支：只有 batch 的当前摘要为 `retryable_no_send`、原 Task effect receipt 已证明 `failed/retryable/not-attempted`、以及同一 batch 中唯一的 exact ordinal 有持久 `not_attempted` 事实时才给出策略。plan 绑定该 batch、Run、source receipt 和 ordinal；RetryDelivery 只续接它，不创建新 batch、目标、版本预期或 Run，也不重发其他 ordinal。已经 claim 的项和 `unknown` 只允许 exact marker/版本查询，不能借 RetryDelivery、普通 Continue 或人工 attestation 推断未发送。
- 首次IM文件预检明确未发送且具有exact-Run私有预检凭据时，文件修复后也使用上述writeback操作。原回复文本保持，重新核实合法文件与原目标；预检凭据不等于完整附件内容回执，不授权未知结果重发。
- `actions.retry_delivery.attestations` 列出可选送达裁定；已发布的 `actions.continue.attestations` 同步保留相同列表。unknown 禁止盲目重发，但普通 Continue 始终可以提交新指令。明确失败可按私有凭据重试，裁定只记录实际查证的事实，不得用于绕过原目标、内容和防重复发送校验。

- Task identity 始终不变；旧 Run prompt 不读取、不复制，新 Run 持久化的 prompt 只包含本次新输入。

### 人工裁定投递结果

`POST /status/api/tasks/{task_id}/attest-delivery?delivery={delivered|not-delivered}&reason=...&run_id={source_run_id}`

外部效果没有明确回执时，系统先有界查询原效果，禁止盲目重发。查询耗尽后为本轮未完成，不产生管理员待办；原用户收到确认问题后仍保留原交付事实，不创建 Task 等待。此端点用于明确核对后的可选裁定，将原效果的实际送达情况写成同 Run 后继收据，不改写原 Run 或未知发送事实。

- 只收 policy 在 `actions.continue.attestations` 里列出的值；没列出时返回 `409` 和 policy 的 reason（不是页面自己编的码）。
- `run_id` 只能是 Task 当前的 latest Run；指向别的 Run 返回 `409 attest-source-stale`。`task_revision` 与其余 mutation 一致：不匹配返回 `409 task_revision_changed`。
- 不接收 `agent` 或 `message`，不启动 runtime 作业、不创建新 Run：它写一条新的 effect attempt receipt，`attestation` 字段记录人给的那个事实。
- `delivery=delivered`：这条 effect 记为 `succeeded + delivery_state=delivered`，Task 执行状态保持 completed，Run 仍保持原来的 `succeeded`。
- `delivery=not-delivered`：记为确定的 `failed + retryable=true + delivery_state=not-delivered`；Task 执行状态保持 completed；同 Run 的发送恢复在可重试时给出 `actions.retry_delivery.strategy=writeback`，由上面那条原地重投接手。响应中的 `writeback` 如实回报重投起没起来（`{"started": bool, "reason": string}`）——没起来不是裁定的失败，事实已经落账。
- 一条未知结局只许裁定一次：之后 policy 不再列出 `attestations`，再提交返回 `409`。裁定不许改写原回执，只追加后继 attempt，未知发送事实保持原样，精确原效果的查询 ACK 或这条带裁定的后继可以结算它。

### Stop（兼容 Cancel）

`POST /status/api/tasks/{task_id}/stop?reason=...&run_id={current_run_id}`

- 停止当前执行，保留 Task、会话、工作区、未提交文件和 Artifact。已发布的 `/cancel` 是同义入口，状态与 `actions.cancel` 保留兼容拼写。
- 存在 active Run 时先解决其进程 ownership；对应 Run 进入 `stopped`。
- `recovery-required` 且没有可用 pid/pgid 时，服务端以状态 ownership fence 固定旧 Run，再取消 Task。
- 无法证明进程已停止时记录 `reaping_failed`，返回冲突，不把 Task 伪装成已取消。
- 干净 completed 或已经 cancelled 的 Task 返回 terminal/no-op；完成但仍缺产物/写回的 Task 可以 Stop，表示停止剩余工作。
- 工作区按配置的保留期清理；保留期内 Continue 撤销旧截止时间。Task Artifact 按自己的保留策略继续存在。
- 已有 Operational Run 的停止任务可用新指令 Continue；新 Run 保留原生会话能力与工作区，原 Run 不变。不会自动恢复旧执行、重放已停止输入或重试旧交付。零 Run 停止撤回准入。系统的概括任务使用已封存材料，提交新指令返回 `recap-input-fixed`，不新增运行记录。

## 工作目录清理

Task workspace 只有一条归属链：append-only 的 `task-state.workspaces[]`。一个 Task 可以登记多个仓库目录；每项有稳定的 Task-local `id`、服务端分配的绝对 `path` 和可选 repository metadata。已有项不可换 id、路径或仓库；恰好一个 `primary=true` 只负责选择 Run 的默认 `cwd`，不限制 Task 的工作区数量。

TaskService 在首个 Run claim 之前一次登记 Task identity 和初始工作区，再逐项创建、clone 或 checkout。物化尚未成功时 canonical Task status 保持 `running` 且没有 Run；Status 只以 admission 的 `workspace-materialization-wait` 投影机器等待，原入口 receipt 另带 `waiting=true`，但不会创造 `waiting` / `storage-wait` Task status。此时可以 Cancel；有效会话的 Continue 仍持久化为同一 Task 的 pending input，不能越过物化、伪造 Run 或另选工作区，恢复器只按原 admission/Workspace fence 依次 claim。Runner 向每个 runtime agent 注入相同的 Workspace ownership contract；运行中的 zero-workspace Task 必须以 `jarvis-box workspace create --id primary` 建立第一个仓库，非空 registry 后续增加仓库时使用普通 stable id。Agent 不得绕过该命令创建、替换或物化 `JARVIS_WORKSPACE_ROOT` 的任何直接子项。该命令先验证当前 Run 仍持有 Task，并在原子 state mutation 中追加登记，登记落盘后才创建目录。Status detail、Continue、自动清理和手工清理都只读取 `task-state.workspaces[]`；`cwd`、`workdir`、`run-context.json`、artifact 文件和目录扫描都不是 workspace 归属来源。

所有 lane 使用同一登记规则，不设客户工作流白名单。普通 Run 成功后保留工作区至持久化清理截止时间，由后台按登记回收；完成回写不以提前删除工作区为前置条件。用户 Stop 按 JARVIS_TASK_WORKSPACE_CLEANUP_DELAY_MINUTES 保留工作区，到期由既有处置事务清理；到期前 Continue 撤销旧计划。已验证的外部主体终结属于立即清理边界：非终态 Task 先持久化 cancellation intent、停止运行并提交取消终态，再在释放 Task/state locks 后清理全部登记项。已有 completed/cancelled Task 保持原终态，只重试登记式处置。清理失败、unknown 或退避保留独立的处置义务和原因，不把已提交终态改回 `finalizing` 或 `needs-attention`；并发 Continue 仍须通过原处置 fence。

Task 创建时会把 GitLab/GitHub/Jira/Codeup 外部工作对象登记成规范化 `task-state.subject`。GitLab issue `close`、MR `close/merge`，GitHub issue `closed`、PR closed/merged，Codeup MR close/merge，以及 Jira issue 进入 Done category 或被删除时，provider adapter 调用同一个终态入口：非终态 Task 先停止并转为 cancelled，再清理全部登记目录；已有终态只重试清理。首次处理 terminal delivery 时，服务先把当时精确匹配到的 Task registration 与 Run fence 集合原子写入 receipt，再做任何取消或清理；部分失败、进程退出或磁盘故障后的 retry 只重放这份快照，不重新扫描 Task。关联只来自创建时的 subject 登记，不从 `issue_or_mr` 文本、workspace 路径、Artifact、branch 或 lane 反推。仍未生成任何 Run、处于准入阶段的 Task 不会因正常工作区重试推进状态版本而丢失取消义务；只在同一 Task registration、current/latest 为空且两类 Run 集合仍空时重验并取消，旧零 Run 快照不能跟随后来认领的首 Run。

GitLab/GitHub 的最终评论如果返回 HTTP 404，delivery owner 会用同一个 provider 身份检查目标项目或仓库。目标项目或仓库仍可访问，而 issue、MR 或 PR 已不存在时，Task 进入与 provider terminal event 相同的登记式清理流程；先提交 `cancelled`，成功 Run 保持 `succeeded`，再清理 Workspace 和 typed external resource。清理失败保留取消终态及独立处置义务，由处置流程恢复，不重新执行 Agent 或 provider writeback。项目/仓库不可访问、鉴权失败或配置错误仍记录为对应 exact Run 的 provider delivery effect 失败，不会被转换成取消。

`POST /status/api/tasks/{task_id}/delete-workspace`

```json
{
  "workspace_id": "f3a91c5e16c27b42"
}
```

该接口是 Status 页面提供的主机维护动作；每次只删除用户选中的一个已登记工作区，不改变 Task lifecycle：

- 客户端只能回传最近一次 Task detail 中服务端签发的 `workspace_id`，不能提交任意路径。
- 仅允许清理没有 active Run 或机器推进 owner 的 completed/cancelled Task 工作区。
- 服务端在执行前持有 Task state mutation lock，重新确认 Task 仍为终态、目录仍在登记表中，再解析目录；只接受配置 Workspace root 下的真实直接子目录，root 本身、root 外路径、符号链接和服务当前工作目录均拒绝。
- Status 手动删除和定时回收调用同一套 TaskService finalizer 和锁。只有显式登记在 `external_resources[]` 的类型化资源才触发 Docker finalizer；文件名、目录名和 repository 名不能创建资源所有权。Docker 不可用时保留资源记录与 Workspace，并写入稳定失败签名和持久化退避。完整契约见 [Task external resource lifecycle](task-external-resource-lifecycle.md)。
- 已登记目录即使已经不存在也保持删除资格；重复调用返回成功并标记 `already_absent=true`，不会把幂等重试误报为冲突。
- 删除结果写入 Task audit event。

`POST /status/api/workspaces/clean-completed` 批量处置终态且无活动 Run 的 Task 工作区。响应中的 `completed_task_count` 是纳入处置的 Task 数，`skipped_task_count` 是不满足条件而保留的 Task 数；`workspace_count` 是这些终态 Task 的登记工作区数。工作区结果按本次新增结算分别计入 `removed_count`、`already_absent_count`、`skipped_count` 和 `failed_count`。活动 Task 被跳过不增加工作区的 `skipped_count`。

同一 Task 的部分工作区处置失败时，已持久化成功的成员仍如实计为删除或原已不存在；失败不能覆盖其他成员的成功结果。重试不重复计算已结算成员。统计保持在原 Task 登记、Run 和工作区集合内，并发 Continue 或登记变化后的新一轮结果不能代入旧请求。

## Status task projection

允许：

- safe Target key/hash、标题和 provider label
- Task id、`current_run_id`、`latest_run_id`、Run sequence、状态、时间、safe agent name
- Run 启动前的当前准备操作、实时/最终准备耗时、重试次数和 safe transport detail
- exact Run `prompt.txt` 的 bounded、redacted 输入投影，以及 RunTrace 的 bounded、redacted 进程输出时间线；输入可以包含工作流契约、上下文和主机路径，但 RunTrace 本身不复制 prompt
- `actions`、`safe_actions`、`inspect_actions`
- safe lifecycle/blocker/action summary
- native publication 的安全摘要（state、已确认计数和受保护详情可用性）
- 一次性事件订阅 `event_subscriptions` 的安全聚合：`availability` 与 `active_count`；它只说明当前 Task 是否有可用的一次性事件订阅，不能选择、撤销或重投订阅
- opaque safe Artifact ref
- Task detail 中显式建模的 `workspace_locations`，包括该 Task 工作目录的绝对 `location`

禁止：

- 作为结构化字段的 `task_dir`、`run_dir`、log 路径，以及 `workspace_locations[].location` 之外的任意 Workspace 绝对路径
- native AgentSession id/file
- private resume handle value
- cross-agent source ref
- raw payload、provider token、reply token、`prompt.txt` 原文或跨 Run prompt/history
- process command、argv、env、pid/pgid
- native publication manifest、batch/operation/claim identity、marker、actor proof、target binding、repository path、source artifact/path/SHA、provider URL、remote id 与 provider evidence
- event-subscription 的 opaque set/rule refs、OriginalTargetActor、sender、reply target、执行链接/完整 execution tuple、source receipt/cut、hook identity/proof、webhook body、凭据与投递地址；个人查看/撤销只在原 IM 已认证控制面完成

Status Artifact endpoint 只解析经过授权的 safe ref。普通 `/status/api/tasks/{task_id}/artifacts` 只列出所选 exact Run 的 safe artifact，不返回文件内容；工作台读取文件内容或浏览该 Task 已登记工作区时使用仅接受 loopback 请求的 `/status/api/system/tasks/{task_id}/artifacts`。两条路由都拒绝 `payload.json`、legacy `meta.json`、`run-context.json`、`prompt.txt`、`run-trace.jsonl`、`task-state.json`、`task-events.jsonl` 和 runtime logs，并在返回文本前执行 redaction。`prompt.txt` 与 RunTrace 只能通过 exact Run progress 的 bounded/redacted 投影读取，不能通过 base64 封装绕过文本 redaction。

## 系统设置 API

事件订阅沿相同认证边界使用 `GET /status/api/system/tasks/{lookup_id}/event-subscriptions?task_revision={revision}`，返回安全执行摘要、opaque `set_ref`、`set_revision`、条件与动作、状态、期限和最近结算。每页默认最多 16 项，`limit` 只接受 1–16；非空 `next_cursor` 绑定完整 Task lookup、revision 和页长，版本或选择变化后必须重读。它不返回原 IM sender、接收地址、source cut、hook proof、原始输入或凭据。

`POST` 同一路径只接受 `{ "set_ref": "ess_...", "set_revision": 1 }` 与 query `task_revision`。服务端在当前 Task/set 双重版本下签发不超过 30 秒的 operator-audit proof，再由 TaskService 撤销。原 IM 用户的撤销与操作员撤销分别归因；操作员不冒用 `OriginalTargetActor`。该入口不能登记订阅、触发 Continue、重投事件或补发通知；撤销只停止未来授权动作，既有 Run 和历史结算保持。公开同路径在解析 Task 前返回 404，损坏/陈旧分页或版本不匹配明确拒绝。

`/status/api/system/*` 为 topbar 系统设置面板提供：

- `GET overview|agents|doctor|crons`：实例、Agent、诊断、内部轮询与已脱敏配置；`overview.license` 返回本机授权字段表 `rows`、需要处理的原因 `problem` 和可选到期提醒 `expiry`，与 `license status` 使用相同本地快照，不联网；
- `GET tasks/{lookup_id}/native-publication`：同一受保护读取边界中的原生发布受限详情，包含所选 Run 的状态、已确认版本与证明过的对象链接，不返回私有源 artifact 或 Agent 计划；
- `POST agents/current`：保存默认 Agent，每次保存清除所有 scope 和 Agent 描述器的前置参数。`POST|DELETE agents/scopes/{scope}` 设置或取消指定 scope，具体规则见 [Agent 选择和验证](runtime-agents.md#选择和验证)；
- `POST chatbridge/reset`：重置 ChatBridge 连接；
- `POST tasks/clean`：按 dry-run、终态、lifecycle lock 和 disposal certificate 清理 Task Artifact；
- `POST tasks/start`：原子启动显式 operator prompt。

这些 endpoint 不再根据 loopback 切换人类权限。每个 mutation 仍执行输入校验、业务 owner 和 audit 契约；`POST tasks/clean?dry_run=1` 返回候选项且不删除数据。系统 response 可以展示当前主机路径和经脱敏的运行配置，但不得返回 credential、private resume handle 或 raw provider payload。

系统设置 UI 必须把这些 endpoint 解释成用户任务，而不是原样暴露 API 名称。默认 Agent 和 scope response 的成功只证明未来路由配置已保存，不代表 active Run 已切换；ChatBridge reset 的成功要继续以重新读取的 running/provider connected 状态为证据；operator prompt 的 `result.task_id` / `result.run_id` 是进入 Status 工作项跟踪的凭据；clean response 的 `status=dry-run|cleaned|deferred|error` 必须被汇总并保留逐项原因。

`GET|HEAD /server` 使用 permanent redirect 转到 `/status`。旧的人类 `/server/api/*` endpoint 不做 POST redirect；`POST /server/api/tasks/start` 是 loopback-only prompt admission，scheduled authority 只由 internal route 与当前 lane allowlist 推导。

`POST /server/api/service/maintenance` 是 CLI 服务维护 transport，只接受无 Origin 的 loopback JSON 请求和与当前实例相同的 canonical runs root。它消费 TaskService 的 exact maintenance plan，不执行服务管理器操作，也不新增用户生命周期操作；CLI 在调用服务管理器前重新检查阻塞任务。

### Runtime Agent 模型资源与额度

`GET /status/api/system/agents` 在既有 Agent inventory 和 scope 配置之外，为每个 `agents[]` 返回可选 `resource`，并为每个 `scopes[]` 返回可选 `target`。这些字段描述实际计费主体，不把 Agent 名称当作模型或账户：

```json
{
  "name": "claude",
  "available": true,
  "resource": {
    "status": "unavailable",
    "provider": "deepseek",
    "provider_host": "api.deepseek.com",
    "model": "deepseek-v4-pro[1m]",
    "account_type": "api-wallet",
    "account_ref": "acct_1a2b3c4d5e6f",
    "source": "deepseek-balance-api",
    "checked_at": "2026-08-26T12:00:00Z",
    "quota": {
      "kind": "wallet",
      "available": false,
      "balances": [
        {
          "currency": "CNY",
          "total_balance": "-1.05",
          "granted_balance": "0.00",
          "topped_up_balance": "-1.05"
        }
      ]
    }
  }
}
```

- `resource.status=ready|unavailable|unsupported|error` 分别表示额度可用、计费账号不可用、计费方没有安全公开的自动读取接口、读取失败；它不替代 Agent 自身的 `available`。
- `provider` 和 `model` 来自 canonical runtime env、实际 base URL、Agent 模型变量、Codex prefix args 和持久 Agent HOME 中的本机配置。Codex 会按实际优先级合并 `config.toml`、`$CODEX_HOME/<profile>.config.toml` 与 `-c/--config`、`-m/--model`，并解析 `model_provider`、`model_providers.<id>.base_url`、`env_key` 和内置 OpenAI provider 的 `openai_base_url`；每个 scope 只有一个覆盖点——该 scope 自己的 prefix args：Codex 把它送进整条路由解析，所以 `scopes[].target` 的 provider、base URL、model 和 account 都可能与默认 Agent 不同；其余智能体只从 prefix args 里取 `-m/--model`（取不到就用默认 Agent 的模型），provider、base URL 和 account 沿用该 Agent 的解析结果，产品里没有 per-scope base URL 或账户这个覆盖面。
- `account_ref` 是当前有效高熵 credential 的短哈希引用，只用于判断多个 Agent 是否共享计费账号；response 不返回 credential、邮箱、组织名或原始账户对象。
- `quota.kind=wallet` 返回 Provider 声明的余额和可用性；`quota.kind=rolling-window` 返回命名额度池的主/次窗口、已用比例、窗口长度和重置时间，并可返回完整重置机会。余额保留 Provider 的十进制定点字符串，不转换为浮点数。
- `source=codex-app-server` 使用本机 Codex 账户接口读取 ChatGPT 套餐和滚动窗口；`source=deepseek-balance-api` 只在有效模型路由的 host 恰好是 `api.deepseek.com` 时，将该 Agent 实际使用的 credential 发送到固定的 DeepSeek 官方余额 endpoint。服务不向自定义 base URL 回传 credential，避免配置 URL 形成 SSRF/credential exfiltration。
- 同一 Provider 和 `account_ref` 的实时查询在一次 request 内去重。普通 GET 始终从当前 canonical 配置读取 Agent 清单、选择、scope、命令路径与可用性；只有版本、额度和 scope 的模型账户信息可复用与当前配置匹配的 60 秒 snapshot，避免浏览器重连和系统事件反复查询计费方。旧配置的后台探测不能覆盖新的路由选择；`refresh=1` 跳过 snapshot，供“重新检查”使用。每类上游查询最多等待 5 秒；失败只投影到对应 `resource`，不让 Agent inventory 整体失败，也不发起模型推理。
- Anthropic、OpenAI API、GitHub Copilot、Google AI / Vertex AI 和自定义网关当前只做 provider/model 解析；没有适用的安全公开账户额度接口时返回 `unsupported / provider-quota-api-unavailable`，而不是猜测余额。
- Codex 的 profile 缺失、配置无法解析或 `model_provider` 没有对应定义时返回 `unsupported / provider-route-unresolved`；此时 provider 为 `unknown`，不会回退到 ChatGPT/OpenAI 账户探测。命令型 `model_providers.<id>.auth` 不由 Status 执行，避免额度页面触发外部认证命令。

`resource.reason` 是 credential-safe 的稳定 code。Status UI 必须翻译成人类文案，不得把 `rolling-window`、`api-wallet`、probe source 或错误 code 原样直出。

服务重启会恢复已经持久化的 terminalization intent，以及 TaskService 接受的 Agent 失败恢复意图。Status 与 CLI 从同一 `TaskView.runtime_recovery` 读取类别、累计次数、上限、到期时间、恢复状态与停止原因。等待期间 `lifecycle_stage=runtime-recovery-wait`、`next_actor=machine`、`is_processing=false`，且不占用智能体进程。取消或人工 Continue 使旧等待失效。

普通 Agent 执行失败沿用原 Agent 有界自动 Continue。受信的 Codex capacity、Codex usage limit 与 Claude＋DeepSeek context 超限按各自的策略恢复，所有自动恢复类别共用最多五次的持久预算。自动恢复范围由已接受的恢复意图决定，不创建全局 cooldown，也不从历史失败补造恢复权限。

Codex 明确拒绝音频输入时，该 Run 以失败结束，不创建自动恢复意图。操作者可在原任务选择能处理所需输入的 Agent 并显式 Continue。取消、超时、基础设施及交付故障也不进入普通续跑。失联 Run 不会被当成成功。完整规则见[执行模型](execution-model.md#agent-中断的有界自动-continue)。

## 安全与审计

- `/status` 必须部署在可信团队边界；更强身份认证和浏览器跨站策略由反向代理或上游网关提供。
- lifecycle mutation 前先做 action policy 检查；工作目录清理按终态、签发的 workspace id 和目录边界检查。
- Task/API response 继续使用明确投影，系统 response 继续执行 secret redaction；同权限不等于 credential 可见。
- audit event 至少记录 operation、Task、Run（如有）、actor/reason、结果和时间。

## 历史任务取代状态

取代关系按[执行模型的完整身份与成功条件](execution-model.md)核验，API 通过 TaskView 的 `supersession`、`monitor_status` 和 `actions` 展示结果，不改写原始 Task/Run 终态与失败记录。已证实取代的 Task 不产生用户待办，不允许 Continue 或 Cancel。仅 Subject 相同、裸 Task/Run ID 或名称相似不足以证明取代；操作者可通过 `jarvis-box tasks supersede <旧 Task> --by <成功 Task>` 建立经核验的关系。

历史只读 Run 的 progress 从登记证书绑定的 RunTrace 展示 Agent 输出；文件缺失、digest 漂移或 Run identity 不符返回 `503 historical-run-trace-unavailable`。未登记 trace 的历史 Run 返回空输出列表，状态仍可查看，不代表已恢复 Agent 对话。

## 软件更新

`GET /status/api/system/service/update` 返回 `ok` 和 `update`：`current_version`、`enabled`、`online`、`agent_available`、`phase`、`latest_version`、`ready_version`、`ready_id`、`last_checked`、`next_check`、`apply_pending` 和安全的 `error`。读取不联网、不下载、不重启。`online` 表示当前成功签到授予的短期后台联网资格，不是 license Run 门禁。

`POST` 同一路径只接受两种请求：`{"enabled":false}` 保存并立即通知开关；或 `{"version":"X.Y.Z","ready_id":"…","force":true}` 确认应用当前已验证候选。版本或候选已变化、执行器不可用、未确认中断时返回 409；安装请求幂等交给独立宿主执行器。执行器在允许后台联网时先复核稳定通道：`checking`、`downloading` 期间仍未停服；若准备了更新候选，则结束旧请求并返回新 `ready_version`、`ready_id` 及重新确认提示，不沿用旧确认安装其他版本。此接口使用既有系统设置认证与写保护，不接受下载地址、脚本或路径。应继续轮询，只有 `current_version` 等于请求版本才表示新版本实际运行；请求被受理不等于更新成功。

## 授权检查

`GET /status/api/system/overview` 的 `license_refresh_available` 表示本机是否接入授权检查。“重新检查”通过 `POST /status/api/system/license/refresh` 使用本机已有身份检查授权，完成后重读 overview；GET overview 和 SSE 读取不发起签到。在线授权调用正式签到接口，离线授权只验签本地授权，不联网，不创建或停止 Task/Run。

成功返回 HTTP 200、`ok=true` 和最新 `license` 面板。检查失败返回 HTTP 502、`license_refresh_failed`、用户可读的 `detail` 与最新面板；不返回原始上游响应或内部路径。未接入授权检查返回 HTTP 503 `license_refresh_unavailable`，非 POST 返回 HTTP 405。

CLI 可携带 `runs_dir` 查询参数核对所选运行目录；与服务实际目录不符时，在签到前返回 HTTP 409 `runtime_owner_mismatch`。省略该参数的 Status 页面操作继续检查当前服务。
