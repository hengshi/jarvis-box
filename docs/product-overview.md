# 产品概览

Jarvis Box 是客户部署中负责接收工作、运行高权限 Runtime Agent、保存 Task/Run 与 workspace、把结果写回来源系统并提供状态观测的运行产品。它适合已经明确由谁授权、从哪里接收工作、结果写到哪里的场景。

## 它与其他 Jarvis 组件的分工

| 组件 | 负责什么 |
| --- | --- |
| create-jarvis | 引导 Host Runtime Agent 建设客户拥有的 Jarvis repo、repo-local skills 和工作流。 |
| Jarvis Runtime Foundation | 将 Jarvis 能力维护到目标 Agent HOME 的原生 discovery roots。 |
| Jarvis Box | 执行 Task/Run、workspace、provider loop、writeback 和状态观测。 |
| uv-im-connector | 独立连接 IM provider；它随 Jarvis Box image 交付固定版本 binary，但拥有独立的 credential 和 state boundary。 |

Jarvis Box 不是 construction installer，也不消费客户 Jarvis repo。它不会 clone、pull、mount、validate 或注入 Jarvis；Runtime Agent 按自身原生 skill discovery 使用已经安装的能力。

## 可以接收什么工作

| 来源 | 入口 | 结果去向 |
| --- | --- | --- |
| GitLab | issue、MR、note webhook | 原 issue/MR 评论、分支/MR 与 CI 查询 |
| GitHub | issue、PR、comment webhook | 原 issue/PR 写回 |
| Jira | issue webhook | 原 issue 评论与已关联代码仓库 |
| 飞书项目 | 工作项与评论 webhook | 原工作项评论与已关联代码仓库 |
| TAPD | 缺陷、需求、任务和评论 webhook | 原工作项评论与已关联代码仓库 |
| 禅道 OSS 21 | Bug、用户故事、任务、用例和评论 webhook | 原工作项评论与已关联代码仓库 |
| 云效 Projex | 保留事件 API 适配 | 原工作项评论与已关联代码仓库；平台原生自动触发尚未完成 |
| 云效 Codeup | MR 或 commit 的 Note Hook 评论指令 | 对应 MR patchset 或原 commit 评论 |
| IM | uv-im-connector event | connector message/resource API |

入口始终受 operator 配置的允许清单约束。GitHub 的签名入口缺少密钥时拒绝；飞书项目缺少配置时不启用。GitLab 和 Jira 的明文 token 入口保留公开的无密钥兼容行为；Jira 若带签名，只校验签名。具体的公开网络与认证规则见 [网络入口](network-ingress.md) 和相应接入文档。

## 上线后能看到什么

`/status` 和 `/status/terminal` 都读取同一套 Task/Run 后端。空间页按累计产出与交付质量、当前工作、已完成工作组织信息；终端工作台适合按任务归属连续阅读 Run 并在同一会话继续。两页各自保存选择、草稿和阅读位置。

GitLab 和 GitHub 的交付指标分别以当前 `glab`、`gh` 登录账号为 actor，显示账号创建以来的合并交付、人工纠正和证据可信度；不需要另配 Jarvis username，也不跨 provider 汇总。其他工作项平台与消息渠道目前不提供这些代码交付指标，它们也不是客户业务验收或货币 ROI 的事实来源。恢复历史分析请见 [Delivery Metrics 历史起点](delivery-metrics.md)。
