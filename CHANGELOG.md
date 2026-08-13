# 更新日志

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
- 恢复合并后 self-skills-improve 任务，并将 followup、self-improve、external cleanup 和 dependency cache 纳入完整 Task/Run happy-path 证据。
- Native 与 Docker 统一复用客户无关的标准依赖缓存，覆盖 Go、JavaScript、Python、Java、Rust、C/C++ 等常见生态；Docker 通过持久命名卷保留缓存，未知或项目特殊工具使用显式可选 hook。
- 修复 Docker 中 GitLab 项目访问 Token 可调用 API 却无法 clone 的凭据用户名问题，并让 workspace cleanup 接受 Task 注册的规范 workspace ID。
- 加固 release gate：企业微信使用无 GUI 协议 envelope，external resource cleanup 经过真实 Jarvis 二进制和 production finalizer，CI 镜像缓存与多架构 systemd/launchd 证据保持分层执行。
- Docker 改为公网 archive 一键加载：客户无需访问内网 Registry、登录镜像仓库或手工校验 checksum。

## 0.2.0

- 将 Jarvis Box 稳定为客户中立的 Task/Run、workspace、Agent 和 provider writeback 运行时；Company Jarvis 与 Runtime Foundation 独立拥有客户知识、workflow、maintenance 和 self-improve。
- Native 安装和升级始终使用发起安装的现有 OS 用户，保留实际 runtime root、历史 state 与原始时间信息；服务运行或存在 active Task 时拒绝替换 artifact，不提供绕过检查的安装 force 模式。
- Docker 提供两条明确认证路径：导入当前 Host 用户的可移植身份，或直接在持久容器 Agent HOME 内登录；provider execution token 和 Agent credential 不进入 `runtime.env`。
- 重建分层端到端证据模型：release gate 验证 GitHub/GitLab 真实交付与 Docker 认证、企业微信/钉钉真实 IM provider 以及 Jira；MR 阶段验证统一 IM core、飞书 transport stub 和飞书项目 core shim，不再把 stub 或局部测试表述为 provider 认证。
- Code Review 依次使用源分支 repo skill、目标分支 repo skill 和 Agent 默认方法；缺少 repo-local `code-review` skill 不再中止任务。
- 统一 GitLab、GitHub 和公共下载站的发布事务；同一版本制品必须逐个 SHA-256 一致，全部验证通过后才更新 `latest.json`。
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

- 使 jarvis-box 成为客户中立的 Task/Run 运行时：客户 Jarvis 的 bootstrap、sync、discovery roots、maintenance 和 scheduler 策略由客户 Runtime Foundation 拥有，不再属于 jarvis-box 配置。
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
- 将相同的客户文档发布到公开 GitHub 版本 tag，并在源、bundle 或 GitHub 内容不一致时使 release 验证失败；`latest.json` 仅在上述检查和 GitHub Release 成功后更新。

## 0.1.34

- 将客户的 `create-jarvis` 构建过程与正式的 jarvis-box 生产部署分离。
- 为正式 Docker Compose 运行时添加不可变的 Company context 和 deployment lock，可选隔离的 `uv-im-connector`。
- 为 amd64 和 arm64 提供开箱即用、高权限的 root 容器。Docker socket 访问仍为显式选择启用的能力。
- 使生产部署和验证在当前及旧版 Docker Compose 上均可移植，不依赖宿主侧 `jq`。
- 通过内部 GitLab registry 以项目自有基础镜像发布，使 release 不依赖 Docker Hub 可用性。
- Native 安装器仅保留为显式的迁移/恢复通道。

## 0.1.33

- 使用普通空 Compose 环境文件用于客户 Runtime 启动和部署检查，包括拒绝 `/dev/null` 作为 env file 的 Docker Compose 实现。
