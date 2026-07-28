# jarvis-box

jarvis-box is the formal production runtime for a Company Jarvis. It runs the
customer's approved Company snapshot and repository-local skills in an
immutable Docker Compose deployment. The container intentionally runs the
Agent as root inside the container; the Docker socket is a separate,
host-root-equivalent opt-in capability.

Current public baseline: `v0.1.34 (v2026.7.28)`. Production image pin:
`JARVIS_IMAGE=<registry>/jarvis-box@sha256:<digest>`.

## New-customer path

Customer construction is not a jarvis-box installation step. Give the
customer's Host Agent one instruction:

```text
阅读 https://github.com/hengshi/create-jarvis 并帮我构建属于我们公司的 Jarvis。
```

That journey constructs the Company Jarvis, learns each selected repository
through its commit-change eval loop, and guides the customer through workflow
skill construction. The customer does not clone jarvis-box or run its source
scripts for this work.

## Formal production runtime

After Company, repository, and workflow construction reaches `construction-ready`,
the Host Agent prepares a private deployment home containing:

```text
<deployment-home>/
├── deployment.env
├── company-context.json
├── company/                 # approved Company commit, read-only in the runtime
├── runtime.env
└── connector.env            # only when uvim is enabled
```

Use the released Compose bundle and a digest-pinned image:

```bash
scripts/deploy-production.sh /srv/acme-jarvis start
scripts/deploy-production.sh /srv/acme-jarvis shell
# complete provider-native login in the shell
scripts/deploy-production.sh /srv/acme-jarvis verify
```

`start` deliberately leaves the service in `deployment-not-ready`: health and
login remain available, while business writes return `deployment_not_ready`.
`verify` checks the exact Company context, image, repository refs, toolchain,
Agent smoke, persistence, and optional connector before writing the immutable
deployment lock and promoting the service to ready.

The base deployment does not mount the host Docker socket. Enable the separate
overlay only when the Company's approved workflow requires host Docker control.

## Legacy migration installer

The public `install.sh` wrapper is retained only for migration and recovery of
pre-0.2 native installations. It fails closed unless
`JARVIS_ENABLE_LEGACY_NATIVE=1` is explicitly set. It is not the new-customer
construction path and must not be used to create a second jarvis-box beside the
formal Compose runtime.

## Release surfaces

- [create-jarvis](https://github.com/hengshi/create-jarvis) — customer Host-Agent construction method
- jarvis-box — formal production runtime (this release)
- `https://download.hengshi.com/jarvis-box/releases/v<version>/` — signed release bundles and image metadata

## License

jarvis-box is distributed under the HENGSHI Commercial License. It is not
licensed as open source software.
