# 更新日志

## 未发布

## 0.2.31

- 内置 `uv-im-connector v0.0.17`，包含群聊附件接收、飞书图文回调及时 ACK、合法长文件名上传和 WebSocket 握手取消修复，并移除 connector 自设的文件大小限制。
- Jarvis Box 入站附件不再受单文件 100 MiB、单条消息合计 100 MiB 或最多 10 个的配额限制；下载、Agent 提示词和运行上下文保留全部附件。默认 connector HTTP client 不再因固定 15 秒总超时中断慢速大文件传输，仍响应调用方取消。
- 升级前请备份 connector 状态目录。新版 connector 写入的附件资源使用新存储布局；回退旧版时需同时恢复对应的状态备份。

## 0.2.30

- 降低历史任务较多时 Status 页面进度查询的 CPU 开销；查看普通任务不再扫描全部任务的定时作业历史。
- 多个 Status 页面共享任务列表和摘要的缓存重建，减少事件推送触发的重复扫描，并避免已失效的旧摘要重新进入缓存。
- 后台恢复和工作区清理在每轮巡检中共用一次任务扫描，减少重复读取；保留原有恢复周期、任务归属校验和清理保护。

## 0.2.29

- 托管 Agent 自动发现与运行时准备命令安装在同一目录的工具；新任务统一使用最新运行时配置，修改或移除工具路径配置后不再沿用旧值，取消与恢复时也能正确找到浏览器清理工具。
- 修复 macOS 深层任务目录下浏览器因 socket 路径过长无法启动的问题；浏览器使用受任务归属校验保护的短路径，并在任务结束、取消和启动失败时清理。

## 0.2.28

- 修复飞书项目 post-check 通过 Workflow Runtime Contract 启动嵌套 customer workflow 后丢失 Meegle 实时读取能力的问题；能力只继承给同一飞书工作项的 Meegle backend 子 Run，plugin 与其他 provider 仍不接收 Meegle credential。
- Status 按仓库同时展示“未经人工修改”的数量和比例；统计缺失或不完整时继续显示 `—`，并保持窄屏布局不溢出。
- Status 工作项列表在并发请求下复用同一份构建结果，缓存失效后串行刷新；请求取消不会发布不完整快照，减少任务较多时的重复扫描和 500 响应。
- 新增客户派生 Docker 镜像指南，说明如何在当前 release 的 digest-pinned 基础镜像上安装系统编译依赖，并覆盖多平台构建、验证、升级、回滚和凭据边界。

## 0.2.27

- 内置 `uv-im-connector v0.0.15`，飞书与企业微信消息会补充可用的发送者和会话显示名称；Status 页面保留 connector 提供的具体来源名称，并在缺少显示名时使用稳定目标标识。
- Status 页面新增运行 Agent 的计费账号额度，并按实际 provider 路由链展示模型配额，便于识别当前使用的账号和 fallback 路径。
- IM command mention 支持紧跟中文命令，并优先匹配配置中最长的 mention 名称，避免重叠名称把命令正文截断。

## 0.2.26

- Docker 生产镜像切换到经过双架构验证的不可变 runtime base，普通 Jarvis Box 升级不再重复构建系统依赖和官方工具；部署重建后会自动原子更新官方工具，失败时保留上一套可用版本。
- 新增 `jarvis-box tools path|status|update|reset` 管理入口；客户自装工具统一保存在持久化 `/home/jarvis/.local/bin`，镜像升级和容器重建后仍保留。
- Status 页面会在 Delivery Metrics 完成后自动刷新，并防止完成事件之前启动的请求重新写入过期缓存，新的分析结果无需手工刷新即可显示。
- 飞书项目 command ingress 现在遵循 `JARVIS_MENTION_NAMES` 配置，并正确处理富文本 mention metadata 和 Unicode 文本，不再只识别内置名称。
- Jira 评论写回改用当前 Jira CLI 支持的 template/non-interactive 参数，避免默认评论命令因无效文件参数失败。
- Agent Browser 清理不再把已退出进程的瞬时 signal race 保留为最终错误，减少任务收尾时的误报。

## 0.2.25

- 默认分支单分支 Workspace 会重新使用 repo-cache 作为对象来源，但通过非 local 单分支 clone 保持 tag 和其他分支历史隔离；cache 不可用时仍回退权威远端。
- ChatBridge 只把当前 Run `outbox/` 中的文件作为附件发送，不再从回复正文或历史 Run 制品推断附件，避免旧附件重复发送或正文路径被误判为附件。
- Status 本机 Task Run 趋势按首条本机记录到今天的连续日期展示，缺失日期补 0；“不显示异常值”按数据分布识别异常日，不再只隐藏最高点。

## 0.2.24

- Status 的本机任务运行统计恢复准确；“本机已记录任务运行”、今日、昨日和趋势图现在按本机实际运行记录展示。
- Status 的累计产出区域将运行耗时口径改为“已完成运行耗时合计”，按已完成 Task Run 的实际耗时累计；趋势默认展示全部数据，并新增本机时间窗口选择和隐藏最高点选项。
- Status 工作项 feed 的锚点滚动恢复；系统对话框、详情和弹层中的状态、提交、作者和错误提示文案更一致，不再出现难以理解的原始标签或错误代码。

## 0.2.23

- 默认分支单分支 Workspace clone 现在明确禁止拉取 tag refs，避免默认分支上的可达 tag 突破 default-only 历史边界。
- 新增客户侧代码归属与 Git 提交身份指南，说明在共享 Jarvis Box deployment 中如何区分 provider 登录身份、runtime agent 身份、commit author/committer 和代码负责人配置边界。
- Status 页面前端资产拆分为独立 HTML/CSS/JS，修复工作项 feed 锚点滚动；累计产出继续保留 review history，并新增当前保留任务的 Agent 累计运行时长口径。
- Status 本机运行指标保持 provider-neutral：切换 GitLab、GitHub、Jira、飞书项目或即时消息筛选时，不改变本机 Task Run 趋势和累计运行时长。
- ChatBridge 出站附件不再额外套用 Jarvis Box 内置文件数、单文件大小或总大小配额；实际可投递边界由 provider/connector 实时能力和 IM 渠道上传、发送限制决定。

## 0.2.22

- Status 的累计产出区域暂时不再展示运行 Agent token 用量；`runtime_token_usage` API 兼容字段仍保留，Delivery Metrics 与本机 Task Run 趋势不受影响。

## 0.2.21

- 修复 0.2.20 升级后飞书项目 webhook 不再处理的问题：Meegle backend 启动预检现在同时识别运行账号持久化 HOME 中已登录的默认 token store，不再要求额外配置 profile 或 token 环境变量；未认证或预检超时仍保持降级启动并拒绝不可执行的读写请求。
- 飞书项目默认 Meegle backend 的 post-check Agent 现在可以用匹配 Run 专属的 Meegle CLI 身份刷新完整工作项字段、全量评论、所需附件、关系和关联工作项；plugin backend 仍只提供服务端快照，所有最终评论和 provider mutation 继续由 Jarvis Box 服务端执行。
- 修复飞书项目完成通知把 API `project_key` 拼成无效 `/work_item/` 页面链接的问题；Meegle backend 现在解析空间 `simple_name`，并统一生成可访问的 `/<simple_name>/<work_item_type>/detail/<work_item_id>` 链接，同时 Task、Status Continue 和写回重试仍持有稳定 `project_key`，不会把展示用 `simple_name` 误传给飞书项目 API。

## 0.2.20

- Status 的累计产出区域将 runtime token 用量独立为全局 section，并按 agent 与 model 显示缺少 metadata 的 session 数，避免 token telemetry 不完整时误导交付质量卡片。
- Delivery Metrics 结果读取更稳健：Agent 输出里只有一个可恢复的严格 JSON 分类结果时仍可进入基线统计，减少有效分析结果被包装文本阻断的情况。
- Provider command 与 workflow 写回在发现缺失、污染或不符合发布规则的评论 artifact 时会标记为 `agent-output-invalid`，Status 会把任务显示为可 Continue 的 Agent 修复项，而不是普通写回失败。
- macOS Native 安装会把自定义 `JARVIS_LAUNCHD_LABEL` 写入 launchd 环境，`doctor` 和 Status 诊断会按实际 label 检查服务，避免多实例或自定义 label 环境误判服务状态。
- 新增多实例部署指南，并明确正式同机多实例推荐 Docker；Native 多实例只适合已批准的迁移、恢复或维护窗口，且 lifecycle 操作前必须单独证明 OS service identity。
- 飞书项目 Meegle CLI 后端只有在显式配置 profile 或 token 时才做启动预检；身份暂未配置时服务仍可启动并审计 webhook，读写后端在身份修复前保持不可用。

## 0.2.19

- Status 的累计产出与交付质量区域新增本机 Task Run by-day 趋势图，默认按 180 天自然日展示历史 Run 活跃度；历史数据暂不可用时会显示降级状态而不影响 `/status` 页面整体加载。
- Status 价值指标新增 runtime token KPI，并修复 Status API 示例 schema 与 Claude token telemetry 过滤，便于在同一页面观察运行成本、交付质量与本机吞吐趋势。
- 自定义定时 prompt 任务现在每次触发都会创建独立工作项，便于在任务列表和 Status 页面分别跟踪，避免长期复用旧 Task。
- Release 发布重新增加公开 S3 fallback mirror：`jarvis-box update` 会优先使用私有 GitHub Release，失败后自动从 `download.hengshi.com/jarvis-box` 下载同名 release bundle 和 `SHA256SUMS`，并继续以 checksum 校验作为安装 authority。`update --check` 现在显示元数据来源和可用下载源。
- Docker 部署升级和会停止/重建服务的 Compose 操作现在会先检查同一 deployment home 的 Task 生命周期；存在 active、waiting、finalizing、CI-wait 或 recovery-required Task 时会在停服前拒绝，并打印阻断 Run。显式 `--force` 需要 `JARVIS_DOCKER_UPGRADE_FORCE_STRATEGY`，并会先把策略和受影响 Run 写入 deployment home 后再继续服务变更。

## 0.2.18

- Delivery Metrics lane 现在可以通过 `JARVIS_DELIVERY_METRICS_ENABLED=false` 明确禁用；禁用后 Status 不再启动新的分析 Task，操作台 Start 和恢复入口会拒绝该 lane，已在运行的 Task 与 Continue 收尾不受影响。
- Status 的价值分析进度更专注于 Delivery Metrics 当前状态，不再把当前 Task 列表混入进度摘要，降低操作台扫描噪音。
- Agent Run 被调用方取消或进程回收无法证明已停止时，Jarvis Box 会主动终止已启动的受管进程，减少取消、恢复和 workspace 清理之间的残留进程风险。
- 使用 Workspace 内 vendored Yarn 3+ release 文件（例如 `.yarn/releases/yarn-4.3.1.cjs`）的项目，现在也可以被识别为支持 `nmMode: hardlinks-global`，从而复用全局 Yarn cache 的硬链接；无法证明版本或与 `packageManager` 冲突时仍保持原有保守行为。

## 0.2.17

- 修复飞书项目 Task 从 Status 继续时丢失原工作项身份、以及多 Run 写回重试误用其他 lane 产物目录的问题；Continue 现在按 lane 的既有产物所有权重放回复，投递目标从 Task 的不可变 subject 恢复，成功后 Task 收敛为完成状态。writeback Continue 不重复运行 Agent，也不接受新消息。
- `jarvis-box workspace create` 现在解析远端默认分支：请求的分支无法解析时回退克隆远端默认分支，并把回退说明追加进 Agent 提示，让 Agent 在改动前确认分支是否合适；工作区目录已存在时拒绝登记 base branch 变更。
- 飞书项目 webhook 在 Meegle CLI 或插件 API 未配置时 fail closed，返回明确错误而不是进入无法处理的准入状态；Meegle CLI 暂不可用时服务启动降级跳过认证预检，不再因此整体退出。
- 依赖缓存覆盖扩展：新增 XDG cache、Corepack/Bun/Deno、Playwright/Puppeteer/Cypress 浏览器缓存、Turbo/Nx task cache、pre-commit/Ruff/mypy/Python pycache 和 Coursier 等工具缓存策略。Cargo 构建默认关闭 incremental 编译，检测到 sccache 时自动设置 `RUSTC_WRAPPER`；单一 Cargo Workspace 会把 Rust 中间构建产物放入按仓库身份隔离的共享目录，不跨 Workspace 共享 `target/` 顶层输出。配置了专用 agent browser 时，Puppeteer 使用该浏览器并跳过安装时 Chromium 下载。
- Delivery Metrics 历史基线改为普通 `delivery-metrics` lane Task：分析 Task 会出现在 `jarvis-box tasks list` 和 Status 工作项列表，可通过普通 Task detail 查看、Continue 或 Cancel；Status 每次 Provider 刷新最多启动一个新的分析 Task，并读取 Task 根目录的 `delivery-metrics-result.json` 写入统计。判断 Agent scope 由 `value-judge` 改为 `delivery-metrics`（`jarvis-box agent set --scope delivery-metrics`），升级时 Flyway 会把旧 scope 变量一次性改写，并移除旧的自定义判断策略变量。
- 修复 Status 页面同一 work item 的主任务选择：进程仍在运行的任务优先展示，其余按最近活动时间排序。
- 修复 `tasks start/cancel/continue` 的 help 预扫描把 `--reason help`、`--message help` 等参数值误当作 help 请求的问题；任务操作被服务器拒绝时现在显示 HTTP 状态码和响应正文，而不是笼统的 `exit status 22`。
- 修复磁盘空间等待任务的恢复：self-improve 等定时任务在空间恢复后可以被正确重新启动，任务存储等待记录会补全任务目录以便恢复，清理恢复不会覆盖已经观察到的终态结果。
- `jarvis-box update` 与 Docker 部署/升级正式切换到私有 `hengshi-jarvis/jarvis-box` GitHub Release：update 通过 GitHub API 检查并消费私有 Release 资产（需要仓库 access token），不再从公开下载站获取安装脚本；Docker 部署入口从同一 Release 的 release bundle、`SHA256SUMS` 与 `production-image.json` 消费。
- 修复 release qualification 的 IM protocol-envelope gate 候选镜像供给：gate 脚本对已认证候选镜像自行 `docker pull` 并校验，不再依赖前序步骤清理后残留的本地镜像引用，避免 `pull_policy=never` 的 Compose 启动因镜像缺失而失败。
## 0.2.16

- 动态 Workspace 在未显式指定分支或 checkout ref 时，只获取远端默认分支的完整非浅历史；不再经由全 refs repo cache 暴露其他分支 ref 或其他分支独有对象。
- Jarvis Box 正式二进制分发面收敛到私有 `hengshi-jarvis/jarvis-box` GitHub Release。公开仓库改为 onboarding stub，只保留客户文档、issue 入口和私有 GitHub access 指引；release bundle、checksum、`production-image.json` 和私有 GHCR image 不再通过公开仓库或下载站发布。

## 0.2.15

- Jarvis Box 私有源码发布面切换到 GitHub 后，公开发布同步增加客户文档空白校验；本版本当时仍保留旧公开二进制消费合同。

## 0.2.14

- Jarvis Box 私有工程源码与正式发布流水线迁移到 GitHub；本版本当时仍保留旧公开二进制消费合同。

## 0.2.13

- Task 对外生命周期收敛为 Start、Continue、Cancel；direct shell 与 Runtime Foundation jobs 通过一次 `tasks start --prompt` 由服务端分配 Task/首 Run，调用方不再预建 Task 或写 Task `prompt.txt`。
- 内置 `uv-im-connector v0.0.14`，消费统一的 provider 发送失败契约与安全诊断。
- GitLab 或 GitHub 的 Issue、MR/PR 在 Task 执行期间被删除时，最终评论会在项目或仓库仍可访问的前提下触发登记式清理并将 Task 取消；清理需要重试时保持 finalizing，成功 Run 不受影响。

## 0.2.12

- Docker 部署在关闭远程 Provider 与公开 Status 写入时，仍可从本机运行客户配置的 JARVIS 记忆固化、日省和心智进化任务；磁盘空间暂不可用时会等待，并在空间恢复后继续。迁移前已落盘的旧定时 Task 仅保留恢复兼容，不能再次创建。
- 创建动态 Workspace 时，无法解析、缺失或不是 Git worktree 的本地仓库会在登记前被拒绝，并提示改用显式 remote，避免留下不可用的 Workspace 记录。
- 修复 Status 页面连接建立瞬间可能漏掉 Task 操作和状态更新的问题，实时状态在首次加载期间也会完整到达。
- 修复从 Status 页面继续 Chat Task 后 Agent 可能在页面请求结束时被提前终止的问题；接受继续操作后，任务会持续运行，直到正常完成或被显式取消。
- Status 的 Agent 执行时间线重新显示当前 Run 的用户指令，并为不同 Agent 提供一致的过程展示和公开脱敏结果。
- 新增 Delivery Metrics 历史基线恢复与故障诊断指南；更换判定 Agent、命令参数或模型配置后，待处理批次会自动使用最新配置，无需重启服务，也不会重算已分析基线。


## 0.2.11

- 主动通知配置改为明确的 `JARVIS_NOTIFY_PROVIDER`，单实例 connector 由 UVIM 实时元数据自动解析；旧 channel 配置只作迁移兼容，provider/connector 错配会在启动时失败。
- Provider-native 交付质量持续回填新增实时分析阶段、agent、当前批次、完成比例和安全重试状态，Status 页面不再只显示待分析数字；切换 runtime agent 后回填即时采用新 agent 判定，且不再重置已分析的历史基线，判定口径只随判定策略变化触发增量重新分析。
- `jarvis-box workspace list` 只读取当前 Task/Run 的权威 workspace registry，以 JSON 输出归属明确的工作区，不扫描磁盘猜测状态。

## 0.2.10

- Provider command 现在始终绑定 TaskService 分配的当前 Run：GitLab、GitHub、Jira 和飞书项目会读取实时输入、保留精确 provider artifact 与外部资源 ID，并且只在当前 Run 的远端写回验证成功后推进 Task 级回复；Continue、取消、失败诊断和 workspace finalization 使用同一所有权。
- Status 页面新增 runner-owned 跨 Agent RunTrace，保留原始输出、分类与修订轨迹，并统一展示 GitLab/GitHub delivery 价值指标、当前质量 provider 和持续工作的增量反馈。
- 修复 recovery 与真实进程完成同时发生时的终态竞争；恢复 fence 不再覆盖已经观察到的成功/失败结果，重启后的 Task/Run 状态会收敛到真实完成证据。
- 心智进化任务可通过统一 `JARVIS_NOTIFY_CHANNEL` 向显式 direct/group 目标发送周报；未配置目标时仍只保留本地报告，通知 artifact 不暴露在公开 Status 文件浏览面。
- GitHub 可只作为 GitLab、Jira 或飞书项目 Task 的受控 Workspace 目标仓库使用，无需启用 GitHub webhook 或配置 `GITHUB_WEBHOOK_SECRET`。
- Chat continuation 的回复由继续后的 Task/Run 所有，完成消息不会丢失或误投；macOS 默认使用隔离的 managed Chrome for Testing，不再占用桌面浏览器 profile，显式配置 `AGENT_BROWSER_EXECUTABLE_PATH` 时仍遵循该配置。
- 扩展 Native 依赖缓存并修复 Yarn 版本、模式和清理边界；不同 Workspace 可安全复用支持的缓存，同时避免 cleanup deadlock 或跨项目模式污染。
- Docker 升级会持久化稳定 runtime hostname，保护 Meegle 加密 profile 在首次升级和后续 force-recreate 后仍可解密；身份不明确或无法恢复时会在替换容器前失败。

## 0.2.9

- 新增客户中立的 task-start Agent runtime preparation hook：每个新 Task 在 Workspace/provider 准备完成后、Agent 启动前可由客户 Runtime Foundation 按 Company repo revision 刷新 skills；Continue/failover 不重复执行，失败会阻止 Agent 使用半更新运行时启动。
- `@jarvis` 在 GitLab、GitHub、Jira 和飞书项目中统一作为 comment command mention；Jira/飞书项目不再绑定单一 GitLab 仓库，一个 work item 可关联零个或多个 GitLab/GitHub repository。
- 新增全局原 subject 写回开关，安装测试可保留 Agent 与本地审计而不向 GitLab、GitHub、Jira 或飞书项目写入评论/字段；Workflow Runtime Contract 升级到 v2 并停止生成 action grants，既有 v1 Run 仍可兼容读取并按原 grant 校验。升级环境若仍包含已移除的 v1 grant 配置，写回会保持关闭，直到运维人员显式配置新开关。
- GitHub PR 评论、changes-requested/commented review 和 inline review comment 现在可进入与 GitLab MR 共用的 follow-up 状态机；命令 mention 保持优先，fork PR 使用 head repository source branch workspace 并向原 PR 写回状态，状态评论和安装验收回写开关在两个 provider 间一致。
- 修复 provider 回写工件的外部资源 ID 类型保真，避免 GitLab note 等数字 ID 在运行工件中被转换后失去精确身份。
- 内置 `uv-im-connector v0.0.13`，修复企业微信大文件上传分片编号，并为 provider 发送失败保留脱敏后的可操作诊断日志。

## 0.2.8

- 提升工作区 clone 可靠性：对临时 Git 网络故障执行有限重试，任务取消可中断 clone 和退避等待，Status 页面会持续显示准备操作、尝试次数和耗时。
- 工作区默认按需下载 Git LFS 内容，避免 Task 启动时下载与任务无关的大型图片、视频等资源；需要时可按路径执行 `git lfs pull --include=<path>`。
- 飞书项目 webhook 默认可使用已认证的 Meegle CLI 读取工作项、查询评论并回写结果，不再要求客户创建飞书项目插件；插件后端改为显式选择。
- 修复飞书项目插件后端的工作项和评论 API 路径，避免 webhook 预取返回 404 后 Agent 无法启动或评论无法写回。
- Meegle CLI 后端在 webhook 完成鉴权和接收落账后立即返回，后续读取与任务启动不再因飞书请求超时或客户端断开而取消。

## 0.2.7

- 新增 `jarvis-box tasks create` 命令，允许维护等定时任务通过 CLI 创建正式 Task 并在状态页可见。
- 新增 `tasks start --in-place`，维护/自改进任务直接在源目录启动，不再每次执行产生冗余的 source+run 双任务。
- 定时维护与自改进任务会按各自用途执行，不再误进入 issue 处理流程。
- 正式支持 GitLab commit URL 触发 jarvis-command，状态页任务标题不再为空。
- ChatBridge 批量取消不再误伤 workspace 已清理的已完成任务。
- Jarvis Box 状态页面服务地址默认显示 `0.0.0.0`（此前无 WEBHOOK_HOST 时回退到 `127.0.0.1`）。
- `tasks create` 会拒绝越出允许目录的路径和重复任务创建，减少错误任务与越界文件访问风险。
- 无需代码仓库的定时维护与自改进任务现在可以正常运行；服务重启后任务状态会恢复为实际结果，不再长期停留在错误状态。
- 任务结束后的资源回收更加可靠，减少残留进程及其导致的后续任务异常。

## 0.2.6

- GitHub 真实交付发布门禁改用 GitHub webhook `ping` delivery 验证公网入站可达性，不再依赖 runner 回环访问临时 tunnel URL，避免有效公网链路被误判失败。

## 0.2.5

- GitHub 真实交付发布门禁改用 runner 当前 OS 用户已认证的 Claude，并在 Task 进入失败、需处理或取消终态时立即停止，不再继续空等 Pull Request 超时。

## 0.2.4

- 修复 Native 首次安装在 macOS launchd 启动较慢时过早失败的问题；安装器会在有限窗口内等待服务真正就绪。

## 0.2.3

- 新增一键 Docker 安装入口，自动完成镜像下载、加载和启动；下载过程兼容旧版 `curl`，并对临时网络错误执行有限重试。
- Native 安装会在 `~/.jarvis-box` 内自动安装和管理随版本发布的 UVIM 连接器，并在升级时迁移已有配置与状态，不再依赖旧的 `~/.hengshi` 连接器路径。
- 优化部署构建缓存复用和精确清理，重复安装与发布验证更快，同时避免遗留无人引用的临时镜像。

## 0.2.2

- 客户安装下载对临时 TLS、连接和 HTTP 错误执行有限重试，覆盖入口脚本、版本化安装器与发布包。
- Native 安装不下载或替换 `gh`、`glab`、Codex、Claude 等 provider/Agent CLI，直接复用安装者当前 OS 用户已有的工具与认证；缺少某项工具不阻塞无关 provider 的安装。
- Docker 默认以发起部署的当前 OS 用户 UID/GID 运行 Jarvis Box，不自行提权、不创建额外服务用户，也不使用 root 所有的客户数据目录。
- 新部署将 state、Agent HOME、运行时认证和依赖缓存统一保存到宿主机当前用户拥有的 bind-mount 目录，容器重建后仍可直接复用。
- 为任意宿主机 UID/GID 生成完整的容器用户身份，使 HOME、`getent`、Node.js 用户信息、SSH 和 Agent 工具在同一非 root 身份下闭环。
- 加固部署配置与备份边界：加载配置前先校验物理路径和所有权，备份始终使用当前 deployment home 并以私有权限创建。
- 拒绝把 Docker deployment home 放入任意 Git checkout，避免客户 Jarvis 源码、建设材料与 runtime state 混写。
- 发布 provenance gate 同时支持 fast-forward 与 squash merge：必须定位已合并 MR 的成功 source pipeline，并且 source/tag Git tree 完全一致才允许发布。

## 0.2.1

- 修复 GitLab 合并请求与工作项使用相同编号时的标题、链接和制品错位，确保评审始终绑定正确的项目与合并请求。
- 恢复自动评审跟进链路：识别标准 Jarvis bot 身份、避免终态交界重复启动，并在合并请求评论和 Status 页面持续展示跟进任务的执行状态。
- 恢复合并后 self-skills-improve 任务，并将 followup、self-skills-improve、external cleanup 和 dependency cache 纳入完整 Task/Run happy-path 证据。
- Native 与 Docker 统一复用客户无关的标准依赖缓存，覆盖 Go、JavaScript、Python、Java、Rust、C/C++ 等常见生态；Docker 通过持久命名卷保留缓存，未知或项目特殊工具使用显式可选 hook。
- 修复 Docker 中 GitLab 项目访问 Token 可调用 API 却无法 clone 的凭据用户名问题，并让 workspace cleanup 接受 Task 注册的规范 workspace ID。
- 加固 release gate：企业微信使用无 GUI 协议 envelope，external resource cleanup 经过真实 Jarvis 二进制和 production finalizer，CI 镜像缓存与多架构 systemd/launchd 证据保持分层执行。
- Docker 改为公网 archive 一键加载：客户无需访问内网 Registry、登录镜像仓库或手工校验 checksum。

## 0.2.0

- 将 Jarvis Box 稳定为客户中立的 Task/Run、workspace、Agent 和 provider writeback 运行时；Company Jarvis 与 Runtime Foundation 独立拥有客户知识、workflow 和定时认知工作。
- Native 安装和升级始终使用发起安装的现有 OS 用户，保留实际 runtime root、历史 state 与原始时间信息；服务运行或存在 active Task 时拒绝替换 artifact，不提供绕过检查的安装 force 模式。
- Docker 提供两条明确认证路径：导入当前 Host 用户的可移植身份，或直接在持久容器 Agent HOME 内登录；provider execution token 和 Agent credential 不进入 `runtime.env`。
- 重建分层端到端证据模型：release gate 验证 GitHub/GitLab 真实交付与 Docker 认证、企业微信/钉钉真实 IM provider 以及 Jira；MR 阶段验证统一 IM core、飞书 transport stub 和飞书项目 core shim，不再把 stub 或局部测试表述为 provider 认证。
- Code Review 依次使用源分支 repo skill、目标分支 repo skill 和 Agent 默认方法；缺少 repo-local `code-review` skill 不再中止任务。
- 统一当时的多发布面事务；同一版本制品必须逐个 SHA-256 一致，全部验证通过后才更新稳定版本指针。
- 修复 `/status` 在 task mutation 后丢失当前选择的问题，并把部署模式、scheduler owner 与 live transport evidence 纳入运行测试方法。

## 0.1.38

- Native 安装与服务以已有 OS 用户身份运行；Docker 部署可将宿主 `gh`、`glab`、Codex 和 Claude 认证导入私有 runtime auth 目录，凭据不进入镜像。
- 完成生产 happy-path 契约，覆盖 GitHub、GitLab、统一 IM 及认证的企业微信/飞书/钉钉 adapter、Jira 和飞书项目，包括 Task/Run identity、精确 workspace checkout、provider writeback、terminal lifecycle 和 lease-aware cleanup。
- 跨 adapter 运行复用认证的 IM 构建镜像与外部缓存，同时为受支持的 Docker runner 保留可移植冷启动路径。

## 0.1.37

- 修复 GitHub command workspace 创建逻辑，确保 GitHub 任务始终 clone 其 GitHub 仓库，不再回退为 GitLab clone URL。
- 为 GitHub、GitLab、Jira 和 IM 补齐闭环 happy-path 覆盖，横跨 ingress、Task/Run、workspace 语义、Agent 执行、provider writeback 和 cleanup。
- 认证企业微信、飞书和钉钉 adapter，通过一个共享生产镜像完成，同时保留各 provider 的原生 ingress 与回复协议。
- 使钉钉 fixture 兼容 Docker Compose 1.29：注入完整作用域的 admission allowlist，不使用嵌套插值默认值。
- 防止已存在等价 merge-request pipeline 的开放 MR 重复触发分支 pipeline。

## 0.1.36

- 使 jarvis-box 成为客户中立的 Task/Run 运行时：客户 Jarvis 的 bootstrap、sync、discovery roots、定时认知工作和 scheduler 策略由客户 Runtime Foundation 拥有，不再属于 jarvis-box 配置。
- 从正式 Docker 运行时中移除 Jarvis checkout 挂载、context manifest、deployment lock 和客户专属 workspace 工具假设。
- 新增带版本的 Workflow Runtime Contract，包含精确 action grant、经验证的 provider writeback 和显式的客户自有 workflow 链式调用。
- 新增真实的 GitLab issue→Claude→MR Docker E2E，并在 Agent 退出和 workflow action 交付后保留其完成证据。
- 加固 Task workspace 所有权、进程回收和清理，确保服务生命周期操作不作用于无关或所有权模糊的工作。
- 扩展 `doctor`，验证系统 skills 和进程启动所使用的可写 Codex 托管目录，并提供可操作的 ownership 修复指引。
- 以真实宿主平台证据加强 Darwin/Linux 进程表、权限和信号契约的 runtime-test 指引。
- 加固 contract-workflow workspace 交接：清理父 workspace 运行时字段（`path`、`task_id`），保留所有权身份（`remote`、`project`），防止嵌套 workflow run 复用过期或冲突的子路径。
- 修复 release overlay 基线/版本校验，使 Docker 镜像与部署文档可同时发布并仍然通过严格的生产发布门禁。
- 补充 Monkey Test issue→Claude→MR 真实 issue 冒烟路径，包括 fixture 变量提取和闭环行为的 provider evidence 检查。
- code-review workflow 按“源分支规则、目标分支规则、Agent 默认方法”的顺序选择评审方法；仓库没有 `skills/code-review/SKILL.md` 不再导致任务启动失败。
- 启动 contract workflow 时保留父任务 workspace 上下文，使嵌套 bugfix/replay 流程保持同一 workspace，避免 workspace 冲突失败。
- 将 runtime 基础能力收敛为 Runtime-Agent 所有，jarvis-box 聚焦于 Task/Run、控制面、runtime-job transport 和 workflow-contract 校验。

## 0.1.35

- 在正式 jarvis-box 镜像中内置固定版本的 `uv-im-connector` 可执行文件，使两个 Compose service 使用同一个客户可见的镜像 digest。
- 移除单独选择的 `UVIM_IMAGE` 部署输入，同时保持 connector 凭据、健康、日志和状态与 Agent 隔离。
- 每个 release bundle 附带客户运维手册，覆盖 Jarvis 生态、首次部署、直接 Docker Compose 操作、升级、回滚、备份、凭据轮换、诊断和移除。
- 将相同的客户文档发布到当时的公开版本 tag，并在源、bundle 或 GitHub 内容不一致时使 release 验证失败；稳定版本指针仅在上述检查和版本发布成功后更新。

## 0.1.34

- 将客户的 `create-jarvis` 构建过程与正式的 jarvis-box 生产部署分离。
- 为正式 Docker Compose 运行时添加不可变的 Company context 和 deployment lock，可选隔离的 `uv-im-connector`。
- 为 amd64 和 arm64 提供开箱即用、高权限的 root 容器。Docker socket 访问仍为显式选择启用的能力。
- 使生产部署和验证在当前及旧版 Docker Compose 上均可移植，不依赖宿主侧 `jq`。
- 通过内部 GitLab registry 以项目自有基础镜像发布，使 release 不依赖 Docker Hub 可用性。
- Native 安装器仅保留为显式的迁移/恢复通道。

## 0.1.33

- 使用普通空 Compose 环境文件用于客户 Runtime 启动和部署检查，包括拒绝 `/dev/null` 作为 env file 的 Docker Compose 实现。
