# Jarvis Box repository skill depth

This guide is for an Agent already executing one of the five repository skills. The four customer packages are independently installable; `jarvis-box-release-maintainer` stays in the source repository and is deliberately excluded from `install-skills.py`.

Do not load the hidden eval expectations during normal work. Use them only from an external evaluator after the task attempt is complete.

## Shared repository model

The public repository is a release overlay. Its durable authorities are:

| Fact | Authority |
| --- | --- |
| Product ownership and release flow | `REPOSITORY-MODEL.md` |
| Contribution/admission boundary | `CONTRIBUTING.md` |
| Customer-visible release history | `CHANGELOG.md` |
| Runtime behavior and lifecycle contract | `docs/execution-model.md`, `docs/storage-model.md`, `docs/task-external-resource-lifecycle.md` |
| Configuration and identity | `docs/configuration.md`, `AUTHENTICATION.md`, `docs/guide/security.md` |
| Customer operation/upgrade/license | `CUSTOMER-OPERATIONS.md`, `docs/operations.md`, `docs/cli.md` |
| Provider ingress/writeback | `docs/integrations/`, `docs/network-ingress.md` |
| Product skill packaging | `install-skills.py`, `skills/`, `.jarvis-box-managed-files` |

The public overlay does not contain the private source, tests, image-build logic, or release qualification code. It therefore cannot authorize an implementation change or prove a runtime behavior by file presence alone.

## Capability topology

| Capability | Primary skill | First proof |
| --- | --- | --- |
| Configure runtime behavior, provider routing, messages, models, tools, or caches | `jarvis-box` | Re-read effective configuration, doctor, and the narrow requested behavior |
| Install/update product skills | `jarvis-box` | `install-skills.py --check` plus fresh Agent discovery |
| Onboard or reassess end-to-end readiness | `jarvis-box-init` | Real ingress -> Task/Run -> Agent -> writeback -> terminal/cleanup evidence |
| Diagnose a deployment without mutation | `jarvis-box-doctor` | Typed status/doctor/task/provider evidence separated by stage |
| Monitor recent work and blockers | `jarvis-box-monitor` | Explicit window/population and typed Task/Run/delivery states |
| Recover/cancel a Task or resolve uncertain delivery | `jarvis-box` | Current Task policy and Continue strategy; no blind side-effect replay |
| Manage license, upgrade, rollback, or deployment mode | `jarvis-box` | Matching release contract, active-Task preflight, and post-change verification |
| Build a customer-derived Docker image | `jarvis-box` | Digest-pinned base/result and executable tool probe |
| Maintain docs, release notes, manifest, or customer skills | `jarvis-box-release-maintainer` | Diff bounded to public overlay, depth audit, installer check, PR |
| Resolve documentation/runtime version drift | `jarvis-box` | Installed version and matching release bundle outrank public `main` |
| Interpret webhook acceptance and writeback | `jarvis-box-doctor` for diagnosis; `jarvis-box-monitor` for observation | Receipt/Task/Run/provider evidence as separate stages |

## D1: implementation anchors

- `skills/jarvis-box/SKILL.md` owns the customer configuration/dispatch workflow and routes adjacent work.
- `skills/jarvis-box/references/configuration.md` maps intent to supported fields without becoming the variable registry.
- `skills/jarvis-box/references/release-contract.md` owns version authority and delivery-stage semantics.
- `skills/jarvis-box/references/operations.md` and `tasks.md` own lifecycle-safe operation and recovery guidance.
- `skills/jarvis-box-init/SKILL.md` owns readiness qualification.
- `skills/jarvis-box-doctor/SKILL.md` owns read-only diagnosis.
- `skills/jarvis-box-monitor/SKILL.md` owns read-only reporting.
- `skills/jarvis-box-release-maintainer/SKILL.md` owns the public/private mutation boundary and overlay proof.

The current authority for runtime behavior remains the target release's binary/help and bundled evidence. Public paths are anchors for what to consult, not proof that the installed binary supports it.

## D2: mechanical controls

From the repository root:

```bash
python3 -m py_compile install-skills.py
python3 skills/jarvis-box/scripts/audit_skill_depth.py --repo . --router jarvis-box
git diff --check
```

For product skill packaging, use an owned temporary `skills/` root and run install followed by `--check`. This proves tree identity and destination handling; it does not prove that an installed older binary supports newer settings. The depth auditor checks inventory, category ownership, path confinement, frontmatter basics, UI metadata presence, and direct depth/eval/audit links.

## D3: risk and evidence

| Skill | Risk | Level | Reason |
| --- | --- | --- | --- |
| `jarvis-box` | critical | L3 | Can mutate configuration, restart/recreate services, alter license/identity, or choose a recovery action |
| `jarvis-box-init` | high | L3 | Can falsely declare readiness if intake, execution, delivery, and cleanup are collapsed |
| `jarvis-box-doctor` | normal | L1 | Read-only; the main risk is misdiagnosis |
| `jarvis-box-monitor` | normal | L1 | Read-only; the main risk is misleading sampling or initiating analysis |
| `jarvis-box-release-maintainer` | high | L3 | Can erase the public/private boundary or publish undocumented customer behavior |

An L3 claim requires an isolated current-revision route/forward case with hidden expected route and forbidden adjacent routes. L1 claims remain bounded to current repository structure and documentation.

## D4: runtime-hidden evaluation

[evals.json](../evals/evals.json) holds route, adjacent-route, negative, forward, and cross-repository cases. During a normal customer task, do not open expected routes, forbidden routes, invariants, proof, or oracle source. An external evaluator copies only the skill packages and task fixture into a fresh workspace, runs the task, then compares the result with the hidden expectations.

High-risk policies requiring an evaluated route include: release selection, webhook `202` interpretation, `outcome_unknown` delivery, destructive/force upgrade, public-overlay implementation boundary, and readiness claims.

## D5: cross-repository closure

| Boundary | Local last authority | Downstream first authority | Handoff | End-to-end proof owner |
| --- | --- | --- | --- | --- |
| Public overlay -> private implementation | `CONTRIBUTING.md`, `REPOSITORY-MODEL.md` | Canonical private source repository | Preserve requirement and public-surface evidence; do not carry private code into overlay | Private source CI/release gate |
| Product skill -> installed Agent | `install-skills.py`, `skills/` | Target Agent discovery root | Four package directories; no binary or Company skill mutation | Fresh Agent discovery plus `--check` |
| Jarvis Box -> Company Runtime Foundation | `docs/architecture.md`, `docs/deployment.md` | Customer Company Jarvis Runtime Foundation | `runtime-job`/prepare contract; no Company repo copy into Jarvis Box | Customer's own foundation doctor and real Agent discovery |
| Jarvis Box -> provider subject | Provider adapter and `ProviderActionExecutor` contract | GitLab/GitHub/Jira/Feishu/IM subject | Exact immutable subject and prepared artifact | Provider-visible writeback/reply plus Task/audit evidence |

A public overlay doc edit cannot claim downstream runtime or provider behavior. A compile/install pass cannot claim a successful customer workflow.

## D6: drift and self-improve

Invalidate or narrow the affected skill when any of these change:

- `REPOSITORY-MODEL.md`, `CONTRIBUTING.md`, or `.jarvis-box-managed-files`;
- `install-skills.py` package list or destination rules;
- `CHANGELOG.md` current release/version selection;
- `docs/execution-model.md` Task/Run actions, statuses, or strategies;
- `docs/storage-model.md` and `docs/task-external-resource-lifecycle.md` ownership/cleanup rules;
- `docs/configuration.md`, `AUTHENTICATION.md`, deployment examples, or release helper actions;
- provider integration writeback or webhook receipt contracts;
- license commands and machine-binding rules;
- the skill descriptions or router table.

On a real failure, review correction, path drift, or eval regression, preserve evidence first. Route the candidate through `jarvis-self-improve-skill`; compare old and new guidance on the same trigger plus adjacent/negative cases before writing one primary home. Never edit guidance during a live task merely to justify that task's answer.
