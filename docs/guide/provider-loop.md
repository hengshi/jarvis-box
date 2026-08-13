# Provider loop

一个完整 provider loop 包含：

```text
verified ingress
  → Runtime Agent native Jarvis discovery and routing
  → Task/Run + workspace
  → high-authority Agent execution
  → customer verification gates
  → provider writeback
  → observable END
```

Webhook signature、allowlist 和 idempotency 保护入口；正式 Agent identity 执行工程动作，Jarvis Box 的 provider action owner 执行原 subject 回写；connector identity 处理 IM。三者不能被模糊成一个“低权限 token”。安装验收可用 `JARVIS_PROVIDER_WRITEBACK_ENABLED=false` 只关闭原 subject mutation，不关闭 Agent 执行和本地证据。

新增 provider 时必须说明：身份与 secret owner、事件规范化、任务幂等键、Agent capability/native discovery、writeback、retry/END、redaction 与真实 E2E。只有 inbound webhook 而无执行/写回不算 provider loop。
