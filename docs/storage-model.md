# 存储模型

jarvis-box 使用 artifact-first storage。每个 Task 的 `task-state.json` 是当前状态，`task-events.jsonl` 是审计事件流，Run Artifact 是证据。jarvis-box 不新增全局 FIFO queue、prompt history store、Redis、SQLite 或 status projection database。

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

以后新增存储格式时，必须保留从所有受支持旧格式到新格式的迁移路径。旧程序遇到未知的更高格式应拒绝改写并保留文件；不能将其当空数据初始化。确定性派生缓存可以重建，但已有 Agent/人工分析结果属于历史业务数据；分析指令和输入语义不变时，代码重构或格式升级不能触发重新分析。

## State Root

`JARVIS_STATE_DIR` 保存 jarvis-box 应用状态。它包含：

- Run/Task artifact root
- ChatBridge default Task bindings and message-to-Task indexes
- 其他受管应用状态

`JARVIS_STATE_DIR` 不是 service log 目录，也不是 Workspace。

Task 的可选 `runtime_recovery` 保存受信原生终止事实、完整来源 Run 身份、恢复类别、累计次数、候选使用记录、到期时间、认领的后继 Run 和停止原因。恢复预算与后继 Run 在同一 TaskService 事务中认领；重启不会清零。Claude终止及压缩回执保留实际协议标识，闭集接受`claude-stream-json/2.1.235`、`claude-stream-json/2.1.304`，旧235记录不重写为304；未知版本不授予恢复权。缺少该字段的已发布 Task 保持原语义，不因扫描历史失败而获得自动执行权限。目标版本 Flyway 在 startup lease 前验证存储，并保留旧 Task、会话、工作区与外部回执。

恢复只作用于所属 Task，不创建 `runtime-agent-route.json`、`runtime-agent-events.jsonl` 或全局 cooldown，也不读取旧同名文件推断权限。原始 stdout/stderr、历史日志与助手正文不能生成恢复意图。三种允许的恢复及停止规则见 [执行模型](execution-model.md#原生终止的有界自动-continue)。

## Delivery Metrics 派生状态

`JARVIS_STATE_DIR/status-value/` 保存 GitLab 和 GitHub Delivery Metrics 的可重建读模型派生状态：

- `snapshots/<provider>.json` 保存当前快照、Provider scope、登录主体和 pending 数量；
- `evidence/<provider>/<hash>.json` 保存已完成的 typed classification 和固定 evidence code。

分析执行属于普通 `delivery-metrics` lane Task。Task 根目录只保存首次 provider input、typed state 和审计事件；每个 Run 目录保存自己的 prompt、run context、`delivery-metrics-result.json` 和其他 Run Artifact。当前执行或等待恢复的这些 Task 会进入默认 `jarvis-box tasks list`，历史记录用 `jarvis-box tasks list --all --lane delivery-metrics` 查看，并受 Start、Continue、Cancel 和 `tasks clean` 的统一生命周期控制。

快照仅在 scope、actor 和 schema 均匹配时复用；scope 包含 Provider、Provider host、配置仓库集合和 Delivery Metrics 合同版本。Runtime Agent 选择不进入分析 identity，因此切换 Agent 不会重算已完成 evidence。相同 Provider、host、完整账号身份、仓库、MR/PR 和源 SHA 的有效结论继续复用；合并后的评论或元数据 `updated_at` 变化不会使结论失效。已发布的 schema 4/v7 文件及受支持的 v1 合同结论保持可读，原证据键中的更新时间字段不再作为已知格式的结果匹配条件，无需重写原文件。原 Task 已清理时也可复用保留证据；账号、主体或源 SHA 不同不得串用。

status-value 只保存 typed 派生结果，不保存 raw note、review body、Agent stderr、token 或命令。不得为 Delivery Metrics 增加全局 FIFO queue、cursor 或私有分析状态；pending 项只能通过 Provider 刷新和 Task store 重新派生。服务启动、MR/PR 关闭或合并、分析 Task 完成及定时补查会主动同步快照，普通 GET 不提交分析任务。文件损坏、版本不兼容或 scope 不匹配时，服务忽略不兼容的派生状态并重新同步；已有 Task 的失败或无效结果仍由操作者明确 Continue，不因重建快照自动重跑。操作步骤见 [Delivery Metrics 历史起点](delivery-metrics.md)。

## Status Metrics 派生状态

`JARVIS_STATE_DIR/status-metrics/task-runs-daily.json` 保存本机 Task Run by-day 趋势的可重建 rollup。主数据源是 `JARVIS_WORK_LEDGER_FILE` 指向的 `work-ledger.jsonl`，默认回落到 `JARVIS_STATE_DIR/work-ledger.jsonl` 或 Run 根目录旁的 `work-ledger.jsonl`。

趋势的统计范围是首个可信启动事实所在日期到今天，包含零运行日；页面的 7/30/90 天选择只改变显示范围，不截断历史统计。Task Artifact 清理不删除 ledger 中的历史启动和耗时事实，不能用固定 180 天窗口代替全量口径。

rollup 保存 schema、source、timezone、按天 count、异常时间/格式计数和完整性校验信息，以及 ledger 的读取位置与文件身份。Ledger append 时增量读取；ledger 截断、轮转、替换或缓存损坏、不兼容时重新建立派生结果，不能把旧缓存当历史事实或返回可信的假零。

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

`custom-user-task` 是 providerless prompt job。它的 `job_id` 保存在 `task-state.json`、当前 Run 的 `run-context.json`、Task 根目录的 `payload.json` 和 intake/conflict event 中，用于日志、Status、筛选、防并发和排障；`reason` 保留可读触发来源。jarvis-box 不为它创建 provider writeback projection，IM、webhook 或 GitLab 投递结果必须由 agent task 自己写入结果证据。重复触发同一 active `job_id` 时，服务在已有 Task 的 `task-events.jsonl` 中写入 `custom_user_task_start_conflict`，并向调用方返回 conflict；这不是全局队列、cursor 或自动补跑机制。

`chat-bindings/bindings/` 每个 IM Target 保存默认 Task 指针或 `/new` 的重置记录，按接收时间与入站消息 identity 排序。重置不删除排序凭据，较旧准入的恢复不能覆盖较新的选择或重置。`chat-bindings/messages/` 保存同一 Target 内 message id 到 Task 的引用索引，包括已确认发送的机器人回复 id；不创建 Run 的控制消息在动作前以可选 `control_claim=true` 登记消费，其 TaskRef 四字段全空，不授予引用权限，也不证明动作完成或回执送达。缺少该标志的已发布消息记录继续按原 Task 引用合同读取，无需重写。两者均以同步临时文件、原子替换和目录同步提交；临时文件写入失败不破坏已提交记录，并发读取只会看到替换前或替换后的完整 JSON。两者都不保存 Run id、Run 状态、reply token、native session 或 provider credential；Task/Run artifact 始终是执行状态的唯一事实来源。

消息索引的 `source_key` 为规范化的 `provider:connector:conversation`，文件名是 `SHA256(source_key + NUL + message_id)` 的小写十六进制加 `.json`，输入按UTF-8编码。读取时必须复验记录中的同一source key和原生message id；文件名不单独授予Task身份或操作权限。

IM 首轮准入的私有描述符保留原接收时间。恢复通过 TaskService 的原准入校验后补齐同一完整 TaskRef 的绑定，不使用恢复时刻重新选择默认 Task。已发布描述符缺少接收时间时使用原 Task 登记时间；已发布的默认 Task 指针和消息索引保持可读。目标版本 Flyway 在签发启动凭据前验证新增的选择与重置编码。

exact Run 的 `.private/reply-handle.v1.json` 可附加 `origin_sender_id` 与 `origin_sender_digest`，以 `chat-reply-sender/v1` 域绑定既有 handle digest。它们不改变已发布 credential digest、opaque ID 或有效期；缺少这对字段的历史记录仍按原投递合同读取，半对或摘要冲突拒绝。新消息无 token 且无 expiry 时，同一文件只保存目标及完整 sender 证明，不能伪造凭据或已消费次数。Flyway 追加 sender 迁移，只从注册及消息归属已核实的旧私有完整入站记录补齐；无法证明的历史 sender 保持缺失，不能从公开 payload、context 或 Task 首创者推断。原未知交付仍可通过已有 sealed operator attestation 在同 Run 处理，不创建 Agent Run。

ChatBridge 的入站附件与待交付文件分别保存在 exact Run 的 `attachments/` 与 `outbox/`：`attachments/` 中的文件只供 runtime agent 使用，`prompt.txt` 和 `run-context.json` 可以保存本地路径；`outbox/` 只接受目录根部的普通非空文件，实际可投递边界由精确 provider、connector capability 和 IM 渠道限制决定。私有目标凭据和最终交付回执另保存在同一 Run 的 `.private/`。TaskService 在发送前持久化 exact Run effect-start，随后只接受同一 fence 的 typed receipt；结果未知时不自动重放可能已经送达的附件。Status task projection、Status Artifact endpoint 和 symlink alias 都不得枚举或读取这些私有目录；provider 下载 URL、文件密钥、raw IM payload 和 reply token 不写入 Status response。

`.private/final-reply-receipt.json` 的完整v2回执继续保存原payload摘要及已确认附件前缀。可选的首次预检形状使用`preflight_only=true`和独立`reply_text_sha256`，完整`payload_sha256`为空、附件前缀和消息ID为空，只表示该exact attempt尚未执行最终发送且文件暂时不可读。它必须与同一Task/Run/intent及明确未发送的可重试effect一致；不能授权具名补发或未知结果裁定。完整读取成功并复验原文及目标后才转为普通完整payload形状，已有完整回执不得降级。已发布的完整v2数据不重写，缺少预检凭据的旧失败不从公开内容补造授权。

## RunTrace 与 Native AgentSession

Runner-owned `run-trace.jsonl` 是 jarvis-box 对当前 Run 进程 stdout/stderr 的唯一持久化日志，并按原始顺序追加进程输出；Status 从该 trace 重建脱敏时间线。当前 Run 的 bounded input 只保存在 TaskService 写入的 `prompt.txt`，RunTrace 不再复制 input record。Run 输入是真正交给 runtime agent 的当次指令，可以是用户原文，也可以包含 workflow 生成的契约、运行上下文和主机路径；它不能充当 conversation memory、跨 Run prompt history 或 native resume source。

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

`task-state.json` 记录 Task 当前事实；每个 `runs/<run-id>/run-state.json` 记录该 Run 当前事实：

- Target 和 Task 标识
- lane、`custom-user-task` 的 `job_id`、status、phase、lifecycle summary
- current Run metadata
- runtime agent name
- process metadata
- safe action policy
- safe resume handle status/ref
- artifact refs

`task-events.jsonl` 记录状态变更审计事件。事件用于排查和补充证据；当前状态以 `task-state.json` 为准。Run 产生的事件必须携带 `run_id`，可以确定顺序时同时携带 `sequence`。从事件恢复 Task 投影时按最大的 Run sequence 选择最新 Run，不能让旧 Run 的晚到事件覆盖当前 Run。

终态 Run 不可变。Task/Run state mutation 同时使用进程内 mutex 和文件锁，因此 Web 服务与独立 CLI 进程共享同一 compare-and-swap 边界；每次权威 JSON 替换必须依次完成临时文件 `fsync`、close、rename 和父目录 `fsync` 后才能返回成功，不能把 page cache 中可见但断电后可能丢失的 rename 当成 durable commit。Task 生命周期文件锁使用 runs root 外围稳定 inode，不放在会被 retirement 删除的 Task 目录内；它串行化每次 Run ownership/state 提交、Workspace 准备、到期清理和 Cancel。provider/local finalization effect 不得持有生命周期锁；同一 Task 另用稳定的跨进程 finalization owner 锁串行化 completion 与 recovery，使跨 Task 的 `workflow.start` 不会与 Catalog gate 形成反向锁序。runtime helper 也必须携带 Run id 并通过同一 ownership 条件更新 Task state 和 Task event；仅有 task directory 不足以取得写权限。新 Run 以读取到的 Task owner 和 `latest_run_sequence` 为 compare-and-swap 条件取得 `current_run_id`，并发请求不能无条件覆盖该指针，owner 发生 ABA 也不能复用旧 sequence；rename 已可见但目录同步失败属于 typed ambiguous commit，无论底层是 ENOSPC、EDQUOT 还是 EIO，都只能在真实写探测恢复后按同一 Run/Task instance 重写确认，不能另建目录或遗留幽灵 owner。TaskService 是 managed Run 的终态仲裁者；只有仍拥有当前 Task Run identity 的 completion 才能先持久化包含不可变 Task instance、完整 Run 终态 patch 和 Task 终态 patch 的 write-ahead `terminalization_intent`，随后提交不可变 Run 终态、在生命周期锁外执行 provider/local effect、重新校验 owner 后写 receipt 并释放 Run ownership，再按 `JARVIS_TASK_WORKSPACE_CLEANUP_DELAY_MINUTES` 原子安排 Workspace 清理。Cancel 同样在任何进程信号前按当前 owner/sequence 写入 intent，且该中间状态保留 PID 和 Run pointer；cancellation intent 一旦提交即拥有 Task 终态仲裁权，晚到 completion 不得覆盖。无 Run owner 却仍有 PID/PGID 的状态必须 fail closed，不发信号、不清目录也不清进程证据。恢复器必须先停止或固定旧 Run，不能把仍可能运行的进程当作可清理 Task。Run 或最终 Task state 写失败时仍保留 `finalizing` intent；启动及每 5 秒运行的恢复器先收敛已死亡进程留下的 Run owner，再按 intent、当前 Run evidence 和 `workspaces[]` 幂等重放，不扫描 Workspace，也不把删除 Workspace 当成终态写入的前置条件。已有新 Run 时，旧 Run 只保留自己的终态 Artifact 和 delivery evidence，不改写当前 Task projection 或 state。

Provider effect 调用前，TaskService 还必须在同一 `terminalization_intent` 中持久化 `effect_started_at`。恢复时已有 typed effect receipt 就只提交剩余 Task patch；已有 `effect_started_at` 却没有 receipt 则表示外部结果不可证明，只能追加 `unknown` receipt 并转 `needs-attention`，不得自动重发非幂等 provider mutation。

### 磁盘准入与自动恢复

`JARVIS_TASK_STORE_MIN_FREE_GB` 定义启动新工作前必须保留的磁盘余量，默认 10 GB，只有显式 `0` 才禁用；空值或畸形的 Run 环境不会把保护静默关闭，服务与 scheduled job 的非法显式配置会直接拒绝启动。TaskService 先原子登记 Task identity、canonical subject 和完整的 1:N `workspaces[]`，再检查 Task Artifact 所在卷和每一项已登记 Workspace 路径；准入通过前不创建 Run、不 mkdir/clone Workspace，也不启动进程。Runner 在进程启动前再次检查这些卷，覆盖准入与 spawn 之间以及多个独立卷之间的容量变化。

`repo-cache` 是 box-owned 的 bare mirror。缓存刷新使用 exclusive lease，cache clone 全程持有 shared lease，避免另一个 Task 在 Git 读取 object 时改写同一 mirror。缓存刷新成功且 cache 与 Workspace 位于同一文件系统时，显式 branch/ref Workspace 通过 Git local clone 复用不可变 object 的硬链接，随后立即把 `origin` 恢复为权威远端；Workspace 不写 `objects/info/alternates`，所以 cache 删除或重建不会让已有 Workspace 失效。显式 branch/ref 的本地硬链接 clone 在缓存刷新失败、本地 clone 不可用、lease 获取失败或跨文件系统时退回权威远端 clone。默认分支单分支 Workspace 也使用 repo-cache，但通过非 local 的单分支 clone 从 mirror 读取对象，避免暴露 mirror 中其他分支的 refs 或 object；跨文件系统不影响这条非 local cache clone，只有缓存刷新、lease、cache clone 或 origin 绑定失败时才退回权威远端。这里共享的是 Git object 的物理块，不共享工作树、构建产物或可变运行数据；单独对一个 Workspace 执行 `du` 仍可能显示这些硬链接的完整逻辑大小。

Active Run 中通过 `workspace create` 创建且未显式提供 `--base-branch` 或 checkout ref 的仓库具有更窄的历史边界：jarvis-box 由 remote symbolic `HEAD` 选择默认分支，随后在 repo-cache 可用时从刷新后的 bare mirror 做非浅的 `--single-branch --no-local --no-tags` clone，并把 Workspace `origin` 恢复为权威 remote。cache 不可用时才直接从权威 remote 做相同边界的 clone。该路径不把 tag ref、其他分支 ref 或其他分支独有 object 暴露给 Workspace。需要显式 branch/ref 的 Provider 路径继续使用其已声明的 checkout 合同和 repo cache；两类路径不能互相降级。

Workspace clone 和 Jarvis 执行的 checkout 默认设置 `GIT_LFS_SKIP_SMUDGE=1`，只检出 LFS pointer，不在 Task 启动路径自动下载图片、视频或其他 LFS 内容。这避免 cached clone 因 bare mirror 不是 LFS endpoint 而被误判失败，也避免与任务无关的 LFS 内容同时占用 `.git/lfs` 和工作树两份空间。确实需要二进制内容的任务应在已绑定权威 `origin` 的 Workspace 中用 `git lfs pull --include=<path>` 按路径 materialize；Operator 可以显式覆盖该环境变量恢复 Git LFS 的标准全量 checkout。Status 的 clone 进度会显示 `LFS 按需下载`，使该策略对操作者可见。

Start 的已登记 Workspace 因 `low-disk`、`ENOSPC`、`EDQUOT`、暂时不可取得的 Git ref 或其他物化错误而尚未就绪时，Task 保持 `status=accepted`，没有 `current_run_id`；最小 `pending_launch` 记录使用 `wait_reason=workspace-materialization-wait` 和下次重试时间，入口 receipt 单独返回 `waiting=true`。`waiting` / `storage-wait` 不是 Task status。服务启动时及此后每 5 秒只扫描带当前版本合法 `pending_launch` 的 canonical Task state；恢复器重新调用原 lane launcher，由 TaskService 再次物化并用现有 owner/sequence CAS 创建第一个 Run。并发恢复最多一个调用取得 Run owner，服务重启不丢失等待义务，也不需要 Redis、全局 FIFO queue、Workspace 目录发现或进程内 callback。只有全新空状态或当前版本显式写出的 admission scaffold 可以取得首次 Task registration；没有 pending claim 的历史 `accepted` 状态不会被猜测为待执行工作。已发布旧格式的 `admission_pending=true` 与匹配 Start receipt 属于待执行工作，必须验证原始入口后转换；首次 Start 的兼容读取覆盖 review、IM、命令、自定义任务、issue/workflow、followup、自改进与已受理的定时任务。恢复保留原 Task、原指令和入口数据，仍经过原 launcher 与 TaskService；已退役定时名称只允许恢复已有受理义务，不恢复新触发入口。重复任务依赖与磁盘等待分别保留，磁盘恢复不能绕过尚未完成的旧 Task。旧 IM 附件复制到新 Run，过期回复凭据保留原到期与接收目标语义，由连接器检查主动消息能力。workflow 保留原输入 schema 和 action grants。Delivery Metrics 恢复遵守禁用设置，已有精确历史结果时不启动分析，普通刷新识别原随机 ID 的已迁移 Task，完成结果由同一缓存 owner 保存。缺少原始输入、归属冲突或不能唯一关联输入的旧 Continue receipt 保留原文件并使升级失败，不能清空 intent、选择最新 staging 目录或把 Continue 改成 Start。转换成功时消费已知旧准入标记；mixed-format 记录有旧 pending claim 却没有 canonical pending owner 时拒绝写入。无法持久化 Task registration 的硬 ENOSPC 不能伪装成已接收，必须向入口返回错误。

Task-store 的一次 `ENOSPC`、权限或原子写失败是当前 persistence fault，不是只能随进程重启清除的配置状态。服务每次启动都先对实际台账根目录执行同一条真实写探测；探测失败仍提供只读诊断，并将当前故障交给既有准入和周期恢复处理，不得把新进程尚无锁存快照当成写能力已经恢复。健康检查、Run 准入和周期 terminalization recovery 都走和正式状态写入相同的文件锁及 crash-durable 原子替换路径执行 create/write/file-fsync/rename/directory-fsync/delete 探测；探针若不完成文件和目录同步，不得解除 latch。同一时刻的并发检查合并为一次探测，探测本身失败不会覆盖原始业务写入的故障证据，成功也只解除它开始时观察到的错误 generation，期间出现的更新错误不能被旧探测误清除。终态重放不是请求路径上的进程内重试：每个待终态 Task 只留一份 durable intent，由一个周期扫描协程按固定节拍重放，每轮至多一次；除启动核验外，运行期真实写探测只在 latch 存在时进行，次数只随扫描节拍增长、不随 Task 数增长，所以磁盘故障期间不会出现探测惊群。`JARVIS_TASK_STORE_MIN_FREE_GB` 只约束新 Run/clone 准入；终态恢复以实际可写为提交条件，不要求磁盘先回到新工作余量，也不提前删除当前 Task 的 Workspace。当前 fault 解除后，新 Run 或 finalization 清除 Task 的 `task_store_degraded` 并记录恢复时间；workspace 卷恢复后同样清除 `workspace_storage_degraded`。最后一次错误和恢复时间继续作为历史诊断信息保留，但不得继续阻塞调度。

准入检查与运行期写入属于两道不同的保护。agent 启动后，Runner 的 `run-trace.jsonl`、result、`reply.md` 或其他关键 Run Artifact 的持久化失败都绑定到当前 Run；runtime-native AgentSession stream 不由 jarvis-box 写入或复制。即使进程 exit code 为 0，Jarvis-owned Artifact 写入失败也必须提交 `persistence-failed / needs-attention`，保留已登记 Workspace，不能伪装成 completed。Artifact 已持久化之后发生的 provider delivery failure 不属于 Run persistence failure：Run 保持 `succeeded`，外部结果只追加到该 exact Run 的 typed effect receipt（`succeeded|failed|unknown`）。definite failed/retryable delivery 使 Task 投影为 `needs-attention`，Continue(writeback) 先写 `effect_retry_intent` 和新的 effect-start，再重试同一 Run 的 delivery effect，不创建 Run；`unknown` 不能自动重发。其他 completion callback、Task 终态提交失败不产生第二个 blocker 名，也不把 Task 升级成人工待办：终态提交携带的 durable `TerminalizationIntent` 原样保留，由周期 terminalization recovery 无条件幂等重放同一 intent，重放成功前 Task 保持 `finalizing`（投影 `blocker_kind=finalization-pending`，owner 是 machine），重放失败只以 `taskservice_completion_error` 与 `taskservice_recovery_failed` 状态事件暴露给运维。最终事件和通知只在 provider effect 及 Task 终态提交之后触发。准入检查通过后，创建 `runs/`、创建具体 Run 目录或 Workspace clone/create 直接返回 `ENOSPC` / `EDQUOT`，都必须回到同一 `storage-wait` 准入状态；已经取得 owner 的未启动 Run 先终态化为 failed，再释放 owner。TaskService 完成这次转换后必须向所有 lane 返回 Waiting，provider/lane wrapper 不得把 canonical `storage-wait` 重写为 `launch-failed`。错误只登记在对应 Task 的存储证据中，不得误锁无关 Task。周期恢复重新检查实时容量，并在成功取得新 Run 后清除等待错误、记录 recovery。

文件锁不可用时不得退化成只有进程内 mutex 的写入。锁创建、`flock`、状态写入或 rename 任一步失败都必须让本次 mutation fail closed 并登记新的 persistence fault。低磁盘准入只阻止会继续放大写入的新 Workspace/Run；已终态 Task 的登记式自动清理和 Status 手工删除仍是释放空间的通道，不受进程内 persistence fault 阻断，释放后由真实写探测解除 fault。不得通过扫描目录、猜测归属或删除 active/needs-attention Task 来应急回收；Workspace 由登记驱动的终态清理负责，terminal Task Artifact 由 retention clean 负责。

## Prompt Artifact

`prompt.txt` 只保存当前 Run 的输入：

- Start Run：首次用户消息。
- Continue Run：新的用户消息。
- Task recovery Run：运维恢复提示。

`prompt.txt` 不包含历史用户/助手消息、native session 内容、resume handle value 或 cross-agent source ref。

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
- 如果 status list、summary 或 work-items 需要在请求路径中全量扫描 `runs_dir` 才能返回，视为实现偏离契约。

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

`JARVIS_DEPENDENCY_CACHE_ROOT` 保存跨 Task 复用的包管理器缓存，默认是 `${JARVIS_RUNTIME_ROOT}/dependency-cache`，Docker 为独立持久卷 `/var/cache/jarvis-box`。它不属于 `workspaces[]`，workspace cleanup 和 Task retention 都不得删除它。Jarvis Box 只注入标准缓存环境；如配置 `JARVIS_WORKSPACE_DEPENDENCY_CONFIGURER`，则在 lane 完成 checkout 后、Agent 启动前调用 Operator 提供的程序。该 hook 可配置依赖工具，也可写 workspace-local Git identity 等仓库本地策略；失败必须让 Run 启动失败，不能带着半配置 workspace 继续执行；hook 内容仍由客户 Runtime Foundation 负责。

缓存根目录只承载各工具的原生下载缓存、内容寻址缓存和工具自身支持的共享安装目录。服务启动时预先创建管理根内的 vcpkg 默认二进制缓存目录，已有目录及权限保持；该目录仍属于持久依赖缓存，不随 Task Workspace 清理。它与 `repo-cache` 在 Workspace 准备流水线中协同，但不混用生命周期或目录：repo cache 复用 Git object，dependency cache 复用包管理器依赖，LFS 内容默认按需 materialize。内置 policy 覆盖常见生态的标准缓存入口：XDG cache、Go module/build cache，npm/Yarn/pnpm/Corepack/Bun/Deno，Playwright/Puppeteer/Cypress 浏览器缓存，Turbo/Nx task cache，Python 包管理器、pre-commit、Ruff、mypy 和 pycache，Gradle/Maven/Coursier，Cargo 和 Rust 编译缓存，C/C++ 的 ccache/sccache、Conan、vcpkg，以及 NuGet、Composer、Bundler。`CARGO_INCREMENTAL=0` 是默认 Agent policy，用于压低短生命周期 Workspace 的 Rust incremental build 状态；若运行环境可找到 `sccache`，Jarvis 把 `RUSTC_WRAPPER` 设置为解析后的 sccache 可执行文件路径，否则不设置 wrapper，避免 Cargo 在缺少工具时失败；初始注册集合中只有一个 Cargo Workspace 时，Jarvis 会通过 `CARGO_BUILD_BUILD_DIR` 把 `debug/deps`、`debug/build` 等中间构建目录放到按 repo identity 隔离的共享 cache，但不改变 `CARGO_TARGET_DIR`。Jarvis 不支持在 active Run 动态注册第二个 Cargo Workspace 后刷新当前 Agent 环境，也不会自动清除该变量。配置了可执行 agent browser 时，Jarvis 还向 Agent 暴露 `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH` 与 `PUPPETEER_EXECUTABLE_PATH`；这是显式 executable handoff，不会把 Playwright 和 Puppeteer 的 revision cache 合并成一个目录。

Bundler 是共享安装目录的明确例外：`BUNDLE_USER_CACHE` 保存用户级索引与下载缓存，`BUNDLE_PATH` 保存可跨 Workspace 复用的已安装 gems；Ruby ABI 与 native extension 平台隔离沿用 Bundler 自己的目录结构。通用 Workspace 准备接口负责调用各工具 policy；生命周期调用方不识别语言或包管理器。Jarvis 仅为本次 Run 准备时登记集合中实际使用 Yarn 的 Workspace 生成 `.jarvis-yarnrc.yml`，并通过 `.git/info/exclude` 隐藏该文件；能严格确认 Yarn 3+ 时加入 `hardlinks-global`，其他 Yarn 版本保留自身兼容行为，非 Yarn Workspace 不写入该文件，零/非 Yarn 集合不创建空归属收据或导出专用 rc 文件名。自动策略写入前检查全部 Yarn Workspace；遇到 Workspace 自有的同名文件，本次不改任何配置并跳过整个 Task 的自动 rc 策略。既有 schema 1 归属收据保持可读，合法空集合不构成文件归属；收据损坏、token 不符或已登记持有的文件归属冲突仍拒绝启动。严格确认支持基于 vendored release 文件名：`.yarnrc.yml` 顶层 `yarnPath` 在 Workspace 内存在且文件名符合 `yarn-<版本>.cjs` 约定、版本 major ≥ 3，并与 `packageManager` 声明交叉验证；`yarnPath` 为 `${ENV}` 插值、URL、非字符串或文件缺失时无法证明，保持不注入。Jarvis 不支持在 active Run 新增不同 Yarn major 后刷新 Workspace-local policy；当前 Agent 不会自动获得新设置，Operator 显式环境仍优先。文件系统支持跨目录硬链接时，Yarn 可以让各 Workspace 的 `node_modules` 复用 global content store 的物理文件。单独对一个 Workspace 执行 `du` 仍可能显示这些硬链接的完整逻辑大小，不能把该数值直接与 cache 目录相加当作物理占用。跨项目共享整个 `target/`、`node_modules`、`build/`、`.next/`、`dist/` 等编译结果不属于默认模型；Cargo 只共享中间 build-dir，最终 binary 和脚本常用的 `target/` 顶层输出仍留在 Workspace。需要项目级 build cache 时，应使用工具自带内容寻址缓存，或由 workspace configurer 按 OS、架构、工具链和项目建立隔离键。缓存属于单个 Jarvis 安装的信任边界，不跨客户共享，清理由独立运维策略负责。

`JARVIS_WORKSPACE_ROOT` 保存 Task Workspace。一个 Task 可以拥有零个到多个 Workspace；唯一归属记录是 append-only 的 `task-state.workspaces[]`。每项包含稳定的 Task-local id、服务端分配的绝对路径、可选 repository metadata 和 `primary` 标记。路径由 `task_id + task_instance_id + workspace_id` 共同派生；同一个 task id 被重新创建后也不会复用旧实例目录。非空集合恰好有一个 `primary=true`，只负责选择 Run 的默认 `cwd`；空集合不合成目录，Run 使用 launcher 的普通工作目录。

初始 Workspace 必须和 Run ownership claim 在同一次 crash-durable Task state mutation 中登记；active Run 中的 zero-workspace Task 必须通过 `jarvis-box workspace create --id primary` 建立第一个 canonical Workspace，非空 registry 后续增加仓库时使用普通 stable id。Runner 在所有 agent lane 的启动和 resume prompt 中注入这条 ownership contract，明确禁止 agent 绕过该命令创建、替换或物化 `JARVIS_WORKSPACE_ROOT` 的任何直接子项；已登记 Workspace 内部的正常文件操作不受影响。两条登记写路径都先验证 repository source 可解析，再提交 `workspaces[]`，随后在 Task 生命周期锁内重新验证 Run ownership、检查 Task store 和全部已登记 Workspace 所在卷，最后才创建、clone 或 checkout 目录。`--project` 依赖已配置的 `GITLAB_HOST`；GitHub 等其他远端使用显式 `--remote`。验证失败发生在 registry mutation 和目录创建之前；声明 repository 的成功 Workspace 必须是真实 Git worktree，只有 project/remote 都为空时才允许空目录。jarvis-box 不通过独立 reclaimer 扫描或清理 Task Workspace。已有 repository 目录必须包含真实 `.git` 目录或 worktree 文件；登记的 id、path、project、remote 和 primary 保持稳定。目录从未创建成功或已按登记清理时，Continue 可以由同一个 Workspace owner 重新分配路径；`base_branch` 只是目录准备输入。`cwd`、`workdir`、Run context、Artifact、marker 文件和目录扫描都不是 Workspace 归属来源。

一个 Task 的全部已登记 Workspace 跨多个 Run 存续。每个 managed Run 从启动到其进程组退出都持有同一把 Task 级 shared Workspace lease；清理前必须证明没有 Run owner、没有存活的已登记进程身份、没有 terminalization intent，取得对应的 exclusive Task lease，再逐项取得 exclusive Workspace lease。手工与定时清理共享这组准入条件。Run 结束/取消时先按 Task+Run 环境标记和稳定进程 identity 清理受管后代进程；脱离 managed 进程组的进程再由 `cwd` 和 open-file reference 扫描兜底，无法确认安全时保留目录并进入可见的延迟清理。外部资源只来自 Task 显式登记的 typed `external_resources[]`；文件名、目录名、repository 名和 Docker working-directory scan 都不能创建资源所有权。详细状态机见 [Task external resource lifecycle](task-external-resource-lifecycle.md)。Run 释放 `current_run_id` 时，Task state 原子写入 `workspace_cleanup_due_at = now + JARVIS_TASK_WORKSPACE_CLEANUP_DELAY_MINUTES`；Continue claim 新 Run 时清除该截止时间。任何 Workspace disposal 失败都持久化并退避重试。删除已开始但回执未落盘的登记项在恢复扫描中继续同一 intent；接续前重新取得 Task/path lease、校验登记归属和进程占用，幂等清理剩余目录（含 .deleting）后写回执，不因缺少清理截止时间而永久遗留。全量清理成功后写入 `workspace_disposal_completed=true`；`tasks clean` 只消费这个凭证，不重新解释 Workspace 或外部资源。

Cancel、provider 明确发出的 Issue close 或 MR close/merge，以及经验证的 GitLab/GitHub subject-not-found writeback 都是立即清理边界。Subject-not-found 需要最终评论返回 HTTP 404，并由同一 provider 身份证明目标项目或仓库仍可访问；项目/仓库不可访问、鉴权失败和配置错误保持普通 writeback failure。立即清理先解决 active Run 与同 Run 后代进程 ownership，再按同一份 `workspaces[]` 和 typed `external_resources[]` 尝试清理，不等待配置的保留窗口。Subject-not-found 清理失败或延迟时，Task 保留 completion `terminalization_intent` 并保持 `finalizing`；恢复器完成清理后再原子提交 `cancelled`，成功 Run 不改写为失败，`task_cancelled` 只发布一次。普通 Run 结束与 workspace 删除彼此独立；Run 终态落盘、provider writeback 或其恢复不得以提前删除 workspace 作为前置条件。

Task 首次 claim 还会由 `taskstore.Store` 在全局登记锁内分配递增的 `task_registration_sequence`，生成随机不可变 `task_instance_id`，并把外部工作对象规范化为不可改绑的 `task-state.subject`（`provider`、`kind`、`project`、`number`）；这些字段和 `workspaces[]` 在同一次 state mutation 中先于目录创建落盘。`.task-registry.json` 及 `.task-registry.lock` 只属于这个 Store，不存在独立 registry 包或 adapter writer。Provider webhook 的明确终态会按该登记精确匹配事件首次处理时已经存在的 Task：GitLab issue `close`、MR `close/merge`，GitHub issue `closed`、pull request `closed`（按 `merged` 归一为 `close/merge`），以及 Jira issue 状态进入 Done category 或被删除。匹配到的非终态 Task 统一经 `TaskService.CancelTask` 终止并清理全部已登记 Workspace；已经 completed/cancelled 的 Task 保持原终态，只重试登记目录清理。

Provider adapter 只负责把 webhook 归一成 subject terminal event，TaskService 不含 lane/provider 清理分支。首次处理一个 provider delivery 时，adapter 与 Task 创建共享全局登记锁：先把当前登记序号写成 durable `task_registration_cutoff`（status=`planning`），再扫描 cutoff 以内、subject 精确匹配的 Task，最后把每项 `{task_dir, task_instance_id, task_registration_sequence}` 写成 receipt 快照后才调用 TaskService。即使进程在 cutoff 落盘后、扫描前退出，retry 仍按同一 cutoff 重新计划；部分失败只重放 receipt 快照。同一路径后来被其他 Task 实例复用时，instance/sequence 校验会拒绝副作用。receipt 写入失败、损坏或身份不匹配时必须 fail closed。`issue_or_mr` 仍用于展示原 URL，但不参与终态归属判断；Artifact、branch、workspace 路径和目录扫描也都不是 subject 或 workspace 的归属来源。

清理目录不删除 `workspaces[]` 登记，因此 Status detail 仍能展示该 Task 的全部路径和存在状态。登记目录已经不存在时，手工删除仍是合法的幂等操作并返回 `already_absent`。`tasks clean` 只处理 terminal Task/Run Artifact；Task Workspace 的自动和手工清理由登记表和持久化截止时间驱动，不通过目录扫描或 orphan discovery 推断归属。

## Clean

`tasks clean --older-than <days>` 删除的是 `runs_dir` 下超过保留期的 cleanable terminal `task_dir`。

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
- active/running、needs-attention 或 `recovery-required` Task

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
