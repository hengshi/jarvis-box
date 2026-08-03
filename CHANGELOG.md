# 更新日志

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
- 在 `docs/e2e.md` 中记录 Monkey Test issue→Claude→MR 真实 issue 冒烟路径，包括 fixture 变量提取和闭环行为的 provider evidence 检查。
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
