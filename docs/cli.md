# CLI reference

## Runtime Agent

```bash
jarvis-box agent doctor
jarvis-box agent smoke
jarvis-box agent current
jarvis-box agent list
```

`doctor` 验证可执行文件/配置；`smoke` 执行真实 Agent 调用。Jarvis 发现由 Jarvis Runtime Foundation 拥有，通过 Agent 自身验证，而非 `jarvis-box jarvis validate` 命令。

## Server and Task/Run

```bash
jarvis-box serve
jarvis-box tasks list
jarvis-box tasks start <source-task-id> --reason "start from an existing Task"
jarvis-box tasks start --prompt "handoff to the managed runtime"
jarvis-box tasks start --prompt "consolidate memory" --lane memory-consolidation
jarvis-box status
jarvis-box logs
jarvis-box doctor
jarvis-box monitor
```

Compose 配置 service mode、state/log/workspace 路径和 Agent 可执行文件。jarvis-box 不将 Jarvis root skill 注入 Run。
`jarvis-box status` 始终输出 effective `runs_dir` 和 `workspace_root`；前者由 `JARVIS_RUN_DIR`（默认 `${JARVIS_STATE_DIR}/runs`）决定，后者由 `JARVIS_WORKSPACE_ROOT`（默认 `${JARVIS_RUNTIME_ROOT}/workspace`）决定。集成方必须读取这两个 effective 值，不得根据默认目录反推 Task 或 Workspace 根。

`jarvis-box tasks start --prompt <text>` 是外部交互式 shell 和 Runtime Foundation job 共用的原子 admission。它只能在调用进程没有 `JARVIS_TASK_ID`、`JARVIS_TASK_DIR`、`JARVIS_RUN_ID`、`JARVIS_WORKSPACE_ROOT` 时使用；CLI 从 canonical runtime env 检查 loopback service health，然后用一次 Start 请求交付 prompt。服务端分配 Task identity、登记 intake、创建首 Run 并启动 Agent；调用方不创建 Task、不读取 `task_dir`，也不写 `prompt.txt`。成功 JSON 返回真实 `task_id`、`task_dir`、`run_id`、`run_dir` 和 effective `workspace_root`。

Delivery Metrics 历史基线由 Status 服务管理，不是 Task 或 Run。`tasks list` 和 `monitor` 不显示它；请使用 `/status` 或 `/status/api/value?provider=gitlab|github`。查看进度和恢复中断分析见 [Delivery Metrics 历史基线](delivery-metrics.md)。

`--lane` 仅用于 prompt Start。默认 lane 是 `jarvis-command`；另外只接受 `memory-consolidation`、`daily-reflection` 和 `cognitive-evolution`。scheduled 权限由服务端 loopback internal route 与 lane allowlist 推导，不存在调用方 authority flag。

## Task workspace

```bash
jarvis-box workspace create --id <stable-id> --project <group/repo> --base-branch <branch>
jarvis-box workspace create --id <stable-id> --remote <git-url> --base-branch <branch>
```

在 active Run 内可用只读入口查看权威 registry：

```bash
jarvis-box workspace list
```

该命令输出一个 JSON object，包含当前 `task_id`、`run_id` 和按登记顺序排列的
`task-state.workspaces[]`。它校验当前 Run ownership，不扫描目录，也不从 `cwd`、
`run-context.json` 或文件系统猜测 Workspace。

该创建命令仅在 active 受管 Task 中可用。它在创建 workspace 之前原子地登记服务端分配的路径。zero-workspace Task 的第一个 Workspace 必须使用保留 id `primary`；非空 registry 的后续 Workspace 使用普通 stable id。带 `--project` 的 repository 必须能通过已配置的 `GITLAB_HOST` 解析；GitHub 或其他 provider-neutral 仓库必须显式使用 `--remote`。repository source 会在 registry mutation 前验证，成功后目录必须是真实 Git worktree；无法解析的 `--project` 不会登记或发布空目录。只有同时省略 `--project` 和 `--remote` 才表示有意创建空的非 repository Workspace。

省略 `--base-branch` 且没有 Provider checkout ref 时，jarvis-box 从 remote symbolic `HEAD` 选择默认分支，执行非浅的单分支 clone；该 Workspace 不包含其他分支 ref 或其他分支独有历史。显式 branch/ref 使用声明的 checkout 合同。

## Release helpers

```bash
scripts/deploy-production.sh <deployment-home> start
scripts/deploy-production.sh <deployment-home> shell
scripts/deploy-production.sh <deployment-home> verify
scripts/deploy-production.sh <deployment-home> deploy
scripts/deploy-production.sh <deployment-home> runtime-job <inner-command> [args...]
```

`runtime-job` 是 Jarvis 自有 Scheduler Adapter 的通用 Docker transport。它不识别、安装或验证内部命令。

旧版 native `start/stop/restart/setup/migrate` 命令仅保留用于批准的 v1 迁移/恢复。
