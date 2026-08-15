# 存储模型

jarvis-box 使用 artifact-first storage。每个 Task 的 `task-state.json` 是当前状态，`task-events.jsonl` 是审计事件流，Run Artifact 是证据。jarvis-box 不新增全局 FIFO queue、prompt history store、Redis、SQLite 或 status projection database。

## 路径

公开路径变量定义在 [configuration.md](configuration.md)。

```text
JARVIS_RUNTIME_ROOT/
  dependency-cache/
  envs/
    .env.jarvis-box
  workspace/
    <workspace-id>/
  state/
    jarvis-box/
      chatbridge/
      chat-bindings/
        bindings/
        messages/
      runtime-agent-route.json
      runtime-agent-events.jsonl
      runs/
        <task-id>/
          <lane>/
            task-state.json
            .task-state.json.lock      # Web/CLI lifecycle mutation lock
            task-events.jsonl
            run-context.json
            payload.redacted.json
            attachments/
            result.json              # final provider-facing projection
            reply.md                 # final provider-facing projection
            runs/
              <run-id>/
                run-state.json
                .run-state.json.lock   # terminal transition lock
                run-context.json
                prompt.txt
                agent.log
                outbox/                  # private pending IM delivery files
                result.json
                reply.md
  logs/
    jarvis-box/
```

Linux system install 可以将 config、state 和 logs 映射到 `/etc/jarvis-box`、`/var/lib/jarvis-box` 和 `/var/log/jarvis-box`。逻辑边界不变。

## State Root

`JARVIS_STATE_DIR` 保存 jarvis-box 应用状态。它包含：

- Run/Task artifact root
- ChatBridge default Task bindings and message-to-Task indexes
- 其他受管应用状态

`JARVIS_STATE_DIR` 不是 service log 目录，也不是 Workspace。

`runtime-agent-route.json` 保存尚未到期的 service-level agent cooldown。`runtime-agent-events.jsonl` 保存 unavailable observation、cooldown extension 和 restored 审计事件；具体 Task 的 cross-agent child conversation 记录在该 Task 的 `task-events.jsonl`。两者不属于 Task Artifact；服务重启时只恢复 timer 和路由状态，不据此恢复或重跑 Task。

## Task Directory

`JARVIS_RUN_DIR` 是 Run/Task artifact root，默认 `$JARVIS_STATE_DIR/runs`。

每个 `task_dir` 是一个可清理的 Task 子树。`task_dir/runs/<run-id>` 才是单次 Run Artifact；Task 根目录只保存当前状态、审计流、provider 输入和最终 writeback projection。

`task_dir` 内可包含：

- `task-state.json`
- `task-events.jsonl`
- `run-context.json`
- `payload.redacted.json`
- ChatBridge downloaded attachments under `attachments/`
- `runs/<run-id>/run-state.json`
- `.task-state.json.lock` 和每个 Run 的 `.run-state.json.lock`；只用于 Web 服务与 CLI 跨进程串行化状态变更，不承载产品状态
- 每个 Run 自己的 `prompt.txt`、canonical `run-context.json`、runtime log、`result.json`，以及本次 Run 产生的 reply/comment 快照（如有）
- ChatBridge Run 的 `outbox/`，只保存 agent 明确请求交付给 IM 用户的最终文件；附件发送 recovery marker 和安全错误摘要保存在 `.private/`
- Task 根目录的最终 provider output projection：ChatBridge 使用 `reply.md`；GitLab/MR comment lane 使用 `comment.md`

Run Artifact 是证据，不是 conversation memory。产生 provider output 的 Run 保存自己的 `reply.md` 或 `comment.md` 快照；Task 根目录的同名文件是 Continue writeback strategy 使用的最终 provider-facing projection。Task 连续性由 Task state、AgentConversation lineage 和 runtime-native resume 负责，不由 reply、prompt、runtime log 或 jarvis-box 自己拼接的 history prompt 负责。

`chat-bindings/bindings/` 每个 IM Target 只保存默认 Task 指针。`chat-bindings/messages/` 保存同一 Target 内 message id 到 Task 的引用索引，包括已确认发送的机器人回复 id。两者都不保存 Run id、Run 状态、reply token、native session 或 provider credential；Task/Run artifact 始终是执行状态的唯一事实来源。

ChatBridge 附件下载目录属于单个 Run。`attachments/` 中的文件只供 runtime agent 和本机运维排查使用；`prompt.txt` 和 `run-context.json` 可以保存下载后的本地路径，方便 agent 定位文件，但 public projection 和 public Artifact endpoint 不得枚举或读取该目录，也不得通过 symlink alias 绕过该限制。provider 下载 URL、provider 文件密钥、raw IM payload 和 reply token 不写入附件 metadata 的公开形态。

ChatBridge 出站 `outbox/` 也属于单个 Run。jarvis-box 只接受目录根部的普通非空文件，先对数量、单文件大小和总大小做整批校验，再依据精确 provider + connector 的 live capability 上传和发送；任何预检失败都不开始远端发送。发送开始前写 private recovery marker，因此超时、进程崩溃或重试不会自动重放可能已经送达的附件。`outbox/` 及其 symlink alias 不得由 public Artifact endpoint 枚举或读取。

## Runtime Agent Log 与 Native AgentSession

Run 内的 runtime agent log 是 Run Artifact。它记录 jarvis-box 启动的 runtime agent 进程 stdout/stderr、退出线索和运行期可审计输出，典型文件名是 `codex.log`、`claude.log` 或 `agent.log`。

Native AgentSession jsonl 属于 runtime agent，不属于 Run Artifact。它保存 agent 自己的 conversation memory、checkpoint、compact 结果、tool trace 或 session metadata，用于 native resume。

两者可能出现部分文本重叠，但语义不重复：

| Surface | Owner | 内容 | 生命周期 | 用途 |
| --- | --- | --- | --- | --- |
| Runtime agent log | jarvis-box | 当前 Run 的进程 stdout/stderr 和运行输出。 | 跟随 Run Artifact；`tasks clean` 可以删除 terminal Run 的该文件。 | 审计、排障、确认运行失败或输出。 |
| Native AgentSession jsonl | runtime agent | AgentSession conversation、checkpoint、compact 和 native resume 所需记录。 | 由 runtime agent 管理；jarvis-box 不把它复制进 Run Artifact。 | native resume 和 native compact；跨 agent 时目标 runtime 创建自己的 session。 |

规则：

- Runtime agent log 不能作为 conversation memory、prompt history 或 resume source。
- Native AgentSession jsonl 不能作为 public Artifact 暴露，不能被复制到 Run Artifact，也不能被 jarvis-box 解析后拼接进 prompt。
- `task-state.json`、`task-events.jsonl` 和 public status 只能保存 safe resume status/ref，不能保存 native session id、session file path 或 resume handle value。
- Cross-agent Continue 创建目标 runtime 的新 session；jarvis-box 不导入、不转写、不展开源 session 内容。
- 文本重叠只是观测层面的副作用，不改变 ownership：Run log 用来审计一个 Run，AgentSession jsonl 用来延续一个 AgentConversation。
- Runtime agent log 必须由 jarvis-box 捕获进程输出后按固定策略合并写入；不得通过 symlink、hardlink 或 raw pointer 复用 native AgentSession 文件来伪装成 Run Artifact。
- Runtime output persistence 必须避免写放大：首个输出可以立即落盘，后续输出按大小或时间窗口 flush，Run 结束或超时时强制 flush。stdout/stderr activity event 也必须合并，不能按每个 chunk 写 `task-state.json` 或 `task-events.jsonl`。

## Authoritative State

`task-state.json` 记录 Task 当前事实；每个 `runs/<run-id>/run-state.json` 记录该 Run 当前事实：

- Target 和 Task 标识
- lane、status、phase、lifecycle summary
- current Run metadata
- runtime agent name
- process metadata
- safe action policy
- safe resume handle status/ref
- artifact refs

`task-events.jsonl` 记录状态变更审计事件。事件用于排查和补充证据；当前状态以 `task-state.json` 为准。Run 产生的事件必须携带 `run_id`，可以确定顺序时同时携带 `sequence`。从事件恢复 Task 投影时按最大的 Run sequence 选择最新 Run，不能让旧 Run 的晚到事件覆盖当前 Run。

终态 Run 不可变。Task/Run state mutation 同时使用进程内 mutex 和文件锁，因此 Web 服务与独立 CLI 进程共享同一 compare-and-swap 边界；每次权威 JSON 替换必须依次完成临时文件 `fsync`、close、rename 和父目录 `fsync` 后才能返回成功，不能把 page cache 中可见但断电后可能丢失的 rename 当成 durable commit。Task 生命周期文件锁使用 runs root 外围固定数量的稳定分片 inode，不放在会被 retirement 删除的 Task 目录内；它串行化 Run 分配、Workspace 准备、provider completion、到期清理和 Cancel，而不阻止 provider callback 写自己的 Run Artifact。runtime helper 也必须携带 Run id 并通过同一 ownership 条件更新 Task state 和 Task event；仅有 task directory 不足以取得写权限。新 Run 以读取到的 Task owner 和 `latest_run_sequence` 为 compare-and-swap 条件取得 `current_run_id`，并发请求不能无条件覆盖该指针，owner 发生 ABA 也不能复用旧 sequence；rename 已可见但目录同步失败属于 typed ambiguous commit，无论底层是 ENOSPC、EDQUOT 还是 EIO，都只能在真实写探测恢复后按同一 Run/Task instance 重写确认，不能另建目录或遗留幽灵 owner。TaskService 是 managed Run 的终态仲裁者；只有仍拥有当前 Task Run identity 的 completion 才能先持久化包含不可变 Task instance、完整 Run 终态 patch 和 Task 终态 patch 的 write-ahead `terminalization_intent`，随后提交不可变 Run 终态、provider writeback、释放 Run ownership，并按 `JARVIS_TASK_WORKSPACE_CLEANUP_DELAY_MINUTES` 原子安排 Workspace 清理。Cancel 同样在任何进程信号前按当前 owner/sequence 写入 intent，且该中间状态保留 PID 和 Run pointer；cancellation intent 一旦提交即拥有 Task 终态仲裁权，晚到 completion 不得覆盖。无 Run owner 却仍有 PID/PGID 的状态必须 fail closed，不发信号、不清目录也不清进程证据。恢复器必须先停止或固定旧 Run，不能把仍可能运行的进程当作可清理 Task。Run 或最终 Task state 写失败时仍保留 `finalizing` intent；启动及每 5 秒运行的恢复器先收敛已死亡进程留下的 Run owner，再按 intent、当前 Run evidence 和 `workspaces[]` 幂等重放，不扫描 Workspace，也不把删除 Workspace 当成终态写入的前置条件。已有新 Run 时，旧 Run 只保留自己的终态 Artifact 和 delivery evidence，不改写当前 Task projection 或 state。

### 磁盘准入与自动恢复

`JARVIS_TASK_STORE_MIN_FREE_GB` 定义启动新工作前必须保留的磁盘余量，默认 10 GB，只有显式 `0` 才禁用；空值或畸形的 Run 环境不会把保护静默关闭，服务与 scheduled job 的非法显式配置会直接拒绝启动。TaskService 先原子登记 Task identity、canonical subject 和完整的 1:N `workspaces[]`，再检查 Task Artifact 所在卷和每一项已登记 Workspace 路径；准入通过前不创建 Run、不 mkdir/clone Workspace，也不启动进程。Runner 在进程启动前再次检查这些卷，覆盖准入与 spawn 之间以及多个独立卷之间的容量变化。

`repo-cache` 是 box-owned 的 bare mirror。缓存刷新使用 exclusive lease，local clone 全程持有 shared lease，避免另一个 Task 在 Git 读取 object 时改写同一 mirror。缓存刷新成功且 cache 与 Workspace 位于同一文件系统时，Workspace 通过 Git local clone 复用不可变 object 的硬链接，随后立即把 `origin` 恢复为权威远端；Workspace 不写 `objects/info/alternates`，所以 cache 删除或重建不会让已有 Workspace 失效。缓存刷新失败、本地 clone 不可用、lease 获取失败或跨文件系统时，创建流程退回权威远端 clone。这里共享的是 Git object 的物理块，不共享工作树、构建产物或可变运行数据；单独对一个 Workspace 执行 `du` 仍可能显示这些硬链接的完整逻辑大小。

Workspace clone 和 Jarvis 执行的 checkout 默认设置 `GIT_LFS_SKIP_SMUDGE=1`，只检出 LFS pointer，不在 Task 启动路径自动下载图片、视频或其他 LFS 内容。这避免 cached clone 因 bare mirror 不是 LFS endpoint 而被误判失败，也避免与任务无关的 LFS 内容同时占用 `.git/lfs` 和工作树两份空间。确实需要二进制内容的任务应在已绑定权威 `origin` 的 Workspace 中用 `git lfs pull --include=<path>` 按路径 materialize；Operator 可以显式覆盖该环境变量恢复 Git LFS 的标准全量 checkout。Status 的 clone 进度会显示 `LFS 按需下载`，使该策略对操作者可见。

Start 准入遇到 `low-disk`、`ENOSPC` 或 `EDQUOT` 时，Task 进入 `status=waiting`、`phase/monitor_status=storage-wait`、`next_action=wait-for-storage`。该状态持久化最小的 `pending_launch` 准入记录，保留 Task registration 和全部 Workspace registration，但没有 `current_run_id`。服务启动时及此后每 5 秒只扫描 canonical Task state；对应卷恢复后，恢复器重新调用原 lane launcher，由 TaskService 再次检查容量并用现有 owner/sequence CAS 创建第一个 Run。并发恢复最多一个调用取得 Run owner，服务重启不丢失等待状态，也不需要 Redis、全局 FIFO queue、Workspace 目录发现或进程内 callback。只有全新空状态或当前版本显式写出的 admission scaffold 可以取得首次 Task registration；未标记的历史 `accepted` 状态不会被猜测或迁移。无法持久化 Task registration 的硬 ENOSPC 不能伪装成已接收，必须向入口返回错误；权限错误、未知 `statfs` 错误等非容量故障进入 `admission-failed / needs-attention`，不做无限自动重试。

Task-store 的一次 `ENOSPC`、权限或原子写失败是当前 persistence fault，不是只能随进程重启清除的配置状态。健康检查、Run 准入和周期 terminalization recovery 都走和正式状态写入相同的文件锁及 crash-durable 原子替换路径执行 create/write/file-fsync/rename/directory-fsync/delete 探测；探针若不完成文件和目录同步，不得解除 latch。同一时刻的并发检查合并为一次探测，探测本身失败不会覆盖原始业务写入的故障证据，成功也只解除它开始时观察到的错误 generation，期间出现的更新错误不能被旧探测误清除。多个终态 Task 采用 250 ms 到 5 s 的有界指数退避，不会在磁盘故障时形成固定频率的探测惊群。`JARVIS_TASK_STORE_MIN_FREE_GB` 只约束新 Run/clone 准入；终态恢复以实际可写为提交条件，不要求磁盘先回到新工作余量，也不提前删除当前 Task 的 Workspace。当前 fault 解除后，新 Run 或 finalization 清除 Task 的 `task_store_degraded` 并记录恢复时间；workspace 卷恢复后同样清除 `workspace_storage_degraded`。最后一次错误和恢复时间继续作为历史诊断信息保留，但不得继续阻塞调度。

准入检查与运行期写入属于两道不同的保护。agent 启动后，runtime log、AgentSession stream、result 或最终回复的任一关键持久化失败都绑定到当前 Run；即使进程 exit code 为 0，也必须提交 `persistence-failed / needs-attention`，保留已登记 Workspace，不能伪装成 completed。最终事件和 jarvis-command 通知只在 provider 回写及 Task 终态提交之后触发；这些步骤失败时通知结果必须改为 `completion-finalization-failed`。准入检查通过后，创建 `runs/`、创建具体 Run 目录或 Workspace clone/create 直接返回 `ENOSPC` / `EDQUOT`，都必须回到同一 `storage-wait` 准入状态；已经取得 owner 的未启动 Run 先终态化为 failed，再释放 owner。TaskService 完成这次转换后必须向所有 lane 返回 Waiting，provider/lane wrapper 不得把 canonical `storage-wait` 重写为 `launch-failed`。错误只登记在对应 Task 的存储证据中，不得误锁无关 Task。周期恢复重新检查实时容量，并在成功取得新 Run 后清除等待错误、记录 recovery。

文件锁不可用时不得退化成只有进程内 mutex 的写入。锁创建、`flock`、状态写入或 rename 任一步失败都必须让本次 mutation fail closed 并登记新的 persistence fault。低磁盘准入只阻止会继续放大写入的新 Workspace/Run；已终态 Task 的登记式自动清理和 Status 手工删除仍是释放空间的通道，不受进程内 persistence fault 阻断，释放后由真实写探测解除 fault。不得通过扫描目录、猜测归属或删除 active/needs-attention Task 来应急回收；Workspace 由登记驱动的终态清理负责，terminal Task Artifact 由 retention clean 负责。

## Prompt Artifact

`prompt.txt` 只保存当前 Run 的输入：

- Start Run：首次用户消息。
- Continue Run：新的用户消息。
- Task recovery Run：运维恢复提示。

`prompt.txt` 不包含历史用户/助手消息、native session 内容、resume handle value 或 cross-agent source ref。

## Private Handles

Adapter 可以把 runtime-native session id、thread id、checkpoint ref 或 opaque token 保存为 private resume handle metadata。

规则：

- private handle store 位于 `JARVIS_STATE_DIR/agent-resume-handles/`。
- private value 只在 adapter dispatch 时解析。
- private value 不写入 public status response、public Artifact listing、E2E evidence、service logs 或用户可见摘要。
- private value 不写入 `task-state.json`、`task-events.jsonl`、`run-context.json`、`prompt.txt`、`result.json` 或 runtime logs。
- private handle 不能跨 runtime agent 复制。
- cross-agent source ref 不是公开持久对象；目标 runtime 的 continuation instruction 只引用 Task/Workspace/lineage 所需信息。

## Public Projection

`/status` 的 public projection 是响应 allowlist 和进程内派生读模型，不是独立存储层。

规则：

- jarvis-box 单进程运行时，public projection 必须保存在进程内，通过 Task state 写入、Run 完成事件、服务启动时从 Artifact 重建和后台 reconcile 更新。重建 projection 不调度 Run。
- 磁盘上的 `task-state.json` 和 `task-events.jsonl` 是恢复来源，不是每个 `/status` 请求的查询引擎。
- `/status` 不引入 Redis、SQLite 或其他外部 cache/database。外部存储只有在多节点写入、十万级 Task、跨进程事务或复杂离线查询成为真实需求后才重新评估。
- 如果 status list、summary 或 work-items 需要在请求路径中全量扫描 `runs_dir` 才能返回，视为实现偏离契约。

允许字段：

- safe Target key/hash 和标题
- Task id、标题、状态、更新时间
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
- arbitrary filesystem path
- `task_dir`
- `run_dir`
- `log_file`
- Workspace absolute path
- chat message history

## Artifact Access

Public Artifact endpoint 只解析授权后的 safe artifact ref 或受限 `run`/`run-group` 相对路径。它不提供 Workspace root，不读取 raw payload、run-context、prompt、events 或 runtime logs。完整 root/path 文件浏览只属于 `/server` local-admin 面。

规则：

- 先做 Target visibility check。
- 只读取允许 root 下的文件。
- 不列出或读取 ChatBridge `attachments/` 或 `outbox/` 目录；路径解析后落入这些目录的 symlink alias 也必须拒绝。
- 返回文本前必须 redaction。
- 不返回文件系统绝对路径。
- 不返回 private handle、native session id、cross-agent source ref、reply token、raw provider token 或主机路径。

## Logs

`JARVIS_LOG_DIR` 保存 jarvis-box service、deploy 和 runtime wrapper 日志。它不等于 `runs_dir`，也不被 `tasks clean` 清理；宿主 scheduler 与 Runtime Foundation logs 不属于该目录的产品契约。

Run 内的 runtime agent log 属于 Run Artifact。Service log tail 只能通过 `/server` 或 CLI 运维命令读取。

## Workspace

`JARVIS_DEPENDENCY_CACHE_ROOT` 保存跨 Task 复用的包管理器缓存，默认是 `${JARVIS_RUNTIME_ROOT}/dependency-cache`，Docker 为独立持久卷 `/var/cache/jarvis-box`。它不属于 `workspaces[]`，workspace cleanup 和 Task retention 都不得删除它。Jarvis Box 只注入标准缓存环境；如配置 `JARVIS_WORKSPACE_DEPENDENCY_CONFIGURER`，则在 lane 完成 checkout 后、Agent 启动前调用 Operator 提供的程序。该 hook 失败必须让 Run 启动失败，不能带着半配置 workspace 继续执行；hook 内容仍由客户 Runtime Foundation 负责。

缓存根目录只承载各工具的原生下载缓存、内容寻址缓存和工具自身支持的共享安装目录。它与 `repo-cache` 在 Workspace 准备流水线中协同，但不混用生命周期或目录：repo cache 复用 Git object，dependency cache 复用包管理器依赖，LFS 内容默认按需 materialize。Bundler 是共享安装目录的明确例外：`BUNDLE_USER_CACHE` 保存用户级索引与下载缓存，`BUNDLE_PATH` 保存可跨 Workspace 复用的已安装 gems；Ruby ABI 与 native extension 平台隔离沿用 Bundler 自己的目录结构。通用 Workspace 准备接口负责调用各工具 policy；生命周期调用方不识别语言或包管理器。当前只有实际使用 Yarn 的 Workspace 会生成并通过 `.git/info/exclude` 隐藏 `.jarvis-yarnrc.yml`；能严格确认 Yarn 3+ 时加入 `hardlinks-global`，其他 Yarn 版本保留自身兼容行为，非 Yarn Workspace 不写入该文件。这个 Workspace-local 边界允许同一 Agent 在运行中新增不同 Yarn major，而不会保留旧目录推导出的 Agent-wide mode；Operator 显式环境仍优先。文件系统支持跨目录硬链接时，Yarn 可以让各 Workspace 的 `node_modules` 复用 global content store 的物理文件。单独对一个 Workspace 执行 `du` 仍可能显示这些硬链接的完整逻辑大小，不能把该数值直接与 cache 目录相加当作物理占用。跨项目共享整个 `target/`、`node_modules`、`build/` 等编译结果不属于默认模型。需要编译缓存时，应使用 ccache/sccache 或由 workspace configurer 按 OS、架构、工具链和项目建立隔离键。缓存属于单个 Jarvis 安装的信任边界，不跨客户共享，清理由独立运维策略负责。

`JARVIS_WORKSPACE_ROOT` 保存 Task Workspace。一个 Task 可以拥有零个到多个 Workspace；唯一归属记录是 append-only 的 `task-state.workspaces[]`。每项包含稳定的 Task-local id、服务端分配的绝对路径、可选 repository metadata 和 `primary` 标记。路径由 `task_id + task_instance_id + workspace_id` 共同派生；同一个 task id 被重新创建后也不会复用旧实例目录。非空集合恰好有一个 `primary=true`，只负责选择 Run 的默认 `cwd`；空集合不合成目录，Run 使用 launcher 的普通工作目录。

初始 Workspace 必须和 Run ownership claim 在同一次 crash-durable Task state mutation 中登记；active Run 中的 zero-workspace Task 必须通过 `jarvis-box workspace create --id primary` 建立第一个 canonical Workspace，非空 registry 后续增加仓库时使用普通 stable id。Runner 在所有 agent lane 的启动和 resume prompt 中注入这条 ownership contract，明确禁止 agent 绕过该命令创建、替换或物化 `JARVIS_WORKSPACE_ROOT` 的任何直接子项；已登记 Workspace 内部的正常文件操作不受影响。两条登记写路径都先提交 `workspaces[]`，随后在 Task 生命周期锁内重新验证 Run ownership、检查 Task store 和全部已登记 Workspace 所在卷，最后才创建、clone 或 checkout 目录。jarvis-box 不通过独立 reclaimer 扫描或清理 Task Workspace。已有 repository 目录必须包含真实 `.git` 目录或 worktree 文件；登记的 id、path、project、remote 和 primary 保持稳定。目录从未创建成功或已按登记清理时，Continue 可以由同一个 Workspace owner 重新分配路径；`base_branch` 只是目录准备输入。`cwd`、`workdir`、Run context、Artifact、marker 文件和目录扫描都不是 Workspace 归属来源。

一个 Task 的全部已登记 Workspace 跨多个 Run 存续。每个 managed Run 从启动到其进程组退出都持有同一把 Task 级 shared Workspace lease；清理前必须证明没有 Run owner、没有存活的已登记进程身份、没有 terminalization intent，取得对应的 exclusive Task lease，再逐项取得 exclusive Workspace lease。手工与定时清理共享这组准入条件。Run 结束/取消时先按 Task+Run 环境标记和稳定进程 identity 清理受管后代进程；脱离 managed 进程组的进程再由 `cwd` 和 open-file reference 扫描兜底，无法确认安全时保留目录并进入可见的延迟清理。外部资源只来自 Task 显式登记的 typed `external_resources[]`；文件名、目录名、repository 名和 Docker working-directory scan 都不能创建资源所有权。详细状态机见 [Task external resource lifecycle](task-external-resource-lifecycle.md)。Run 释放 `current_run_id` 时，Task state 原子写入 `workspace_cleanup_due_at = now + JARVIS_TASK_WORKSPACE_CLEANUP_DELAY_MINUTES`；Continue claim 新 Run 时清除该截止时间。任何 Workspace disposal 失败都持久化并退避重试。全量清理成功后写入 `workspace_disposal_completed=true`；`tasks clean` 只消费这个凭证，不重新解释 Workspace 或外部资源。

Cancel 以及 provider 明确发出的 Issue close、MR close/merge 是立即清理边界：它们先解决 active Run 与同 Run 后代进程 ownership，再按同一份 `workspaces[]` 立即尝试清理全部目录，不等待配置的保留窗口；无法完成的 Workspace/外部资源义务随取消状态持久化并进入退避重试。普通 Run 结束与 workspace 删除彼此独立；Run 终态落盘、provider writeback 或其恢复不得以提前删除 workspace 作为前置条件。

Task 首次 claim 还会在全局登记锁内分配递增的 `task_registration_sequence`，生成随机不可变 `task_instance_id`，并把外部工作对象规范化为不可改绑的 `task-state.subject`（`provider`、`kind`、`project`、`number`）；这些字段和 `workspaces[]` 在同一次 state mutation 中先于目录创建落盘。Provider webhook 的明确终态会按该登记精确匹配事件首次处理时已经存在的 Task：GitLab issue `close`、MR `close/merge`，GitHub issue `closed`、pull request `closed`（按 `merged` 归一为 `close/merge`），以及 Jira issue 状态进入 Done category 或被删除。匹配到的非终态 Task 统一经 `TaskService.CancelTask` 终止并清理全部已登记 Workspace；已经 completed/cancelled 的 Task 保持原终态，只重试登记目录清理。

Provider adapter 只负责把 webhook 归一成 subject terminal event，TaskService 不含 lane/provider 清理分支。首次处理一个 provider delivery 时，adapter 与 Task 创建共享全局登记锁：先把当前登记序号写成 durable `task_registration_cutoff`（status=`planning`），再扫描 cutoff 以内、subject 精确匹配的 Task，最后把每项 `{task_dir, task_instance_id, task_registration_sequence}` 写成 receipt 快照后才调用 TaskService。即使进程在 cutoff 落盘后、扫描前退出，retry 仍按同一 cutoff 重新计划；部分失败只重放 receipt 快照。同一路径后来被其他 Task 实例复用时，instance/sequence 校验会拒绝副作用。receipt 写入失败、损坏或身份不匹配时必须 fail closed。`issue_or_mr` 仍用于展示原 URL，但不参与终态归属判断；Artifact、branch、workspace 路径和目录扫描也都不是 subject 或 workspace 的归属来源。

清理目录不删除 `workspaces[]` 登记，因此 Status detail 仍能展示该 Task 的全部路径和存在状态。登记目录已经不存在时，手工删除仍是合法的幂等操作并返回 `already_absent`。`tasks clean` 只处理 terminal Task/Run Artifact；Task Workspace 的自动和手工清理由登记表和持久化截止时间驱动，不通过目录扫描或 orphan discovery 推断归属。

## Clean

`tasks clean --older-than <days>` 删除的是 `runs_dir` 下超过保留期的 cleanable terminal `task_dir`。

删除内容：

- 整个 `task_dir`
- 该 `task_dir` 内的 state、events、prompt、payload、log、result、reply、comment 和 writeback artifact
- `JARVIS_STATE_DIR/agent-resume-handles/` 内与该 terminal Run 关联的 private handle entry
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
