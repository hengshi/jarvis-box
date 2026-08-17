# Status UI

`/status` 是 Jarvis 数字员工的统一状态页。阅读顺序固定为：先证明累计产出与交付质量，再看当前工作与已完成工作；选中工作项后，右侧继续使用原 Task workbench 查看 Task、Run、Agent 输出、文件和生命周期操作。它不是服务维护控制台。

历史基线的恢复和排障步骤见 [Delivery Metrics 历史基线操作手册](delivery-metrics.md)。

## 页面模型

页面只投影三类现有事实，不创造 Activity、Work History 或统一 Value Case：

- Provider-native Delivery Metrics：GitLab merged MR、GitHub merged PR 及代码改动归因证据；
- Task 列表：沿用现有 work-items 内容、状态、搜索、请求人、分页与选择行为；
- Task workbench：沿用现有结构、数据和交互，只调整可用宽度与视觉层级。

Provider 是页面级筛选：`全部 / GitLab / GitHub / Jira / 飞书项目 / 即时消息`。它同时限定中央价值证据和工作项范围。`全部`只并列已配置 GitLab / GitHub 的独立证据，不相加 MR 与 PR；未配置统计仓库的代码 Provider 不渲染质量卡片，也不保留空白占位。Jira、飞书项目和即时消息当前只筛选 Task，因为它们的交付结果与人工介入语义不能套用代码交付指标。

Delivery Metrics 卡片由 Status 读模型驱动，不属于下方 Task 列表。基线分析不会创建 Task、Run 或 Workspace，也不会出现在 `jarvis-box tasks list`。

## 累计产出与交付质量

每个代码托管 Provider 独立回答三个问题：

1. **当前账号合并交付**：当前 `glab` / `gh` 登录账号作为 author 创建并已合并的 MR / PR 数量；Provider 范围内全部 merged 只作为上下文。
2. **未发现人工纠正**：完全原样合并，以及发生过 revision 但当前策略未判断为公开人类反馈促成的数量与比例。
3. **发现人工纠正**：当前策略判断公开人类反馈促成了后续 source revision 的数量与比例。

`未发现人工纠正` 与 `发现人工纠正` 使用相同的已知分母。人工 review、comment、approve、merge、rebase 或 committer/pusher 身份本身不能推出人工纠正；Runtime Agent 按判断策略检查公开人类反馈与后续修订的因果关系。

证据覆盖不是价值 KPI。它以可信度脚注显示：可判断数、unknown 数、仓库覆盖、freshness 和 warning。分母为零、身份归因不足或采集不完整时，两个代码修改指标显示 `—` 和“暂不判断”，不得显示误导性的 0 或 0%。

仓库明细、分类口径和近期 MR / PR 证据放在原生 `details / summary` 可展开区，不与头部问题争夺视觉层级。入口必须显示“展开 / 收起”和方向箭头，并为 hover、键盘 focus 与展开状态提供可见反馈。不展示货币 ROI，也不把 Provider merge 称为终端业务验收。

## 历史基线进度

首次建立基线或仍有 pending 项时，Provider 卡片显示“实时分析会话”：

- 当前阶段和 `analysis_progress.agent`；
- `analyzed / total`、待分析数量和进度条；
- 当前批次的仓库与 MR/PR number；
- 失败后的安全错误码和下次尝试时间。

打开 `/status` 会加载持久化 snapshot、queue 和 cursor，并继续未完成的分析。`scheduled`、`collecting_evidence`、`judging` 和 `persisting` 表示后台仍在工作；`retry_wait` 表示服务已安排退避重试。页面的手动刷新会同步 Provider 历史，它不执行 Task Continue。

## 工作项与 workbench

工作项沿用既有内容和行为：

- 请求人筛选、Task / Run ID 搜索和分页；
- 服务端 `status_group` 决定状态语义；
- 当前工作包含工作中、需要关注和失败项，完成与取消项进入已完成工作；
- 选中项、safe source link、Task / Run 状态、progress、Artifact 与操作 policy 均来自现有接口。

右侧 Task workbench 不重新建模：保留现有 detail shell、progress、Agent session、文件视图、Continue / Start / Cancel、workspace 清理和 SSE 更新。桌面三栏初始宽度按 `1 / 4 / 5` 分配；用户仍可通过原分栏拖拽调整宽度，双击分隔条恢复默认比例。

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

## 状态词

- Task：`accepted`、`running`、`finalizing`、`needs-attention`、`completed`、`cancelled`
- Run：`starting`、`running`、`succeeded`、`failed`、`stopped`
- Monitor：`active`、`finalizing`、`needs-attention`、`completed`、`cancelled`、`recovery-required`、`ci-wait`

人类文案使用“Run 需要恢复”或“运行观察链已失联”。低 CPU 或长时间无输出不是失联证据。

## 边界

`/status` 默认不显示 CPU 图表、cron/scheduler、runtime env editor、原始 JSON、任意文件系统浏览、service logs、native AgentSession 或 provider secret。这些属于 `/server` 或 local-admin CLI。

## 视觉与无障碍

- topbar 是页面中唯一的数字员工身份标题；左栏不重复 Jarvis 名称或页面介绍，只显示当前工作状态、Provider 和请求人筛选。
- 桌面优先采用状态/筛选、价值与工作项、Task workbench 三栏；中央栏使用唯一的连续纵向滚动，按价值、当前工作、已完成工作顺序阅读，不在工作项内部再嵌套滚动；workbench 保持在当前视口。
- 使用中性背景、紧凑行高、小圆角和稳定对齐；视觉冲击来自清楚的数字、比例和工作现场，不使用霓虹、玻璃态或科幻装饰。
- 语义颜色只表达状态，不作为唯一识别方式；id、时间和日志使用等宽字体。
- 控件有键盘焦点、disabled state 和至少 WCAG AA 对比度；支持 reduced motion。
- 手机端优先保证无页面级水平溢出、Provider 可选择、Task 可打开；不要求复刻桌面信息密度。
- Provider 文本只通过 `textContent` 写入；MR / PR 外链必须再次校验 HTTPS 和当前 Provider host，并带 `noopener noreferrer`。
