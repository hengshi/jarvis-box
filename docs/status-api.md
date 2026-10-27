# Status API

`/status` 是 Jarvis Box 唯一的人类界面，工作状态与系统设置共用同一可信团队边界。Jarvis Box 不为人类观看者定义角色，也不根据 `RemoteAddr` 切换权限；反向代理或上游网关负责需要的身份认证。

## 自动修复交付漏斗

`GET /status/api/issue-funnel` 聚合本机接入的 GitLab、GitHub、Jira、禅道、飞书项目、TAPD、云效工单的自动 post-check 链路，不按仓库、登录账号、页面来源筛选或运行趋势时间范围拆分。服务启动、工作项事件和每分钟补查会主动更新内存快照并通知页面，不依赖 API 请求。普通 GET 使用一分钟内的内存快照，`refresh=1` 重新采集；读取不启动 Agent 或改变 Task 状态。

禅道 `bug`、`story`、`task`、`case` 使用完整 Subject 身份分别统计，同号工作项不会合并。只有自动 post-check 受理计入入口，独立评论指令不增加受理数；识别为 Bug、开始修复及实际修复 MR/PR 的提交、合并仍分别要求对应证据，关闭禅道工作项不等于修复已合并。

- `scope=all-connected-work-items`；`generated_at` 是本轮同步时间。
- `stages` 依次为 `accepted`、`bug`、`bugfix`、`submitted`、`merged`，每层有去重工单数 `count`、记录是否完整的 `complete`、相对上一层的 `step_rate`、相对入口的 `total_rate`。`complete=false` 时 count 是已证实下限；分子或分母不完整、或分母为零时，相关比例为 `null`。Status 图表另外以已记录的 `count` 相除展示环节比例与总转化率，并明确标注按已记录数量计算；这些展示比例不表示完整历史转化率已确定。未知的零值或零分母仍显示 `—`。
- 身份包含 Provider、authority、project、kind（`issue` / `work_item`）、ID。代码仓库名称忽略大小写，其他工单项目保留稳定键；同编号的不同来源、实例或项目独立计数，同一工单的重试、多个修复和 backport 只计一次；任何一个实际关联修复合并即进入最后一层，不能据此声称全部版本修复完成。
- 原工单来源与修复代码平台独立：例如 Jira `APP-42` 或飞书项目稳定工作项可关联 GitLab MR / GitHub PR，不要求另建代码平台 issue。身份来自准入时保存的规范化 subject，不能用飞书 URL 的展示别名代替稳定项目键。工单关闭不等于代码修复合并。
- 入口按规范化工单身份合并平台留存的自动 post-check 回执与本机自动受理、post-check 启动/完成台账，支持 GitLab Issue Hook 的 `issues` 与 `work_items` URL；同一 issue 的 URL 写法和重试不重复计数。历史恢复必须独立发现平台回执，不能先以本机保留的 issue 集合限制平台查询。Bug 证据来自 workflow 的标准 metrics、post-check 已有 `workflow.start: bugfix` 建议，已发布 v1 post-check 评论中记录的明确处置，或实际 `workflow:bugfix` / 早期 `issue-execution` 启动/完成台账；自动修复必须有实际准入的子 Task或执行台账。历史结论只解析结论段中的既有 outcome / disposition，兼容 Markdown 加粗，不从证据段引用推导分类；明确的独立 command 启动记录不作为自动 bugfix 准入。查询从不启动分类任务。修复链接来自该 bugfix 的 metrics，或已发布 Task 级报告的明确交付字段；相关 feature 链接、本地准备、未推送补丁不算提交。匹配身份的平台记录可来自本机保留的 provider 读取产物，缺失时才查询目标平台。有效平台合并时间或带完整 host 身份的合并事件回执才计入合并；回执的 merge_observed_at 是本机收到事件的时间，不冒充 merged_at。独立 approve 不属于最后一层条件。
- `items` 返回原工单的 `subject`、`url`、已到达的 `stage` 与关联 `changes`（`url`、`verified`、`state`、`merged`），用于核对聚合结果。当前 Status 仅展示漏斗图、数量与转化率，不消费 `items` 或提供 issue/MR/PR 明细展开。不相关的 MR/PR、其他账号的独立提交不能补进该链路。
- `classification_unknown`、`repair_links_unknown`、`change_state_unknown` 分别表示 Bug 结论尚未确定（包括结果未留存或处置尚需证据）、自动修复尚无结构化修复链接（包括 metrics 缺失、空对象或空 change_requests 列表）、含任意未核验修复链接的 issue 数（即使同一 issue 已有其他修复合并，也保留该缺口）；有缺口时 `status=partial`，计数和比例表示已证实到达，不把等待或未知当成功。台账或任务读取失败时 `status=unavailable`，不返回伪零计数。
- 新运行观察以完整 Task/Run 世代去重，追加到已有工作台账的 `issue_funnel` 事件中；普通 Task 清理保留台账观察，删除台账则丢失相应历史。即时追加失败会记录警告；清理在固定的 Task 身份与锁内先从保留的 Run 产物幂等补齐观察，写入失败则返回清理错误并保留任务与产物。修复台账后重试普通清理即可，不重发 provider 动作或重新启动 Agent；dry-run 不写台账。清理保留同一 Task registration 已有受理观察的 identity；缺失时才以首个 Run 的身份补齐，尚无 Run 的 Task 使用空 Run 身份。历史基线复用既有自动受理/执行事件与保留 Task/Run 的 workflow 产物。离线回建从平台关联 MR 推导交付时，要求标题或关联议题字段明确引用该 issue，且具备修复分支，或同时具备对应 issue 的分支与明确修复标题，支持标准 `Issue / Issues / Related issue` 段中的完整工单引用及 URL，不能仅凭分支编号计入。原工单上可信自动执行后的明确修复回执可直接绑定其 MR/PR 字段，不依赖 MR 标题措辞；任意提及、背景链接或独立 command 回执不能建立交付关联。已有 feature MR 仍须有身份匹配的报告或原工单的明确交付回执记录本次修复已交付，且不能已在本次自动执行前合并。已发布 v1 存储的 Task 级 workflow 报告只在原始存储版本、Task 注册身份、workflow handle 与原工单身份及 URL 全部匹配时读取为历史观察，不创建 Run，不给现代 Task 增加根目录回退；已清理且无结构化证据的历史分类/修复链接无法还原。
- 离线工具消费已有台账、保留报告及已导出的规范化平台历史包；Jira/飞书项目历史只统计已留存或已导出的证据，不提供全历史自动采集。未留存的历史不能据此恢复成完整统计。
- 本机保留的平台记录按完整 provider/host/project/number 身份读取，可验证历史接入仓库的修复。实时 MR/PR 查询只允许当前配置的 GitLab host/projects 和 GitHub host/repositories，最多使用本轮 20 秒的查询预算；缺少本地证据且不可访问、身份不符或已移除配置的链接保持未知。

Workflow Runtime Contract 的 `workflow-result.json` 可报告以下独立于 opaque `outcome` 的观察字段：

```json
{"schema_version":2,"status":"completed","summary":"已提交修复","metrics":{"issue_type":"bug","change_requests":["https://github.com/owner/repo/pull/42"]},"actions":[]}
```

`metrics.issue_type` 为 `bug`、`other` 或 `unknown`；post-check 应报告分类，bugfix 应报告本次修复实际产出的 `metrics.change_requests`（最多 50 个）。已有 post-check 的标准结果/修复建议和真实执行台账可直接贡献统计，不要求历史任务补写 metrics；只有确实缺失的结果和修复链接保留证据缺口，不影响既有 workflow。metrics 不授予 provider action、workflow.start 或 lifecycle mutation 权限；runtime 不读取客户自定义 disposition、decision 文件或自然语言总结推断这些观察。离线历史恢复工具可将已发布 v1 评论的明确处置、身份匹配的 Task 报告交付字段与实际修复关联规范化为既有台账观察；它保留原始证据摘要、`snapshot_as_of` 与 `recovered_at`，不启动任务或重写源台账。恢复使用受信发布身份、版本化自动回执或绑定本 issue 的自动创建任务审计标记；普通评论提及、复制其他 issue 的结论、独立 command 重跑及当前 Bug 标签均不能建立自动受理入口。历史自动化发布账号可显式补充，不能只统计当前登录账号。平台已删除或未发布回执且本机记录也已丢失的历史无法证实，已记录入口数不等于保证完整的终身总数。已有 feature MR 只有明确记录本次修复已经交付到该 MR 才能贡献提交阶段。

## Status 读模型

`GET /status/api/ledger` 提供本机工作台账的分页读取。`kind=accepted`、`started`、`completed`
分别选择受理、运行启动和完成事件，`limit` 控制每页窗口。response 包含 `ok`、`events`、
`has_more`、`next_before` 和读取时间 `ts`。继续读取时把 `next_before` 原样作为 `before`
参数传入，直到 `has_more=false`；游标是不透明值，不代表事件时间或业务身份。
事件包含 `event_id`、`kind`、`ts` 及相应观察字段；完成事件中的有效
`detail.runtime_duration_ms` 是已记录运行耗时，缺失不表示零。台账属于保留的历史观察，
其受理、启动和完成条数不必等于当前仍保留的 Task/Run 数。

`GET /status/api/work-items` 返回：

- `items` / `count`：当前分页窗口。
- `total`：所选来源范围内的工作项总数，不受分页 `limit` 影响。
- 可选 `provider` 在分页前筛选 Task 的规范化来源。支持值由服务端 provider 注册信息定义，与页面来源选项一致；包括 `gitlab`、`github`、`jira`、`feishu-project`、`tapd`、`zentao`、`yunxiao-projex`、`yunxiao-codeup`、`im` 和 `jarvis-box`，未注册的筛选值返回 HTTP 400；`lark`、`wecom`、`dingtalk`、`uvim` 等消息来源归入 `im`。response 的 `provider` 返回实际筛选，未筛选时为 `all`。
- 分页游标绑定生成它的 Provider 范围；游标不能跨 Provider 重用，避免页间混入其他来源。
- `metrics.historical_accepted_count`、`metrics.started_run_count`、`metrics.active_task_count` 和 `metrics.task_run_trend` 是本机指标；`provider` 筛选只改变工作项列表及其分页数量、总数，不得改变这些机器级指标。`recorded_task_count` / `recorded_run_count` 只表示当前保留记录。
- 每个 item 的 `provider` 是 Task subject、run context 或 source URL 的保守规范化投影，不改变外部 Provider 的权威对象。
- IM item 可返回 `requester_display_name` 和 `conversation_display_name`。它们是入站消息时的可选展示快照，用于 Status 文案、搜索和按发起人筛选；缺失时继续使用 provider-scoped sender ID / Task ID，且永远不替代 Target、ACL、排重或回复路由使用的稳定 ID。
- 每个 item 的 `status_group` 来自同一 TaskView，取值为 `ready`、`doing`、`needs-human`、`failed`、`completed` 或 `historical`；`all` 仅用于筛选和总数，不是工作项状态。客户端不得从状态或错误文案重复推断分组。
- `metrics.task_run_trend` 返回从首条运行记录到本机今日、按自然日聚合的 Agent Run started 趋势，来源为工作台账中的 `kind=started` 追加事件；无运行日期补零。该趋势是机器级口径，`provider` 筛选只影响 work items，不改变 trend 统计。
- `metrics.task_run_trend.runtime_duration_ms` 返回本机工作台账中已完成运行记录的耗时合计，来源为 `kind=completed` 事件携带的运行耗时字段。它是本机工作台账可观测口径，不代表机器在线时间，也不等同于当前保留 Task state 的 Agent 执行时长。
- 历史受理、累计启动数和已完成耗时分别返回 `historical_accepted_metric`、`started_run_metric`、`completed_runtime_metric`，包含 `status`、`value` 和 `as_of`。账本不可完整读取时，Task 列表仍返回 HTTP 200；账本指标为 `unavailable`，数值兼容字段与 `as_of` 为 `null`，不把未知显示成零。当前没有持久化历史 rollup 回退。
- 完整可读账本中，部分完成记录缺少有效耗时时，`completed_runtime_metric` 返回 `status=partial`、已记录耗时合计和本次 `as_of`；两个耗时数值兼容字段返回相同下限。该值不能作为完整精确合计，页面以 `≥` 展示。全部完成记录都缺少有效耗时则为 `unavailable`；无完成记录为 `empty`、值为 0。单条缺少耗时不影响其他指标，也不触发历史任务重跑。
- `metrics.run_duration_statistics` 返回已结束 Run 的平均耗时、中位耗时、有效样本数、缺失耗时数及按 lane 拆分的同口径统计，详见[运行耗时统计](#运行耗时统计)。

分组与处理责任由同一版本的 TaskView 统一决定，工作项和 feed 不从旧 `monitor_status`、phase 或错误字符串重新分类。磁盘准入等待属于 `doing`、由机器恢复，不计入管理员需要处理数量；后继 Run 成功并完成必需交付后，Task 与工作项可进入 `completed`、`next_actor=none`，旧失败 Run 仍作为历史保留。取消终态同属 `completed` 分组，但 `terminal_outcome=cancelled`，不能当作成功交付。缺失、冲突或未知的安全事实按执行模型保守投影，不由历史状态文案推定完成。

`GET /status/api/tasks` 和单 Task detail 返回 Status task projection。默认读路径只读取 Task state 和 bounded Artifact metadata；单 Run progress 只在 exact `TaskView.runs[].prompt_artifact_id` 指向 canonical `prompt.txt` 时投影其 bounded、redacted Run 输入，并把 Runner-owned RunTrace 作为进程输出时间线。Run 输入是真正交给 runtime agent 的当次指令：人机会话可以是用户原文，workflow lane 可以包含服务端生成的契约、运行上下文和主机路径。它不得包含可用 credential、private resume handle 或 raw provider secret，也不得从 native AgentSession 或跨 Run history 补齐。

RunTrace 和结果产物的公开输出会脱敏原生会话、线程和恢复句柄以及凭证字段；原生 hook 或工具结果将 JSON 或逐行 JSON 嵌在字符串中时，内部字段同样脱敏。普通业务 ID（包括 UUID）和非敏感正文保留，不仅凭 UUID 格式判断敏感内容，私有原始日志不因此改写。

`GET /status/api/tasks/{task_id}/result` 读取所选 Run 的结果文件：MR/PR 评审读取已冻结的发布正文，其他运行读取 `result.json`，只读历史运行读取已登记的同名产物。没有该产物时返回 `503 task-result-unavailable`，不改变 Task 或 Run 的执行结果。普通聊天的最终文字通过 `progress` 输出时间线查看，其他产物通过文件接口查看；系统不把最后一条聊天文字伪装成结果文件。

单 Task 查询接受 Task id、当前/最新 Run id，也接受仍保留 `run-state.json` 的历史 Run id。使用 Run id 查询时返回其所属 Task；Run id 不会被当成 Task identity。

精确搜索只改变 Task/Run 的详情焦点，不新增工作项或改变列表统计；位于当前分页之外的任务也只作为独立详情展示。

`GET /status/api/related-tasks?task_id={lookup_id}` 返回同一不可变 Target 的相关 TaskView，以及 `count` 和 `total`；可选 `limit` 默认20、最大50。使用 TaskView 的 opaque `lookup_id`，可同时传入已冻结的 `task_view_revision`。此列表与工作项内嵌 `related_tasks` 消费同一投影，不从相同标题或项目编号猜测归属。

Catalog 返回 `task_view_revision`，`snapshot_hash` 和分页游标使用同一版本。页面随后读取 Task、progress、result、related Tasks、Artifact root/list/content 时必须携带该版本；不匹配返回 `409 task_view_revision_changed` 和当前版本，成功 JSON 同样回显版本。浏览器只对只读请求有界重读 Catalog 并重试，丢弃过期响应；修改操作冲突后不自动重放。没有版本参数的读取只用于非 Catalog 客户端。

单 Task 详情包含同一版本的任务及工作区信息。未固定 Catalog 版本的读取遇到正常并发状态变化时有界重读完整详情；固定版本在组装详情期间发生变化仍返回 `409 task_view_revision_changed`，不混合两个版本。持续变化或其他投影故障仍可返回不可用；读取重试不会重新提交任务动作。

HTTP 修改操作要求 TaskView 的 opaque `lookup_id`。CLI 的 `tasks start/continue/cancel <task_id>` 会先读取严格 TaskView，冻结 `lookup_id`、`task_revision` 与操作所需 Run，再提交请求；读取后 Task 变化会返回冲突，不重新选择另一个 Run。

单 Task detail 的 `workspace_locations` 是唯一个结构化工作区路径字段，用于建立 Task 与可清理工作目录的明确关联。每项只包含服务端生成的 opaque id、显示标签、绝对目录、存在状态、删除资格和原因；其他主机路径只能作为 bounded Run 输入文本或系统设置 response 出现，不得变成 Task 身份或 Workspace ownership 来源。

IM Agent Run 成功但 final reply 未送达时，Run 仍保持 `succeeded`；Task detail 从同一 exact Run typed effect receipt 投影 delivery 结果。`succeeded/skipped` 收敛为完成，definite `failed` 且 `retryable=true` 投影为 `needs-attention` 并提供 `actions.continue.strategy=writeback`、`requires_input=false`；该 Continue 只重试同一 Run 的 delivery effect，不创建新 Run、不读取公开 `reply-error.json` 授权重发。旧版本保存的 `chatbridge.reply / reply-handle-unavailable / not-attempted` 失败即使 `retryable=false`，也保留显式 writeback 恢复能力：原历史字段不改写，仍需同一 Run 的完整私有交付收据，实际发送前重新校验原回复权限。`unknown` 表示外部结果不可证明，系统不自动重发；此时 policy 在 `actions.continue.attestations` 里列出 `delivered` / `not-delivered` 两个人工裁定，由人查证目标系统后经 attest-delivery 落成一条新的 effect attempt receipt。receipt 可包含 provider/connector、source、category、retryable、delivery_state、upstream HTTP status、provider code、Retry-After 和 request id 等脱敏字段；不包含 raw provider body。

附件已发出但超时未知时，Jarvis 在原 IM 会话询问是否收到；确认消息成功发送后，TaskView 为 `status_group=doing`、`lifecycle_stage=waiting-input`、`next_actor=user`、`blocker_kind=reply-awaiting-confirmation`。明确收到会完成原 Task；明确未收到使用现有裁定与写回重试，不新建 Agent Run。附件超出渠道大小或图片尺寸限制时，原会话收到具体限制与交付位置询问，对应 blocker 为 `reply-attachment-limit`。两者均不计入管理员需要处理数量。

原IM用户明确只缺未确认集合的一部分时，effect历史可包含`attestation=missing-attachments/v1`及`missing_attachments`文件名数组，表示只补这些文件、其余按原用户声明收到；它不等同于平台发送ACK。该选择保留在同一Run的裁定与交付历史中，内容再次核验后仅补缺少部分。Status的`attest-delivery`请求仍只接受policy列出的`delivered`/`not-delivered`，不从展示字段授予新发送权限，也不接受附件名单。

`runs[].failure` 保留启动失败原因与脱敏详情。尚未启动的 Run 不返回零值 `started_at`；客户端使用 `created_at` 展示创建时间，并标明“未启动”。typed `storage-wait` 为机器等待，磁盘恢复后自动继续，历史 Run 的失败记录仍保留。

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

长期在线约束：

- 首屏读取一次 list/work-items，后续通过一条 SSE 连接接收变化。
- 未变化的 SSE tick 不得全量扫描 `runs_dir`。
- 只对选中的 Task 读取 bounded event/log tail。
- Artifact 内容只在用户显式打开时读取。
- 多个浏览器标签共享服务端 projection/cache。

授权面通过同一 SSE 连接的 `license` 事件更新。两个 Status SSE 端点的载荷均为 `license: {problem, expiry?}`，不包含安装、机器或授权身份字段表；连接建立、后台签到失败及每 15 秒心跳时读取本地快照，不扫描任务目录或访问授权服务。系统设置接到事件后通过 `GET /status/api/system/license` 重读完整授权面板，该读取不收集 Task 状态、不签到。页面只渲染服务端给出的结论，不从字段表重算授权。工作项首个响应的 `server.license_expiry` 同样承载可选顶栏提醒（`text`、`detail`、`level=warn|overdue` 和可选 RFC3339 `expires_at`），不依赖 SSE 可用。`expires_at` 是服务端已选定的到期时刻，浏览器只用它按自身时区展示提醒日期，不据此重新判定授权是否有效；API 时间保留原始时刻与时区信息。

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

Provider merge 是 provider-native 工程交付 proxy，不代表终端客户业务验收。登录账号 change request 只按 author 识别，不涵盖该账号在其他作者 MR/PR 中的贡献；Jira、飞书项目、跨来源关联、聚合和去重均不在此 response 中。

同一 snapshot 保留 `runtime_token_usage` 兼容字段，但 Status 页面不展示运行 Agent token KPI。按 runtime agent 再按 model 汇总 `session_count`、`input_tokens`、`output_tokens`、`cached_tokens`、`reasoning_tokens` 和 `total_tokens` 是 EM-METRIC-002 这条 receipt 分支打开后的前向契约，`status` 的 `partial` 与 `known` 两种取值同属该分支：`known` 只能由某个 Run 自己的 typed final-cumulative receipt 产生，adapter 必须能给出独立稳定的 final usage event identity（`docs/execution-model.md:502`），而当前接入的 Codex 与 Claude adapter 都还没有它，所以该分支现在必须保持关闭。因此当前 release 该字段恒定是空壳：`status=not_available`、`agents` 为空数组，整体、agent 级和 model 级 `session_count` 与 `unknown_session_count` 以及五类 token 数都是 0。无论 Run 有没有 token metadata，接口都不会失败。`window` 固定标为 `retained-task-state`，代表当前保留 Task 记录内的运行用量，不等同于 Provider merge 历史累计窗口。接口不返回价格、预算、费用预测或 raw native session 内容，也不从 stdout/stderr、result JSON、全局 home session、文件 mtime 或目录存在推断用量。

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

Task response 的 `actions` 恰好使用以下 key：

```json
{
  "start": {"enabled": true, "reason": "inactive-source-task", "requires_input": false},
  "continue": {
    "enabled": true,
    "reason": "task-ready",
    "strategy": "agent",
    "requires_input": true
  },
  "cancel": {"enabled": false, "reason": "terminal-task", "requires_input": false}
}
```

三个 key 一律带 `requires_input`，`false` 也上线、不省略：页面按 `requires_input !== false` 判，键缺失会被读成 true，于是把不收输入的操作当成要输入。`strategy` 只属于 Continue，无策略时省略。

后端 policy 是唯一授权来源。UI 和 CLI 不自行推断 enabled 状态。所有生命周期 mutation 写入 audit event。

### Start

`POST /status/api/tasks/{task_id}/start?reason=...`

- 选中的 Task 只是 source。
- 创建新 Task、新 AgentConversation 和首个 Run。
- 成功结果中的 `task_id` 是新 Task，`run_id` 是它的首个 Run；两者不能混用。
- 原 Task、Run 和 Artifact 不变。
- source active、`needs-attention`、完成但仍缺产物/写回、进程 ownership 未解决或 lane 不支持时返回 `409` 和明确 reason；先 Continue 或 Cancel 原 Task。

无 source 的原子 Start 使用 `POST /status/api/tasks/start`（人类 gateway，`jarvis-command`）或 loopback-only `POST /server/api/tasks/start`。JSON body 为 `prompt`、可选 `reason` 和 `lane`。服务端生成 Task identity、登记 intake、创建首 Run、启动并返回真实 Task/Run identities。Runtime Foundation 的 host scheduler 只从 loopback internal route 使用三个 allowlisted lane；internal launch authority 由该路由与 lane 共同推导，普通 Task、远端调用和 provider lane不会继承。

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
- Task action 使用同一 Task projection 中的 canonical source Run：普通 Continue 使用 latest operational Run，recovery 使用 policy 指定的 recovery source。页面选中的历史 Run 只控制浏览，不能改变 Continue source。服务端验证完整 Task/Run identity、revision、sequence 和 canonical 路径；命令冻结后 source 已变化则返回冲突，不重选新的 Run。
- 同 agent 且 private handle 有效时使用 native resume；其他情况创建 child AgentConversation，并以 `agent_strategy=native-resume|new-agent-conversation` 说明选择。
- Continue 遇到 active Run 时，服务端先同步解决旧 Run ownership，再创建后续 Run；失败返回 `409 run-stop-failed`。
- `actions.continue.strategy=recover` 且 `requires_input=false` 时不提交 `agent` 或 `message`，由 TaskService 消费 sealed recovery plan。lost-Run recovery 是内部旧 Run 收敛；正常 idle、等待 CI、网络或模型响应不能触发 recovery。
- `actions.continue.strategy=writeback` 且 `requires_input=false` 时，本端点提交 TaskService sealed retry plan，只重试当前 latest exact Run 中可恢复的确定失败 delivery receipt，包括上文限定的历史回复权限预检失败。请求不得携带 `agent` 或 `message`；成功或失败都追加新的 effect attempt receipt，不创建 Run。
- 首次IM文件预检明确未发送且具有exact-Run私有预检凭据时，文件修复后也使用上述writeback操作。原回复文本保持，重新核实合法文件与原目标；预检凭据不等于完整附件内容回执，不授权未知结果重发。
- `actions.continue.attestations` 是独立的人工裁定闭集，当前只有 `delivered` / `not-delivered`。reason `writeback-outcome-unknown` 时 Continue 本身 disabled，exact Run 的 effect receipt 是 `unknown`，系统不自动重发。IM 等待原用户确认时，普通 `strategy=agent` Continue 仍可提交新指令，同时可列出对原未知交付的裁定；两种动作不能互相代替，也不创建管理员待办。两个值由 policy 给出，通过下面的 attest-delivery 端点提交；页面不得从 `effects` 自行推断。不可重试的明确失败只列出 `delivered`：操作员实际核对已送达后可收尾，不能借裁定启用自动重发。文件超限等待不因此开放未知结果裁定。
- Task identity 始终不变；旧 Run prompt 不读取、不复制，新 Run 持久化的 prompt 只包含本次新输入。

### 人工裁定投递结果

`POST /status/api/tasks/{task_id}/attest-delivery?delivery={delivered|not-delivered}&reason=...&run_id={source_run_id}`

结局未知本来是死路：系统不许自动重发（可能重复投递），于是 Run 成功、外部动作却没着落，任务永久停在 `needs-attention`，而 `strategy=writeback` 分支又把通用的继续/取消挡在外面——页面上的继续和取消全是灰的。人能做的只有去目标系统看一眼，这个端点就是把人看到的那个事实写进账本。

- 只收 policy 在 `actions.continue.attestations` 里列出的值；没列出时返回 `409` 和 policy 的 reason（不是页面自己编的码）。
- `run_id` 只能是 Task 当前的 latest Run；指向别的 Run 返回 `409 attest-source-stale`。`task_revision` 与其余 mutation 一致：不匹配返回 `409 task_revision_changed`。
- 不接收 `agent` 或 `message`，不启动 runtime 作业、不创建新 Run：它写一条新的 effect attempt receipt，`attestation` 字段记录人给的那个事实。
- `delivery=delivered`：这条 effect 记为 `succeeded + delivery_state=delivered`，Task 收敛到 `completed/completed`，Run 仍保持原来的 `succeeded`。
- `delivery=not-delivered`：记为确定的 `failed + retryable=true + delivery_state=not-delivered`；Task 停在 `needs-attention`，policy 随后给出 `actions.continue.strategy=writeback`，由上面那条原地重投接手。响应中的 `writeback` 如实回报重投起没起来（`{"started": bool, "reason": string}`）——没起来不是裁定的失败，事实已经落账。
- 一条未知结局只许裁定一次：之后 policy 不再列出 `attestations`，再提交返回 `409`。裁定不许改写原回执，只追加后继 attempt，因此未知回执仍严格是 attempt 链的终点，唯一例外是这条带裁定的后继。

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

TaskService 在首个 Run claim 之前一次登记 Task identity 和初始工作区，再逐项创建、clone 或 checkout。物化尚未成功时 canonical Task status 保持 `accepted` 且没有 Run，Status 将这种无 active Run 的 accepted Task 归入等待项；原入口 receipt 另带 `waiting=true` 和 `workspace-materialization-wait`，但不会创造 `waiting` / `storage-wait` Task status。此时可以 Cancel，不能以 Continue 越过自动恢复。Runner 向每个 runtime agent 注入相同的 Workspace ownership contract；运行中的 zero-workspace Task 必须以 `jarvis-box workspace create --id primary` 建立第一个仓库，非空 registry 后续增加仓库时使用普通 stable id。Agent 不得绕过该命令创建、替换或物化 `JARVIS_WORKSPACE_ROOT` 的任何直接子项。该命令先验证当前 Run 仍持有 Task，并在原子 state mutation 中追加登记，登记落盘后才创建目录。Status detail、Continue、自动清理和手工清理都只读取 `task-state.workspaces[]`；`cwd`、`workdir`、`run-context.json`、artifact 文件和目录扫描都不是 workspace 归属来源。

所有 lane 使用同一登记规则，不设客户工作流白名单。普通 Run 成功后保留工作区至持久化清理截止时间，由后台按登记回收；完成回写不以提前删除工作区为前置条件。取消及已验证的外部主体终结属于立即清理边界：非终态 Task 先持久化 cancellation intent、停止运行并提交取消终态，再在释放 Task/state locks 后清理全部登记项。已有 completed/cancelled Task 保持原终态，只重试登记式处置。清理失败、unknown 或退避保留独立的处置义务和原因，不把已提交终态改回 `finalizing` 或 `needs-attention`；并发 Continue 仍须通过原处置 fence。

Task 创建时会把 GitLab/GitHub/Jira/Codeup 外部工作对象登记成规范化 `task-state.subject`。GitLab issue `close`、MR `close/merge`，GitHub issue `closed`、PR closed/merged，Codeup MR close/merge，以及 Jira issue 进入 Done category 或被删除时，provider adapter 调用同一个终态入口：非终态 Task 先停止并转为 cancelled，再清理全部登记目录；已有终态只重试清理。首次处理 terminal delivery 时，服务先把当时精确匹配到的 Task registration 与 Run fence 集合原子写入 receipt，再做任何取消或清理；部分失败、进程退出或磁盘故障后的 retry 只重放这份快照，不重新扫描 Task。关联只来自创建时的 subject 登记，不从 `issue_or_mr` 文本、workspace 路径、Artifact、branch 或 lane 反推。仍未生成任何 Run 的 accepted Task 不会因正常工作区重试推进状态版本而丢失取消义务；只在同一 Task registration、current/latest 为空且两类 Run 集合仍空时重验并取消，旧零 Run 快照不能跟随后来认领的首 Run。

GitLab/GitHub 的最终评论如果返回 HTTP 404，delivery owner 会用同一个 provider 身份检查目标项目或仓库。目标项目或仓库仍可访问，而 issue、MR 或 PR 已不存在时，Task 进入与 provider terminal event 相同的登记式清理流程；先提交 `cancelled`，成功 Run 保持 `succeeded`，再清理 Workspace 和 typed external resource。清理失败保留取消终态及独立处置义务，由处置流程恢复，不重新执行 Agent 或 provider writeback。项目/仓库不可访问、鉴权失败或配置错误仍记录为对应 exact Run 的 provider delivery effect 失败，不会被转换成取消。

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
- opaque safe Artifact ref
- Task detail 中显式建模的 `workspace_locations`，包括该 Task 工作目录的绝对 `location`

禁止：

- 作为结构化字段的 `task_dir`、`run_dir`、log 路径，以及 `workspace_locations[].location` 之外的任意 Workspace 绝对路径
- native AgentSession id/file
- private resume handle value
- cross-agent source ref
- raw payload、provider token、reply token、`prompt.txt` 原文或跨 Run prompt/history
- process command、argv、env、pid/pgid

Status Artifact endpoint 只解析经过授权的 safe ref。普通 `/status/api/tasks/{task_id}/artifacts` 只列出所选 exact Run 的 safe artifact，不返回文件内容；工作台读取文件内容或浏览该 Task 已登记工作区时使用仅接受 loopback 请求的 `/status/api/system/tasks/{task_id}/artifacts`。两条路由都拒绝 `payload.json`、legacy `meta.json`、`run-context.json`、`prompt.txt`、`run-trace.jsonl`、`task-state.json`、`task-events.jsonl` 和 runtime logs，并在返回文本前执行 redaction。`prompt.txt` 与 RunTrace 只能通过 exact Run progress 的 bounded/redacted 投影读取，不能通过 base64 封装绕过文本 redaction。

## 系统设置 API

`/status/api/system/*` 为 topbar 系统设置面板提供：

- `GET overview|agents|doctor|crons`：实例、Agent、诊断、内部轮询与已脱敏配置；`overview.license` 返回本机授权字段表 `rows`、需要处理的原因 `problem` 和可选到期提醒 `expiry`，与 `license status` 使用相同本地快照，不联网；
- `POST agents/current`、`POST|DELETE agents/scopes/{scope}`：默认 Agent 和 lane scope；
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
- 同一 Provider 和 `account_ref` 的实时查询在一次 request 内去重。普通 GET 复用 60 秒 snapshot，避免浏览器重连和系统事件反复查询计费方；`refresh=1` 跳过 snapshot，供“重新检查”使用。每类上游查询最多等待 5 秒；失败只投影到对应 `resource`，不让 Agent inventory 整体失败，也不发起模型推理。
- Anthropic、OpenAI API、GitHub Copilot、Google AI / Vertex AI 和自定义网关当前只做 provider/model 解析；没有适用的安全公开账户额度接口时返回 `unsupported / provider-quota-api-unavailable`，而不是猜测余额。
- Codex 的 profile 缺失、配置无法解析或 `model_provider` 没有对应定义时返回 `unsupported / provider-route-unresolved`；此时 provider 为 `unknown`，不会回退到 ChatGPT/OpenAI 账户探测。命令型 `model_providers.<id>.auth` 不由 Status 执行，避免额度页面触发外部认证命令。

`resource.reason` 是 credential-safe 的稳定 code。Status UI 必须翻译成人类文案，不得把 `rolling-window`、`api-wallet`、probe source 或错误 code 原样直出。

服务重启会恢复已经持久化的 terminalization intent，以及 TaskService 接受的三类原生终止恢复意图。`TaskView.runtime_recovery` 提供类别、累计次数、上限、到期时间、恢复状态与停止原因；Status 与 CLI 读取同一投影。等待期间 `lifecycle_stage=runtime-recovery-wait`、`next_actor=machine`、`is_processing=false`，不占用智能体进程；取消或人工 Continue 使旧等待失效。仅受信的 Codex capacity/usage limit 与 Claude＋DeepSeek context 超限允许有界自动 Continue，不创建全局 cooldown，不扫描历史失败补造权限。其他执行态恢复仍由用户选择 Continue/Cancel，失联 Run 不会被当成成功。完整规则见 [执行模型](execution-model.md#原生终止的有界自动-continue)。

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

历史只读 Run 的 progress 从登记证书绑定的 RunTrace 展示 Agent 输出；文件缺失、digest 漂移或 Run identity 不符返回 `503 historical-run-trace-unavailable`。未登记 trace 的历史 Run 返回空输出列表，状态仍可查看，不代表已恢复 Agent 对话。

## 授权检查

`GET /status/api/system/overview` 的 `license_refresh_available` 表示本机是否接入授权检查。“重新检查”通过 `POST /status/api/system/license/refresh` 使用本机已有身份检查授权，完成后重读 overview；GET overview 和 SSE 读取不发起签到。在线授权调用正式签到接口，离线授权只验签本地授权，不联网，不创建或停止 Task/Run。

成功返回 HTTP 200、`ok=true` 和最新 `license` 面板。检查失败返回 HTTP 502、`license_refresh_failed`、用户可读的 `detail` 与最新面板；不返回原始上游响应或内部路径。未接入授权检查返回 HTTP 503 `license_refresh_unavailable`，非 POST 返回 HTTP 405。

Workflow 的 provider action 省略 `provider`、`project` 或 `subject_id` 时，从已校验的 `workflow-input.json` 原始 subject 补齐；显式不一致的目标仍拒绝。在执行任何 action 前发现结果格式不合法，属于明确未发送的本地预检失败，可修正结果后重试，不标记为投递结果未知。
