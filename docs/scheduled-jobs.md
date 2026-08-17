# Scheduled jobs

jarvis-box 拥有其常驻的 provider 轮询、connector 循环和 Task/Run 机制。客户 Jarvis 的 sync、maintenance 和 self-improve 任务属于该 Jarvis 的 Runtime Foundation。

内部 Runtime Job 对 Docker 无感知。Native scheduler 直接调用它们。对于正式 Docker 运行时，Jarvis 自有的 host Scheduler Adapter 调用：

```bash
scripts/deploy-production.sh <deployment-home> runtime-job <inner-command> [args...]
```

内部 job 将其 state/log 写入持久 Agent HOME。Host scheduler 记录 helper/容器启动失败。jarvis-box 不检查 host scheduler 定义或日志，也不安装客户调度。

正式 job 必须通过专用的本地 scheduled lifecycle 创建和启动 Task：

```bash
jarvis-box tasks create <task-id> --lane maintenance --reason <reason> --local-scheduled
# 写入命令返回的 Task 目录中的 prompt.txt
jarvis-box tasks start <task-id> --reason <reason> --in-place --local-scheduled
```

`--local-scheduled` 只调用 loopback-only 的 `/server/api/scheduled-tasks/*`，并且只接受 `maintenance` 和 `self-improve`。服务会在 Task state 中持久化这项 launch authority，使磁盘准入等待可在服务重启后继续恢复；未带该 authority 的历史 Task、provider lane、远端请求和所有 `/status` mutation 在 `read-only` 下仍被拒绝。该入口不会启用 provider ingress、comment poller、provider writeback 或代码托管通知。
