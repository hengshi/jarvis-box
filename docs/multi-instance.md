# 多实例部署

本文面向同一台机器上维护多个 Jarvis Box 的客户 operator。正式多实例首选 Docker：每个 deployment home 自然隔离 Compose project、认证、状态与 workspace。Native 多实例不推荐，只适用于已批准的迁移、恢复或短维护窗口。

开始前，不要根据当前目录、`HOME`、默认端口或旧路径猜测实例。先选择目标实例，再核对它的有效路径和服务身份。

<a id="实例身份"></a>

## 一个实例由什么确定

| 事实 | Docker | Native |
| --- | --- | --- |
| runtime root | deployment home 中的持久 `data/` 集合 | `JARVIS_RUNTIME_ROOT`，默认 `$HOME/.jarvis-box` |
| runtime env | `<deployment-home>/runtime.env` | `JARVIS_ENV_FILE`，默认 `$JARVIS_RUNTIME_ROOT/envs/.env.jarvis-box` |
| Task state | `<deployment-home>/data/state` | `JARVIS_STATE_DIR` |
| Workspace root | 容器 `/workspace`，Host 为 `<deployment-home>/data/workspaces` | `JARVIS_WORKSPACE_ROOT`，默认 `$JARVIS_RUNTIME_ROOT/workspace` |
| service identity | `JARVIS_DEPLOYMENT_NAME` / Compose project | systemd unit 或 launchd label |
| HTTP entry | `JARVIS_BIND_ADDRESS` + `JARVIS_PORT` | `WEBHOOK_HOST` / `WEBHOOK_PORT` / health URL |

`jarvis-box status --smart` 显示 CLI 当前解析的 `runtime_root`、`env_file`、`run_dir`、`state_dir`、`log_dir` 和 `workspace_root`。这足以证明路径选择；Native 中它不证明 lifecycle 命令会操作同一 systemd unit 或 launchd label。

<a id="docker-多实例"></a>

## Docker：受支持的长期模式

为每个实例创建不同的 absolute deployment home、Compose project name、端口或上游路由和 Provider webhook URL：

```bash
ops=/absolute/release/scripts/deploy-production.sh
alpha_home=/srv/alpha-jarvis-box
beta_home=/srv/beta-jarvis-box

"$ops" "$alpha_home" verify
"$ops" "$beta_home" verify
```

每个 home 必须有自己的 `deployment.env`、`runtime.env`、`auth/` 和 `data/`。绝不能共享：

- `data/state`
- `data/workspaces`
- `data/agent-home`
- `data/connector-state`
- `data/dependency-cache`
- `auth/`

对一个实例的备份、升级、回滚和 Runtime Job，始终使用它的 home：

```bash
"$ops" "$alpha_home" deploy
"$ops" "$alpha_home" verify
"$ops" "$beta_home" runtime-job <customer-runtime-command>
```

同一 Provider 可以由多个实例接入，但每个实例必须独立配置 allowlist、webhook URL/secret、writeback 开关与运行身份。两个实例不能同时消费同一个 webhook URL 或同一批未分区 Provider 事件。

<a id="native-多实例不推荐"></a>

## Native：仅限受控临时场景

同一 OS 用户下必须为每个实例显式选择不同 runtime root、env file、state/log/workspace、service label 和端口。例如：

```bash
export JARVIS_RUNTIME_ROOT="$HOME/.jarvis-box-alpha"
export JARVIS_ENV_FILE="$JARVIS_RUNTIME_ROOT/envs/.env.jarvis-box"
export JARVIS_STATE_DIR="$JARVIS_RUNTIME_ROOT/state"
export JARVIS_LOG_DIR="$JARVIS_RUNTIME_ROOT/logs"
export JARVIS_WORKSPACE_ROOT="$JARVIS_RUNTIME_ROOT/workspace"
export JARVIS_LAUNCHD_LABEL='local.jarvis-box.alpha'
export WEBHOOK_SERVICE_LABEL='local.jarvis-box.alpha'
export WEBHOOK_PORT=18787

jarvis-box status --smart
jarvis-box tasks list
```

在这个 shell 里先核对 `status --smart` 输出，再读写 Task/Workspace。不要在多实例 Host 直接执行未选定 runtime 的 `tasks continue` 或 `workspace create`。

更关键的是：`JARVIS_ENV_FILE` 和 `JARVIS_RUNTIME_ROOT` 不是 Native service lifecycle selector。Linux 内置 lifecycle 操作安装时的 `jarvis-box` unit；macOS 依赖已安装 label/plist。`jarvis-box start`、`stop`、`restart` 只适合单 Native 实例，或已单独证明 service identity 的维护窗口。长期同机多实例请改为 Docker。

<a id="workspace-归属"></a>
<a id="操作检查表"></a>

## Workspace 与操作清单

Workspace 属于选定的 Jarvis Box 实例，不属于调用 shell、客户 Jarvis repo 或 Runtime Foundation。

- 在受管 Run 中，`JARVIS_TASK_ID`、`JARVIS_TASK_DIR`、`JARVIS_RUN_ID` 和 `JARVIS_WORKSPACE_ROOT` 共同确定所有权；只用 `jarvis-box workspace create` 登记 workspace。
- 在外部 shell 或 Runtime Foundation job 中，用 `jarvis-box tasks start --prompt ...` 进入受管 Task。服务返回真实 Task/Run/Workspace 路径；调用方不创建 Task 目录。
- 修改服务前，对 Docker 使用该 home 的 release helper preflight；Native 仅在已确认 service identity 后使用 lifecycle 命令。
- 每个实例保持唯一 env、state、log、workspace、dependency-cache 和 HTTP 入口。网关可分流多个公网入口，但不应共享 webhook secret。
- 升级或回滚只使用对应 release bundle 与 home；Native 必须先证明目标 service identity。
