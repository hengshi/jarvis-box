# 存储模型

本文面向实现或集成 jarvis-box 持久化、升级、备份、恢复、状态读取和 Artifact 访问的工程人员。它定义发布数据的跨版本合同：哪些文件和字段是 authority，哪些内容只是可重建投影，何时允许升级、恢复、保留或清理；不是安装指南。客户操作入口请从 [文档目录](README.md) 开始，运行时配置路径见 [配置参考](configuration.md)。

jarvis-box 使用 artifact-first storage：每个 Task 的 `task-state.json` 是当前状态，`task-events.jsonl` 是审计事件流，exact Run 的 Artifact 是该 Run 的证据。Task store 是由 `JARVIS_RUN_DIR` 选择的 Task/Run Artifact 根。Status 内存发布、Delivery Metrics 快照、缓存和索引都是可重建的派生读取，不新增持久状态 owner、全局 FIFO queue、prompt history store、Redis、SQLite 或 status projection database；私有 handle、凭据和原生会话材料不属于公开投影。

本文件只拥有存储格式、持久化归属、兼容读取与恢复边界。Task/Run 的业务状态、生命周期操作、事务语义和唯一业务 owner 以 [执行模型](execution-model.md) 为准；不得从目录名、mtime、日志、派生缓存或可读 Artifact 反推或另行授予业务操作权限。建议先读 schema 与路径、再读“版本升级与数据兼容”和“Authoritative State”；查 Task/Run 文件边界读“Task Directory”与“RunTrace 与 Native AgentSession”，查 Workspace 与清理读“Workspace”与“Clean”，查外部投递恢复读“Webhook 受理与恢复”。任何格式变更都必须同时保留本文件中已发布的 decoder、Flyway identity、字段和恢复限制。

Task 当前写入 schema 7，状态为 running、completed、failed、cancelled，不设置 waiting。准备、执行、输出修正与收尾沿用已有 intent；执行成功且输出有效后为 completed。交付失败、附件超限、等待送达确认、交付重试失败或用户未收到只记入交付回执，不把 Task 改成 failed/running。failed 表示真实执行或输出校验失败。

新 Run 写入 schema 4，必需交付合同固定 kind 与产物引用，不写 finalization_failure_mode。新 pending launch 写入版本 2；旧版本 1 和旧 Run schema 2/3 的 failure-mode 字段只按已发布合同读取，旧 intent 保留其原引用。已发布 Run 不自动重写成 schema 4，同一 Task 可以保留不同格式的 Run 历史。

已发布的 schema 1/2/3/4/5/6 Task 经原版本解码读取，并由既有 Flyway 清单中的追加迁移在启动租约之前发布新版格式。schema 1–4 继续适用各自已发布的 lifecycle reader 和业务纠正规则；schema 5 和 6 的格式升级保留业务状态、intent、结果和 Run。schema 4 的可选 native-publication aggregate 在历史 Task 上保持为空：迁移不从 outbox、附件、effect、binding 或私有文件回填 batch、grant、claim、重试或消息。`effect_retry_intent` 可选的 `native_publication_observe`、`native_publication_observe_ordinal` 与 `native_publication_observe_receipt_count`，只标记已封存 native batch 中一个已为 `unknown` 的 claimed ordinal 的 Observe-only 后续核对；缺少任一字段保持已发布的行为，不推导核对权限。封存基线将原 `unknown` 及至多两次后续 Observe 限为三条 ordinal receipt，恢复不得重置该预算。该标记不含 Publish、Agent、Run、manifest 或目标选择；迁移不为历史 Task 补造它，也不改变历史 Run 或已有 receipt。迁移也读取尚未发布的 aggregate WAL：保留原身份、revision、pending/intent、交付事实与 Run 结果，消费原事务，不另起模型调用、补发消息或重算指标。Task 格式变化不改写已发布 schema 3 Run 的字节；重复迁移与普通 Task 更新同样保留未变化的 Run 文件。

Task 和 Run 可保存受理时的 `topic`。`topic` 只保存受理时已脱敏、受限且带来源的主题材料，不能从 `prompt.txt`、trace、原生会话或目录名猜测回填。历史 Task 缺少 `topic` 且其来源标题只是内部编号时，公开投影只可在严格 aggregate 已验证后读取首个 Run（`sequence=1`）的 `accepted-request.json.admitted_original_prompt`；文件内完整 Task/Run identity、lane 与 Task/Run 路径都必须精确匹配。匹配文件本身也不证明它是原始用户材料：仅已发布 Status 原始 HTTP 请求的、没有 source Task/Run 血缘的 `TargetManual` `jarvis-command` 或 `TargetCustomJob` `custom-user-task`，以及具有相同 `command_text` 的首个 IM `chat-command` 可用。`custom-user-task` 的调用方（包括客户 scheduler）经 loopback Start 提交完整原始 prompt，故属于前述 `TargetCustomJob`；旧 scheduled lane 的 `TargetScheduled` 不属于它。已发布的 provider command writer 会把拼装后的 prompt 写入 `admitted_original_prompt`，不能由该字段回推原评论；provider 历史记录保持未命名任务。continuation、source Start、recovery、`TargetScheduled`、其他程序任务及任何缺少上述来源证明的记录一律不用，并回退到未命名任务。该 artifact 只在严格 aggregate 加载时读取一次，投影不再 I/O。

schema 7 在源 Task 的稳定执行结算时追加不可变 `RecapInput`：它固定 Source Run 的完整 generation、策略版本、经脱敏的有来源材料及其摘要，不含 Run 执行状态。策略版本是 `RecapInput` 的已封存字段，后续发现、恢复或二进制升级不得从当前全局常量重新计算它。它不得从旧 topic、`prompt.txt`、trace、会话、目录或旧 recap 结果猜测回填。源 Task 仅可另存已经绑定完整 Analysis Run identity 的脱敏标题结果；不保存分析 Task 的 pending/started/terminal 状态、队列、进程或私有用量。关联 `task-recap` Task 的确定性身份由 Source Task registration、Source Run generation 和封存输入摘要构成；该 Task 的普通 Task/Run 是唯一的执行、恢复和既有普通 Run 用量投影 owner。缺少可核验 token/cost 事实时，该投影保持 unknown，不伪称为零或已知。标题结果只在 Source Task registration、Source Run generation 和输入摘要仍匹配时写回，迟到结果只留在关联 Task 的审计中。公开 `TaskView` 只投影已脱敏的 `title`、`display_title`、`display_title_source` 及有限的 recap 状态，不公开 topic、`RecapInput`、关联 Task identity 或其输入；完整脱敏的来源标题保留给检索；来源标题和请求的展示摘录最多 4096 UTF-8 字节，消费者再按显示宽度渲染省略；读取页面不会调度或执行 recap。

schema 7 是有意的旧 writer 边界：只认识更早 Task 格式的二进制必须拒绝 schema 7，而不能加载后覆写并丢失 `RecapInput` 或标题结果；回退只能先恢复到 schema 7 前的完整存储快照，不能用旧 writer 处理已发布 schema 7。Run 继续写入 schema 4，terminal Run 不因标题材料或结果而改写。

Webhook 原始认证输入保存在既有投递 journal，当前新记录标明 `webhook-intake/v1` 恢复协议。已启动但未结算的旧记录没有此证明时只保留诊断，必须由本机明确 `webhooks retry` 恢复；迁移不替旧记录补造自动执行权限。`pending` 的从未派发输入仍由原受理队列交接。评论入缓冲后保留原输入直至实际交接，`pending-comment` 查询只反映缓冲情况，Task/Run 及其去重继续归唯一 admission ledger。

会话过渡期间的新指令保存在同一 Task 的 `pending_continues`，每项具有唯一 ID、受理时间、原输入及原适配器重建材料，不保存进程回调。TaskView 只公开数量，不公开材料。追加与后继 Run claim 受同一生命周期锁和 revision 保护；受理内容不可改写，claim 后先发布输入 Artifact，再移除等待项。原适配器材料写入 exact Run 的私有 `accepted-continue-input.json` v1，内容摘要固定在新 Run 的可选 `accepted_continue_input_sha256` 字段中；只有完整匹配的原 Run 及 TaskService 明确指定的未接收输入才能用于重建，文件本身不授权重放或发送。该字段不修改 Run schema 版本，也不回写旧 Run；Stop 清除未执行输入，恢复循环按原 lane 重建配置。尚未开始的工作区清理被撤销，已经开始的处置保留精确 owner 和回执后再重建。

Flyway 追加 `20261109_execution_delivery_separation / execution-delivery-separation/v1`；旧 waiting 默认完成，真实执行义务继续运行，旧收尾意图和只读历史 needs-attention 完成。schema 4 中仅因发送失败或未知而标错的成功执行转为 completed。Run 格式仍为 schema 4，历史 Run、发送回执、身份、revision 和 Artifact 不因 Task 迁移改写，不重跑或补发。

目标 Flyway 清单保留 `20261112_run_start_coverage / run-start-coverage/v1`，并追加 `20261113_run_start_history / run-start-history/v1`，分别声明工作台账的 v1 启动覆盖标记和历史启动对账回执格式。后者只追加同一账本的事实与回执，不改写既有启动事实、不为历史日期自行补造覆盖，也不改变 Task/Run schema、状态或 lifecycle；已发布的账本 reader 继续读取既有记录。v1 标记由服务启动时的账本 owner 按其版本化合同写入；历史对账只接受公开 CLI 的显式计划和完整区间裁定。缺少两者中的任何一个只按对应有效边界缩小或使按小时指标不可用，不阻止已有服务或既有指标。

已发布的 `20261117_task_recap_metadata / task-recap-metadata/v1` 迁移记录继续有效。`20261118_task_recap_lane / task-recap-lane/v1` 在启动租约前统一发布 Task schema 7，并从 Agent 描述中移除已退役的 `recap.generation`，保留原生标题读取和其他 Agent 设置。schema 6 的概括记录作为只读历史保留。能与原 Run 和成功记录核对的旧标题继续显示，直至同一 Task 写入新标题。升级不会启动历史概括 Run。

## 路径

公开路径变量定义在 [configuration.md](configuration.md)。下图表示逻辑归属；state、workspace 和 logs 使用各自的生效路径，不要求位于同一个物理父目录。Task store 由 `JARVIS_RUN_DIR` 选择，默认位于 `$JARVIS_STATE_DIR/runs`。

```text
JARVIS_RUNTIME_ROOT/
  dependency-cache/
  envs/
    .env.jarvis-box

<生效 workspace root>/
  <workspace-id>/

JARVIS_STATE_DIR/
  chatbridge/
  chat-bindings/
    bindings/
    messages/
    notification-aliases/
  status-value/
    snapshots/
      gitlab.json
      github.json
    evidence/
      <provider>/
        <hash>.json

JARVIS_RUN_DIR/                       # 默认 JARVIS_STATE_DIR/runs
  <task-id>/
    task-state.json
    .task-state.json.lock             # Web/CLI lifecycle mutation lock
    task-events.jsonl
    payload.json                     # Start provider input; write once
    runs/
      <run-id>/
        run-state.json
        .run-state.json.lock         # terminal transition lock
        run-context.json
        prompt.txt
        run-trace.jsonl              # sole Jarvis-owned stdout/stderr journal
        outbox/                      # private pending IM delivery files
        result.json
        reply.md

<生效 service log root>/
```

Linux system install 可以将 config、state 和 logs 映射到 `/etc/jarvis-box`、`/var/lib/jarvis-box` 和 `/var/log/jarvis-box`。逻辑边界不变。

## 版本升级与数据兼容

已发布版本写入的持久化数据是跨版本产品合同。内部代码重构不取消旧数据的读取、历史浏览或原任务接续能力。存储 schema 与产品版本分别演进；格式变化需要新增迁移步骤，并保留已发布格式的解码和迁移历史，不能让新版只识别最新格式。

安装或升级时，目标版本在服务停止后通过 `jarvis-box migrate runtime` 执行有序 Flyway 清单。除配置迁移外，清单也包含 Task/Run 存储迁移：先按旧格式校验归属，再由同一个 TaskService 事务发布当前格式。所有已登记 Task 都必须完成兼容性校验和必要的格式发布，成功后才签发启动租约；失败保留原始数据并阻止新服务启动。未登记的旧历史保留为只读记录，不推测新的执行归属。

格式迁移保留 Task/Run 身份、sequence、业务 revision 与更新时间、业务状态、待处理 intent、会话、Artifact、未知扩展字段和已有结果，不创建 Run，不执行 Agent，不发送业务消息。已是当前格式的数据不重复改写；每个 Task 的日志支持中断后的事务恢复，Flyway 清单保留 intent 和成功或失败记录。已经完成的迁移在后续升级中跳过，新增格式变更追加步骤，不删除或改写已发布步骤的身份。

`20261106_im_notification_references`（`im-notification-references/v1`）是追加的完成通知引用兼容步骤。它只启用新 V2 通知 receipt 与派生 alias 的读取/维护边界；旧 V1 通知继续按已发布格式只读，绝不从旧正文、时间、目录或历史发送结果回填引用。该步骤不改写 V1 receipt，不创建 Task/Run，不启动 Agent，也不发送 IM。

`20261106_im_attachment_resource_identity`（`im-attachment-resource-identity/v1`）登记附件可选 `resource_id` 的存储兼容边界，沿用现有 Task 存储迁移，不扫描或回填历史附件身份。字段的具体读取规则仍由下面的 ChatBridge 附件合同定义；该迁移不是逐字段的正文或附件校验器，也不产生 Run、Agent 或消息效果。

群历史回查使用 Run 的可选 typed `im_context_grant`，保存不可变原生 scope、原输入指纹、规范事件摘要及当前能力摘要，不保存 raw capability 或原生凭据。该字段由 TaskService 在既有启动流程提交，不投影到公开 RunView；缺少字段的历史 Run 保持原状，不回填授权。待启动请求中的 scope 与 raw access 均不序列化，存储等待恢复只从严格 aggregate 取得既有授权并轮换摘要，不能以准备文件作为权限来源。兼容步骤沿用 Go Flyway 的 Task 存储迁移，在启动租约前验证格式，不创建 Task/Run 或发送消息。生命周期有效性见[执行模型](execution-model.md#prompt-contract)。

`20261107_im_collaboration`（`im-collaboration/v1`）登记 IM 协作元数据的兼容边界。已发布的历史查询、读取计划和结果回执只由既有 decoder 作为私有嵌套字段读取，保留原始数据而不为它们补造授权、材料、输入或副作用。当前材料读取不在 Task 中写 ContextQuery、Materialization、第二句柄、读取 receipt、六态 journal 或启动恢复记录；UV 的 opaque handle 连同当前 Run 的重新授权才是读取边界。普通 Run 文件、原生资源名及用户给定路径都不能产生读取权，公开 TaskView 也不返回 handle、原文、资源 URL、查询条件或本地路径。迁移只校验持久化合同，不执行读取、下载或消息发送。

结构化 IM 问题沿同一兼容步骤保存追加式 stage、投递 plan/receipt 和单一 answer resolution；完整内容只在私有 aggregate，公开投影只有交互阶段与投递状态。卡片 presentation 保存随机 handle 的摘要、原 Task/Run、问题代次、目标与内容摘要；原生发送证明另外记录实际 CardID、revision、摘要及消息定位。关闭卡片的 update receipt 仅记录可重建 operation 的展示效果，不授予执行权。`chat-bindings/interactions/` 是由这些事实重建的定位索引，索引不存在、Task 同名重建或身份不匹配时拒绝操作，不扫描正文猜测归属。旧数据缺这些字段即没有该交互能力，不回填问题、按钮或发送权限。

### 一次性外部事件订阅的持久记录

一次性外部事件订阅使用同一 strict Task aggregate 的 append-only typed records：`RegistrationIntent` 固定完整 TaskIdentity、原 Target actor、exact GitHub execution、规则、accepted/deadline；`SubscriptionSet` 固定 source key、local receipt cut、资格化 hook 的安全 digest 和规则；claim、delivery/Continue settlement、revoke、execution reference 与未登记的 terminal settlement 分别追加，绝不替换历史。source receipt ledger 和精确 set index 属于 GitHub source owner；index 只缩小读取范围，TaskService 每次仍按完整 Task identity、set/rule、原 Target/current policy、expiry、cut 和 lifecycle 复核。source receipt、hook qualification、webhook body、token、reply credential 与完整 actor 不进入 public TaskView；普通 Status 只投影 `availability` 和活动计数。重启恢复只消费这些持久记录和现有 recovery sweep，不扫描 provider、Task catalog 来找订阅，也不创建 queue、scheduler 或 Agent poller。

以后新增存储格式时，必须保留从所有受支持旧格式到新格式的迁移路径。旧程序遇到未知的更高格式应拒绝改写并保留文件；不能将其当空数据初始化。确定性派生缓存可以重建，但已有 Agent/人工分析结果属于历史业务数据；分析指令和输入语义不变时，代码重构或格式升级不能触发重新分析。

## State Root

`JARVIS_STATE_DIR` 保存 jarvis-box 应用状态。它包含：

- Run/Task artifact root
- ChatBridge default Task bindings and message-to-Task indexes
- provider-confirmed 完成通知的派生引用索引
- 其他受管应用状态

IM 明确 Task 输入复用现有消息归属索引和 strict Task/Run aggregate。已受理输入的身份/摘要保存在 Run；后继分配前由既有 `RunReplacementIntent.Input` 保留。当前或历史 Run ID 唯一定位其父 Task，随后必须重新核验完整 Task 登记、当前 identity/revision、actor、Target 与 Continue fence；旧 `TaskView.LookupID`（`task:v2:`）仍可作为兼容输入或既有链接读取。外部来源任务的续接路由只记录已受理输入与后继 Run 的对应关系；回复授权由该 Run 的 `notification_reply_intent.authorization` 唯一保存，不能由路由索引补造。明确选择的出处保存在本轮 `run-context.json`，不另建输入账本、话题关联表、反向关联投影或 Task 状态。消费控制消息的索引记录不能证明输入摘要或执行成功。选择、隔离与重投规则见[执行模型](execution-model.md#im-明确选择-task-的-continue)。

完成通知的 V2 authority 始终是 exact Run `.private/` 下的 sealed receipt：它带完整 Task/Run identity、已发布 safe snapshot、envelope digest 和已确认的 native publication locator。envelope 摘要覆盖完整的已确认定位列表；列表被替换或增补而与摘要不符时，索引修复和引用读取均拒绝该回执。safe snapshot 封存 typed `SourceActor` 及可信初次受理时的 `SourceAccount`；它们仅是当前 GitLab/GitHub `jarvis-command` 通知引用重取 sealed actor、精确资源和当前 command policy 的输入，不是通用成员查询、反向身份解析或其他 source lane 的权限凭据。其 `Text` 只在同一 source Run 的 sealed `provider.comment` payload 及同 Run `succeeded + delivered` effect 都存在时可读，其他情形固定为安全的“已发布结果不可用”，不读取可变结果文件或 trace。`chat-bindings/notification-aliases/<sha256>.json` 只是由 locator hash 访问这份 receipt 的派生索引，独立于普通 `bindings/` 和 `messages/`，不能写入默认 Task、原始 prompt、Agent transcript、native reply credential 或来源平台身份。只有 provider/connector、真实 native conversation 与 message ID 完整且 provider 返回 confirmed publication 时才可建立 alias；native conversation type 是可选的附加证据，不能从主动私信目标补猜。

已确认投递之后 alias 写入失败只保留 alias pending/unavailable，恢复器只能修复索引而不能重发通知。索引读取时必须重新核验 V2 receipt、完整 generation fence 与 locator；receipt 清理、Task/Run ABA、损坏或不一致会把记录改为仅含 locator hash 的 unavailable tombstone。tombstone 使同一引用确定拒绝，不能退回普通 message binding 或会话默认 Task。旧 V1 receipt 无此引用能力，仍可读取但不回填 alias。

`JARVIS_STATE_DIR` 不是 service log 目录，也不是 Workspace。

Task 的可选 `runtime_recovery` 保存受信原生终止事实、完整来源 Run 身份、恢复类别、累计次数、候选使用记录、到期时间、认领的后继 Run 和停止原因。恢复预算与后继 Run 在同一 TaskService 事务中认领；重启不会清零。Claude终止及压缩的新回执使用稳定事件合同标识`claude-stream-json/v1`，不绑定CLI补丁版本；已发布的`claude-stream-json/2.1.235`、`claude-stream-json/2.1.304`记录继续可读并可沿原恢复链使用，历史标识不重写。未知协议标识不授予恢复权。缺少该字段的已发布 Task 保持原语义，不因扫描历史失败而获得自动执行权限。目标版本 Flyway 在 startup lease 前验证存储，并保留旧 Task、会话、工作区与外部回执。

恢复只作用于所属 Task，不创建 `runtime-agent-route.json`、`runtime-agent-events.jsonl` 或全局 cooldown，也不读取旧同名文件推断权限。原始 stdout/stderr、历史日志与助手正文不能生成恢复意图。普通续跑、三类专门恢复及停止规则见 [执行模型](execution-model.md#agent-中断的有界自动-continue)。

## Delivery Metrics 派生状态

`JARVIS_STATE_DIR/status-value/` 保存 GitLab 和 GitHub Delivery Metrics 的读模型和管理员导入的来源复核记录：

- `snapshots/<provider>.json` 保存当前快照、Provider scope、登录主体和 pending 数量；
- `evidence/<provider>/<hash>.json` 保存已完成的人工纠正分类、固定证据码和可选的交付来源。旧结果缺少来源时继续复用人工纠正结论。
- `reviewed-origins/<scope-hash>.json` 是管理员显式导入的来源记录，按平台、站点、账号及账号创建时间隔离。仅匹配同仓库、MR/PR 编号和源 SHA。文件不可原位替换，相同文件可安全重试。导入和对应账号的采集各自校验文件。采集读到损坏或不匹配的文件时告警，保留文件并继续使用可核验的分析结果。

分析执行属于普通 `delivery-metrics` lane Task。Task 根目录只保存首次 provider input、typed state 和审计事件；每个 Run 目录保存自己的 prompt、run context、`delivery-metrics-result.json` 和其他 Run Artifact。当前执行或等待恢复的这些 Task 会进入默认 `jarvis-box tasks list`，历史记录用 `jarvis-box tasks list --all --lane delivery-metrics` 查看，并受 Start、Continue、Cancel 和 `tasks clean` 的统一生命周期控制。

快照仅在 scope、actor 和 schema 均匹配时复用；scope 包含 Provider、Provider host、配置仓库集合和 Delivery Metrics 合同版本。Runtime Agent 选择不进入分析 identity，因此切换 Agent 不会重算已完成 evidence。相同 Provider、host、完整账号身份、仓库、MR/PR 和源 SHA 的有效结论继续复用；合并后的评论或元数据 `updated_at` 变化不会使结论失效。已发布的 schema 4/v7 文件及受支持的 v1 合同结论保持可读，原证据键中的更新时间字段不再作为已知格式的结果匹配条件，无需重写原文件。原 Task 已清理时也可复用保留证据；账号、主体或源 SHA 不同不得串用。

status-value 只保存 typed 派生结果，不保存 raw note、review body、Agent stderr、token 或命令。不得为 Delivery Metrics 增加全局 FIFO queue、cursor 或私有分析状态；pending 项只能通过 Provider 刷新和 Task store 重新派生。服务启动、MR/PR 关闭或合并、分析 Task 完成及定时补查会主动同步快照，普通 GET 不提交分析任务。文件损坏、版本不兼容或 scope 不匹配时，服务忽略不兼容的派生状态并重新同步；已有 Task 的失败或无效结果仍由操作者明确 Continue，不因重建快照自动重跑。操作步骤见 [Delivery Metrics 历史起点](delivery-metrics.md)。

## Status Metrics 派生状态

工作台列表、Task peer 观察与分页游标仅存在于服务内存，重启后重新构建。它们复用唯一严格 loader/projector；缓存命中必须在 lifecycle lock 内复验源内容和 Run 成员，提交后的增量发布可携带未变化 Task 的先前观察。一个共享缓存中的完整或增量轮次串行更新，失败失效不能被先开始的旧轮覆盖。Task 详情可显式选择带观察时间的 peer 读取；修改始终重新严格检查，不从缓存取得权限。分页、过期、内存与连接边界见 [Status API](status-api.md#status-读模型)，不写入 Task/Run schema 或 startup migration 清单。

本机运行趋势、累计启动数、完成耗时和按小时启动分布的唯一历史事实源是 append-only 的 `work-ledger.jsonl`。Status 不写 `status-metrics/task-runs-daily.json` 或其他本机指标 rollup；不存在磁盘增量状态可作为账本的回退或替代。Task Artifact 清理不删除 ledger 中的启动和耗时事实，不能用固定 180 天窗口代替账本口径。

Status 在内存中保留经过完整验证的账本归约快照。每次账本源文件的路径身份、大小或修改时间变化时，后台在共享文件锁下重新完整验证并归约，而不是从偏移量或旧 rollup 增量拼接；任何未完成、取消或失败的轮次都会丢弃其部分结果。发布在后台独立推进，工作台摘要、分页查询和事件流从最后一次已发布的不可变账本归约快照投影所请求时区的 MachineMetrics，既不按请求扫描账本，也不触发覆盖记录写入。账本截断、轮转、替换、损坏或无法完整读取时，旧内存快照不能伪装成新的历史事实或可信零值。

按小时分布的覆盖证据与启动事实同在账本中。不可变的服务启动标记为 `kind=run_start_coverage`、`event_id=run_start_coverage_v1`、UTC `ts`，以及 `detail.schema=run-start-coverage/v1`；它只由成功初始化的启动路径在完整账本验证后、既有独占文件锁内写入一次。可选的历史对账回执为 `kind=run_start_history` 和 `detail.schema=run-start-history/v1`：计划绑定 canonical runtime target 和导入前账本前缀；回执的 immutable v1 字段 `coverage_from`、`coverage_through`、`plan_sha256`、`pre_receipt_bytes` 和 `pre_receipt_sha256` 分别固定经裁定区间、精确计划和实际导入事实后的账本前缀，回执 ID 由同一计划 SHA-256 派生。WorkLedger 在同一独占锁内完成严格输入验证、已有事实去重、事实追加和回执确认；没有只追加事实而不完成裁定的操作模式，也不保留独立 cursor、rollup 或 sidecar。

历史来源通过私有、可移交的 manifest 进入计划。collector 以操作者独立提供的归档 SHA-256 校验同一份私有压缩快照，再从该快照计算完整成员摘要并保留原始启动行；其成功输出给出完整 manifest 的精确字节摘要，由操作者单独保留。CLI 的 `--sources` 必须与这份可信记录对应的 `--expect-sources-sha256` 成对提供；同一次有界私有读取的完整字节通过校验后，才解析 manifest、读取目标或创建计划。来源元数据不能自行证明原始行的真实性。只核验目标本机历史时不接受来源摘要参数，仍使用现有目标前缀绑定。

使用外部来源时，计划的 `source_sha256` 保存已核对的来源摘要；计划 SHA-256 封存待导入原始行、来源元数据、目标及区间裁定。Apply 只接受精确计划及其已审阅摘要，不接受来源参数；它严格重验计划输入和目标，不重新打开原 archive 或来源文件，也不检测原位置在采集后的变化。复用 manifest 重新计划时仍须核对原可信采集摘要；来源改变则重新采集并保存新的可信输出，不得用变化后文件现算的摘要冒充原记录。采集、计划和应用的文件完整性校验均不能替代下述连续完整区间裁定；命令和操作步骤见 [CLI 参考](cli.md#补录已核验的-run-启动历史)与[运维入口](operations.md#受控补录-run-启动历史)。

历史对账只由 `metrics backfill` 的明确 UTC `coverage-from` 和 `attest-complete` 建立。该裁定是操作者对所选保留来源集在连续区间的完整性声明，不从最早一行、来源名、文件时间或归档位置推断；`origin` 仅为审计标签。回执有效时，按小时统计的 UTC 覆盖边界是它的 `from` 与 v1 标记中较早的时刻。导入但早于这一区间的启动事实仍是普通启动事实，可进入累计和每日趋势，却不能证明按小时覆盖。reader 重新完整扫描账本并验证所有回执绑定；如果回执之后追加了时间不晚于其 `through` 的历史启动事实，该回执失效，按小时统计退回仍有效的 v1 标记，或如实不可用。初始化及准入顺序见 [EM-METRIC-001](execution-model.md#em-metric-001-指标和可用性)。

每日趋势从首条启动事实到浏览器时区的当天保留零日，并与按小时分布共用所请求的时区；页面的 7/30/90 天选择只改变显示范围，不截断历史统计。时区变化只改变派生分桶，不修改账本、覆盖事实或 Task/Run。未指定时区的既有 API 调用保留服务进程时区语义。账号贡献日历按各 Provider 的日期合同保留原日期，普通时间戳按浏览器时区展示。

后台 Status 台账读取使用可取消的共享文件锁等待与逐记录扫描；取消或截止后丢弃该轮部分统计并释放文件句柄，不留下不可中断的锁等待线程。原有台账追加、去重、格式校验与持久化顺序保持不变。

资源等待与 IM 用户确认沿用已发布的 Run failure、effect receipt 和 IM binding 格式。新版本只依据明确的 typed `storage-wait` 恢复未启动 Run，不把旧版本的普通失败文案改判为自动重试，也不清空历史 Run。IM 用户确认由原绑定授权，送达裁定追加新的 effect receipt，保留原始超时证据；已确认送达不重复发送。

IM明确缺失名单为未确认集合的严格子集时，TaskService在同一effect历史追加版本化`attestation=missing-attachments/v1`及`missing_attachments_json`规范JSON数组字符串，名单不可为空或重复，仅用于该Run的chatbridge reply。存储保持回执值比较及不可改写前缀，TaskView以`missing_attachments`数组投影。旧reader遇到这个闭集之外的标识拒绝读取，不能丢弃选择后重发全部文件。私有完整v2交付回执可追加`confirmed_attachment_indexes`保存连续`attachment_count`前缀之外的确认；省略时保留旧连续前缀语义，原payload摘要仍绑定完整文件集合。每次补发重新验证内容与集合，只更新同一Run的交付进度，不重写已完成Run。Flyway追加`20261023_im_attachment_selection / im-attachment-selection/v1`，复用既有Task存储迁移在启动租约前验证已发布记录；不从公开文件或旧错误文案制造选择，缺少选择的历史unknown仍等待原用户或明确裁定。

## Task Directory

`JARVIS_RUN_DIR` 是 Run/Task artifact root，默认 `$JARVIS_STATE_DIR/runs`。
这个环境变量和物理目录沿用 0.2.27 的旧名称，但其逻辑角色是 **Task store
root**：第一层 `<task-id>` 是 Task，不是 Run；只有 Task 内的
`runs/<run-id>` 才表示 Run。新版本不再据此把 Task 根和 Run 根各写一套输入或日志。

每个 `task_dir` 是一个可清理的 Task 子树。`task_dir/runs/<run-id>` 才是单次 Run Artifact；Task 根目录只保存当前状态、审计流、provider 输入和 Task-level projection。

`task_dir` 内可包含：

- `task-state.json`
- `task-events.jsonl`
- Start 时由 TaskService 一次写入的 `payload.json`
- `runs/<run-id>/run-state.json`
- `.task-state.json.lock` 和每个 Run 的 `.run-state.json.lock`；只用于 Web 服务与 CLI 跨进程串行化状态变更，不承载产品状态
- 每个 Run 自己的 `prompt.txt`、canonical `run-context.json`、`run-trace.jsonl`、`result.json`，以及本次 Run 产生的 reply/comment 快照（如有）
- ChatBridge 的 `attachments/` 与 `outbox/` 都属于对应 exact Run：前者只供 runtime agent 使用，后者只保存 agent 明确请求交付给 IM 用户的最终文件；发送结果只进入 exact Run typed effect receipt，不另建 recovery marker。

Run Artifact 是证据，不是 conversation memory。产生 provider output 的 Run 只保存自己的 `reply.md` 或 `comment.md`；Task 根目录不再制造同名 provider-facing projection。Task 连续性由 Task state、AgentConversation lineage 和 runtime-native resume 负责，不由 reply、prompt、RunTrace 或 jarvis-box 自己拼接的 history prompt 负责。

`custom-user-task` 是 providerless prompt job。它的 `job_id` 保存在 `task-state.json`、当前 Run 的 `run-context.json`、Task 根目录的 `payload.json` 和 intake/conflict event 中，用于日志、Status、筛选、防并发和排障；`reason` 保留可读触发来源。jarvis-box 不为它创建 provider writeback projection，启用结果通知时，最终答复存为 exact Run 的 `final-message.md`；提交时固定的路由通过现有 pending admission 和 Run 私有 `result-notify-source.json` 保存，投递回执归属同一 Run。其他 IM、webhook 或 GitLab 业务动作仍由 Agent 写入结果证据。重复触发同一 active `job_id` 时，服务在已有 Task 的 `task-events.jsonl` 中写入 `custom_user_task_start_conflict`，并向调用方返回 conflict；这不是全局队列、cursor 或自动补跑机制。

`chat-bindings/bindings/` 每个 IM Target 保存默认 Task 指针或 `/new` 的重置记录，按接收时间与入站消息 identity 排序。重置不删除排序凭据，较旧准入的恢复不能覆盖较新的选择或重置。`chat-bindings/messages/` 保存同一 Target 内 message id 到 Task 的引用索引，包括已确认发送的机器人回复 id；不创建 Run 的控制消息在动作前以可选 `control_claim=true` 登记消费，其 TaskRef 四字段全空，不授予引用权限，也不证明动作完成或回执送达。缺少该标志的已发布消息记录继续按原 Task 引用合同读取，无需重写。两者均以同步临时文件、原子替换和目录同步提交；临时文件写入失败不破坏已提交记录，并发读取只会看到替换前或替换后的完整 JSON。两者都不保存 Run id、Run 状态、reply token、native session 或 provider credential；Task/Run artifact 始终是执行状态的唯一事实来源。

消息索引的 `source_key` 为规范化的 `provider:connector:conversation`，文件名是 `SHA256(source_key + NUL + message_id)` 的小写十六进制加 `.json`，输入按UTF-8编码。读取时必须复验记录中的同一source key和原生message id；文件名不单独授予Task身份或操作权限。

IM 首轮准入的私有描述符保留原接收时间。恢复通过 TaskService 的原准入校验后补齐同一完整 TaskRef 的绑定，不使用恢复时刻重新选择默认 Task。已发布描述符缺少接收时间时使用原 Task 登记时间；已发布的默认 Task 指针和消息索引保持可读。目标版本 Flyway 在签发启动凭据前验证新增的选择与重置编码。

exact Run 的 `.private/reply-handle.v1.json` 可附加 `origin_sender_id` 与 `origin_sender_digest`，以 `chat-reply-sender/v1` 域绑定既有 handle digest。它们不改变已发布 credential digest、opaque ID 或有效期；缺少这对字段的历史记录仍按原投递合同读取，半对或摘要冲突拒绝。新消息无 token 且无 expiry 时，同一文件只保存目标及完整 sender 证明，不能伪造凭据或已消费次数。Flyway 追加 sender 迁移，只从注册及消息归属已核实的旧私有完整入站记录补齐；无法证明的历史 sender 保持缺失，不能从公开 payload、context 或 Task 首创者推断。原未知交付仍可通过已有 sealed operator attestation 在同 Run 处理，不创建 Agent Run。

ChatBridge 的入站附件与待交付文件分别保存在 exact Run 的 `attachments/` 与 `outbox/`：`attachments/` 中的文件只供 runtime agent 使用，`prompt.txt` 和 `run-context.json` 可以保存本地路径；`outbox/` 只接受目录根部的普通非空文件，实际可投递边界由精确 provider、connector capability 和 IM 渠道限制决定。私有目标凭据和最终交付回执另保存在同一 Run 的 `.private/`。TaskService 在发送前持久化 exact Run effect-start，随后只接受同一 fence 的 typed receipt；结果未知时不自动重放可能已经送达的附件。Status task projection、Status Artifact endpoint 和 symlink alias 都不得枚举或读取这些私有目录；provider 下载 URL、文件密钥、raw IM payload 和 reply token 不写入 Status response。

显式引用的飞书合并转发材料继续使用上述资源缓存与 exact Run `attachments/` 通道，不新增正文数据库、Task/Run 状态或历史索引。连接器负责顶层容器与子材料的原生资源定位；Jarvis 仅保存经脱敏的资源来源、对应标识和本地附件路径，不能由同名文件或子消息 ID 推导来源 Task 权限。

ChatBridge 的附件对象可含 `resource_id`，只从脱敏协议 `ResourceRef.ID` 投影，供引用说明与 exact-Run Agent 附件清单对应；通用 `key` 保留既有用途，不能成为该展示字段的来源。字段作为可省略字符串存在于既有 Task payload 与 Run context，既有下载、清洗和未接收输入复制会保留它；复制只更新实际目标路径，不改变资源对应。私有 admission descriptor 仍为 v1，只保存原有下载凭据与数量，不重复保存这份脱敏协议元数据。旧对象缺字段或为 `null` 时身份未知，重新保存仍省略，不从历史文件名、key 或 URL 回填。pending/carry 的 typed JSON reader 拒绝损坏 JSON 和不兼容字段类型；其他未知扩展字段保留各 reader 已有的宽松行为。该字段不进入 Status 的附件枚举或下载授权，旧 runtime 的未知迁移日志/启动租约拒绝规则保持生效。

`.private/final-reply-receipt.json` 的完整v2回执继续保存原payload摘要及已确认附件前缀。可选的首次预检形状使用`preflight_only=true`和独立`reply_text_sha256`，完整`payload_sha256`为空、附件前缀和消息ID为空，只表示该exact attempt尚未执行最终发送且文件暂时不可读。它必须与同一Task/Run/intent及明确未发送的可重试effect一致；不能授权具名补发或未知结果裁定。完整读取成功并复验原文及目标后才转为普通完整payload形状，已有完整回执不得降级。已发布的完整v2数据不重写，缺少预检凭据的旧失败不从公开内容补造授权。

## RunTrace 与 Native AgentSession

Runner-owned `run-trace.jsonl` 是 jarvis-box 对当前 Run 进程 stdout/stderr 的唯一持久化日志，并按原始顺序追加进程输出；Status 从该 trace 重建脱敏时间线。TaskService 将当次进程提示词写入 `prompt.txt`，RunTrace 只记录进程输出。提示词可以是用户原文，也可以包含 workflow 生成的契约、运行上下文和主机路径。多进程评审的 `prompt.txt` 保存公共提示词，各进程的完整指令由原生会话记录。`prompt.txt` 不承担会话记忆、跨 Run 历史或原生续接。

Native AgentSession jsonl 属于 runtime agent，不属于 Run Artifact。它保存 agent 自己的 conversation memory、checkpoint、compact 结果、tool trace 或 session metadata，用于 native resume。

两者职责不同：

| Surface | Owner | 内容 | 生命周期 | 用途 |
| --- | --- | --- | --- | --- |
| RunTrace | jarvis-box | 当前 Run 的进程 stdout/stderr 和运行输出。 | 跟随 Run Artifact；`tasks clean` 可以删除 terminal Run 的该文件。 | 审计、排障和 bounded/redacted Status timeline。 |
| Native AgentSession jsonl | runtime agent | AgentSession conversation、checkpoint、compact 和 native resume 所需记录。 | 由 runtime agent 管理；jarvis-box 不把它复制进 Run Artifact。 | native resume 和 native compact；跨 agent 时目标 runtime 创建自己的 session。 |

规则：

- RunTrace 不能作为 conversation memory、prompt history 或 resume source。
- `prompt.txt` 中的 Run 输入只允许作为当前 Run 的 bounded、redacted Status 投影；不得从 native AgentSession 补齐原文或历史消息。
- Native AgentSession jsonl 不能作为 Status Artifact 暴露，不能被复制到 Run Artifact，也不能被 jarvis-box 解析后拼接进 prompt。
- `task-state.json`、`task-events.jsonl` 和 Status task projection 只能保存 safe resume status/ref，不能保存 native session id、session file path 或 resume handle value。
- Cross-agent Continue 创建目标 runtime 的新 session；jarvis-box 不导入、不转写、不展开源 session 内容。
- RunTrace 用来审计一个 Run，AgentSession jsonl 用来延续一个 AgentConversation；jarvis-box 不再并行生成 `agent.log`、`codex.log` 或 `claude.log`。
- RunTrace 必须由 jarvis-box 捕获进程输出后按固定策略写入；不得通过 symlink、hardlink 或 raw pointer 复用 native AgentSession 文件来伪装成 Run Artifact。
- Runtime output persistence 必须避免写放大：首个输出可以立即落盘，后续输出按大小或时间窗口 flush，Run 结束或超时时强制 flush。stdout/stderr activity event 也必须合并，不能按每个 chunk 写 `task-state.json` 或 `task-events.jsonl`。

Task 根目录不写 `run-context.json` 或派生的 `meta.json`，Run 目录及 provider-specific `workflow-input.json` 都不复制 raw `payload.json`；RunTrace 不复制 `prompt.txt`。
旧版本已经生成的重复文件只作为历史证据只读保留；它们不得参与新状态、操作权限、恢复或 writeback 决策，也不得恢复已删除的 writer。

## Authoritative State

### Task、Run 与事件

`task-state.json` 记录 Task 当前事实；每个 `runs/<run-id>/run-state.json` 记录该 Run 当前事实：

- Target 和 Task 标识
- lane、`custom-user-task` 的 `job_id`、status、phase、lifecycle summary
- current Run metadata
- runtime agent name
- process metadata
- safe action policy
- safe resume handle status/ref
- artifact refs
- 单会话评审维护续接的 `review_session_source_run_id` 指向原 Run。它固定复用的原会话、受理提交和输入，同 Agent 自动恢复继承该字段。已发布记录没有该可选字段时按原规则读取。

`task-events.jsonl` 记录状态变更审计事件。事件用于排查和补充证据；当前状态以 `task-state.json` 为准。Run 产生的事件必须携带 `run_id`，可以确定顺序时同时携带 `sequence`。从事件恢复 Task 投影时按最大的 Run sequence 选择最新 Run，不能让旧 Run 的晚到事件覆盖当前 Run。

### 状态写入、终态与恢复

终态 Run 不可变。Task/Run state mutation 同时使用进程内 mutex 和文件锁，因此 Web 服务与独立 CLI 进程共享同一 compare-and-swap 边界；每次权威 JSON 替换必须依次完成临时文件 `fsync`、close、rename 和父目录 `fsync` 后才能返回成功，不能把 page cache 中可见但断电后可能丢失的 rename 当成 durable commit。Task 生命周期文件锁使用 runs root 外围稳定 inode，不放在会被 retirement 删除的 Task 目录内；它串行化每次 Run ownership/state 提交、Workspace 准备认领、到期清理认领和 Cancel；首次 Start 的实际目录创建、clone 和 checkout 在生命周期锁外执行，由同一 Task 的独占 Workspace lease 保护。准备结束后重新复验完整 Task registration、revision 与 pending admission，取消或换代后的旧准备不得取得 Run。并发恢复只尝试取得该 lease，不在生命周期锁内等待，因此慢速远端不会阻塞 Task Catalog。provider/local finalization effect 不得持有生命周期锁；同一 Task 另用稳定的跨进程 finalization owner 锁串行化 completion 与 recovery，使跨 Task 的 `workflow.start` 不会与 Catalog gate 形成反向锁序。runtime helper 也必须携带 Run id 并通过同一 ownership 条件更新 Task state 和 Task event；仅有 task directory 不足以取得写权限。新 Run 以读取到的 Task owner 和 `latest_run_sequence` 为 compare-and-swap 条件取得 `current_run_id`，并发请求不能无条件覆盖该指针，owner 发生 ABA 也不能复用旧 sequence；rename 已可见但目录同步失败属于 typed ambiguous commit，无论底层是 ENOSPC、EDQUOT 还是 EIO，都只能在真实写探测恢复后按同一 Run/Task instance 重写确认，不能另建目录或遗留幽灵 owner。TaskService 是 managed Run 的终态仲裁者；只有仍拥有当前 Task Run identity 的 completion 才能先持久化包含不可变 Task instance、完整 Run 终态 patch 和 Task 终态 patch 的 write-ahead `terminalization_intent`，随后提交不可变 Run 终态、在生命周期锁外执行 provider/local effect、重新校验 owner 后写 receipt 并释放 Run ownership，再按 `JARVIS_TASK_WORKSPACE_CLEANUP_DELAY_MINUTES` 原子安排 Workspace 清理。Cancel 同样在任何进程信号前按当前 owner/sequence 写入 intent，且该中间状态保留 PID 和 Run pointer；cancellation intent 一旦提交即拥有 Task 终态仲裁权，晚到 completion 不得覆盖。无 Run owner 却仍有 PID/PGID 的状态必须 fail closed，不发信号、不清目录也不清进程证据。恢复器必须先停止或固定旧 Run，不能把仍可能运行的进程当作可清理 Task。Run 或最终 Task state 写失败时仍保留 `finalizing` intent；启动及每 5 秒运行的恢复器先收敛已死亡进程留下的 Run owner，再按 intent、当前 Run evidence 和 `workspaces[]` 幂等重放，不扫描 Workspace，也不把删除 Workspace 当成终态写入的前置条件。已有新 Run 时，旧 Run 只保留自己的终态 Artifact 和 delivery evidence，不改写当前 Task projection 或 state。

Provider effect 调用前，TaskService 还必须在同一 `terminalization_intent` 中持久化 `effect_started_at`。恢复时已有 typed effect receipt 就只提交剩余 Task patch；已有 `effect_started_at` 却没有 receipt 则表示外部结果不可证明，只能追加 `unknown` receipt 并转 `failed`，不得自动重发非幂等 provider mutation。

### 磁盘准入与自动恢复

`JARVIS_TASK_STORE_MIN_FREE_GB` 定义启动新工作前必须保留的磁盘余量，默认 10 GB，只有显式 `0` 才禁用；空值或畸形的 Run 环境不会把保护静默关闭，服务与 scheduled job 的非法显式配置会直接拒绝启动。TaskService 先原子登记 Task identity、canonical subject 和完整的 1:N `workspaces[]`，再检查 Task Artifact 所在卷和每一项已登记 Workspace 路径；准入通过前不创建 Run、不 mkdir/clone Workspace，也不启动进程。Runner 在进程启动前再次检查这些卷，覆盖准入与 spawn 之间以及多个独立卷之间的容量变化。

`repo-cache` 是 box-owned 的 bare mirror，以完整 project 和权威 remote 共同标识仓库。仅声明 `--remote` 时，由 Git 路径派生缓存键的 project，复用同一 remote 和项目路径的已有缓存，不改写 Workspace 登记；不同 remote 仍隔离。缓存刷新使用 exclusive lease，cache clone 全程持有 shared lease，避免另一个 Task 在 Git 读取 object 时改写同一 mirror。缓存刷新成功且 cache 与 Workspace 位于同一文件系统时，显式 branch/ref Workspace 通过 Git local clone 复用不可变 object 的硬链接，随后立即把 `origin` 恢复为权威远端；Workspace 不写 `objects/info/alternates`，所以 cache 删除或重建不会让已有 Workspace 失效。显式 branch/ref 的本地硬链接 clone 在缓存刷新失败、本地 clone 不可用、lease 获取失败或跨文件系统时退回权威远端 clone。默认分支单分支 Workspace 也使用 repo-cache，但通过非 local 的单分支 clone 从 mirror 读取对象，避免暴露 mirror 中其他分支的 refs 或 object；跨文件系统不影响这条非 local cache clone，只有缓存刷新、lease、cache clone 或 origin 绑定失败时才退回权威远端。这里共享的是 Git object 的物理块，不共享工作树、构建产物或可变运行数据；单独对一个 Workspace 执行 `du` 仍可能显示这些硬链接的完整逻辑大小。

Active Run 中通过 `workspace create` 创建且未显式提供 `--base-branch` 或 checkout ref 的仓库具有更窄的历史边界：jarvis-box 由 remote symbolic `HEAD` 选择默认分支，随后在 repo-cache 可用时从刷新后的 bare mirror 做非浅的 `--single-branch --no-local --no-tags` clone，并把 Workspace `origin` 恢复为权威 remote。cache 不可用时才直接从权威 remote 做相同边界的 clone。该路径不把 tag ref、其他分支 ref 或其他分支独有 object 暴露给 Workspace。需要显式 branch/ref 的 Provider 路径继续使用其已声明的 checkout 合同和 repo cache；两类路径不能互相降级。

Workspace clone 和 Jarvis 执行的 checkout 默认设置 `GIT_LFS_SKIP_SMUDGE=1`，只检出 LFS pointer，不在 Task 启动路径自动下载图片、视频或其他 LFS 内容。这避免 cached clone 因 bare mirror 不是 LFS endpoint 而被误判失败，也避免与任务无关的 LFS 内容同时占用 `.git/lfs` 和工作树两份空间。确实需要二进制内容的任务应在已绑定权威 `origin` 的 Workspace 中用 `git lfs pull --include=<path>` 按路径 materialize；Operator 可以显式覆盖该环境变量恢复 Git LFS 的标准全量 checkout。Status 的 clone 进度会显示 `LFS 按需下载`，使该策略对操作者可见。

Start 的已登记 Workspace 因 `low-disk`、`ENOSPC`、`EDQUOT`、暂时不可取得的 Git ref 或其他物化错误而尚未就绪时，Task 保持 `status=running`，没有 `current_run_id`；最小 `pending_launch` 记录使用 `wait_reason=workspace-materialization-wait` 和下次重试时间，入口 receipt 单独返回 `waiting=true`。`waiting` / `storage-wait` 不是 Task status。服务启动时及此后每 5 秒只扫描带当前版本合法 `pending_launch` 的 canonical Task state；恢复器重新调用原 lane launcher，由 TaskService 再次物化并用现有 owner/sequence CAS 创建第一个 Run。并发恢复最多一个调用取得 Run owner，服务重启不丢失等待义务，也不需要 Redis、全局 FIFO queue、Workspace 目录发现或进程内 callback。只有全新空状态或当前版本显式写出的 admission scaffold 可以取得首次 Task registration；没有 pending claim 的历史 `accepted` 状态不会被猜测为待执行工作。已发布旧格式的 `admission_pending=true` 与匹配 Start receipt 属于待执行工作，必须验证原始入口后转换；首次 Start 的兼容读取覆盖 review、IM、命令、自定义任务、issue/workflow、followup、自改进与已受理的定时任务。恢复保留原 Task、原指令和入口数据，仍经过原 launcher 与 TaskService；已退役定时名称只允许恢复已有受理义务，不恢复新触发入口。重复任务依赖与磁盘等待分别保留，磁盘恢复不能绕过尚未完成的旧 Task。旧 IM 附件复制到新 Run，过期回复凭据保留原到期与接收目标语义，由连接器检查主动消息能力。workflow 保留原输入 schema 和 action grants。Delivery Metrics 恢复遵守禁用设置，已有精确历史结果时不启动分析，普通刷新识别原随机 ID 的已迁移 Task，完成结果由同一缓存 owner 保存。缺少原始输入、归属冲突或不能唯一关联输入的旧 Continue receipt 保留原文件并使升级失败，不能清空 intent、选择最新 staging 目录或把 Continue 改成 Start。转换成功时消费已知旧准入标记；mixed-format 记录有旧 pending claim 却没有 canonical pending owner 时拒绝写入。无法持久化 Task registration 的硬 ENOSPC 不能伪装成已接收，必须向入口返回错误。

Task-store 的一次 `ENOSPC`、权限或原子写失败是当前 persistence fault，不是只能随进程重启清除的配置状态。服务每次启动都先对实际台账根目录执行同一条真实写探测；探测失败仍提供只读诊断，并将当前故障交给既有准入和周期恢复处理，不得把新进程尚无锁存快照当成写能力已经恢复。健康检查、Run 准入和周期 terminalization recovery 都走和正式状态写入相同的文件锁及 crash-durable 原子替换路径执行 create/write/file-fsync/rename/directory-fsync/delete 探测；探针若不完成文件和目录同步，不得解除 latch。同一时刻的并发检查合并为一次探测，探测本身失败不会覆盖原始业务写入的故障证据，成功也只解除它开始时观察到的错误 generation，期间出现的更新错误不能被旧探测误清除。终态重放不是请求路径上的进程内重试：每个待终态 Task 只留一份 durable intent，由一个周期扫描协程按固定节拍重放，每轮至多一次；除启动核验外，运行期真实写探测只在 latch 存在时进行，次数只随扫描节拍增长、不随 Task 数增长，所以磁盘故障期间不会出现探测惊群。`JARVIS_TASK_STORE_MIN_FREE_GB` 只约束新 Run/clone 准入；终态恢复以实际可写为提交条件，不要求磁盘先回到新工作余量，也不提前删除当前 Task 的 Workspace。当前 fault 解除后，新 Run 或 finalization 清除 Task 的 `task_store_degraded` 并记录恢复时间；workspace 卷恢复后同样清除 `workspace_storage_degraded`。最后一次错误和恢复时间继续作为历史诊断信息保留，但不得继续阻塞调度。

准入检查与运行期写入属于两道不同的保护。agent 启动后，Runner 的 `run-trace.jsonl`、result、`reply.md` 或其他关键 Run Artifact 的持久化失败都绑定到当前 Run；runtime-native AgentSession stream 不由 jarvis-box 写入或复制。即使进程 exit code 为 0，Jarvis-owned Artifact 写入失败也必须提交 `persistence-failed / failed`，保留 Run 诊断与已登记 Workspace 的归属，不能伪装成 completed。Artifact 已持久化之后发生的 provider delivery failure 不属于 Run persistence failure：Run 保持 `succeeded`，外部结果只追加到该 exact Run 的 typed effect receipt（`succeeded|failed|unknown`）。definite failed/retryable delivery 的有界机器重试、耗尽或不可重试结果不改变执行已成功的 Task `completed` 状态。独立的 RetryDelivery 先写 `effect_retry_intent` 和新的 effect-start，再恢复同一 Run 的 delivery effect，不创建 Run；普通带新输入的 Continue 独立受理。`unknown` 不能自动重发。其他 completion callback、Task 终态提交失败不产生第二个 blocker 名，也不把 Task 升级成人工待办：终态提交携带的 durable `TerminalizationIntent` 原样保留，由周期 terminalization recovery 无条件幂等重放同一 intent，重放成功前 Task 保持 `running`，以未结算的 terminalization intent 投影机器推进义务（不是 `finalizing` Task 状态），重放失败只以 `taskservice_completion_error` 与 `taskservice_recovery_failed` 状态事件暴露给运维。最终事件和通知只在 provider effect 回执及 Task 终态提交之后触发，不以成功送达为执行完成前提。准入检查通过后，创建 `runs/`、创建具体 Run 目录或 Workspace clone/create 直接返回 `ENOSPC` / `EDQUOT`，都必须回到同一持久化存储等待准入或 Run launch wait（不是 `storage-wait` Task 状态）；已经取得 owner 的未启动 Run 先终态化为 failed，再释放 owner。TaskService 完成这次转换后必须向所有 lane 返回 Waiting，provider/lane wrapper 不得把 canonical 存储等待回执重写为 `launch-failed`。错误只登记在对应 Task 的存储证据中，不得误锁无关 Task。周期恢复重新检查实时容量，并在成功取得新 Run 后清除等待错误、记录 recovery。

文件锁不可用时不得退化成只有进程内 mutex 的写入。锁创建、`flock`、状态写入或 rename 任一步失败都必须让本次 mutation fail closed 并登记新的 persistence fault。低磁盘准入只阻止会继续放大写入的新 Workspace/Run；已终态 Task 的登记式自动清理和 Status 手工删除仍是释放空间的通道，不受进程内 persistence fault 阻断，释放后由真实写探测解除 fault。不得通过扫描目录、猜测归属或删除仍有执行或恢复 owner 的 Task 来应急回收；Workspace 由登记驱动的终态清理负责，terminal Task Artifact 由 retention clean 负责。

## Prompt Artifact

`accepted-request.json` 是准备前的 accepted-input snapshot，保留本次 Run 的 admitted prompt 与 exact `OriginalPrompt`，使准备失败或重启不会凭历史会话猜回输入。它不是最终进程 prompt，也不授予 recovery 重放未确认输入的权限。

每个 Run 的最终输入 Artifact 只在 lane 准备、ordinary runtime preparation/hook 和 recovery prompt 调整全部完成后由 TaskService 一次写入：

- `input.txt` 保存 adapter 加执行契约前的 exact `OriginalPrompt`。Start 是首次用户输入，agent Continue 是本次新用户消息（仅有已验证的未接收 source 输入时按既有规则在其前），recovery Run 可以为空。
- `prompt.txt` 保存当次进程提示词，包含按需追加的 lane 执行契约、运行上下文和无凭据群历史访问指引。多进程评审保留公共提示词。指引不改写 `OriginalPrompt`。
- `run-context.json` 在同一最终 Artifact 写入阶段随该 prompt 封存。

这些文件不包含历史用户/助手消息、native session 内容、resume handle value、cross-agent source ref、raw IM-context capability 或 provider-native credential。它们不能作为跨 Run prompt history、native resume 或群历史访问授权来源。

## Private Handles

只有 runtime adapter 的 structured start/resume receipt 同时绑定完整
Task registration、Run generation、AgentConversation 和 agent 时，才可以保存
runtime-native session id、thread id、checkpoint ref 或 opaque token。Codex adapter
从 `exec --json` 的首条 `thread.started` 协议事件取得 session，保存在该 Task 的
`.runtime/<run-id>/` 私有目录；读取时复验完整 owner。已验证 receipt 的 Continue
接续原生会话；没有 receipt 的现代执行创建 child AgentConversation，不扫描会话日志。

已登记的 0.2 升级格式允许接续精确旧 Run 的原生 handle：先验证旧 Task registration、
Run generation、AgentConversation 及旧执行事件，再核对 handle 的 agent、capturing Run
和 session 格式。旧 Run 发布为 v2 后仍须通过相同旧执行证据。旧 handle store 只从
canonical runtime 配置的 `JARVIS_STATE_DIR/agent-resume-handles/` 读取；
`JARVIS_RUN_DIR` 可独立配置，不能从 Task 目录反推 state root。缺少 state 配置会拒绝续接，
不会静默改用新会话。现代执行缺少 receipt 不取得旧 handle 的读取资格。

0.2 IM Target 的首次恢复仅消费通过旧创建事件验证的首个 Run（sequence=1）context。
该文件的 Task/Run ID 与 run_dir 必须和已登记 owner 全等，不能带现代 generation 字段；
Task 目录由已验证的 Run 所在路径确定。旧 writer 不写 task_dir；若该字段存在，仍须与 owner 全等。
会话标识须匹配 Task root 原已保存的 provider:conversation。后续 context 不能补写
历史 Target，已存在 Target 不覆盖；不匹配时拒绝，TaskService 之外不发布恢复值。

规则：

- 现代 private receipt 的 key 和每次读取都必须复验完整 fence，裸 Run ID 不是 key；
  旧 handle 的 Run key 只定位候选，不能代替上述升级来源与归属证明。
- private value 只在 adapter dispatch 时解析。
- private value 不写入 Status response、Status Artifact listing、E2E evidence、service logs 或用户可见摘要。
- private value 不写入 `task-state.json`、`task-events.jsonl`、`run-context.json`、`prompt.txt`、`result.json` 或 runtime logs。
- private handle 不能跨 runtime agent 复制。
- cross-agent source ref 不是公开持久对象；目标 runtime 的 continuation instruction 只引用 Task/Workspace/lineage 所需信息。

## Status Projection

`/status` 的 Task projection 是响应 allowlist 和进程内派生读模型，不是独立存储层或角色权限层。系统设置使用独立的 typed response，但与 Task projection 属于同一人类信任边界。

规则：

- jarvis-box 单进程运行时，Task projection 必须保存在进程内，通过 Task state 写入、Run 完成事件、服务启动时从 Artifact 重建和后台 reconcile 更新。重建 projection 不调度 Run。
- 磁盘上的 `task-state.json` 和 `task-events.jsonl` 是恢复来源，不是每个 `/status` 请求的查询引擎。
- `/status` 不引入 Redis、SQLite 或其他外部 cache/database。外部存储只有在多节点写入、十万级 Task、跨进程事务或复杂离线查询成为真实需求后才重新评估。
- 如果 status list、summary 或 work-items 需要在请求路径中全量扫描 `runs_dir` 才能返回，视为实现偏离契约。兼容完整读取对已登记 Catalog 的同步校验和对单个工作台账文件的读取，不等于扫描运行目录发现 Task；工作台摘要、分页和事件流则使用已发布快照，读取边界见 [Status API](status-api.md#发布与读取)。

允许字段：

- safe Target key/hash 和标题
- Task id、标题、状态、更新时间
- lane、`custom-user-task` 的 `job_id`、触发 reason、最近成功/失败时间
- current/latest Run id
- safe agent name
- safe resume status
- operation policy
- opaque Artifact refs

禁止字段：

- resume handle value
- native AgentSession id
- native AgentSession file path
- cross-agent source ref
- raw inbound payload
- reply token
- raw provider token
- 作为 Task 结构化字段的 arbitrary filesystem path；系统设置 response 和 bounded Run 输入可以展示当前主机路径
- `task_dir`
- `run_dir`
- `log_file`
- Workspace absolute path
- chat message history

## Status Artifact Access

Status Artifact endpoint 只解析授权后的 safe artifact ref 或受限 `run`/`run-group` 相对路径。它不提供 Workspace root，不读取 raw payload、run-context、prompt、RunTrace、events 或 runtime logs。系统设置面板可以显示它自身 typed response 中的主机路径，但不增加任意 root/path 文件浏览器。

规则：

- 先做 Target visibility check。
- 只读取允许 root 下的文件。
- 不列出或读取 ChatBridge `attachments/` 或 `outbox/` 目录；路径解析后落入这些目录的 symlink alias 也必须拒绝。
- 返回文本前必须 redaction。
- 不返回文件系统绝对路径。
- 不返回 private handle、native session id、cross-agent source ref、reply token、raw provider token 或主机路径。

## Logs

`JARVIS_LOG_DIR` 保存 jarvis-box service、deploy 和 runtime wrapper 日志。它不等于 `runs_dir`，也不被 `tasks clean` 清理；宿主 scheduler 与 Runtime Foundation logs 不属于该目录的产品契约。

Run 内唯一的 Jarvis-owned 进程日志是 `run-trace.jsonl`。runtime-native AgentSession 仍由对应 agent 管理，不属于 Run Artifact。Service log 只能通过 CLI 运维命令读取；Status 系统设置面板只展示 runtime inspector 已经结构化并脱敏的诊断与内部轮询摘要，这些原始运维字段统一位于“技术细节”，不成为顶层操作分区。

## Workspace

`JARVIS_DEPENDENCY_CACHE_ROOT` 保存跨 Task 复用的包管理器缓存，默认是 `${JARVIS_RUNTIME_ROOT}/dependency-cache`，Docker 为独立持久卷 `/var/cache/jarvis-box`。它不属于 `workspaces[]`，workspace cleanup 和 Task retention 都不得删除它。Jarvis Box 只注入标准缓存环境；如配置 `JARVIS_WORKSPACE_DEPENDENCY_CONFIGURER`，则在已登记 Workspace 验证、复用或重建完成后、Agent 启动前调用 Operator 提供的程序。该 hook 可配置依赖工具，也可写 workspace-local Git identity 等仓库本地策略；失败必须让 Run 启动失败，不能带着半配置 workspace 继续执行；hook 内容仍由客户 Runtime Foundation 负责。

缓存根目录只承载各工具的原生下载缓存、内容寻址缓存和工具自身支持的共享安装目录。服务启动时预先创建管理根内的 vcpkg 默认二进制缓存目录，已有目录及权限保持；该目录仍属于持久依赖缓存，不随 Task Workspace 清理。它与 `repo-cache` 在 Workspace 准备流水线中协同，但不混用生命周期或目录：repo cache 复用 Git object，dependency cache 复用包管理器依赖，LFS 内容默认按需 materialize。内置 policy 覆盖常见生态的标准缓存入口：XDG cache、Go module/build cache，npm/Yarn/pnpm/Corepack/Bun/Deno，Playwright/Puppeteer/Cypress 浏览器缓存，Turbo/Nx task cache，Python 包管理器、pre-commit、Ruff、mypy 和 pycache，Gradle/Maven/Coursier，Cargo 和 Rust 编译缓存，C/C++ 的 ccache/sccache、Conan、vcpkg，以及 NuGet、Composer、Bundler。`CARGO_INCREMENTAL=0` 是默认 Agent policy，用于压低短生命周期 Workspace 的 Rust incremental build 状态；若运行环境可找到 `sccache`，Jarvis 把 `RUSTC_WRAPPER` 设置为解析后的 sccache 可执行文件路径，否则不设置 wrapper，避免 Cargo 在缺少工具时失败；初始注册集合中只有一个 Cargo Workspace 时，Jarvis 会通过 `CARGO_BUILD_BUILD_DIR` 把 `debug/deps`、`debug/build` 等中间构建目录放到按 repo identity 隔离的共享 cache，但不改变 `CARGO_TARGET_DIR`。Jarvis 不支持在 active Run 动态注册第二个 Cargo Workspace 后刷新当前 Agent 环境，也不会自动清除该变量。配置了可执行 agent browser 时，Jarvis 还向 Agent 暴露 `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH` 与 `PUPPETEER_EXECUTABLE_PATH`；这是显式 executable handoff，不会把 Playwright 和 Puppeteer 的 revision cache 合并成一个目录。

Bundler 是共享安装目录的明确例外：`BUNDLE_USER_CACHE` 保存用户级索引与下载缓存，`BUNDLE_PATH` 保存可跨 Workspace 复用的已安装 gems；Ruby ABI 与 native extension 平台隔离沿用 Bundler 自己的目录结构。通用 Workspace 准备接口负责调用各工具 policy；生命周期调用方不识别语言或包管理器。Jarvis 仅为本次 Run 准备时登记集合中实际使用 Yarn 的 Workspace 生成 `.jarvis-yarnrc.yml`，并通过 `.git/info/exclude` 隐藏该文件；能严格确认 Yarn 3+ 时加入 `hardlinks-global`，其他 Yarn 版本保留自身兼容行为，非 Yarn Workspace 不写入该文件，零/非 Yarn 集合不创建空归属收据或导出专用 rc 文件名。自动策略写入前检查全部 Yarn Workspace；遇到 Workspace 自有的同名文件，本次不改任何配置并跳过整个 Task 的自动 rc 策略。既有 schema 1 归属收据保持可读，合法空集合不构成文件归属；收据损坏、token 不符或已登记持有的文件归属冲突仍拒绝启动。严格确认支持基于 vendored release 文件名：`.yarnrc.yml` 顶层 `yarnPath` 在 Workspace 内存在且文件名符合 `yarn-<版本>.cjs` 约定、版本 major ≥ 3，并与 `packageManager` 声明交叉验证；`yarnPath` 为 `${ENV}` 插值、URL、非字符串或文件缺失时无法证明，保持不注入。Jarvis 不支持在 active Run 新增不同 Yarn major 后刷新 Workspace-local policy；当前 Agent 不会自动获得新设置，Operator 显式环境仍优先。文件系统支持跨目录硬链接时，Yarn 可以让各 Workspace 的 `node_modules` 复用 global content store 的物理文件。单独对一个 Workspace 执行 `du` 仍可能显示这些硬链接的完整逻辑大小，不能把该数值直接与 cache 目录相加当作物理占用。跨项目共享整个 `target/`、`node_modules`、`build/`、`.next/`、`dist/` 等编译结果不属于默认模型；Cargo 只共享中间 build-dir，最终 binary 和脚本常用的 `target/` 顶层输出仍留在 Workspace。需要项目级 build cache 时，应使用工具自带内容寻址缓存，或由 workspace configurer 按 OS、架构、工具链和项目建立隔离键。缓存属于单个 Jarvis 安装的信任边界，不跨客户共享，清理由独立运维策略负责。

`JARVIS_WORKSPACE_ROOT` 保存 Task Workspace。一个 Task 可以拥有零个到多个 Workspace；唯一归属记录是 append-only 的 `task-state.workspaces[]`。每项包含稳定的 Task-local id、服务端分配的绝对路径、可选 repository metadata 和 `primary` 标记。路径由 `task_id + task_instance_id + workspace_id` 共同派生；同一个 task id 被重新创建后也不会复用旧实例目录。非空集合恰好有一个 `primary=true`，只负责选择 Run 的默认 `cwd`；空集合不合成目录，Run 使用 launcher 的普通工作目录。

初始 Workspace 必须和 Run ownership claim 在同一次 crash-durable Task state mutation 中登记；active Run 中的 zero-workspace Task 必须通过 `jarvis-box workspace create --id primary` 建立第一个 canonical Workspace，非空 registry 后续增加仓库时使用普通 stable id。Runner 在所有 agent lane 的启动和 resume prompt 中注入这条 ownership contract，明确禁止 agent 绕过该命令创建、替换或物化 `JARVIS_WORKSPACE_ROOT` 的任何直接子项；已登记 Workspace 内部的正常文件操作不受影响。两条登记写路径都先验证 repository source 可解析，再提交 `workspaces[]`。ownership 与存储准入由 TaskService 复验；实际创建、clone 或 checkout 不占用 Task 生命周期锁，目录发布和清理由对应 Workspace lease 串行化。首次 Start 的零 Run 准备还持有 Task 独占 Workspace lease，完成后以完整 Task/admission fence 再次认领 Run；活动 Run 的动态新增在返回成功前再次确认原 Run ownership。`--project` 依赖已配置的 `GITLAB_HOST`；GitHub 等其他远端使用显式 `--remote`。验证失败发生在 registry mutation 和目录创建之前；声明 repository 的成功 Workspace 必须是真实 Git worktree，只有 project/remote 都为空时才允许空目录。jarvis-box 不通过独立 reclaimer 扫描或清理 Task Workspace。已有 repository 目录必须包含真实 `.git` 目录或 worktree 文件；登记的 id、path、project、remote 和 primary 保持稳定。目录从未创建成功或已按登记清理时，Continue 可以由同一个 Workspace owner 重新分配路径；`base_branch` 只是目录准备输入。`cwd`、`workdir`、Run context、Artifact、marker 文件和目录扫描都不是 Workspace 归属来源。

一个 Task 的全部已登记 Workspace 跨多个 Run 存续。每个 managed Run 从启动到其进程组退出都持有同一把 Task 级 shared Workspace lease；清理前必须证明没有 Run owner、没有存活的已登记进程身份、没有 terminalization intent，取得对应的 exclusive Task lease，再逐项取得 exclusive Workspace lease。手工与定时清理共享这组准入条件。Run 结束/取消时先按 Task+Run 环境标记和稳定进程 identity 清理受管后代进程；脱离 managed 进程组的进程再由 `cwd` 和 open-file reference 扫描兜底，无法确认安全时保留目录并进入可见的延迟清理。外部资源只来自 Task 显式登记的 typed `external_resources[]`；文件名、目录名、repository 名和 Docker working-directory scan 都不能创建资源所有权。详细状态机见 [Task external resource lifecycle](task-external-resource-lifecycle.md)。Task 进入 completed/cancelled 且无运行或重试 owner 时，Task state 写入 `workspace_cleanup_due_at = now + JARVIS_TASK_WORKSPACE_CLEANUP_DELAY_MINUTES`；Continue claim 新 Run 时清除该截止时间。任何 Workspace disposal 失败都持久化并退避重试。删除已开始但回执未落盘的登记项在恢复扫描中继续同一 intent；接续前重新取得 Task/path lease、校验登记归属和进程占用，幂等清理剩余目录（含 .deleting）后写回执，不因缺少清理截止时间而永久遗留。全量清理成功后写入 `workspace_disposal_completed=true`；`tasks clean` 只消费这个凭证，不重新解释 Workspace 或外部资源。

用户 Stop（含旧 cancel 别名）在同一停止事务中持久保存 defer_workspace_cleanup=true 并按 JARVIS_TASK_WORKSPACE_CLEANUP_DELAY_MINUTES 登记清理截止时间；Continue 先取得锁时清除旧截止，过期清理后仍可由同一 Workspace owner 重建目录。已发布 intent/receipt 缺少该字段时保持原规则。Provider 明确发出的 Issue close 或 MR close/merge，以及经验证的 GitLab/GitHub subject-not-found writeback 都是立即清理边界。Subject-not-found 需要最终评论返回 HTTP 404，并由同一 provider 身份证明目标项目或仓库仍可访问；项目/仓库不可访问、鉴权失败和配置错误保持普通 writeback failure。立即清理先解决 active Run 与同 Run 后代进程 ownership，再按同一份 `workspaces[]` 和 typed `external_resources[]` 尝试清理，不等待配置的保留窗口。Subject-not-found 清理失败或延迟时，Task 保留 completion `terminalization_intent` 并保持 `finalizing`；恢复器完成清理后再原子提交 `cancelled`，成功 Run 不改写为失败，`task_cancelled` 只发布一次。普通 Run 结束与 workspace 删除彼此独立；Run 终态落盘、provider writeback 或其恢复不得以提前删除 workspace 作为前置条件。

Task 首次 claim 还会由 `taskstore.Store` 在全局登记锁内分配递增的 `task_registration_sequence`，生成随机不可变 `task_instance_id`，并把外部工作对象规范化为不可改绑的 `task-state.subject`（`provider`、`kind`、`project`、`number`）；这些字段和 `workspaces[]` 在同一次 state mutation 中先于目录创建落盘。`.task-registry.json` 及 `.task-registry.lock` 只属于这个 Store，不存在独立 registry 包或 adapter writer。Provider webhook 的明确终态会按该登记精确匹配事件首次处理时已经存在的 Task：GitLab issue `close`、MR `close/merge`，GitHub issue `closed`、pull request `closed`（按 `merged` 归一为 `close/merge`），以及 Jira issue 状态进入 Done category 或被删除。匹配到的非终态 Task 统一经 `TaskService.CancelTask` 终止并清理全部已登记 Workspace；已经 completed/cancelled 的 Task 保持原终态，只重试登记目录清理。

Provider adapter 只负责把 webhook 归一成 subject terminal event，TaskService 不含 lane/provider 清理分支。首次处理一个 provider delivery 时，adapter 与 Task 创建共享全局登记锁：先把当前登记序号写成 durable `task_registration_cutoff`（status=`planning`），再扫描 cutoff 以内、subject 精确匹配的 Task，最后把每项 `{task_dir, task_instance_id, task_registration_sequence}` 写成 receipt 快照后才调用 TaskService。即使进程在 cutoff 落盘后、扫描前退出，retry 仍按同一 cutoff 重新计划；部分失败只重放 receipt 快照。同一路径后来被其他 Task 实例复用时，instance/sequence 校验会拒绝副作用。receipt 写入失败、损坏或身份不匹配时必须 fail closed。`issue_or_mr` 仍用于展示原 URL，但不参与终态归属判断；Artifact、branch、workspace 路径和目录扫描也都不是 subject 或 workspace 的归属来源。

清理目录不删除 `workspaces[]` 登记，因此 Status detail 仍能展示该 Task 的全部路径和存在状态。登记目录已经不存在时，手工删除仍是合法的幂等操作并返回 `already_absent`。`tasks clean` 只处理 terminal Task/Run Artifact；Task Workspace 的自动和手工清理由登记表和持久化截止时间驱动，不通过目录扫描或 orphan discovery 推断归属。

旧 waiting 默认经 Flyway 迁为 completed；仅因业务观察或发送结果而 failed 的成功执行同样纠正为 completed。业务观察、问题、原身份、revision、Run 字节与交付回执保留，迁移不执行工作。仍有机器准入或执行恢复义务的记录保持 running 的对应阶段，发送重试不改变成功执行结果。旧终态记录没有清理截止时间时，清理器使用原 `updated_at` 加配置保留期作为到期依据，并重新验证同一 Task/Run、登记与路径 lease；迁移不伪造新截止时间。completed、cancelled 的空闲终态工作区均可到期回收，真实执行失败继续保留原有工作区和诊断 Artifact 以便恢复；仅发送失败按成功执行的原保留期限清理工作区；业务卡点不持有工作区。

## Clean

`tasks clean --older-than <days>` 删除的是 `runs_dir` 下距最后业务活动超过保留期的 cleanable terminal `task_dir`。业务活动包括受理请求、Run 创建/开始/结束、取消及常规交付回执，以及事件订阅的受理、注册、撤销、触发认领与结算。订阅处理结果为 `blocked` 时同样保留活动时间，不能从结果名称推断是否发送过续接受阻提醒。未结算的订阅 claim 仍可能拥有在途外部投递，阻止删除。概括标题及资源维护的元数据更新不延长记录保留期。

处理特定任务时可追加 `--task <task_id>`，只清理该 Task；`--dry-run` 先预览。同样要求终态、保留期与已完成的工作区处置凭证，不会放宽安全条件。

删除内容：

- 整个 `task_dir`
- 该 `task_dir` 内的 state、events、prompt、payload、log、result、reply、comment 和 writeback artifact
- 将来 sealed handle 能力落地后，由同一完整 Task/Run fence 证明的 private handle entry
- 删除后变空的中间父目录

不删除：

- `runs_dir` 根目录
- `JARVIS_STATE_DIR` 根目录
- `JARVIS_LOG_DIR`
- `JARVIS_WORKSPACE_ROOT`
- 仍有 active Run、机器执行义务或 `recovery-required` 的 Task

只有 `completed` 或 `cancelled` Task 可以被 retention clean。被清理的 Task 不能再 Continue；需要继续时必须从可见 Target Start。

## Supersession 关系与审计

任务取代采用“原始终态不可变，关系证据可追加，有效状态可计算”的存储模型：

- 原始 `status`、`phase`、退出码和收尾错误保持不变。
- 显式人工关联只向旧 Task 追加 `superseded_by`、`supersession_linked_at` 和 `supersession_link_reason`。
- 系统同时追加 `task_supersession_linked` 事件，事件的 `provider_action` 固定为 `none`。
- `effective_status`、`monitor_status=superseded`、`next_action=none` 等字段在读取任务集合时投影，不覆盖原始失败记录。
- 只有后继 Task 完整成功、subject 一致且存在显式 lineage 时投影才成立。

因此，历史 reconcile 不会把已被取代的 Task 重新加入继续执行或评论回写计划。

## Webhook 受理与恢复

GitHub、GitLab、Jira、飞书项目、TAPD、禅道、云效 Projex 与 Codeup 共用同一投递受理协议，各渠道的规范路由和别名行为一致。TAPD 的无业务连通性探针仍同步返回 200；鉴权失败、非法 JSON、超大请求及接入未配置的错误仍直接拒绝。

业务投递通过鉴权和 JSON 校验后，服务将请求写入 `runs_dir/.webhook-deliveries/<receipt_id>.json`，同步文件和目录后立即返回 `202 Accepted`。该目录及收据限当前运行用户访问；认证请求头不保存，body 中的接入 token 在存储前由对应 adapter 清除。GitHub 的已验签原始 body 保持不变。

收据固定渠道、事件、投递 ID 和完整 body 的 SHA-256。平台没有投递 ID 时，由渠道、事件与 body 摘要确定身份。相同投递处理中返回 202 和 `delivery_in_progress`；完成后返回 200 和 `webhook_delivery_duplicate`，不会重复派发，也不会把缓存中的 Task/Run 字段作为新的生命周期依据。初始 202 中只有 `receipt_id` 和可用的 `delivery_id`，没有 Task ID、业务完成结果或清理计数。

服务后台继续调用对应 dispatcher；所有 Task/Run 准入、状态变更和副作用仍由原有 TaskService owner 处理。最终业务结果进入收据的 `result.status` / `result.payload`、work ledger 和适用的 Status 事件，不再通过原 webhook HTTP 响应返回。完成或确定失败的收据清除请求 body，只保留身份及结果；派发结果未知时保留请求 body 供核查，不自动重放。

运输收据的阶段为 `pending`、`dispatching`、`completed`、`failed`、`outcome_unknown`；它们不是 Task/Run 状态。服务重启只继续尚未开始派发的 `pending` 投递。发现没有活跃派发者的 `dispatching` 收据时，标记 `outcome_unknown`，不盲目重放可能已经发生的外部副作用。失败或结果未知的重复投递返回 409，应先检查 Task、后台结果与平台事实，再决定新的人工操作。

收据由 webhook 运输层独占写入，随实例状态目录备份和保留；Task retention clean 不删除投递去重依据。正常停止服务时不再认领新的投递，尚未认领的收据保持 pending；服务等待已经认领的派发结束后完成关闭，停服信号和原请求断开都不会提前取消该派发。派发返回不确定错误或明确报告未知的准入结果时，收据保持 outcome_unknown，不记成确定失败。
