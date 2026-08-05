# Scheduled jobs

jarvis-box 拥有其常驻的 provider 轮询、connector 循环和 Task/Run 机制。客户 Jarvis 的 sync、maintenance 和 self-improve 任务属于该 Jarvis 的 Runtime Foundation。

内部 Runtime Job 对 Docker 无感知。Native scheduler 直接调用它们。对于正式 Docker 运行时，Jarvis 自有的 host Scheduler Adapter 调用：

```bash
scripts/deploy-production.sh <deployment-home> runtime-job <inner-command> [args...]
```

内部 job 将其 state/log 写入持久 Agent HOME。Host scheduler 记录 helper/容器启动失败。jarvis-box 不检查 host scheduler 定义或日志，也不安装客户调度。
