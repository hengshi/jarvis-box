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
jarvis-box status
jarvis-box logs
jarvis-box doctor
jarvis-box monitor
```

Compose 配置 service mode、state/log/workspace 路径和 Agent 可执行文件。jarvis-box 不将 Jarvis root skill 注入 Run。

## Task workspace

```bash
jarvis-box workspace create --id <stable-id> --project <group/repo> --base-branch <branch>
jarvis-box workspace create --id <stable-id> --remote <git-url> --base-branch <branch>
```

该命令仅在 active 受管 Task 中可用。它在创建 workspace 之前原子地登记服务端分配的路径。

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
