# Changelog

## 0.1.38

- Makes native installs and services run as the existing OS user, while Docker
  deployments can import host `gh`, `glab`, Codex, and Claude authentication
  into a private runtime auth directory without copying credentials into the
  image.
- Completes the production happy-path contract across GitHub, GitLab, unified
  IM plus certified WeCom/Lark/DingTalk adapters, Jira, and Feishu Project,
  including Task/Run identity, exact workspace checkout, provider writeback,
  terminal lifecycle, and lease-aware cleanup.
- Reuses the certified IM build image and external caches across adapter runs,
  while retaining a portable cold-start path for supported Docker runners.

## 0.1.37

- Fixes GitHub command workspace creation so GitHub tasks always clone their
  GitHub repository instead of falling back to a GitLab clone URL.
- Adds closed-loop happy-path coverage for GitHub, GitLab, Jira and IM across
  ingress, Task/Run, workspace semantics, Agent execution, provider writeback
  and cleanup.
- Certifies the WeCom, Lark and DingTalk adapters through one shared production
  image while preserving each provider's native ingress and reply protocol.
- Makes the DingTalk fixture compatible with Docker Compose 1.29 by injecting
  fully scoped admission allowlists without nested interpolation defaults.
- Prevents duplicate branch pipelines when an open merge request already has
  an equivalent merge-request pipeline.

## 0.1.36

- Makes jarvis-box a customer-neutral Task/Run runtime: customer Jarvis
  bootstrap, sync, discovery roots, maintenance and scheduler policy remain
  owned by the customer Runtime Foundation instead of jarvis-box configuration.
- Removes the Jarvis checkout mount, context manifest, deployment lock and
  customer-specific workspace tool assumptions from the formal Docker runtime.
- Adds the versioned Workflow Runtime Contract, with exact action grants,
  validated provider writeback and explicit customer-owned workflow chaining.
- Adds a real GitLab issue-to-Claude-to-MR Docker E2E and preserves its
  completion evidence across Agent exit and workflow action delivery.
- Hardens Task workspace ownership, process reaping and cleanup so service
  lifecycle operations do not act on unrelated or ambiguously owned work.
- Extends `doctor` to validate the writable Codex managed directories used by
  system skills and process launch, with actionable ownership repair guidance.
- Strengthens runtime-test guidance for Darwin/Linux process-table, permission
  and signaling contracts with real host-platform evidence.
- Hardens contract-workflow workspace handoff by sanitizing parent workspace
  runtime fields (`path`, `task_id`) while preserving ownership identity
  (`remote`, `project`), preventing nested workflow runs from reusing stale
  or conflicting child paths.
- Fixes release overlay baseline/version verification so Docker image and deploy
  docs can ship together and still pass strict production release gates.
- Documents the Monkey Test issue→Claude→MR real-issue smoke path in `docs/e2e.md`,
  including fixture-variable extraction and provider evidence checks for
  closed-loop behavior.
- Ensures code-review workflow does not fail when repo-local `skills/code-review/SKILL.md`
  is missing by using repo-cache fallback.
- Preserves parent task workspace context when starting contract workflows so nested
  bugfix/replay flows retain the same workspace and avoid workspace-conflict failure.
- Consolidates runtime foundations to be Runtime-Agent-owned, with jarvis-box focused on
  Task/Run, control plane, runtime-job transport, and workflow-contract validation.

## 0.1.35

- Bundles the pinned `uv-im-connector` executable in the formal jarvis-box
  image, so both Compose services use one customer-visible image digest.
- Removes the separately selected `UVIM_IMAGE` deployment input while keeping
  connector credentials, health, logs, and state isolated from the Agent.
- Adds a customer operations manual to every release bundle, covering the
  Jarvis ecosystem, first deployment, direct Docker Compose operations,
  upgrades, rollback, backup, credential rotation, diagnostics, and removal.
- Publishes the same customer documentation to the public GitHub version tag
  and fails release verification when source, bundle, or GitHub content differs;
  `latest.json` is promoted only after those checks and GitHub Release succeed.

## 0.1.34

- Separates the customer's `create-jarvis` construction journey from formal
  jarvis-box production deployment.
- Adds an immutable Company context and deployment lock to the formal Docker
  Compose runtime, with an optional isolated `uv-im-connector`.
- Ships a batteries-included, high-authority root container for both amd64 and
  arm64. Docker socket access remains an explicit opt-in capability.
- Makes production deployment and verification portable across current and
  legacy Docker Compose without host-side `jq`.
- Publishes through the internal GitLab registry with project-owned base
  images, making the release independent of Docker Hub availability.
- Retains the native installer only as an explicit migration/recovery surface.

## 0.1.33

- Uses a regular empty Compose environment file for customer Runtime startup
  and deploy checks, including Docker Compose implementations that reject
  `/dev/null` as an env file.
