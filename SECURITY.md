# Security Policy

## Supported Versions

The public `0.1.x` line receives selected security and installer updates.

## Reporting a Vulnerability

Report security issues privately. Do not open a public GitHub issue containing exploit details, secrets, customer data, or private environment information.

Send reports to:

- hi@hengshi.com

Include:

- affected jarvis-box version
- installation surface: Ubuntu systemd, macOS launchd, container, Kubernetes, or Helm
- reproduction steps
- observed impact
- any logs after removing tokens, private URLs, local paths, and agent-native session identifiers

## Sensitive Data

Do not publish:

- GitLab access tokens, webhook secrets, IM app secrets, or runtime agent credentials
- raw `task-state.json`, `task-events.jsonl`, `run-context.json`, or provider payloads without redaction
- runtime-native session files or private resume handles
- customer source material or proprietary repository URLs
