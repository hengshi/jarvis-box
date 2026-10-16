# Customer operations

Use the target release's `docs/operations.md`, `docs/cli.md`, `AUTHENTICATION.md` and `CUSTOMER-OPERATIONS.md` for exact procedures. Start with version, deployment mode, runtime root, env file, service identity and effective directories. Do not infer a production host or universal port/path from this skill.

## Readiness and diagnosis

Native: `jarvis-box init`, `status --smart`, `doctor`, `agent current/list/doctor`, `license status`, `tools status`. `agent smoke` performs an actual Agent call; run it when that call is within the requested validation scope. Docker: use the selected deployment helper's `compose ps`, `verify`, `shell` and in-container CLI, under its persistent runtime user.

Required tools and provider identities follow the selected configuration. Do not require Claude, GitHub authentication, or a private source repository on every deployment. Do not require unrelated presentation or skill-authoring skills. Company discovery is validated through that Company's own installer/doctor and a fresh Agent session, not a hardcoded Company path. Jarvis Box does not provide the removed `setup-claude` command.

Separate service health, configured Agent capability, license admission, provider ingress and successful delivery. A health HTTP 200 or a doctor PASS does not prove a real provider journey. Final onboarding evidence is an authorized ingress → Task/Run → optional registered workspace → Agent → original-target writeback → terminal state → eligible cleanup. Report untested stages as pending; do not manufacture delivery evidence.

## License

Since 0.2.35, unlicensed machines can still start the service and show Status but cannot create new Runs. `license status` is local/read-only and can return exit code 0 when unlicensed: inspect the verdict, reason and expiry instead of interpreting the command's exit code as admission.

- Online: `license activate` prompts without echoing the activation code. Background refresh maintains signed decisions; `license refresh` is a diagnostic network operation.
- Offline: `license request --out <request.json>`, obtain a provider-signed file through the customer's established process, then `license import <license.json>`. Request/import/status do not need outbound network access.
- Deactivation is a deliberate license mutation, never a diagnostic repair. Old offline files do not undo local deactivation; use a newly issued decision.
- Keep machine identity and license state with the deployment. Do not copy another machine's state or invent a release license-server override.

## Saving configuration and restarting

Back up the exact owning configuration privately before an authorized edit; preserve ownership and modes. List lifecycle blockers with `tasks list`, then use the selected mode's ordinary lifecycle command. Do not automatically Cancel/force Tasks to apply text, Agent or provider changes. A managed Agent must hand service replacement to an external maintenance operator when it would terminate its own Run.

Native `JARVIS_ENV_FILE`/`JARVIS_RUNTIME_ROOT` select paths but do not by themselves select a Linux systemd unit; prove service identity before lifecycle operations. Docker always uses the selected deployment home and release helper. A container restart alone does not recreate env injected by Compose; follow the release's `deploy`/recreate procedure after changing Host-side `runtime.env` or `deployment.env`.

## Upgrade and rollback

`jarvis-box update --check` inspects available releases without installing. New binaries, product skills, and Company skills are distinct update decisions. Downloading a binary release does not implicitly install product skills into every Agent root.

For an authorized upgrade, use the same deployment mode, the target release's checksummed artifacts and its documented active-Task preflight. From 0.2.32, standard Docker deployments can use their owned `update.sh`; first bootstrap it only when release metadata explicitly publishes `docker_update`. Do not guess a URL or require a Host Native binary for Docker. Native installers have no force bypass. Docker force is only for an explicit decision to abandon current Runs and requires the release's recorded strategy.

Back up the actual Native runtime or complete Docker deployment home, including persistent Agent identity, state/license, connector state and runtime hostname. Rollback must follow the old release's contract and restore its matching state backup where required; switching an image tag alone is insufficient. Connector storage changes can require restoring the corresponding connector backup. Native↔Docker migration is a separate deployment operation.

## Tools and credentials

Use `tools path/status` for inspection; `tools update/reset` mutate the managed tool overlay. Customer user tools live in the configured persistent user bin. OS packages belong to a customer-derived Docker image. Do not repair authentication by mounting a Host HOME, Keychain or SSH agent into a container. Validate provider and Agent authentication separately in the actual runtime user/HOME.
