---
name: jarvis-box-init
description: Check and guide Jarvis Box customer onboarding for the actual Native or Docker deployment, configured Agent, providers, license and Company skill discovery.
---

# Jarvis Box onboarding

Use the installed `jarvis-box` skill's [operations reference](../jarvis-box/references/operations.md). If the pack is incomplete, use the matching release's `docs/operations.md` and `CUSTOMER-OPERATIONS.md`, then repair the explicit product-skill installation.

Resolve version, target deployment, actual service user/HOME, effective runtime/env/state/run/log/workspace paths and service identity. Native starts with `init`, `status --smart`, `doctor`, `agent current/list/doctor`, `license status`; Docker uses its release helper and selected deployment home. A running service or successful license-status command does not prove new-Run admission.

Check only configured Agents/providers and the Company's actual discovery roots. Do not require Claude credentials, GitHub/private source access or unrelated skills on all installations. Distinguish missing identity/configuration from a failed configured capability. Use the customer's authorized scope to fix routine reversible setup problems; service replacement, destructive actions and external test sends retain their own authorization boundaries.

Finish with an authorized real ingress → Task/Run → optional registered workspace → Agent → original-target delivery → terminal/cleanup observation. Agent smoke and filesystem presence prove only their own stages. Report READY only with the evidence required for the customer's deployment; name pending stages and the exact next action otherwise. Never send test messages or start production work just to fill a readiness checklist.
