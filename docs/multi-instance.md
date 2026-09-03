# 多实例部署

同一台机器可以运行多个 Jarvis Box 实例，但每个实例必须有独立的 runtime identity。正式多实例部署推荐使用 Docker；Native 多实例不推荐，只适合已批准的迁移、恢复或维护窗口。不要用当前目录、`HOME`、默认端口或历史路径推断正在操作哪个实例。

## 实例身份

一个实例至少由下列事实共同确定：

| 事实 | Docker | Native |
| --- | --- | --- |
| runtime root | deployment home 下的持久 `data/` 目录集合 | `JARVIS_RUNTIME_ROOT`，默认 `$HOME/.jarvis-box` |
| runtime env file | `<deployment-home>/runtime.env` | `JARVIS_ENV_FILE`，默认 `$JARVIS_RUNTIME_ROOT/envs/.env.jarvis-box` |
| Task state | `<deployment-home>/data/state` | `JARVIS_STATE_DIR` |
| Workspace root | 容器内 `/workspace`，宿主为 `<deployment-home>/data/workspaces` | `JARVIS_WORKSPACE_ROOT`，默认 `$JARVIS_RUNTIME_ROOT/workspace` |
| Service identity | `JARVIS_DEPLOYMENT_NAME` / Compose project | systemd unit 或 launchd label |
| HTTP endpoint | `JARVIS_BIND_ADDRESS` + `JARVIS_PORT` | `WEBHOOK_HOST` / `WEBHOOK_PORT` / health URL |
| 多实例姿态 | 推荐；release script 按 deployment home 隔离 | 不推荐；必须额外证明 OS service identity |

`jarvis-box status --smart` 会打印当前 CLI 解析到的 `runtime_root`、`env_file`、`run_dir`、`state_dir`、`log_dir` 和 `workspace_root`。该输出证明 runtime path 选择，不等于证明 Native OS service manager 已选中同一个实例。多实例主机上的 Agent 在执行 workspace、升级或恢复动作前都应先读取该输出；Native service lifecycle 还必须额外确认 systemd unit 或 launchd label。

## Docker 多实例

正式客户多实例部署优先使用 Docker。每个实例使用不同的 absolute deployment home、不同的 Compose project name 和不同的端口或反向代理入口。Docker 的隔离边界更明确：release script、Compose project、runtime env、auth、state、workspace、dependency cache 和 provider endpoint 都从 deployment home 派生。

```bash
ops=/absolute/release/scripts/deploy-production.sh

alpha_home=/srv/alpha-jarvis-box
beta_home=/srv/beta-jarvis-box

"$ops" "$alpha_home" verify
"$ops" "$beta_home" verify
```

每个 deployment home 都要有自己的 `deployment.env`、`runtime.env`、`auth/` 和 `data/`。不要让两个实例共享 `data/state`、`data/workspaces`、`data/agent-home`、`data/connector-state`、`data/dependency-cache` 或 `auth/`。备份、升级、回滚和 `runtime-job` 都只使用对应实例的 release script 与 deployment home：

```bash
"$ops" "$alpha_home" deploy
"$ops" "$alpha_home" verify

"$ops" "$beta_home" runtime-job <customer-runtime-command>
```

同一 provider 可以被不同实例接入，但必须把 allowlist、webhook URL、webhook secret、写回开关和运行身份作为每个实例的独立配置处理。两个实例不应同时消费同一个 webhook URL 或同一批未分区的 provider 事件。

## Native 多实例（不推荐）

Native installer 是已批准迁移和恢复场景的入口，不是新客户默认部署入口。需要在同一 OS 用户下维护多个 Native 实例时，每个实例必须显式设置独立的 runtime root、env file、state/log/workspace 路径、服务 label 和端口，并由 operator 证明 OS service manager 会操作目标实例。

```bash
export JARVIS_RUNTIME_ROOT="$HOME/.jarvis-box-alpha"
export JARVIS_ENV_FILE="$JARVIS_RUNTIME_ROOT/envs/.env.jarvis-box"
export JARVIS_STATE_DIR="$JARVIS_RUNTIME_ROOT/state"
export JARVIS_LOG_DIR="$JARVIS_RUNTIME_ROOT/logs"
export JARVIS_WORKSPACE_ROOT="$JARVIS_RUNTIME_ROOT/workspace"
export JARVIS_LAUNCHD_LABEL="local.jarvis-box.alpha"
export WEBHOOK_SERVICE_LABEL="local.jarvis-box.alpha"
export WEBHOOK_PORT=18787

jarvis-box status --smart
jarvis-box tasks list
```

不要在多实例主机上直接运行裸 `jarvis-box tasks continue` 或 `jarvis-box workspace create`。先在同一个 shell 中选定 `JARVIS_ENV_FILE` 或 `JARVIS_RUNTIME_ROOT`，再用 `status --smart` 确认输出匹配目标实例。

不要把 `JARVIS_ENV_FILE` 或 `JARVIS_RUNTIME_ROOT` 当作 Native lifecycle service selector。Linux systemd 的内置 lifecycle 路径操作安装时的 `jarvis-box` unit；macOS launchd 路径依赖已安装的 label/plist。`jarvis-box start`、`jarvis-box stop` 和 `jarvis-box restart` 只适合单 Native 实例，或已经由 operator 明确验证 service identity 的维护窗口。需要长期同机多实例时，改用 Docker。

## Workspace 归属

Workspace 归属于被选中的 Jarvis Box 实例，不归属于调用 shell、客户 Jarvis repo 或 Runtime Foundation。

- 在受管 Task 内，`JARVIS_TASK_ID`、`JARVIS_TASK_DIR`、`JARVIS_RUN_ID` 和 `JARVIS_WORKSPACE_ROOT` 共同确定当前 Run；`jarvis-box workspace create` 只在该所有权成立时可用。
- 在外部 shell 或 Runtime Foundation job 中，使用 `jarvis-box tasks start --prompt ...` 进入受管 Task。服务端返回真实 `task_dir`、`run_dir` 和 `workspace_root`；调用方不创建 Task 目录。
- 需要给 Agent 或客户脚本定位根目录时，读取所选实例的 `jarvis-box status --smart`，不要根据 `$HOME/.jarvis-box`、`~/.hengshi-jarvis`、当前目录或默认端口推断。

## 操作检查表

- 每个实例有唯一的 deployment home 或 `JARVIS_RUNTIME_ROOT`。
- 每个实例有唯一的 env file、state dir、log dir、workspace root 和依赖缓存根。
- 每个实例有唯一的 HTTP 入口；多个公网入口通过上游网关分流，不共享同一个 webhook secret。
- 生命周期变更前运行对应 Docker 实例的 `service preflight`，或在单 Native 实例上运行 `jarvis-box tasks list`。
- 升级和回滚只使用对应实例的 release bundle 和 deployment home；Native 多实例升级必须先证明目标 service identity。
