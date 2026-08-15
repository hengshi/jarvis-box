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
| `AGENT_BROWSER_EXECUTABLE_PATH` | optional dedicated automation-browser executable; on macOS the default is agent-browser's managed Chrome for Testing cache, and a missing managed browser fails closed instead of launching desktop Chrome |
| `JARVIS_CONNECTOR_PROFILE` | empty or `uvim`; sole connector lifecycle switch |
| `GITLAB_HOST` / `GITLAB_PROJECTS` | GitLab host and operator allowlist |
| `REVIEW_GITLAB_PROJECTS` | GitLab review subset |
| `JARVIS_SELF_SKILLS_IMPROVE_ENABLED` | 是否在符合条件的 GitLab MR 合并后运行 repo-local self-improve lane |
| `JARVIS_SELF_IMPROVE_GITLAB_PROJECTS` | self-improve 项目子集，必须包含在 `GITLAB_PROJECTS` 中 |
| `JARVIS_SELF_IMPROVE_TARGET_BRANCHES` | self-improve 允许的目标分支 |
| `GITHUB_REPOSITORIES` | GitHub operator allowlist |
| `REVIEW_GITHUB_REPOSITORIES` | GitHub review subset |
| `JARVIS_GITHUB_WEBHOOK_ENABLED` | GitHub webhook intake switch; defaults to `true`. Set `false` when allowlisted GitHub repositories are only workspace targets for another source provider. |
| webhook secret variables | provider signature verification |
| `JARVIS_ISSUE_POST_CHECK_ENABLED` | enable issue post-check lane after applicable workflow is available through Agent discovery |
| `JARVIS_PROVIDER_WRITEBACK_ENABLED` | global switch for Jarvis Box-owned original-subject mutation; default `true`; set `false` during installation tests to retain local results without Jarvis Box writing comments, labels, statuses, or review/follow-up updates to GitLab, GitHub, Jira, or Feishu Project. It does not sandbox the high-authority Agent's provider-native CLI identity. Upgrades from a runtime env containing the removed Workflow v1 grant variables fail closed to `false` until an operator explicitly sets this switch. |
| `JARVIS_WORK_ITEM_REPOSITORIES` | provider-neutral JSON mapping from source provider + work-item scope to zero or more allowlisted GitLab/GitHub repositories; supports simultaneous cross-provider associations and never accepts caller-supplied clone endpoints |
| `JARVIS_*_COMMAND_ALLOWED_USERS` | optional non-bot author allowlists for GitLab, GitHub, Jira, and Feishu Project command comments |
| `JARVIS_UV_IM_CONNECTOR_URL/TOKEN` | jarvis-box → connector access when profile is `uvim` |
| `JARVIS_TASK_STORE_MIN_FREE_GB` | workspace admission floor |
| `JARVIS_WORKSPACE_DEPENDENCY_CONFIGURER` | 可选的依赖准备程序；在 checkout 后、Agent 启动前调用 |
| `JARVIS_AGENT_RUNTIME_PREPARE_COMMAND` | 可选的绝对可执行路径；每次新 Task 的 Workspace/provider 和依赖准备完成后、首次 Agent 启动前调用 |
| `JARVIS_AGENT_RUNTIME_PREPARE_TIMEOUT_SECONDS` | Agent runtime preparer 超时；默认 `120` |
| `GIT_LFS_SKIP_SMUDGE` | Jarvis workspace clone/checkout 默认 `1`，LFS 按需下载；显式设为 `0` 恢复全量 materialize |

Native 默认把依赖缓存放在 `${JARVIS_RUNTIME_ROOT}/dependency-cache`。`JARVIS_DEPENDENCY_CACHE_ROOT` 可显式覆盖，但 Docker 中该路径由 Compose 固定为 `/var/cache/jarvis-box`，不要在 `runtime.env` 重定义。Jarvis Box 把这个稳定根目录和各工具的原生缓存变量注入每个 Agent；各语言继续使用自己的缓存格式、锁和校验规则。Workspace checkout 完成后，只有实际使用 Yarn 的 Workspace 才会生成未跟踪的 `.jarvis-yarnrc.yml`：能完整证明 Yarn 3+ 时加入 `nmMode: hardlinks-global`，其他 Yarn 版本只镜像原配置。C/C++、Python、Rust 等非 Yarn Workspace 不会生成 Yarn 文件或收到 Yarn Workspace policy。Agent 统一使用这个文件名，因此运行中新增 Yarn 2 Workspace 不会继承 Yarn 3-only 设置。零 Workspace Run 不注入该文件名；首个动态 Workspace 在当前 Run 保持工具原生行为，下一次 Run 再启用 Workspace-local 优化。Operator 显式设置的缓存变量始终优先。

内置依赖缓存覆盖 Go，npm/Yarn/pnpm，pip/uv/Poetry/PDM/Pipenv，Gradle/Maven，Cargo，ccache/sccache，Conan/vcpkg，NuGet、Composer 和 Bundler。Jarvis 只设置工具原生缓存变量，缓存格式、校验和锁仍由对应工具负责；客户已设置的路径优先。`CARGO_HOME` 会复用 crates registry/git 下载；Bundler 同时使用持久的 `BUNDLE_USER_CACHE` 和 `BUNDLE_PATH`，后者让新 Workspace 直接复用已安装 gems，并由 Bundler 自身按 Ruby ABI 和 native extension 平台分层；使用 node-modules linker 的 Yarn 3+ Workspace 可以在文件系统支持时用硬链接复用 global cache 内容。Jarvis 不会把整个 `node_modules` 目录或 Cargo `target/`、CMake build 等可变项目编译产物跨 Workspace 共享。客户自有构建工具同样始终收到 `JARVIS_DEPENDENCY_CACHE_ROOT`，并可通过 `JARVIS_WORKSPACE_DEPENDENCY_CONFIGURER` 在 checkout 后映射自己的原生缓存目录。

可选依赖准备程序的调用格式为 `<program> <repo> --configure-existing <workspace> [--base-branch <branch>]`。客户 Runtime Foundation 可以提供该程序；Jarvis Box 不生成、不猜测项目专用安装命令。

Agent runtime preparer 不带参数运行，必须只向 stdout 输出一个不超过 4096 bytes 的 JSON object：

```json
{"schema":"jarvis-agent-runtime-prepare/v1","status":"updated|unchanged|stale-valid","revision":"<opaque-revision>"}
```

Jarvis Box 在新 Task 的 Workspace/provider 和依赖准备完成后、Agent spawn 之前调用它，并为成功结果保存 Task receipt；普通 `Continue` 和同一 Run 内的 Agent failover 不重复调用。若首次 prepare 失败，或旧 Task 尚无成功 receipt，后续 `Continue` 必须在 Workspace/provider 准备完成后重试。非零退出、超时或非法响应会阻止 Agent 启动，但不会阻止 Workspace 创建。该程序及其 repo/ref、锁、revision 判断和 Agent discovery-root 同步规则由客户 Runtime Foundation 拥有；Jarvis Box 不读取或拉取 Company Jarvis repo。Native 应配置当前服务用户可执行的 Foundation 路径；Docker 应配置持久 Agent HOME 内的容器绝对路径。

Provider allowlists are direct operator configuration. jarvis-box does not reconcile them against a Jarvis repo. Enabling a workflow lane does not provide the workflow; the Jarvis Runtime Foundation must first install it into native Agent discovery roots.

Compose injects state/log/workspace paths, service manager and image reference. Do not redefine those deployment-owned facts in `runtime.env`.

## `connector.env`

uv-im-connector exclusively owns provider-native secrets. `UV_IM_AUTH_TOKEN` must match `JARVIS_UV_IM_CONNECTOR_TOKEN`. When profile is disabled, deployment helper may create an empty permission-restricted file for Compose compatibility.

Native 安装同样由 Jarvis Box 管理 connector，但不会把 provider secret 混入主运行环境。发布制品内置 `uv-im-connector`；installer 将其安装到 `${JARVIS_BIN_DIR}/uv-im-connector`，读取 `${JARVIS_RUNTIME_ROOT}/envs/.env.uv-im-connector`，并使用 `${JARVIS_RUNTIME_ROOT}/state/uv-im-connector`。设置 `JARVIS_CONNECTOR_PROFILE=uvim` 后，systemd/launchd companion service 与 jarvis-box 一起受安装、升级和停用流程管理。

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
