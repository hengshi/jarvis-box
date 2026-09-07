# CLI reference

## Runtime Agent

```bash
jarvis-box agent doctor
jarvis-box agent smoke
jarvis-box agent current
jarvis-box agent list
```

`doctor` 验证可执行文件/配置；`smoke` 执行真实 Agent 调用。Jarvis 发现由 Jarvis Runtime Foundation 拥有，通过 Agent 自身验证，而非 `jarvis-box jarvis validate` 命令。

## Runtime tools

```bash
jarvis-box tools path
jarvis-box tools status
jarvis-box tools update
jarvis-box tools reset
```

Jarvis 管理的官方工具通过持久化 overlay 原子更新，失败时继续使用镜像内基线。Docker 安装或升级会自动尝试一次更新。客户自装的独立用户级工具放到 `${JARVIS_USER_TOOL_BIN:-/home/jarvis/.local/bin}`；显式值必须是绝对目录，Jarvis 会把它加入每个 Agent 进程的 `PATH`，同时保留用户默认的 `.local/bin`。Docker 默认目录随 deployment home 持久化，容器重建后仍保留。需要 `apt` 管理的编译器、头文件或系统共享库通过[客户派生 Docker 镜像](custom-docker-image.md)提供。

## Server and Task/Run

```bash
jarvis-box serve
jarvis-box tasks list
jarvis-box tasks list --all --limit 50
jarvis-box tasks json --monitor-status ci-wait
jarvis-box tasks start <source-task-id> --reason "start from an existing Task"
jarvis-box tasks start --prompt "handoff to the managed runtime"
jarvis-box tasks start --prompt "send customer report" --lane custom-user-task --job-id customer-daily-report --reason scheduled-customer-daily-report
jarvis-box status
jarvis-box logs
jarvis-box doctor
jarvis-box monitor
```

Compose 配置 service mode、state/log/workspace 路径和 Agent 可执行文件。jarvis-box 不将 Jarvis root skill 注入 Run。
`jarvis-box status` 始终输出 effective `runs_dir` 和 `workspace_root`；前者由 `JARVIS_RUN_DIR`（默认 `${JARVIS_STATE_DIR}/runs`）决定，后者由 `JARVIS_WORKSPACE_ROOT`（默认 `${JARVIS_RUNTIME_ROOT}/workspace`）决定。集成方必须读取这两个 effective 值，不得根据默认目录反推 Task 或 Workspace 根。
`jarvis-box status --smart` 同时输出 `runtime_root` 和 `env_file`。同一台机器运行多个实例时，优先使用 Docker deployment home。Native 维护 shell 可以通过 `JARVIS_ENV_FILE` 或 `JARVIS_RUNTIME_ROOT` 选定 runtime path，再读取 `status --smart` 确认 `runtime_root`、`env_file` 和 `workspace_root`；这不等于选择了 systemd unit。Native lifecycle 命令只适合单实例或已明确验证 service identity 的维护窗口。完整规则见 [多实例部署](multi-instance.md)。

`jarvis-box tasks start --prompt <text>` 是外部交互式 shell 和 Runtime Foundation job 共用的原子 admission。它只能在调用进程没有 `JARVIS_TASK_ID`、`JARVIS_TASK_DIR`、`JARVIS_RUN_ID`、`JARVIS_WORKSPACE_ROOT` 时使用；CLI 从 canonical runtime env 检查 loopback service health，然后用一次 Start 请求交付 prompt。服务端分配 Task identity、登记 intake、创建首 Run 并启动 Agent；调用方不创建 Task、不读取 `task_dir`，也不写 `prompt.txt`。成功 JSON 返回真实 `task_id`、`task_dir`、`run_id`、`run_dir` 和 effective `workspace_root`。

`tasks list` 和 `tasks json` 默认只显示当前会阻断 lifecycle 操作的 Task，例如 active/running、waiting/storage-wait/duplicate-wait、ci-wait、finalizing 和 recovery-required。默认 `tasks json` 输出 operator 快速定位字段：`task_id`、`lane`、`monitor_status`、`status`、`phase`、`current_run_id`、已知 `pid`/`pgid` 和 source reference。查看历史或调试时显式使用 `--all`，并可叠加 `--status`、`--monitor-status`、`--lane` 和 `--limit`。

Delivery Metrics 历史基线由 Status 服务管理枚举和节奏，实际分析是普通 `delivery-metrics` lane Task。正在执行或等待中的 Delivery Metrics Task 会出现在默认 `tasks list` 和 `monitor` 中；历史 Task 用 `tasks list --all --lane delivery-metrics` 查看。统计结果仍通过 `/status` 或 `/status/api/value?provider=gitlab|github` 查看。恢复中断分析见 [Delivery Metrics 历史基线](delivery-metrics.md)。

在 `tasks start --prompt` 中，`--lane` 仅用于 prompt Start。默认 lane 是 `jarvis-command`；`delivery-metrics` 是普通 lane，可由 Status 服务或 operator 通过同一 Start 入口创建。`custom-user-task` 是 operator 创建或宿主定时触发的 providerless prompt job lane；lane 表示运行时行为类，`--job-id` 表示用户任务身份，例如 `customer-daily-report`。任意自定义 lane 会被拒绝，`--job-id` 只允许与 `custom-user-task` 一起使用。同一 `job_id` 已有 active/running Task 时，新的 Start 返回可解释的 conflict，不创建第二个 Task。已完成的 `custom-user-task` 不能从 detail 上直接 Start 重跑；补跑必须显式发起新的 prompt Start，避免重复发送日报、周报或客户报告。`custom-user-task` 不注入 provider writeback contract；IM、webhook 或 GitLab 投递证据由 agent task 自己在结果中记录。`read-only` 模式不会给 `custom-user-task` 本地定时任务特权。`memory-consolidation`、`daily-reflection` 和 `cognitive-evolution` 等 scheduled lane 只接受服务端 loopback internal route，不存在调用方 authority flag。

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

省略 `--base-branch` 且没有 Provider checkout ref 时，jarvis-box 从 remote symbolic `HEAD` 选择默认分支，执行非浅的单分支、no-tags clone。可用 repo-cache 会作为对象来源：Jarvis Box 先刷新 bare mirror，再通过非 local 的单分支 clone 从 cache 创建 Workspace，并把 `origin` 恢复为权威 remote；cache 不可用时才回退权威 remote。该 Workspace 不包含 tag ref、其他分支 ref 或其他分支独有历史。显式 branch/ref 使用声明的 checkout 合同。

## Release helpers

```bash
scripts/deploy-production.sh <deployment-home> start
scripts/deploy-production.sh <deployment-home> shell
scripts/deploy-production.sh <deployment-home> verify
scripts/deploy-production.sh <deployment-home> deploy
scripts/deploy-production.sh <deployment-home> --force deploy
scripts/deploy-production.sh <deployment-home> runtime-job <inner-command> [args...]
```

`deploy`、`start` 和会停止/重建服务的 `compose` 子命令会在 Docker service mutation 前执行 active-task preflight。存在未完成或需要恢复的 Task 时，命令会先退出；`--force` 只用于客户已确认放弃当前 Run 的场景，并要求设置 `JARVIS_DOCKER_UPGRADE_FORCE_STRATEGY`，脚本会先在 deployment home 下记录受影响 Run 和策略。

`runtime-job` 是 Jarvis 自有 Scheduler Adapter 的通用 Docker transport。它不识别、安装或验证内部命令。

旧版 native `start/stop/restart/setup/migrate` 命令仅保留用于批准的 v1 迁移/恢复。
