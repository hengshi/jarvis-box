# Jarvis Box 运维入口

按要完成的事情找命令。架构、内部 phase 和全部变量不属于日常操作。

## 先定义 Docker 命令

Native 用户不需要这一步。Docker 用户在当前 shell 定义：

```bash
ops=/absolute/release/scripts/deploy-production.sh
home=/absolute/deployment-home
```

后续示例中的 `"$ops" "$home"` 始终使用同一个 release 和 deployment home。

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

### 查看或恢复 Delivery Metrics 历史基线

Delivery Metrics 由 Status 服务运行，不属于 Task。它不会出现在 `jarvis-box tasks list`。打开 `/status` 或读取一次 value API，就会加载持久化队列并继续未完成分析：

```bash
curl -fsS 'http://127.0.0.1:8787/status/api/value?provider=gitlab' |
  jq '{warnings, analysis_progress, totals: (.snapshot.totals // null)}'
```

GitHub 使用 `provider=github`。阶段、错误码、Agent 切换和完整恢复步骤见 [Delivery Metrics 历史基线操作手册](delivery-metrics.md)。

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

默认会检查 active Task。存在 active Run 时操作被阻断，并列出下一步。先等待、继续或取消任务。

`jarvis-box stop --force` 和 `jarvis-box restart --force` 会按 Task/Run 所有权执行停止与清理，只用于客户明确决定放弃当前运行的场景。安装器本身没有 force 模式。

## 升级

### Native

```bash
jarvis-box stop
sudo bash install.sh
jarvis-box doctor
jarvis-box agent smoke
```

安装器发现已有服务仍在运行时会在替换 artifact 前停止并提示先规范停服。它不会自动取消 Task。

### Docker

确认没有正在执行的 Task，然后使用稳定公网入口完成运维包、镜像、配置更新、部署和验证：

```bash
curl -fsSL https://download.hengshi.com/jarvis-box/docker-install.sh \
  | bash -s -- <version> /absolute/deployment-home
```

```bash
"$ops" "$home" deploy
"$ops" "$home" verify
```

Docker 部署脚本把容器的持久机器身份记录在 `<deployment-home>/data/runtime-hostname`。首次接管旧部署时，它会在替换容器前保留旧容器的实际 hostname，使依赖 hostname 的加密凭据在升级后仍可读取。不要绕过 `deploy-production.sh` 重建服务，也不要单独删除、复制或编辑该文件；身份与现存容器不一致时，脚本会在 `down` 前拒绝继续。

回滚时恢复旧 digest，再执行同样两条命令。Jarvis revision 更新由 Runtime Foundation 完成，不与 jarvis-box image 升级绑定。

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

Docker 备份 deployment home 和需要保留的 named volumes：

- `<deployment-home>/data/agent-home`
- `<deployment-home>/data/workspaces`
- `<deployment-home>/data/state`
- `<deployment-home>/data/logs`
- `<deployment-home>/data/config`
- `<deployment-home>/data/connector-state`（启用 IM 时）
- `<deployment-home>/data/runtime-hostname`

备份可变数据前先规范停服，或使用客户认可的一致性备份方案。

## 出问题时按这个顺序

1. 看 `status`，确认失败属于 Delivery Metrics、provider、Task/Run、Agent 还是 connector；
2. 运行 `jarvis-box doctor` 和 `jarvis-box agent smoke`，Docker 使用 `verify`；
3. 看对应服务日志，不先改 state 文件；
4. 检查 provider allowlist、认证 capability 和真实 writeback；
5. 仍无法恢复时，保留 Task state、event 和日志证据再处理。
