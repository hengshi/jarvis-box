# jarvis-box

jarvis-box is the formal Task/Run and Agent execution runtime. Its production image is a high-authority, digest-pinned Docker artifact. Docker socket access remains a separate host-root-equivalent opt-in.

Current public baseline: `v0.1.38 (v2026.8.2)`. Production image pin:
`JARVIS_IMAGE=<registry>/jarvis-box@sha256:<digest>`.

## New-customer path

The customer's authorized Host Runtime Agent first uses create-jarvis:

```text
请运行 git clone https://github.com/hengshi/create-jarvis create-jarvis，读取本地 create-jarvis/SKILL.md，然后帮我构建一套 Jarvis。
```

That journey publishes a customer-owned Jarvis repo, builds its Runtime Foundation and repo-local skills, then guides this release's Docker onboarding. Customers do not clone private jarvis-box source.

## Deployment

Private deployment home:

```text
<deployment-home>/
├── deployment.env
├── runtime.env
└── connector.env        # only when uvim is enabled
```

There is no Jarvis checkout mount, context file or deployment lock.

```bash
release_dir=/absolute/path/to/extracted-release
"$release_dir/scripts/deploy-production.sh" /srv/jarvis-box start
"$release_dir/scripts/deploy-production.sh" /srv/jarvis-box shell
# complete provider-native login in persistent Agent HOME
"$release_dir/scripts/deploy-production.sh" /srv/jarvis-box verify
```

## Runtime Foundation bridge

The customer Jarvis repo owns bootstrap/sync/maintenance jobs and its Scheduler Adapter. The release provides only a generic outer transport:

```bash
"$release_dir/scripts/deploy-production.sh" /srv/jarvis-box runtime-job <inner-command> [args...]
```

The helper executes the command inside the running formal container with the persistent Agent HOME. Inner jobs remain Docker-unaware. jarvis-box does not clone, pull, mount, validate or inject a Jarvis repo; the Runtime Agent discovers installed Jarvis skills through native discovery roots.

The single image contains jarvis-box, pinned uv-im-connector binary, Agent CLIs/toolchain and generic runtime skills only. Compose may run jarvis-box and connector as separate services with separate credential/state boundaries.

See the [客户部署与运维指南](CUSTOMER-OPERATIONS.md) for installation, runtime-job, backup, upgrade and recovery procedures.

`install.sh` installs a Native system service as the existing installing OS user and reuses that user's HOME/authentication. It never creates a `jarvis` service user.

## License

jarvis-box is distributed under the HENGSHI Commercial License.
