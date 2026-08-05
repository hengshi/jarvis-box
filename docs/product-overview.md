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
| IM | uv-im-connector events | connector message/resource API |

签名和 operator 配置的 allowlist 保护入口。Runtime Foundation/Jarvis 路由发生在 Agent 内部，而非通过 jarvis-box context resolver。

新客户让 Host Runtime Agent 读取 create-jarvis 来构建 Jarvis。Docker onboarding 后，`/status` 仍是 jarvis-box 诊断视图，不是 Jarvis 的 source of truth。
