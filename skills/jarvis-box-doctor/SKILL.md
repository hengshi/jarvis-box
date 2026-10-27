---
name: jarvis-box-doctor
description: Diagnose the selected Jarvis Box deployment without changing it. Check effective configuration, Agent capability, license admission, providers and Task artifacts.
---

# Jarvis Box diagnosis

Report only. Do not edit configuration, install tools, authenticate, activate a license, restart services, reconnect IM, send a test, or mutate Tasks.

Resolve the installed version and target Native/Docker instance, then read `status --smart`, `doctor`, `agent current/list/doctor`, `license status`, `tools status` and applicable `tasks verify`, `tasks show <task-id>` and `tasks events <task-id>` evidence. Execute checks in the actual runtime user/HOME; Docker Host authentication does not prove container identity. Read the installed `jarvis-box` skill's [operations](../jarvis-box/references/operations.md) and [Task diagnosis](../jarvis-box/references/tasks.md) only as needed; the matching release docs are the fallback.

Separate service health, license permission to start a Run, configured Agent, enabled providers/ChatBridge, storage admission, execution, writeback and cleanup. Follow effective paths and configured service identity/port. GitLab and GitHub are supported runtime providers regardless of where product source is hosted. Check Company Foundation health only when it exists, using its own recorded command. Do not assume one Agent, token variable, skill root or Company path.

For configured ZenTao, check the site's identity, Token-owning account, product/execution scopes, native webhook action ID and supported CLI version using `docs/integrations/zentao.md`. Treat API reads, incoming creation events, Agent execution and final comment delivery as separate evidence. Do not expose tokens or send a real probe during this read-only diagnosis.

Use PASS/FAIL/WARN/PENDING with concise evidence and a concrete next action. Unconfigured optional providers are not failures. A successful CLI exit does not override an explicit degraded/denied verdict. Redact secrets and private session handles; report limitations instead of running a real Agent or provider mutation to resolve them.
