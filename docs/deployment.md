# 正式 Docker 部署合同

## 前置条件

- 已从私有 `hengshi-jarvis/jarvis-box` GitHub Release 下载并校验 release bundle；GitHub Release 不可用时可从公开 S3 mirror `https://download.hengshi.com/jarvis-box` 下载同名文件，但仍必须使用同一份 `SHA256SUMS` 校验；
- `JARVIS_IMAGE` 固定到 OCI digest；
- 客户批准正式 Agent/provider 权限和可选 Docker socket；
- 若需要客户 Jarvis，Jarvis repo 已交付可执行 Runtime Foundation。

Jarvis 构建由 Host Runtime Agent + create-jarvis 完成，不依赖 jarvis-box。

基础镜像无法满足客户代码仓库的系统编译依赖时，使用[客户派生 Docker 镜像](custom-docker-image.md)。派生镜像必须以当前 release 的正式 digest 为基础、推送到客户私有 registry，并把派生镜像 digest 写入 `JARVIS_IMAGE`；不要在运行中的容器里执行 `apt install`。

## Deployment home

```text
<deployment-home>/
├── deployment.env
├── runtime.env
├── auth/              # 自动导入的私有身份快照，0700/0600
└── connector.env      # 仅启用 uvim 时需要；禁用时 helper 可创建空文件
```

这里不保存或挂载 Jarvis repo，不存在 `jarvis-context.json`、`deployment-lock.json` 或替代 manifest。
同一宿主机部署多个 Jarvis Box 时推荐使用 Docker。每个实例必须使用独立 deployment home、Compose project name、端口和 provider webhook URL。不要共享 `data/`、`auth/` 或 runtime env file。操作细则见 [多实例部署](multi-instance.md)。

## Start and identity

首次 onboarding 在 `runtime.env` 设置 `JARVIS_SERVE_MODE=read-only`。Docker 身份只有下面两条受支持路径，二选一即可。

**Path A：自动导入宿主机当前用户身份（推荐）。** `start` 会先以当前宿主机用户执行 `auth-import`，把选定的 `gh/glab` 与可移植 Agent 身份导入私有 `auth/`，再启动容器；不接受业务写入。

```bash
scripts/deploy-production.sh /absolute/deployment-home start
scripts/deploy-production.sh /absolute/deployment-home shell
```

宿主机已有多个 GitHub 账号时，在 `deployment.env` 设置 `JARVIS_GITHUB_USER` 明确选择 machine user。无法导出的系统 Keychain 身份可在宿主机交互终端执行一次 `auth-import`；无交互环境使用 `JARVIS_GITHUB_TOKEN`、`JARVIS_GITLAB_TOKEN`、`JARVIS_CODEX_API_KEY` 或 `JARVIS_ANTHROPIC_API_KEY`。这些变量只供导入命令读取，不写入 `runtime.env`。

**Path B：只在容器 Agent HOME 中登录。** 在 `deployment.env` 设置 `JARVIS_AUTH_IMPORT=skip`，启动后进入持久 Agent HOME 完成需要的 `gh auth login`、`glab auth login`、`codex login` 或 `claude` 登录，再重建服务并执行 `verify`。容器重建不会清除该身份；删除 deployment home 下的 `data/agent-home` 才会清除。

```bash
scripts/deploy-production.sh /absolute/deployment-home start
scripts/deploy-production.sh /absolute/deployment-home shell
# 在 shell 内只登录实际启用的 provider / Agent，然后 exit
scripts/deploy-production.sh /absolute/deployment-home compose up -d --force-recreate jarvis-box
scripts/deploy-production.sh /absolute/deployment-home verify
```

两条路径都不要复制或挂载 Host HOME、Keychain、SSH agent 或整个 credential store，也不要把执行 Token 写入 `runtime.env`。

Native 部署没有隔离边界：安装器使用发起安装的现有 OS 用户（sudo 时为 `SUDO_USER`）作为 systemd/launchd `User` 和 HOME，因此直接复用该用户已有的 `gh/glab/codex/claude` 认证。安装器只验证用户存在，绝不创建 `jarvis` 或 `jarvis-box` 用户。

## Jarvis Runtime Foundation

jarvis-box 不负责 Jarvis bootstrap。Host Runtime Agent 使用客户 Jarvis repo 的指令，通过通用 helper 在正式环境内执行：

```bash
scripts/deploy-production.sh /absolute/deployment-home runtime-job \
  <jarvis-bootstrap-command> <approved-remote> <approved-ref> \
  <disable-in-container-scheduler-option>

scripts/deploy-production.sh /absolute/deployment-home runtime-job <quick-sync-command>
scripts/deploy-production.sh /absolute/deployment-home runtime-job <runtime-foundation-doctor>
```

Bootstrap、recovery sync 和宿主调度的全量 sync 必须使用客户 Jarvis 的显式 skip-scheduler 选项。Docker 部署以 host Scheduler Adapter 为权威；若客户 Runtime Foundation 无法禁用容器内 scheduler，onboarding 必须 fail closed。

Bootstrap 的临时 material 删除后，stable commands、cache、state/log 与 Agent discovery roots 必须仍在持久 Agent HOME 中可用。真实 Agent discovery probe 属于 Jarvis onboarding，不属于 jarvis-box generic probe。

Jarvis-owned host Scheduler Adapter 也调用 `runtime-job`。内部 sync、memory-consolidation、daily-reflection 和 cognitive-evolution command 不调用 Docker。

Runtime Foundation doctor、真实 Agent discovery 与下述 generic verification 通过并得到客户批准后，才把 `runtime.env` 切为 `JARVIS_SERVE_MODE=worker`；只启用已经具备适用 Jarvis workflow 的业务 lane，再执行首个监督任务。

## Generic verification

```bash
scripts/deploy-production.sh /absolute/deployment-home verify
```

验证项：

1. running image 与 digest pin 一致；
2. container-root authority 和 batteries-included toolchain；
3. generic `skill-creator` 可发现，create-jarvis 未进入 runtime；
4. Agent doctor 和 smoke；
5. runtime profile 与 connector service 一致；
6. 可选 connector protocol/version/capability；
7. 可选 Docker socket；
8. container recreation 后 Agent HOME 与 Task/Run state 仍存在。

它不读取 Jarvis repo、校验客户 workflow/repo refs或写 readiness lock。

## Connector and Docker socket

`JARVIS_CONNECTOR_PROFILE=uvim` 只写在 `runtime.env`。同一个 `JARVIS_IMAGE` 启动 connector service，但 connector 使用独立 env/state/credential boundary。

Native 部署不要求客户另行下载或维护 connector。release archive 同时携带 `jarvis-box` 与 `uv-im-connector`，installer 以当前 OS 用户安装 companion systemd/launchd service；provider secret 只放在 `${JARVIS_RUNTIME_ROOT}/envs/.env.uv-im-connector`。主服务与 connector 分属不同进程和状态目录，但由同一 Jarvis Box 版本和 installer 共同管理。

默认不挂 Docker socket。只有客户明确批准 host-root-equivalent capability 时在 `deployment.env` 设置 `JARVIS_ENABLE_DOCKER_SOCKET=1`。

## Upgrade and rollback

jarvis-box 升级只替换 digest-pinned image 并重跑 generic verify；持久 volumes 保留。Jarvis 更新由其 remote → cache → sync → discovery roots 处理，不要求改变 image。回滚 image 与回滚 Jarvis revision 是两个独立操作。

Native 与 Docker 是并列部署面；迁移时不得让两套服务同时消费同一 provider identity 或 webhook。

Docker 升级、`start` 和会停止或重建服务的 `compose` 子命令会先读取同一 deployment home 的 Task state。存在 active、waiting、finalizing、CI-wait 或 recovery-required Task 时，脚本会在 `docker compose down`、`stop` 或 `up --force-recreate` 前退出并打印阻断 Run。只有客户明确决定放弃当前运行时，才使用 `--force`；force 要求当前 jarvis-box 容器仍在运行，并要求 `JARVIS_DOCKER_UPGRADE_FORCE_STRATEGY` 记录取消/恢复策略。脚本会先把策略和受影响 Run 写入 `<deployment-home>/data/upgrade-preflight/`，再在容器 PID namespace 内停止受影响 Run。无法枚举 Task state、缺少 force 策略或运行容器不可达时默认 fail closed。

## Docker 非 root 部署契约

正式 Docker 路径只有一个所有权模型：现有安装用户直接运行 `scripts/deploy-production.sh`，脚本拒绝 root、拒绝与当前 UID/GID 不一致的配置，并预创建 `$JARVIS_DEPLOYMENT_HOME/data/*`。Compose 使用同一 UID/GID 运行 Jarvis Box 与 connector，并挂载这些已预创建的目录。产品不创建专用 `jarvis` 用户，也不使用或迁移 Docker named volume。
