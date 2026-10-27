# 执行模型

本文是 jarvis-box 对象模型、状态机、事务、投影和业务指标的唯一规范性契约。实现代码必须以本文件为准；[architecture.md](architecture.md) 只能说明模块、依赖和部署边界，不得重新定义本文件拥有的身份、状态、操作、事实源、事务顺序、投影、指标或可用性语义。

## 全链路主干

本节是 Task/Run 全链路的唯一主干契约。后文的 Provider、Workspace、Continue、Completion 和 Status 章节只能细化它，不能建立第二套归属、状态或操作规则。

jarvis-box 只有一条业务主线：

```text
Provider / IM / CLI / Status / Scheduler 意图
  -> 入口 Adapter 认证、规范化和去重
  -> 不可变 Target identity + Task command
  -> Work Module 加载一个 strict Task aggregate
  -> 在同一 Task lifecycle lock 下决策和提交事务
  -> Run / AgentConversation / Workspace / external effect Adapter
  -> exact Run completion / provider receipt / cleanup receipt
  -> 同一 aggregate 收敛 Task 终态
  -> 一次 TaskView 投影
  -> Status / CLI / work item / diagnostics / SSE 共享这一读模型
```

Provider lane、ChatBridge、MR/PR review、follow-up、Delivery Metrics 和定时任务都是入口、执行或写回 Adapter，不是独立状态机。Status、work item、系统设置和浏览器也只是投影消费者，不能重新解释 Task 是否正在运行、是否需要人工、哪个 Run 属于当前操作。

### 稳定不变量索引

下表是代码、场景矩阵、测试和 review 引用业务语义的唯一稳定 ID 索引。ID 的含义只能在本文件修改；下游文档和测试只能引用、细化或证明，不能重新解释。新增逻辑若无法归入已有 ID，必须先在本表增加或修订不变量，再修改实现。

| 稳定 ID | 规范性不变量 |
| --- | --- |
| `EM-CORE-001` | Provider、IM、CLI、Status、Scheduler、Runner、recovery 和 cleanup 必须汇入同一组 strict aggregate、TaskService lifecycle owner 与 TaskView projector；Work Module 是收口这些 owner 的稳定 seam，不得维护平行状态机。 |
| `EM-TARGET-001` | Target identity 在 Task 创建时持久化并包含 provider authority；部署配置、路径和后来产生的 Artifact 都不能补写或改写历史 Target。历史 upcast 仅限两份版本化合同：pre-authority Task 已持久化的 subject 与同一 Task root 的 canonical URL 在 provider/kind/project/number 全等时，由 URL 只读补 authority，不改盘；已登记的 0.2 IM Task 缺少 Target 时，可按下文的原始首 Run context 合同首次恢复 Target，只有 TaskService 事务可发布。不得从后续 Run、未验证 Artifact、部署配置或路径猜测 Target；已存在 Target 不覆盖，任一冲突即 fail closed。 |
| `EM-TASK-001` | `task_instance_id` 与结构 Task ref 唯一标识动作 owner；可重名 task id、Target 反查和裸 Run id 不是 Task identity。 |
| `EM-CMD-001` | Start 创建新 Task；Continue 作用于 focus Task 并按 strategy 决定是否创建新 Run；Cancel 只作用于 focus Task。所有 TaskService 执行请求都必须在入口显式携带闭集 operation=`start|continue`；`ResumeSessionID`、`ContinueStrategy`、prompt、Run/Task 当前状态都只是对应命令的载荷或 fence，绝不能反向推断 operation。空值、未知 operation，以及 Start 携带 Continue 专属的 resume handle，都必须在读取、恢复或修改 Task/Run、分配目录和启动进程前拒绝。Status 发出的 source Start 必须冻结完整 source Task registration、strict latest operational source Run 和显式 zero-current 预期，TaskService 在分配目标 Task registration、目录、admission WAL 或复制 Artifact 前于 source Task lifecycle lock 内复验；Status 发出的 Continue 必须冻结完整 Task registration、strict latest source Run（允许显式零 Run）和 strict current Run 预期（允许显式无 current Run）。该 expectation 只是展示事实；只有 owner planner 在同一 lifecycle lock 复验通过后才能签发 opaque `ContinueSourceFence` capability。seal 绑定完整 TaskRef、latest source、current expectation、operation=`continue`、strategy 与 lane；adapter 可以原样运输 opaque seal，但复制、删改或按新读到的 R2/Task ABA 字段重建 struct 都不能获得有效 capability。唯一的 strategy 重签发生在 TaskService 自己的 runtime router 于任何 effect 前把 unavailable source agent 的 `recover` 确定性改为 cross-agent `agent` 时：owner 必须先验证原 seal 与完整 aggregate snapshot，再只对同一 Task/Run/current expectation 重签 `agent`，并在最终 lifecycle lock 内重复全部校验；adapter、R2、Task ABA 或 lane 漂移均不能取得该能力。TaskService 在任何 Continue preflight、Stop、intent 或新 Run claim 前于同一 lifecycle lock 验证 seal 和全部绑定事实。若该 Continue 在 provider T2 prefetch 才发现 MR/PR 已 merged/closed，terminal Cancel 必须仍消费完整 T1 sealed `ContinueSourceFence`，不得从 Task directory 重读 registration/current 作为授权；TaskService 在任何 stop、cancel intent、terminal state 或 cleanup effect 前重验 seal/T1 registration/latest/current，allocation in progress 时只能等待后重验而不得 signal，R2（active 或 completed）和 Task ABA 一律无副作用拒绝。Status 的 Chat `retry-writeback` 同样先冻结完整 R1 `TaskRunFence`，再由 TaskService 在 lock 内封存 opaque retry plan；ChatBridge 只能运输该 plan，实际 IM effect 前再次由同一 owner 校验 R1 仍是 exact idle latest，R2/ABA 一律返回 typed stale conflict、零 provider 调用，绝不重新按 latest 选择 Run。任一 owner 已变化时原命令无副作用失败。GET/Catalog/Inspect 只读，后台发现器只能用稳定 evidence identity 和幂等 receipt 提交 typed Start Command，不能让页面刷新次数决定任务创建。 |
| `EM-AGG-001` | Advance、Catalog、Inspect 从同一 strict aggregate 和同一 revision 读取；事实缺失、损坏、歧义或 outcome unknown 时 fail closed。 |
| `EM-ADMISSION-001` | 零 Run 的唯一判据是 strict aggregate 的 `OperationalRuns=[]`；它本身只表示已受理但尚未获得执行世代，机器准入等待属于 processing，不得伪造 Run、Session、失败或人工待办。已持久化的 definite admission/launch failure 在 `OperationalRuns=[]` 时才是 Task 级 pre-Run 事实，TaskView 必须投影为 typed `admission-failed` / `admission-launch-failed` 与 inspection policy，绝不能伪称“最后一次 Run 失败”。一旦存在 R1..Rn，后继准入的 wait/failure 必须以 exact terminal latest Rn 和同 fence 的 typed receipt/WAL 进入 S 分支，保留全部 Run/Session history；不得显示 `No Run created`、不得把历史 Run 数清零、也不得借 Task-root phase 把 active Rn 当成 successor source。每个 provider/command/review/follow-up，以及 merged-change `self-skills-improve` Start，以稳定 provider evidence key 和显式 attempt identity 进入全局 admission ledger：同一 identity 只能有一个 durable intent、一次 effect-start 与一个 outcome receipt。这里的 `self-skills-improve` 是 MR/PR 合并事件触发的 provider lane，绝不是已退休的 scheduled identity `self-improve`。代码 review evidence 中的 commit SHA 是本次 review 的不可变 subject：T2 live prefetch 只允许更新 opened/merged/closed 等 reachability/state，禁止覆盖 admission 的 source branch、target branch 或 commit；Workspace preparer 必须提供 HEAD resolver 并精确 fetch/checkout admitted commit，resolver 缺失、HEAD 为空或不等于 admitted commit 都必须在 fingerprint/Agent 前 fail closed；Agent `review-summary.json.reviewed_commit_sha` 也必须非空且等于 exact Run 的 admitted commit，mismatch 不得进入 provider writeback、live/backfill Followup 或完成态 TaskView，而要投影为 `agent-output-invalid`。TaskService 必须在 completion、active poller 和 DeliveryRetry 的任何 provider effect-start 之前校验这份 exact-Run 本地事实，并把校验文件与实际 comment bytes append-once 冻结为同一 private publication snapshot；后续 provider writeback、live/backfill Followup、Task-root 最终 Artifact projection、Status TaskView 的 `result_summary` 与 result inspection 中的 review/comment 都只消费该快照，不能重新读取 Agent-owned mutable 文件。现代 exact Run 缺少快照时，这些消费者必须按“尚无可发布结果”fail closed；公开 meta/run-context 缺失或损坏、writeback disabled 或公开 summary 恰好仍是同 commit 都不能授权回退，只有不存在现代 Task/Run fence 的 legacy 只读记录保留原 Artifact 兼容投影。缺失、不一致或污染只能写 exact-Run publication-validation，禁止产生 `exact_run_effect_started` / `delivery_retry_effect_started` 或 delivered callback receipt；completion intent、guardian recovery 和 retry 必须持久化并重放同一 declarative publication contract。prompt、result、Followup projection 与 completion receipt 始终引用同一 commit。入口已知 canonical Target 时，Target 必须同 intent 一起持久化；accepted ledger 的 project、Issue/MR IID 与 source URL 只能由该 typed Target 写入，绝不能解析 evidence 文本或在 recovery/replay 时补造。旧的无 Target record 仍可读、可 replay 且不得另记 accepted。Launcher 必须在提交 TaskService 前携带完整的 typed admission 配置，Run claim 后才执行的 `PrepareRun` 不能补写或影响准入事实。 |
| `EM-RUN-001` | `{task id, task instance, task registration sequence, run id, run sequence}` 是 Run 存在、归属和顺序的完整 generation fence；latest/current 字段、mtime 和目录不能替代 registry。Operational registry 一旦存在更高正 sequence，较低 sequence 的 current pointer 就是单调性冲突，strict aggregate 必须 fail closed，不能把旧 current 当作 Artifact 或 mutation owner。 |
| `EM-HISTORICAL-RUN-001` | 已登记 Task 上早于完整 immutable `run_created` claim 的 Run，只能由 TaskService 在 service-maintenance write lock 和同一 Task lifecycle lock 下根据显式 approval manifest 制作 immutable historical-run registration certificate；certificate 固定完整 TaskRef、唯一有序历史 Run 对、Run-state/选定 legacy event/artifact 的 digest 与 frozen display snapshot。证书验证成功的 Run 仅属于 `HistoricalReadOnlyRuns`：可浏览已冻结的 Session/progress/artifact，永不成为 OperationalRun、latest/current、lifecycle、Start/Continue/Cancel、recovery、cleanup、writeback、resume 或 usage 的事实源。scan candidate、目录、Task/Run pointer、mtime、历史文本或 certificate 外的 Run 都不能自授此权限。 |
| `EM-ARTIFACT-001` | Session、log、result 和 delivery artifact 必须由 exact Run 的 ArtifactScope 读取。Task root 只允许已证明的 pre-generation root-only Task，或 marker 的 Task/Run/sequence/逐文件清单都匹配的 current-Run alias；禁止 latest、无 marker root 或 sibling Run 回退。零 Run admission 的 Task-root `run-context.json` 是不可变的准入证据：R1 claim 后任何 Run 都不得覆写它、把它发布为 latest-Run alias，或在本 Run context 缺失时继承它；每个 Run 只读写自己的 `runs/<run-id>/run-context.json`。Artifact 写入故障不得提前终止 live process，也不得改写已经提交的 Run 终态；必须保留实际进程退出事实。在 completion 提交前，必要的 Jarvis-owned Run 产物（包括 run-trace、result 和回复产物）无法可靠保存时，即使 OS exit code 为 0，也必须按持久化失败结算并保留 Workspace，不能发布成功。已提交终态后的读取或派生投影重建失败只改变该 exact Run 的 Artifact 可用性/诊断轴；只有必要 terminal receipt 本身无法取得时才进入独立的 unknown/deferred terminalization。 |
| `EM-LICENSE-001` | 发布构建必须接入授权客户端。TaskService 在 Start / 创建新 Run 的 Continue 入口和实际启动 Agent 前检查本机签名授权；入口拒绝不分配 Task/Run，准备期间失效则以当前 exact Run 的 preparation failure 与 launch failure 收口并保留拒绝原因。全部 lane、准入恢复和 failover 共用同一个启动检查。IM 准入拒绝通过原消息回复通道返回授权提示；未激活时告知联系管理员激活后使用，不以重新发送任务代替处理授权。授权变化不终止已有进程，Cancel、诊断、清理和仅写回的 Continue 不经过新 Run 授权门。开发构建可显式不接入授权；运行期配置不得关闭发布构建授权。 |
| `EM-PROCESS-001` | 进程所有权必须由 exact Run、process generation、pid/pgid、containment、guardian 和 exit receipt 共同证明；不确定时禁止启动、停止或清理。 |
| `EM-CONVERSATION-001` | AgentConversation 绑定 exact Run；resume handle 和 runtime-private session 值不得跨 Run、Task、Agent 或公开投影泄露。IM reply handle 的 destination 必须保存 provider transport 的 closed target vocabulary 和对应稳定 identity；`channel_type` 只描述会话形态，不能原样复制成 target kind。显式 provider target 必须保持不变；仅从 UVIM channel type 派生时使用协议闭集 `direct→user`、`group→group`、`thread|channel→channel`、`room|conversation→conversation`，未知值在持久化 handle 和 provider effect 前 fail closed。同一个 native session transcript 可以被多个 Run 续用，Reader 为读取范围附加的 Run 标签不是消息级 ownership：只有经过 exact Run 私有 trace/ArtifactScope 验证的消息才能凭 Run fence 越过 selected Run 的 start/end 时间窗；普通 native transcript 必须按该 Run 的持久起止窗口切分，不得把 R2 消息投影进 R1。 |
| `EM-WORKSPACE-001` | Workspace 和外部资源仅由 Task 的 typed registry 拥有；cwd、目录扫描、Compose 名称和进程环境不是 ownership 事实。 |
| `EM-WORKSPACE-002` | Workspace lease、prepare、retention、cleanup 和 recovery 使用同一登记事实，且与 Run delivery outcome 正交。 |
| `EM-EFFECT-001` | Run succeeded 只证明 Agent 执行成功；必需 delivery 只有 durable delivered/skipped receipt 才完成，failed/unknown 必须保留 typed blocker 和精确 action policy。provider/workflow effect 的权威 receipt 属于 exact Run 私有 Artifact；ChatBridge 的权威是同一 exact Run `.private/final-reply-receipt.json` 加完整 fence 的 `chat_reply_delivery`，二者必须引用同一 receipt/attempt identity 与 private receipt digest。Chat 的可解释失败也只能来自这组双侧匹配事实中的 closed safe fields（category、retryable、delivery state、attempts，以及可选 HTTP status、provider code、Retry-After、request id）；原始 error/body/log 与公开 `reply-error.json` 不能回填、覆盖或细化失败。provider/workflow 的 `failed` 只能由 server-private typed definite-no-effect error 产生；当前闭集 reason 是 `local-command-not-started`、`local-preflight-rejected`、`local-adapter-not-configured`，receipt 必须同时保存 `retryable=true`。`local-command-not-started` 只能由内置 CLI adapter 在明确的进程启动前失败（PATH lookup 的 `exec.ErrNotFound`，或显式命令的 `fork/exec` + `ENOENT`）构造；`local-preflight-rejected` 只能由 server executor 在完整 action-set preflight 尚未调用任何 action effect 时为 exact failed action 签发；`local-adapter-not-configured` 只能由 workflow.start executor 在调用 adapter 前的 nil guard 签发。三者都必须先固定完整 Task/Run/action/target identity 并通过同一 exact-Run `dispatching → failed` transaction；任一 identity、fence 或 receipt 写入失败都只能 outcome unknown。普通 `open/stat` 的 ENOENT、HTTP status、stderr、exit 文案、context/network 错误和公共审计都不能升级为 failed 或授权重发。只有该完整 exact receipt 可授权同一 identity 的 `failed → dispatching → acknowledged|failed|outcome-unknown` 重试转换；重试前写入 `dispatching` 后中断一律为 outcome unknown。外部 mutation 之前的本地发布校验是独立 effect class：只有 exact Run private `publication-validation.json` 中完整 Task/Run fence、artifact identity/digest 与 closed `agent-output-invalid` 才能授权“Continue 重生成”；Status 不得重新读取 `comment.md` 现场执行第二次校验，receipt 缺失、损坏或与当前 artifact 不一致只能 outcome unknown。Task state 中的 delivery map 只是该 transaction 的投影缓存：它在 private receipt 缺失时只能证明 pending/claimed/outcome unknown，绝不能单独证明 delivered/failed；private receipt 缺少 matching Task projection 也不能单独证明完成。Workflow effect class 由 exact Run 中通过校验的有效 action set 决定；issue-post-check 在外部回写开启时先补齐必需的结论评论动作，其余 customer workflow 不推测缺失动作：普通 workflow 的空集=`none`、仅 `provider.*`=`provider`、仅本地 action（如 `workflow.start`）=`workflow`、二者并存=`provider+workflow`；lane 名称、target、comment 文件或已 ACK 的单个 action 都不是分类权限。provider-writeback 的 executable-lane 前置条件只有闭合两态：三个 current scheduled lane 及 source-owned `custom-user-task` 是 `providerless`，普通可执行 lane 从 exact action set 得到 `provider-capable`。`maintenance` 与 `self-improve` 必须在进入这个分类器前以 typed retired-persisted error 拒绝并返回零 disposition；它们是迁移输入，不是第三种 effect 成员，也绝不能以布尔 `false` 伪装成 providerless。**例外只限 current scheduled taxonomy 的三个 lane：`memory-consolidation`、`daily-reflection`、`cognitive-evolution` 是 providerless `none`，不读取、不验证也不从残留的完整或半截 workflow Artifact 推断 action requirement；该 Run 不要求 workflow/provider receipt。`maintenance` 与 `self-improve` 已退休，不是 scheduled/effect class，绝不能借这个例外取得 `none`。** completion gate、Status、ActionPolicy、retry ACK 与 poller 必须消费同一个 action-set requirement；空集不要求 receipt，mixed 只有 combined view 满足才完成。所有脱离原同步 completion transaction 的 server callback——comment poller、completion notification、follow-up running/terminal status——在任何公共 audit、provider 调用或 acknowledged/unknown 终态 delivery receipt 之前，都必须向 TaskService 提交 `{TaskRef, RunRef, effect_kind, intent_id}`；允许先持久化同一 identity 的本地 `dispatching` intent，但它本身不授权 effect。TaskService 在 Task lifecycle lock 内重读 strict owner、校验该 effect kind 的 active/terminal 前置条件并持久化 `exact_run_effect_started`；失败或未配置 authorizer 一律零 effect。若 completion notification 的本地 preflight 已确定不会发生外部 effect（disabled、local prompt、recipient/messenger/report 缺失或本地 validation 拒绝），则不得伪造 `exact_run_effect_started`；它的公开 skip/validation 审计只能交给 TaskService 的 exact-Run local-artifact projector，在同一 Task lifecycle lock 内复验完整 Task/Run owner 并原子写入，失败或 stale callback 必须零审计。provider 调用在该 durable effect-start 提交后于 lifecycle lock 外执行；提交之后才发生的 owner 变化不追溯撤销已开始的 effect，但旧 callback 在 effect-start 前遇到 successor、cancel、Task ABA、foreign artifact 或 Run context 漂移必须 fail closed。无关 effect class 的缺失或损坏既不能阻断本 action set，也不能授权它。effect outcome unknown 只有在当前 Task lifecycle 已进入 completed/completion-finalization 且该 effect 是本 action set 必需步骤时才能成为 mutation blocker；active、accepted、admission-pending 或取消中的 Task 不得因未来尚未要求的 delivery receipt 缺失而禁用 Cancel/Continue/Start。ActionPolicy 只消费 TaskView projector 已封闭的 blocker，不得再次读取 receipt 建立第二套时序。`workflow-actions.json`、`comment-post-*.json`、`reply-action.txt`、`reply-response.json` 和 `reply-error.json` 都是由 receipt 派生的本 Run审计，WorkLedger 只是历史展示。它们都不是 Task lifecycle event，审计写失败不得授权重放或改写 Task 投影。 |
| `EM-LEGACY-LANE-001` | `maintenance` 与 `self-improve` 是 **pre-current taxonomy persisted identities**，不是 current scheduled lane、effect class 或新建授权，也不是三个 current lane 的 alias：两者不存在可证明的一一映射。executable-lane/provider-requirement classifier 必须在产生 effect disposition 前以 typed retired-persisted error 拒绝它们并返回零 disposition，而不是把它们加入 effect 闭集、返回 `providerless=false`，或继续从 action/artifact 推断成普通 lane。只有专用的 legacy projection/upcaster 可以读取它们：若严格 Run aggregate 可证明没有 current Run、每个已登记 Run 都 terminal（允许零 Run），且 Task 的历史终态明确为 `cancelled`，TaskView 固定投影 `lifecycle_stage=legacy-retained`、`blocker_kind=legacy-retained`、`status_group=historical`、`next_actor=none` 与只读 ActionPolicy，并保留原 lane、Run、Session 与 Artifact 范围；不读取/验证 workflow Artifact，也不要求或推断任何 provider/workflow effect。若 aggregate 不完整、存在 current/nonterminal Run，或有 pending terminalization，则固定投影 `lifecycle_stage=legacy-quarantined`、`blocker_kind=legacy-lane-migration-required`、`status_group=historical`、`next_actor=none`，禁用 Start/Continue/Cancel/recovery/writeback/cleanup，绝不猜测它应映射到哪一条 current lane。`historical` 是公共 Task 状态闭集中的非当前、非完成、非人工待办分区：不计入 current/attention/completed，不产生 Target owner 或系统操作 action。所有 mutation/effect owner 必须在最终 Task lifecycle lock 内，于 idempotent fast path、projection repair/materialization、WAL/receipt/Artifact、共享 ledger/registry 和外部 effect 之前判定该边界；实际 commit callback 必须重验，锁外 preflight 不能代替 owner 判定。Task state 缺失或损坏时只能先只读重建并分类，不能为了识别 lane 先写回 projection。21 个 `CommandKind` 与 10 个 `MaintenanceOperation` 是闭集测试清单；新增成员没有 retired-boundary disposition 和真实 owner proof 时门禁失败。该 bounded projection 不改写 live state、Task event 或历史 Artifact。真实旧数据中的同一个 `maintenance` 值曾同时承载定时维护、self-improvement、Issue post-check 和无 Run/无 prompt 的未知记录，因此 `migrate runtime` 不得按名称自动改写或把它们映射到三条 current lane；原始值只作为不可变审计事实保留。如未来需要恢复某条记录的可执行语义，必须由逐 Task approval manifest 固定完整 Task/Run identity、来源证据 digest、目标语义和回滚策略，生成 immutable migration receipt；不得以物理 rename、prompt/目录猜测或 runtime alias 代替迁移。 |
| `EM-TRANSACTION-001` | mutation 固定按 strict read/revision、durable intent/effect-start、effect、receipt、owner recheck、state commit 的顺序执行；首个已提交 terminal 决定获胜。异步 callback 或 poller 不能把启动时捕获的 path/map 当成后来执行 effect 的权限，必须在最后一个 provider-effect 边界通过 TaskService exact-run effect-start transaction 重新线性化 owner。不可逆或可能回调另一 owner 的 effect 必须在 lifecycle/cache/service lock 外执行；同步完成也必须经 typed handoff 延迟到外层锁释放后再投影，禁止持有 follow-up/cache lock 启动 Run 后让 completion callback 反向等待同一锁。 |
| `EM-RECOVERY-001` | recovery 只推进已持久化且 owner 可证明的 intent/receipt，不重新解释历史文本、不新造命令，也不盲重放结果未知的外部副作用。现代 recovery observation 必须以 `{task_id, task_instance_id, task_registration_sequence, run_id, sequence}`（Task 级零 Run 明确为 `run_id="", sequence=0`）fence exact owner；只有显式 pre-registry legacy zero-Run 才可缺少注册/Run identity。lost-Run pre-reap source 还必须同时证明 active exact Rn、完整 immutable process identity 且 `ValidateProcessIdentity` 的 closed outcome 为 `process-already-absent`、没有 exact result；`monitor_status`、`pid_running`、phase/status、current/latest/stopped pointer 或错误文本都不是授权。post-reap source 只认同一 exact Rn 的完整 `process_reaped` maintenance success receipt。receipt 由不可变 Task/Run/operation/effect identity 派生，`Reason`/`Error` 只是 payload；同一 receipt 不得因文案变化再次投影。root maintenance scan 只发现证据；每个候选必须先在其 Task lifecycle lock 内物化 WAL/repair，再以同一锁重新授权并只返回 sealed typed plan。server lost-Run 的 `RecoveryLaunchRequested` 必须返回 accepted、非 historical/effect-skipped typed receipt，才可把该 sealed `ServerLostRunRecoveryPlan` 放入 `CommandLaunchRun` transport；adapter 不得构造、删失或改写 plan。TaskService 在实际 Run claim 的同一 lifecycle lock 内验证 plan 私有 seal、Task registration、strict latest/current R1 与同一 requested receipt；任一 R2（active 或 completed）、Task ABA、缺 plan 或伪 plan 都在目录、Artifact、process 和 Rn+1 claim 之前 fail closed。admission recovery 的 sealed plan 是独立 owner，二者不可混用。adapter 不得取得 raw state 或在扫描外重新分类。 |
| `EM-PROJECTION-001` | 同一 TaskView revision 同时决定 lifecycle、status group、terminal outcome、supersession、is_processing、actions、diagnostics 和 consumer counts；真实 Handler 只选择一次 canonical action policy，并由它生成 `actions`、`safe_actions`、`primary_action`；消费者不得二次分类或用空配置重算动作。 |
| `EM-PROJECTION-002` | focus Task 是 actions、Task files、Workspace 和 cleanup owner；selected Run 只决定 Session、progress、log 和 result 的查看范围。 |
| `EM-DIAGNOSTIC-001` | 系统待处理数只统计同一 TaskView revision 中 `next_actor=operator` 且当前可执行的规范化 action；同一事实不得由 Verify、Diagnose 或 Reconcile 重复计数。 |
| `EM-METRIC-001` | 历史受理、已记录 Run、今日/昨日 Run、趋势、活动 Task、活动 work item 和存储 inventory 是不同指标；每项只读声明的 ledger/projection，并携带 availability 与 as_of。 |
| `EM-METRIC-002` | 单个 Run 的 runtime token usage 只有完整 `{task_id, task_instance_id, task_registration_sequence, task_dir, run_id, run_sequence, agent, agent_conversation_id}` 都匹配的 private typed final-cumulative adapter receipt 及其 usage digest 才能为 known；stdout/stderr、result JSON、全局 home session、mtime、目录存在和旧 Run receipt 都只能使其保持 unknown/partial。 |
| `EM-OPERATIONAL-001` | Doctor/内部轮询的运行状态只来自配置、OS/command exit 和带稳定 identity 的 typed receipt；log/detail/error、mtime、目录扫描及 workflow/comment 审计只能展示，不能反投影 success/no-op/failed/issue。Provider history CLI 必须用 documented HTTP response frame 产生 closed transport outcome；stderr、exit 文案和 response body 不能分类 auth、retry 或 capability。缺 receipt/frame 必须是 unknown，不能伪造成成功或失败。 |
| `EM-RUNTIME-001` | 只有 exact Run 的受信版本化原生终止事实，经 TaskService 接受并持久化后，才授权三类有界自动 Continue：Codex capacity、Codex usage limit、Claude＋DeepSeek context 超限。恢复预算、到期、认领和失效由同一 Task owner 决定；无全局 cooldown，不重新解释历史日志。助手/工具正文、stderr、中间错误后成功、其他失败及缺失/未知 receipt 均不授权自动执行。 |
| `EM-CI-001` | managed CI wait 必须先由 TaskService 从 immutable Task Target 与 exact Run fence 生成 sealed CI Target claim；claim 固定 provider authority、project、selector kind/value 和 canonical endpoint。CLI 参数、环境 host、pipeline URL 或 provider payload不能创建/改写 claim；每个 poll/result receipt 必须回显同一 claim，并验证 pipeline identity 属于该 authority/project，缺失、漂移或 unsupported Target 在发起 provider call 和写 Task 投影前 fail closed。 |
| `EM-DISPOSAL-001` | Workspace/外部资源处置是独立维度；清理失败或重试不得改写已提交的 Run/Task delivery outcome。 |
| `EM-SUPERSESSION-001` | 只有两端都携带完整 `{task_dir, task_id, task_instance_id, task_registration_sequence}` 的显式 lineage，且 successor 已满足完整成功条件时，历史 Task 才投影为 superseded；名称、裸 Task/Run ID、时间和同 Target 不足以推断。`effective_status`、`monitor_status=superseded`、summary/evidence 等字段只是单次 read-model overlay：strict aggregate 每轮先清除旧 overlay，再由本轮验证成功的 lineage 附加不可由持久化 JSON 伪造的 sealed supersession 结论，TaskView 只消费该结论。旧的 bare-id lineage 和残留 overlay 只保留审计，不参与投影。人工关联先把 selector 唯一解析成两端 TaskRef，再在同时持有两端 lifecycle lock 时复验 registration、subject 与 successor 完整成功 receipt；任一端被重建或 selector 歧义都 fail closed。 |
| `EM-WATCH-001` | SSE 只传 revision/invalidation；浏览器重读唯一快照，并以 `{catalog revision, UI generation, focus task_uid, selected run_ref, endpoint}` 丢弃迟到 response，同时保留输入、焦点、展开状态和显式 selected Run。System Operations 的完整 `overview` 是可建立 TaskView fence 的权威快照：若请求发出后浏览器尚未观察到更晚 SSE（同一 request/generation 仍有效），它返回的非空 revision 可以推进首次或已过期的本地 fence；不得拿旧 SSE revision 反复拒绝这个当前快照，最后又以 `loading=false` 落入无 overview 的伪稳定状态。反之，请求期间观察到新 SSE 时，旧 response 必须丢弃并以该新 fence 重读。Status 工作台和 System Operations 不得运行秒级或其他周期性页面刷新；没有新 revision、显式导航或人工刷新时，请求数与 DOM 必须保持稳定，编辑、焦点和操作按钮持续可用。后台 scheduler 的 candidate、blocked、waiting、failed、replayed 等发现/诊断计数不是 invalidation authority；只有本轮可证明已提交的 durable transition receipt，或在同一 state lock 中 before/after 不同的缓存 `state_changed`，才能发布 `background-task-state-changed`。同一 durable transition 的 lane telemetry 与 scheduler summary 不得各自触发 Task invalidation；summary receipt 是周期性恢复的唯一 publisher。 |
| `EM-PUBLIC-001` | Status/API 只返回 allowlist 安全字段；typed `workspace_locations[]` 是已登记 Workspace 路径的唯一例外，private handle 和任意主机路径禁止公开。 |
| `EM-ADAPTER-001` | Provider、IM、review/follow-up、workflow 和 scheduler 只负责认证、规范化、去重和 effect 运输；它们不得拥有 Task/Run 生命周期。 |
| `EM-DEPLOY-001` | Native、Docker、安装、升级和运行时配置不得引入第二套 identity、storage、lifecycle、scheduler owner 或事实源。版本迁移的唯一代码 owner 是目标 release 中已经完成 artifact digest 校验的新二进制，旧二进制不得预执行自己所知的 migration 冒充目标版本迁移。Native `update` 必须在停服前由当前安装器仅执行无 canonical runtime 写入的 target preparation：下载并校验完整目标 release、从受校验 archive 提取目标 `install.sh`；停服后只执行该目标安装器，禁止已安装旧脚本在替换 target artifact 后继续控制 migration/start。`0.x` 的 minor 线（例如 `0.2` 与 `0.3`）是独立兼容线，跨线与正式 major 升级相同，必须在任何下载或 service mutation 前取得显式 opt-in。Native 升级固定顺序为 cross-process install transaction lock -> strict active-work preflight -> **在任何 ensure-path、env reconcile、artifact/state 写入前** service stopped / exclusive maintenance window -> verified target artifact install -> canonical ownership -> 安装器以已验证 target artifact 和本次安装 attempt 签发短生命周期 migration grant -> 目标新二进制在最终 lock 内复验同一 grant attempt，写 durable migration intent -> 在 canonical runtime env/state 上执行幂等 migration -> durable matching receipt（每条 receipt 必须同时匹配当前 migration implementation identity；仅 intent=receipt 不足）-> grant 严格由 `issued` 推进到 target artifact/attempt/journal-bound `lease-pending`，再推进到 `lease-issued` startup lease（`lease-pending` 是唯一可恢复 crash 状态）-> service start 消费 lease 且持有全生命周期 runtime singleton lock -> health receipt。install transaction lock 必须按 physical host root 唯一且落在 host-stable、独立于 `TMPDIR`、不可由单次 installer 配置改写的固定位置，否则同一 runtime 会产生双 owner；打开该固定 path 必须 no-follow/exclusive-create，并在任何 truncate/write 前从已打开 fd 复验 regular file、当前 euid owner、单 hardlink 且 group/other 不可写，任一不满足都 fail closed。systemd 只有明确 inactive/failed 的已加载服务，或明确 `LoadState=not-found` 的首次安装，才是 stopped；launchd 在 `jarvis-box stop` 执行 `bootout` 后不保留 loaded-but-inactive 状态，因此只有同时包含 exact label 与 exact user domain 的 `launchctl` could-not-find-service（首次安装或已安装 runtime 被显式 bootout）才是 stopped。两种 service manager 的任意 command failure、空输出或 `unknown` 都不是 stopped 证据。`serve` 只验证并消费该 lease 与已闭合的 migration journal，绝不得自行执行 migration、签发 grant 或把旧 target 的 lease 当作新 target 授权；首次开发/未安装 runtime 只能经显式 development bootstrap 的 `migrate runtime` 取得同一类 lease，不能由直接 `serve` 隐式创建。首次安装、跨版本升级和重复安装必须走同一 owner。journal schema 是已发布的闭集，未发布 schema（包括 v1）必须 fail closed；任何 current inventory 之外的 intent 或 failed receipt 都是未闭合 migration，必须阻断 startup；已知且 implementation 全等的有效 intent 在进程崩溃后没有 receipt 时，只能由停服且持有当前安装授权的目标 migration owner 在同一 journal lock 下，追加保留原 attempt/binary identity 的 failed 记录，明确该次结果未经确认；再以递增的新 attempt 重入同一幂等 implementation。原 intent 和已发布数据必须保留，不猜测成功，不删改日志；恢复再次中断仍按相同规则重试。attempt 必须连续递增，前一 attempt 未闭合时不能出现下一 intent。Serve 和 lease issuer 只消费全部有匹配 succeeded receipt 的 inventory，不执行恢复。migration 失败、尚未恢复的 intent 无 receipt、implementation/target binary/version/digest/attempt/journal identity 不匹配、service-stopped 证据为 unknown 或 canonical path 不可写时，安装器不得启动新服务、恢复暂停 Task 或报告升级成功；重试只能继续同一 migration identity。taxonomy 替换必须在交付时明确选择带可证明映射及回滚策略的数据迁移，或明确的只读退休投影；不得用 runtime alias、effect 兼容或下一次升级可能补跑来代替迁移。 |

`EM-ADMISSION-001` 的 review T2 原始 provider payload 只能存在于 launcher 私有临时 staging，读取 opened/merged/closed 后即销毁；不得复制到 exact Run。prefetch 的返回合同只有归一化后的 `mr_state`，staging 中的任意 `RunContext`、provider identity、URL、Agent 命令或 Meta 都不是事实，禁止覆盖 sealed C1。exact Run 暴露给 Agent 的 `merge-request.json` 必须由 C1 admission 的 provider/object/project/IID/source branch/target branch/commit 合成，只允许叠加 T2 reachability state；`notes.json` 不得装入 T2 live comments。Prompt 必须禁止 Agent 用 glab/gh/provider API 重新读取或覆盖 identity、diff、branch、commit、notes，实际 review 只能消费已经精确 checkout 并复验 HEAD 的 admitted commit。这样 workspace、Agent 输入、review result、publication 与 Followup 始终是同一个 C1；只在 summary 中回填 `reviewed_commit_sha=C1` 不能修复被 C2 context 污染的 review。

`EM-TARGET-001` 要求 provider adapter 的兼容 kind 先归一化为 canonical Subject kind，再与 typed Subject 或 canonical URL 比较；例如 Jira `jira_issue` 只是历史 adapter 拼写，必须归一为 `issue`，Feishu 只有已知的 `feishu_work_item`/`work_item` 可归一为 `work_item`。兼容别名不得因为字符串不同把一个已有 authority/project/number 的合法 Target 变成 providerless，也不得把未知 kind 强制归到另一个 canonical Target。下游 workflow-input 必须继续使用已经归一化的 Subject kind；adapter Meta 的历史 object kind 只能作为缺失证据的兼容输入，不能反向覆盖 canonical Subject。

`EM-DEPLOY-001` 的 install transaction lock 必须先对 physical host root 的已打开稳定 inode 持有全局 flock，再以 `O_NOFOLLOW|O_EXCL` 打开并 flock runtime-keyed regular file；生产 host root 是 `/`，隔离测试使用各自显式 test root，不能把不同模拟主机误并成一个 owner。helper 在复验当前 euid owner、单 hardlink 和安全 mode 后，只能通过匿名 pipe 返回绑定 host-root/file `dev:ino` 的 grant，shell 不得再从可替换 pathname 读取 ready token。每个安装 phase 及首次 canonical state mutation 前都必须复验同一匿名 grant channel 仍打开；PID 只用于释放 helper，不能作为 owner/liveness 证据，因为 PID 可复用。这样即使同 euid 进程 unlink/replace lock pathname，同一 physical host root 上的第二个合规 installer 也仍被稳定 root inode 串行化，不能在另一 file inode 上形成并行 owner；helper 死亡、grant channel EOF、symlink、FIFO/device、foreign owner 或不安全 mode 均 fail closed。

`EM-LEGACY-LANE-001` 的只读退休投影只处置 Jarvis Box 内的 Task/Run 语义，不取得 host scheduler 的所有权。Runtime Foundation 必须在自己的升级事务中，以版本化 manifest、exact label/path、停用后缺席证明和 durable receipt 退役旧 `jarvis-maintenance` / `jarvis-self-improve` 调度入口；Jarvis Box 安装器不得按名称扫描或删除这些 Foundation 资源。即使 Foundation 迁移尚未完成，Jarvis Box 的 internal Start、recovery 与 effect 边界也必须拒绝 `maintenance` / `self-improve`，因此遗留 scheduler 调用不得创建新 Task、Run 或外部 effect。`local.runtime-sync` 及三条 current cognitive schedule 不属于 legacy lane retirement，任何实现都不得顺带处置。

`EM-DEPLOY-001` 的 startup lease 只在首次启动时消费一次，不能把这条规则解释成禁止正常 `stop -> start`、`restart` 或故障后的同制品重启。未消费 lease 必须在有效期内；已消费 lease 的 `consumed_at` 必须是原有效期内且不晚于当前时刻的合法时间。后续启动只读复验既有消费记录、同一 target version/commit/binary/inventory/env identity 及完整且未漂移的 migration journal，不刷新消费时间、不执行 migration、不签发新 grant/lease。首次消费的期限不是已安装服务的运行期限。并行 `serve` 由启动前取得、覆盖整个进程生命周期的同一 runtime singleton lock 拒绝；顺序重启不得以已消费为理由要求重装。制品、迁移实现、journal 或授权记录失效仍须拒绝启动并回到安装事务，不得绕过验证。

`EM-DEPLOY-001` 的 canonical ownership 只覆盖显式 Jarvis 目录和安装器创建的私有目录。显式 env 文件不授予安装器接管其已有外部父目录的权限；父目录 owner/mode 必须保持不变。外部目录由操作者保证服务用户具有原子替换配置所需的目录访问权限，安装器不能通过 chown/chmod 共享父目录来取得该能力。

### `EM-ADMISSION-001` 首个 R1 的 sealed admission

IM 因磁盘空间等待的任务在实际 Run 启动后，应在原渠道原会话收到“空间已恢复、原任务已开始执行、无需重发”的进度通知，然后再交付最终结果。通知只在 Run 的进程与 running 事实已提交后触发，等待中取消或仍未启动时不发；后台重复检查及等待期间的服务重启不重复发。通知复用原会话的回复能力与主动发送策略，等待回执已消费或过期的凭据不得当作新凭据重用。该进度通知有发送截止，失败记诊断，不改变任务执行或最终结果交付的结算；发送期间进程退出造成的未知结果不得盲目补发。

`M10 Start` 的 registered zero-Run Task 不是可 replay 的 Run，也不是任何
Adapter 可从 Task root 自行启动的授权。它只能由 TaskService 在受理事务中产生
一次 opaque `InitialRunAdmissionReceipt`，并由 Adapter 原样运输到
`CommandLaunchRun`；TaskService 在分配目录之前、以及实际 claim R1 的同一
lifecycle lock 内，分别重验该 receipt。server context 只是 transport，不能构造
seal 或把 Task directory 变成 receipt。

zero-Run admission 也绝不拥有进程：`pid`、`pgid`、`process_run_id`、process
generation、containment、capture-pending 或 `reaping_failed` 任一仍存在，都表示
Task/Run 投影损坏或上一代处置未闭合。所有 admission projection 必须在同一
lifecycle transaction 中 fail closed，不能通过清空其中两三个字段把损坏状态改写成
合法 Z2。

v0.2.32 已发布 writer 可能在 immutable Task registration 提交前留下 definite
zero-Run 失败记录。只有同时满足以下 released shape 的记录可由 Catalog
保留为 `lifecycle_stage=pre-registration-retained` 的只读历史行：目录 basename、`task_id`
与 legacy `run_id` 三者完全相等；不存在 `task_instance_id`、
`task_registration_sequence`、current/latest Run 或正 `latest_run_sequence`；状态已是
`needs-attention|completed|cancelled`；且存在合法 `accepted_at`。该投影固定
`status_group=historical`、`lifecycle_stage=pre-registration-retained`、无
`lookup_id`、无 Run/Workspace/effect owner、无任何 mutation action，也不改写原文件；
raw subject 只能成为无 authority 的 `legacy_isolated` 展示信息。`Load` 和所有 lifecycle
入口仍须以 pre-registration 拒绝它，Run/artifact 子树也不能补造 registration。任何不完整
或超出这组 closed shape 的记录均不得借此兼容投影取得 Task/Run owner。
这组历史记录还必须没有 `workspaces` 成员或 `workspace_path` 占用声明。定时任务去重、工作区登记冲突检查和处置授权使用同一 strict 读取边界：经过上述校验的零资源历史不阻塞其他 Task，且不被补登记或改写；有资源声明、Run/process 声明或损坏 identity 的记录仍须拒绝授权。

普通 lane launcher 不构成 source Start capability。Status 只有在 adapter 实现
typed `SourceStartLauncher`、能够显式接收并原样运输上述
`InitialRunAdmissionReceipt` 时才可展示/执行 source Start；当前只有
`jarvis-command` 与 `post-check` 具备该能力。其他 lane 必须在创建目标 Task、写
accepted ledger 或分配 R1 之前返回 `unsupported-lane`。以后新增支持必须先实现
sealed source descriptor 到 exact R1 的 typed consumer，再接入 capability resolver；
仅仅配置普通 Start/recovery launcher 不得使 ActionPolicy 放行。历史空 lane 的
唯一规范化结果是 `jarvis-command`，因此 capability resolver、目标 Task 持久化和
R1 launcher 必须全部选择 Jarvis typed consumer，不能因 Issue launcher 也存在而
把同一 source command 投影到 post-check。

首个 R1 只有两种 producer，二者共用该 capability 和同一 fail-closed gate：

- 直接 prompt Start：receipt 绑定 immutable TaskRef、完整四个 Task-root ingress
  artifact（`prompt.txt`、`payload.json`、`meta.json`、`run-context.json`）的 regular-file/
  no-symlink 读取和 exact digest，以及这些 artifact 中的完整 launch descriptor。
- Status source Start：receipt 额外绑定 frozen exact source Task/Run fence、source-start
  WAL/pending descriptor、目标 TaskRef 与同一四个 root artifact 的 exact digest；若
  `trigger_context_copied` / `decision_copied`，则 `trigger-payload.json` /
  `decision.json` 也属于必须 regular-file/no-symlink 且 digest 相等的执行输入。
  `trigger-payload.json` 保留 source bytes，而 target 的 `payload.json`、context、meta
  必须形成同一首 R1 descriptor；source Run 只授权创建该目标 Task，不能被 Task root、
  目录名或 later latest pointer 替代。

两种 descriptor 都必须逐字段绑定首次 R1 的 operation、lane、Task/Run root identity、
Target/issue、agent/agent command、subject、workspace declaration、raw prompt 与 runtime
prompt；TaskService 必须在 generic registered-Task normalizer 填充 state 的 immutable
字段之前保留并验证原始 launch request，不能把 caller 篡改的 Target、agent、subject 或
workspace 静默改回 state 后再声称 receipt 匹配。未实现 typed source Start
consumer 的 `delivery-metrics` 等 lane 不得创建 child；任何未来实现也只能运输
这一个 receipt，不得为 zero-Run Task 建立第二套 latest/replay authority。路径存在
或可读不能替代 digest。receipt 与 `AdmissionRecoveryPlan`、
`ServerLostRunRecoveryPlan` 互斥。receipt 缺失/伪造、artifact 或 descriptor 变更、Task ABA、
source 变化、已存在 R1、或任意 recovery 混用，一律在创建 Run、copy artifact 或 process
dispatch 前无副作用拒绝。

### `EM-CORE-001` Work Module 的深模块 seam

产品层最终只保留三个 Interface entry point：

```go
type Work interface {
	Advance(context.Context, Command) (TransitionReceipt, error)
	Catalog(context.Context, CatalogQuery) (CatalogSnapshot, error)
	Inspect(context.Context, InspectionQuery) (Inspection, error)
}
```

- `Advance` 承接 Start、Continue、Cancel，以及 Runner completion、recovery、writeback receipt 和 cleanup receipt 这些内部命令。
- `Catalog` 返回 Task 列表、Target/work-item 分组和与它们同一个 projection revision 的计数。
- `Inspect` 一次返回 `focus_task`、可切换 Run 目录、`selected_run`、Task actions、Run 证据和 Task 文件范围。

这是目标 Interface 和迁移约束，不是假定仓库当前已经存在同名 Go symbol，也不要求更换现有文件存储格式。当前真实 semantic owner 如下；在 facade 完成前，这些 owner 共同组成 Work seam，新增实现不得另建同义状态机：

| Work 能力 | 当前唯一实现 owner | 当前收口状态 |
| --- | --- | --- |
| strict aggregate load / exact Run projection | `internal/taskstore` 的 `CollectContext`、`FindInCollection`、`ProjectRunRecordsStrict` 和 intent/event recovery | 已实现 |
| Run allocation、Continue、Cancel、completion、recovery、cleanup transaction | 目标 owner 是 `internal/taskservice.Service` | provider admission、server provider launcher、ChatBridge 的 Start/Continue/Cancel、Workspace disposal、CLI service stop/update pause 与 browser cleanup 已进入 `Service.Advance`；server completion event transport 只包装 `CommandLaunchRun` 的终态通知，不暴露 `RunAgent` 分配/启动能力。ChatBridge 只在准入后提交 exact TaskRef binding outcome。仍保留的 legacy TaskService public helper 必须以 managed production 不可达的结构证明登记，不能算作第二条写链路 |
| Status Catalog | `collectStatusTaskStatesContext` + 一次 `projectTaskViews` | 已收口到同一 captured `now`、TaskView slice 和 canonical `task_view_revision` |
| Status Inspect | `statusInspection` + `statusSelectedRunScope` | 已收口到 request-local Task/Run snapshot；focus/actions/history/selected Run/source continuation 共享 revision，并与调用方冻结的 Catalog revision 做精确等值校验 |
| 跨 Adapter 的同名 `Work.Advance/Catalog/Inspect` Go facade | `Service.Advance` 已建立 Runner observation 的第一个生产切片；Catalog/Inspect 仍由既有 owner 提供 | 只允许按本模型做无语义迁移；只有全部 production writer 清零后才能把 facade 名称计作完成 |

内部 strict aggregate loader 封装 `task-state.json`、Task event ledger、admission/run-claim/terminalization intent、Run registry、process observation 和 typed resource registry。Adapter 不得绕过上述 owner，直接根据某个文件、字段、目录或字符串推导业务结论。`Work.Advance` 的完成条件不是出现同名 interface，而是所有 production lifecycle mutation 都由 `taskservice.Service` 在同一 lock/revision/intent/receipt 骨架中推进；Runner 只上报 observation，server/chatbridge/provider/CLI 只运输 Command 或 effect。任何仍直接调用 `StateIO`/`Commit*Transition`/`UpdateForRun` 的 lifecycle 路径都属于未完成迁移。

下表是该完成条件的生产入口账本。它按语义写入口维护，不按某个缺陷或分支维护；新增直接写路径必须先登记为未收口，不能因为调用了共享 helper 就视为已符合 `Work.Advance`。

| 生产入口 | 当前直接写面 | 目标输入 / owner | 收口判据 |
| --- | --- | --- | --- |
| Runner execution 与 resume | managed 路径把 identity capture、spawn、launch commit、timeout/reap、exit disposition、runtime activity、marker、session audit、callback fault 和 browser cleanup 上报为 typed observation；`legacyState` 只服务非 managed 兼容路径。Runtime adapter 只能从自己的 closed protocol event 生成 `RuntimeFailureReceipt` / `AgentResumeHandleReceipt`，不得把 stdout/stderr 或另一个 Agent 的输出交给正则、模型或通用文本 classifier 后当作事实 | `taskservice.Service.Advance(CommandObserveRunner)` 强制 observation 携带并复验 `{task_id, task_instance_id, task_registration_sequence, run_id, sequence}`，process mutation 再校验 PID/generation/containment；failure/resume receipt 还绑定 agent、agent conversation、adapter schema 与 receipt id；completion 仍由 TaskService terminalization WAL | managed Runner 不直接提交 Task/Run lifecycle；旧 Task instance/R1 observation 不写 successor state/event/effect。未知 failure 只终结当前 Run，不触发 router unavailable/cooldown/failover。共享 WorkLedger event id 同时包含 Task registration 与 Run generation，TaskID 与 RunID 分列保存 |
| Status Start/Continue/Cancel/retry | `internal/server/status.go`、`task_actions.go` 及 lifecycle handler 的直接 transition/writeback mutation | structural Task ref + expected revision 的 `Command`；Continue/Cancel 另携带 frozen exact Run expectation；Chat retry 另携带 TaskService-sealed opaque exact-Run plan；`taskservice.Service` | GET ActionPolicy 与 POST 共用同一 plan；每次 POST 对 strict Task 立即投影一次并只消费该 closed policy 的 `enabled/reason/strategy/requires_input`，disabled 一律拒绝且不写 lifecycle；Continue 的每个 production lane adapter 必须把同一 source/current expectation 原样送到 Run claim，Chat retry launcher 必须把同一 opaque plan 原样送回 TaskService，二者都不能在 adapter 内按 latest/current 重选；handler 只做 transport、鉴权和 response，不写 lifecycle |
| Admin、storage 与启动恢复 | `internal/server/admin.go`、`storage_wait.go`、terminal/writeback recovery 路径的 state 修复 | 已存在 durable intent/receipt 指向的 recovery Command | recovery 不新造业务意图，只推进 exact owner；所有物化修复带 revision/receipt |
| ChatBridge / IM binding、Start、Continue、Cancel 与 completion | ChatBridge 只归一化 conversation Target、不可解析 binding intent、strict Run artifact 和 IM transport；TaskService 准入后才提交 exact TaskRef binding outcome，`chat_reply_delivery` intent/receipt/projection 归 `taskservice.Service` | `CommandLaunchRun`、`CommandCancelTask`、`CommandChatBridgeLifecycle` 与 sealed-plan `CommandRetryChatBridgeWriteback`；取消和 delivery receipt 分别携带 exact TaskRef、以及 exact `{task_id, task_instance_id, task_registration_sequence, run_id, sequence, receipt_id}` | intent 不可被选择/取消消费；owner 成功登记 Task 后才提交 binding。delivery owner 先持久化 claimed intent，解锁后才发送；receipt 派生终态。Chat retry 的 artifact reader 仅可读 sealed plan.RunDir，plan 后出现 successor 必须在 effect 前 typed stale conflict。claimed 无 receipt 收敛 unknown，绝不自动重放 |
| Managed CLI | CI wait、Workspace registry/outcome/storage、external-resource registry、service stop/update pause 与强停后的 browser cleanup 都通过 typed Command 运输 | CLI 从 TaskService 注入或 strict aggregate 解析的完整 TaskRef/Run fence 提交 Command；CI wait 在 provider call 前额外取得 TaskService sealed `CITargetClaim`；`taskservice.Service` | CLI 不直接写 StateIO，也不直接按 path/socket 执行 browser cleanup；CI 参数必须与 claim 完全相同，provider host 只取 claim authority，poll/result 回显 claim 与 pipeline identity。owner 先写 intent/effect-start，锁外执行 effect，再以 receipt 和 exact owner recheck 投影。过期 receipt 不改变 successor |
| Workflow/provider action 与 adapter | `internal/server/workflow_actions.go`、provider adapter、launcher 中 exact Run 私有 action intent/receipt、派生 action/response Artifact 和 WorkLedger 历史条目 | effect intent/receipt 或 Run plan；provider adapter 只执行 effect | action outcome 先写 receipt，再由 owner 收敛 Task；adapter 不提交 lifecycle，也不把 provider/workflow 审计追加为 Task event |
| External resource / workspace helper | 可被 CLI/server 直接调用的 package helper 与 cleanup mutation | `taskservice.Service` 的 typed registry/cleanup command | 所有登记、lease、cleanup 和 disposal receipt 都在 Task lifecycle lock/revision 下 |
| 强制 stop/update 与后台维护 | adapter 只做 preflight、服务管理和 typed maintenance Command 运输；Task mutation 归 TaskService | Cancel/reconcile/maintenance Command | Docker preflight 固定由本次部署的 digest-pinned image 执行；checkout 中是否碰巧存在一个本地 `jarvis-box` 文件不得切换 owner、版本或 PID namespace。preflight/upgrade 文件和 root scan 只供发现/审计；每个 Task 仍用 exact TaskRef/RunRef、intent/effect-start/receipt/reproject。root maintenance lock 只协调窗口，不是 durable owner 或副作用 receipt |

`internal/taskservice` 内部在 lifecycle lock 下的 state mutation、严格 loader 的只读 recovery、WAL/receipt settlement，以及 guardian 私有 process receipt 是 owner 实现，不属于待迁移旁路。`tasks verify`、只读 Inspect 和不改变 Task lifecycle 的安全探测也不进入 `Advance`。账本的某一行只有在对应 production writer 枚举为空、入口契约测试通过且没有语义兼容 wrapper 反向暴露写能力时才能标记收口。

写入口审查必须覆盖 Adapter 的直接 state 写入、raw filesystem lifecycle 写入，以及通过旧 public method 间接触发的 mutation。只有全部生产写路径归于 `TaskService.Advance` 才算收口；调用共享 helper、命名或注释不能证明 owner 正确。使用普通代码审查和行为回归核对入口与最终结果，不维护按每个 AST occurrence 锁定的独立债务清单；已被替代的内部写路径必须删除。

读侧审查必须区分唯一 projection owner、只消费 sealed TaskView/typed plan 的 transport，以及具有独立 closed schema 的非 Task payload。Provider receipt 的 `status` 不是 Task lifecycle 状态。Adapter 的 recovery candidate、ActionPolicy、CLI maintenance plan、Chat continuation plan 和 follow-up cache reconciliation plan 必须是 sealed typed value；返回 raw Task map 再由调用方分类，仍算未迁移。审查实际数据流并以行为测试验证，不以 occurrence 清单或 owner allowlist 自证正确。

follow-up JSON 只是 finding-set/cache，不拥有 Task 生命周期。它记录的 active/admission owner 必须是完整 TaskRef；有 Run 时还必须记录完整 `{run_id, run_sequence}`。每次 cache reconciliation 都先把这组 fence 交给 TaskService strict aggregate planner；planner 只返回 closed `owned`、`materialize`、`terminal`、`stale` 或 `blocked` disposition，以及已验证的 Task/Run fence、terminal outcome 和稳定 reason。`materialize` 是 admitted zero-Run cache 转移到首个实际、current、`followup/start` R1 的唯一授权，必须复验同一 Task generation、完整 Run fence 和 Run-private context；foreign/stale Run、Task ABA 或 context 漂移一律不得把 cache 提升为 active。只有 `terminal` 可关闭该 cache 的 in-flight finding set，只有 `stale` 才可按原 finding set requeue；`owned`、`blocked`、任一缺失/损坏/ABA/不匹配的 Task、Run、registry 或 artifact 一律不重排、不重发、不以 PID、目录、Task status/phase/monitor 文本自行补判。等待恢复的 follow-up Start 还必须从 TaskService-sealed `followup-launch` descriptor 重建不可变 ingress snapshot；descriptor digest/binding、TaskRef、zero-Run source、lane 或 operation 任一漂移都必须在读取 mutable cache 或调用 launcher 前失败。历史 `review-summary` 扫描同样先由 TaskService 把目录解析为同一 Task/Run fence，并且只接受该 Run-private、terminal 的 `mr-review` artifact；`result.json`、评论 action 文件或目录存在都不是完成证据。Runner completion 也必须同时匹配缓存 Task/Run fence 和 strict terminal plan 后才可产生 provider effect。Follow-up 状态评论本身也是 exact Run provider effect：intent/plan/receipt identity 必须固定完整 TaskRef、`{run_id,run_sequence,run_dir}`、finding-set revision、phase 和 payload digest；短 cache lock 内只可登记 intent，`UpsertFollowupStatus` 必须在锁外执行，之后写 acknowledged/definite-failure/outcome-unknown receipt，再重取 lock 复验同一 owner 后提交 comment id/cache projection。effect-start 后没有 closed receipt一律 outcome unknown且禁止自动重发；旧 Task/Run、缺 sequence、同目录 ABA 或 payload 漂移不得更新当前 comment/cache。FollowupDispatcher 只运输上述 plan 和 provider status effect；它不得直接读取 `task-state.json` 或将 Task lifecycle 文本映射为 cache action。

Status/Admin 的 lost-Run recovery 同样先提交完整 TaskRef，不得从一次 Status collection 的 `current/latest`、`monitor_status`、`pid_running`、`reaping_failed` 或 `runtime-launch-failed` 文本自行决定是否恢复。`runtime_launch_failed` 的持久 bool 是唯一现代 failure fact；仅当该 bool 缺失时，legacy adapter 才可接受 exact `authoritative_phase|phase=runtime-launch-failed` 枚举，`last_error_reason`、`status_reason`、错误输出及 substring 永远不能阻断/授权 recovery。TaskService strict aggregate planner 选择并验证唯一 current Run 后，返回 sealed `ready`、`skip` 或 `blocked` plan：plan 固定携带完整 Task/Run fence、lane、稳定 reason、已派生的 recovery observation，以及供既有 lane launcher 消费的不可再分类 launch snapshot。只有 `ready` plan 才能提交 observe/reap transition；每一个 requested/failed/waiting/skipped/replayed/spawned receipt 都从同一 plan 生成，重新取 plan 或 TaskService owner recheck 失败一律停止。Admin 只做 capability 路由、锁外 launcher transport 和 effect receipt 回传；它不得读取 raw Task lifecycle 字段、生成 recovery receipt fence，或把 launcher error 映射为别的 Task generation 的终态。

CLI service stop/restart/update 的维护读取也遵守这一条：TaskService 一次 strict root scan 只能返回 sealed `ServiceMaintenancePlan`。每个 blocking entry 都携带完整 TaskRef，只有存在 current Run 时才携带同一代的完整 Run fence；其 disposition 是 closed set `pause-active-run`、`cancel-zero-run-admission` 或 `block`，reason 是 closed typed reason，展示只能使用 plan 的 stable summary。CLI 不得根据 raw `status`、`phase`、`monitor_status`、`next_action`、PID、socket、latest/current 指针或 scan map 自己决定是否 stop、pause、cancel、resume 或 cleanup。`--force` 只消费上述 plan 提交 exact Command；stop/restart 每个 effect 后重取 plan。在线 update 先准备校验目标制品，再由 TaskService 关闭新 Run 准入并在首次暂停前持久化本轮完整 Task/Run、Agent、conversation 清单；在同一维护门下允许不同 Task 最多三个并发执行 exact Command，每个 Task 在自己的 lifecycle lock 内重验 owner，service manager action 前仍须重取 plan，仍有 entry 即拒绝。维护门同时覆盖 IM、webhook、后台 Start 和 CLI；IM 保留原事件游标与回复期限，webhook 保留原受理收据，门开放后继续运输原输入。无活动 Task 且服务未运行时仍允许离线升级。

`update --force` 消费完 plan 后还必须把本次中断的 Run 逐项接着跑：Continue 只能取该 Run 自己的 Agent 和用户可见的恢复说明，正常暂停后的 Continue 复用可验证的原生会话，升级成功与安装器失败都要续跑，续跑失败必须让命令失败；只停不恢复视同未实现。版本化维护收据只记录本轮意图和恢复结果，不拥有 Task lifecycle；目标 Flyway 在 startup lease 前验证其已发布 schema。重启后或显式失败恢复才接管该轮收据，当前进程不得自动恢复自己正在暂停的事务，竞争升级不得取得另一轮恢复权。原 Run 未结算或恢复被取消时保持待恢复和准入关闭，由既有恢复 sweep 收敛后重验；owner 已推进、Task 取消或已有失败 successor 都只观察，不自动再创建 Run。准备阶段失败的最新 Run 若尚未启动 Agent 且没有私有原生句柄，显式 Continue 可以在同一 strict aggregate 内检查更早、同 Agent、同不可变 conversation 的完整 Operational Run；只有原 Resolver 逐条核验完整注册和私有收据后才能复用句柄，任何损坏立即拒绝。命令权限和 source fence 仍绑定最新失败 Run，不改写历史，不据此自动重试。非正常失联继续遵守 EM-RECOVERY-001 的 sealed recovery 策略，不据此伪造原生会话。所有条目收敛后开放准入；重复恢复只返回结果。

没有 current Run 的 admission（包含它仍在等待存储的同一 zero-Run admission）没有 Run/browser owner：stop/restart 只能 cancel，update 一律拒绝恢复/中断；带 current Run 的 storage wait、process identity unresolved、terminalization/recovery pending、missing/corrupt/ambiguous aggregate 都是 fail-closed `block`，不得从任意文本或空字段降级为可暂停。effect receipt 的 `status` 是该 effect 自己的 closed receipt schema，不是 Task lifecycle state。`workspace list` 同样只通过 complete environment fence 和 `MutationService.CurrentWorkspaces` 读取；缺少或过期 fence 必须失败，不能由 `task-state.json`、`taskStateTerminal` 或目录状态补全。

Runtime adapter 的失败观察必须携带完整 Task/Run fence、AgentConversation、Agent、受信的版本化协议、closed failure kind 和本次调用内的终止 event identity。只有“原生终止的有界自动 Continue”中列出的三类顶层终止事件，经 TaskService 在 current owner 下接受并落盘后，才能申请同一 Task 的后继 Run。普通非零 exit、signal、context cancellation、spawn error 只是进程事实；原始 stdout/stderr、error.Error()、日志 tail、助手或工具生成的 JSON 分类及 try-again 文案不能授权自动执行。

协议适配的版本、终止事件及最终失败退出必须全部成立；receipt 缺失、版本不支持、完整身份不符或持久化失败均 fail closed，不产生恢复权限。Codex thread.started.thread_id 仍只授权私有 AgentResumeHandleReceipt，不能单独证明 failure 或 usage。三类恢复采用 Task 内预算和到期时间，不建立全局 availability/cooldown。runtime token usage 继续要求独立稳定的 final-cumulative event identity；普通 terminal result、助手 message/item id 和 session id 不能替代它，没有该证明时 usage 保持 unknown。

managed `jarvis-box ci wait` 在任何 GitLab API call 前把解析后的 CLI request 与完整 Task/Run fence交给 TaskService。TaskService 只从当前 Task 的 immutable GitLab Target 生成 `CITargetClaim`：`merge_request` 只允许同 project + 同 MR iid，`commit` 只允许同 project + 同 SHA；`issue`、branch selector、缺 authority、legacy URL、Run context 和后来 Artifact 不能合成 claim。命令参数必须与 claim 的 canonical endpoint 完全一致，实际 `GITLAB_HOST` 只能取 claim authority。每个 phase/poll/result command 都携带 claim id、authority、project、selector 与 endpoint；TaskService 在 lifecycle lock 中重新加载 current Target/Run 并重算 claim。pipeline id 必须是 provider 返回的 closed scalar identity；非空 pipeline URL 必须与 claim authority、project 和 pipeline id 精确匹配。无 claim、参数漂移、环境 host 冲突、payload URL 越界、R1→R2 或 Task ABA 都不得调用 provider 或写 `ci-wait`、pipeline URL、result/event。非 managed CLI 可以保留显式参数的只读等待，但它没有 Task 投影权。

Delivery Metrics 的历史发现与准入由服务端后台协调流程拥有：服务启动时同步，MR/PR 关闭或合并 webhook 失效快照并唤醒同步，分析 Task 完成后自动读取结果、继续发现尚无 Task owner 的 pending 项，每分钟补查 Provider 历史。页面关闭或无人访问 API 不影响分析。每个 Provider 同时最多处理一个分析 Task，每轮最多提交一个 typed Start；所有执行仍属于普通 `delivery-metrics` lane，没有全局 FIFO queue、私有 cursor 或第二个生命周期。事件回调只失效和唤醒，不直接执行 Agent。`GET /status/api/value`（含 `refresh=1`）只刷新和读取派生统计，不提交 Start/Continue；已有 Task 的失败或无效结果由操作者明确 Continue，后台不自动付费重试。有效历史结论和 Cancel 的最终决定继续复用。自动修复漏斗由同一服务端流程在工作项事件后及每分钟刷新，并将结果通知已打开的页面；读取漏斗不启动分析或改变 Task 状态。

同一个 Delivery Metrics evidence key 在任意时刻至多有一个 Task owner：Task ID 取 canonical Subject 身份键的散列，对同一 MR/PR 恒定。刷新必须从 TaskStore strict 读取该 Task——inspect 后 load、再重新投影，并要求两者逐字段相等——并只消费由此得到的 canonical TaskView：只有 exact Run 通过完整 fence 校验、终态为 succeeded，且结果 Artifact 通过合同校验时，才把结果提升为指标事实；active、waiting、zero-Run admission、Run 未成功、Artifact 无效或 Task 记录损坏等其他情形都继续占有 evidence、投影为 `pending`，不得自动创建替代 Task。只有真的 `ErrNotFound` 才当作尚无 owner 并允许准入；Task 记录损坏、store 根缺失或不可读一律 fail closed，读取错误不得降级成「没有 Task」而放行准入。MR/PR 关闭或合并事件不取消交付分析 Task，因为分析以合并后的事实为输入；迟到的终态 webhook 也不得中止已开始的分析。操作者 Cancel 仍是 retained state 内的最终决定，把该 Subject 投影为 `judgment-unknown` 并永久占有 evidence，后续刷新不得为同一 Subject 提交替代 Start。

Delivery Metrics classification 合同只把“非 author、非 Jarvis/bot 的人类自己写出的实质纠错内容，并且后续 source revision 能和这条纠错建立因果关系”计为 `human-corrected`。人类只是转述、确认、merge/approve，或要求 agent 按 bot/Jarvis review 修复，不继承 bot/Jarvis review 的纠错内容；若发生过 source revision 但缺少 qualifying human correction，则归为 `self-revised`，证据不足才是 `judgment-unknown`。

Status Value 的 GitLab/GitHub provider transport 固定请求 CLI 的 documented `--include` HTTP framing，并在 JSON decode 前严格分离 status/header 与 body。只有完整 HTTP status frame 可以产生 typed auth（401）或 transient（429/5xx）结论；CLI stderr、exit error 和 response body 永远只是诊断。多段 frame 只接受 body 为空且边界可证明的 redirect chain，否则 unavailable。GitLab `order_by=merged_at` 的一次 400 仍是 ambiguous；只有对同一 endpoint 仅移除 `order_by` 的 probe 成功且返回声明 schema，才投影 typed unsupported-order warning，probe 数据本身不得进入指标。

TaskService 一旦分配 Run，后续 preparation/dispatch/spawn 即使失败，返回给 Adapter 的结果也必须保留 exact `{task_id, task_instance_id, task_registration_sequence, task_dir, run_id, run_dir, sequence}`。Adapter 只能把失败 receipt 提交给该 generation 的 `Advance`；不得丢弃 handle 后用 staging id、Task root、latest pointer 或下一代 Run 记录失败。

SSE/Watch 只传递 revision 和 invalidation notice，不传递另一份可覆盖 `Catalog`/`Inspect` 的状态。一个 Task event 只能由 Handler 注册在 EventBus 上的唯一 cache owner 执行一次 Catalog/summary/derived-cache generation invalidation；发布 Adapter 和任意数量的 SSE subscriber 都不得再次推进 generation。主 work-item 读模型收到 Task invalidation 后重读相应 Interface，并要求 response 的 `task_view_revision` 与待消费 revision 一致；迟到 response 不得渲染。WorkItems 等派生缓存必须把构建时的 Catalog `task_view_revision` 作为有效性 fence：Catalog 失效必须同时使全部派生缓存和 cursor generation 失效；即使事件漏通知且两个 TTL 的完成时刻不同，命中派生缓存前也必须重读或验证当前 Catalog revision，禁止同时对外提供 R1 WorkItems 与 R2 Catalog。每个异步 UI request 在发出时冻结 `{catalog revision, UI generation, focus task_uid, selected run_ref, endpoint}`；任一分量与当前界面不一致都必须丢弃 response，不能用同一个 task_uid 在 A→B→A 切换后接受旧 A，也不能让旧 selected Run 覆盖新选择。浏览器遇到 revision 不一致时只允许执行有界退避；达到上限后等待新的 invalidation 或用户显式刷新，不能用即时重试制造页面刷新死循环。浏览器发起 Start-from-source、Continue、Cancel、单 Task Workspace 删除或批量 Workspace 清理时，必须把用户当前看到的 `task_view_revision` 原样带入 mutation；服务端必须绕过 Catalog cache 重读 strict snapshot 并做等值校验，失配统一返回 `409 task_view_revision_changed`，且在重读 ActionPolicy、写 intent、启动进程、发 provider 请求或删除文件前停止。客户端收到该 409 只允许执行一次有界重读，绝不能自动重提原 mutation。系统设置等包含输入、焦点和 mutation 控件的交互面只记录 invalidation，在用户显式刷新、切换分区或提交操作后的稳定边界重读，不得由资源 tick 自动重建 DOM。该稳定边界的重读必须合并成最多一个 in-flight request；从请求发出到同 revision 快照原子替换完成之前，屏蔽可变操作控件，不能让一个延迟 response 在用户已开始输入或点击后再替换交互 DOM。

revision 是规范化内容的等值 token，不是单调序号；内容 A→B→A 合法，consumer 只能比较请求冻结值与 response 当前值是否精确相等，不能做大小判断或因为曾见过 A 就永久拒绝 A。上段禁止接受的是旧 UI generation 的迟到 A response，而不是禁止系统再次生成同内容 A。

Followup cache identity 必须是完整 canonical Subject `{provider,authority,kind,project,number}` 的全量 SHA-256；project 路径的安全化字符串不能充当 key。旧命名 cache 只在它是该 Subject 的唯一命中时原位复用；同一 Subject 同时存在 legacy/canonical 两份、path/字段/URL 不一致、authority 缺失或配置 authority 漂移都必须在 live read、Task admission 和 provider effect 前失败。

每个实际 Followup Run 在 `PrepareRun` 中先写 append-once `.private/followup-admission.json`，固定完整 RunRef、canonical Subject、Target digest、本轮 finding-set digest，以及真正进入 Git 的 `clone_url/source_project_path/target_project_path/source_branch/target_branch` 与其 digest；公开 cache、`followup-state.json`、`run-context.json` 与 status comment id 都不能替代它。replay 的公开 state 与 provider live read 必须同时与该私有 Git-input seal 一致，任一漂移都在 Workspace/Git 前失败。首次 admission 把 sealed pending finding set 原子转入 in-flight 后必须清空对应 pending 集，避免新评论把本轮 finding 再次并入下一轮；storage-wait 恢复只能从 sealed descriptor/state 和 matching Run-private admission snapshot 物化 in-flight，恢复期间新到且 `pending=true` 的 finding 保留给后续 Run，mutable cache 不能把 C2 注入正在执行 C1 的 Run。TaskService 分配 exact Run 后，launcher 必须重新生成 prompt、Agent args、log/result 路径和 Run-local env，任何 provisional/staging 路径不得进入实际命令。

pre-snapshot 版本创建的现代 Followup Run 只有在 TaskService exact Run 事件与 Run state 同时证明它由标准 `jarvis-box update --force` 以 `jarvis-box-update-forced` 停止时，才可进入一次有界升级兼容；普通缺 snapshot、手工 stop、失败 Run 或 owner 不完整一律 fail closed。该兼容不得执行旧 Run 的公开 Git 字段：Status Continue 必须携带 TaskService sealed Continue source fence，launcher 必须从 provider live API 取得完整 Git 输入、保留原 finding set，并在 successor Run `PrepareRun` 中生成当前 schema 的私有 snapshot 后才可触达 Workspace/Git。provider live 返回不完整时保持不可恢复，不得回退到公开 cache。当前实现尚未打开这条兼容，因此它现在必须保持关闭：`jarvis-box update --force` 已改由 service-maintenance plan 以 `service-update` 暂停活动 Run、再用该次 plan 返回的精确 paused 清单显式 Continue，Run 上不再留下 `jarvis-box-update-forced` 这一停止事实，TaskService 侧也没有把它解释为升级兼容的 consumer。缺 sealed snapshot 的 pre-snapshot Run 一律按 fail closed 处理，只有停止事实的 producer 与 consumer 同时落地后才可打开这条分支。

Follow-up status intent/plan/receipt 还必须固定 sealed Subject/Target digest 与 finding-set digest。terminal update 的 comment id 只来自同 Run 私有 running ACK，不能从 mutable cache 取值。缺少 private admission snapshot、authority/finding 漂移、旧 Task/Run 或 duplicate cache 时，必须在 effect authorizer、provider call 和 public audit 前失败。

### 唯一事实源与归属

| 事实 | 唯一 authority | 禁止的替代来源 |
| --- | --- | --- |
| Target identity | Task 创建时持久化的 immutable `subject`/Target key，包含 provider authority/host；pre-authority 历史 Task 只允许用同一 Task root 已持久化且其余 identity 全等的 canonical URL 补 authority | 当前 `GITLAB_HOST`、目录名、任意展示 URL、后来的 Artifact |
| Task identity | `task_instance_id` + 结构 Task ref | 可重名的 `task_id`、裸 Run id、Target 反查 |
| Task lifecycle | strict aggregate loader 按 state + durable intent + event recovery 规则得到的 aggregate | Status handler、lane wrapper、Artifact 文本、UI 字符串 |
| Operational Run 存在、顺序和归属 | strict Run registry / Run event projection | `current_run_id`/`latest_run_id` 单字段、mtime、目录是否存在 |
| Historical read-only Run | 完整 TaskRef + 显式 approval manifest 所制的 certificate + certificate 中 frozen Run/artifact evidence | candidate scan、证书外目录、Run pointer、历史文本、任意 action/recovery/effect |
| active Run owner | Task 上的 current ownership fence + 完整 Run projection | 最新时间、某个 live PID、页面选中 Run |
| Process ownership | exact `{task id, task instance, task registration sequence, run id, run sequence, pid/pgid, process generation, containment}` | PID/PGID 数字本身、低 CPU、长时间无输出 |
| AgentConversation | 显式 conversation record + private resume-handle metadata | native session 文件名、日志内容、其他 agent 的 handle |
| Workspace ownership | append-only `workspaces[]` | `cwd`、目录扫描、Run context、Git worktree 名 |
| 外部资源义务 | typed `external_resources[]` | Docker 全局扫描、Compose 文件、仓库名、marker |
| Run Artifact | exact `RunRecord.ArtifactScope` | Task-root 历史文件、sibling Run、“最新可读文件” |
| Provider/workflow delivery | exact Run/Task effect intent + durable receipt/action audit | `comment.md` 存在、HTTP 错误文本、旧 Run 成功 marker |
| Workspace disposal | Task 登记表 + disposal batch/round/member WAL + 当前 aggregate certificate | `workspace_disposal_completed` bool、Task 是否 completed、Workspace 路径已不存在 |
| 历史受理与 Run 趋势 | append-only work ledger | 当前保留的 Task state 数、SSE Task dashboard |
| Doctor/内部轮询运行状态 | typed OS/command observation 与带稳定 loop identity 的 durable outcome receipt | log 文案、detail/error、mtime、目录/Artifact 扫描 |
| Status/CLI 状态与 actions | 同一 `TaskView` projector | light/full 分别分类、work-item 文本推断、前端二次分类 |

历史 Task 缺失 provider authority/host 时默认只能作为单个 Task 查看。若同一 Task root 同时持久化了 canonical provider URL，且 URL 解析出的 provider/kind/project/number 与 subject 已有字段全部相等，则只读 projector 可以只补 authority 并参与 Target/WorkItem 聚合；这是对本机真实 pre-authority schema 的 bounded upcast，不修改磁盘。URL 缺失、来自 Run/Artifact/配置、或任一字段冲突时仍保持单 Task fail closed。Task subject 整体缺失时，即使 Task-root display URL 或 latest `run-context.json` 恰好含有完整 provider/authority/project/kind/number，也不能制造 Target、replay 或 provider mutation authority。部署配置只能帮助新请求建立 identity，不能改写历史 identity。

同一规则同时约束 Target inbox、work-items、related Task 和 GitLab activity overlay：只有相同的持久化 provider + authority + kind + resource identity，或分别通过上述 Task-root canonical URL upcast 得到完全相同 identity，才可跨 Task 合并。只相同的 project/iid、`target_key`、目录名、Run context 或展示文案仍必须保留为不同 unknown-subject 分组；activity 不得借当前部署 host 黏到其中任意一个。

新 Target 的 authority 在认证入口归一，规则属于 Adapter contract：GitLab、GitHub/GitHub Enterprise 与 Jira 使用已认证 provider URL 的小写 host（非默认端口保留）；Feishu Project 使用其认证 API boundary `project.feishu.cn`，stable project key 仍属于 resource identity；IM 使用 connector/account identity，不使用展示名称。Adapter 无法从已认证输入或自身稳定配置证明 authority 时必须拒绝创建 provider Target，不能等到 Run artifact 或 Status 读取时补齐。

### `EM-AGG-001` strict Task aggregate

`Advance`、`Catalog` 和 `Inspect` 使用同一个 aggregate loader：

1. 用 opaque/structural Task ref 唯一定位 Task；可重名展示 id 产生多个候选时返回 ambiguity，不得选“最新”。
2. 读取 Task state 和 durable admission/run-claim/terminalization intent。intent 是未完成事务的高优先级事实，不得被旧 state 隐藏。
3. state 不可读时从 Task events 重建读模型；只有 recovery 可把重建结果物化回 state，普通 GET 保持只读。重放必须先从校验通过的 `task_admission_committed` / `run_created` WAL 选择最高不可变 `{task_id, task_instance_id, task_registration_sequence}`，丢弃其他 Task 代次及缺少完整代次证据的现代事件，再在该分区内选择最高 `{run_id, run_sequence}`；不得先按 Run 选事件，因为同一路径重建后的 Task 可以复用相同 TaskID、RunID 和 Run sequence。Task-level Workspace disposal WAL 同样受 Task 代次 fence 约束，不能绕过 Run reducer 提前污染 successor。没有任何注册线性化点的历史账本才允许进入显式 pre-registry legacy 重放；同一 registration sequence 出现冲突 identity 时投影为不完整，不能猜一个 winner。
4. 完整投影 `OperationalRuns`。任一 Operational Run state/registry/event 损坏时 aggregate 标记 `projection-incomplete`，禁用 mutation、writeback、cleanup 和跨 Task history merge。只有 `EM-HISTORICAL-RUN-001` certificate 的结构、TaskRef、Run-state 与 legacy event identity 完整验证的早期 Run 才进入独立 `HistoricalReadOnlyRuns`；这些身份事实不完整、证书外 Run、TaskRef/Run-state/event digest 漂移都使 aggregate fail closed，不能静默回退为普通旧 Run。artifact manifest 本身由 certificate digest 鉴真，但 artifact 文件字节只在实际选择该文件时重算摘要；单个展示 artifact 缺失或漂移只让该文件 unavailable，不能在每次 Catalog 刷新时递归读取全部历史字节，也不能反向抹掉已经验证的 Run identity。
5. lifecycle 仍阻塞时，只有 Operational exact `current_run_id` 是 active owner；Task 空闲时，最高正 sequence 的完整 Operational Run record 是 latest delivery generation。HistoricalReadOnlyRuns 不参与这个选择，即使其 sequence 更大。
6. 为每个 Run 构建显式 Artifact scope 和 process identity，不做 sibling/root fallback。
7. 按 Task 登记表加入 Workspace、external resource、delivery 和 disposal 事实。
8. 在一次 projector 调用中生成 lifecycle、action policy、status group、diagnostics 和 consumer counts。

loader 返回的 aggregate 是带 revision 的一致快照。页面、CLI 和后台恢复不得在一个请求中混用两次不同 revision 的结果。Task state 与 strict Run aggregate 分步读取时，loader 必须在二者完成后复核同一 Task-state revision；若写事务在读取窗口内推进了 revision，本次混合观察不属于业务上的 `projection-incomplete`，必须整体丢弃并立即做有界重读，不能把这个瞬时读取窗口投影成 `needs-human`、禁用原本可用的操作或写入缓存。只有有界重读仍无法取得闭合快照，或者同一稳定 revision 的事实确实缺失、损坏、歧义时，才发布 fail-closed projection。一次复核成功后，Task state、Operational/Historical Run 集合、Artifact scope、lifecycle、action policy 和 response revision 必须冻结为同一 request-local snapshot；后续磁盘变化属于下一 revision，不能反向使已封存的本次读取失效。

### `EM-RECOVERY-001` root maintenance repair ledger

`WithServiceMaintenanceRead/Write` 只协调 RunRoot 范围的 admission、claim 与维护窗口。它是进程退出后由内核释放的锁，不是 durable effect owner、repair receipt 或一次目录扫描结果的授权证明。reap、admission materialization、terminal recovery、scheduled disposal、retention clean 和 supersession 仍须逐 Task 使用 exact TaskRef/RunRef 事务；持有 root lock 不能把 path、旧 state、preflight 文件或扫描快照提升为 mutation authority。

lost-Run `Continue(recover)` 的 Run fence 只有两个封闭来源，二者都由同一个 TaskService strict-aggregate/receipt projector 产生，Status TaskView 和 recovery planner 不得各自从 `latest_run_id`、`stopped_run_id`、`status`、`phase` 或错误文案重分类：

1. **pre-reap current source**：完整 Task registration 下的 strict Operational current Rn，`current_run_id` 与该 exact Run record 一致，Task lifecycle 仍为 active/running/spawned，且同一 exact Rn 具有完整 `{process_run_id,pid|pgid,process_generation,process_containment}`。TaskService 必须重新验证该 generation 的 closed OS outcome 为 `process-already-absent`，并证明该 Rn 的 exact result Artifact 不存在；健康 running PID、正常 active process、已完成 result、非 recovery strategy、raw `monitor_status`/`pid_running`、任意 phase/status 或 pointer 都不能单独产生该 source；
2. **post-reap maintenance receipt source**：`current_run_id=""` 后，同一完整 Task registration、strict highest Operational Rn、该 Rn Run-local terminal `stopped`，并有同 Task/Run/sequence 的 durable `process_reaped` receipt。receipt 必须是 maintenance transaction 写出的 closed success：`run_fenced=true`、`reaping_failed=false`、`result.ok=true` 且不存在 survivor/failure；它不是一个裸 stopped 指针。

第二种 source 的 `process_reaped` receipt 已经封存了 maintenance 成功停止的 exact Rn；它允许 TaskView 保持 `continue.strategy=recover` 并把同一 Rn fence 交给 POST，即使 maintenance 为释放 live owner 已清空 `current_run_id`。两种 source 都必须拒绝 historical/legacy Run、缺或 corrupt receipt、Task ABA、R2（active 或 terminal）/更高 successor、非 stopped terminal、reap failure 和任何不完整 strict aggregate。TaskView 只有在同一 revision 的 strategy 已封为 `recover` 时才公开该 fence；TaskService 在 lifecycle lock 内以同一 projector 重验后才可接受 `RecoveryLaunchRequested` 并 claim Rn+1。

strict maintenance scan 必须返回同一 root snapshot 中的完整 `valid candidates + per-candidate/root failures`。发现任意不可读 candidate、registry/projection 不完整、WalkDir 错误或 repair ledger 不可读时，整个 root 的破坏性维护 fail closed；不能因为先遇到一个错误而隐藏其他 repair item，也不能清理其余看似健康的 Task。手工处置与 scheduler 使用同一个 root repair gate。

可从完整 durable events 恢复的 state 也不能在同一 sweep 中直接授权处置。root-owned repair transaction 固定为：

```text
strict scan evidence
  -> repair intent（canonical locator + domain + evidence epoch）
  -> repair effect-started
  -> exact Task lifecycle lock 下物化 projection
  -> repair receipt
  -> repair projection-completed / resolved
  -> 下一次 strict scan 重新读取后才可进入 disposal
```

repair ledger 自身有独立跨进程 lifecycle lock，覆盖 read/claim/append，不能依赖 shared service maintenance lock 的升级。已落 repair receipt、尚未完成 repair projection 时只允许重投影，不得再次物化或启动 disposal。可识别 Task 的 evidence epoch 使用 `{task_instance_id, task_registration_sequence}`；相同目录的 successor 必须新建 epoch，并显式 supersede 旧 ticket。无法证明 TaskRef 的 `unknown epoch` ticket 不得由后来出现的同目录 Task 自动 resolve、继承 backoff 或获得处置权限，只能在证据充分的专用恢复/人工流程中关闭。

repair intent、attempt、receipt、projection、supersession、exhaustion 和 resolved 都是 Status revision/invalidation 的 durable 输入；无持久事实变化的 scheduler tick 不得刷新页面。恢复 summary 必须显式返回本轮 `transition_count`，且它由 TaskService 在 exact Task lifecycle lock 内确认的 intent/receipt/state projection 计算，不得以 `candidate_count`、`blocked_count`、`waiting_count`、`failed_count`、`recovered_count`、TaskID、RunID 或最终 error 代替：WAL/receipt 已落而 state projection 失败时仍是一次 transition，后续 receipt-only 重放或未变化失败不是新 transition。一次 sweep 只要 count 大于零，Status 恰好发布一次 invalidation，payload count 为本轮真实 changed/receipt 数；不得把同一 receipt 在 launcher、outcome 和 summary 分支重复相加。lane 可在服务端内部 EventBus 保留 `storage-wait-recovered`、`duplicate-wait-recovered`、`admission-pending-recovered` 等遥测事件，但 HTTP SSE 边界禁止透出这些 raw event/payload；同一 scheduler round 的 summary receipt 是唯一 tasks invalidation publisher。内部 recovery marker 的删除若未改变 canonical TaskView/状态投影，不是 invalidation authority。

`acknowledged` provider mutation intent 的 writeback recovery 也是上述 sealed-plan 规则：Status scan 只运输候选的完整 TaskRef/TaskID，TaskService 必须在同一 Task lock 内严格验证 registration、无 active Run/admission/terminalization、exact delivery Run 和可恢复 lifecycle，再返回 closed `ready`/`skip`/`blocked` plan 与完整 TaskRunFence、exact Run record/artifact scope 和 lane。adapter 只能从该 plan 的 exact Run scope 读取 private ACK receipt 并提交同一 fence 的 delivery receipt；公开 audit 只能展示，不能作为输入。ACK 表示外部 provider/workflow effect 已完成，却不表示本地 Task terminalization 已提交：该恢复只能以完整 sealed fence 重验同一 private receipt，并提交 receipt-only 的本地终结事务；其 stable receipt id 只能由 operation、lane 和完整 TaskRunFence 派生，不能由时间、Reason、Error 或审计文本派生。它不得调用 provider/workflow executor、构造新的 provider input 或以“effect already done”跳过本地 projection；已存在同一 receipt 的重投影不产生新 transition，完整 matching 本地 terminal receipt 则使 planner `skip`。provider effect 的 legacy input 只能由尚未 ACK 的 delivery transaction 在第二次 exact-fence authorization 后提供。adapter 不得读取 raw `current_run_id`、`latest_run_id`、`status` 或 `phase` 来挑选/重新授权 Run。R1→R2、Task ABA、缺失或 corrupt registry/Run 任一发生均 fail closed，旧 plan 不得影响 successor。

Chat `retry-writeback` 不走 generic recovery launcher：Status 的 TaskView action 在 T1 仅冻结 strict R1 `TaskRunFence`；TaskService 在 T2 的 Task lifecycle lock 内先以 `ProjectExactRunChatReplyEffect` 验证 R1 的 private receipt 与 `chat_reply_delivery` 是同一完整 fence、closed `failed` 且 attempt 尚未耗尽，随后才封为 `ChatBridgeWritebackRetryPlan{TaskRef, RunFence, RunDir}`。`acknowledged`、`unknown`、missing/corrupt receipt、无 delivery projection 和 budget exhausted 都是 closed `writeback-not-retryable` conflict，绝不把 artifact capability 或 provider closure 交给 adapter；private seal 也不允许 adapter 根据路径、Task map 或 latest pointer 仿造。ChatBridge 只读取 ready plan 的 R1 artifacts/reply handle，并将完整 plan 原样交回 `CommandRetryChatBridgeWriteback`。owner 在 effect intent 前复验 sealed plan，随后 exact delivery claim 再次复验；R2 在任一间隙出现都必须是 `ErrChatBridgeWritebackRetryStale` / HTTP 409，provider closure 为零调用，且不得完成 R1 或 R2。无竞争时只重放 R1，receipt/terminal projection 也只能引用 R1。

admission materialization 逐 Task 汇总 `RecoverPendingRunClaim`、`RecoverAdmissionProjection` 和 `RestoreStateFromEvents` 返回的 changed；adapter 只能消费该显式 receipt。缺失 `task-state.json` 才可由完整、精确 fence 的 admission WAL 重建；corrupt、permission/I/O read error 或无法从完整 reducer 证明 current Task registration/Run generation 的 admission state 必须 fail closed，既不覆盖字节、也不计 transition。terminalization recovery 是更窄的独立例外：Catalog 对 corrupt state 仍保持 unavailable，只有 Task event reducer 能完整证明同一 Task registration、exact Run claim 和 sealed terminalization/writeback intent 时，TaskService recovery owner 才可在 Task lifecycle lock 内先显式 `RestoreStateFromEvents`、再重放该 intent；恢复本身计一次 durable transition。无 sealed intent、ledger 不完整/冲突、permission 或 I/O 错误都不得进入此例外，一个坏 Task 也不得阻止另一个 exact Task 收敛。Follow-up sweep 同理：它在同一 followup state lock 内比较 state file 的 before/after，只把 `state_changed=true` 的结果交给 Status；结果标签本身不是授权。系统设置只从同一 TaskView/maintenance projection 产生一份可执行 operator action，不能把 open ticket、verify observation 和 diagnose observation 重复计数。

storage/admission recovery 的严格 root scan 还必须一次性物化 `RecoverPendingRunClaim`、admission WAL 和历史 Chat Continue pre-spawn capacity failure；随后 **TaskService** 在同一 Task lifecycle lock 内校验 intake artifacts、storage health、duplicate blocker、pre-spawn 与 stale admission，并只返回 sealed `AdmissionRecoveryPlan`。plan 的闭集 disposition 为 `launch` / `blocked` / `skip` / `settle-invalid`，携带 typed wait kind、closed reason、admission fingerprint token、完整 TaskRef 与 nullable exact Run fence，以及只含 lane、Start/Continue operation、selected source artifact scope、descriptor reference、canonical subject 和已登记 workspace 的最小 typed launch request；它绝不携带 Task state 或 `pending_launch` map。server 只能按 plan 检查 lane transport 能力、调用 launcher；`launch` 必须把原 plan 交给 `CommandLaunchRun`，后者在实际 replacement Run claim 的同一 Task lifecycle lock 内重新比较 token、TaskRef、lane、status/phase fence，任一漂移/ABA 都在创建 Run、Artifact 或进程前拒绝。admission WAL 的 snapshot 必须完整保留 fingerprint 与 owner 校验读取的全部 typed 字段，尤其是 `task_store_persistence` / `workspace_storage`；共享 snapshot schema 不得在写入后裁掉其中任一字段，否则 producer 自己生成的 Z2/S1 也必须判为 projection-incomplete，而不能放宽读取校验。`skipped`、`invalid` 或 `launch-failed` outcome 也必须以同一 token/fence 提交；`storage` plan 的 launcher failure 只得到当前 token/fence 的 retryable acknowledgement，保留原 `storage-wait`，而 `duplicate`、`pre-spawn`、`admission` 的 definite failure 才由 TaskService 终态化。不得从 `Maintenance` receipt 取得 raw Task map，也不得重读 `status`、`phase`、`pending_launch`、`storage_wait`、`duplicate_wait`、Run artifact 或错误文本重新分类。`AdmissionRecoveryDescriptor` 只是 adapter 写入的私有 ingress 字节，单独的 descriptor 文件、kind/digest、mtime、目录或可读性均不授予恢复或 launch 权限。TaskService 在 admission WAL 内将其封为 `AdmissionDescriptorBinding`：`{descriptor_ref, TaskRef{task_id,task_dir,task_instance_id,task_registration_sequence}, source_fence{同一 TaskRef,run_id,sequence}, admission_receipt_id, admission_token, lane, operation}`；没有 source Run 时 `run_id=""`、`sequence=0` 必须显式持久化。binding 的 receipt/token 由这些 typed 字段确定，不能由正文、错误或时间生成。plan、ChatBridge artifact reader 与最终 Run claim 都要复验同一个 binding：Task ABA、descriptor body/ref、lane、operation、source fence、receipt 或 token 任一不一致即 fail closed，不能降级为 Task-root artifact 或重新选择 latest Run。普通请求和裸 replay 的 R1→R2 重签始终拒绝；唯一允许的 Rn→Rn+1 是 TaskService 已在同一 lifecycle lock 内复验 sealed `AdmissionRecoveryPlan` token、旧 binding 与当前 Task/Run 后，把该 binding 随 replacement `run_created` 原子推进到新 Run，adapter 不能调用或模拟这条 owner-only transition。历史 Chat Continue 的极窄 pre-version normalizer 也同样不是例外：它仅在 `runtime_launch_failed=true`、精确 `last_error_reason`、当前 scope 的 `*_degraded=true` 与带精确 path 的 typed degradation record、以及同一失败 Continue Run 的完整 artifacts 同时成立时生成 `storage-wait`；`launch_error` 仅为诊断文本，任何前缀、措辞或包含“low disk”的文案均不得选择 scope 或授权自动启动。该 typed record 也是 admission fingerprint 的一部分，记录替换后旧 plan 必须失效。任何 root/Task/Run artifact 的 corrupt、permission 或 I/O failure 都使整轮计划 unavailable，绝不能用可读前缀启动任务；计划在 ABA replacement 后的 outcome 或 Run claim 必须被 TaskService 拒绝且不得写 successor。

### 正交状态维度

不再用一个 `status`/`phase` 字符串同时表达执行、交付、恢复和清理。aggregate 至少保留下列正交维度：

| 维度 | 取值 | 含义 |
| --- | --- | --- |
| Task lifecycle | `accepted` / `running` / `finalizing` / `needs-attention` / `completed` / `cancelled` | 用户逻辑工作状态 |
| Run lifecycle | no Run / `starting` / `running` / `succeeded` / `failed` / `stopped` | 一次 Agent 执行世代 |
| Admission | none / pending / storage-wait / duplicate-wait / committed / failed | 新 Run 准入和 crash recovery |
| Process ownership | none / pre-spawn / live-owned / exit-observed / lost / unresolved | 能否启动、停止、恢复或清理 |
| Delivery | not-required / pending / delivered / failed / outcome-unknown | Provider/workflow/IM 写回事实 |
| Attention | none / requester-input / contributor-review / run-failed / timeout / recovery-required / projection-incomplete / operator-check | 需要谁做什么，不覆盖原始终态 |
| Workspace disposal | retained / scheduled / running / retrying / blocked-unknown / partial-exhausted / cleaned | Task 登记资源的独立处置进度 |
| Supersession | current / superseded | 历史故障是否已被明确后继 Task 收口 |
| Projection availability | ready / stale / unavailable / incomplete | 读模型是否可安全解释 |

`storage-wait`、`duplicate-wait` 和 `ci-wait` 是机器等待子状态，不创造第七种 Task lifecycle status。`workspace_disposal` 不改写 Task delivery outcome。`superseded` 是有证据的有效状态投影，不改写原始 Task 终态。

现有存储格式中的 `status=waiting` 是 legacy persistence encoding，不是 TaskView lifecycle。strict aggregate 只有在同时读到 typed admission reason 时才可将它归一为 `Task lifecycle=accepted + Admission=storage-wait|duplicate-wait|ci-wait + next_actor=machine + is_processing=true`；裸 `waiting` 不能决定 `status_group`。只有恢复证据不完整、自动重试耗尽或结果不确定时，才进入相应 typed attention，不得把普通机器等待投影为 needs-human。

已发布 v0.2.x 首次 Start 的版本 1 `pending_launch` 是明确的旧持久化合同，不具有 v2 admission journal。兼容读取必须同时验证完整 Task registration、匹配的 Start receipt、无 Run/进程 owner，以及该 lane 实际写出的原始入口文件。review 核对对象与提交；IM 核对原消息、接收目标及回复凭据；followup 使用 Task 内冻结的状态与原指令；workflow 保留原输入版本、业务 inputs 和 action grants；定时任务只恢复已经受理的工作。原始指令不能因 launcher 重构而被重建成另一项任务。typed 磁盘等待保留原 scope/path/门槛；重复任务等待独立保留旧 blocker 的 Task ID、路径和全局 registration sequence，即使磁盘故障覆盖显示 phase 也不能丢失该依赖。首次推进仍由 TaskService 校验原 Task generation 与密封输入，并用原 launcher 准备第一个 Run；不得据裸 `waiting`、展示字段或 live cache 重建请求。旧 ingress JSON 与 admission envelope 的排版差异不构成新的 payload，完整 JSON 值相等时保留原始文件字节，内容变化仍拒绝。

Delivery Metrics 的已迁移 pending Task 保留原随机 ID 和语义缓存键。禁用时不得恢复模型执行；已有精确历史结果时收敛等待而不创建 Run；普通刷新必须识别原 Task，不能另建固定 ID 的重复分析。已恢复 Run 的结果由普通分析完成路径保存，结果缓存与 Task lifecycle 不构成两个执行 owner。

IM 首次 Start 同样必须持久化 `chat` 准入描述符。其版本化 adapter input 在 TaskService 所有的准入记录内保存回复 token 和附件下载所需的私有 URL、解密材料；这些材料不得进入 TaskPayload、Run context、Agent prompt 或公开 Artifact。首次 Run 分配后才将仍有效的回复 token 绑定到该 exact Run 的私有回复凭据。等待期间凭据到期时保留原目标与过期事实，由原 connector 的 capability 决定能否主动发送，不延长凭据、不改变目的地。恢复必须经原 ChatBridge adapter 和完整准入 fence，保留原始消息、附件和 Agent 选择。

CLI/Status 提交的普通、定时和自定义任务也必须持久化首轮准入描述，保留原始指令、Agent、
Target 与触发原因。磁盘不足仍返回受理及等待原因；恢复由原入口重建执行配置，经 TaskService
的封存输入校验后重试同一个 Task。不得把等待当作启动失败，也不得更换自定义 job 或定时任务身份。

恢复器按 canonical Subject 选择 GitHub 或 GitLab 的原 launcher。等待期间 MR/PR 已 merged/closed 时，launcher 的成功 `Skipped` 必须经 TaskService 校验同一 admission 与 Task generation，执行现有 Cancel 事务并清除等待；Status 不再 processing，不伪造成功 Run，也不能下一轮继续重放。失效回调不得取消较新的 Task/Run。

历史数据里已持久化的 `monitor_status`、`next_action` 和其他派生字段只能由 legacy adapter 转换成上述事实，不能和 projector 并列为新的 authority。新 mutation 应持久化 typed reason/intent/receipt，`next_action`、`status_group`、`lifecycle_stage` 和 actions 统一由 TaskView 派生。

`zero Run` 的定义只有一个：当前 Task 的 strict `OperationalRuns` 集合为空。它不等于 `current_run_id` 为空，也不包括“R1 已完成、R2 admission 尚未 claim”的 Task；后者仍是 multi-Run Task，只能由 admission fence 携带 nullable exact prior Run 作为历史/兼容边界，绝不能进入 M04 或伪造一个零 Run Task。

pre-registry legacy root 兼容也不能绕过该定义。仅有 Task 根目录的 `task_id/run_id`、`status`、`monitor_status`、`phase`、`accepted_at/updated_at` 或其他 intake/display 字段，不足以创建 Operational Run；即使这些字符串写成 `active`、`failed` 或 `completed` 也仍是零 Run/不可证明数据。legacy root 只有在不存在现代 registration、Run pointer/registry 和 admission scaffold，且至少存在一项不可变或 Run-specific 执行证据（正 `sequence`、Agent identity、进程 identity、明确的 execution start/completion timestamp，或已经由 strict event reducer 建立的 Run）时才允许只读投影。缺少这项证据的 pre-registry `accepted/waiting` 必须保持空 Run history/Session，不能因为展示字符串或 Task id alias 被伪造成 legacy R1。

零 Run 不是一个可反复扩展的特殊状态，而是下表封闭的 admission × finalization 投影。任何生产写入者、strict aggregate、TaskView、Status/CLI consumer 和测试只能落在这些行；未命中时必须进入第 5 行，不能新增字符串分支：

| 行 | 唯一持久事实 | TaskView | Run / Session | 合法推进 |
| --- | --- | --- | --- | --- |
| Z1 ready | 已登记 Task，`accepted`，无 admission intent、无 Operational Run | `ready`、`is_processing=false`、`next_actor=agent` | 空 | 由 sealed Start/Continue admission claim 首个 Run，或 Cancel |
| Z2 machine admission wait | 同一 Task registration 的 durable `admission_pending`、storage-wait 或 duplicate-wait intent/receipt，严格无 Operational Run | `doing`、`is_processing=true`、`next_actor=machine` | 空 | TaskService 复验 admission token 后 claim 首个 Run，或 Cancel |
| Z3 definite pre-Run failure | 同一 Task registration、严格无 Operational Run 的 typed admission/launch-failure receipt | `needs-human`、typed `admission-failed|admission-launch-failed`、execution `not-created` | 空 | 只按其 closed inspection/action policy；不得归因给“最后一次 Run” |
| Z4 cancelled | 空 RunRef 的 `task_cancelled` intent + committed receipt | `completed`、`terminal_outcome=cancelled`、`finalization_kind=cancel` | 空 | 无执行推进；只允许正交 cleanup/disposal |
| Z5 incomplete | raw/missing/conflicting admission、registration、Run pointer、intent 或 receipt | `needs-human`、`projection-incomplete`、mutation disabled | 空或不可证明，均不得展示 | 修复持久事实后重投影；不得从 status/phase/reason 猜测 |

Z1 是冻结的兼容/迁移读分支，不是现代 writer 必须制造的中间态：Prompt admission producer 在同一 admission transaction 内完成 Task registration 并直接发布 Z2 `admission-pending` WAL。测试不得为了给 Z1 凑 producer 而手写一条现代 admission WAL；Z1 正例只验证一个完整 Task registration、strict zero Operational Runs 且没有等待/终态 claim 的既存 Task 如何被读取。任何自称 `admission-pending|storage-wait|duplicate-wait` 的状态都不再属于 Z1，必须有匹配 admission WAL 才是 Z2，否则就是 Z5；已发布 v0.2.x 的完整首次 Start admission-pending、磁盘等待或重复任务等待，必须一起核对 registration、Start receipt 和原始 ingress 后转换为当前 pending owner，不放宽现代 writer/reader。旧 pending claim 不能因格式发布而清空；无法安全转换的 lane、receipt 或 mixed-format owner 必须保留原始数据并阻止升级，不得当成 Z1 放行。

Provider ingress 的 `task-allocated-cancelled` 不是 Z6 或另一种 zero-Run subtype：它只是 provider effect ledger 对既有 Z4 的 typed receipt。Store 必须在同一 Task lifecycle lock 内先投影 strict aggregate，再验证 exact committed `FinalizationCancel`；空 fence 还必须是 `OperationalRuns=[] + empty RunRef`，带 Run fence 则必须精确匹配该 cancel receipt。pre-spawn cancellation 中 launcher 会在取消 preparation lease 后先返回，而 Cancel owner 随后才提交 finalization；adapter 可以只为同一 exact typed cancellation candidate 做有界等待并重复交给 Store 验证，不能把这个正常 transaction gap 立即误报为 outcome unknown。adapter 不得从 context/error 文案把 launch failure 猜成 cancellation：它只能提交 typed candidate；超过有界等待后两个 closed finalization 仍均不匹配时保留 effect outcome unknown、禁止重放。

零 Run admission WAL 的 `phase × admission_kind` 是写侧与 strict reader 共用的闭集：`accepted → prompt-start|source-start`；`admission-pending → prompt-start|source-start|registration|active-task-gate-start|duplicate-wait-resolved`；`storage-wait → storage-wait|registration`；`duplicate-wait → duplicate-wait|duplicate-wait-refresh|registration`；`admission-failed → admission-failed|intake-artifacts-invalid`。`active-task-gate-start` 只表示语义重复检查已经完成且允许继续 admission，绝不能表示存在 blocker；真正的 blocker 只能写成 `duplicate-wait + duplicate-wait`。kind 非空但不在对应集合中仍是非法：writer 必须在 event/state commit 前拒绝，历史 WAL reader 必须投影 Z5。带 source Run 的 WAL 不使用该零 Run 集合，S1 只允许 `admission-pending → pre-spawn-replay`，或 `storage-wait → pre-spawn-replay|legacy-chat-continue-storage-wait`；其他 phase/kind 组合一律为 S2。前者表示 exact terminal Rn 的 successor 准入已被 crash recovery 接管但尚未 claim Rn+1，后者表示同一 successor 因 typed capacity evidence 等待，二者都必须保留 R1..Rn history。

已有 Operational Run 的 successor admission 是另一条主干，绝不并入 Z1–Z5。Continue/重试可以先 claim R2，随后在 Agent spawn 前遇到 typed capacity failure；此时 R2 的 `run_launch_failed` terminal receipt 可以为 R3 发布 machine wait。历史兼容 normalizer 也可以用一条匹配 exact latest idle Run 的 admission WAL 表示同一主干。两种 authority 都必须绑定完整 Task registration、`current_run_id=""`、strict latest non-current 且 Run-local status 已终态的 Operational Run 及其正 sequence，并使 state cache 与 receipt 完整一致：

| 行 | 唯一持久事实 | TaskView | Run / Session | 合法推进 |
| --- | --- | --- | --- | --- |
| S1 successor machine wait | exact latest terminal idle Rn + 同 fence 的 typed `run_launch_failed` retry receipt，或显式 legacy-normalization admission WAL | `doing`、`is_processing=true`、`next_actor=machine` | 保留 R1..Rn；默认/显式 Session 仍只属于 exact selected Rn，不制造 Rn+1 | TaskService 复验 receipt 后 claim Rn+1 |
| S2 successor incomplete | 已有 R1..Rn，但 wait/failure 的 source Run、terminal state、Task registration、receipt/WAL 或 state cache 任一缺失、冲突或非 closed kind | `needs-human`、`projection-incomplete`、mutation disabled | 保留所有可证明历史；不可证明的 Run/Session 不展示 | 修复持久事实后重投影；不得从 status/phase/reason 猜测 |
| S3 successor definite failure | exact latest terminal idle Rn + 同 fence 的 typed successor-admission outcome receipt，且 state cache 已关闭 admission owner | `needs-human`、typed `successor-admission-failed`、`next_actor=operator` | 保留 R1..Rn 与 exact selected Rn Session；execution 不是 `not-created` | inspection、Cancel，或消费 exact Rn Continue fence 的人工重试；不得称“Run 前失败” |

S1 与 Z2 可以共享 `AdmissionWaitProjection` 的 wait kind，但 projection 必须携带是否 zero Run 以及 nullable exact source Run fence；consumer 不得因两者都显示 `storage-wait` 就合并 Run 数、Session 或 mutation。prior-Run admission WAL 只有 `legacy-chat-continue-storage-wait` 与 `pre-spawn-replay` 两个封闭 normalizer kind 可作为 S1 authority；任意 `storage`、`registration` 或其他自由字符串 WAL 都是 S2。recovery 产生的 S1 `run_launch_failed` 必须持久化 closed observation kind、原 typed command receipt，并让 strict reader从完整 Task/Run fence 重新派生 `recovery_observation_key` 与该 event 的 `recovery_receipt_id`；字段缺失、格式错误或任一摘要不一致均为 S2，两个任意非空字符串不能成为恢复授权。S3 的 receipt 必须明确表示它结算的是 Rn 之后的 admission owner，而不是改写 Rn 的 execution outcome；普通 `run_launch_failed`、raw `launch-failed` phase 或 recovery 错误文案不足以建立 S3。active duplicate gate 可把 S1 当机器 owner；service-maintenance 不得把 S1/S3 签成 `cancel-zero-run-admission`，在专用 successor settlement/cancel transaction 外只能 closed block。

`ci-wait` 明确不属于零 Run：它必须拥有 exact current Operational Run、sealed `CITargetClaim` 和 progress receipt，才可投影为 `doing/machine`。缺任一项即按 CI typed blocker 或 Z5 fail closed，不能退化成 Z2。

`sequence=0` 的 Z4 cancellation 参与 Task replay，但永远不能建立 `current_run_id`、`latest_run_id`、本 Task 的 Run history、Session 或 Artifact owner。同一 Target 的 inspection catalog 可以列出兄弟 Task 的 Run，但它与 `focus_task.run_history/run_count` 分离，每项保留自己的完整 owner TaskRef；零 Run focus Task 不默认选择兄弟 Run，只有用户显式选择完整 `run_ref` 后才能只读其 Session，且不能改变 focus Task 的 mutation owner。

`LaunchResult.Skipped` 只是 adapter transport observation，不是第三种零 Run 终态，也不能凭自由文本决定 lifecycle。若 Run claim 前的 sealed admission plan 复验后确认无需再执行（例如 provider Target 已终态），TaskService 必须把该 admission 结算为同一 exact Task 的 Cancel receipt，投影为 `completed/cancelled`；Z2 成为 Z4，S1 则保留 R1..Rn 的 Run/Session history 后取消 Task，绝不得把它改叫 zero Run。若 `PrepareRun` 在 Run claim 后返回 typed skip，则它属于该 exact Run 的正常 completion transaction，保留 Run history/Session 边界，并且 adapter 不得再次把它送入 pre-Run admission settlement。没有 sealed admission owner、closed skip disposition 或 exact completed Run receipt 的裸 `Skipped` 一律不能改变 Task 状态。

零 Run 与零 Workspace 完全正交：零 Run Task 可以已经登记 Workspace；零 Workspace Task 也可以已经有 canonical Run。前者只约束 Run/Session/browser child 是否存在，后者只说明 disposal batch 的 frozen member set 为空；两者都不能用来绕过完整 TaskRef、strict aggregate、external-resource registry、process/terminalization owner 和 aggregate certificate 校验。

MR/PR review 的完成发布是一条 lane-specific 主干，不与 generic workflow result 混合。TaskService 封存的 publication snapshot 必须同时绑定 exact Task/Run generation、canonical `subject`（含 provider authority/project/IID）、admitted commit、source/target branch、summary identity/digest、最终 bot marker 和实际 comment bytes/digest。provider 写回、live/backfill Followup、Task-root `comment.md`、Status Continue/retry 与 selected-Run result 都直接消费同一契约和快照字节：不得先把快照恢复进公开 Run Artifact 再重读，公开 `meta.json` / `run-context.json` 的删改也不得重定向 Target、commit、branch 或 comment prefix。实际 adapter authority 必须等于 sealed subject authority，配置漂移只能在 effect-start/provider 调用前阻断，不能把同 project/IID 发往另一 host。backfill planner 只能从 durable Task subject、exact terminal Run 与私有 publication contract 签发 typed plan；公开 summary 不存在时仍可恢复，私有快照不存在时则必须阻断。DeliveryRetry 必须同时读到 matching private completion-recovery contract 和已经存在的 publication snapshot，绝不能在 retry 中调用 prepare 从 public Artifact 重建。用户显式选择 R1 时 result Artifact 只能读取 R1 的快照，不能借 focus/latest R2。MR-review Run 中意外出现的 `workflow-input.json`、`workflow-result.json` 或 generic `result.json` 属于跨 lane evidence，不能改变 effect requirement、完成状态、Continue/retry policy 或结果摘要。

MR/PR review completion publication 必须先在 Task lifecycle lock 内证明 contract 的 canonical `subject` 与 durable `task-state.subject` 完全相同；Task subject 缺失/漂移或待发布字节不是合法 UTF-8，都必须在 snapshot、effect-start 和 provider call 前失败。

Generic workflow/post-check 的 `workflow-input.json + workflow-result.json` 也必须在 completion effect-start 前封存成 exact Task/Run 私有 contract snapshot；snapshot 至少绑定完整 Task registration、Run id/sequence、两份原始 bytes 的 digest、validated action identity set 与 `none|provider|workflow|provider+workflow` requirement。TaskService completion gate、provider/workflow executor、terminal Task projection、Source Start/Continue policy、Status/ActionPolicy、retry/recovery 和 selected-Run inspection 只能消费这份 snapshot 及其 matching effect receipts，不能在各自时点重新读取公开文件建立第二套 authority。需要 workflow contract 的 lane 缺任一输入、结果或 snapshot 必须在原 Run completion transaction 内 fail closed；不能先把 Task 标成 completed，再因后来补写一个 `workflow-result.json` 改成可 Start，也不能在 completed 后删除、替换公开 input/result 来发明或移除 effect requirement。公开 input/result 终态后只用于可见性与诊断；snapshot 缺失/损坏是 typed projection incomplete，不允许用当前文件内容回填。current scheduled taxonomy 的三个 providerless lane 仍按上文例外不创建也不消费该 snapshot。

### `EM-CMD-001` 命令、操作 owner 和 `EM-TRANSACTION-001` 事务顺序

| 命令 | owner | 是否新建 Run | 结果 |
| --- | --- | --- | --- |
| Start | 显式 Target/源 Task 只作为来源引用；新 Task 是结果 owner | 是，但可先出现合法零 Run admission | 新 Task、新 AgentConversation、首 Run |
| Continue(agent) | `focus_task` | 是 | 同 Task 下的后续 Run，可 resume 或新建 child conversation |
| Continue(recover) | `focus_task` | 解决丢失 owner 后再新建 | 同 Task 的 recovery Run |
| Continue(writeback/workflow-action) | `focus_task` | 否 | 重放已有 durable 投递内容/动作 |
| Cancel | `focus_task`；Status 还封存当时的 exact current Run 或 explicit zero-current-Run | 否 | 保留 Task/Run/Artifact 的 cancelled 终态；命令到达前出现 R2/R1 时拒绝旧操作 |
| Runtime completion | exact `{Task, Run, sequence, process generation}` | 否 | 只终态化匹配 Run，并在仍是 owner 时收敛 Task |
| Reconcile/recovery | durable intent 指向的 exact owner | 只有原命令定义需要时 | 推进已有事务，不创造新意图 |
| Workspace/resource cleanup | `focus_task` 的 typed registry | 否 | 只改变 disposal 维度 |

每个 mutation 的顺序固定为：

1. 解析 opaque/structural ref，拒绝歧义。
2. 在 Task lifecycle lock 下重读 strict aggregate 和 expected revision。
3. 纯决策生成 transition plan；未通过准入时不做副作用。
4. 在任何进程信号、Agent 启动、Provider 写回或删除之前持久化 exact intent/WAL。
5. Adapter 执行副作用，携带完整 Task registration、Run id/sequence 和 idempotency/effect id。
6. 持久化 acknowledged / rejected / outcome-unknown receipt。
7. 在同一 lock 下重新校验 owner 并提交 Task/Run 事实。
8. 发布 revision/invalidation；消费者重读 TaskView。

writeback retry 在第 2 步选定的 exact `TaskRunFence` 同时是 adapter 重建
`IssueRun`/`MRReviewRun` 的唯一 owner。`run-context.json` 是 Run-local 执行输入，
必须持久化 `{task_id,task_instance_id,task_registration_sequence,task_dir,run_id,
run_sequence,run_dir}` 完整 RunRef；历史 context 缺失 registration 字段时，retry
只能从已经 sealed 的 binding 补齐，且任何非空冲突值、sibling Run path 或 Task ABA
都必须拒绝。generic replay 为“尚未分配的新 Run”临时使用的 Task-root `run_dir`
不得进入 provider effect identity；在已经验证 `SourceRunDir` 等于 binding exact Run
后必须被同一 binding 替换。context、Task root、latest pointer 或公开 writeback audit
都不能自行授权重放。

零 Run admission 可以在 Task root 持久化一次 `run-context.json`，但该文件的 owner
始终是 pre-generation admission，不会在 R1 claim 后升级为 Run ArtifactScope，也不是
“当前/最近 Run context”的可变副本。R1..Rn 的 canonical context 必须由各自 exact
Run preparation/commit seam 写入 `runs/<run-id>/run-context.json`；后继 Run 缺少本地
context 时必须 fail closed 或从同一 Run 的 typed preparation input 构造，禁止回读
Task-root admission context、上一 Run 或 sibling Run。任一 Run commit 都不得覆写最初
的 Task-root admission bytes；因此 admission、R1、R2 三份 context 在路径、owner 与
生命周期上互相隔离。

崩溃发生在 4–7 任一点时，recovery 只按 durable intent/receipt 继续。已发出外部请求但无法证明结果时记为 `outcome-unknown`，禁止自动或 Continue 重发；不得把“再试一次”当成幂等。

IM 附件的明确大小或尺寸限制由发送适配器在上传前检查，原文件保留，并在原会话询问其他交付位置；TaskView 使用 `doing / waiting-input / user`，不产生管理员待办。附件发送已发起但超时未知时，不盲目重发附件，先在原会话发送送达确认问题。相同绑定中的明确“全部收到”或“全部没收到”经既有 sealed delivery attestation 提交，前者完成，后者通过 Continue(writeback) 重投同一 Run 尚未确认送达的附件。明确具名确认（“未收到的附件：a.txt、b.txt”或“只缺a.txt”）须由 exact Run 私有回执验证身份、原内容及已确认集合。名称须在完整附件集合中唯一，名单须为尚未确认集合的非空子集；只补名单中的文件，其余尚未确认文件按原用户明确的“只缺”裁定记为已收到。原用户裁定与发送端实际观测分别保留，不把裁定改写成平台ACK。未知、重名、不匹配或包含已有确认文件的名单只向原用户澄清并保持等待，不猜测补发范围。选择与确认事实由TaskService封存，跨重启及确定失败重试保持，不创建Run或Agent。普通新需求仍作为新指令 Continue。等待用户确认使用 `reply-awaiting-confirmation`，等待交付位置使用 `reply-attachment-limit`。其他未知外部 effect 继续保留既有人工裁定边界。

每次 writeback 实际发送前再次核验私有回执对应的历史 effect 身份及原内容摘要；内容改变时零发送，当前失败回执保留原摘要和已确认前缀。恢复原字节后可重试同一 Run，不把前缀归零后全量重发。身份或回执损坏明确拒绝，公开回复和文件不授予补发权限。

原用户确认已经封存且该Run的reply effect成功、Task完成时，迟到的明确确认不作为新工作Continue。具名确认须匹配该Run完整私有回执及原内容所证明的附件名；“只缺最后一步，请补充计算过程”等普通新要求仍是Continue。即使确认有新的原生消息ID，也只记录该消息的现有Task绑定并回复已处理说明，不改变Task/Run/effects或重新补发；显式Start/New命令保持各自语义。这个无副作用回执不授予新的裁定权限，不把其他成员的消息写成收件事实。

Runner 在 Agent 启动前发现磁盘余量不足，必须提交 typed `infrastructure / storage-wait`，保留未启动 Run 的失败历史，投影为 `doing / waiting-admission / machine`。周期恢复重新检查原 Task 和全部登记 Workspace 所在卷，容量满足后以原始输入、同一 Task 和 exact latest Run fence 提交 Continue；不按历史错误文案猜测自动恢复权限。启动失败的具体原因保存在该 Run 的 failure 中，Status 展示脱敏详情；零值启动时间表示“未启动”，不是公历日期。

Follow-up 忽略 Jarvis 自己的版本化评论标记，且 debounce 到期后在创建 Task 前重新读取对应 PR/MR 的实时状态。已合并或关闭的变更消费等待输入并跳过执行；实时状态不可取得时保留等待，不尝试准备已删除的分支。

### `EM-PROJECTION-001` / `EM-PROJECTION-002` 唯一 TaskView 投影

TaskView 必须一次产生以下字段，后续消费者只能筛选、分组和渲染：

- raw Task/Run lifecycle facts 与 projection revision；
- `status_group`: `ready` / `doing` / `needs-human` / `failed` / `completed` / `historical`；
- `terminal_outcome`: `none` / `completed` / `cancelled`。它区分成功交付与明确取消，不能从同为 `completed` 的 `status_group` 反推；安全 blocker、非完成终态和 outcome unknown 必须为 `none`；
- `supersession`: `current` / `superseded`。它只来自 `EM-SUPERSESSION-001` 的 strict lineage 结论；不完整投影或安全 blocker 必须保守为 `current`，不能以同 Target、名字或旧 monitor 文本猜测；
- `lifecycle_stage`、`blocker_kind`、`next_actor` 和 typed `next_action`；
- projector 内部先封存 closed `execution_state`、`admission_waiting`、`continue_exhausted` 和 typed blocker，再由这些同 revision 事实唯一生成 Start/Continue/Cancel `ActionPolicy`，包含 strategy、enabled 和 disabled reason；ActionPolicy 不得再次读取 raw `status`、`phase`、`authoritative_phase`、`monitor_status`、`next_action` 或错误文案形成第二套状态机。任何裸 Task map、缺少 sealed facts 的兼容调用都必须 fail closed；测试也必须先经过真实 TaskView projector，不能直接喂 raw map 给私有 policy helper；
- 当 `continue.strategy=recover` 时，projector 还必须在同一 revision 封存完整 `recovery_fence={task_id,task_dir,task_instance_id,task_registration_sequence,run_id,sequence,recovery_source}`。`recovery_source` 只可为 EM-RECOVERY-001 的 strict pre-reap current Rn 或 complete maintenance `process_reaped` receipt 所封存的 post-reap stopped Rn；恢复 adapter 只能消费这个封存 fence，绝不能从 raw Task 的 `current_run_id`、`latest_run_id`、`stopped_run_id` 或 lifecycle 文本重新选择 Run。fence/receipt 缺失、损坏或在 R1→R2/Task ABA 后失配必须 `409` fail closed；
- projector 还必须在同一 revision 封存 `completion_finalization`、`duration_ms` 和 `evidence_chain`：`statusTaskLifecycle` 是唯一可以把 raw phase/status/monitor、时间戳和 Run-private artifact evidence 归一为这三项事实的 owner。ActionPolicy、公开 Status transport、maintenance/retry adapter 和所有其他 consumer 只能读取这些 sealed fields，不能从 raw lifecycle 或 artifact 再次判定完成收尾、时长或证据链；
- projector 还必须封存 `writeback_state` 与 `writeback_summary`。它们唯一来自 selected exact Run 的 `StatusRunEffectProjection`：provider/workflow 只读 `.private/provider-action-*.json` 的完整 identity+digest+closed outcome，ChatBridge 只读 `.private/final-reply-receipt.json` 与完整 Task/Run fence 的 `chat_reply_delivery`，本地发布校验只读 `.private/publication-validation.json` 的完整 fence、artifact identity/digest 与 closed outcome。Status 不得重跑 comment contamination/publication guard 来制造 `agent-output-invalid`。`workflow-actions.json`、`provider-writeback.json`、`comment-post-*`、`reply-action.txt`、`reply-response.json` 和 `reply-error.json` 都只可作为 evidence display；缺 receipt、corrupt receipt、artifact 已变化、R1→R2 或 ABA 一律 `unknown`/fail-closed，绝不能由 audit 文案补成 done、failed、Continue 或 retry。ACK 但未完成本地 completion finalization 为 `pending`，不是 done；
- `is_processing`，由 active ownership/机器等待/finalizing 事实派生；
- diagnostics actions，与 ActionPolicy 使用同一个 sealed `blocker_attribution`。attribution 的 `availability` 只取 `ready|incomplete`；只有 `ready` 且其 fact/source/owner/revision 全部闭合时才可生成 diagnostic fact 或 mutating action；
- `workspace_disposal` 正交视图；
- immutable Target identity 的安全公开投影。

Target inbox、work item 和 recurring job history 都是 TaskView consumers：它们只可用同一 `status_group`、`terminal_outcome`、`supersession`、`is_processing`、typed lifecycle/blocker 和 canonical `primary_action` 进行筛选、分组或文案细化，不能再读取 `monitor_status`、`phase` 或错误字符串重新分类。Work item 的 live 事实只读取 related TaskView 的 `is_processing`。合法的 accepted、无 Run、无 admission wait Task 固定投影为 `status_group=ready`；strict aggregate 不能安全分类时固定投影为 `status_group=needs-human + blocker_kind=projection-incomplete + projection_availability=incomplete` 并禁用 mutation，不得把投影故障伪装成一个叫 `unclassified` 的业务状态，也不得回退到 raw Task 字符串。aggregate 整体 unavailable 时不产生普通 TaskView 行，由 Catalog 返回 unavailable；唯一非 aggregate 例外是 EM-ADMISSION-001 已封闭的 v0.2.32 zero-Run pre-registration history，它只产生无 mutation selector 的 `historical` 行。`workspace_disposal` 的 retry、blocked 或 partial-exhausted 只描述运维处置，绝不能把已经确定的 job delivery success/failure 改成另一种结果。

Work feed 中没有 TaskView owner 的外部 activity/webhook 行只能消费 adapter 声明的 closed event/disposition；Run 历史行只能消费 strict Run projection 的 exact status enum。`summary`、`reason`、错误文案和 action 名称仅供展示，不能通过 contains/prefix/suffix 再推 `failed`、`completed`、`needs-human` 或 `deduped`；未知外部事件枚举保留独立 `event_class=unclassified/run_observed`，不得写入或冒充 TaskView `status_group`。

投影优先级由结构事实决定，不做 `contains("failed")` 或文案匹配：

1. ambiguity / projection-incomplete / process-identity-unresolved / external outcome-unknown 先 fail closed；
2. durable terminalization intent 投影 `finalizing`；
3. 已提交 cancelled 且没有安全矛盾时投影 `terminal_outcome=cancelled`，历史 Artifact 不能复活它；
4. active Run、pre-spawn、storage/duplicate/CI 机器等待都属于 doing；
5. requester/contributor 输入与 review blocker 属于 needs-human；
6. Run failure、timeout、lost-run recovery 或可确定的 delivery failure 保留它们各自的 typed blocker；
7. 只有完成必需 delivery 且不再有 action owner 的 Task 进入 `status_group=completed` 且 `terminal_outcome=completed`；
8. superseded Task 保留原始失败事实，`supersession=superseded`；其 delivery group 可以是 completed，但它不能因此提升 Delivery Metrics 或掩盖安全 blocker。

`active`、`running`、`spawned`、`finalizing` 等 Run-owned 显示状态只有在 exact `current_run_id` 与 strict Run projection 同时存在时才可产生 `is_processing=true`；缺 owner 时投影 `run-ownership-missing`，不能用原始状态字符串补出一个正在运行的 Task。Agent lifecycle JSON 已存在但无法解析、status 不受支持、summary 为空或显式 schema version 不受支持时投影 `agent-output-invalid`；Artifact 不存在才投影 `missing-*`。终态提交尚未重放成功的 Task 投影 `blocker_kind=finalization-pending`，不得因为 Run 已终态就按 `run-failed` 显示：workflow/review/writeback 的 typed 事实仍在 effect receipt 上，投影必须按它给出 delivery blocker；只有 Run 自己记下的基础设施失败才由 `runFailureBlocker` 翻成 `persistence-failed` / `resource-cleanup-failed`。已证明 superseded 的 Task 对 delivery projection 是 completed，对 Workspace disposal 同样属于无 active owner 的终态；单项与批量 cleanup 不能因其原始失败状态而拒绝处置。

零 Run 的 definite admission/launch failure 在公开 evidence chain 中必须以 `intake` / `admission` 显示，并把 `execution` 标为 `not-created`（无 Run、无 Session）；不得因为原始 monitor 是 `needs-attention` 而显示 failed execution 或“上一个 Run”。

`Catalog` 中的 work item 只按 immutable Target identity 分组 TaskView。一个 work item 的 `is_processing` 等于所有 related TaskView 中 `is_processing=true` 的存在性，不受 primary Task 是否 completed 影响。work-item 列表、当前任务数和“当前工作”分区必须消费这一个事实。

Catalog 搜索先在未套 provider/user scope 的完整候选集中解析规范化 Task/Run identity：存在结构化精确命中时只能返回该 owner；若精确 owner 被 scope 排除则结果为空，绝不能用同前缀的兄弟 Task/Run 顶替。只有完整候选集中不存在精确 identity 时，才执行标题、Target 和 identity 前缀等模糊检索并保留全部合法候选。模糊检索是发现能力，不是改写 exact owner 的回退规则。

`Catalog` response 中 Task 列表、`counts`、Target inbox、work-items 和 related Tasks 必须携带/消费同一 canonical `task_view_revision`。该 revision 只能由 durable TaskView、maintenance projection 与聚合成员的规范化内容计算；`age_ms`、顶层或嵌套 `duration_ms`、`process_segments.duration_ms`、`wall_elapsed_ms`、`total_agent_duration_ms` 以及任何由 captured `now` 推进的 registry fingerprint 字段都必须先排除。Run registry fingerprint 只能依赖 immutable identity、durable registry/evidence 和 closed outcome，绝不能依赖查询时钟；否则没有业务变化也会持续发布新 revision，形成 SSE/页面刷新风暴。派生缓存不能仅凭自身 TTL 判断 fresh；缓存携带的 revision 与当前 Catalog revision 不相等时必须丢弃并从当前 Catalog 重建。只有请求携带的 expected revision 精确等于当前缓存 Catalog revision 时，Inspect mismatch 才能把该已证明过期的缓存失效；任意未知 revision 不得作为远程 cache flush 能力。`counts` 只能统计 TaskView 的 `ready|doing|needs-human|failed|completed|historical`；其中 `historical` 不计入 current/attention/completed，`all` 只是总数/筛选器，不是 Task 状态。counts 不能另按 raw `monitor_status` 计数，也不能把 `needs-attention` 重复叠加到 `failed`。cursor snapshot 同样排除上述 observation clock；只有 durable TaskView revision、聚合成员或持久事实变化才能使 cursor 失效。

`Inspect` 一次返回：

```text
focus_task             -> actions / Task files / Workspace / cleanup owner
related Task catalog   -> 同一不可变 Target 下的可证明 Task
Run choices            -> 上述 Task 的 strict Run records
selected_run           -> progress / Agent Session / Run logs / Run result
```

Inspect 是 request-local fresh projection，但不是不带父版本的第二套视图。Task、events、logs、progress、result、related Tasks 与 Artifact root/list/content 等所有由 Catalog 进入的 Inspect GET 都必须携带浏览器冻结的 `task_view_revision`；server 先重算同一 canonical revision，精确相等才返回，不相等统一返回 `409 task_view_revision_changed` 并回显 current revision。progress、related Tasks 和 Artifact 等有 JSON body 的 response 还必须回显同一 revision，浏览器再次核对后才可渲染。缺 query 只允许兼容非 Catalog 调用，不能被 status UI 用来降级；mismatch response、迟到的 200 response 和已过期 UI generation 都不得修改 DOM、selected Run、timer 或操作控件。只读 Inspect 遇到 `409` 时，浏览器必须先有界重读同一 Catalog，再以新 revision 重试同一输入；超过预算后保持未选择/不可操作并等待下一次显式刷新或 durable invalidation。mutation 一旦遇到 revision conflict 绝不能自动重放。

Run choice 的实际 value 使用 opaque `run_ref`；可见标签至少包含 lane/scope、sequence、短 Run id、状态和时间，保证重名 `task_id`/`run_id` 仍可区分。选中 sibling Task 的 Run 不改变 `focus_task`。

Task 诊断数字、处理问题列表和页内结论使用同一 TaskView revision 下 `next_actor=operator` 且 `primary_action.kind=api` 的可执行 mutation actions。只打开日志、Artifact 或详情的 `mode/link` action、普通诊断信息、`next_actor=none` 和 superseded 不计入待处理数。

每个可操作失败事实必须先获得稳定的 `diagnostic_fact_id`，其 identity 由 Task instance、exact Run/effect/receipt/evidence role 和事实 revision 构成；展示 kind、reason 文案、建议命令和发现它的 reader 不属于 identity。同一 durable receipt 或 evidence fact 即使同时被 Verify 和 Diagnose 观察到，也只能映射为一个 `diagnostic_fact_id`。Verify 与 Diagnose 只贡献结构校验、归因和 evidence，不能各自拥有一个 operator action；TaskView projector 合并同一 fact 后，再由同一 ActionPolicy 生成唯一 action。无法证明同源的事实保持分离并 fail closed，禁止用 kind 字符串或 reason 文案猜测去重。

### `EM-METRIC-001` 指标和可用性

TaskView 只描述当前保留 Task。本机累计活跃度是独立 MachineMetrics 投影：

| 指标 | 事实源 | 不能替代它的值 |
| --- | --- | --- |
| 历史接入受理记录 | work ledger 的 `kind=accepted` 累计数；当前 writer 必须绑定完整 Task registration，pre-current legacy 行可能缺少完整 Task identity | 当前 Task 目录数、历史 Run 数；legacy 行不能反查或计为 Task |
| 本机已记录任务运行 | work ledger `kind=started` 累计数 | 历史受理数、当前保留 Run 数 |
| 今日任务运行 | work ledger `kind=started` 按本机今日自然日归约 | 趋势数组的最后一项、Task state 更新时间 |
| 昨日任务运行 | work ledger `kind=started` 按本机昨日自然日归约 | 趋势数组的倒数第二项 |
| 自动修复交付漏斗 | 本机自动 post-check 工单的结构化 workflow 观察、实际 bugfix 子 Task 与托管平台核验的修复 MR/PR；按完整 provider subject 去重 | 账号提交总量、任务成功状态、issue Bug 标签、客户 outcome 自由文本 |
| 本机任务运行趋势 | work ledger `kind=started` 从首条记录日到今日按自然日归约 | SSE dashboard、固定滑动窗口 |
| 已完成运行耗时合计 | work ledger `kind=completed` 的 duration 累计 | 机器在线时间、当前保留 Run 耗时 |
| 平均任务处理时长、任务处理时长中位数及按 lane 拆分 | work ledger `kind=completed` 的有效运行耗时样本及各记录的 `detail.lane` | Task 总历时、当前运行耗时、当前保留任务的 lane 推测 |
| 日均（去异常） | 上述完整 `started` 日趋势使用声明的异常值规则归约 | 当前筛选窗口的普通日均 |
| 当前运行 Task | TaskView `is_processing` | work-item 数、PID 数、Task 目录数 |
| 当前运行 work item | 至少一个 related TaskView 正在处理 | primary Task 状态 |
| 存储保留记录 | retention/storage inventory | 历史受理或 Run 累计 |

MachineMetrics 每个 typed value 同时携带 `ready` / `empty` / `partial` / `stale` / `unavailable` 和显式 `as_of`。`ready`、`empty`、`partial` 和 `stale` 的 `as_of` 是最近一次成功观察时间；从未成功观察的 `unavailable` 使用 `as_of=null`，不能伪造当前时间。数值兼容字段只在 typed value 含已知 value 时返回数字，`unavailable` 时必须为 `null`，不得把未知编码成 0。`started` 累计数虽然可由完整趋势求和，仍是声明过的业务指标，不得因为可派生就从 API 或 UI 删除。`stale` 只能说“数据截至 as_of”，不得把旧最后两天冒充今日/昨日；`unavailable` 是未知，不是数字 0。MachineMetrics（包括 CPU、内存、磁盘和 task-store health）的实时观测只能改变 `server-view`/metrics 自身；在 durable TaskView 与 maintenance projection revision 不变时，绝不能改变 tasks SSE 的 hash/revision、发出 `task-view` invalidation 或促使 Task/系统设置界面重建。

已完成耗时只累加 ledger 中有效的非负 `runtime_duration_ms`。完整可读账本中部分完成记录缺少有效耗时（包括 Agent 启动前失败）时，已有有效耗时返回 `partial`、已知合计与当前 `as_of`，Status 以 `≥` 标明下限并解释缺口；不能用单条缺值抹去其他已记录耗时，也不能把缺值当成零补写。全部完成记录都缺少有效耗时才返回 `unavailable`；没有完成记录返回 `empty + 0`。该规则不放宽坏账本的完整读取要求。

平均任务处理时长与中位数以单次已结束 Run 为一个样本，使用同一 `kind=completed` 有效非负耗时，包括成功、失败、停止和取消，零耗时有效；进行中的 Run 和两次 Run 之间的等待不计入，Continue 生成的每次运行分别计样本。平均值是有效耗时之和除以样本数，中位数为排序后的中间值，偶数个样本取中间两值的平均值。总体与各 lane 分别返回有效样本数、缺失耗时数与可用性；部分耗时缺失时统计仅描述已知样本，不能使用累计合计的下限语义。没有完成记录为 `empty`，有完成记录但耗时均缺失为 `unavailable`，两者的平均值和中位数均为 null。所有 `unavailable` 的 `as_of` 为 null；完整可读账本保留已知数量，账本不能完整读取时数量也为 null、lane 列表为空。

每条新 `started` / `completed` 记录将 Task 的 lane 保存在 `detail.lane`，各 lane 按同一口径独立归约。历史完成记录缺少 lane 时保留明确的未知分组，不反查当前 Task 或从编号、名称、来源推测，不改写历史行；有效耗时仍参与总体统计，lane 缺失不单独降低总体耗时可用性。平均值、中位数和 lane 明细均为本机累计指标，不受 Task 记录清理、来源筛选、趋势日期范围和异常高峰开关影响，不剔除异常耗时。字段定义见 [运行耗时统计](status-api.md#运行耗时统计)。

WorkLedger 是 append-only JSONL 事实源。读取累计数、趋势、分页明细和执行 `AppendOnce` 去重时，必须在与 writer 相同的文件锁下读取完整 record boundary；任一非空坏 JSON、缺少 `kind` 的记录或未以换行结束的残缺尾记录，都表示账本不能完整归约，禁止静默跳过后发布 partial `ready`/`empty`。`Append`/`AppendOnce` 只有记录追加且 `file.Sync` 成功后才算 durable success；Status、receipt 和后续 projection 不能把尚在页缓存的字节视为已提交事实。没有经过校验的旧 rollup 时投影 `unavailable + as_of=null`；已有完整、校验通过的旧 rollup 时只能返回该 rollup 的 `stale + 原 as_of`，并给出不泄漏本机路径/原始数据的 integrity warning。`accepted` 累计 rollup 还必须绑定固定 source 和非公开 ledger path identity，并校验 value、as_of 与完整性摘要；只能在当前完整读成功后以读完时的服务器时间更新。坏账本也必须让 `AppendOnce` fail closed，避免因为读不到既有 `event_id` 而重复追加。

当前 writer 的 `kind=accepted` 只表示一个已认证 ingress delivery 已经形成带不可变 registration 的 Task，并被持久受理一次；provider transport intent/effect-start、HTTP acknowledgement、被忽略且未创建 Task 的 delivery 都不是 accepted。它不是 Status、TaskView、目录数量或一次 HTTP acknowledgement 的派生值：admission owner 必须在同一 Task admission transaction 中，先把带完整 Task registration 的 durable admission WAL 写入，再以该不可变 `{task_dir, task_id, task_instance_id, task_registration_sequence, ingress/evidence key}` 派生 stable work-ledger `event_id` 并 `AppendOnce`，最后投影 state。WAL 已落而 ledger/state 未落时，recovery 只能用 WAL 中保存的同一 receipt 重放 `AppendOnce` 和投影；ledger 写失败则 admission 保持未投影、等待同一 receipt repair，不能把 TaskView 或指标查询当作补记 authority。provider/IM delivery 使用 adapter 的 stable delivery UUID/effect id，并把 deployment-resolved shared work-ledger path 写入 Task admission receipt；任何 launched/waiting/allocated-failure/cancelled outcome 在结算 provider effect 前都必须从 exact Task state 复验该 receipt 的 admission key、evidence key、attempt、完整 Task registration、Target 和 ledger path 与当前 claim 全等。另一个真实合法 Task/Run 也不能结算当前 delivery。duplicate、restart 与 recovery 必须重放该路径，不能因为当前环境配置变化迁移历史事实。Status 手动 Start、从既有 Task 新建 Start、认证 loopback scheduler、custom-user job 与 delivery-metrics discovery 没有外部 delivery UUID 时，TaskService 新分配的 immutable Task registration 就是该 ingress 的 receipt identity。异步 dispatch 的成功、失败或结果未知分别记录独立的 dispatch/effect receipt，绝不能再次生成 `accepted`；因此重试同一 delivery、HTTP acknowledgement、冲突 admission 和 detached dispatch completion 都不能让历史受理数重复增加。

pre-current ledger 中已经存在的 `accepted` 行是不可变的 legacy 接入历史：它们可能把 Run ID 写入 `task_id`，也可能缺少 Task identity，甚至来自旧版尚未收紧的 transport 受理边界。累计指标保留这些 append-only 行，所以它只能称为“历史接入受理记录”，绝不能称作或反查为历史 Task 总数；legacy 行也不能取得 Task mutation、recovery、Target 聚合或 accepted 补写权限。升级不静默重写历史 ledger；只有升级后的新行适用上述完整 Task registration 合同。

managed Run 的 `started`、timeout/failed 和 completion 账本事件由 TaskService 在 exact Task/Run transition 被接受后写入；`event_id` 必须由 `{task_dir, task_id, task_instance_id, task_registration_sequence, run_id, run_sequence, transition}` 稳定派生并以 append-once 语义提交。账本的 `task_id` 永远保存 Task identity，Task registration 与 Run identity 分别保存在 detail；不得用 RunID 填充 TaskID，也不得由 Runner 和 TaskService 各写一次同一 transition。相同目录、TaskID、RunID 与 Run sequence 被新 Task registration 复用时不能与旧实例合并成同一 ledger receipt。

自动修复漏斗是只读业务观察，聚合 GitLab、GitHub、Jira、飞书项目、TAPD、禅道与云效已接入工单，不受页面来源筛选影响。workflow 通过独立 `metrics.issue_type` 与 `metrics.change_requests` 报告分类和本次修复链接；这些字段不授予动作或 lifecycle 权限，客户 `outcome` 继续不透明。实际 workflow.start 子 Task 与有效结果的观察使用完整 Task/Run generation 追加到既有 work ledger 的 `issue_funnel` 记录，不维护第二套任务状态机；普通 Task 清理保留这些记录。即时观察追加失败只记录警告，不改变 provider receipt 或业务完成状态；TaskService 的清理事务在固定 Task/Run 身份与生命周期锁内先向历史投影器补齐本地观察，追加失败不得删除源 Task/Run。清理重试只重放 append-once 观察，不执行 provider effect，不创建新 Run；dry-run 不执行历史写入。原工单以 provider、authority、project、kind、ID 的准入身份关联子 Task；修复独立以实际 GitLab MR / GitHub PR 身份核验，允许跨仓库、跨代码平台，不要求复制工单。历史入口按规范化工单身份合并平台留存的自动 post-check 回执与既有受理、执行台账（包括 Issue Hook 的 work_items URL），不运行分类 Agent。平台历史恢复独立发现入口，不能用本机保留的 issue 集合限制平台查询；明确的自动发布回执与绑定本 issue 的创建任务审计标记可证明受理，普通提及、其他 issue 的复制结论或独立 command 重跑不建立自动入口，独立 command 启动也不证明自动 bugfix 准入。历史结论支持已发布的 Markdown 加粗，只读取结论段；原工单可信自动执行后的明确 MR/PR 交付回执直接关联对应修复，背景引用仍不能证明交付。已发布 v1 存储的 Task 级 workflow 报告可在原始版本、注册身份、Task 级 handle 与原工单规范化身份和 URL 全部匹配时贡献只读历史观察；这不是现代 Run Artifact 根目录回退，不改变 Task/Run 投影或动作权限。已有有效 post-check 结果、已发布 v1 评论处置及 workflow.start 修复建议不依赖新增 metrics 字段。离线历史恢复工具可将已发布 Task 级报告的明确交付处置及实际修复关联规范化为既有台账观察；runtime 继续保持 outcome 不透明，不把 feature 链接或本地准备当作交付，也不参与动作授权。确已丢失的结果和修复链接显示证据缺口：受影响阶段的数量显示已证实下限，完整历史转化率保留未知；Status 可展示明确标注的已记录数量之比，未知的零值或零分母不显示为 0%。最后一层需要匹配身份的平台合并时间或带完整 authority 的平台合并回执，可复用本机保留的平台记录，不能从本地完成、approve 或账号提交总量推断。详细统计与可用性口径由 [Status API](status-api.md#自动修复交付漏斗) 维护。

### `EM-METRIC-002` Run runtime token usage receipt

runtime token usage 是 **exact Run 的可选观测指标**，不是 Task terminal outcome、Agent 日志解析结果或 MachineMetrics。`known` 仅可由该 Run 的 `.private/runtime-token-usage-receipt.json` 产生：receipt 必须是 adapter 从受信、版本化 upstream schema 的独立稳定 final usage event 持久化出的 typed `final_cumulative=true` snapshot，并同时回显完整 `{task_id, task_instance_id, task_registration_sequence, task_dir, run_id, run_sequence, agent, agent_conversation_id}`、稳定 adapter/receipt/event identity、观测时间、非负整数 usage map 和 usage 的 canonical SHA-256 digest。只提供 conversation/thread/session id、assistant item id、普通 terminal result id 或累计数字而没有独立 final usage event identity 的 adapter，必须保持 `unknown`。reader 先从 strict Run registry 取得 exact owner，再逐字段相等比较 receipt；目录存在、裸 Run ID、latest/current、Task root、sibling Run 或相同 agent 都不是替代 owner。

receipt 写入是 Run-local private artifact 的 append-once final transaction：同一规范化 receipt 可重放，不同 receipt、digest 冲突或同一 Run 的再次累计必须显式冲突，不能静默覆盖。adapter 只能在已拥有完整 Run fence 与 AgentConversation 的终态累计事实时调用该 writer；它不能从 stdout/stderr、result JSON、全局 home/session 文件、mtime 或扫描到的历史 transcript 补造 receipt。未接入 receipt 的 adapter 保持 `unknown`，不是零 token。

缺失、损坏、symlink、字段缺失、非 final、负数、digest 不匹配、foreign Task/registration/Run/agent/conversation、复制残留，以及 R1→R2 ABA（即使 task dir、TaskID 或 RunID 复用）都必须 fail closed：该 Run 是 `unknown`，多 Run 聚合只可为 `unknown` 或 `partial`，绝不可把别的 generation 的 usage 附着到它。读取该 artifact 的失败只改变 metrics 可用性，不得改变 Run/Task 状态、终态、重试、清理或 delivery 决策。

### 主干上的业务分支

下列不是十三套状态机，而是共享主干的入口、策略或消费者：

| 分支 | 主干责任 |
| --- | --- |
| Provider work-item intake | 认证、规范化 Target、去重，提交 Start |
| Provider command | 规范化 comment command，提交 Start/Continue，由 delivery Adapter 写回 |
| Review / follow-up | 为现有 Target 建 Task/Run，复用相同 completion 和 delivery transaction |
| ChatBridge / UVIM | 规范化 conversation Target，复用 Task/Run，IM reply 只是 delivery Adapter |
| Status / CLI lifecycle | 只提交 Start/Continue/Cancel Command，不直接改 state |
| Admission / duplicate / storage wait | 在首 Run 或后续 Run claim 前保存可重放 intent |
| Runner / AgentConversation | 执行 exact Run plan，返回 process observation/completion fact |
| Timeout / guardian / lost-run | 以 exact process identity 解决 owner，不自行改写 TaskView |
| Workflow / provider writeback | 执行带 effect id 的 intent，持久化 receipt 后由 aggregate 收敛 |
| Runtime failover | 在同 Task 中创建后续 AgentConversation/Run，不改写旧 Run |
| Workspace / external resource cleanup | 只按 typed registry 和 lease 处置，独立投影 disposal |
| Retention clean | 只消费 terminal + disposal-complete 凭证，不重新推导归属 |
| Status / work item / system operations / metrics | 消费 TaskView 或声明的 MachineMetrics，不建第二事实源 |

### 业务测试矩阵

`tests/execution-model-matrix.yaml` 是业务场景与实现、测试的对应目录，不是可执行测试或完成证明。M01–M37 是稳定业务场景族，不按当前函数、文件或一次缺陷编号增删；每行声明业务不变量、持久事实、canonical seam、最终消费者和禁止结果。测试必须观察真实生产事务和最终消费者的业务结果，并区分对应禁止结果；一个组合测试可以同时覆盖多个边界和场景，不要求拆成互不重用的测试。目录引用存在、静态检查通过或人工完成标签都不能替代实际测试结果。当前真实环境验收范围和缺口记录在 `internal/server/test_coverage_assets/scenarios.yaml`。

正向 lifecycle proof 只能经真实 `TaskService.Advance` 创建或改变 Task/Run，再经 strict aggregate、`TaskView`/`MachineMetrics` 和最终消费者观察结果；不得手写 Task/Run 状态或绕过 owner transaction。corruption、legacy、migration、ABA 和 parser rejection 只作为名称明确的负向输入，不能充当正向 seam/consumer proof。浏览器 mock 只能证明浏览器 reducer，不能证明 server projection 或 owner transaction。

测试框架、扫描器、fixture 组织和迁移清单不是业务模型的一部分。它们可以作为仓库工程手段，但不得反向增加状态、owner、协议或业务规则，也不得成为修改生产代码的理由。新增或修改逻辑必须先选择现有 M 行；确有新业务转换时先修改本模型与稳定矩阵，再修改实现和测试。

测试以 Work Module Interface 为主证明面，不再围绕每个 helper 生成一条只证明实现细节的测试。每个修复先选择能改变业务路径的维度：

| 维度 | 必须覆盖的等价类 |
| --- | --- |
| Command | Start；Continue agent/recover/writeback/workflow-action；Cancel；completion；reconcile；cleanup |
| Task lifecycle | accepted；running；finalizing；needs-attention；completed；cancelled |
| Run ownership | 零 Run；pre-spawn；exact current；terminal；multi-Run；corrupt/incomplete；display id 歧义 |
| Process evidence | 无 PID；exact live generation；已退出；PID 复用；guardian 未证明；timeout |
| Delivery | not-required；acknowledged；rejected；retryable failed；outcome-unknown；receipt persistence failure |
| Storage fault point | intent 前；intent 后；effect 前；effect 后/receipt 前；receipt 后/state 前；final state 后 |
| Concurrency | completion vs Cancel；Continue vs cleanup；recovery vs live watcher；R1 late completion vs R2；duplicate requests |
| Identity scope | 同 host/同 Target；不同 host/同 project+iid；缺 host；同 task id 不同实例；同 run id 不同 Task |
| Runtime receipt | exact closed adapter event；普通 exit；stdout/stderr 伪造 closed reason；模型分类器伪造；unknown schema；receipt persistence failure；R1 receipt 到达 R2 |
| CI target | exact MR；exact commit；同 project 错 MR/SHA；不同 project；不同 authority；issue/branch/legacy URL 无 claim；pipeline URL/ID 不匹配；Task/Run ABA |
| Projection consumer | Catalog count/list；Inspect/actions；Run selector/session；Task files；system diagnostics；CLI；SSE；metrics availability |
| Disposal | zero Run × zero/nonzero Workspace；Selected/Full；planned/running/receipt-only/retrying/blocked-unknown/partial-exhausted/cleaned；member success 不重做；Selected→Full 显式 supersession；state repair 与下一轮处置分离；external resource/browser failure |

不做全量笛卡尔积。共享 reducer/transaction 的转换在 Work Module 证明一次；只有入口重建、外部写回、会话 UX 或运输契约不同的 Adapter 才补专有证据。每个缺陷至少有一条“存储事实 -> strict aggregate -> TaskView -> 最后用户消费者”的组合回归，并断言错误结果没有出现。

### 模型闭集：投影、receipt 与 stale 的唯一解释

这一节把容易被不同读取者各自补全的边界封闭起来。它不是新的状态机；它规定前文正交事实进入 `TaskView`、`MachineMetrics` 与 Adapter 的唯一映射。任何未列出的枚举、缺字段、跨代际引用或来源冲突都必须进入 typed `projection-incomplete` blocker、`unknown` 事实，或 `stale` / `unavailable` 可用性，并禁用 mutation；不得以旧 `status`、页面缓存、目录、时间或文案猜测一个更乐观的值。

1. `ci-wait` 是 `Admission=ci-wait` 的机器等待，不是 Run 成功、失败或人工待办。managed CI wait 必须同时有 sealed `CITargetClaim`、完整 TaskRef 和 exact current Run fence；任一缺失、漂移、poll receipt 不匹配或 pipeline 越界都投影为 typed `ci-claim-invalid` / `ci-outcome-unknown`，并在 provider call 前 fail closed。合法 `ci-wait` 的唯一 TaskView 结果为 `status_group=doing`、`is_processing=true`、`next_actor=machine`；它不能借 `waiting` 文本建立。
2. `skipped` 是 exact effect receipt 的闭集 outcome，不是 absence 的同义词。只有 receipt 带完整 EffectRef（TaskRef、RunRef、lane、effect kind、attempt/receipt identity、payload digest）和 closed typed skip reason 时才可出现。`not-required` 只表示该 lane 没有 delivery obligation；`skipped` 只可在 effect policy 明确允许 skip 时映射为 TaskView `writeback_state=not-required`，否则 required effect 的 `skipped` 必须映射 `writeback_state=unknown` 并保留 blocker。`acknowledged` 还必须经过同一 Task finalization receipt 才映射 `done`；`failed`、`subject-not-found`、`outcome-unknown`、`invalid` 和 `unrecorded` 绝不能映射 `done`。
3. `status_group` 的闭集为 `ready` / `doing` / `needs-human` / `failed` / `completed` / `historical`。`ready` 只表示合法 accepted、无 Run、无 admission wait、`next_actor=agent` 且 `is_processing=false`；它不同于正在执行或机器等待的 `doing`。`historical` 只表示 EM-LEGACY-LANE-001 已封闭的退役 persisted identity，或 EM-ADMISSION-001 已封闭的 v0.2.32 zero-Run pre-registration history；两者都无 current execution、人类责任或完成声明。TaskView 无法安全分类不会再发明其他业务状态：可识别的当前 Task 固定得到 `needs-human + projection-incomplete + projection_availability=incomplete` 且无 mutating action；整个 aggregate 不可用则由 Catalog 返回 unavailable。Catalog counts、Target inbox、work item、系统设置和 SSE 对同一 revision 使用这套闭集；`all` 只允许作为总数或筛选器。
4. `completion_finalization` 必须携带 closed `finalization_kind`：`none` / `completion` / `cancel` / `launch-failure` / `writeback-retry`。它还必须携带 `state=none|pending|committed|failed|outcome-unknown`、完整 TaskRef、nullable exact RunRef 及 stable intent/receipt identity。空 RunRef 只有两个合法来源：零 Run cancel 明确使用 `run_id="",sequence=0`；`EM-ADMISSION-001` 的 definite zero-Run launch failure 必须由 TaskService typed launch-failure receipt 证明同一完整 Task registration、严格不存在 Operational Run、event/patch 均为空 RunRef。Run claim 前的 typed no-work/skip 必须归一化为前一种 Cancel；Run claim 后的 prepared skip 必须归一化为 exact Run completion，二者都不得新增 `launch-skipped` finalization kind。raw/untyped launch-failure、半空 RunRef、已有任一 Operational Run 或 Task ABA 一律不能产生 closed finalization。`finalizing` 只能由 `state=pending` 产生；任何读取者都不得根据 `phase`、error 文本或已写的 result Artifact 重建 kind 或 state。pre-registration 状态中的 raw `completion-finalizing`、`cancelling`、`launch-failure-finalizing` 没有稳定 Task/Run owner，固定投影 `finalization_kind=none,state=none`；若它仍声称占用 Run，则由 TaskView 单独投影 `run-ownership-missing/needs-human`，绝不能计入 doing。exact committed Run 的 `status/phase=stopped` 是 `run-stopped` 人工续办事实，不进入 completed/writeback 分支：TaskView 固定保持 `status_group=needs-human`、`terminal_outcome=none`，且 finalization RunRef 必须与该 stopped Run 精确相等；pending、failed 和 outcome-unknown finalization 仍按各自更高优先级投影。
5. TaskView 是 closed record，而非 `map` 的可选字段集合：`task_view_revision`、TaskRef、`status_group`、`terminal_outcome`、`supersession`、`lifecycle_stage`、`execution_state`、`admission_waiting`、`finalization_kind`、`completion_finalization_state`、`writeback_state`、`blocker_kind`、`blocker_attribution`、`next_actor`、canonical ActionPolicy、`is_processing`、diagnostic facts、workspace disposal policy 和 projection availability 必须同一 revision 一次封存。唯一缺少 TaskRef 的 closed row 是上述 `pre-registration-retained` 历史投影；它必须同时缺少 `lookup_id`、Run/Workspace/effect owner 和 mutation action selector，不能进入 lifecycle consumer。公开 transport、CLI、Status handler、maintenance 和 browser 只能消费这些 closed fields；缺一个 required sealed field 时该读模型为 `incomplete`，而不是允许消费者从 raw Task 续算。
6. required effect 的 `outcome-unknown` 是 completion-finalization 阶段的安全 blocker，优先于 Run success、旧 delivery success、supersession 显示和 disposal 状态；它固定 `terminal_outcome=none`、`writeback_state=unknown`、typed `inspect-*` policy，且禁止自动重放。未进入 completion-finalization、取消、accepted 或 active Task 的 future effect 缺失不构成 blocker，不能禁用其合法 Start/Continue/Cancel。
7. 所有可持久化或可运输 owner reference 都是 closed structural ref：`TaskRef={task_dir,task_id,task_instance_id,task_registration_sequence}`；`RunRef={TaskRef,run_id,sequence,run_dir}`（零 Run 明确为空 RunRef）；`EffectRef={RunRef,lane,effect_kind,attempt_id,receipt_id,payload_digest}`；Workspace/disposal ref 还带 `workspace_id,workspace_registry_revision,round_id`。Target binding、lineage、admission/recovery plan、conversation、session、receipt、cache 和 ActionPolicy 只能携带这些完整 ref 或一个 opaque capability；裸 id、路径、latest/current pointer、mtime 和 display label 不是 owner ref。
8. `stale` 是有上一次已验证 snapshot 的只读可用性，不是仍可 mutation 的“差不多正确”。TaskView/Catalog revision、TaskRef、RunRef、EffectRef 或 projection availability 任一与当前 strict aggregate 不相等时，Inspect/mutation 必须返回 stale conflict 并要求重新读取；客户端只可保留其展示状态，不能替换 selected Run、DOM 操作性状态或提交旧 action。只有 MachineMetrics 允许返回上次完整 snapshot 的 `stale + 原 as_of`；没有经过完整验证的值只能是 `unavailable + as_of=null`。
9. 每个 TaskView blocker 必须有 typed `blocker_attribution={availability,fact_id,owner_kind,owner_ref,source_kind,source_receipt_revision}`。`availability` 只取 `ready|incomplete`，`owner_kind` 只取 `task|run|effect|process|workspace|maintenance`；只有 `availability=ready` 且其 fact、owner、source 与 receipt revision 全部闭合时才可授权一个 diagnostic/action。`blocker_kind`、展示 reason、建议动作和 reader 名称不能代替归因；同一 attribution 只生成一个 diagnostic/action。归因不完整固定使 TaskView `projection_availability=incomplete`、`status_group=needs-human` 并禁用全部 mutation。System Operations 必须把这一批 snapshot 标成 `availability=incomplete`、报告 `incomplete_task_count`，并令权威 `issue_count=null`；它可以继续展示已经闭合的只读 action，但不得把缺归因的 Task 静默丢弃后显示“零问题/无需处理”。
10. supersession 的 truth row 只有一行：完整、当前、同 subject 的 predecessor TaskRef 与 successor TaskRef 由 sealed lineage receipt 相连，且 successor `terminal_outcome=completed`、必需 delivery 已完成、无 finalization/effect safety blocker时，predecessor 才得到 `supersession=superseded`、`status_group=completed`、`terminal_outcome=none`、`next_actor=none`、`blocker_kind=superseded`。它保留 predecessor 原始 Run/delivery failure 供审计，不把 predecessor 计为成功 delivery、成功 Run 或 Delivery Metrics；任何不完整/陈旧 lineage、后继部分完成、未知 receipt 或 blocker 都是 `supersession=current`。

因此，模型矩阵中的每一行都必须同时声明持久事实、canonical seam、最终消费者和禁止结果；一条只断言 helper 或只断言 raw state 的测试不构成闭环证据。

## 三个生命周期操作

jarvis-box 只有三个会改变 Task lifecycle 的产品操作：

| 操作 | Status API | CLI | 结果 |
| --- | --- | --- | --- |
| `Start` | `POST /status/api/tasks/{id}/start` | `tasks start <id>` | 创建新 Task、新 AgentConversation 和首个 Run。可以引用旧 Task，但不改写旧 Task。 |
| `Continue` | `POST /status/api/tasks/{id}/continue` | `tasks continue <id> [...]` | 延续同一 Task。服务端按状态选择 agent continuation、lost-Run recovery 或 delivery retry。 |
| `Cancel` | `POST /status/api/tasks/{id}/cancel` | `tasks cancel <id>` | 终结 Task；存在 active Run 时先解决其进程 ownership。 |

Inspect、list、verify、reap 和 clean 是只读或维护操作，不属于 Task lifecycle。Native resume、cross-agent child conversation、Stop Run、Recover Lost Run 和 Retry Writeback 都是 `Continue`/`Cancel` 的内部策略或底层原语，不是额外的产品操作。

异常不会创建第四种 lifecycle 操作，也不应通过 Start 伪装成恢复：需要保留原 Task 时使用 Continue，需要放弃原 Task 时使用 Cancel。Start 只表达创建一个不同的新 Task。

## Provider lane ownership

`issue-post-check` 必须向原 subject 回写可读结论，包括证据不足、需要补充输入和跳过复核的结论。Agent 在 `summary` 返回提单人可读的结论，完整正文可写入 `comment.md`。外部回写开启且 Agent 未声明 `provider.comment.create` 时，finalizer 优先使用非空 `comment.md`；正文缺失或为空时将 `summary` 原子、持久化保存为正文，并补齐指向 exact input subject 的唯一评论动作。该动作先于其他已声明动作，进入同一 schema/grant、capability、正文发布校验和 Run 私有回执链路。Task 仅在必需投递有成功回执后完成；缺少动作不要求人工 Continue 或再次调用 Agent。Agent 原始结果保留，实际动作记录在执行审计中。标签、状态和后续 workflow 仍需显式声明，不从 customer outcome 推测。普通 workflow 的空动作、关闭外部回写、实际投递失败与结果未知的处理规则保持不变；不能用公开 action audit 授权重发。

GitHub、GitLab、Jira、飞书项目、TAPD 与云效 webhook 在鉴权和 JSON 校验后，先持久化运输收据，再返回 202；Task/Run 准入与副作用由后台 dispatcher 继续交给现有 TaskService owner。运输收据的 pending/dispatching/completed/failed/outcome_unknown 只描述投递责任，不是 Task/Run lifecycle，不生成新的业务操作或投影。重启只继续 pending，派发结果未知时禁止自动重放。HTTP 202 不等于 Task 已创建、Run 已启动或业务成功；最终事实仍由 TaskView、exact Run receipt 与 work ledger 提供。详见[Webhook 受理与恢复](storage-model.md#webhook-受理与恢复)。

`EM-ADAPTER-001` 的认证在任何 Task admission 之前完成。Jira Cloud 的管理 webhook
使用原始请求体与 `X-Hub-Signature` 的 HMAC-SHA256 签名；配置自定义 token 请求头的集成
仅在没有签名时走 token 认证。无效签名不得回退到 token 或创建 Task。只读服务同样不受理
任务，只为已认证事件记录拒绝结果。认证格式属于 Provider Adapter，不增加 Task/Run 状态。

| 组件 | 唯一职责 | 不负责 |
| --- | --- | --- |
| `IssueLauncher` | 创建类事件的 post-check 与客户 workflow contract 执行 | `@jarvis` 评论命令、直接 provider mutation |
| `CommandLauncher` | 已接入平台评论中显式命令的 Agent 执行；保留平台主体及版本，产出 `comment.md` | 伪造 workflow type、向 Agent 暴露评论 endpoint、直接 provider mutation |
| `ProviderActionExecutor` | 保证 post-check 结论投递，校验并执行 command 与 workflow-result 中声明的其他 provider action，持久化 response/action/audit | 命令解释、客户 workflow 选择、Agent 生命周期 |

`@jarvis` 只是各 provider adapter 的命令匹配入口。命中后直接进入 `jarvis-command` lane，不生成 workflow input，也不把命令包装成一个虚构的 workflow type。GitLab、GitHub、Jira 和默认 Meegle backend 都向 command Agent 提供 provider CLI 与稳定 subject identity，并通过同一 read contract 要求其在执行前读取实时正文、完整评论历史和附件清单；默认 Meegle post-check Agent 同样获得只用于当前 Feishu Project Run 的 CLI 能力，并必须刷新项、全量评论、所需附件、关系和关联工作项。Feishu Project plugin 是唯一的服务端预取分支，Agent 只读取 `issue.json` 与 `notes.json`，plugin credential 不越过服务边界。所有 command 和 post-check 的原 subject 写回都由 `ProviderActionExecutor` 执行。GitLab MR 与 GitHub PR follow-up 共用 provider-neutral dispatcher 和状态机，provider adapter 只归一化事件并实现实时读取/状态评论；command mention 永远优先于普通评论 follow-up。MR/PR review 与 follow-up 保留自己的交付器，但消费同一个全局回写开关；review 写回是 append-only，follow-up 状态评论才按 marker 更新同一条 provider 评论。每次 provider/workflow effect 先为 exact Run 写 immutable intent（Run-private effect 使用私有目录；follow-up status 使用绑定完整 Task/Run fence 的 durable cache intent），再在 Task lifecycle/cache lock 外执行 effect，最后写 acknowledged、definite failure 或 outcome-unknown receipt并复验 owner后投影；`workflow-actions.json`、`comment-post-action.txt`、`comment-post-response.json` 和 `followup-enqueue-result.json` 只是在该 Run 内展示或恢复既有结果。不得再为这些审计 append Task event；共享 WorkLedger 的失败同样不得改变 receipt、触发重发或派生 Task lifecycle。Provider subject-not-found 只能由同一 CLI 身份的双探针闭合：exact subject API 返回结构化 HTTP `404`，且其父 project/repository API 返回结构化 HTTP `2xx`。CLI stderr、error text、裸 JSON 或未绑定探针状态的“reachable”布尔值都不能授权取消；父级 `401/403/404` 或状态未知仍是普通 writeback failure。TaskService 将闭合结果写成 `cancellation_effect_kind=provider-subject-not-found`，只有此 closed field 才可授权即时 workspace disposal，`cancel_reason` 仅展示。IM conversation reply 仍由 ChatBridge reply owner 管理，不属于“原 provider subject 回写”开关的范围。

Command 与 workflow 评论由 `ProviderActionExecutor` 在发送前统一处理可识别的本机路径：行内 Markdown 本机链接降为可读标签，裸路径降为文件名并保留行号；不生成未经验证的远端链接。处理范围是 macOS 标准 Users 用户目录树中的路径、包含 Jarvis Box 隐藏运行目录的绝对路径及对应的本机文件链接。HTTP(S) 链接、仓库相对引用和其余说明保持原文。原始 Agent Artifact 保留，基于文件发送的 provider 必须读取与校验后正文一致的派生文件。转换后仍执行 publication guard；串入的命令输出、内部运行字段及无法消除的本机信息继续拒绝发送。可转换路径本身不要求 Agent 重生成或 failover，首次投递和重试使用同一规则。Workflow 的全部评论正文在首个外部动作前完成本地预检，发送边界再次核验；在尚无外部动作时拒绝属于确定的 `local-preflight-rejected / not-attempted`，修正后只重试原 Run 交付，不要求操作员核实是否送达。已有外部动作执行后的不确定失败仍保留 `outcome-unknown`，不得据后续正文错误重放整个动作集。

能力矩阵是路由和写回校验的单一语义源；不从 provider 名称推导隐含组合：

| Provider | work-item.create | comment.command | subject.lifecycle | comment.write | repo association | repo host | change review | follow-up | issue labels/status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GitLab | 是 | 是 | 是 | 是 | 是 | 是 | 是 | 是 | 是 |
| GitHub | 是 | 是 | 是 | 是 | 是 | 是 | 是 | 是 | 否 |
| Jira | 是 | 是 | 是 | 是 | 是 | 否 | 否 | 否 | 否 |
| 飞书项目 | 是 | 是 | 是 | 是 | 是 | 否 | 否 | 否 | 否 |
| TAPD / 禅道 | 是 | 是 | 是 | 是 | 是 | 否 | 否 | 否 | 否 |
| 云效 Projex | API 适配 | API 适配 | API 适配 | 是 | 是 | 否 | 否 | 否 | 否 |
| 云效 Codeup | 否 | 是 | 是 | 是 | 否 | 是 | 否 | 否 | 否 |

能力表描述接收端的业务能力，不表示平台原生事件已经接通或真实链路已通过验收。Projex 原生自动触发尚未完成，标准自动化模板没有新增评论回调；API 事件回放不能证明在平台创建工作项或发表评论会自动派单。Codeup 的指令与终结事件适用于 MR/commit 的各自身份，自动 review/followup 尚未接入。Codeup 新 MR 评论的准入在现有 admission 事务中有界读取权威状态，已关闭/合并以既有 skipped outcome 收尾，不创建 Task/Run；未知状态或身份不符不能启动，不回退到 webhook 状态。已有回执的重复评论不再次读取平台；当前状态检查不得覆盖触发评论的 patchset/SHA，commit 不套 MR 终态规则。各平台的事件、上下文和认证差异分别遵循其接入文档，不由同类平台成功推定可用。

禅道使用原生 Basic Auth Webhook，并在准入前通过 API 重读真实对象与 action。`bug`、`story`、`task`、`case` 是独立 Subject kind，同号不合并；范围分别使用 `product:<id>` 或任务的 `execution:<id>`。只有 `opened` 触发预检，`commented` 中的明确命令进入 command lane；可实时验证的 `closed`/`canceled` 只取消同一完整 Subject。对象已删除、不可读取或 action 不匹配时拒绝推断取消。原生评论回写保留状态，备注只显示回复正文；服务端持久化隐藏的 Run 标记用于去重和阻止自身评论再次触发。完整历史、附件和官方 CLI 的版本约束见[禅道接入](integrations/zentao.md)。

各 adapter 先把原始事件精确分类为 `work-item.created`、`work-item.updated`、`comment.created`、`change.updated`、`review.created` 或 `subject.terminal`，再按 capability 路由。自动 post-check 只消费 `work-item.created`；后续更新不会因为字符串包含 `created` 而误触发。一个 Jira/飞书/GitLab/GitHub work item 可以关联零个、一个或多个 GitLab/GitHub 仓库，包括两种 repository host 同时关联；关联不等于二选一路由。

## Target

`Target` 是外部工作身份和可见性边界。

示例：

- GitLab issue、merge request、commit、note
- Jira issue
- IM conversation，包含私信、群组和频道
- status 手动 Task
- JARVIS 记忆整理、每日复盘或经验积累产生的可见工作

字段：

- `id`
- `key`
- `provider`
- `authority`: provider host，或 IM connector/account 等稳定 authority
- `kind`
- `title`
- `visibility`
- `current_task_id`
- `created_at`
- `updated_at`

规则：

- `key` 必须由 provider + authority + kind + provider resource identity 稳定构造。authority 缺失的历史 Task 只能以 unknown Target 单 Task 查看，不得参与跨 Task 聚合。
- IM Target key 使用 provider + connector + conversation id。
- IM `/start <任务描述>` 创建新的 Task 和 AgentConversation，并在 **TaskService 已持久化准入 outcome** 后提交 Target 默认 Task；它不停止该 Target 已经运行的其他 Task。空 `/start` 不改变绑定。
- Target 的 current binding 与 message-to-Task index 都保存完整结构 Task ref `{task_id, task_dir, task_instance_id, task_registration_sequence}`，不保存 Run id、Run 状态或 runtime session。读者每次使用时都必须从 `task-state.json` 和 task registry 复核这四项；Task ID、目录或任一 registration 不匹配即为 stale binding，必须 fail closed，不能按同名目录、最新 Run 或历史 Artifact 继续。
- ChatBridge 收到 `/start`、`/new <任务描述>`、普通新任务或追加消息时，先以稳定入站消息 identity 持久化不可解析的 binding intent；该 intent 只可用于恢复其自身，不能被 Resolve、Continue、Cancel 或 reply 路由消费。`RunRequest.AdmissionRecovery` 必须携带同一 intent，TaskService 成功登记 Task（包括零 Run waiting）后，adapter 才以 exact Task ref 提交 message/current binding outcome。commit 前必须同时证明当前 registration 与同一完整 descriptor binding：Start/零 Run 由 `task_admission_committed.admission_snapshot` 持久化显式 zero-Run source；Continue 不提前覆盖上一终态，上一 Run 只作为独立 continuation input fence，descriptor binding 则在同一 Task lifecycle lock 内直接绑定新分配 Run，并把 binding 与重复的 `pending_launch.source_run_id/source_run_sequence` 随 `run_created` claim 原子写入。恢复创建 replacement Run 时只能由已复验的 sealed plan 把旧 binding 原子推进到该 replacement generation。PrepareRun 只消费这份已 claim 的完整 binding；Task 私有目录中单独遗留的 descriptor 不是 outcome。进程在 intent 与 outcome/commit 之间退出时，后续请求只能从这份 descriptor-matched TaskService outcome 补齐 commit；没有该证明、registration 或 descriptor 不匹配时保留/丢弃 intent，绝不选择 Task。
- `/new` 无任务文本提交 Target selection reset tombstone；`/new <任务描述>` 只先记录 reset-and-select intent，不能在新 Task 准入之前删除旧 current binding。current binding 与 reset 使用同一稳定 `{selection time, inbound message identity}` 排序；因此旧消息晚完成时不能覆盖较新的 `/new`，并发新消息的选择可重放且确定。
- IM message-to-Task index 用于引用消息反查，不改变默认 Task。解析优先级为显式 id、引用、默认 Task；引用按 parent、root、thread 的顺序查找，缺省或未命中时查下一项，重复消息 id 只查一次。每条命中的候选都执行完整 TaskRef 复核后才可继续；身份冲突不得跳过后回退。
- 不创建 Run 的控制命令（取消、空 `/new`、空 `/start`、未知及已移除命令）在选择 Task、修改绑定或回复前，以同一 Target/message identity 在既有消息索引原子登记 `control_claim=true`；四项 TaskRef 必须全空，引用解析跳过此类记录。旧记录缺少该可选标志时仍按原 Task 消息合同读取。claim 只证明消息已消费，不证明动作完成或回执送达；即使执行或回复中断，重投也不得重新选择后来的默认 Task 或非终态集合，不复用一次性回复凭据。用户可查看实际任务状态后提交新的命令；此合同不承诺崩溃时动作与回执的 exactly-once 完成。
- 入站 sender/conversation ACL 与引用选择分别校验。未授权发送人拒绝受理；同一群内已授权成员共享该 IM Target，不额外产生按 Task 作者隔离的权限。普通消息的外 Target 或未知消息 id 在当前 Target 引用索引中未命中时，不授予外部 Task 或回复凭据的权限；合法当前普通输入仍按当前 Target 默认 Task 继续，无默认时按新任务处理。已命中 binding 但 TaskRef/Target 冲突属于身份错误，必须拒绝，不能回退默认 Task 掩盖冲突。裸 `/cancel` 仅在未携带引用时使用默认 Task；携带引用但未命中本 Target 时说明无法定位并拒绝取消。显式 `/cancel <run-id>` 仍只操作本 Target 中该 Run 所属 Task，不能回退默认 Task。
- Task/Run completion 只能更新所属 Task/Run，不能更新 Target 默认 Task。
- 旧 Task 仍可通过 Task id 在 `/status` 中访问和继续。
- Target 不存储 provider reply token、resume handle 或 raw inbound payload。
- ChatBridge 的 session progress、stale outbox、recovery receipt、delivery receipt 等所有 Task event readers 都以完整 TaskRef 和 exact `{run_id, sequence}` 过滤后才可读取或投影。目录、Task ID、Run ID、Run sequence 即使全部复用，也不能让 predecessor 的 event、outbox 或 delivery receipt 影响 successor。

## Task

`Task` 是用户关心的逻辑工作。

字段：

- `id`
- `target_id`
- `title`
- `status`: `accepted`、`running`、`finalizing`、`needs-attention`、`completed`、`cancelled`
- `current_run_id`
- `latest_run_id`
- `current_agent_conversation_id`
- `task_instance_id`: Task 创建时生成的随机不可变实例标识
- `task_registration_sequence`: Task 创建时从全局登记账本取得的递增序号
- `subject`: 创建时登记的 provider、authority/host、kind、project、number；仅外部对象触发的 Task 存在
- `issue_or_mr`: 由 admission 从同一 Target 生成的展示 URL；它不是 identity，也不由 Runner observation 更新
- `workspaces[]`
- `workspace_registry_revision`: 每次登记表内容变更单调递增；它和不可变 Task registration 一起构成 Workspace disposal 的 compare-and-swap fence
- `terminalization_intent`: 仅在成功/取消终态副作用尚未全部提交时存在的 durable recovery record；completion intent 同时保存不可变 Task/Run identity、完整 Run 终态 patch 与 Task 终态 patch；post-registration skip 还显式保存 skip reason，并关闭本次 Run 的 provider writeback 要求
- `created_by`
- `updated_by`
- `created_at`
- `updated_at`

规则：

- Task status 描述逻辑工作，不描述 pid。
- `subject` 是 immutable canonical identity；外部 URL、Artifact、分支名和目录名都不能反推或改绑它。
- Runner 的 capture/spawn/runtime/completion observation 只拥有 Run/process fact；即使 observation 省略或携带不同 URL，也不得清空或替换 Task 已登记的 `subject` / `issue_or_mr`。
- Task 可以在用户继续时从 `completed` 或 `needs-attention` 进入 `running`。
- `finalizing` 不是可 Continue 状态；服务先按 intent 自动收敛，明确缺少 provider evidence 时转为 `needs-attention`。
- Task 继续必须创建新的 Run。
- Task 不复活旧 Run。
- `current_run_id` / `latest_run_id` 是 Task 投影缓存，不是 Artifact 或历史所有权。生命周期仍阻塞时，`current_run_id` 只有在它也是完整 Operational registry 的最高正 sequence 时才是 active owner；若 registry 已有更高 generation，旧 current 与单调 Run 世代冲突，整个 strict projection fail closed。Task 空闲后，完整 Operational Run registry / event ledger 中最高正 sequence 的 Run 是 delivery generation。任何会启动、继续、回写、恢复、清理、删除或宣称 Operational history 完整的路径都必须先完成 strict Operational Run projection；任一 Operational Run state/registry/ledger 不可读时 fail closed，并把一个 `run_projection_incomplete` 人工处置项投影到 Status，不能静默丢掉损坏 Run 后继续使用健康 sibling。`HistoricalReadOnlyRuns` 只由 `EM-HISTORICAL-RUN-001` certificate 产生，不参与 Task lifecycle 或任何 action。
- 内部 Stop Run 成功且后续 Run 尚未创建时，Task 进入 `needs-attention`/`stopped`；它不产生 `waiting` Task 状态。即使 exact stopped Run 已有 committed completion finalization，它仍投影为 `run-stopped`、`terminal_outcome=none`，不得被 completed/writeback 分支吞并。
- Cancel 在发送任何进程信号前先写入保留当前 Run/PID ownership 的 durable intent，把 Task 置为 `finalizing/cancelling`；随后停止/固定 Run owner，并先提交 `cancelled` business terminal fact。所有 Task/state locks 释放后再启动独立 Workspace disposal transaction；处置失败只改变 disposal 轴，不回滚 `cancelled`，也不会删除 Artifact。
- Task 不存储 runtime-native session file 内容、resume handle value 或 cross-agent source ref。

## Run

`Run` 是一次 agent CLI 调用。

字段：

- `id`
- `sequence`
- `task_id`
- `target_id`
- `agent_name`
- `agent_cmd`
- `agent_conversation_id`
- `input_event_id`
- `request_fingerprint`
- `prompt_artifact_id`
- `cwd`
- `pid`
- `status`: `starting`、`running`、`succeeded`、`failed`、`stopped`
- `created_at`
- `started_at`
- `completed_at`

规则：

- pid 只属于非终态 Run。
- Run id 使用 compact canonical 形式 `r_<12 Crockford Base32>`；Task、sequence、provider、时间和来源消息是独立字段，不编码进 id。
- 终态 Run 在 compare-and-swap 后不可变。
- 迟到完成由 TaskService 追加 `late_run_completion_ignored` 审计事件；失去终态竞态的 Runner 不得追加 terminal completion 事件、共享 work-ledger completion 或 provider writeback，也不得重写当前 Task binding。
- Run Artifact 属于该 Run，不是 conversation history。
- RunTrace 和结果产物的公开读取按字段语义隐藏原生 session/thread/resume handle 与凭证，包括嵌在字符串内的 JSON 和逐行 JSON；普通业务 UUID 保留。UUID 的格式本身不授予它私有 handle 的含义，脱敏不改写原产物。
- Run-owned reader 必须携带同一个不可变 `{task_id, task_dir, run_id, sequence, ArtifactScope}`；Status 的 session、progress、artifacts、logs、result、source continuation 与 writeback retry 不能各自再次解析“latest”。现代 Run 只读取 `runs/<run-id>`，仅已证明的 pre-generation root-only Task 或逐文件 projection marker 可以读取 Task 根目录。
- 0.2 到 0.3 的已登记 Task 是受支持的版本化升级格式，不是 pre-registry Task。完整 Task registration、旧根 `run_id=task_id` 与 `accepted_at` 来源、同 Task 的 Run ID/sequence、无现代 claim 冲突的精确 `run_created` 事件及不早于 Task 创建的时间共同证明旧终态 Run 的归属。严格 loader 将这些 Run 上转为同一个 canonical aggregate，保留终态、AgentConversation、sequence 和 artifact；目标版本的停服 Flyway 迁移在签发启动租约前，经内部 migrate-storage 命令和精确 Task fence 发布当前存储格式；普通 TaskService 事务继续使用同一兼容读取。格式发布不推进业务 revision 或 UpdatedAt，保留全部业务状态和待处理 intent，不要求历史任务全部完成，不创建执行、不发送业务消息；已是当前格式时返回同一 revision，不重复改写。存储版本以后递增时保留已发布解码合同并追加迁移步骤，不得删除旧数据的升级路径。新事务在写入日志前、旧事务在重放发布前，都须核对磁盘 Run 清单；未纳入 aggregate 或明确历史登记的 Run 使事务拒绝，保留原文件供诊断。此前事务已发布 v2 Task 根但遗留旧 Run 文件时适用同一规则。现代 Run 的部分身份、Task/Run ABA、冲突事件或只有目录而无执行证据不进入此规则。0.2 IM Target 的来源仅限完整旧 Task registration、旧根已持久化的 provider:conversation 标识，以及首个 Run（sequence=1）的原始 context。首 Run 必须通过同一旧执行事件证明，context 的 task_id/run_id/run_dir 必须与该 exact Task/Run 全等；Task 目录由已验证的 Run 所在路径确定，旧 writer 不写 task_dir，若该字段存在也必须全等，且不得含 task_instance_id、task_registration_sequence、run_sequence 或 sequence claim；provider、conversation 必须与旧根标识全等，connector 必须是合法 authority。只在 Target 缺失时读取，不使用 latest 或后续 context；来源缺失不得授权旧绑定，身份冲突拒绝且不改盘。ChatBridge 只为同一已验证 Task/Target 的全缺省旧 TaskRef 绑定补齐 generation，绑定时间须不早于 Task 创建，或由首个已验证 Run 的原始消息绑定以相同 Task、目录和精确创建时间证明首次登记前的绑定；只补齐与已验证来源和创建时间完全匹配的默认绑定，引用关系和选择时间不变。Codex 只在这个精确旧 Run 的原生 handle 与 Agent、capturing Run 一致时接续原会话；旧 Run 发布为 v2 后仍以旧执行事件证明来源。现代执行的事件不符合旧证据，缺少 receipt 不回退旧 handle store。
- 不满足上述已登记版本升级合同的历史 Run，只有 explicit approval manifest 经 `TaskService` 写成 Task root `.private/historical-run-registration.json` 的 schema-versioned certificate 后，才能把其中准确列出的 pre-upgrade Run 显示为 `HistoricalReadOnlyRun`。manifest 至少固定 `authorization{kind=pre-upgrade-signed-manifest|operator-attested,approval_id,approval_digest,policy_version}`、完整 TaskRef 及其 digest、按 `{sequence,run_id}` 有序且唯一的 Run 清单；每项固定 `runs/<id>/run-state.json` 相对路径及 SHA-256、选择的 legacy event locator/digest、frozen display snapshot、允许浏览的 artifact manifest/hash 和 record digest，整体再由 `manifest_digest` 与 `certificate_id` 绑定。legacy event 必须先按同一 `run_id` 证明只有 approval 指定的一个正 sequence，且该 pair 至少有一条显式有序 `run_created`；旧 writer 遗留的 `sequence` 缺失/null event 只有在这项唯一性证明之后，且自身不含 modern Task registration、claim、冲突 Task id 或冲突 Task directory 时，才整体绑定到该 pair。显式 `sequence=0`、非法 sequence、同 Run id 的另一正 sequence、或仅有无序 `run_created` 都不能绑定。certificate 写入固定顺序是 exact idle terminal TaskRef recheck -> durable migration intent -> certificate -> committed receipt/event -> Task state 的 certificate id/digest -> clear intent；重试只能重投影同一 receipt，不能扫描候选后自行扩大列表。Task replacement、TaskRef/approval/certificate/Run-state/event identity digest 漂移、重复/乱序 pair、certificate 外 Run、含 modern Task registration 却缺 immutable claim 的事件、或任何 active/continuable lifecycle 都必须拒绝。artifact bytes 在建证时一次性生成 manifest；之后某个 artifact 漂移只关闭该文件的读取，不能让未变化的 certificate/Run identity 失效，也不能授权读取替代文件。
- HistoricalReadOnlyRun 的 Session/progress/log/result 浏览只使用 certificate frozen snapshot 和被选中文件的逐文件 hash；Status 不扫描其目录，不读取 native Agent Session 或 resume root，不跟随 source continuation，不用当前 Task state 补 result，也不把它暴露为 Task Files 的目录 root。它没有 `current`、`latest`、process、delivery、AgentConversation 或 resume ownership，不能成为 Runtime usage、provider/workflow/ChatBridge effect、source continuation、recovery、cleanup 或任何 TaskView action policy 的输入。一个 Task 可以同时有 certificate-bound historical R1 与完整 Operational R2；默认 inspection 只要存在任一 Operational Run 就优先 Operational 域，R1 只能凭完整 certificate-bound `run_ref` 显式切换。历史登记不会改写旧 Task 的持久化 `latest_run_id/sequence` 审计缓存；当该 pair 被 certificate 精确覆盖、`current_run_id` 为空且 strict aggregate 没有 Operational Run 时，Status 必须忽略该缓存的 operational 含义并允许显式浏览 historical-only history，绝不能因此制造 latest/current owner。没有 certificate 的已登记 historical Run 保持 `projection-incomplete`，不得因目录仍可读而展示成可操作 Run。
- mutation selector 必须先在完整 Catalog 中扫描只读 Run 域再解析 Task owner；即使 R1 已被 R2 覆盖、另一 Task 的 `task_id` 又恰好等于 R1，裸 R1 也必须返回 read-only/ambiguity 而不能写到另一 Task。selector resolver 负责拒绝原始历史 Run 字符串，TaskService 只对其收到的完整 TaskRef/Run fence 在 lock 内再次校验；后者无法替代前者。人工 supersession 只接受绑定 `{task_id,task_instance_id,task_registration_sequence,task_dir}` 的 `task:v2` capability 或精确 Task 目录，不接受裸 Task/Run/current/latest id。
- 历史嵌套 workflow Task 经显式登记后，读取路径以已验证 certificate 的完整 TaskRef/TaskDir 为准，不额外要求子目录 basename 等于 Task ID；没有匹配证书的新版 Task 仍校验目录身份。历史 Run 的输出优先读取 certificate artifact manifest 绑定且逐文件 SHA-256 未变化的 `run-trace.jsonl`，复用 RunTrace 投影并校验 exact Run/sequence；没有已登记 trace 时输出消息列表为空，状态仍从 frozen snapshot 展示，不能把状态算作 Agent 对话。trace 缺失、内容漂移或身份冲突返回明确的输出不可用，不影响其他已验证历史文件或赋予 Run 操作权限。历史登记的 frozen display 以该 Run 的 `run-state.json` 状态为准；legacy event 只在状态缺失时补充，不能用事件携带的 Task `completed` 覆盖 Run `succeeded`。操作入口 `migrate historical-runs` 先按显式 Run 清单生成只读 approval 草稿，operator 确认后以 `--apply` 提交同一个 manifest；预览、安装和启动均不得自动批准目录候选。
- Run 不存储 resume handle value 或 cross-agent source ref。
- 同进程 live watcher 永远拥有其 exact Run 的 completion；guardian exit receipt 只供 watcher 已不存在的进程恢复，不能抢占正常 `Wait`/OnComplete。`CompletionRecoveryContract`、`GuardianExitReceipt` 和 completion callback receipt 均为 managed schema v2，且每一份都必须携带并匹配 `{task_id, task_instance_id, task_registration_sequence, run_id, sequence}`；TaskService 还必须在同一 lifecycle lock 下将三者与当前 registry 复验。schema v1 或缺失任一 Task registration 字段的 sidecar 只能作为不可投影的历史残留，绝不能为 deleted/recreated 后相同目录、TaskID、RunID、Run sequence 的 successor 提供 recovery、containment 或 callback 权限。通用 completion callback 使用 Run-private durable receipt 提供 at-most-once 投递：先写 `claimed`，成功后写 `delivered`；服务若在两者之间崩溃，恢复必须 fail closed，不能冒险重复外部副作用。Task/Run 终态事件重试不得再次调用已经 claimed/delivered 的 callback。
- 同一 current Run 的正常工作区或外部资源登记可以推进 Task revision，不能使其已验证的进程完成 observation 失效。TaskService 在 lifecycle lock 内复验完整 Task/Run identity 与 current owner 后使用当前 revision 结算；Task replacement、另一 Run 或旧 generation 的完成仍被拒绝。普通外部 Command 的 revision fence 不放宽。

## AgentConversation

`AgentConversation` 是 jarvis-box 对一个 runtime-native conversation 的编排记录。

字段：

- `id`
- `task_id`
- `target_id`
- `agent_name`
- `agent_cmd`
- `resume_handle_id`
- `resume_status`: `initializing`、`resumable`、`active`、`missing`、`unsupported`、`expired`、`invalid`、`retired`
- `current_run_id`
- `last_run_id`
- `parent_agent_conversation_id`
- `created_at`
- `updated_at`

规则：

- `id` 在首个 Run 启动前创建。
- 同一 AgentConversation 最多有一个 active Run。
- agent continuation 到达时如果存在 active Run，先同步执行内部 Stop Run；确认停止后再创建后续 Run。
- `parent_agent_conversation_id` 表达 Continue 创建新 AgentConversation 时的 lineage。
- AgentConversation 不存储源 conversation ref。Adapter 需要跨 agent source ref 时，只能在调度期间从父 conversation 和 private handle metadata 推导。

## AgentSession

`AgentSession` 是 runtime agent 拥有的 native session、thread、checkpoint 或 conversation file。

示例：

- Codex session id 或 session file
- Claude Code conversation/thread
- Copilot CLI conversation
- Gemini checkpoint
- Opencode session

规则：

- jarvis-box 不把 AgentSession 当作公开业务对象。
- jarvis-box 不解析 AgentSession 内容来拼 prompt。
- jarvis-box 不把一个 runtime 的 AgentSession 内容转成另一个 runtime 的历史。
- Adapter 可以捕获一个 opaque resume handle 或 source ref metadata。
- 私有 handle value 只在 adapter dispatch 时解析。
- Start 保存已选择的启动参数，包括其中显式选定的模型；同 Agent Continue 沿用该选择，原生会话缺失并不授权切换模型。旧 Run 未保存参数时，只按当前明确配置解析：工作类型仍选择该 Agent 才使用其模型参数，否则仅使用该 Agent 自身的配置，不套用其他 Agent 的参数或从历史聊天推测。后继 Run 保存解析结果，跨 Agent Continue 按目标 Agent 的配置重新选择。
- Codex、Claude 和 Copilot Continue 校验由 exact Run receipt 选定的本地会话记录是否可用。Codex 的 active 与官方 `archived_sessions` 记录均须为唯一的 regular file 且 `session_meta.id` 匹配；官方归档由已配置的 Codex CLI 解除归档，完成后重新验证 active 记录，再沿用原 native session。外部历史轮转的压缩归档识别显式 `source` 的元数据，以及带 `prefix`/`archive` 的历史元数据：前者绑定当前 sessions 根，后者必须匹配当前 HOME 下同名归档对，各自仅采用已知 stat 布局中的原字节数。两者均只恢复成员路径、原字节数、SHA-256 和 `session_meta.id` 都匹配的单个 regular 文件，不覆盖已有文件，不猜测未知格式。记录不可用或归档无法验证、恢复时，返回无可用 handle，由同一个 Continue 创建 child AgentConversation 和新 native session，保留 Task、Workspace、当前指令和交付契约，并记录运行时诊断；不要求用户 `/new`。此检查不从其他会话发现 handle，不导入历史聊天，也不放宽 Task/Run receipt 的身份校验。

## AgentResumeHandle

`AgentResumeHandle` 是 adapter 私有状态。

字段：

- `id`
- `task_id`
- `task_instance_id`
- `task_registration_sequence`
- `run_id`
- `run_sequence`
- `agent_conversation_id`
- `agent_name`
- `adapter_schema`
- `source_receipt_id`
- `kind`: `native_session_id`、`thread_id`、`checkpoint_ref`、`conversation_id`、`opaque`
- `value`
- `captured_by_run_id`
- `status`: `valid`、`missing`、`unsupported`、`expired`、`invalid`、`retired`
- `created_at`
- `updated_at`

规则：

- `value` 只存在于 private handle store。
- private store 的 key 必须由完整 Task registration + Run generation + AgentConversation + agent 派生，不能只用裸 `run_id`；读取时逐字段复验，任何缺失、ABA、Agent/Conversation 不匹配都返回 unavailable，不能回退到同名文件或另一个 Run。
- handle 只能来自对应 runtime adapter 的 closed structured start/resume receipt。Codex adapter 只接收自己启动的 `exec --json` 进程首条 `thread.started` 协议事件，绑定完整 Task registration、Run generation 和 AgentConversation 后写入 runtime-private receipt；Continue 在 lifecycle lock 内校验该 receipt。缺少凭据的新任务或旧记录启动新会话，凭据身份损坏拒绝继续；不通过扫描旧 session JSONL 补造凭据。stdout/stderr 中的 UUID、`session id:` 文案、JSON-looking 日志、用户 prompt echo 和另一 runtime 的事件都不是 handle capture authority。
- Claude/Copilot adapter 在启动前明确签发或选择 native session ID，并核对实际 argv 中唯一的 `--session-id` / `--resume` 选择与该值一致；只有进程成功启动并取得 exact Run ownership 后才能保存私有 receipt。后继 Run 读取同一 Task/Run/Conversation/Agent 绑定的 receipt 续接原会话，不能根据日志猜 ID。已发布的 Codex receipt 缺省 Agent 字段仅代表 Codex，不得被其他 Agent 使用。
- 已发布 0.2 的 Codex/Claude/Copilot terminal Run handle 由追加的停服 Flyway migration 导入：必须同时核实原 Task registration、Run creation event、Run Agent、handle kind、原 Run ID 和有效 session ID；不从目录或缺失值重建。迁移只写私有续接 receipt，保留原历史生命周期，不启动进程；重复迁移不得覆盖冲突 receipt。Gemini/OpenCode 继续遵守各自已有的能力声明；已移除的 Agent 不恢复支持。
- 公开 JSON 只可暴露 handle metadata 和 safe status。
- `value` 不得出现在 Run JSON、launch request JSON、Status projection response、Artifact、logs、E2E evidence 或用户可见摘要中。

## Workspace

`Workspace` 是 Task 拥有的一项文件系统区域；一个 Task 可以拥有零个到多个 Workspace。

规则：

- Task 以 append-only `task-state.workspaces[]` 作为唯一归属登记表；每项包含稳定 id、服务端分配路径和可选 repository metadata。
- 登记和处置共享同一个以规范化绝对路径为 key 的全局 disposal lease。任何新增、变更或重放 `workspaces[]` 的写入都必须先取得该路径 lease，再在 Task lifecycle lock 内比较并写入新的 `workspace_registry_revision`；处置也必须先取得同一 lease。Status 详情、单项删除和批量清理只能消费同一 TaskView 投影产生的 sealed `workspace_disposal_policy`；该 policy 分别给出 selected 与 completed-bulk 的 closed enabled/reason，适配层不得再读 `status`、`phase`、`monitor_status`、Run pointer 或进程字段重新分类。policy reason 的封闭集合必须包含上游 mutation gate 能产生的 `projection_incomplete`、`blocker_attribution_incomplete`、`run_projection_incomplete`、process/effect ownership reason 以及 terminal eligibility reason；GET policy 与 POST adapter 必须原样消费同一值，不得把一个合法上游原因降级为 `workspace_policy_unavailable`。Status 只提交 exact TaskRef/workspace id 给 TaskService，不能以一次 `Collect`、TaskView policy、owner count、目录存在性或页面快照授权删除；TaskService 必须在 effect 前以同一 TaskRef、registry revision、idle Run proof 和 path lease 复验。若 lease 内复验发现任意不同 TaskRef 仍登记同一路径，该路径是 shared，处置永久跳过且保留双方登记，不能以“已终态”或“文件不存在”覆盖。
- 已登记项的目录存在时，id、path、project、remote 和 primary 保持稳定，保护其中的工作树与未提交修改；`base_branch` 可以在 Start/Continue 时从 provider 实时状态刷新。若目录从未创建成功或已按登记清理，当前请求可以把 repository metadata 修复为声明项目集合中的合法成员，并由同一个 Workspace owner 重新分配路径。非空集合恰好有一个保留 id `primary`，只用于选择 Run 的默认 `cwd`；空集合不合成虚假 Workspace，Run 使用 launcher 的普通工作目录。
- TaskService 必须先验证每个 repository source 可解析，再在 Task state mutation 中登记初始 Workspace，最后才逐项创建或 clone。TaskService 是 Task Workspace 唯一清理 owner，不依赖 Runtime Foundation reclaimer，也不通过目录扫描猜测归属。Runner 向每个 runtime agent 注入同一 Workspace ownership contract；zero-workspace Task 在 active Run 中取得第一个仓库时必须通过 `jarvis-box workspace create --id primary` 建立 canonical primary，后续增加仓库使用普通 stable id。动态命令同样在 registry mutation 前验证 repository source；`--project` 只有配置 `GITLAB_HOST` 时才能解析，其他仓库必须传 `--remote`。声明 repository 的成功结果必须是真实 Git worktree，只有 project/remote 都为空时才允许空目录。首次创建与 Continue 重建 Workspace 使用同一个 base branch 解析规则：显式分支已确认在远端不存在时回退 remote 默认分支，将请求分支、实际分支和原因传给本轮 Agent，告知用户并在修改代码前确认回退是否适合；immutable review checkout ref/commit 不适用这一降级。运行中的 CLI 从 TaskService 接收不可伪造的 `{task_id, task_instance_id, task_registration_sequence, run_id, sequence}` fence：先以 typed workspace-registry Command 在同一 lifecycle lock 中登记，再在 lock 外执行 clone/configure 等外部效果，最后以 outcome、storage 或 cleanup receipt 回到 `Service.Advance`。每个 command 强制携带非空稳定 receipt id，并在同一 owner 内重新校验完整 fence；R1 在 R2 claim 后的迟到 receipt、同目录同 Task ID 的替换代际 receipt 和空 receipt 都不得写事件、状态或 successor 的 Workspace。若 effect 已发生但 receipt 因 ownership丢失被拒绝，已登记路径仍是 Task-owned disposal/recovery 的唯一依据，不能改写 successor。
- 所有冷 cache mirror clone 和远端 Workspace clone 使用同一瞬时故障策略：最多 5 次尝试，间隔 1、2、4、8 秒；识别 early EOF、unexpected disconnect、响应 body 不完整和 HTTP/2 stream/internal error 等传输故障。当前 Run 的首次此类故障后，后续网络 Git 尝试显式使用 HTTP/1.1。每次尝试前删除未发布的 staging；cache 始终只是优化，构建失败不发布残缺 mirror，并回退到 authoritative remote。取消 Task 必须中断正在执行的 clone 和退避等待。
- Run claim 后、Agent PID 发布前，Task state 持久化 `preparation_started_at` 和当前准备操作；读模型实时计算准备/操作耗时，并通过 `preparation_operation_started`、`preparation_operation_retrying`、`preparation_operation_fallback` 事件留下审计证据。若 Operator 配置了 Agent runtime preparer，新 Task 先完成 Workspace/provider 和依赖准备，再调用这个无参数、版本化的客户 Runtime Foundation hook 并保存成功 receipt，最后启动 Agent；已有成功 receipt 的 `Continue` 与同一 Run 的 Agent failover 不调用，首次失败或旧 Task 没有 receipt 时则在 Workspace/provider 准备完成后重试。Agent 启动、launch 失败、取消或 recovery 会冻结总准备耗时并清空当前操作。
- active 或 needs-attention Task 的全部已登记 Workspace 可以跨多个 Run 复用。目录缺失时，TaskService 根据登记重建；登记以外的 `cwd`、`workdir`、Run context、Artifact 和目录扫描都不能成为归属证据。
- Run 结束时，TaskService 先持久化带完整 Run/Task 终态 patch 的 `terminalization_intent`，再提交当前 Run 终态、执行适用的 provider completion/writeback 和最终投影；释放 Run ownership 时按 `JARVIS_TASK_WORKSPACE_CLEANUP_DELAY_MINUTES`（默认 20 分钟）原子写入 `workspace_cleanup_due_at`。只有绑定 provider workflow 的 lane 才要求当前 Run 留下 provider writeback evidence；current scheduled taxonomy **仅** `memory-consolidation`、`daily-reflection`、`cognitive-evolution` 三条 lane，它们是 providerless：Agent 环境不得携带 `JARVIS_PROVIDER` 或 `INTAKE_*` provider intake capability，不生成 provider workflow input、comment poller 或 writeback 要求；即使旧运行残留半截 workflow Artifact，也不能阻塞其 succeeded Run 的 terminalization 或 empty-set disposal certificate。退休的 `maintenance`、`self-improve` 不可由此 runtime path 执行或取得 providerless effect；其历史终态只按 `EM-LEGACY-LANE-001` 只读保留。`JARVIS_PROVIDER_WRITEBACK_ENABLED=false` 时 provider lane 仍执行并保留本地结果，但不启动 comment poller、不要求外部回写 evidence，并以 `provider-writeback.json` 记录跳过原因。post-registration preparer 的合法 skip 也使用同一顺序并保存 reason。Provider 回写失败通常落成 `needs-attention`。GitLab 或 GitHub 最终评论返回 HTTP 404，且同一服务身份仍可访问目标项目或仓库时，writeback owner 记录 `subject-not-found / provider-subject-not-found`；它先发布带成功 Run 事实的 `cancelled` Task，随后由同一 Workspace disposal transaction 在所有 Task/state locks 释放后处理 browser、登记 Workspace 和 typed external resource。清理失败只保留 disposal 的 durable intent/receipt 与 retry 状态，不得把已提交的 Task business terminal state 回滚为 `finalizing`。该分类只适用于 GitLab 和 GitHub；其他 provider 继续使用各自的 writeback failure contract。持久化瞬时失败也由服务启动及运行期恢复器幂等重放。Run 终态提交不依赖 Workspace 删除。
- Continue claim 新 Run 时清除未开始的 retention disposal round 并复用目录；每个 managed Run 在自身进程组退出前持有 Task 级 shared Workspace lease，覆盖运行中动态追加的所有登记项。处置入口只能向 TaskService 提交 typed `DisposalScope`：`Selected{workspace_ids}` 或 `Full{workspace_registry_revision, frozen_workspace_ids}`。`source` 仅是审计文本，不能决定 scope、截止时间、重试或 supersession。Selected 只推进指定 item，不改变 Full retention 的 deadline；Full round 在同一个 Task lifecycle mutation 中冻结完整成员集合、TaskRef、registry revision、canonical idle RunRef（若存在）、初始 retry generation 和稳定 round id，随后才释放锁执行 child transaction。扫描快照、共享 `due_at`、页面状态或每个 item 临时推导的 `FullTask` 都不是 round authority。
- Full round 的 browser cleanup 是 batch 级、最多一次的 exact canonical-idle-Run child transaction，不是每个 Workspace 的 path callback。顺序固定为：持久化 frozen Full round → 持久化 browser child intent → 锁外 effect → receipt → exact Run/Task reproject；child definite failure 进入该 round 的 backoff，child effect-start 无 receipt 为 unknown 并阻止父 filesystem/resource effect，receipt-only 只能重投影。没有 canonical Run 的合法 zero-Run Task 不伪造 browser child；有 Run 时不得退化为空 RunRef，更不得使用上一 Run 的 socket。任何只按 path 调用 browser cleanup、在 frozen round 之前执行 browser effect、或在每个 Workspace 中重复 browser effect 的路径均非法。
- Workspace disposal 的 claim、effect 和 settlement 之间只运输 closed reason 与 closed effect outcome；`error`、`message`、`EffectError` 和 child response 中的自由文本仅供展示/审计，禁止以 contains、prefix、suffix 或格式化字符串把它们反投影成 `task_active`、`registration_changed`、`outcome-unknown`、retry 或 skip。effect-start 无 receipt 的 unknown 只能来自 durable checkpoint/typed outcome；诱导性错误文案不得改变处置决策。
- 每个 Workspace item 在所属 round/scope 下执行独立事务：持久化 `{round_id, scope_kind, task_id, task_instance_id, task_registration_sequence, workspace_id, workspace_registry_revision, normalized_path, attempt}` intent → 释放 Task/state lock → 取得该路径全局 disposal lease 并复验唯一 owner → 持久化 effect-start → 执行 typed external-resource/quarantine/remove effect → 持久化 receipt → 以同一 round、TaskRef、登记 revision 与 idle proof 重投影。已有明确 unknown receipt，或外部副作用缺少可判定回执时，禁止盲目重复执行。同一已登记的本地幂等目录删除尚无明确 unknown receipt 时，恢复器重新取得 Task/path lease、核实登记归属和进程占用后可接续原 intent，不创建另一删除义务；receipt 已落而 projection 写入失败时只能重投影，禁止再次执行 effect，并且 receipt-only 仍是 disposal fence：写入 `projection_completed_at` 前 Continue/new Run claim 必须拒绝。脱离 managed 进程组的进程按 `cwd` 和 open-file reference 复核，无法确认安全时 fail closed。
- retry/backoff 归属于 durable round/item identity，不归属于一次页面点击或 Workspace 数量。Selected item 的 definite-failure receipt 只推进该 item 的 `next_retry_at/attempt`，不挪动 Full deadline；Full round 汇总全部可执行成员后只增加一次 round attempt，不能按 N 个 Workspace 增加 N 次。Full 与 Selected 的接管必须用显式 `supersedes_round_id`/parent relation；到期 Full 可以覆盖尚未 effect-start 的 Selected retry，但不得接管 unknown effect。一个 item exhausted 仍保留其他成员义务，并在 TaskView 展示未完成成员、稳定 reason 和各自 attempt。Status 与 `tasks clean` 必须消费同一持久化、按 `workspace_id` 排序的 member summary，不能从 Task 级 retry scalar 或最后一个 child response 重新猜测。定时 finalizer 在每个 serve 进程中都运行。
- zero-Workspace 不是绕过事务的快捷分支，而是受约束的 empty-set Full round。签证书前必须同时证明：完整 TaskRef、strict aggregate Run projection 可读、空且 revision 固定的 Workspace registry、合法且为空的 external-resource registry、无 active/terminalization/process owner，以及 canonical Run 存在时已有成功 browser child receipt。任一 Run/registry 不完整或仍有 external resource 时 fail closed、不得删除、不得签证书，也不得伪造 Workspace。
- Disposal batch 固定 TaskRef、registry revision 和 frozen members；batch 下每个 round 只是一次 aggregate pass，member attempt 只在该 member 得到 definite-failure receipt 后递增。member 的 durable state 至少包含 `{workspace_id, normalized_path, state, attempt, next_retry_at, reason, intent_id, receipt_id, producing_round_id}`。同 batch 的后继 round 可继承已经 cleaned member 的 exact receipt，绝不能再次执行其 effect；unknown member 阻止接管，partial-exhausted member 保留人工重试义务。Selected 与 Full 的接管先持久化 predecessor `superseded` 与 successor relation，不能只改 current pointer。
- 全部 frozen item receipt 成功、external-resource obligations 清空且 browser child（若需要）成功后，TaskService 先追加 durable `workspace_disposal_aggregate_receipt`，至少包含 `{certificate_id, batch_id, current_round_id, TaskRef, workspace_registry_revision, sorted member_receipts[{workspace_id, normalized_path, attempt, receipt_id, producing_round_id}], external-resource outcomes, browser_child_receipt_id, zero_set}`，再把 `workspace_disposal_completed=true` 作为可重建缓存投影。任一新 Run claim、Task ABA 或 registry revision 变化都原子失效旧证书。对同一仍有效的 batch/round，已签 aggregate certificate 优先于任何较早读取的 coordinator aggregate：迟到的 settlement 只能把 round/state 对齐为证书的 completed 投影，不能以当时观察到的 effect-start 或 deferred 结果降级为 unknown/retry。state 中孤立的 bool 不是 authority；TaskView 与 `tasks clean` 必须验证当前 aggregate receipt，且 `tasks clean` 在同一 lifecycle lock 内重新读取并校验证书后才可删除 Task 目录。没有有效证书的终态 Task 返回 `workspace-disposal-not-complete` 及未完成成员，不被静默跳过。
- Status Cancel 同样先持久化 cancellation intent，再发送进程信号并终态化 Run。受管后代进程的停止证据仍是终态 transaction 的一部分；仅在 terminal Task fact 已 durable 且所有 Task/state locks 释放后，才启动每项 Workspace 的 plan → effect → receipt → reproject transaction。Workspace/Docker 清理失败把未完成义务和退避期限写入取消终态，但不得让五秒恢复器重放 filesystem effect 或把 terminal Task 改回 `finalizing`。intent 不会提前清空 PID 或 Run owner；一旦提交即优先于晚到的 completion，后者不得覆盖取消决定。无 Run owner 但仍有存活 PID/PGID 时取消 fail closed，保留进程与 Workspace 证据。若进程在 Stop 前退出，启动及运行期恢复器先解决该 Run ownership，再做登记式清理。最终状态写入失败时保留 intent，磁盘恢复后自动重放；失败或停止且尚未进入终态处理的 Task 保留目录用于诊断或 Continue。
- 清理目录不删除登记项；Status detail 继续显示每项路径与存在状态，并允许执行受控删除。
- `execution_project` 不是独立项目来源，只能选择 Task context 中 `associated_repositories[]` 的 provider + project identity；`execution_repo` 由 Jarvis Box 基于 provider host 和 allowlist 派生。非关联成员不得进入 Workspace project、remote、prompt、environment 或执行审计；当同时关联多个仓库时，workflow 必须明确选择或保留多 workspace 交付，不能默认取第一个。
- Public projection 只允许 Task detail 的 `workspace_locations[]` 暴露已登记路径；其他任意 filesystem path 都不得公开。

## 授权与新 Run

`EM-LICENSE-001` 只控制创建新的 Agent 进程，不新增生命周期操作或 Task 状态 owner。在线授权按签名决定、安装/设备/宿主绑定、可信时间与租约检查；离线授权使用同一客户端验签和绑定，按签发有效期检查且不联网。授权身份与决定持久化在本机授权目录，Task/Run 仍由 TaskService 与 strict aggregate 管理。Status 的授权面板消费与 CLI 相同的本地快照，不自行推导另一套允许规则。当前验签状态已否定的未激活／停用签到失败不再作为当前问题，真实网络失败保留至成功检查。系统设置手动重新检查使用同一授权客户端：在线签到、离线本地验签，再重读状态；只刷新授权租约，不提交 Task/Run Command。停用后重导入已接受的旧签名授权不得恢复准入；恢复需新的在线激活或签发时间晚于本机已接受签名决定的时间高水位的新授权文件。

## Start

Start 创建新的 Task、AgentConversation 和 Run。

只有正常完成或已取消的 source Task 可以 Start；`needs-attention`、停止、失联、缺产物或写回未完成的 source 必须先 Continue 或 Cancel。

Status 的 source Start 是一条显式的来源快照事务。产生 ActionPolicy 的同一次 strict aggregate 投影必须把完整 source TaskRef、strict latest operational RunRef 和 `zero-current-run` 封入 server-private command；POST adapter 只运输该快照，不能在执行时重新选择 latest。TaskService 持有全局 registry guard 后进入 source Task lifecycle lock，在该锁内重新读取 strict aggregate 并同时复验 Task registration、latest Run identity/sequence、没有 current Run 以及 source 仍为允许 Start 的 inactive terminal lifecycle；全部成立后才允许分配新的 Task registration、Task 目录、admission WAL 或复制任何 source Artifact。延迟的 R1 Start 若此时已经出现 R2、原 zero-current 已变成 current Run、Task ABA 或 aggregate 不完整，必须返回 snapshot-changed 且不创建子 Task、不消耗 Task registration sequence、不写 admission/work ledger。source Artifact 只能从这次复验通过的 exact Run `ArtifactScope` 复制，不能由 taskstore、adapter 或后续 launcher再次读取 mutable latest pointer。

步骤：

1. Provider adapter 解析输入、Target、actor、visibility 和稳定 provider evidence key，只提交 typed Start Command；key 必须由 provider authority、lane、触发对象的 immutable provider id/版本事实（例如 Issue iid+created event、comment/note id、MR/PR commit SHA、follow-up finding-set revision、merged change landed SHA）组成，不能使用时钟、临时 RunDir、目录扫描或展示文本。adapter 的 dedupe JSON 只能缓存已提交 receipt，不能以 `Stat -> launch -> write`、`O_EXCL` 空文件/目录或历史目录扫描充当 admission authority。
2. `TaskService` 在全局 admission/registry lock 内对 `{evidence_key, attempt_id}` 执行 append-once claim：已提交 receipt 直接重放；首次或尚未 effect-start 的同一 intent 只能被一个 caller 原子提升为 effect-start 并在锁外调用 launcher；effect-start 后没有 outcome receipt 时，进程内 live admission registry 仍持有该 record 的在途调用者（同进程并发/重复 webhook）→ 返回 in-flight 回执（`202 delivery_in_progress`），live registry 无持有者（进程重启后内存态清空，无法证明在途）→ 一律 `outcome-unknown`；两种都不得由重复 webhook、tick 或重启盲目 launch。明确且可证明未开始的 failure 才结算为 definite failure；其后只有新的、稳定且显式的 attempt identity 才可建立新的 intent。并发 webhook、comment、MR review 或 scheduler tick 不得各自创建 Task/Run 后再覆盖同一 dedupe 文件。若某 lane 将 receipt 再投影到独立 cache（例如 follow-up state），重放前还必须以 receipt 的 Task id、`task_instance_id`、`task_registration_sequence` 复验当前 Task，并以 Run id、Run path、Run context 的 lane/operation 复验 exact Run；同目录、同 Task id 或同 Run id 的旧代际均不得更新该 cache。
   已发布 0.2 的 provider 去重回执是跨版本的受理事实，生命周期独立于 Task retention。目标版本在服务停止的 Flyway 阶段读取 GitLab/GitHub/Jira command、Issue creation、飞书项目 event 回执以及 merged-change claim：验证原文件名、业务字段、regular/no-symlink 路径，按原 runtime 的 canonical provider authority 和完整 Subject 固化到同一个全局 admission ledger，保留 source digest。已经清理的 Task 不得为迁移而重建，不得伪造现代 registration 或完成事实。post-launch 回执可重放原受理结果；只有 pre-launch claim 时保留 outcome-unknown。飞书项目旧 bare receipt 未记录 lane，其 UUID 是跨事件类型的投递身份，迁移保留同一 UUID/Subject 的去重约束。live adapter 只提交从原事件推导出的 released receipt identity，由 ledger 核对 provider、authority、lane 和 Subject；不得在请求处理中读取旧文件。未发生 effect-start 的现代 intent 仍受历史去重事实约束；已持久化的现代 effect/outcome 保持原有权威。同一历史事件不得获得新 launch permit，不同事件仍走正常准入。配置 authority 日后改变不能移动已迁移事实，source 冲突或损坏必须失败且不落部分账本。
   同一个已发布评论批次内的成员身份，与该批次的当前 admission intent 原子保存在同一条全局台账记录中。它们只索引同一个 claim、effect 和 outcome，不产生独立 launch permit；intent 尚未开始时，成员重投返回 in-flight，不可用单条输入抢占整个批次。成员归属、authority 或批次重叠发生冲突时拒绝。批次处理后清除可变 intake 缓存，不会撤销这些成员的去重事实。
3. `TaskService` 选择 effective runtime agent。
4. `TaskService` 在同一全局 Task 登记事务中分配并持久化新的 `task_registration_sequence`；同一次 admission mutation 写入随机 `task_instance_id`、canonical `subject`（如有）、初始 `workspaces[]` 和最小 `pending_launch`，但不创建 Run。历史 Task state 不在这个入口补登记或迁移。
5. Launcher 在调用 TaskService 前把本次请求的 typed admission 配置（包括显式存储余量门槛）放进 `RunRequest`；TaskService 只消费这份请求事实，不从 Agent execution environment、进程环境或之后的 callback 猜测。随后 TaskService 检查 Task Artifact 所在卷和每一项已登记 Workspace 路径的磁盘余量。容量不足时 Task 进入 `storage-wait`，没有 `current_run_id`；服务启动及每 5 秒运行的恢复器在容量恢复后重新走原 lane launcher。并发恢复仍由 Task owner/sequence CAS 保证只创建一个 Run。直接 effect 失败只有在 error chain 保留 OS `ENOSPC` / `EDQUOT` typed errno 时才能补充 capacity evidence；subprocess stderr、`error`/`message`/`reason` 文案以及把 response map stringify 后的文本都不是 storage 或 persistence-retry receipt。`PrepareRun` 只在 Run claim 后绑定 Run-local Artifact、Agent 参数和执行环境，不能反向改变已经完成的 admission decision。

   存储恢复器的目录扫描只提交 TaskService maintenance materialization command：它依次在 strict root scan、每 Task lifecycle lock 内收敛 pending Run-claim WAL、admission WAL、缺失 Task projection 和历史 Continue capacity evidence，并返回 sealed `AdmissionRecoveryPlan`，而非只读候选快照或 raw Task map。TaskView、service-maintenance planner、active duplicate gate 与 ChatBridge source planner 必须验证同一条最新 durable admission authority 与当前 state cache 完整一致：Z2 authority 是 zero-Run admission WAL；S1 authority 是 exact latest failed Run 的 typed retry receipt，或绑定同一 source Run 的封闭 normalizer WAL。一张仅在 `status/phase/pending_launch/storage_wait/duplicate_wait` 上“长得像”等待的 raw state，既不能计入 doing、成为新 Task 的 duplicate blocker，也不能签发 Run launch、Task-root Artifact 或 cancellation capability。service-maintenance 只有在 strict OperationalRuns 为空且 Z2 WAL 匹配时才可签发 `cancel-zero-run-admission`，并必须运输完整 TaskRef 与 explicit zero-current-Run expectation，由 TaskService 在 effect 边界复验；Z1、Z5、S1 或无 authority state 只能得到 closed block/no-authority。duplicate gate 只接受 exact current Run owner、Z2 WAL 或 S1 typed receipt，不能用 raw active predicate 阻塞新 work。plan 固定携带 closed disposition、typed wait kind、admission token、完整 TaskRef/nullable exact Run fence、typed reason，以及 lane transport 的最小 typed launch request；该 request 只描述 Start/Continue、已选 source artifact、完整 `AdmissionDescriptorBinding` 所封的 descriptor transport reference、subject 和 workspace，绝不复制 state 或 `pending_launch`。裸 descriptor reference 只能定位私有字节，不能被 server/adapter 当作该 plan 的替代授权。server adapter 不直接调用这些写入口或重新读取 state/Run artifacts 分类；它把 `launch` plan 原样交给 `CommandLaunchRun`，TaskService 再在实际 Run claim 的同一 Task lifecycle lock 内复验 token、Task generation、lane 与 expected status/phase，失败时不创建 Run、Artifact 或进程。launcher 在 Run claim 前返回 sealed `Skipped` 时，TaskService 以同一 token/fence 复验后提交 Cancel intent/receipt：Z2 投影为 Z4，S1 保留历史 Run 后取消 Task；typed intake invalid 则提交 Z3 launch-failure intent/receipt。两者的重试都只能物化同一 receipt，不能结算更换过的 admission，也不得写 `completed/launch-skipped`。零 Run 的现代分支必须已有 Task registration；无 registration 的历史 intake 只能读，不能借历史 ledger 取得 registration、recovery audit、launch、settlement 或 accepted-ledger 写权限。

   ChatBridge 的零 Run 恢复/续跑是上述 plan 的专门运输路径：maintenance plan 到达 ChatBridge 后，adapter 必须先交回 TaskService，在同一 Task lifecycle lock 下得到 sealed `launch|blocked` disposition、closed reason、完整 `TaskRef`、`{run_id:"", sequence:0}` source fence 和当前 admission token；只有 `launch` 才可读取该 Task 根目录的 ingress artifacts。ChatBridge 不得从 `phase`、`authoritative_phase`、`status`、`latest/current` pointer、runs 目录是否存在、错误文本或根目录 Artifact 推断这一权限，也不得在 `blocked` 时替换 Task/Run。随后它把**同一** `AdmissionRecoveryPlan` 原样运输给 `CommandLaunchRun`，由 Run-claim transaction 再次复验 token，故 Task ABA、admission wait 更新、取消、durable supersession、未决进程 owner、损坏 aggregate 和 definite pre-Run failure 都只能闭合拒绝，不能降级为 root-artifact fallback。

历史 chat Continue 在进程启动前因容量不足却错误投影为 `needs-attention` 时，只允许由当前已登记 Task state 中 `runtime_launch_failed`、精确 `last_error_reason`、`*_degraded` 和带精确 path 的 typed capacity record，加上 exact failed Run 的 `run-state.json`、`run-context.json`、`meta.json` 和 `prompt.txt` 共同授权一次性归一化。`launch_error` 是非授权诊断 payload，不能以任何文字、前缀或“low disk”包含关系补足或替代 typed record。归一化是 TaskService 的 admission-projection transaction：提交前复验当前 `{task_id, task_instance_id, task_registration_sequence, run_id, sequence}`、失败态 fingerprint、Continue artifacts 与 typed scope/path/health；提交后的 `task_admission_committed` 是唯一 crash-replay authority。Task JSONL 中缺少完整 Task registration 的旧容量事件只能作为审计记录；即使它复用了相同 TaskID、RunID 和 Run sequence，也不得选择 storage scope/path、授权重放或改变当前 Task。
6. 准入通过后，TaskService 才以读取到的 Task owner 和 `latest_run_sequence` 为条件创建 sequence 为 1 的 Run，再逐项创建或 clone 目录，并把 `primary` 作为 Run 默认 `cwd`。Workspace/provider 和依赖准备完成后，若配置了 Agent runtime preparer，TaskService 执行它并要求合法成功响应；失败时保留已准备的 Workspace 但不启动 Agent。claim 后的 `run_created` 审计写入失败时不得启动进程；Run 分配和 Task ownership 必须按持久化恢复规则收敛，不能制造幽灵 owner。
7. `TaskService` 把本次 prompt 和 canonical run-context 写入真实 Run 目录；原始 provider payload/meta 保留在 Task 根目录，可选 Run preparation 回调只处理依赖最终 RunDir 的 provider-specific Artifact。

   Run claim 后准备或派发失败，即使调用方请求已经取消或超时，TaskService 仍须在独立于该取消信号的收尾 context 下复验 exact Task/Run owner 并落盘失败终态；不得留下无人执行的 starting Run 等待失联恢复。该 context 只完成已有 claim 的收尾，不授权重新准备或启动 Agent，原错误仍返回调用方，原执行输入保留供 Continue 使用。

8. `TaskService` 按选中的 agent 重建命令参数和每次 Run 的环境变量。
9. `Runner` 再次检查 Task Artifact 所在卷和全部已登记 Workspace 所在卷，然后启动一个进程并生成 Run 私有 Artifact；TaskService 负责 Run 终态仲裁和 Task 投影。Run claim 同时建立显式 launch-resolution barrier，只有 PID 已发布、启动失败或同步终态完成后才解除；Cancel 不用固定时长轮询猜测启动是否结束。
   Runner 在创建进程前先持久化 `process_identity_capture_pending` launch-owner fence；Spawner 必须在 `Start` 返回前、启动任何可能 `Wait/reap` 该进程的 goroutine 之前同步捕获 OS process generation，并通过强制的 `Process.ProcessGeneration()` 契约交给 Runner。极短命进程即使已经退出也使用这份启动快照，不能在交接后重新读取已经消失的 `/proc/<pid>` 并误报 launch failure。Unix Spawner 以 guardian 作为独立监督者，Agent 使用单独进程组；Linux guardian 在 Agent 存在前启用 child-subreaper，因此后代即使调用 `setsid()` 离开 Agent 进程组，daemonize 后仍由 guardian 收养、校验、终止和 reap；Darwin/BSD 没有对等的非特权 subreaper，其声明的自动终止边界是 Agent 进程组，不把主动新建 session 的进程冒充为已受管后代。guardian 在 Task 的 active identity、Run trace 和 `spawned` 审计全部持久化前保持 crash gate 和 Task/Workspace lease，只有 `CommitLaunch` 成功写入 gate 后才允许正常 `Wait`。此前任何持久化或所有权失败都先落 `unpublished-launch-abort-pending` fence，再由 `AbortLaunch` 在 leader 尚未 reap 的窗口终止声明的 OS containment boundary。若服务在该清理窗口崩溃，未提交 guardian 会终止该边界；重启在 guardian 持有的 Task lease 释放前不得清除未知 identity，也不得启动新的 Start/Continue。已持久化 generation 的 abort fence 则必须重新校验并收割。服务若在 spawn/handoff 窗口崩溃，重启 admission 不能把该 fence 当作普通 pre-spawn Run 覆盖，而要显式投影为 `process-identity-capture-interrupted`。generation 真正无法捕获时仍 fail closed：Runner 先把 fence 升级为 `process-identity-unresolved`，再由 Spawner 在 leader 尚未 reap、PID/PGID 不可能复用的窗口终止该 containment boundary；只有边界内成员、继承流、guardian 持有的 Workspace lease 全部清空且 leader exit 已观察后才解除 fence，不能把只杀 leader 或只观察 leader exit 当成安全退出。若服务恰好在清理完成后、退出事件落盘前崩溃，重启恢复只能用不发送终止信号的存在性探测确认记录的 PID 和 PGID 均已消失，再原子补写 `run_process_identity_exit_observed`；PID/PGID 仍在、已复用或探测结果不确定时继续保留 fence。

### 当前 provider Start 入口清单

下表是 `EM-ADMISSION-001` 的迁移边界，不是按文件名猜测的“可能入口”。每一行都必须先进入同一个 global provider-admission ledger；同一 evidence 的重复 delivery 只重放 receipt，绝不重调 launcher。

| Start surface | 入口 | stable evidence facts | 说明 |
| --- | --- | --- | --- |
| GitLab work-item | `IssueDispatcher` | authority、`post-check`、project、issue iid、created | Issue 创建一次 Start。 |
| GitHub work-item | `GitHubIssueDispatcher` | authority、`post-check`、repository、issue number、created | GitHub Issue 创建一次 Start。 |
| Jira work-item | `JiraDispatcher` | Jira authority、`post-check`、project key、issue key、created | Jira 创建 delivery 不以 sidecar 文件或历史目录判断是否启动。 |
| Feishu Project work-item | `FeishuProjectDispatcher` | `project.feishu.cn`、`post-check`、project key、work-item type/id、created | 创建事件的重复 delivery 重放 global ledger receipt；事件文件仅缓存已提交 receipt。 |
| human command | `JarvisCommandDispatcher`、`GitHubCommandDispatcher` | authority、`jarvis-command`、project/repository、noteable kind+number、note/comment id | 评论文本、RunDir 和 delivery clock 不是 identity。 |
| Jira command | `JiraDispatcher` | Jira authority、`jarvis-command`、project key、issue key、comment id | 同一 comment 的重投递不产生新 Run。 |
| Feishu Project command | `FeishuProjectDispatcher` | `project.feishu.cn`、`jarvis-command`、project key、work-item type/id、delivery UUID | 缺少稳定 comment/delivery identity 的请求 fail closed，不能用时间或目录补造 identity。 |
| review | `MRReviewDispatcher`、`GitHubPRReviewDispatcher` | authority、`mr-review`、project/repository、MR/PR number、head commit SHA | `review-diff-fingerprint.txt` 和历史 Run 目录仅是本次 Run Artifact，不能反向决定 Start。 |
| review follow-up | `FollowupDispatcher` | authority、`followup`、change identity、canonical pending finding-set digest | follow-up JSON 只累积 findings 和缓存已受理 Task/Run 的完整 TaskRef/Run fence；scheduler tick 不构成新 evidence。cache recovery 必须消费 TaskService 的 sealed reconciliation plan，不能按缓存或 Task JSON 文本重算 active/terminal/stale。 |
| merged self-improve | `SelfImproveDispatcher` | authority、`self-skills-improve`、change identity、landed commit SHA | 同一 merged change 的重复 hook 重放 receipt。 |
| GitHub delivery wrapper | `Handler.handleGitHubWebhook` | authority、`webhook-delivery`、event、delivery id、body SHA-256 | 用于 custom GitHub dispatcher 的外层 effect fence；typed dispatcher 仍保有更细粒度 evidence。 |

所有列出的 provider Start 均以同一个 global ledger 为 authority；adapter sidecar 只能在 outcome receipt 提交后缓存结果，不能 claim、恢复或反推 effect。`effect-started` 没有 outcome receipt：live admission registry 持有在途调用者 → in-flight 回执（同进程并发投递，非失败）；live registry 无持有者（进程重启后内存态丢失）→ `outcome-unknown`。两种都不扫描历史 Task/Run 目录、不移除 claim 后重试。显式的新 attempt 只允许接续该 evidence 的 `definite-failure`，并须携带稳定 attempt identity；当前 webhook 入口只提交初始 attempt，尚未暴露 operator retry endpoint。

已发布 0.2 的 MR/PR 审查去重证明也必须由停服 Flyway 迁入同一账本：原 webhook payload、审查 metadata、规范 Subject、执行 handles 和已发布的 comment-post receipt 共同绑定原事件。旧版 PrepareRun 曾把 metadata 的 commit 更新为实时 HEAD；原事件已受理的证明与实际审查提交的证明必须分开核对，只有明确匹配的 review-summary 才能额外复用不同的实际审查提交。迁移只保留 admission 去重，不重建已清理 Task/Run、不补造现代 publication 或完成事实。原文件之后被保留策略清理，也不能触发已受理审查再次执行；新提交继续正常准入。线上 adapter 只查询迁入的账本记录，不扫描旧文件。

已发布 0.2 的 follow-up intake 也属于上述迁移合同。停服迁移校验原项目文件名和完整 Subject，将原文件原字节归档，并将队列并入 authority-qualified target cache；原 pending 评论和已排队的 review findings 固定为同一批输入，后到评论留给下一次运行。旧 in-flight 在 launcher 前写入，只能迁入 outcome-unknown，不能视为完成或自动重放。已消费评论的稳定身份迁入全局账本，缓存删除不撤销去重。cache 不拥有 Task 生命周期；执行时通过 strict Catalog 找到同一 Subject 的既有 follow-up Task，再由 TaskService 的 action policy 与完整 fence 决定 Continue，新任务不能由旧缓存的 active/status 字段授权。原批次成功交接后才从队列移除，不恢复已经移除的自动 review 循环。

合并事件的 `self-skills-improve` 在分配新 Task/Run 前，通过该 Subject 的 Provider API 检查 target branch 的 `skills/self-skills-improve/SKILL.md`。文件不存在必须同时证明分支可访问，才结算为 `self_improve_skill_missing` 的 skipped admission，不产生失败工作项。权限错误、私有仓库不可见、超时和无效响应属于探测失败，不能冒充缺少技能；PrepareRun 仍核对实际检出文件。重复事件继续复用全局 admission receipt。

Status 的 Target 聚合不合并 Task 身份：同一 Target 下的所有关联 Task 必须在详情头部的 Task → Run 树中可选择，各 Run 展示自己的时间，Run 选择只作用于所选 Task。树不得根据 Run 序号推断 native resume 或 session 复用。刷新保持所选 Task/Run；生命周期 mutation 继续消费所选 Task 的当前 sealed action/fence，不得改投聚合行默认的最新 Task。Target 工作区清理列表汇总各关联 Task 的工作区；单项清理使用该项所属 Task 的身份和读取版本，不能借用当前选中 Task 的版本。

## Continue：agent strategy

普通 Continue 延续当前 Task。请求必须显式给出目标 runtime agent 和新消息。

步骤：

1. 解析 Task 和 Target。
2. 验证 actor 对 Target 可见。
3. 读取当前 AgentConversation 和目标 agent。
   MR/PR 评审的 operator Continue 同样先由原 provider adapter 实时读取外部对象状态；已 merged/closed 时在 Stop、后继 Run claim 和 Workspace 准备前明确拒绝，保留旧 Run/交付事实。读取失败不能推断为终态，实时 HEAD 不能替换原评审已受理的固定提交。
4. 读取 Task 的 `workspaces[]`。目录存在时验证 id/path/project/remote 不变；目录缺失时只允许按当前声明项目集合修复 repository metadata 并由 Workspace owner 重新分配路径。provider 实时状态可以刷新 `base_branch` 准备输入。
5. 在停止任何进程前，只读检查 Task store、全部 Workspace 所在卷、Workspace root/path 类型，以及现存 repository Workspace 的 Git worktree 有效性。当前仍有 active Run 时，全部登记 Workspace 还必须继续存在；缺失目录时 Continue 在这里失败，旧 Run ownership、进程和 Artifact 均不改变。没有 active Run 的 retained Task 仍可在后续准备阶段重建已经按策略清理的目录。
6. 只读预检通过后，如果当前 Task 有 active Run，同步执行 Stop Run；只有确认进程 ownership 已解决后才继续。
7. 如果 Stop Run 失败，返回 `run-stop-failed`，不创建新 Run。
8. 如果目标 agent 等于当前 agent，且 adapter 支持 native resume、private handle 有效且会话可恢复，则复用当前 AgentConversation。
9. 其他情况创建 child AgentConversation。目标 agent 可以与当前 agent 相同，也可以不同；source native handle 可以缺失。
10. 在 Task state mutation 中创建新的 Run，并合并当时最新的 `workspaces[]`，避免并发追加登记被旧快照覆盖。
11. Run claim 提交后，重复检查存储并重新验证、准备目录；通过后把 `primary` 作为默认 `cwd`。这次检查覆盖预检之后发生的并发变化；它失败时按 successor launch failure 收敛，但不能把不可预测的进程启动错误描述成完全事务化切换。
12. `prompt.txt` 只写入本次 Run 的新用户消息和 adapter 执行契约，不复制历史对话。
13. 复用 AgentConversation 时调用 adapter native resume；创建 child AgentConversation 时启动目标 agent 的新 native session，并提供 Task、已登记 Workspace 集合和来源 lineage。
14. 如果 Task 绑定外部 provider Target，新 Run 必须继承该 provider 的 delivery/writeback contract；same-agent resume 和 cross-agent child AgentConversation 都不能把契约降级成本地 prompt。每次 Run 的 writeback action/response 写入该 Run Artifact，再由 TaskService 按当前 Run ownership 投影到 Task 根目录。

Agent strategy 不读取历史聊天消息，不把一个 runtime 的 native handle 传给另一个 runtime，不修改终态 Run。跨 agent 时，Task 连续性来自同一个 Task、已登记 Workspace、Artifact 和 lineage；目标 agent 获得的是新的 native session。

准备阶段失败也必须保留 exact Run 的已受理输入，允许操作者修复环境后以新消息 Continue。对 strict latest Run 严格终态为 failed、从未 started 且 run-context 不存在的情况，显式 agent Continue 只继承 strict Task 身份和已登记 Workspace，使用本次新消息准备后继 Run。此规则不根据 schema 猜测来源版本，也不认证或补造遗失输入；它同时适用于已发布 0.3 在 PrepareRun 失败后未写入输入的记录。原 lane 的完整输入与权限必须独立核对，不能降级为普通本地 prompt。已经 started 的 Run、损坏或身份不符的现存 context 仍拒绝；IM private reply handle、workflow input、review publication 与其他 delivery 权限仍须各自的完整证据。

## 内部 Stop Run 原语

Stop Run 只供 Continue 和 Cancel 在内部解决当前 active Run ownership，不是 Status/CLI/IM 的并列产品操作。

规则：

- Stop Run 面向 Task 的 `current_run_id`，不面向任意 pid。
- 成功后 Run 进入 `stopped`，Task 清除 `current_run_id`。如果后续 Run 尚未建立，Task 投影为 `needs-attention`、phase=`stopped`；exact committed stopped Run 仍是人工续办终态，不计 completed/writeback，`terminal_outcome` 保持 `none`。
- Stop 和进程 completion 竞争时，以 Run 终态 compare-and-swap 的第一个成功提交者为准；后到者只能追加审计事件。
- 正常 completion 的提交顺序固定为：校验当前 Run owner、以 file-fsync/rename/directory-fsync 持久化包含完整 Run/Task 终态 patch 的 write-ahead `terminalization_intent`、Run 终态 compare-and-swap、最终 provider output 投影、provider completion/writeback、释放 `current_run_id` 并在同一次 Task state mutation 中按配置写入 `workspace_cleanup_due_at`、最终观察者通知。Task 生命周期文件锁覆盖 ownership 变化，最终 Task state mutation 再校验 Run owner。Run 终态或最终 Task 写入遇到 ENOSPC、或进程在两者之间退出时，都只会留下具备完整恢复输入的 `finalizing` intent；rename 已可见但目录同步失败时，恢复探针和幂等重写确认同一个终态，不重复 provider side effect，也不提前删除 Workspace。若 launch-failure 的 write-ahead intent 本身因 typed persistence error 未能提交，TaskService 必须保留已 claim 的 `current_run_id`，并将错误稳定分类为 `task-store-degraded`；不得释放 Run owner、伪造终态或只返回无类别的 I/O 文本。恢复器验证不可变 Task instance 和当前 Run delivery evidence 后幂等收敛，不要求重启。进程退出后若本次 Run 根本没有留下必须的 provider evidence，恢复器 fail closed 为 `needs-attention` 并保留 Workspace。
- Continue 在同一把 Task 生命周期锁内先完成只读 Workspace/Git preflight，再执行 Stop Run 和新 Run claim。确定性 preflight 失败不发送进程信号、不创建 successor Run，也不转移 `current_run_id`。只要 Continue 通过预检并先取得 ownership，就清除 `workspace_cleanup_due_at` 并复用现有目录；若配置的保留窗口已到且清理先取得锁，Continue 根据仍然保留的 `workspaces[]` 重建缺失目录。
- Cancel 是立即安排处置的终态操作：解决 active Run ownership 后先提交 cancelled business fact，再在所有 Task/state locks 释放后按 `workspaces[]` 启动 Full disposal transaction。Provider 的 Issue close、MR close/merge 使用同一条 terminal + disposal 主线，不等待保留窗口；处置失败不撤销 cancelled。
- stop intent 在进程退出观察之前写入时，Runner 上报 `stopped`；若进程退出已先被观察并提交终态，Stop Run 返回带审计的 no-op。
- Task、已登记 Workspace 目录、AgentConversation、resume handle 和 Artifact 保留。
- 没有 active Run 时，Stop Run 是带审计事件的 no-op。
- 已停止 Run 的迟到完成不得恢复 binding 或改写 Task 状态。
- IM `/cancel [<run-id>|all]` 只取消同一 Target 内匹配的 Task；内部按需调用 Stop Run。

Follow-up 若所有历史 Run 都未进入 Agent，Status Continue 重新进入原 lane 的 Workspace PrepareRun，保留完整原评论批次、源分支和 lane 约束，再附加本次操作员消息。遗失 followup input 时，只允许从同一 authority-scoped Subject 的既有 intake 读取与 strict source Run 的 immutable RequestFingerprint 完全一致的原评论批次；原空批次不获得任何新 pending 评论。缺少该证明时，在新 Run claim 前拒绝，不用分支元数据代替原任务，也不消费、确认或重放新评论。已核对输入在 claim 前封存。任何历史 Run 已启动过 Agent 时，维护恢复及评论队列触发的 Continue 都复用工作区，不重新 reset/clean 未完成工作；评论队列准备只以非强制 checkout 选择源分支，保留本地提交和文件，也让已按策略清理后重建的工作区恢复到该源分支；若最新未启动的失败 Run 又遗失 context，Status Continue 在 claim 前拒绝，不能以普通新消息绕过原 lane 合同。

## Continue 的 Agent 切换策略

目标 agent 与当前 AgentConversation 不同时，Continue 在同一个 Task 和同一组已登记 Workspace 上切换 runtime agent。

步骤：

1. 验证当前 Task、Workspace 登记和 actor visibility。
2. 如果父 AgentConversation 有 active Run，由 Continue 同步执行内部 Stop Run 并确认停止。
3. 创建新的 AgentConversation。
4. 写入 `parent_agent_conversation_id`。
5. 创建新 conversation 的首个 Run。
6. Adapter 可以从父 conversation 和 private handle metadata 推导 source ref；source ref 缺失不阻止基于已登记 Workspace/Artifact 的继续。
7. Target runtime 创建新的 native session，并接收只包含当前 Task、已登记 Workspace、lineage 和新消息的 continuation instruction。
8. 更新 Task 的当前 AgentConversation；Target 默认 Task 指针不变。

Agent 切换不是 import/export。jarvis-box 不转换历史记录。目标 runtime agent 可以根据 instruction 和 source ref 读取它能够理解的源 session，也可以只根据已登记 Workspace 和 Task Artifact 继续。

## Continue：writeback strategy

当 delivery pending/failed 且 provider-ready 内容存在时，Continue 只重试同一 Task 已生成结果的 provider delivery。

规则：

- 只在 writeback pending 或 failed，且待发送内容存在时启用。
- GitLab/GitHub/Jira/飞书项目 comment 和 ChatBridge reply 使用各自 provider writer。
- 不启动 runtime agent，不创建 Run，不修改终态 Run。
- 重放目录服从统一 ArtifactScope：provider command 读取已严格投影的 delivery Run；post-check、MR review 和 ChatBridge 只有在 `task-artifact-projection.json` 的 Task、Run、sequence 与逐文件清单精确匹配时，才可读取 Task-root current-Run alias。无 Run 的 pre-generation lane-owned Task-root artifact 是唯一无 marker 例外。每个 lane 必须明确选择一种所有权路径，禁止 root/latest/sibling fallback。投递目标从 Task 的不可变 `subject` 恢复，历史 Run context 只补充经过该 subject 校验的 provider-specific 参数。
- 成功或失败都追加 writeback audit event，并更新 provider-facing projection；成功后 Task 收敛到 `completed/completed`。可确定且安全重试的失败投影为 `Task lifecycle=needs-attention + Delivery=failed + next_action=retry-writeback`；结果不确定时使用 `Delivery=outcome-unknown + next_action=operator-check` 并禁用重发——系统自己不得重发，唯一的出口是人去目标系统查证后给出裁定：`delivered` 直接收敛为完成，`not-delivered` 把这条 effect 变成一次确定的 `failed` 并接回上面那条原地重投。两个裁定由 policy 在 `actions.continue.attestations` 里列出（未知分支列出两项；不可重试的明确失败只列出 `delivered`，仅用于操作员实际修复投递并查证成功后收尾，不授权系统重发），页面只是它的投影，不自行从 `effects` 推断。
- exact Run 的合法 `failed` receipt 是一个已完成、可解释的 delivery 结果，不是 completion transaction 损坏：TaskService 的正常 completion 与启动恢复都必须保留不可变的 `Run=succeeded` 并完成 Task 终态提交，不得把它当成本地 Artifact 合同失败去改写 Run 终态或投递分类。这条分类同时适用于 provider delivery 和本地 workflow action delivery；两者的 definite/retryable failure 都投影为 `status_group=needs-human`，不得因 blocker 名称不同把 workflow action 伪装成 Run `failed`。raw Task 可保留 execution 终态 `completed/completed`，strict aggregate 再从同一 exact receipt 封存 `lifecycle=needs-attention + delivery=failed`及它的 action policy；旧存储中的 `completed/writeback-failed` 只是兼容编码，不是第二个状态权威。未经裁定的 `outcome-unknown`、`invalid` 和必需 effect 的 `unrecorded` 仍不能完成 finalization，也不能授权重发；`outcome-unknown` 只有被人裁定成一个确定的事实（`delivered`/`not-delivered`）之后才离开这个集合，裁定本身是一条新的 effect attempt receipt，不是对原回执的改写。对于不可重试的明确失败，操作员完成外部投递修复并查证结果已送达后，也可追加 `delivered` 裁定，保留原失败回执；不接受 `not-delivered` 裁定或自动重发。未知回执因此是 attempt 链的终点：只有带裁定的后继才允许接在它后面。
- 已成功发送、原回复文本缺失或没有可信私有重试凭据时不选择 writeback strategy；确定零发送的首次文件临时不可读，可由下述 exact-Run 预检回执授权修复后的原 Run 交付。

ChatBridge 的 provider send failure 与 Agent Run failure 是两个事实。Agent 已成功且 `reply.md` 已持久化时，最终 IM 回复失败不得把 Run 改成 failed，也不得让 Continue 重新执行 agent：

- Run 保持 `succeeded`。旧存储记录可仍是 `status=completed`、`monitor_status=completed`、`phase=writeback-failed`，但 strict aggregate 必须将它归一为 `Task lifecycle=needs-attention + Delivery=failed`；TaskView 不得直接暴露为 completed；
- `reply-error.json` 是公开审计 evidence；权威 delivery failure 只写在 exact Run private `final-reply-receipt.json` 与 sealed `chat_reply_delivery`，其中保存 closed `delivery_state` 及 provider-neutral `failure`（`category`、`retryable`、`attempts`、可选 HTTP status/code、Retry-After、request id）。只有二者完整 fence、attempt identity、receipt digest 和 safe failure 全等时，Status 才能生成结构化说明；公开文件即使存在更具体或相互矛盾的 kind、次数、文本也不得选择状态、重试或说明；
- ChatBridge private receipt 的唯一现代 schema 是 v2：`{task_id, task_instance_id, task_registration_sequence, task_dir, run_id, sequence, receipt_id, attempt_id, attempt, adapter_schema, payload_sha256, delivery_state}`；`chat_reply_delivery` 在 intent、Task receipt event 和投影中重复同一 fence、attempt identity、closed state 与 `provider_receipt_sha256`。Status 只有在两者 identity 和 digest 全等时才投影 definite delivered/failed；任一侧缺失、v1、损坏、ABA、R1→R2、同 state 不同 attempt/digest 都 fail closed。同一 `receipt_id` 只收敛既有 attempt；只有 definite `failed` 且提交新 receipt 才能进入下一 ordinal，最多 3 次。`unknown` 永远不产生新 attempt，也不自动重放；
- 入站 reply token、expiry 与 target 先形成不可持久化的 pre-allocation handle；TaskService 分配完整 Task/Run generation 后，ChatBridge 才能把它绑定为 exact Run `.private/reply-handle.v1.json`。该 bound-handle schema 与 final-reply receipt 的版本独立，不是旧的无完整 generation fence 的 `reply-handle.json`。公开 payload/meta/context、Task root、latest/sibling Run、未经迁移的旧无 fence 格式和缺 token/expiry 的半个 credential 都不得恢复 delivery capability。已发布 0.2 的 latest terminal Run 私有凭据由追加的 Flyway migration 在服务停止时升级：必须证明 released Task registration、exact Run creation event、原 Run context 的 Task/Run/消息/收件目标一致；保留原 token 到期时间，不接纳 Task-root 或 sibling 凭据。迁移只写新的完整 bound handle，不重跑 Agent、不发送消息、不修改历史生命周期。Status Continue 读取已迁移的旧 Run 时，在验证同一 released registration、Run event 与 bound handle 后仅在内存补齐旧 context 缺少的完整身份字段；包含部分 modern identity 的 context 仍拒绝。旧失败 Run 未保存 completion policy 时，后继 Run 恢复原 IM 回复合同。旧私有消息的收件目标必须与原 Run public 入站 sender/conversation type 或显式 target 按已发布 transport 合同独立导出的目标一致（0.2.39 使用的 UVIM 0.0.19 飞书 direct/group 都以 public conversation ID 为 conversation target），不能由私有旧文件单独指定另一收件人。Start、Continue、Status Continue 和 admission recovery 只能读取 selected Run 的 bound handle，并同时校验完整 TaskRunFence、覆盖 private body/target/expiry 的 digest、有效期、regular file/no-symlink；
- reply token 到期只撤销该 token 的回复权限，不删除经完整 private handle 校验的收件目标。过期 token 不得传给发送端；UVIM 只能在平台声明支持该目标类型的主动发送时，沿既有主动发送路径投递。缺失、损坏、跨 Task/Run 或目标冲突的 handle 仍拒绝发送。原入站无需短期凭据的 transport 继续使用其原有投递能力，不得因为没有 bound handle 拒绝继续。已发布 0.2 的 tokenless 记录（token 为空且 expiry 缺失）允许只读解析 exact Run 旧私有入站消息：必须证明 released registration、Run creation event、完整 Task Target，且原 Run public sender/conversation type 或显式 public target 按上述已发布 transport 合同独立导出的收件地址与私有消息一致；只恢复地址元数据，不创建 token、延长有效期或写入新的私有凭据。混合/不完整 credential、缺失旧私有输入和 partial modern identity 仍拒绝。Status Continue 与 lost-Run recovery 必须先校验显式选中的 source Run，再为新 Run 重绑 private handle、重新计算 identity/digest，保留原到期时间；不得只复制公开 handle ID，也不得延长 token 有效期；
- 原回复权限证明缺失或损坏属于发送前失败；只能恢复原证明后由操作者显式重试原结果，每次仍完整核验私有权限，不自动发送或重跑 Agent。已保存的 `chatbridge.reply / reply-handle-unavailable / not-attempted` 失败即使被旧版本标为不可重试，也保留相同恢复能力；读取原完整私有交付收据与历史事实，不修改旧收据或降级校验。其他永久失败和结果未知仍遵守原拒绝规则。
- staging artifact 迁入已分配 Run 时，`JARVIS_COMMAND_RUN_DIR`、`JARVIS_COMMAND_RUN_ID`、reply、outbox、attachment 路径必须一次性重绑到同一 Run；`prompt.txt` 保存本次实际执行的完整 runtime prompt，而不是裸 `OriginalPrompt`。否则 recovery 会执行不同契约或把结果写到错误 generation；
- 重试预算耗尽、永久失败或投递结果不确定时，Status 直接展示结构化原因。操作者可以用 Continue 提交经 exact Run projection marker 验证的 `retry-writeback` receipt；它不读取 service log、不提供 agent prompt，也不会在 Task lock 内发送 IM；
- 只有 sealed `chat_reply_delivery` 中已证明可恢复的 definite failed receipt 才选择 writeback strategy，包括上述原回复权限预检失败的历史分类；其他情况仍须 receipt 标明 retryable。尚未开始 effect 的 `pending` 与已持久化 intent 的 `claimed` 投影为 delivery pending/outcome unknown，禁止重发；private receipt 或 Task projection missing/corrupt/conflict 投影为 invalid 并要求 inspect-artifacts；完整匹配的 `unknown` 收敛为 `writeback-outcome-unknown / inspect-writeback`，同样禁止 Continue 重发。

IM送达确认只接受exact latest Run原始发送者。私有bound handle以可选`origin_sender_id`/`origin_sender_digest`扩展记录身份，摘要使用`chat-reply-sender/v1`域并绑定既有credential digest；原opaque ID、credential摘要、token及expiry不变。缺少sender pair的已发布记录继续可读；半pair或摘要冲突拒绝。无token且无expiry的消息可以保存具有完整sender证明的同一私有记录，重建时expiry仍为nil、没有凭据消费事实；半凭据不能按此处理。IM新输入绑定本次sender；Status/recovery重绑仅继承所选来源的私有sender并按新fence重算，公开context和Task首创者不能补权。

停服Flyway追加`20261023_im_reply_sender`，只从已证明released registration、Run creation、消息、Target及凭据一致的exact Run旧私有完整输入补齐sender，原迁移身份保留。现代旧记录未保存该身份时不能从公开payload猜测；保留数据及普通Continue，并开放既有sealed operator attestation作为核实后的同Run补救。此可选裁定与普通新指令并存，不更改waiting-input/user投影或新增管理员待办，也不授权其他群成员通过聊天裁定。

严格缺失子集由既有delivery attestation封存：TaskService把`missing-attachments/v1`及非空唯一名单写成同一Run的后继effect；存储字段`missing_attachments_json`为规范JSON数组字符串，保持回执的值比较及历史前缀不可改写约束，TaskView以`missing_attachments`数组投影。普通完整未确认集合仍使用已发布的`not-delivered`。新标识不被旧reader识别，旧reader须拒绝该Task，不能忽略名单后全量重发。发送适配器在完整原payload摘要匹配后再次核实名单属于当前未确认集合，并将其余文件按用户裁定加入私有v2回执的`confirmed_attachment_indexes`。该字段只补充`attachment_count`连续前缀之外的确认索引，严格递增且不与前缀重叠；缺字段的旧回执仍只有连续前缀语义。后续真实发送只选择未确认索引；失败、内容暂不可读及再次unknown均保留这项进度，完整payload摘要不变。追加Flyway `20261023_im_attachment_selection`在startup lease前通过既有Task存储迁移和严格校验接受已发布数据，不猜测历史缺失名单，也不改写旧结果或自动发送。

已有完整原内容回执的交付重试遇到本地文件缺失或读取权限错误时，本次尚未发送，写新的exact-attempt `failed/not-attempted/retryable` 私有回执并保留原payload摘要及已确认前缀。修复后仍复验完整原内容，只交付未确认部分。不得把部分可读文件当作新payload、清空前缀、沿用旧attempt回执或要求Agent重做。没有可信原内容回执的首次预检失败不因此获得旧交付重试权限；身份损坏、私有或越界路径继续拒绝。

首次文件预检在任何最终发送调用之前遇到ENOENT/EACCES时，可以追加同一v2回执的显式预检形状：`preflight_only=true`、完整payload摘要为空、独立`reply_text_sha256`、零已确认附件/消息，且为`failed/not-attempted/retryable`。只在exact Run私有目标已核实、原文存在且没有更早交付attempt时建立；这不是未知结果裁定，也不声称已封存尚不可读的附件字节。后续文件预检失败保留同一原文凭据；首次完整读取成功后，必须复验原文摘要、全部合法文件和私有目标，再建立普通完整payload回执并发送。已有完整payload不得降级为预检形状。预检凭据不授权具名确认或unknown重发；缺少该凭据的旧首次失败保留原事实，不从公开文件补造权限。旧完整v2回执的字段和读法保持，旧reader遇到空完整摘要的新增形状会拒绝重试。

Jarvis Box 不解析 provider 名称、`detail`、HTTP 502 文本或日志。错误分类属于 `uv-im-connector` adapter；重试次数、Task 状态和人工介入策略属于 Jarvis Box。

### ChatBridge durable reply transaction

ChatBridge lifecycle 只有 `prepare-recovery` 与 `complete-reply` 两种 typed `CommandChatBridgeLifecycle`。两者都要求非空、稳定的 `receipt_id`，并由 TaskService 在 exact Task/Run lock 下复验不可变 registration；空 receipt 不能绕过幂等。

`complete-reply` 的主干严格为：

1. 正常 Run completion 只提交 execution terminal receipt，并把 Task 投影为 exact `chat-reply-delivery-pending`；不得先暴露为 delivery-complete，也不得调用 legacy `OnComplete` 裸发送；
2. TaskService 在 lock 内持久化 `chat_reply_delivery_started` 与 `terminalization_intent(kind=chat-reply-delivery, delivery_state=claimed)`；
3. 释放 lock 后，TaskService 把 sealed `ChatBridgeDeliveryPlan` 交给 ChatBridge 执行一次 IM transport effect；plan 包含完整 Task/Run fence、`receipt_id`、`attempt_id`、ordinal 与 adapter schema；
4. ChatBridge 先在 exact Run private 目录写 v2 claimed，effect 后写 delivered/rejected/unknown，并把同一 attempt identity 与 receipt digest 返回 TaskService；
5. TaskService 复验 plan/result identity，在同一 exact Run fence 内持久化 `chat_reply_delivery_receipt`，再派生 execution outcome 与 delivery outcome 的正交终态投影。delivery acknowledged 不得把 failed/stopped Run 改写为 succeeded。

进程在 claimed intent 之后退出时，recovery 只能通过只读 receipt observer 读取并校验同一 v2 private receipt：匹配则用原 digest 收敛，找不到 receipt 就写 `delivery_state=unknown`，冲突则 invalid；observer 永远不能执行旧 closure。单纯 `status=completed`、Agent Run succeeded、private receipt 单边存在或 Task delivery map 单边存在都不是 IM 已送达证据。`retry-writeback` 也走这条 Command；新 receipt 由前一 exact attempt identity 与 next ordinal 派生，不能由 display reason 文本决定。

## 原生终止的有界自动 Continue

只有 TaskService 在 exact current Run 下接受的原生终止事实可以新增自动恢复权限，允许的类别固定为：

| 原生终止 | 同一 Task 的恢复方式 | 边界 |
| --- | --- | --- |
| Codex model capacity | 15、30、60、120、240 秒退避，附少量稳定抖动，再原 Agent、原模型、原 native session Continue | 不切 Agent，不要求上游提供额度重置时间 |
| Codex usage limit | 按 canonical 配置的 fallback order 选择已启用且命令可用的下一 Agent，以 child AgentConversation Continue | 保留工作区、原目标与 Artifact；不复用 Codex handle，不改全局首选，不在候选间循环 |
| Claude Code＋DeepSeek context 超限 | 原模型、原 native session 执行一次必要的上下文压缩，确认压缩成功后 Continue | 不清空会话、不切模型或 Agent；压缩失败或再次超限立即停止 |

一个 Run 仍对应一次 CLI 调用。context 恢复先以 Continue 调用同会话 `/compact`；该 Run 的成功只保存原生压缩回执，不代表原任务交付完成。TaskService 持久化压缩成功和下一次普通 Continue 的来源，再由既有恢复 sweep 沿用同一会话继续原任务。压缩和恢复工作各占一次累计预算；CLI 退出 0 但没有原生压缩成功及 boundary 证明时停止，不重复发送未改变的超限输入。

Runner 仅适配 stdout 中受信的顶层原生终止事件。Codex exec-json 0.163.0 的 `turn.failed.error.message` 使用经该版本源码及原生 CLI 验证的窄映射：capacity 为完整固定消息；usage limit 为该版本的明确额度耗尽消息。Claude stream-json 的版本闭集为2.1.235、2.1.304，同时要求 init 的版本及 DeepSeek 模型、终态 `result.is_error=true` 和 `terminal_reason=prompt_too_long`，回执保留该次 init 的实际协议版本；旧2.1.235回执保持可读。二者还必须最终非零、非 signal、非 timeout、非取消退出，并绑定完整 Task registration、Run generation 与 AgentConversation。闭集以外的版本或未知事件不获得权限。助手/工具正文、普通 stderr、日志片段及中间错误后成功均不触发恢复。版本适配本身不代替目标CLI的真实超限、压缩和继续交付资格；完整链路结果单独记录。

capacity 自动 Continue 必须能确定原模型：优先使用本次启动已固定的模型；使用 CLI 内置默认值时，只允许本次 `thread.started` 唯一对应的原生会话元数据和启动后的当前 `turn_context` 提供模型，并核验版本、provider 与当前工作目录。历史 turn、其他会话或无法验证的记录不能补造模型或恢复权限。无法确认原模型时仍保留受信的中断事实，以具体原因停止自动恢复，并跳过尚未开始的成功产物发布收尾。

TaskService 将来源事实与恢复意图一起持久化，正常结算旧 Run 为 failed；等待不占用 Agent 进程槽位。所有类别共用一条最多五次的恢复链预算，重启、新 Run、类别变化均不清零；context 压缩至多一次，usage 候选不得回到已使用 Agent。每次 Continue 在 Task lifecycle lock 内复验完整来源、当前状态、到期时间、预算和旧 claim，再与后继 Run 原子提交认领结果。重复回调、并发唤醒和重启只能创建一个合法后继。取消、人工 Continue、Task 换代或已有后继立即使旧意图失效。

恢复复用原 lane 的 PrepareRun、目标、已登记 Workspace 和交付合同，仅继续未完成工作。原 Run 历史不改写成功。三类中断没有成功 Artifact 时跳过需要成功产物的发布收尾，不能把缺少 workflow-result.json 误报为外部回写未知；已开始的外部 effect 仍执行原有 receipt/unknown 保护，禁止自动重发。恢复成功解除当前异常；预算、context 次数或候选耗尽，以及无法安全保留原会话时停止并显示具体原因。

Status/CLI 只消费同一 TaskView 的 runtime_recovery 投影：原因、到期时间、次数、状态和停止原因。等待为 machine-owned，is_processing=false；恢复中的 Agent Run 按普通执行投影。没有新恢复权限的历史失败 Task 不因启动扫描自动运行。持久字段经目标版本既有 Flyway 清单验证，不创建全局 cooldown、availability router、隐藏队列或通用重试框架。

普通网络、429/5xx、认证/权限、未明确归入 Codex usage limit 的余额文案、业务失败、缺输入/文件、未知失败，以及其他 Agent/provider 的同名错误均不获得恢复权限。Provider publication guard、workflow contract、writeback 和外部 CI 等待继续属于 completion finalization；agent-output-invalid 的显式 Continue 仍需 exact Run 私有发布校验回执，其余写回恢复遵循原保护。

## Continue：recovery strategy

`tasks continue <task_id>` 在 `monitor_status=recovery-required` 时选择 recovery strategy。它只处理明确选中的一个 Task。

适用对象：

- `recovery-required`

Recovery strategy 不执行 native resume，不接受用户对话消息，保持 source Agent；它不从失联、错误文案或全局 availability 推断 Agent 切换。三类受信原生终止的自动 Continue 是独立的 Task 内权限，不能借给 lost-Run recovery。后继 Run claim 仍在 lifecycle lock 内拒绝 R2、Task ABA 和 lane 漂移。

`recovery-required` 必须来自进程/结果证据矛盾，例如非终态 Run 记录的 PID 已不存在且没有终态结果。运行中进程的 idle time 和 CPU 使用率只能作为观测数据，不能触发 recovery；agent 等待网络、CI 或模型响应时低 CPU 是正常状态。

服务启动和周期恢复只处理已经由进程证据判定为 `recovery-required` 的旧 Run owner：先排除本进程仍在启动的 Run；进程退出已被观察时，本地 Runner 在结果持久化、资源处理和 TaskService finalization 完成前继续持有该 Run 的 completion ownership，恢复器同样必须排除该 Run。这个 ownership 只属于当前服务进程，不持久化；服务重启或 Runner 释放 ownership 后，已有 durable terminalization intent 的 Run 由 terminalization recovery 幂等重放，否则仍无终态且进程证据仍为丢失的 orphan Run 回到 lost-run recovery。Runner 的 completion observation 与 recovery ownership fence 经过同一个精确到 Run 的进程内仲裁，恢复器只有在赢得该仲裁，并在 Task lifecycle 锁下重读状态后证据仍成立时才执行 fence，不向已消失、可能复用的数字 PID 发信号。fence 成功只释放旧 Run/process owner，不能把 Task 降级为普通 `needs-attention`；Task 必须继续投影 `monitor_status=recovery-required` 和 recovery Continue policy，直到用户 Continue 创建新 Run 或 Cancel 终结 Task。该动作本身不创建新 Run。

Server/launcher adapter 只运输 typed recovery observation 或 launch receipt，不能传入 Task patch、直接 append event 或选择 latest 指针。每个现代 observation 都带 immutable Task registration；Run-scoped observation 还带 exact `run_id` 与 `sequence`，Task-level zero-Run audit 明确带空 Run 和 sequence 0。仅历史 pre-registry zero-Run 可经独立 legacy 标志缺省上述 registration/Run identity，且该分支不能创建或选择 Run。TaskService 在同一 lifecycle lock 中复验 Task registration、active Run 或 strict canonical idle Run；目录、展示 Task ID、PID、latest/current cache 与错误文本均不是写权限。相同 Task ID/目录被重建为新 instance、R1 在 R2 后迟到、或当前 admission/terminalization 已拥有 Task 时，旧 receipt 不得写 Task projection、Run outcome 或 successor audit。

recovery effect receipt 由 immutable Task instance、Task registration sequence、Run id/sequence、typed operation 和稳定 effect/attempt identity 派生。`Reason`、`Error` 和重新观察时间只作为审计 payload，不能进入 receipt identity；已记录的同一 receipt 必须在 command 入口幂等跳过，不能只避免重复 event 却用新错误文案重写状态。active Run outcome 只通过 exact owner transition 结算；idle outcome 必须先在 strict registry 确认同一 canonical Run 并以 canonical idle transition 结算。若 storage admission 已经释放 current owner 但仍由同一 canonical lost Run 支撑 waiting 状态，服务只追加该 exact Run 的 receipt audit，不改 admission projection；历史 Run 不得借此覆盖或携带 successor 的状态。

对需要 reap 存活进程的 lost-Run observation，TaskService 固定执行 `exact owner + immutable process snapshot/reap intent durable checkpoint → effect-start durable checkpoint → 锁外 ReapProcess → durable outcome receipt → exact owner recheck/state commit`。checkpoint 记录 Task registration、Run、pid/pgid、process generation、containment 和稳定 receipt；因此 state commit 在 effect 前后失败时，重试能从 ledger 继续结算已知 receipt，而不会依据错误文本或 PID 猜测并再次发信号。若已写 effect-start checkpoint 却在 receipt 前中断，结果一律投影为 `recovery-reap-outcome-unknown`、保留 exact process/recovery intent 并要求 inspect；禁止盲重放。receipt 可以在同一 immutable Task registration 下作为历史 Run 审计落盘，但只有 recheck 后仍为 exact current owner 的 Run 才能改变 Task projection；新 Run 或重建 Task instance 不受旧 receipt 污染。

managed Runner 的 agent-browser cleanup 使用同一个 effect transaction：`完整 Task registration + current Run fence → durable cleanup intent → durable effect-start → 释放 Task lifecycle/state lock → 关闭 exact Run socket/清理带 Task+Run marker 的进程 → durable receipt → exact owner recheck/projection`。intent、effect-start 和 receipt 的稳定 identity 必须包含完整 Task registration、Run generation、socket 与 source。receipt 已落而 Task projection 写失败时，只从 receipt 重建投影，不再次关闭；effect-start 已落但 receipt 缺失时 outcome 为 unknown，向 Runner 返回明确 effect error 并禁止盲重放。旧 Task instance、历史 Run 和丢失 owner 的 effect 不能向当前 Task event ledger 追加审计，也不能触发 browser closer。

## Completion

Run completion 只影响匹配的 Run。

规则：

- completion 通过 compare-and-swap 写入终态。
- 重复 completion 被忽略或记录为重复事件。
- Runner 先写 Run 私有 Artifact，再把 completion 交给 TaskService finalizer。TaskService 只有在 `current_run_id` 和 sequence 仍匹配时才先提交 write-ahead intent；取得该 ownership 的 completion 才能继续提交 Run 终态、追加唯一的 Task 级 `run_completion_finalized` 事件、以稳定 event id 写共享 work-ledger completion，并进入已持久化的原生恢复等待或外部完成回调。managed Runner 不另写 `exit` 或第二条 completion 账本。
- TaskService 在跨进程 Task 生命周期锁下把完整 Run/Task 终态 patch 写入 durable terminalization intent，再执行 Run 终态 compare-and-swap、生成最终 provider output projection、完成 provider delivery，并通过最终 Task state mutation 重新校验 owner、写入 `completed` 与 `workspace_cleanup_due_at`。需要 provider 写回的 lane 必须在当前 Run 目录留下成功 action；Task 根目录只是当前 Run 的展示投影，历史成功 marker 不能满足新 Run。到期清理由同一 Task 生命周期锁和 Workspace lease 保护；Cancel 与 provider terminal lifecycle 才执行立即清理。锁释放前其他 Web/CLI 进程不能取得该 Task，晚到的旧 Run 不得改写状态、最终输出、delivery evidence 或删除新 Task instance 的目录。
- runtime adapter 上报 Task event 时必须通过 `Advance` 携带 structural Task ref 和 `{task_id, task_instance_id, task_registration_sequence, run_id, sequence}` 完整 fence；缺少 exact owner 或 Run 已失去 `current_run_id` 时拒绝写入。TaskService 写入的最终事件也必须携带同一完整 fence。
- 从 event log 重建或投影时必须先选择唯一、不可变的 Task registration，再只在该 Task 代际内按 Run `sequence` 选择最新 Run；旧 Task 即使复用同一目录、TaskID、RunID 和 sequence，其迟到事件也只保留为原始审计事实，不得参与新 Task 的 Run 列表、Agent Session、progress、状态、phase 或 result ref 投影。只有不存在任何 Task registration linearization 的历史 ledger 才允许 pre-registry 兼容读取。
- completion 不触发隐藏队列消费。
- 外部平台任务的可选 IM 完成提醒消费 TaskService 的终态 TaskView 通知；启动及周期恢复扫描补处理遗漏的回调。command/issue adapter 在 PrepareRun 中固定完整 Task/Run 身份和通知来源，发送前复验 Run context，再通过 `completion-notification` effect authorization 取得发送权限。Run 私有回执与发送锁按完整 Task/Run 身份派生，固定 provider、connector、收件人及 payload digest。已存在 effect-start 时不重复发送，缺少 ACK 视为结果未知；只有尚未取得 effect-start 的本地 dispatching intent 可继续申请授权。该提醒不是原平台写回的必需步骤，不改变 Task outcome，也不授权重新执行 Agent。
- 后续用户输入必须通过 Continue 显式创建新的 Run。

## Active Run replacement

同一 Task 同时只能处理一个 active Run。Agent strategy 的 Continue 表达“用新消息继续当前 Task”的 replacement intent：

1. Status inspection 从同一个 sealed TaskView revision 计算完整 Task registration、作为 continuation Artifact/Session owner 的 strict latest source Run（零 Run时显式为空）以及 strict current Run 预期（有 current 时必须是 registry 证明的 exact Run；没有时显式为 zero-current）。selected Run 只控制浏览，不能改写该 source。该展示 expectation 必须交给 TaskService owner planner；planner 只在同一 Task lifecycle lock 内复验它仍等于真实 aggregate 后，才签发 opaque `ContinueSourceFence` seal。
2. seal 绑定完整 TaskRef、source/current generation、operation=`continue`、strategy 和 lane。每个 production lane adapter 只能原样运输这枚 opaque capability；可读取展示字段但不得在 transport、prefetch、workspace prepare 或 replay artifact 读取后按 mutable `latest/current` 重新选择 owner，更不得以复制/改写/重建字段取得新 seal。保留 R1 seal 而把字段替换为 R2，或 Task ABA 后复用旧 seal，都是无效 capability。
3. TaskService 在同一 Task lifecycle lock 内、任何 Continue preflight、Stop/process signal、durable admission/replacement intent、Run 目录创建或 Run claim 之前，先验 seal，再复验完整 Task registration、strict latest source Run 与 strict current Run 预期。R1 页面命令到达时若 R2 已成为 latest/current，或原 zero-current 后已出现 R1，立即以 typed conflict 失败，既不停止新 owner也不创建后续 Run/Artifact。
4. 没有 active Run 且 expectation 仍匹配时直接创建后续 Run。
5. 存在 active Run 且 expectation 仍匹配时先等待显式 launch-resolution barrier，再执行 Stop Run，并等待进程 ownership 已解决；不能把尚未发布 PID 的合法启动误判成丢失进程。
6. 停止成功后，再以停止后的 `current_run_id` 和 `latest_run_sequence` 为 compare-and-swap 条件创建后续 Run；并发进程已取得或完成过新 Run 时当前请求失败，不覆盖新 Run，也不复用 sequence。停止失败时返回 `run-stop-failed`，不创建新 Run。

jarvis-box 不创建后台排队 Run，也不要求调用方先额外提交 Stop Run。用户不再获得“只停止、不决定 Task 后续”的第四个状态；需要终结时使用 Cancel。

## Cancel

Cancel 终结当前 Task。

Provider 同对象事件锁只保护受理至 exact Run claim 发布；进入已登记 Run 的准备阶段时由原 adapter 释放该锁，使关闭/合并事件能提交原生取消，不等待外部准备程序或 Agent 启动。重复事件仍由原 admission/terminal receipt 去重，Task/Run 的取消、仲裁和处置仍只由 TaskService 完成。

1. 解析 Task 的当前 Run ownership。
2. 有 active Run 时解析其 launch owner。尚未开始 Agent dispatch 且由本服务进程持有的准备阶段，先按下一步持久化 exact cancellation intent，再取消该 owner 的准备 context，并在全部 lifecycle 锁外等待其 launch-resolution barrier；准备进程实际退出或已启动进程的精确补偿停止完成后，由原 launch owner 结算同一 intent。等待完成必须重读并核对同一 Task/Run 及取消回执，不能将 barrier 关闭或 PID 为零单独视为停机证明。已进入 dispatch 的窗口不等待自身同步启动回调，仍由严格 Stop 与 PID 绑定失败补偿解决实际进程；无匹配本地准备 owner 时仍按既有严格进程证据处理，不猜测进程已经消失。等待发生在 TaskService mutex 之外，不能与同步 completion callback 互锁。
3. 在任何 Stop/kill/reap 副作用前，以当前 Run owner、sequence 和不可变 Task instance 为条件写入 cancellation terminalization intent；intent 保留原 PID/Run ownership，写入失败时不发送进程信号。
4. 若不存在 current Run owner 却仍有 PID/PGID，立即 fail closed，不发信号、不清 Workspace、不清进程证据；否则同步调用内部 Stop Run。无法证明进程已停止则保持 `finalizing/cancelling` 和 intent，由同一请求或周期恢复器重试。`recovery-required` 且没有 pid/pgid 时，以 Task/Run owner compare-and-swap 固定旧 Run。
5. Task 原子写入 `status=cancelled`、`phase=cancelled`、`current_run_id=""` 并清除 terminalization intent；已提交 cancellation intent 拥有终态仲裁权，竞态 completion 只能被忽略。Task、Run、Workspace 登记和 Artifact 继续保留。
6. 释放全部 Task/state locks 后，按冻结的 TaskRef、Workspace registry revision 和 canonical idle RunRef 启动 Full disposal transaction；每项按 intent/effect-start/receipt/reproject 推进。失败、unknown 或 partial-exhausted 只投影 disposal 义务和 operator action，不能把 Task business state 改回 `finalizing` 或 `needs-attention`。

已冻结非空 Run 的终态回执遇到纯进度 revision 更新时，只在原 Task registration、Run id/sequence、current/latest 均仍相同且 Task running、Run 非终态时，允许将当前 CAS revision 先持久化到同一回执再取消；R2、Task 换代和已进入 finalizing 的意图不获得该权限。零 Run 准入使用独立规则：回执的 Run id 为空且 sequence=0，原 Task registration 完整不变，当前 strict Task 仍为 accepted、current/latest 均空、OperationalRuns 与 HistoricalReadOnlyRuns 均为空，才允许把只向前推进的 revision 持久化回同一回执，再由 TaskService 按完整 fence 取消。工作区物化重试推进 revision 不丢弃原取消义务；一旦首 Run 已认领，旧零 Run 回执不得跟随或重新选择该 Run。CAS 冲突只沿同一完整身份做有界重读，不盲重试停机失败或未知结果。

已发布 0.2 的 external close/merge v2 receipt 由停服 Flyway 导入带原始字节和 digest 的 v5 receipt；现有 v4 receipt 继续原样读取。finalized 只保留去重和观察事实，不重建 Task、不重新取消。未完成 receipt 保留原 Task registration cutoff 和已冻结 registration 集合；在停服切换时，仅为仍匹配的 registration 固定一次现代 Task/Run fence。重试迁移不得重新选择后继 Run，重投事件只能消费该冻结集合，不能取消 cutoff 之后或相同名称的新 Task。旧 receipt 的 `received_at` 只是合并被观察到的时间，漏斗可以记录 `merge_observed_at`，不得补造 Provider 的 `merged_at`。

## Lane continuation preparation

Status、CLI 与维护后的 Continue 保留同一 source fence，并由原 review / workflow adapter 的 PrepareRun 重建后继 Run 的输入、prompt 和 Agent 环境。review 固定源 Run 的 immutable admitted commit 与分支，以已登记工作区准备本次 review artifact 和完整产物要求；不能用新操作员消息代替审查合同。workflow 从 exact source Run 核对原 versioned input 的 Task/Run handles、Subject 与 lane，保留已发布 schema、opaque inputs 与旧 schema 的 action grants，只重绑后继执行 handles；同一 adapter 重新提供 workflow 合同和本次消息，不把历史 prompt 或聊天记录复制成新指令。已经运行过的工作区和未完成文件继续保留，不通过重新 clone 或 reset 恢复。workflow-result.json、review-summary.json 与 comment.md 由 Agent 按合同产出，review/workflow 的最后一条聊天文本不能覆盖这些文件。普通 agent 与 lost-Run recovery strategy 共用该准备路径；writeback-only retry 仍不创建 Run。

## Prompt Contract

Persistent prompt Artifact 只包含当前 Run 的输入。

允许：

- Start: 首次用户 prompt
- Continue agent strategy: 新用户消息
- Continue recovery strategy: jarvis-box 生成的恢复 prompt

禁止：

- 历史用户/助手消息数组
- runtime session compact 内容
- cross-agent source ref
- resume handle value
- provider token

## 跨 Lane 的任务收口

一个业务目标可能经过多个 Lane 和多个 Task。上游 Task 的执行失败与业务目标最终完成是两个不同事实：前者必须保留用于审计，后者用于计算当前是否仍需人工处理。

当成功后继 Task 通过完整 predecessor TaskRef 指向处于 `needs-attention` 的前置 Task，且两者具有相同的规范化 provider/project/subject 时，Jarvis Box 将前置 Task 的有效状态投影为 `superseded`。后继 Task 必须完整成功；失败、部分完成、回写收尾失败、bare `source_task_id`、同名 Task 或仅 subject 相同均不足以收口前置 Task。source Start 在首个 admission snapshot、Task state、Run context 和 lineage event 中同时持久化 source 的 instance/registration sequence，不能在后续投影时按裸 ID 反查。

历史数据缺少 lineage 时，操作人员确认闭环后可执行：

```bash
jarvis-box tasks supersede <旧 task_uid 或精确 Task 目录> --by <成功 task_uid 或精确 Task 目录>
```

该命令只记录任务关系，不运行 Agent、不访问 provider、不补发历史评论。输入只负责选择；TaskService 必须拒绝歧义或 pre-registry Task，并把两端当前 registration 固化进同一个 `supersession_link_receipt`。随后 API、CLI 和状态页会使用同一有效状态投影。

Status 工作项排序消费同一 TaskView 的业务活动证据：Task 创建、Run 创建/开始/完成及 Effect 完成时间的最大值；资源维护更新 Task.updated_at 不构成新的工作活动，不改变工作项或目标主任务的优先展示顺序。该排序不写入生命周期事实。
