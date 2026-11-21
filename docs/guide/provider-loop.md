# Provider loop 是什么

本页帮助客户判断一个来源是否真正接通。仅能收到 webhook 不是完整接入；一个可用的 provider loop 必须把经过验证的来源事件变成可观测、可恢复并能回到原对象的交付。

```text
已验证的 ingress
  → Runtime Agent 执行（可选的已验证 Company/repo 指导）
  → Task/Run 与 workspace
  → 高权限 Agent 执行
  → 客户验收关口
  → provider writeback
  → 可观测的终态
```

Webhook 签名、真实 source scope 和幂等保护入口。正式 Agent identity 执行工程动作；Jarvis Box 的 provider action owner 将结果写回原 subject；IM 的 connector identity 处理消息和资源。Company/repo-local 知识是可选指导，缺少它们不应阻止普通任务。

新部署可以让用户和会话允许名单保持为空。验收真实闭环时应开启 `JARVIS_PROVIDER_WRITEBACK_ENABLED=true`；只有明确做本地结果测试时才设为 `false`。关闭写回的测试不能证明原处交付。

## 接入一个来源前应明确的事项

在新增或审核 provider 时，记录并验证：

1. 谁拥有 provider 身份和 secret，谁批准它们的权限；
2. 哪些事件会被规范化为任务，以及稳定的任务幂等键；
3. Agent 如何发现经批准的能力或客户工作流；
4. 结果如何回写到原 subject，以及失败、重试和终态如何显示；
5. 哪些字段、日志和产物需要脱敏；
6. 一条真实事件是否完成 ingress、执行、writeback 和可观察终态。

只有入站 webhook、没有执行和写回，不是 provider loop。
