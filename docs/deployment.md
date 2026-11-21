# 正式 Docker 部署合同

本文面向把 Jarvis Box 作为 Docker Compose deployment 运行的客户管理员。它定义部署需要的权限、持久化边界和验证结果；具体日常操作和升级见[运维入口](operations.md)。Native 与 Docker 是并列部署模式，迁移期间不要让两套服务同时消费同一 Provider 身份或 webhook。

<a id="前置条件"></a>

## 部署前确认

- 从正式 release 取得并校验 release bundle 和 `SHA256SUMS`。私有 GitHub Release 不可用时，可从 `https://download.hengshi.com/jarvis-box` 获取同名文件，但仍要校验同一份 SHA256SUMS。
- 准备本 release 的正式 `JARVIS_IMAGE`：可访问 registry 时使用 `production-image.json` 中的 digest；离线时先 `docker load` 对应 `.docker.tar.gz` 并使用 `hengshi/jarvis-box:vX.Y.Z`。
- 部署用户能使用 Docker，拥有目标 deployment home，并已获得所需 Agent/provider 身份与可选 Docker socket 的批准。
- Linux Host 已启用 `cron` 且部署用户可用 `crontab`；macOS 使用该用户的 launchd。这些只看护宿主更新执行器，不会在容器中安装第二个 scheduler。

普通 Task 不依赖客户知识包、定制 workflow 或 Runtime Foundation。它们准备好且验证后可单独接入。基础 image 缺少客户代码所需系统依赖时，先构建[客户派生 Docker 镜像](custom-docker-image.md)，并把派生镜像 digest 写入 `JARVIS_IMAGE`。

<a id="deployment-home"></a>

## Deployment home 是实例边界

```text
<deployment-home>/
├── deployment.env       # Compose/operator settings
├── runtime.env          # canonical Jarvis runtime configuration
├── auth/                # imported portable credentials, private (0700/0600)
├── connector.env        # managed uvim only; may remain empty when disabled or external
└── data/                # Agent HOME, state, workspaces, logs and other persistent data
```

不要将 Jarvis repo、checkout、`jarvis-context.json`、deployment lock 或 readiness state 写入这里。每个实例必须有独立 deployment home、Compose project name、端口、Provider webhook URL、runtime env、`auth/` 和 `data/`。不要共享 state、workspace、Agent HOME、connector state 或 dependency cache。多实例规则见[多实例部署](multi-instance.md)。

<a id="start-and-identity"></a>

## 身份与认证

Docker 支持两条路径，二选一；两条都不挂载 Host HOME、Keychain、SSH agent 或完整 credential store。

### A. 导入当前 Host 用户的可移植身份

这是推荐路径。`start` 默认先运行 `auth-import`，将选定的 `gh`/`glab` token、Codex `auth.json`、Claude `.credentials.json` 或显式 headless key 放入私有 `auth/`，再写入持久 `/home/jarvis`：

```bash
scripts/deploy-production.sh /absolute/deployment-home start
scripts/deploy-production.sh /absolute/deployment-home shell
```

Host 上有多个 GitHub 身份时，在 `deployment.env` 中设置 `JARVIS_GITHUB_USER`。无法导出的 Keychain 身份可在 Host 的交互终端执行一次 `auth-import`。非交互导入可由 `JARVIS_GITHUB_TOKEN`、`JARVIS_GITLAB_TOKEN`、`JARVIS_CODEX_API_KEY` 或 `JARVIS_ANTHROPIC_API_KEY` 仅供导入命令读取；不要把它们写进 `runtime.env`。

### B. 只在持久容器 Agent HOME 中登录

在 `deployment.env` 设 `JARVIS_AUTH_IMPORT=skip`，启动后进入容器的持久 Agent HOME，登录实际需要的 CLI，再重建和验证：

```bash
scripts/deploy-production.sh /absolute/deployment-home start
scripts/deploy-production.sh /absolute/deployment-home shell
# In the shell, complete only the required gh/glab/codex/claude login, then exit.
scripts/deploy-production.sh /absolute/deployment-home compose up -d --force-recreate jarvis-box
scripts/deploy-production.sh /absolute/deployment-home verify
```

容器重建会保留此身份；删除 `<deployment-home>/data/agent-home` 才会清除它。Native 没有隔离层：安装器使用安装发起人的现有 OS 用户和 HOME，不创建 `jarvis` 或 `jarvis-box` 用户。

<a id="generic-verification"></a>

## 首次配置、启动和验证

在 `runtime.env` 填写真实 Provider scope、webhook secret、Agent 选择以及必要的 connector 设置。新部署样例启用 `JARVIS_ISSUE_POST_CHECK_ENABLED=true` 和 `JARVIS_PROVIDER_WRITEBACK_ENABLED=true`；用户/会话 allowlist 可留空，但项目、仓库和其他 source scope 不能用空值假定全部允许。完整变量解释见[配置参考](configuration.md)。

启动并验证：

```bash
ops=/absolute/path/to/extracted-release/scripts/deploy-production.sh
home=/absolute/path/to/deployment-home

"$ops" "$home" start
"$ops" "$home" verify
```

`verify` 应确认：运行镜像与 digest pin 一致；服务以安装用户对应的非 root 身份运行；通用 `skill-creator` 可发现而 create-jarvis 未进入运行时；Agent doctor/smoke 可用；runtime profile 与 connector 一致；可选 connector 和 Docker socket 正常；以及重建容器后 Agent HOME 与 Task/Run state 仍保留。

`verify` 不读取客户 Jarvis repo、验证客户 workflow/ref，或写 readiness lock。通过后，仍应从每个已接通 Provider/IM 入口完成一项实际工作，确认 Agent 结果、原工作项/会话收到的回复、审计记录和 workspace 清理。

<a id="jarvis-runtime-foundation"></a>
<a id="connector-and-docker-socket"></a>

## Connector、Runtime Foundation 与 Docker socket

`JARVIS_CONNECTOR_PROFILE` 只写在 `runtime.env`。设置为 `uvim` 后，release 使用同一 image 启动本实例的 connector service；connector 使用独立 env、state 和平台凭据。Native 的 `uvim` 也使用 release 自带的 binary，在当前用户下安装 companion service；主服务与 connector 是独立进程和状态目录，由同一 release 管理。

设置为 `uvim-external` 则连接管理员维护的共享 hub。URL 与本实例独有的非空 scoped client token 写入私有 `runtime.env`；本部署不读取 hub 的平台凭据，不创建本地 connector，也不管理共享 hub。`verify` 核对 hub 健康、经认证的 meta 以及本 deployment 没有受管 connector，不把 hub 版本当作 Box 内置组件版本。调用方隔离要求见 [IM 接入](integrations/im.md#管理员-配置-jarvis-box-与-connector)。

默认不挂 Docker socket。仅在客户明确同意 runtime 获得宿主 root 等价 Docker 能力时设置 `JARVIS_ENABLE_DOCKER_SOCKET=1`。

客户 Runtime Foundation 不是首次启动前置条件。准备好后，Host Runtime Agent 通过通用 transport 在正式环境执行客户自己的命令：

```bash
"$ops" "$home" runtime-job \
  <jarvis-bootstrap-command> <approved-remote> <approved-ref> \
  <disable-in-container-scheduler-option>
"$ops" "$home" runtime-job <quick-sync-command>
"$ops" "$home" runtime-job <runtime-foundation-doctor>
```

客户 bootstrap、recovery sync 和宿主 scheduler 的全量 sync 必须显式关闭容器内 scheduler；无法关闭时 Foundation 接入必须停止。临时 bootstrap material 删除后，稳定命令、缓存、状态、日志和 discovery roots 必须仍在持久 Agent HOME。Jarvis Box 不解释这些命令，也不读取客户 repo。

<a id="upgrade-and-rollback"></a>

## 升级与回滚边界

Jarvis Box 升级替换 image 并重跑 `verify`；客户 Jarvis revision 由其 Runtime Foundation 的 remote/cache/sync/discovery 流程更新，二者独立。升级、`start` 或会停止/重建服务的 Compose 动作都会 preflight Task state。有生命周期阻断项或无法证明当前状态时，在停服前退出。

`--force deploy` 和 `--force start` 通过原容器的 TaskService 暂停可续接的运行，并在目标容器就绪后自动恢复。参数位置与详细流程见[运维入口](operations.md#使用宿主机自助升级入口)。

不要绕过 `deploy-production.sh` 直接 `docker compose down`、重建容器或删除 `<deployment-home>/data/runtime-hostname`。该文件保存稳定机器身份，旧部署接管时也会保留旧 container hostname，以便依赖 hostname 的加密凭据仍可读取。回滚不是只换旧 image digest：恢复匹配旧 release 的完整 deployment-home 备份（包括 `auth/`、connector state、runtime hostname 与其他 data），再使用同一 release 的 `deploy` 和 `verify`。完整步骤见[运维入口](operations.md#升级)。

<a id="docker-非-root-部署契约"></a>

## 非 root 所有权合同

正式 Docker 路径由现有安装用户运行 `scripts/deploy-production.sh`。脚本拒绝 root 与 UID/GID 不一致配置，并预创建 `$JARVIS_DEPLOYMENT_HOME/data/*`；Compose 用同一 UID/GID 运行 Jarvis Box 和 connector。产品不创建专用 `jarvis` 用户、不使用 Docker named volume，也不会接管宿主 Docker daemon、DNS 或网络配置。
