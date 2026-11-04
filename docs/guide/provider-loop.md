# Provider loop

一个完整 provider loop 包含：

```text
verified ingress
  → Runtime Agent execution with optional verified Company/repo guidance
  → Task/Run + workspace
  → high-authority Agent execution
  → customer verification gates
  → provider writeback
  → observable END
```

Webhook signature、真实 source scope 和 idempotency 保护入口；正式 Agent identity 执行工程动作，Jarvis Box 的 provider action owner 执行原 subject 回写；connector identity 处理 IM。Company/repo-local 知识是可选指导，缺少它们不阻塞普通任务。新部署用户和会话允许名单留空，实际验收保持 writeback 开启；只有明确选择本地结果测试时才用 `JARVIS_PROVIDER_WRITEBACK_ENABLED=false`，该测试不证明原处交付。

新增 provider 时必须说明：身份与 secret owner、事件规范化、任务幂等键、Agent capability/native discovery、writeback、retry/END、redaction 与真实 E2E。只有 inbound webhook 而无执行/写回不算 provider loop。
