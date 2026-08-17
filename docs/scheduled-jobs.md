# Scheduled jobs

jarvis-box 拥有其常驻的 provider 轮询、connector 循环和 Task/Run 机制。客户 Jarvis 的 sync 与定时认知工作属于该 Jarvis 的 Runtime Foundation。

当前定时认知工作分类固定为：

| lane | 产品名称 | 用途 |
| --- | --- | --- |
| `memory-consolidation` | JARVIS 记忆固化 | 固化近期值得长期保留的记忆 |
| `daily-reflection` | JARVIS 日省 | 回顾当日工作并形成改进线索 |
| `cognitive-evolution` | JARVIS 心智进化 | 周期性沉淀可验证的方法与能力改进 |

内部 Runtime Job 对 Docker 无感知。Native scheduler 直接调用它们。对于正式 Docker 运行时，Jarvis 自有的 host Scheduler Adapter 调用：

```bash
scripts/deploy-production.sh <deployment-home> runtime-job <inner-command> [args...]
```

内部 job 将其 state/log 写入持久 Agent HOME。Host scheduler 记录 helper/容器启动失败。jarvis-box 不检查 host scheduler 定义或日志，也不安装客户调度。

正式 job 与 direct shell 共用 Task Start admission，一次请求交付 prompt：

```bash
jarvis-box tasks start --prompt <text> --lane memory-consolidation --reason <reason>
```

CLI 从 canonical runtime env 定位 loopback-only `/server/api/tasks/start`。服务只对上表三个 lane 推导 internal launch authority，使磁盘准入等待可在服务重启后继续恢复；provider lane、远端请求和所有会改变状态的 public `/status` mutation 在 `read-only` 下仍被拒绝。该入口不会启用 provider ingress、comment poller、provider writeback 或代码托管通知。

服务端生成 Task identity、登记 intake、创建首 Run 并启动；job 不创建 Task 目录、不读取 `task_dir`、不写 `prompt.txt`。迁移前的 `maintenance` / `self-improve` 不能用于新 Start；合并后 repo-local `self-skills-improve` 是独立能力，不属于本页分类。
