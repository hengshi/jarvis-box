# Status UI

`/status` 是 Jarvis Box 唯一的人类操作页。阅读顺序固定为：先证明累计产出与交付质量，再看当前工作与已完成工作；选中工作项后，右侧继续使用原任务工作台查看任务、运行、智能体输出、文件和生命周期操作。系统运维通过 topbar 的“系统操作”面板按需展开，不再使用独立服务页面。

历史基线的恢复和排障步骤见 [Delivery Metrics 历史基线操作手册](delivery-metrics.md)。

## 页面模型

页面只投影三类现有事实，不创造 Activity、Work History 或统一 Value Case：

- 本机运行指标：本机工作台账中的受理、今日/昨日运行、已记录运行总数、已完成运行耗时和运行趋势；
- Code Delivery Metrics：GitLab 已合并 MR、GitHub 已合并 PR 及代码改动归因证据；
- 任务列表：沿用现有工作项内容、状态、搜索、请求人、分页与选择行为；
- 任务工作台：沿用现有结构、数据和交互，只调整可用宽度与视觉层级。

来源是页面级筛选：`全部 / GitLab / GitHub / Jira / 飞书项目 / 即时消息`。它同时限定中央价值证据和工作项范围。`全部`只并列已配置 GitLab / GitHub 的独立证据，不相加 MR 与 PR；未配置统计仓库的代码来源不渲染质量卡片，也不保留空白占位。Jira、飞书项目和即时消息当前只筛选任务，因为它们的交付结果与人工介入语义不能套用代码交付指标。

Delivery Metrics 卡片由 Status 读模型驱动，不属于下方任务列表本身。基线分析通过普通 `delivery-metrics` lane 任务产出结果；当前执行或等待恢复的这些任务会出现在默认 `jarvis-box tasks list`，历史记录用 `jarvis-box tasks list --all --lane delivery-metrics` 查看；它们也会进入工作项列表，并继续使用统一任务工作台。

实现上，status 页面前端资产位于 `internal/server/status_assets/`，由 `go:embed` 打进 jarvis-box 二进制。`/status` 返回 HTML shell，`/status/assets/status.css` 和 `/status/assets/status.js` 承载样式与交互逻辑；当前不引入单独前端构建链。新皮肤应优先通过 CSS token、布局 class 和独立 asset 演进，不把大段 HTML/CSS/JS 重新嵌回 Go 字符串。

## 累计产出与交付质量

本区先展示本机任务运行活跃度，再展示代码托管来源的可审计交付质量。`历史受理记录`、`今日任务运行`、`昨日任务运行`、`本机已记录任务运行`、`已完成运行耗时合计`、`剔异常日均` 是同一组本机运行指标，必须先以 6 个指标卡集中呈现；趋势图单独位于指标卡之后。`已完成运行耗时合计` 来自本机工作台账中已完成运行记录的耗时求和，不代表机器在线时间、代码托管合并历史窗口或已清理后不可观测的其他口径。指标卡里的 `剔异常日均` 使用本机工作台账从第一条任务运行到今天的全部日期窗口，不受趋势图时间范围和 `不显示异常值` toggle 影响。

趋势图使用 `/status/api/work-items` 返回的本机工作台账日粒度运行记录。默认展示从第一条本机任务运行当天到今天的全部日期窗口；中间无运行日期显示为 0，第一条运行之前的空白日期不进入图表，也不得由后端固定 7 / 30 / 90 / 180 天滚动截断。时间范围下拉可切换为 `近 7 天`、`近 30 天` 或 `近 90 天`。图表提供 `不显示异常值` toggle，用于剔除异常日后的纵轴缩放；异常值从全量日期窗口的正数日运行量计算，优先使用 `Q3 + 1.5 * IQR` 上界，数据过于集中导致 IQR 为 0 时用 `max(中位数 * 3, 中位数 + 10)` 兜底。toggle 只改变趋势图显示，不改原始计数、不改指标口径；时间范围筛选后仍沿用全量窗口判定出的异常日期。趋势图副标题里的 `日均` 跟随当前时间范围，`剔异常日均` 始终使用全量日期窗口。

每个代码托管来源独立回答三个问题：

1. **当前账号合并交付**：当前 `glab` / `gh` 登录账号作为作者创建并已合并的 MR / PR 数量；来源范围内全部已合并数量只作为上下文。
2. **未发现人工纠正**：完全原样合并，以及发生过 revision 但当前策略未判断为公开人类反馈促成的数量与比例。
3. **发现人工纠正**：当前策略判断公开人类反馈促成了后续 source revision 的数量与比例。

`未发现人工纠正` 与 `发现人工纠正` 使用相同的已知分母。人工 review、comment、approve、merge、rebase 或 committer/pusher 身份本身不能推出人工纠正；运行智能体按判断策略检查公开人类反馈与后续修订的因果关系。

证据覆盖不是价值 KPI。它以可信度脚注显示：可判断数、unknown 数、仓库覆盖、freshness 和 warning。分母为零、身份归因不足或采集不完整时，两个代码修改指标显示 `—` 和“暂不判断”，不得显示误导性的 0 或 0%。

运行智能体 token 用量暂不在 Status 页面展示。`runtime_token_usage` 仍可能作为 API 兼容字段返回，但当前页面不把该字段作为 KPI、成本或模型用量证据渲染，避免未校验的 runtime 归因误导判断。

仓库明细与分类口径放在原生 `details / summary` 可展开区，不与头部问题争夺视觉层级；其中只展示仓库维度的统计表格，“未经人工修改”同时显示数量与同口径百分比，不列出具体 MR / PR 明细。入口必须显示“展开 / 收起”和方向箭头，并为 hover、键盘 focus 与展开状态提供可见反馈。不展示货币 ROI，也不把来源合并记录称为终端业务验收。

来源筛选不改变本机运行指标和趋势；工作台账暂不可读时显示 stale / unavailable 状态，不影响工作项列表继续加载。

## 历史基线进度

首次建立基线或仍有 pending 项时，来源卡片显示“实时分析会话”：

- 当前阶段和 `analysis_progress.lane`；
- `analyzed / total`、待分析数量和进度条；
- 当前 `delivery-metrics` 分析任务对应的仓库与 MR/PR number。

打开 `/status` 会加载持久化 snapshot 和 evidence，并从任务存储读取已完成的 `delivery-metrics-result.json`。`discovering_history` 表示正在同步来源历史，`task-running` 表示仍有 MR/PR 等待对应 lane 任务产出，`complete` 表示基线完成。页面收到 `delivery-metrics` Task 完成事件后会自动重新加载当前代码来源，读取结果并按节奏启动下一个 pending Task；每次仍最多启动一个，重复这个过程直到 `pending=0`。页面的手动刷新也会同步来源历史并启动下一个 pending 任务；继续和取消仍在对应任务详情上执行。取消只取消当前分析任务，不把该 MR/PR 记为已判断；如果仍无有效结果，后续刷新可以重新启动替代任务。

## 工作项与 workbench

工作项沿用既有内容和行为：

- 请求人筛选、任务 / 运行 ID 搜索和分页；
- 即时消息任务优先用会话展示名作为目标、发送人展示名作为请求人；展示名缺失时保持原有 provider-scoped ID / Task ID 回退，不据名称推断身份；具体渠道由独立 `im_provider` 字段保留，因此展示名不会把“即时消息：飞书 / 企业微信 / 钉钉”退化成通用“即时消息”；
- 服务端 `status_group` 决定状态语义；
- 当前工作包含工作中、需要关注和失败项，完成与取消项进入已完成工作；
- 选中项、安全来源链接、任务 / 运行状态、进度、文件证据与操作策略均来自现有接口。

右侧任务工作台不重新建模：保留现有详情框架、进度、智能体会话、文件视图、继续 / 开始 / 取消、工作区清理和实时更新。桌面三栏初始宽度按 `1 / 4 / 5` 分配；用户仍可通过原分栏拖拽调整宽度，双击分隔条恢复默认比例。

定时认知工作使用统一的人类名称：`memory-consolidation` 为“JARVIS 记忆固化”，`daily-reflection` 为“JARVIS 日省”，`cognitive-evolution` 为“JARVIS 心智进化”。迁移前已落盘任务的 `maintenance` / `self-improve` 在列表与工作台中显示“旧版定时任务”，原始 lane 仅作为审计字段保留；它们不是新建选项。repo-local `self-skills-improve` 不属于该分类。

用户自定义 recurring report 使用固定 `custom-user-task` lane。工作项列表和工作台必须同时显示 lane、`job_id`、触发 `reason`，并在同一 `job_id` 的任务上投影最近成功和最近失败时间。`jarvis-command` 表示人工 prompt；`custom-user-task` 表示 operator 创建或宿主定时触发的 providerless prompt job。完成态 `custom-user-task` 的 Start 操作保持 disabled，reason 为 `custom-user-task-rerun-requires-prompt-start`；补跑必须从显式 prompt Start 创建 fresh 任务。

## 三个控件

UI 只消费 response 的 `actions` policy，不在前端重算权限。

| 操作 | 控件 | 请求 |
| --- | --- | --- |
| Start | `新任务` 按钮 | `POST .../start` |
| Continue | `继续` 按钮；必要时启用 agent selector + message input | `POST .../continue` |
| Cancel | `取消` 按钮 | `POST .../cancel` |

交互规则：

- disabled reason 可用于 tooltip/错误提示，但不能通过改按钮名称创造新操作。
- `actions.continue.requires_input=true` 时必须选择智能体并输入新消息；同智能体原生恢复与跨智能体子会话对 UI 都是继续。
- `actions.continue.requires_input=false` 时禁用输入区；`strategy=recover` 自动恢复失联运行，`strategy=writeback` 自动重试投递。
- `strategy=writeback` 表示智能体已经生成待投递结果，只剩原工作项的投递没有完成；此时继续操作不接受新消息，也不重复运行智能体。重放位置沿用各 lane 的产物所有权：provider command 使用 `latest_run_id`，post-check、MR review 和即时消息使用任务根目录；投递目标由任务的不可变 subject 恢复。
- `writeback-failed` 任务继续出现在统一任务列表和工作台；概览直接显示规范化失败信息（category、delivery certainty、provider/http code、request id、attempts），不要求先打开服务日志。继续操作重放 `reply.md`，不显示智能体选择器或消息输入框。
- 活动运行的继续操作会在服务端内部停止旧运行后立即继续；用户不需要先执行另一个操作。
- 取消会终结任务；确认文本显示任务 id，不把内部停止运行暴露成并列操作。
- mutation 期间固定控件尺寸并禁用重复提交；完成后从服务端重新读取任务。

## 状态词

- 任务：`accepted`、`running`、`finalizing`、`needs-attention`、`completed`、`cancelled`
- 运行：`starting`、`running`、`succeeded`、`failed`、`stopped`
- Monitor：`active`、`finalizing`、`needs-attention`、`completed`、`cancelled`、`recovery-required`、`ci-wait`

人类文案使用“运行需要恢复”或“运行观察链已失联”。低 CPU 或长时间无输出不是失联证据。

## 系统操作

topbar 的“系统操作”打开 modal drawer。关闭时它不占用价值、工作项或任务工作台布局；打开后按面板独立显示 loading/error，失败不清空上一次成功数据。主导航按用户要完成的事情固定为：

| 分区 | 回答的问题 | 主要操作 |
| --- | --- | --- |
| 系统概览 | 当前是否可用、是否需要处理、下一步去哪里 | 重新检查、进入对应分区 |
| 处理问题 | 哪个诊断或消息连接有问题，是否需要 Jarvis 处理 | 重连即时消息、启动显式 operator prompt |
| 工作方式 | 以后新工作使用哪个智能体 | 修改默认智能体、按工作类型覆盖智能体 |
| 数据维护 | 哪些终态记录可以安全清理 | 预检、确认清理 |

版本、环境、路径、进程/容器资源和内部轮询统一收进系统概览底部的“技术详情”。它们用于确认部署和排障，不作为顶层任务，也不得把容器视角资源写成 Docker 宿主机全局资源。技术详情、版本浮层、tooltip、title 和 aria label 也属于 Status UI：标签、状态值、布尔值、定时提示、版本字段、收件人模式和已知来源/连接器枚举必须使用中文产品语言，不直出 `enabled`、`disabled`、`ready`、`running`、`next`、`Commit`、`Version`、`trigger_author` 等 API 原值。

“工作方式”中的“模型资源与额度”按每个有效调用入口显示四段调用链 `智能体 → 目标模型 → 计费方 / 账户 → 额度证据`，不得把额度直接归因给智能体名称。相同 `account_ref` 表示多个智能体共享同一计费账户；页面在各自调用链中重复该脱敏引用，让共享关系可以直接比较，但不把余额或 token 作为累计产出 KPI。Codex 使用 ChatGPT 登录时展示套餐和滚动额度窗口；任一支持的智能体通过 `api.deepseek.com` 路由时展示对应有效凭据的 DeepSeek 钱包余额。没有安全、公开额度接口的计费方仍显示已识别的模型和计费方，并明确标记“暂不支持自动读取”，不得把未知状态显示成可用。

Codex 的调用链按本机 `config.toml`、选中的 profile 和当前入口的 CLI overrides 解析实际 `model_provider`、模型、网关与凭据引用。不同工作类型的 prefix args 必须独立求值，不能复用默认 Codex 入口的计费账户。配置无法可靠解析时显示“Codex 路由待确认”及明确原因，不回退成 ChatGPT/OpenAI 路由，也不执行 provider 的命令型认证配置。

额度状态与智能体命令可用性是两个独立事实：命令可用不代表计费账户有余额，额度读取失败也不阻断已有任务。手动“重新检查”会重新读取额度；页面只显示脱敏账户引用、规范化余额/窗口和采集时间，不显示邮箱、token、原始上游错误或响应正文。

每个修改操作都写明何时使用、影响当前还是未来工作、是否中断、是否可恢复、成功证据和失败后的下一步。修改默认智能体与工作类型覆盖只影响保存后新启动的运行；正在运行的智能体不切换。重连即时消息只短暂重建消息接入，不取消已有任务/运行。operator prompt 创建可在 Status 工作项中跟踪的新任务/运行。终态清理不可恢复，但不处理活动任务、正在运行的智能体、服务日志或依赖缓存。

所有 mutation 使用服务端现有 owner，不做 optimistic update，完成后重新读取真实状态。`read-only` 是实例运行模式，不是人类角色：页面结构和人类权限不分叉；创建任务、修改智能体、重连即时消息和实际删除被禁用并显示原因，诊断、查看和 `tasks/clean?dry_run=1` 预检仍可执行。控件的 disabled state 必须与 API 能力一致，不能提供注定返回 403 的假入口。

该面板允许展示当前部署的主机路径和已脱敏配置，但不显示 provider credential、private resume handle、raw inbound payload、native AgentSession 或未脱敏 service/runtime log。系统操作面板与其他 `/status` 功能属于同一可信团队边界，Jarvis Box 不再根据请求是否来自 loopback 区分人类权限。更强的认证由上游网关负责。

## 视觉与无障碍

- topbar 是页面中唯一的数字员工身份标题；左栏不重复 Jarvis 名称或页面介绍，只显示当前工作状态、来源和请求人筛选。
- 系统操作使用原生 dialog 语义；支持 Escape 关闭、焦点陷获和关闭后回到触发按钮。移动端面板使用完整视口，内容自身滚动，不与主 workbench 产生双重滚动。
- 桌面优先采用状态/筛选、价值与工作项、任务工作台三栏；中央栏按价值、当前工作、已完成工作顺序阅读。工作项列表本身是独立滚动容器，避免长历史记录把价值区和右侧任务工作台一起推出视口；滚动跳转按钮作用于该工作项列表，不作用于整页。
- 使用中性背景、紧凑行高、小圆角和稳定对齐；视觉冲击来自清楚的数字、比例和工作现场，不使用霓虹、玻璃态或科幻装饰。
- 语义颜色只表达状态，不作为唯一识别方式；id、时间和日志使用等宽字体。
- 控件有键盘焦点、disabled state 和至少 WCAG AA 对比度；支持 reduced motion。
- 手机端优先保证无页面级水平溢出、来源可选择、任务可打开；不要求复刻桌面信息密度。
- 来源与仓库文本只通过 `textContent` 写入；价值区不展示具体 MR / PR 外链。
