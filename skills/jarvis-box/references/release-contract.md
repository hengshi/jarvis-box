# Release compatibility and delivery boundaries

Read this reference before applying current public-repository instructions to an installed Jarvis Box, interpreting release ownership, or deciding what a webhook/writeback result proves.

## Authority order

Use the narrowest source that matches the target installation:

1. The installed binary itself: `jarvis-box version`, `jarvis-box --help`, subcommand help, `status --smart`, and `doctor`.
2. The exact release bundle used for that installation: its examples, Compose files, deployment helpers, `CUSTOMER-OPERATIONS.md`, and `docs/`.
3. The same-version private source Release and `production-image.json` when the user has authorized repository access.
4. The public `hengshi/jarvis-box` repository only as a customer-facing documentation/onboarding overlay for the matching release.

The public overlay is not the private engineering source and is not an installable artifact authority. A public `main` document can describe a newer release than the installed binary. Do not carry commands, environment variables, paths, or permission claims forward or backward across releases without checking the selected release.

The public repository's `REPOSITORY-MODEL.md` is the current ownership statement: private source builds verified artifacts, the private GitHub Release is canonical, the public S3 mirror supplies matching files and Docker archives, and the public repository supplies docs/issues. Treat implementation changes in this repository's public PR path as out of scope unless the maintainer instructions explicitly prove otherwise.

## Version-selection rules

- `latest.json` describes the currently promoted stable channel. A version may be published explicitly without becoming the default latest version.
- Docker archives, release bundles, `SHA256SUMS`, `production-image.json`, and any optional `docker_update` are separate assets from the same release. A tag, a loaded image, a binary, and product skills are separate update decisions.
- An imported Docker archive may name a local release tag; a GHCR path is digest-pinned. Follow the matching release's documented `JARVIS_IMAGE` form and do not invent a floating tag.
- Installing the current skill pack does not upgrade the binary and does not imply that the older release supports the pack's variables or commands.
- If installed version and candidate docs do not match, stop before mutation, identify the exact target release, and use that release's bundled documentation or ask for authorization to upgrade.

## Delivery evidence

Model one provider journey as independent stages:

```text
durable webhook intake
  -> normalized source/subject and Task admission
  -> Run and workspace preparation
  -> Agent execution
  -> provider-ready artifact
  -> original-subject writeback or IM reply
  -> terminal Task state
  -> eligible workspace/resource cleanup
```

- HTTP `202 Accepted` means authentication, request validation, and durable receipt succeeded. It does not include a Task/Run id and does not prove later stages.
- A repeated in-progress delivery can return `202`; a completed duplicate can return `200`; failed or outcome-unknown duplicates return `409`. Inspect provider and Task facts before starting a new operation.
- `outcome_unknown` must not be replayed automatically because the external side effect may already have occurred.
- Agent success, provider delivery, and workspace disposal are independent facts. A completed Task may still show `writeback-failed`; a successful Run remains successful when the provider subject was later found absent.
- `JARVIS_PROVIDER_WRITEBACK_ENABLED=false` suppresses Jarvis Box-owned original-subject mutation. It does not sandbox the high-authority Agent's native provider CLI identity.

## Identity and secret boundaries

- Native uses the installing OS user's existing Home and authenticated CLIs.
- Docker uses a persistent deployment-home Agent HOME and either a narrow portable Host auth import or in-container login. Never mount the whole Host HOME, Keychain, SSH agent, or complete credential store.
- `deployment.env` owns deployment identity and image configuration; `runtime.env` owns routing, allowlists, verification secrets, and connector client access; `connector.env` owns provider-native IM secrets.
- Provider execution tokens and Agent API keys do not belong in `runtime.env`.
- Licenses are machine-bound. Do not copy another machine's license state or invent a release license-server override.

Historical overlay phrases about container root/non-root identity have drifted across documentation generations. For the selected release, verify the actual Compose/deploy contract and observed runtime identity instead of choosing the most recent-sounding sentence from public `main`.

## Maintenance boundary

The public repository accepts release notes, customer docs, and the customer skill package. Product implementation, tests, image build logic, CI, and release qualification remain in the canonical private source. For a requested implementation change, preserve the exact request and route it to the maintainer/private-source workflow; do not patch implementation into the public overlay.
