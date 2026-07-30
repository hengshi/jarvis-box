# Changelog

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
