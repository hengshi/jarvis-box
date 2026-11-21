# 定时作业

本页面向要让客户自己的 Jarvis 或 Runtime Foundation 定时提交日报、周报、日省等任务的管理员。Jarvis Box 提供任务执行和结果投递；作业定义、提示词、时间表和收件人仍由客户 Jarvis 或 Runtime Foundation 拥有。

## 调度边界

Jarvis Box 自身管理常驻的 provider 轮询、connector 循环和 Task/Run。客户的定时作业统一使用 `custom-user-task`，并由调用方的 `job_id` 区分。

- Native scheduler 直接调用内部 Runtime Job。
- 正式 Docker 中，客户拥有的 Host Scheduler Adapter 使用以下 transport 调用环境内命令：

  ```bash
  scripts/deploy-production.sh <deployment-home> runtime-job <inner-command> [args...]
  ```

内部 job 将 state/log 写入持久 Agent HOME；Host scheduler 负责记录 helper 或容器启动失败。Jarvis Box 不安装、检查或读取客户的 host scheduler 定义和日志。

## 提交一项作业

每次调度都创建一个新 Task。调用方必须给出完整 prompt、`custom-user-task` lane 和稳定的 `job_id`：

```bash
jarvis-box tasks start --prompt '<full job prompt>' \
  --lane custom-user-task --job-id customer-daily-report \
  --reason scheduled-customer-daily-report \
  --notify-target direct:<provider-native-user-id>
```

CLI 从 canonical runtime env 定位 loopback-only `/server/api/tasks/start`。同一活动 `job_id` 的重复 Start 返回冲突，不排队补跑；完成后重新提交会创建新 Task，而不是 Continue 历史 Task。Agent 选择遵循 `custom-user-task` 的 [Runtime Agent scope](runtime-agents.md)。调用方不创建 Task 目录、不读取 `task_dir`、不写 `prompt.txt`；服务端分配 Task identity、记录 intake、创建首个 Run 并启动执行。

`--notify-target` 可选，格式为 `direct:<id>` 或 `group:<id>`。省略就不投递。通道复用 `JARVIS_NOTIFY_PROVIDER` 和已有 IM connector；提交前会验证通道能力。等待、服务重启和 Continue 保留提交时的精确目标，不从当前作业配置改投。成功 Run 的最终答复独立投递；去重与未知结果规则见 [任务结果通知](integrations/im.md#任务结果通知)。需要通知时，让 prompt 要求 Agent 生成最终答复，不要让 Agent 再自行发送同一正文。

结果投递不注入 provider writeback，也不改变 Task outcome。

## 已发布入口的兼容范围

v1.1.7 及更早版本的 `memory-consolidation`、`daily-reflection`、`cognitive-evolution` Start 仍只接受原 loopback internal route；已有 Task/Run 和周报投递回执可继续读取。旧周报目标配置只服务这些已发布调用。新作业使用本页通用接口。

`maintenance` 和 `self-improve` 仍禁止新的 Start。repo-local `self-skills-improve` 由合并 webhook 触发，不是 host 定时作业。
