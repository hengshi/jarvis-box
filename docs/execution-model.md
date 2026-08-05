# 执行模型

本文定义 jarvis-box 当前的对象模型和状态机。实现代码必须以本文件和 [architecture.md](architecture.md) 为契约。

## 三个生命周期操作

jarvis-box 只有三个会改变 Task lifecycle 的产品操作：

| 操作 | Status API | CLI | 结果 |
| --- | --- | --- | --- |
| `Start` | `POST /status/api/tasks/{id}/start` | `tasks start <id>` | 创建新 Task、新 AgentConversation 和首个 Run。可以引用旧 Task，但不改写旧 Task。 |
| `Continue` | `POST /status/api/tasks/{id}/continue` | `tasks continue <id> [...]` | 延续同一 Task。服务端按状态选择 agent continuation、lost-Run recovery 或 delivery retry。 |
| `Cancel` | `POST /status/api/tasks/{id}/cancel` | `tasks cancel <id>` | 终结 Task；存在 active Run 时先解决其进程 ownership。 |

Inspect、list、verify、reap 和 clean 是只读或维护操作，不属于 Task lifecycle。Native resume、cross-agent child conversation、Stop Run、Recover Lost Run 和 Retry Writeback 都是 `Continue`/`Cancel` 的内部策略或底层原语，不是额外的产品操作。

异常不会创建第四种 lifecycle 操作，也不应通过 Start 伪装成恢复：需要保留原 Task 时使用 Continue，需要放弃原 Task 时使用 Cancel。Start 只表达创建一个不同的新 Task。

## Target

`Target` 是外部工作身份和可见性边界。

示例：

- GitLab issue、merge request、commit、note
- Jira issue
- IM conversation，包含私信、群组和频道
- status 手动 Task
- scheduled maintenance 产生的可见工作

字段：

- `id`
- `key`
- `kind`
- `title`
- `visibility`
- `current_task_id`
- `created_at`
- `updated_at`

规则：

- `key` 必须稳定。
- IM Target key 使用 provider + connector + conversation id。
- IM `/start <任务描述>` 创建新的 Task 和 AgentConversation，并原子更新 Target 默认 Task；它不停止该 Target 已经运行的其他 Task。空 `/start` 不改变绑定。
- Target binding 只保存 `current_task_id`；Run id、Run 状态、Run 目录和 runtime session 不得复制进 binding。
- IM message-to-Task index 用于引用消息反查，不改变默认 Task。解析优先级为显式 id、parent/root/thread 引用、默认 Task。
- Task/Run completion 只能更新所属 Task/Run，不能更新 Target 默认 Task。
- 旧 Task 仍可通过 Task id 在 `/status` 中访问和继续。
- Target 不存储 provider reply token、resume handle 或 raw inbound payload。

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
- `subject`: 创建时登记的 provider、kind、project、number；仅外部对象触发的 Task 存在
- `workspaces[]`
- `terminalization_intent`: 仅在成功/取消终态副作用尚未全部提交时存在的 durable recovery record；completion intent 同时保存不可变 Task/Run identity、完整 Run 终态 patch 与 Task 终态 patch；post-registration skip 还显式保存 skip reason，并关闭本次 Run 的 provider writeback 要求
- `created_by`
- `updated_by`
- `created_at`
- `updated_at`

规则：

- Task status 描述逻辑工作，不描述 pid。
- `subject` 是 immutable canonical identity；外部 URL、Artifact、分支名和目录名都不能反推或改绑它。
- Task 可以在用户继续时从 `completed` 或 `needs-attention` 进入 `running`。
- `finalizing` 不是可 Continue 状态；服务先按 intent 自动收敛，明确缺少 provider evidence 时转为 `needs-attention`。
- Task 继续必须创建新的 Run。
- Task 不复活旧 Run。
- 内部 Stop Run 成功且后续 Run 尚未创建时，Task 进入 `needs-attention`/`stopped`；它不产生 `waiting` Task 状态。
- Cancel 在发送任何进程信号前先写入保留当前 Run/PID ownership 的 durable intent，把 Task 置为 `finalizing/cancelling`；随后停止 Run、清理登记 Workspace，提交完成后才置为 `cancelled`，不会删除 Artifact。
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
- 迟到完成由 TaskService 追加 `late_run_completion_ignored` 审计事件；失去终态竞态的 Runner 不得追加 `exit`、共享 work-ledger completion 或 provider writeback，也不得重写当前 Task binding。
- Run Artifact 属于该 Run，不是 conversation history。
- Run 不存储 resume handle value 或 cross-agent source ref。

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
- Hermes/OpenClaw native conversation record

规则：

- jarvis-box 不把 AgentSession 当作公开业务对象。
- jarvis-box 不解析 AgentSession 内容来拼 prompt。
- jarvis-box 不把一个 runtime 的 AgentSession 内容转成另一个 runtime 的历史。
- Adapter 可以捕获一个 opaque resume handle 或 source ref metadata。
- 私有 handle value 只在 adapter dispatch 时解析。

## AgentResumeHandle

`AgentResumeHandle` 是 adapter 私有状态。

字段：

- `id`
- `agent_conversation_id`
- `agent_name`
- `kind`: `native_session_id`、`thread_id`、`checkpoint_ref`、`conversation_id`、`opaque`
- `value`
- `captured_by_run_id`
- `status`: `valid`、`missing`、`unsupported`、`expired`、`invalid`、`retired`
- `created_at`
- `updated_at`

规则：

- `value` 只存在于 private handle store。
- 公开 JSON 只可暴露 handle metadata 和 safe status。
- `value` 不得出现在 Run JSON、launch request JSON、public projection response、Artifact、logs、E2E evidence 或公共摘要中。

## Workspace

`Workspace` 是 Task 拥有的一项文件系统区域；一个 Task 可以拥有零个到多个 Workspace。

规则：

- Task 以 append-only `task-state.workspaces[]` 作为唯一归属登记表；每项包含稳定 id、服务端分配路径和可选 repository metadata。
- 已登记项的目录存在时，id、path、project、remote 和 primary 保持稳定，保护其中的工作树与未提交修改；`base_branch` 可以在 Start/Continue 时从 provider 实时状态刷新。若目录从未创建成功或已按登记清理，当前请求可以把 repository metadata 修复为声明项目集合中的合法成员，并由同一个 Workspace owner 重新分配路径。非空集合恰好有一个保留 id `primary`，只用于选择 Run 的默认 `cwd`；空集合不合成虚假 Workspace，Run 使用 launcher 的普通工作目录。
- TaskService 必须先在 Task state mutation 中登记初始 Workspace，最后才逐项创建或 clone。TaskService 是 Task Workspace 唯一清理 owner，不依赖 Runtime Foundation reclaimer，也不通过目录扫描猜测归属。Runner 向每个 runtime agent 注入同一 Workspace ownership contract；active Run 增加仓库时必须使用 `jarvis-box workspace create`，由该命令先原子追加登记，再创建目录。
- active 或 needs-attention Task 的全部已登记 Workspace 可以跨多个 Run 复用。目录缺失时，TaskService 根据登记重建；登记以外的 `cwd`、`workdir`、Run context、Artifact 和目录扫描都不能成为归属证据。
- Run 结束时，TaskService 先持久化带完整 Run/Task 终态 patch 的 `terminalization_intent`，再提交当前 Run 终态、执行 provider completion/writeback 和最终投影；释放 Run ownership 时按 `JARVIS_TASK_WORKSPACE_CLEANUP_DELAY_MINUTES`（默认 20 分钟）原子写入 `workspace_cleanup_due_at`。post-registration preparer 的合法 skip 也使用同一顺序并保存 reason。Provider 回写失败落成 `needs-attention`；持久化瞬时失败保持 `finalizing / retry-finalization`，由服务启动及运行期恢复器幂等重放。Run 终态提交不依赖 Workspace 删除。
- Continue claim 新 Run 时清除 `workspace_cleanup_due_at` 并复用目录；每个 managed Run 在自身进程组退出前持有 Task 级 shared Workspace lease，覆盖运行中动态追加的所有登记项。截止时间到达后，服务在没有 active Run、没有存活的已登记进程身份且没有 terminalization intent 时，先取得对应的 exclusive Task lease，再按 `workspaces[]` 逐项清理；手工 Status 删除使用完全相同的 idle proof。脱离 managed 进程组的进程还会按 `cwd` 和 open-file reference 复核，无法确认安全时 fail closed。清理失败保留截止时间并按持久化退避再次执行。
- TaskService 全量清理完成后原子写 `workspace_disposal_completed=true`，新 Run claim 原子清除它。`tasks clean` 在同一把 lifecycle lock 内重新读取最新 state，只凭这个单一交接凭证删除 Task 目录；没有凭证的终态 Task 返回 `workspace-disposal-not-complete` 及已有 cleanup 结果，不被静默跳过。
- Status Cancel 同样先持久化 cancellation intent，再发送进程信号并终态化 Run。Runner/TaskService 随后先按 Task+Run 标记清理受管后代进程，再尝试清理全部登记 Workspace；Run-owned 进程清理失败会保留 intent，Workspace/Docker 清理失败则把未完成义务和退避期限写入取消终态，避免五秒恢复器无限重放相同事件。intent 不会提前清空 PID 或 Run owner；一旦提交即优先于晚到的 completion，后者不得覆盖取消决定。无 Run owner 但仍有存活 PID/PGID 时取消 fail closed，保留进程与 Workspace 证据。若进程在 Stop 前退出，启动及运行期恢复器先解决该 Run ownership，再做登记式清理。最终状态写入失败时保留 intent，磁盘恢复后自动重放；失败或停止且尚未进入终态处理的 Task 保留目录用于诊断或 Continue。
- 清理目录不删除登记项；Status detail 继续显示每项路径与存在状态，并允许执行受控删除。
- Issue/Jira 的 `execution_project` 不是独立项目来源，只能选择 Task context 中 `candidate_gitlab_projects` / `allowed_projects` 或 canonical provider subject 已声明的成员；`execution_repo` 只能从最终选中的成员派生。非成员值不得进入 Workspace project、remote、prompt、environment 或执行审计；无法得到唯一合法成员时不得构造 clone URL。
- Public projection 只允许 Task detail 的 `workspace_locations[]` 暴露已登记路径；其他任意 filesystem path 都不得公开。

## Start

Start 创建新的 Task、AgentConversation 和 Run。

只有正常完成或已取消的 source Task 可以 Start；`needs-attention`、停止、失联、缺产物或写回未完成的 source 必须先 Continue 或 Cancel。

步骤：

1. Provider adapter 解析输入、Target、actor、visibility 和 dedupe key。
2. 创建 Task 根目录和 `task-state.json`。
3. `TaskService` 选择 effective runtime agent。
4. `TaskService` 在全局 Task 登记锁内分配并持久化新的 `task_registration_sequence`；同一次 admission mutation 写入随机 `task_instance_id`、canonical `subject`（如有）、初始 `workspaces[]` 和最小 `pending_launch`，但不创建 Run。历史 Task state 不在这个入口补登记或迁移。
5. TaskService 检查 Task Artifact 所在卷和每一项已登记 Workspace 路径的磁盘余量。容量不足时 Task 进入 `storage-wait`，没有 `current_run_id`；服务启动及每 5 秒运行的恢复器在容量恢复后重新走原 lane launcher。并发恢复仍由 Task owner/sequence CAS 保证只创建一个 Run。
6. 准入通过后，TaskService 才以读取到的 Task owner 和 `latest_run_sequence` 为条件创建 sequence 为 1 的 Run，再逐项创建或 clone 目录，并把 `primary` 作为 Run 默认 `cwd`。claim 后的 `run_created` 审计写入失败时不得启动进程；Run 分配和 Task ownership 必须按持久化恢复规则收敛，不能制造幽灵 owner。
7. `TaskService` 把本次 prompt 和 canonical run-context 写入真实 Run 目录；原始 provider payload/meta 保留在 Task 根目录，可选 Run preparation 回调只处理依赖最终 RunDir 的 provider-specific Artifact。
8. `TaskService` 按选中的 agent 重建命令参数和每次 Run 的环境变量。
9. `Runner` 再次检查 Task Artifact 所在卷和全部已登记 Workspace 所在卷，然后启动一个进程并生成 Run 私有 Artifact；TaskService 负责 Run 终态仲裁和 Task 投影。Run claim 同时建立显式 launch-resolution barrier，只有 PID 已发布、启动失败或同步终态完成后才解除；Cancel 不用固定时长轮询猜测启动是否结束。

## Continue：agent strategy

普通 Continue 延续当前 Task。请求必须显式给出目标 runtime agent 和新消息。

步骤：

1. 解析 Task 和 Target。
2. 验证 actor 对 Target 可见。
3. 读取当前 AgentConversation 和目标 agent。
4. 读取 Task 的 `workspaces[]`。目录存在时验证 id/path/project/remote 不变；目录缺失时只允许按当前声明项目集合修复 repository metadata 并由 Workspace owner 重新分配路径。provider 实时状态可以刷新 `base_branch` 准备输入。
5. 在停止任何进程前，只读检查 Task store、全部 Workspace 所在卷、Workspace root/path 类型，以及现存 repository Workspace 的 Git worktree 有效性。当前仍有 active Run 时，全部登记 Workspace 还必须继续存在；缺失目录时 Continue 在这里失败，旧 Run ownership、进程和 Artifact 均不改变。没有 active Run 的 retained Task 仍可在后续准备阶段重建已经按策略清理的目录。
6. 只读预检通过后，如果当前 Task 有 active Run，同步执行 Stop Run；只有确认进程 ownership 已解决后才继续。
7. 如果 Stop Run 失败，返回 `run-stop-failed`，不创建新 Run。
8. 如果目标 agent 等于当前 agent，且 adapter 支持 native resume、private handle 有效，则复用当前 AgentConversation。
9. 其他情况创建 child AgentConversation。目标 agent 可以与当前 agent 相同，也可以不同；source native handle 可以缺失。
10. 在 Task state mutation 中创建新的 Run，并合并当时最新的 `workspaces[]`，避免并发追加登记被旧快照覆盖。
11. Run claim 提交后，重复检查存储并重新验证、准备目录；通过后把 `primary` 作为默认 `cwd`。这次检查覆盖预检之后发生的并发变化；它失败时按 successor launch failure 收敛，但不能把不可预测的进程启动错误描述成完全事务化切换。
12. `prompt.txt` 只写入本次 Run 的新用户消息和 adapter 执行契约，不复制历史对话。
13. 复用 AgentConversation 时调用 adapter native resume；创建 child AgentConversation 时启动目标 agent 的新 native session，并提供 Task、已登记 Workspace 集合和来源 lineage。
14. 如果 Task 绑定外部 provider Target，新 Run 必须继承该 provider 的 delivery/writeback contract；same-agent resume 和 cross-agent child AgentConversation 都不能把契约降级成本地 prompt。每次 Run 的 writeback action/response 写入该 Run Artifact，再由 TaskService 按当前 Run ownership 投影到 Task 根目录。

Agent strategy 不读取历史聊天消息，不把一个 runtime 的 native handle 传给另一个 runtime，不修改终态 Run。跨 agent 时，Task 连续性来自同一个 Task、已登记 Workspace、Artifact 和 lineage；目标 agent 获得的是新的 native session。

## 内部 Stop Run 原语

Stop Run 只供 Continue 和 Cancel 在内部解决当前 active Run ownership，不是 Status/CLI/IM 的并列产品操作。

规则：

- Stop Run 面向 Task 的 `current_run_id`，不面向任意 pid。
- 成功后 Run 进入 `stopped`，Task 清除 `current_run_id`。如果后续 Run 尚未建立，Task 投影为 `needs-attention`、phase=`stopped`。
- Stop 和进程 completion 竞争时，以 Run 终态 compare-and-swap 的第一个成功提交者为准；后到者只能追加审计事件。
- 正常 completion 的提交顺序固定为：校验当前 Run owner、以 file-fsync/rename/directory-fsync 持久化包含完整 Run/Task 终态 patch 的 write-ahead `terminalization_intent`、Run 终态 compare-and-swap、最终 provider output 投影、provider completion/writeback、释放 `current_run_id` 并在同一次 Task state mutation 中按配置写入 `workspace_cleanup_due_at`、最终观察者通知。Task 生命周期文件锁覆盖 ownership 变化，最终 Task state mutation 再校验 Run owner。Run 终态或最终 Task 写入遇到 ENOSPC、或进程在两者之间退出时，都只会留下具备完整恢复输入的 `finalizing` intent；rename 已可见但目录同步失败时，恢复探针和幂等重写确认同一个终态，不重复 provider side effect，也不提前删除 Workspace。恢复器验证不可变 Task instance 和当前 Run delivery evidence 后幂等收敛，不要求重启。进程退出后若本次 Run 根本没有留下必须的 provider evidence，恢复器 fail closed 为 `needs-attention` 并保留 Workspace。
- Continue 在同一把 Task 生命周期锁内先完成只读 Workspace/Git preflight，再执行 Stop Run 和新 Run claim。确定性 preflight 失败不发送进程信号、不创建 successor Run，也不转移 `current_run_id`。只要 Continue 通过预检并先取得 ownership，就清除 `workspace_cleanup_due_at` 并复用现有目录；若配置的保留窗口已到且清理先取得锁，Continue 根据仍然保留的 `workspaces[]` 重建缺失目录。
- Cancel 是立即清理操作：解决 active Run ownership 后，按 `workspaces[]` 删除这个 Task 的全部 Workspace，再提交 cancelled 状态。Provider 的 Issue close、MR close/merge 使用同一条 Cancel/清理路径，不等待保留窗口。
- stop intent 在进程退出观察之前写入时，Runner 上报 `stopped`；若进程退出已先被观察并提交终态，Stop Run 返回带审计的 no-op。
- Task、已登记 Workspace 目录、AgentConversation、resume handle 和 Artifact 保留。
- 没有 active Run 时，Stop Run 是带审计事件的 no-op。
- 已停止 Run 的迟到完成不得恢复 binding 或改写 Task 状态。
- IM `/cancel [<run-id>|all]` 只取消同一 Target 内匹配的 Task；内部按需调用 Stop Run。

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
- GitLab/GitHub/Jira comment 和 ChatBridge reply 使用各自 provider writer。
- 不启动 runtime agent，不创建 Run，不修改终态 Run。
- 成功或失败都追加 writeback audit event，并更新 provider-facing projection。
- 已成功发送或内容缺失时不选择 writeback strategy；Continue 回到 agent strategy 或返回明确 disabled reason。

## Runtime Agent Failover

Runtime agent 路由包含两个不同事实：

- `primary_agent`：用户持久配置的首选 agent，例如 `codex`。
- `effective_agent`：当前可用于新 Run 的 agent；正常时等于 primary，failover 期间可以是 `copilot`。

`model-usage-limit` 是服务级 runtime availability 信号，不是 Task 自身失败。处理顺序：

1. 当前 Codex Run 以 `failed` 终态结束，终态不可修改。
2. RuntimeAgentRouter 记录 Codex unavailable、原因、观察时间、refresh time 和 source Run。
3. TaskService 保持原 Task，通过 Continue 创建 Copilot child AgentConversation。
4. TaskService 在同一 Task 和同一组已登记 Workspace 中创建新的 Run。
5. refresh time 前，新 Task、新 AgentConversation 和需要 failover 的现有 Task 都直接选择 Copilot。
6. refresh time 到达后，RuntimeAgentRouter 解除 Codex cooldown；下一次新 Run 再按 primary 选择 Codex。

Failover 不执行 `agent set`，不改写 env file 中作为 primary 的 `JARVIS_RUNTIME_AGENT`，也不把 Copilot native handle 写回 Codex conversation。单个 Run 的进程 env 会写入本次 effective agent。它在外部行为上等价于临时全局切换，但保留 primary，才能在服务重启、并发额度信号和用户改配置时正确恢复。

refresh time 优先使用 runtime 输出的明确 reset time；若输出只有 `model-usage-limit` 而没有可解析时间，使用服务配置的保守 cooldown（当前默认 1 小时）。timer 只是及时触发恢复事件；每次选择 agent 时仍必须按当前时间淘汰过期 cooldown，不能把正确性寄托在 timer 一定执行。

服务重启必须从 service state 恢复尚未到期的 cooldown 和定时器。重复额度信号只能延长同一 agent 的 `unavailable_until`，旧定时器不得提前恢复。已经运行的其他 Codex Run 不被批量停止；它们各自按真实结果结束。

cooldown 到期只影响尚未创建的 AgentConversation/Run。已经切换到 Copilot 的 AgentConversation 继续使用 Copilot native session；不会在中途强制切回 Codex。新 Task 或显式 Continue 到 Codex 时再按当前 availability 选择。

`model-capacity` 默认只触发当前 Task 的 agent 切换，不写全局 cooldown。普通网络错误、认证错误和未知失败不会隐式重跑；当前 Run 以 `failed` 终态结束，Task 进入 `needs-attention`，等待 Continue 或 Cancel。

## Continue：recovery strategy

`tasks continue <task_id>` 在 `monitor_status=recovery-required` 时选择 recovery strategy。它只处理明确选中的一个 Task。

适用对象：

- `recovery-required`

Recovery strategy 不执行 native resume，不切换 agent，不接受用户对话消息。它仍属于 Continue，因为结果是让同一 Task 获得新的 Run。

`recovery-required` 必须来自进程/结果证据矛盾，例如非终态 Run 记录的 PID 已不存在且没有终态结果。运行中进程的 idle time 和 CPU 使用率只能作为观测数据，不能触发 recovery；agent 等待网络、CI 或模型响应时低 CPU 是正常状态。

服务启动和周期恢复只处理已经由进程证据判定为 `recovery-required` 的旧 Run owner：先排除本进程仍在启动的 Run，再在 Task lifecycle 锁下重读状态；证据仍成立时只做 ownership fence，不向已消失、可能复用的数字 PID 发信号。该动作不创建新 Run；后续工作仍由用户显式 Continue，终结则由 Cancel 完成。

## Completion

Run completion 只影响匹配的 Run。

规则：

- completion 通过 compare-and-swap 写入终态。
- 重复 completion 被忽略或记录为重复事件。
- Runner 先写 Run 私有 Artifact，再把 completion 交给 TaskService finalizer。TaskService 只有在 `current_run_id` 和 sequence 仍匹配时才先提交 write-ahead intent；取得该 ownership 的 completion 才能继续提交 Run 终态、追加 Task 级 `exit`、共享 work-ledger completion，并进入 failover 或外部完成回调。
- TaskService 在跨进程 Task 生命周期锁下把完整 Run/Task 终态 patch 写入 durable terminalization intent，再执行 Run 终态 compare-and-swap、生成最终 provider output projection、完成 provider delivery，并通过最终 Task state mutation 重新校验 owner、写入 `completed` 与 `workspace_cleanup_due_at`。需要 provider 写回的 lane 必须在当前 Run 目录留下成功 action；Task 根目录只是当前 Run 的展示投影，历史成功 marker 不能满足新 Run。到期清理由同一 Task 生命周期锁和 Workspace lease 保护；Cancel 与 provider terminal lifecycle 才执行立即清理。锁释放前其他 Web/CLI 进程不能取得该 Task，晚到的旧 Run 不得改写状态、最终输出、delivery evidence 或删除新 Task instance 的目录。
- runtime helper 追加 Task event 时必须同时携带 `task_dir` 和当前 `run_id`；缺少 Run id 或 Run 已失去 `current_run_id` 时拒绝写入。
- 从 event log 重建 Task 时，以最大的 Run `sequence` 选择最新 Run；旧 Run 的晚到事件保留为审计事实，但不参与当前 Task 状态、phase、Run id 或 result ref 的投影。
- completion 不触发隐藏队列消费。
- 后续用户输入必须通过 Continue 显式创建新的 Run。

## Active Run replacement

同一 Task 同时只能处理一个 active Run。Agent strategy 的 Continue 表达“用新消息继续当前 Task”的 replacement intent：

1. 没有 active Run 时直接创建后续 Run。
2. 存在 active Run 时先等待显式 launch-resolution barrier，再执行 Stop Run，并等待进程 ownership 已解决；不能把尚未发布 PID 的合法启动误判成丢失进程。
3. 停止成功后，以停止后的 `current_run_id` 和 `latest_run_sequence` 为 compare-and-swap 条件创建后续 Run；并发进程已取得或完成过新 Run 时当前请求失败，不覆盖新 Run，也不复用 sequence。停止失败时返回 `run-stop-failed`，不创建新 Run。

jarvis-box 不创建后台排队 Run，也不要求调用方先额外提交 Stop Run。用户不再获得“只停止、不决定 Task 后续”的第四个状态；需要终结时使用 Cancel。

## Cancel

Cancel 终结当前 Task。

1. 解析 Task 的当前 Run ownership。
2. 有 active Run 时先在 lifecycle 锁外等待其 launch-resolution barrier；等待发生在 TaskService mutex 之外，不能与同步 completion callback 互锁。
3. 在任何 Stop/kill/reap 副作用前，以当前 Run owner、sequence 和不可变 Task instance 为条件写入 cancellation terminalization intent；intent 保留原 PID/Run ownership，写入失败时不发送进程信号。
4. 若不存在 current Run owner 却仍有 PID/PGID，立即 fail closed，不发信号、不清 Workspace、不清进程证据；否则同步调用内部 Stop Run。无法证明进程已停止则保持 `finalizing/cancelling` 和 intent，由同一请求或周期恢复器重试。`recovery-required` 且没有 pid/pgid 时，以 Task/Run owner compare-and-swap 固定旧 Run。
5. 遍历清理全部已登记 Workspace；清理与最终 Task mutation 再验证同一个 intent。
6. Task 原子写入 `status=cancelled`、`phase=cancelled`、`current_run_id=""` 并清除 intent；已提交 cancellation intent 拥有终态仲裁权，竞态 completion 只能被忽略。Task、Run、Workspace 登记和 Artifact 继续保留。

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

当成功后继 Task 通过明确 lineage 指向处于 `needs-attention` 的前置 Task，且两者具有相同的规范化 provider/project/subject 时，Jarvis Box 将前置 Task 的有效状态投影为 `superseded`。后继 Task 必须完整成功；失败、部分完成、回写收尾失败或仅 subject 相同均不足以收口前置 Task。

历史数据缺少 lineage 时，操作人员确认闭环后可执行：

```bash
jarvis-box tasks supersede <旧 Task ID> --by <成功 Task ID>
```

该命令只记录任务关系，不运行 Agent、不访问 provider、不补发历史评论。随后 API、CLI 和状态页会使用同一有效状态投影。
