# jarvis-box 客户部署与运维

本手册描述 public release 的 Docker 运行面。客户 Jarvis 的知识、workflow、runtime governance、bootstrap/sync/maintenance 和 Scheduler Adapter 由客户 Jarvis repo 自己拥有。

## 1. Jarvis 生态与边界

jarvis-box 提供：

- digest-pinned Docker image；
- Runtime Agent 与通用工具链；
- Task/Run、workspace、state、logs 和 control plane；
- provider loops 与可选 uv-im-connector；
- generic deployment、probe 和 `runtime-job` helper。

jarvis-box 不提供：

- Jarvis repo clone/pull/sync/install；
- Jarvis 目录 mount、context、deployment lock 或 readiness state；
- root skill 注入；
- 客户 Runtime Foundation 的内部任务或调度定义。

Runtime Agent 从持久 Agent HOME 的原生 discovery roots 发现 Jarvis skills。

## 2. 前置条件

- Docker Engine/Desktop 与 Docker Compose；
- 已校验的 release bundle；
- OCI image digest；
- 客户批准的正式 Agent/provider 权限；
- 如需客户 Jarvis，已发布的 Jarvis Runtime Foundation bootstrap/sync/doctor 合同；
- 可选 host-root-equivalent Docker socket 授权。

不要 clone 私有 jarvis-box 源码。Native 安装使用当前 OS 用户；Docker 使用 release bundle 的认证导入与 Compose helper。

## 3. 下载 release bundle 并验证

下载同一版本 bundle 与 `SHA256SUMS`，在解压前验证：

```bash
artifact=jarvis-box_<version>_<platform>.tar.gz
grep -E "  (${artifact}|production-image.json)$" SHA256SUMS | sha256sum -c -
tar -xzf jarvis-box-<version>-<platform>.tar.gz
```

macOS 使用：

```bash
grep -E "  (${artifact}|production-image.json)$" SHA256SUMS | shasum -a 256 -c -
```

从 release metadata 取得 `repository@sha256:...`，不要使用 `latest`。

## 4. Deployment home

在客户控制的私有绝对路径准备：

```text
<deployment-home>/
├── deployment.env
├── runtime.env
└── connector.env       # 仅启用 uvim 时需要
```

从 bundle 复制 examples 后填写，权限建议 `0600`。这里不放 Jarvis checkout、Host HOME、credential dump、context 或 lock。

`deployment.env` 至少包含：

```dotenv
JARVIS_DEPLOYMENT_NAME=jarvis-production
JARVIS_DEPLOYMENT_HOME=/absolute/deployment-home
JARVIS_IMAGE=registry.example.com/jarvis-box@sha256:<64-hex>
JARVIS_BIND_ADDRESS=127.0.0.1
JARVIS_PORT=8787
JARVIS_ENABLE_DOCKER_SOCKET=0
```

`runtime.env` 选择 Agent、provider allowlists/secrets 和 connector profile。Provider allowlist 是 operator 配置，jarvis-box 不从 Jarvis repo 推导。

首次 onboarding 保持：

```dotenv
JARVIS_SERVE_MODE=read-only
```

只有 Jarvis Runtime Foundation 已把适用 workflow 安装到 Agent discovery roots 后，才启用对应业务 lane：

```dotenv
JARVIS_ISSUE_POST_CHECK_ENABLED=false
JARVIS_WORKFLOW_GITLAB_ALLOWED_LABELS=
JARVIS_WORKFLOW_GITLAB_ALLOWED_STATUSES=
JARVIS_WORKFLOW_ALLOWED_START_TYPES=
```

后三项是精确 action 参数授权；空值不授权相应 label、status 或下一 workflow。它们是 operator/provider 安全配置，不是 jarvis-box 内建的客户状态机。

## 5. 首次启动与正式身份

```bash
release_dir=/absolute/path/to/extracted-release
deployment_home=/absolute/deployment-home

"$release_dir/scripts/deploy-production.sh" "$deployment_home" start
"$release_dir/scripts/deploy-production.sh" "$deployment_home" shell
```

在容器的持久 `/root` 中完成 Codex/Claude、`gh`/`glab`、文档/source 和 registry 原生登录。不要绑定 Host HOME、SSH agent 或浏览器 profile。这个 identity 可以具有客户批准的高权限，但必须能独立审计、轮换和撤销。

## 6. Bootstrap customer Jarvis

以下步骤由 Host Runtime Agent 按客户 Jarvis repo 的 runtime governance 执行。jarvis-box 只提供进入正式 Runtime Environment 的 transport。

```bash
"$release_dir/scripts/deploy-production.sh" "$deployment_home" runtime-job \
  <jarvis-bootstrap-command> <approved-remote> <approved-ref> \
  <disable-in-container-scheduler-option>
```

Bootstrap 应把 cache、stable commands、state/log 和 discovery material 安装到持久 Agent HOME，并显式禁止在容器内安装 scheduler；若客户 Runtime Foundation 没有对应参数，本次 Docker onboarding 必须停止。删除临时 checkout/archive 后继续验证：

```bash
"$release_dir/scripts/deploy-production.sh" "$deployment_home" runtime-job <quick-sync-command>
"$release_dir/scripts/deploy-production.sh" "$deployment_home" runtime-job <runtime-foundation-doctor>
```

然后用真实 Runtime Agent invocation 证明 Jarvis entry 可通过原生 discovery 找到。不要用文件存在代替 Agent 行为验证，也不要用 Jarvis mount 或 `JARVIS_HOME` 规避缺失的 Runtime Foundation。

## 7. Host scheduler adapter

Jarvis repo 提供的 Scheduler Adapter 在宿主 scheduler 中调用：

```bash
"$release_dir/scripts/deploy-production.sh" "$deployment_home" runtime-job <inner-command> [args...]
```

- Native scheduler 直接调用同一个 inner command。
- Docker host scheduler 调用上述 helper。
- Agent 已在容器内时直接调用 inner command。
- Inner command 不得调用 Docker。
- Runtime Job 把 state/log 写入持久 Agent HOME。
- Host scheduler 记录 helper/container launch failure。

bootstrap、恢复同步和 host-scheduled full sync 都必须传递 Jarvis 定义的 `--skip-scheduler-update` 等价参数，避免容器内安装第二套 scheduler。

## 8. Generic jarvis-box verification

```bash
"$release_dir/scripts/deploy-production.sh" "$deployment_home" verify
```

Generic probe 验证 image digest、root/toolchain、generic skill、Agent doctor/smoke、connector profile、可选 Docker socket，以及 container recreation 后 Agent HOME 和 Task/Run state 持久化。

它不读取 Jarvis repo、不验证客户 workflow/repo refs、不写 readiness lock。Jarvis Runtime Foundation doctor 与 Agent discovery probe 必须由第 6 节单独完成。

以上验证通过并得到客户批准后，把 `JARVIS_SERVE_MODE` 改为 `worker`，只启用已经存在适用 Jarvis workflow 的业务 lane，再用 `start` 重建服务并执行首个监督任务。这里没有额外 readiness 文件或状态机；真实配置、Runtime Foundation evidence 和 Construction Workspace work card 各自保留自己的事实。

## 9. Docker Compose 运维

```bash
"$release_dir/scripts/deploy-production.sh" "$deployment_home" compose ps
"$release_dir/scripts/deploy-production.sh" "$deployment_home" compose logs --tail=200 jarvis-box
"$release_dir/scripts/deploy-production.sh" "$deployment_home" shell
```

直接 Compose 操作必须始终加载同一 deployment env、Compose file、profile 和可选 Docker socket overlay；优先使用 helper。

## 10. Connector

启用时只在 `runtime.env` 设置：

```dotenv
JARVIS_CONNECTOR_PROFILE=uvim
JARVIS_UV_IM_CONNECTOR_URL=http://uv-im-connector:8787
JARVIS_UV_IM_CONNECTOR_TOKEN=<shared-token>
```

`connector.env` 保存 provider-native secrets，`UV_IM_AUTH_TOKEN` 与 shared token 一致。connector service 与 jarvis-box 使用同一 image digest，但不共享 Agent HOME、Git credentials、Docker socket 或 state volume。

## 11. Docker socket

默认 `JARVIS_ENABLE_DOCKER_SOCKET=0`。只有明确需要宿主 Docker executor 且客户批准时设为 `1`。容器 root + Docker socket 等价宿主 root；它不是普通构建权限。

## 12. 备份与恢复

备份 deployment home 与 named volumes：

- `jarvis-agent-home`：正式 identity/config、Agent discovery roots、Jarvis Runtime Foundation；
- `jarvis-workspaces`：Task workspaces；
- `jarvis-state`：Task/Run/resume state；
- `jarvis-logs`：diagnostics；
- `jarvis-config`：runtime-generated config；
- `connector-state`：connector state。

停止服务或采用客户认可的一致性方案后再备份可变 volumes。Secret backup 服从客户 secret-management policy。

## 13. 升级与回滚

### jarvis-box image

1. 下载并验证新 release；
2. 备份 deployment config/volumes；
3. 修改 `JARVIS_IMAGE` 为新 digest；
4. 执行 `deploy`；
5. 失败时恢复旧 digest 并再次 `deploy`。

### Customer Jarvis

通过 Jarvis Runtime Foundation 的 remote → cache → sync → discovery roots 更新。它不要求更换 jarvis-box image。回滚使用 Runtime Foundation 自己的 approved revision/rollback contract。

不要把两条更新路径合并为 context/lock，也不要在 running container 内临时覆盖 image-owned 文件后称为升级。

## 14. 故障诊断与责任边界

| Symptom | First source |
|---|---|
| bootstrap/sync/maintenance/self-improve failure | Runtime Foundation state/log in Agent HOME |
| host scheduler cannot enter container | host scheduler/operator log |
| Agent identity/executable failure | `jarvis-box agent doctor/smoke` and Agent HOME |
| Task/Run failure | jarvis-box status/state/log |
| provider/connector failure | jarvis-box or connector operator logs |
| Jarvis not discovered | Runtime Foundation doctor + real Agent discovery probe |

jarvis-box does not read host scheduler logs or parse customer runtime governance.

## 15. 凭据轮换、卸载与数据保留

Before removal, identify the exact Compose project and backup required volumes. Stop services with the release helper. Removing named volumes permanently deletes Agent identity/config, Jarvis Runtime Foundation, Task/Run state and workspaces; do so only with explicit customer authorization and exact targets.

Legacy native systemd/launchd remains a separate migration/recovery surface and is not removed by fresh Docker operations.
