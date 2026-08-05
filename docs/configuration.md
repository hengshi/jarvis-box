# 配置参考

## `deployment.env`

Operator-owned Compose configuration:

| Variable | Meaning |
|---|---|
| `JARVIS_DEPLOYMENT_NAME` | Compose project name |
| `JARVIS_DEPLOYMENT_HOME` | private absolute deployment path |
| `JARVIS_IMAGE` | required `repository@sha256:<64 hex>` image |
| `JARVIS_ENABLE_DOCKER_SOCKET` | `0` or `1`; `1` is host-root-equivalent |
| `JARVIS_BIND_ADDRESS` | Host publish address; default `0.0.0.0` for trusted-network access |
| `JARVIS_PORT` | default `8787` |
| `JARVIS_AUTH_IMPORT` | `auto` (default) or `skip`; controls Host identity import before start |
| `JARVIS_GITHUB_USER` / `JARVIS_GITHUB_HOST` | optional Host `gh` identity selector |
| `JARVIS_GITLAB_HOST` | optional Host `glab` identity selector |

Connector profile does not belong here. The deployment home has no Jarvis context, checkout or lock.

## `runtime.env`

jarvis-box routing, allowlist, webhook and connector configuration, recommended mode `0600`. Provider execution Tokens and Agent API keys do not belong here:

| Variable | Meaning |
|---|---|
| `JARVIS_RUNTIME_AGENT` | selected Runtime Agent |
| `JARVIS_CONNECTOR_PROFILE` | empty or `uvim`; sole connector lifecycle switch |
| `GITLAB_HOST` / `GITLAB_PROJECTS` | GitLab host and operator allowlist |
| `REVIEW_GITLAB_PROJECTS` | GitLab review subset |
| `JARVIS_SELF_SKILLS_IMPROVE_ENABLED` | 是否在符合条件的 GitLab MR 合并后运行 repo-local self-improve lane |
| `JARVIS_SELF_IMPROVE_GITLAB_PROJECTS` | self-improve 项目子集，必须包含在 `GITLAB_PROJECTS` 中 |
| `JARVIS_SELF_IMPROVE_TARGET_BRANCHES` | self-improve 允许的目标分支 |
| `GITHUB_REPOSITORIES` | GitHub operator allowlist |
| `REVIEW_GITHUB_REPOSITORIES` | GitHub review subset |
| webhook secret variables | provider signature verification |
| `JARVIS_ISSUE_POST_CHECK_ENABLED` | enable issue post-check lane after applicable workflow is available through Agent discovery |
| `JARVIS_WORKFLOW_GITLAB_ALLOWED_LABELS` | exact comma-separated GitLab labels that a Contract action may add; empty grants none |
| `JARVIS_WORKFLOW_GITLAB_ALLOWED_STATUSES` | exact comma-separated GitLab Work Item Status values that a Contract action may set; empty grants none |
| `JARVIS_WORKFLOW_ALLOWED_START_TYPES` | exact comma-separated public workflow type IDs that `workflow.start` may request; empty grants none |
| `JARVIS_UV_IM_CONNECTOR_URL/TOKEN` | jarvis-box → connector access when profile is `uvim` |
| `JARVIS_TASK_STORE_MIN_FREE_GB` | workspace admission floor |
| `JARVIS_WORKSPACE_DEPENDENCY_CONFIGURER` | 可选的依赖准备程序；在 checkout 后、Agent 启动前调用 |

Native 默认把依赖缓存放在 `${JARVIS_RUNTIME_ROOT}/dependency-cache`。`JARVIS_DEPENDENCY_CACHE_ROOT` 可显式覆盖，但 Docker 中该路径由 Compose 固定为 `/var/cache/jarvis-box`，不要在 `runtime.env` 重定义。Jarvis Box 会在未被 Operator 覆盖时向 Agent 注入 Go、npm、Yarn、pnpm、pip、uv 和 Gradle 的标准缓存目录。

内置下载缓存覆盖 Go，npm/Yarn/pnpm，pip/uv/Poetry/PDM/Pipenv，Gradle/Maven，Cargo，ccache/sccache，Conan/vcpkg，NuGet、Composer 和 Bundler。Jarvis 只设置工具原生缓存变量，缓存格式、校验和锁仍由对应工具负责；客户已设置的路径优先。`CARGO_HOME` 会复用 crates registry/git 下载，但 Jarvis 不会全局共享 Cargo `target/`、`node_modules`、CMake build 等项目编译产物。未知或内部构建系统继续使用 `JARVIS_WORKSPACE_DEPENDENCY_CONFIGURER` 在 checkout 后配置。

可选依赖准备程序的调用格式为 `<program> <repo> --configure-existing <workspace> [--base-branch <branch>]`。客户 Runtime Foundation 可以提供该程序；Jarvis Box 不生成、不猜测项目专用安装命令。

Provider allowlists are direct operator configuration. jarvis-box does not reconcile them against a Jarvis repo. Enabling a workflow lane does not provide the workflow; the Jarvis Runtime Foundation must first install it into native Agent discovery roots.

Compose injects state/log/workspace paths, service manager and image reference. Do not redefine those deployment-owned facts in `runtime.env`.

## `connector.env`

uv-im-connector exclusively owns provider-native secrets. `UV_IM_AUTH_TOKEN` must match `JARVIS_UV_IM_CONNECTOR_TOKEN`. When profile is disabled, deployment helper may create an empty permission-restricted file for Compose compatibility.

## `auth/`

`scripts/deploy-production.sh ... auth-import` snapshots only approved portable credentials from the current Host user: selected `gh`/`glab` tokens, Codex `auth.json`, Claude `.credentials.json`, or explicit headless keys. It never mounts Host HOME, Keychain, SSH agent, or a whole credential store. The directory is mode `0700`, files are `0600`, and Compose mounts it read-only at `/run/jarvis-host-auth`; the entrypoint imports Agent files into persistent `/home/jarvis` and exposes provider tokens only to the runtime process.

## Container paths

| Path | Owner/content |
|---|---|
| `/etc/jarvis-box/runtime.env` | mounted runtime config |
| `/home/jarvis` | persistent Agent identity/config, discovery roots and customer Runtime Foundation |
| `/run/jarvis-host-auth` | read-only imported Host credential snapshot |
| `/workspace` | persistent Task workspaces |
| `/var/lib/jarvis-box` | Task/Run state |
| `/var/cache/jarvis-box` | 跨 Task 复用、独立于 workspace 清理的依赖缓存 |
| `/var/log/jarvis-box` | jarvis-box logs |

No path is reserved for a mounted Jarvis repo. `JARVIS_HOME` and `JARVIS_ENTRY_SKILL` are not Docker deployment inputs.

Build/release variables and complete secret-free templates are in `deploy/production/*.example` and `config/env.jarvis-box.sample`.

## Docker 自动派生变量

`JARVIS_UID`、`JARVIS_GID` 和启用 Docker socket 时的 `JARVIS_DOCKER_GID` 都由 `scripts/deploy-production.sh` 根据当前 OS 用户与 socket 自动派生，不是客户需要手工维护的业务配置。客户只需保证当前用户可直接使用 Docker，并拥有 `$JARVIS_DEPLOYMENT_HOME`。
