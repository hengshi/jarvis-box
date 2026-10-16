---
name: jarvis-box
description: Help customers configure, use, and operate Jarvis Box from plain-language requests. Use for IM messages and templates, Agent or provider setup, notifications, Task recovery, licensing, and Native or Docker operations.
---

# Jarvis Box customer operations

Translate the customer's goal into the smallest verified configuration or operation. Customers describe the behavior they want; do not require them to remember environment variable names or read the entire configuration catalog.

## Resolve the target

Use the supplied host/deployment context. If multiple instances are plausible, ask which one before changing anything. Record the installed version with `jarvis-box version`, deployment mode, service user, and effective paths with `jarvis-box status --smart`. These commands do not install or upgrade anything. A `dev (unknown)` build does not establish a release version.

Docker operations belong to one explicit deployment home and its release's `scripts/deploy-production.sh`. Execute Agent/provider checks in that deployment's persistent Agent HOME, not the Host's identity. Host Agent discovery roots and container discovery roots are independent installation targets.

This pack describes the 0.2.38 contract. Verify commands and variables against the installed release's help and documentation when its version differs. Prefer that release's local bundle docs, then version-matched official customer docs. Do not apply a newer branch's variables to an older binary. The public documentation repository is [hengshi/jarvis-box](https://github.com/hengshi/jarvis-box); release access and licensing are separate.

## Find the customer's intent

Read only the relevant reference:

| Customer request | Reference |
| --- | --- |
| Change IM acceptance/progress/help text, completion title, assistant name or trigger words | [Configuration by intent](references/configuration.md), especially IM messages |
| Choose an Agent/model, connect a provider, adjust allowlists, notifications, storage or preparation | [Configuration by intent](references/configuration.md) |
| Install, upgrade, activate, back up, roll back, or change runtime tools | [Operations](references/operations.md) |
| Inspect tasks, retry delivery, recover a lost Run, clean history, understand metrics | [Tasks and monitoring](references/tasks.md) |

For an unfamiliar setting, search the matching release's `docs/configuration.md`, `config/env.jarvis-box.sample`, integration docs and CLI help using the customer's behavior terms, then the candidate variable. Confirm its actual consumer when source is available. If the release has no supported setting, say so; do not invent a variable.

## Configure and prove the result

1. Identify the owning file or supported CLI. Native uses the effective `JARVIS_ENV_FILE`; Docker separates `deployment.env`, `runtime.env`, `connector.env` and persistent Agent authentication. Read only the relevant keys; do not print secret files.
2. Explain the selected setting in the customer's terms, its current and proposed non-secret values, placeholder rules, and when it takes effect. Show a rendered example for message templates. Ask only for missing information that changes the result; do not ask the customer to choose among variable names.
3. Apply the authorized narrow edit, preserving unrelated values, comments, ownership and private permissions. Use the owning CLI when one exists. Do not create a second configuration source, source an untrusted env file as shell code, or put secrets in prompts, command arguments, reports or Git.
4. Separate saving from activation. Templates and ordinary server environment changes require a controlled restart/recreate; changing Agent routing through its CLI affects subsequent Runs. Follow the selected release's deployment procedure and active-Task preflight. A restart of the runtime executing the current managed Task needs an external operator/maintenance handoff. Never use force to bypass an active Task merely to apply a setting.
5. Re-read effective state, run the applicable doctor, and verify the requested behavior. A real IM probe or provider writeback needs an explicitly authorized target; otherwise report that the configuration is saved and the delivery check remains pending. Do not call `serve` as a dry-run validator: it starts a service.

Report the resulting behavior, where the setting was saved, whether it is active, and the evidence or remaining activation step. Keep the answer focused on the customer's goal.

## Ownership and installation

Jarvis Box owns this pack and `jarvis-box-init`, `jarvis-box-doctor`, `jarvis-box-monitor`. They are customer product skills, separate from repository development skills and Company knowledge/workflows. Install/update this pack explicitly with the pack's `install-skills.py`; it does not require a running Jarvis Box. See the official [skill installation guide](https://github.com/hengshi/jarvis-box/blob/main/docs/agent-skills.md).

Company Runtime Foundation `prepare` may update Company skills before an Agent starts. It does not update this pack or the Jarvis Box binary. Installing into a local Host Agent does not modify any other machine or a Docker Agent HOME. Start a fresh Agent session to verify discovery after installation.
