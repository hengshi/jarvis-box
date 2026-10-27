# 产品概览

Jarvis 生态分开三个责任：

- create-jarvis 指导 Host Runtime Agent 建设客户拥有的 Jarvis repo、Runtime Foundation 和 repo-local skills；
- Jarvis Runtime Foundation 把 Jarvis 能力维护到目标 Agent HOME 的原生 discovery roots；
- jarvis-box 提供高权限 Runtime Agent、Task/Run、workspace、provider loop、writeback 和可观测状态。

uv-im-connector 提供独立 IM provider 连接，固定版本 binary 随 jarvis-box image 交付但使用独立 credential/state boundary。

jarvis-box 不是 construction installer，也不消费 Jarvis repo。它不 clone/pull/mount/validate/inject Jarvis；Agent 使用其原生 skill discovery。

## Provider loops

| Source | Ingress | Writeback |
|---|---|---|
| GitLab | issue/MR/note webhook | comments, branch/MR, CI queries |
| GitHub | issue/PR/comment webhook | issue/PR writeback |
| Jira | issue webhook | comment and code-delivery bridge |
| 飞书项目 | 工作项与评论 webhook | 原工作项评论及代码仓库关联 |
| TAPD | 缺陷/需求/任务与评论 webhook | 原对象评论及代码仓库关联 |
| 禅道 OSS 21 | 缺陷/用户故事/任务/用例与评论 webhook | 原对象评论及代码仓库关联 |
| 云效 Projex | 保留事件 API 适配，平台原生自动触发尚未完成 | 原工作项评论及代码仓库关联；API 回放不证明自动派单 |
| 云效 Codeup | MR 或 commit 的 Note Hook 评论指令 | 对应 MR patchset 或原 commit 评论 |
| IM | uv-im-connector events | connector message/resource API |

入口由 operator 配置的允许清单约束，来源认证遵循各平台合同：GitHub 签名入口缺密钥也拒绝，飞书项目缺配置不启用；GitLab/Jira 明文 token 入口保留其公开的无密钥兼容行为，Jira 带签名时只验签。其他平台使用各自必需的接入凭据，见[网络入口](network-ingress.md)及对应接入文档。Runtime Foundation/Jarvis 路由发生在 Agent 内部，而非通过 jarvis-box context resolver。

新客户让 Host Runtime Agent 读取 create-jarvis 来构建 Jarvis。Docker onboarding 后，`/status` 在一个工作空间内按“累计产出与交付质量 → 当前工作 → 已完成工作”组织信息，右侧继续提供现有 Task/Run workbench。页面级 Provider 按实际支持的来源筛选工作项；GitLab / GitHub 以当前 `glab` / `gh` 登录账号作为各自 actor，独立展示账号创建以来的合并交付、未发现人工纠正、发现人工纠正和证据可信度，不需要额外配置 Jarvis username，也不跨 provider 聚合。其他工作项平台和消息连接当前不套用代码交付指标；这些指标也不是终端客户业务验收或货币 ROI 的 source of truth。历史起点的进度和恢复步骤见 [Delivery Metrics 历史起点](delivery-metrics.md)。
