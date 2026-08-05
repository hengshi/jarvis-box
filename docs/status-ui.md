# Status UI

`/status` 是可见 jarvis-box 工作的团队工作台，不是服务维护控制台。

## 用户问题

页面必须直接回答：

- 最近发生了什么？
- 哪些 Task 正在运行、已取消或需要处理？
- 当前 Task 与 Run 分别是什么状态？
- 后端允许执行三个操作中的哪一个？
- 结果、writeback 和审计证据在哪里？

## 布局

- 工作动态和全量状态筛选
- 请求人筛选
- 选中 Task 的 Task/Run/Agent 信息
- bounded progress、safe Artifact 和日志入口
- 单一 lifecycle 操作区

顶部计数来自完整 public projection；列表可分页。IM 请求人使用 provider 提供的显示名，否则显示稳定的 `<provider>:<sender_id>`。

## 三个控件

UI 只消费 response 的 `actions` policy，不在前端重算权限。

| 操作 | 控件 | 请求 |
| --- | --- | --- |
| Start | `新任务` 按钮 | `POST .../start` |
| Continue | `继续` 按钮；必要时启用 agent selector + message input | `POST .../continue` |
| Cancel | `取消` 按钮 | `POST .../cancel` |

交互规则：

- disabled reason 可用于 tooltip/错误提示，但不能通过改按钮名称创造新操作。
- `actions.continue.requires_input=true` 时必须选择 agent 并输入新消息；同 agent native resume 与跨 agent child conversation 对 UI 都是 Continue。
- `actions.continue.requires_input=false` 时禁用输入区；`strategy=recover` 自动恢复失联 Run，`strategy=writeback` 自动重试 delivery。
- active Run 的 Continue 会在服务端内部停止旧 Run 后立即继续；用户不需要先执行另一个操作。
- Cancel 终结 Task；确认文本显示 Task id，不把内部 Stop Run 暴露成并列操作。
- mutation 期间固定控件尺寸并禁用重复提交；完成后从服务端重新读取 Task。
- 所有确认文本必须显示 Task id。

## 状态词

- Task：`accepted`、`running`、`finalizing`、`needs-attention`、`completed`、`cancelled`
- Run：`starting`、`running`、`succeeded`、`failed`、`stopped`
- Monitor：`active`、`finalizing`、`needs-attention`、`completed`、`cancelled`、`recovery-required`、`ci-wait`

人类文案使用“Run 需要恢复”或“运行观察链已失联”。低 CPU 或长时间无输出不是失联证据。

## 边界

`/status` 默认不显示：

- CPU 图表、cron/scheduler 控件
- runtime env editor、cleanup/reap 控件
- 原始 JSON 状态表或任意文件系统浏览
- service logs、native AgentSession、private handle
- raw payload、prompt history 或 provider secret

这些属于 `/server` 或 local-admin CLI。

## 视觉与无障碍

- 使用中性背景、紧凑行高、小圆角和稳定对齐。
- 语义颜色只表达状态，不作为唯一识别方式。
- id、时间和日志使用等宽字体并可预测截断/换行。
- 控件有键盘焦点、tooltip、disabled state 和至少 WCAG AA 对比度。
- 长输出不得造成页面级水平滚动；支持 reduced motion。
