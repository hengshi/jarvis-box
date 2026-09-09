# Jarvis Box 运维入口

按要完成的事情找命令。架构、内部 phase 和全部变量不属于日常操作。

## 先定义 Docker 命令

Native 用户不需要这一步。Docker 用户在当前 shell 定义：

```bash
ops=/absolute/release/scripts/deploy-production.sh
home=/absolute/deployment-home
```

后续示例中的 `"$ops" "$home"` 始终使用同一个 release 和 deployment home。

同一台机器运行多个实例时，推荐使用 Docker。Docker 始终通过对应 deployment home 调用 `"$ops" "$home"`，隔离 Compose project、端口、auth、state 和 workspace。Native 多实例不推荐；Native shell 设置 `JARVIS_ENV_FILE` 或 `JARVIS_RUNTIME_ROOT` 只能选择 runtime path，先用 `jarvis-box status --smart` 确认 `runtime_root`、`env_file` 和 `workspace_root`，但 service lifecycle 还必须单独确认 OS service identity。完整隔离规则见 [多实例部署](multi-instance.md)。

## Docker deployment 边界

Jarvis Box 运维脚本只管理当前 deployment home 和对应 Compose project 明确登记的资源。它不会重启或重新配置 Docker daemon，不会修改宿主网络或 DNS，不会执行宿主级 `docker system prune`、`docker container prune`、`docker network prune` 或 `docker volume prune`，也不会操作其他 deployment 的容器、network 或 volume。

Docker、DNS、网络或 registry 基础设施不可用时，运维脚本会停止并报告错误。客户的宿主机管理员负责在 Jarvis Box 之外诊断和恢复这些基础设施。

## 看状态

### Native

```bash
jarvis-box status
jarvis-box doctor
jarvis-box agent smoke
```

### Docker

```bash
"$ops" "$home" compose ps
"$ops" "$home" verify
```

Native 在本机访问 `http://127.0.0.1:8787/status`。Docker 默认发布到宿主机所有接口，可从受信任网络访问 `http://<docker-host>:8787/status`；若显式设置 `JARVIS_BIND_ADDRESS=127.0.0.1`，则只允许宿主机访问。`/status` 是诊断视图，不是客户 Jarvis 的知识源。

### 使用 Status 系统操作

从 `/status` 顶部打开“系统操作”，按目标选择：

- **系统概览**：先看“系统当前可用”或“发现 N 项需要处理”，再进入对应分区；版本、路径、进程/容器资源、脱敏配置和内部轮询位于“技术详情”。
- **处理问题**：查看 doctor 失败项；ChatBridge 自动重试未恢复时可重新连接即时消息；需要多步检查或处理时可交给 Jarvis，操作会创建可跟踪的 Task/Run。
- **工作方式**：修改默认 Agent 或某类工作的 Agent 覆盖。保存只影响以后新启动的 Run，不切换正在运行的 Agent；重新选回原 Agent 或“使用默认”即可恢复配置。
- **数据维护**：先执行“预检可清理项”。预检不删除数据；“确认清理”不可恢复，只删除超过保留期、已经终态并完成 workspace disposal 的 Task Artifact，不影响 active Task、正在运行的 Agent、service log 或依赖缓存。

`read-only` 是部署运行模式，不是用户角色。所有人看到同一页面；该模式允许查看、诊断和清理预检，但禁止创建 operator Task、修改 Agent 配置、重连 ChatBridge 和实际删除。按钮不可用时页面会说明原因，不要通过切换网络来源绕过运行模式。

系统操作完成后以页面重新读取的状态为准：Agent 配置看当前默认值/工作类型，消息重连看 running 与 provider connected，operator prompt 记录 Task ID/Run ID，清理查看逐项 `dry-run`、`cleaned`、`deferred` 或 `error`。失败时保留页面错误和对应服务日志，再按本页“出问题时按这个顺序”继续。

### 查看或恢复 Delivery Metrics 历史基线

Delivery Metrics 由 Status 服务管理枚举和启动节奏，实际分析是普通 `delivery-metrics` lane Task。打开 `/status` 或读取一次 value API，就会同步 Provider 历史并按节奏启动 pending Task：

```bash
curl -fsS 'http://127.0.0.1:8787/status/api/value?provider=gitlab' |
  jq '{warnings, analysis_progress, totals: (.snapshot.totals // null)}'
```

GitHub 使用 `provider=github`。阶段、Task Continue/Cancel、Agent scope 和完整恢复步骤见 [Delivery Metrics 历史基线操作手册](delivery-metrics.md)。

## 看日志

### Native

```bash
jarvis-box logs
jarvis-box monitor
```

### Docker

```bash
"$ops" "$home" compose logs --tail=200 jarvis-box
```

启用 IM 时，connector 日志单独查看：

```bash
"$ops" "$home" compose logs --tail=200 uv-im-connector
```

## 进入运行环境

Native 直接使用安装者当前用户的 shell。Docker 使用：

```bash
"$ops" "$home" shell
```

不要通过挂载 Host HOME、SSH agent 或 Keychain 修复认证。

## 停止或重启 Native 服务

```bash
jarvis-box stop
jarvis-box restart
```

默认会检查当前会阻断 lifecycle 的 Task。存在 active/running、waiting、ci-wait、finalizing 或 recovery-required Task 时操作被阻断，并列出下一步。用 `jarvis-box tasks list` 快速查看当前阻断项；需要历史排查时再用 `jarvis-box tasks list --all`。先等待、继续或取消任务。

`jarvis-box stop --force` 和 `jarvis-box restart --force` 会按 Task/Run 所有权执行停止与清理，只用于客户明确决定放弃当前运行的场景。安装器本身没有 force 模式。

这些 Native lifecycle 命令适用于单 Native 实例。Native 多实例主机不能只靠 `JARVIS_ENV_FILE` 或 `JARVIS_RUNTIME_ROOT` 选择 systemd unit；Linux 内置路径操作安装时的 `jarvis-box` unit。长期同机多实例应使用 Docker deployment home。

## 升级

`jarvis-box update --check` 会显示当前版本、目标版本、元数据来源和可用下载源。`jarvis-box update` 通过已安装 release bundle 中的 `install.sh` 自动下载目标版本：优先使用私有 `hengshi-jarvis/jarvis-box` GitHub Release，无法访问或下载失败时改用 `https://download.hengshi.com/jarvis-box` 的公开 S3 mirror；最后仍以 `SHA256SUMS` 校验为准。安装器发现已有服务仍在运行时会在替换 artifact 前停止并提示先规范停服。它不会自动取消 Task。

### Native

```bash
jarvis-box tasks list
jarvis-box stop
sudo bash install.sh
jarvis-box doctor
jarvis-box agent smoke
```

默认 `tasks list` 应为空；若列出 Task，先等待、Continue 或 Cancel。历史排查使用 `jarvis-box tasks list --all`。安装器发现已有服务仍在运行时会在替换 artifact 前停止并提示先规范停服。它不会自动取消 Task。

### Docker

#### 使用宿主机自助升级入口

Docker 部署不要求宿主机安装 `jarvis-box` 二进制。包含此能力的 release 会在 deployment home 写入由该实例拥有的 `update.sh`，以后直接运行 `bash /absolute/deployment-home/update.sh`，或用 `--version X.Y.Z` 锁定目标版本。完整的首次 bootstrap、`latest.json`/`SHA256SUMS` 校验、失败边界和 prerequisites 见同一 release bundle 根目录的 `CUSTOMER-OPERATIONS.md` 的“宿主机自助升级”章节。

只有 `latest.json` 明确提供 `docker_update` 时才表示当前 latest 已发布该入口；没有该字段时继续使用下方手工流程，不要猜测下载 URL。

先用默认快速列表确认没有正在执行或等待恢复的 Task，然后从私有 `hengshi-jarvis/jarvis-box` GitHub Release 获取同一版本的 release bundle、`SHA256SUMS` 和 `production-image.json`；GitHub Release 下载不可用时使用 `https://download.hengshi.com/jarvis-box/releases/v<version>/` 下的同名 mirror 文件。GitHub 下载需要 repository access，公开 mirror 无需登录；运行时 license enforcement 是独立边界。校验制品后，将已加载的目标镜像包标签 `hengshi/jarvis-box:v<version>` 或 `production-image.json` 中的 GHCR `image_ref` 写入现有 `$home/deployment.env` 的 `JARVIS_IMAGE`，再使用目标 release bundle 内的 `deploy-production.sh`。不要手工判断部署模式后直接执行 Docker 停服命令。

```bash
jarvis-box tasks list
"$ops" "$home" deploy
"$ops" "$home" verify
```

`deploy` 会在任何 `docker compose down` 或重建前读取 `$home/data/state/runs` 的 Task 生命周期。存在 active、waiting、finalizing、CI-wait 或 recovery-required Task，或无法证明没有这类 Task 时，脚本会先退出并打印阻断 Run。客户明确决定放弃当前运行时才使用 `"$ops" "$home" --force deploy`；force 要求 jarvis-box 容器仍在运行，并要求设置 `JARVIS_DOCKER_UPGRADE_FORCE_STRATEGY`。脚本会把策略和受影响 Run 写入 `$home/data/upgrade-preflight/` 后再停止 Run、继续服务变更。

Docker 部署脚本把容器的持久机器身份记录在 `<deployment-home>/data/runtime-hostname`。首次接管旧部署时，它会在替换容器前保留旧容器的实际 hostname，使依赖 hostname 的加密凭据在升级后仍可读取。不要绕过 `deploy-production.sh` 重建服务，也不要单独删除、复制或编辑该文件；身份与现存容器不一致时，脚本会在 `down` 前拒绝继续。

回滚时不能只恢复旧 digest：必须同时保留并恢复匹配旧 release 的完整 deployment-home 备份（包括 `auth/`、`data/connector-state/`、`data/runtime-hostname` 和其他 `data/` 状态），再执行同样两条命令。目标部署已经开始后不要只替换 image 盲目回滚；按 updater 输出的备份和人工恢复指引处理。Jarvis revision 更新由 Runtime Foundation 完成，不与 jarvis-box image 升级绑定。

## 更新认证

### Native

在安装者当前 OS 用户下更新 `gh`、`glab`、Codex 或 Claude 登录，然后执行受影响的 doctor/smoke。

### Docker

```bash
"$ops" "$home" auth-import
"$ops" "$home" verify
```

自动导入只复制批准的可移植身份，不复制整个 Host credential store。IM provider secret 始终留在 `connector.env` 和 connector 边界。

## 备份

Native 备份实际 runtime root 中的 state、workspace、logs、Agent identity/config。路径以安装器输出和运行配置为准，不假设固定历史目录。

Docker 备份完整 deployment home；持久数据都位于其中的 bind directories：

- `<deployment-home>/data/agent-home`
- `<deployment-home>/data/workspaces`
- `<deployment-home>/data/state`
- `<deployment-home>/data/logs`
- `<deployment-home>/data/config`
- `<deployment-home>/data/connector-state`（启用 IM 时）
- `<deployment-home>/data/runtime-hostname`

备份脚本通过同一个部署入口执行 `compose stop`，因此也会先做 active-task preflight。存在未完成 Task 时先等待、继续或取消；不要绕过脚本直接停容器。

## 出问题时按这个顺序

1. 看 `status`，确认失败属于 Delivery Metrics、provider、Task/Run、Agent 还是 connector；
2. 运行 `jarvis-box doctor` 和 `jarvis-box agent smoke`，Docker 使用 `verify`；
3. 看对应服务日志，不先改 state 文件；
4. 检查 provider allowlist、认证 capability 和真实 writeback；
5. 仍无法恢复时，保留 Task state、event 和日志证据再处理。
