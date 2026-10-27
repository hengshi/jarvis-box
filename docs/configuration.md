# 配置参考

## `deployment.env`

Operator-owned Compose configuration:

| Variable | Meaning |
|---|---|
| `JARVIS_DEPLOYMENT_NAME` | Compose project name |
| `JARVIS_DEPLOYMENT_HOME` | private absolute deployment path |
| `JARVIS_IMAGE` | required release image: `repository@sha256:<64 hex>`, `ghcr.io/hengshi-jarvis/jarvis-box:vX.Y.Z`, or the loaded `hengshi/jarvis-box:vX.Y.Z` from an offline bundle |
| `JARVIS_ENABLE_DOCKER_SOCKET` | `0` or `1`; `1` is host-root-equivalent |
| `JARVIS_BIND_ADDRESS` | Host publish address; default `0.0.0.0` for trusted-network access |
| `JARVIS_PORT` | default `8787` |
| `JARVIS_AUTH_IMPORT` | `auto` (default) or `skip`; controls Host identity import before start |
| `JARVIS_GITHUB_USER` / `JARVIS_GITHUB_HOST` | optional Host `gh` identity selector |
| `JARVIS_GITLAB_HOST` | optional Host `glab` identity selector |

Connector profile does not belong here. The deployment home has no Jarvis context, checkout or lock.
On hosts with more than one Docker instance, each instance must use a unique `JARVIS_DEPLOYMENT_HOME`, `JARVIS_DEPLOYMENT_NAME`, `JARVIS_PORT`, provider webhook URL, and runtime env file. See [多实例部署](multi-instance.md).

## `runtime.env`

jarvis-box routing, allowlist, webhook and connector configuration, recommended mode `0600`. Git hosting execution Tokens and Agent API keys use the deployment authentication paths. Server-owned work-item API credentials such as `ZENTAO_API_TOKEN` belong in this private canonical file and are scoped to the corresponding Provider Runs:

Native 的 canonical env 由 `JARVIS_ENV_FILE` 选择，默认位于 `$JARVIS_RUNTIME_ROOT/envs/.env.jarvis-box`。显式文件可以放在外部目录；已有外部共享父目录的 owner 和权限由操作者维护，安装器只处理 env 文件，不接管父目录。该目录必须允许服务用户创建临时文件并原子替换 env 文件，否则安装器拒绝继续；推荐使用独立的、由服务用户拥有的私有目录。

| Variable | Meaning |
|---|---|
| `JARVIS_STATE_DIR` | 本机运行状态目录；macOS Native 默认 `${JARVIS_RUNTIME_ROOT}/state`（Runtime root 默认 `~/.jarvis-box`），Linux 默认 `/var/lib/jarvis-box`；服务、授权命令和诊断共用同一解析规则 |
| `JARVIS_RUNTIME_AGENT` | selected Runtime Agent |
| `JARVIS_RUNTIME_AGENT_SCOPE_DELIVERY_METRICS` | optional Runtime Agent override for the Delivery Metrics lane; prefer `jarvis-box agent set --scope delivery-metrics <agent>` |
| `JARVIS_RUNTIME_AGENT_SCOPE_DELIVERY_METRICS_PREFIX_ARGS` | arguments inserted before generated Delivery Metrics lane arguments; use for scope-specific model/runtime options |
| `JARVIS_DELIVERY_METRICS_ENABLED` | Delivery Metrics lane 启停开关，默认 `true`；设为 `false` 后 Status 不再启动新的 `delivery-metrics` Task，操作台 Start/恢复入口拒绝该 lane，已在运行的 Task 与 Continue 收尾不受影响。操作步骤见 [Delivery Metrics 历史起点](delivery-metrics.md#启用和禁用-lane)。 |
| `JARVIS_USER_TOOL_BIN` | optional absolute directory for customer-specific executable tools; Jarvis adds it to every Agent process `PATH` before the user-local default bin |
| `AGENT_BROWSER_EXECUTABLE_PATH` | optional dedicated automation-browser executable; on macOS the default is agent-browser's managed Chrome for Testing cache, and a missing managed browser fails closed instead of launching desktop Chrome |
| `JARVIS_CONNECTOR_PROFILE` | empty or `uvim`; sole connector lifecycle switch. It no longer changes which integrations the box supports: webhook dispatch follows each provider's own configuration below, so a `uvim` box also serves GitLab/GitHub/Jira deliveries whenever those are configured |
| `GITLAB_HOST` / `GITLAB_PROJECTS` | GitLab host and operator allowlist |
| `REVIEW_GITLAB_PROJECTS` | GitLab review subset |
| `JARVIS_SELF_SKILLS_IMPROVE_ENABLED` | 是否在符合条件的 GitLab MR 或 GitHub PR 合并后运行 repo-local `self-skills-improve` lane |
| `JARVIS_SELF_IMPROVE_GITLAB_PROJECTS` | `self-skills-improve` 项目子集，必须包含在 `GITLAB_PROJECTS` 中 |
| `JARVIS_SELF_IMPROVE_TARGET_BRANCHES` | `self-skills-improve` 允许的目标分支 |
| `GITHUB_REPOSITORIES` | GitHub operator allowlist |
| `REVIEW_GITHUB_REPOSITORIES` | GitHub review subset；启用 `self-skills-improve` 时同样作为 GitHub PR 合并后的 repo-local self-improve 仓库范围，未设置时继承 `GITHUB_REPOSITORIES` |
| `GH_HOST` | GitHub 主机名，默认 `github.com`；GitHub Enterprise Server 填自己的主机名（只填主机名，不带协议和路径） |
| `JARVIS_GITHUB_WEBHOOK_ENABLED` | GitHub webhook intake switch; defaults to `true`. Set `false` when allowlisted GitHub repositories are only workspace targets for another source provider. |
| `JIRA_BASE_URL` | Jira 站点完整地址，例如 `https://jira.example.com`；工作项链接与预检回写都按它拼 |
| `JIRA_PROJECTS` | Jira project key allowlist；不在名单里的 project 事件会被忽略 |
| `JIRA_ISSUE_TYPES` | 允许进入工单预检的 issue 类型，默认 `Bug`。**这是一个收窄开关**：没列进来的类型盒子照样收到 webhook，然后静默忽略（工作台账里记 `jira_issue_type_not_allowed`）。要接 Task/Story 必须显式列出，例如 `Bug,Task`。每项可以写类型名（忽略大小写）也可以写 Jira 的类型 ID（例如 `Bug,10003`）；类型名会随触发者的语言本地化（同一个 Task 在中文账号触发时载荷里是「任务」），ID 不会，操作员要从页面上「没处理的事件」那行抄稳定的取值就抄 ID |
| `ZENTAO_BASE_URL` / `ZENTAO_API_TOKEN` | 禅道 OSS 21 站点根地址及 v1 API Token；服务端读取与评论回写共用该身份，详见[禅道接入](integrations/zentao.md) |
| `ZENTAO_ACCOUNT` | 与 API Token 对应的服务账号，官方 CLI 读取时必需 |
| `ZENTAO_CLI_COMMAND` | 禅道 Agent 读取工具，默认 `zentao`；要求 CLI 0.2.0 与 SDK 0.4.1 |
| `JARVIS_ZENTAO_WEBHOOK_SECRET` | 原生 webhook HTTP Basic 密码，用户名固定 `jarvis`；启用时必须同时配置站点、账号、API Token 和 scope |
| `ZENTAO_ALLOWED_SCOPES` | 必须显式配置的禅道范围，逗号分隔；bug/story/case 用 `product:<id>`，task 用 `execution:<id>` |
| `ZENTAO_ALLOWED_USERS` | 可选的禅道评论指令账号允许名单；匹配原始账号，不限制创建事件预检，机器人账号由 `JARVIS_COMMAND_BOT_USERNAMES` 排除 |
| webhook secret variables | provider signature verification |
| `JARVIS_ISSUE_POST_CHECK_ENABLED` | enable issue post-check lane after applicable workflow is available through Agent discovery |
| `JARVIS_PROVIDER_WRITEBACK_ENABLED` | global switch for Jarvis Box-owned original-subject mutation; default `true`; set `false` during installation tests to retain local results without Jarvis Box writing comments, labels, statuses, or review/follow-up updates to GitLab, GitHub, Jira, Feishu Project, TAPD, Yunxiao, or ZenTao. It does not sandbox the high-authority Agent's provider-native CLI identity. Upgrades from a runtime env containing the removed Workflow v1 grant variables fail closed to `false` until an operator explicitly sets this switch. |
| `JARVIS_WORK_ITEM_REPOSITORIES` | provider-neutral JSON mapping from source provider + work-item scope to zero or more allowlisted GitLab/GitHub repositories; supports simultaneous cross-provider associations and never accepts caller-supplied clone endpoints |
| `FEISHU_PROJECT_BACKEND` | 飞书项目后端，留空用默认；一般不需要改 |
| `FEISHU_PROJECT_ALLOWED_SPACES` | 飞书项目空间允许名单；留空不限 |
| `FEISHU_PROJECT_SIMPLE_NAMES` | optional JSON mapping from stable Feishu Project webhook project keys to browser URL `simple_name`; required for plugin-backed stable keys, while the Meegle CLI backend resolves and caches it through `project search` |
| `JARVIS_*_COMMAND_ALLOWED_USERS` | optional non-bot author allowlists for GitLab, GitHub, Jira, and Feishu Project command comments |
| `JARVIS_UV_IM_CONNECTOR_URL/TOKEN` | jarvis-box → connector access when profile is `uvim` |
| `JARVIS_BRAND_NAME` | 助手显示名，默认 `Jarvis`；覆盖 IM 回执与完成通知、发给 Agent 的提示词、写回 MR/PR 的评论、以及 Status 页面的助手文案。定时认知任务保留固定产品名称：JARVIS 记忆整理、JARVIS 每日复盘、JARVIS 经验积累。只改显示名，不改二进制名、镜像、systemd/launchd 单元、安装路径或任何 `JARVIS_*` 变量名。该名字会写进 Status 页面的 JavaScript 字符串和 HTML 标记，也会拼进默认 IM 回执的格式串，因此不能包含 `'` `"` `` ` `` `\` `<` `>` `&` `%` 或控制字符；含这些字符时 serve 启动失败并指明字符 |
| `JARVIS_CHAT_LAUNCH_REPLY_TEMPLATE` | Task 被接受启动时发出的 IM 回执模板，默认 `<助手名> 已开始处理。run_id: %s`；必须保留 `%s`（run id），字面量 `%` 写成 `%%` |
| `JARVIS_CHAT_QUEUED_REPLY_TEMPLATE` | Task 进入准入等待时发出的 IM 回执模板，默认 `<助手名> 已接收任务，%s。task_id: %s`；两个 `%s` 依次是等待原因和 task id，字面量 `%` 写成 `%%` |
| `JARVIS_CHAT_HELP_REPLY_TEMPLATE` | 消息未唤起助手时的提示模板，默认给出 @ 助手名与触发词开头的两种用法；两个 `%s` 依次是助手显示名和触发词（`JARVIS_MENTION_NAMES` 首项），字面量 `%` 写成 `%%`。群聊里 `@` 的对象必须与 `JARVIS_MENTION_NAMES` 一致 |
| `JARVIS_COMMAND_NOTIFY_COMPLETED_TEMPLATE` | 任务完成通知的标题，默认 `<助手名> 任务已完成`；纯文本，不做格式替换 |
| `JARVIS_TASK_STORE_MIN_FREE_GB` | workspace admission floor |
| `JARVIS_STATUS_ASSETS_DIR` | Status 页面资源目录；Native 默认读取服务工作目录下的 `status_assets`，安装后为 `${JARVIS_STATE_DIR}/app/status_assets`；Docker 默认 `/usr/local/share/jarvis-box/status_assets`。自定义时填写服务可读的绝对目录；文件修改后刷新浏览器生效，修改目录配置需要重启服务。定制及升级规则见 [Status UI](status-ui.md#页面资源与定制) |
| `JARVIS_WORKSPACE_DEPENDENCY_CONFIGURER` | 可选的 workspace 准备程序；在 checkout 后、Agent 启动前调用，可配置依赖缓存和 workspace-local Git identity |
| `JARVIS_AGENT_RUNTIME_PREPARE_COMMAND` | 可选的绝对可执行路径；每次新 Task 的 Workspace/provider 和依赖准备完成后、首次 Agent 启动前调用；其父目录也会自动加入 Agent `PATH`，使同目录安装的 runtime 工具可直接发现 |
| `JARVIS_AGENT_RUNTIME_PREPARE_TIMEOUT_SECONDS` | Agent runtime preparer 超时；默认 `120` |
| `GIT_LFS_SKIP_SMUDGE` | Jarvis workspace clone/checkout 默认 `1`，LFS 按需下载；显式设为 `0` 恢复全量 materialize |
| `JARVIS_LICENSE_URL` | **只在开发构建（`-tags jarvisdev`）里生效**：授权服务基地址，非回环地址必须是 `https`。发布构建连的是编译进二进制的常量 `https://jarvis-license.hengshi.com`，这个变量被忽略（`serve` 启动时告警）。开发构建里留空表示该实例不受本地授权控制约束 |
| `JARVIS_LICENSE_STATE_DIR` | 本机授权状态目录，默认 `${JARVIS_STATE_DIR}/license`；设备身份、已验签的服务端决定和租约都在这里，必须在持久化存储上 |
| `JARVIS_LICENSE_CHANNEL` | 报给授权服务的发布通道，默认 `stable` |
| `JARVIS_LICENSE_DEPLOYMENT` | 报给授权服务的部署形态，`native` 或 `docker`；Docker 镜像已设为 `docker`，Native 安装用默认值 |

授权配置和其余 runtime 配置一样只有 `JARVIS_ENV_FILE` 一个来源。`jarvis-box serve`、`jarvis-box status` 的授权段和 `jarvis-box license` 的子命令读的是同一份合并结果（进程环境优先，`runtime.env` 只补空位），所以写进 `runtime.env` 的 `JARVIS_LICENSE_CHANNEL` 它们立刻都看得见；不要为此在进程环境里再写一份，授权配置也不属于 `deployment.env`。授权服务地址不是配置项：它编译在二进制里（发布构建是常量），只有开发构建才读环境变量。

发布构建没有「不受本地授权控制约束」这个状态：地址是编译进去的常量，每台盒子都必须有授权（在线激活或离线授权文件）才能开 Run。不受约束只可能是开发构建（`-tags jarvisdev` + 未配 `JARVIS_LICENSE_URL`），`serve` 启动时会打印 WARN。受约束的构建还必须内置签名公钥——否则 `serve` 直接拒绝启动，而不是降级成「没有限制」：静默降级成不设防正是这个机制最怕的失败模式，所以 `jarvis-box status` 报 `configured=but-unusable` 时的正确动作是修配置，不是去找「为什么 Run 没被拦」。

授权服务是公网服务，jarvis-box 需要能出站访问 `https://jarvis-license.hengshi.com`。离线授权的机器不需要出站访问它——那条路一个请求都不发。服务端证书由**系统信任根**校验，客户端没有跳过校验的开关；私有 CA 签发时必须在运行 jarvis-box 的机器上安装该 CA（Docker 形态是容器内，见[客户派生 Docker 镜像](custom-docker-image.md)）。执行 `jarvis-box license activate` 后按提示输入激活码，输入不回显，回车提交；Docker 也支持同样的交互。自动化可使用标准输入、`activate CODE` 或 `--code CODE`，不从环境变量读取激活码。详见 [CLI 授权命令](cli.md#license)。

Status 面板的「接入配置」分区写的就是这个文件，界面上的每个配置项都对应上表里的一行。几条操作员需要知道的事实：

- 写的是**文件**，不是正在跑的进程。保存之后当前进程拿到的还是旧值，要重启盒子才生效；面板会把这一次真的变了的键列出来。
- 只开放上面这些键，键目之外的键一律拒绝：这个文件会被服务管理器 source，能改任意键等于能向受监管的进程注入任意环境变量。
- 保存前会把原文件备份成 `<env_file>.bak`，路径显示在按钮上方。保存后盒子起不来时，在本机执行 `cp <env_file>.bak <env_file> && jarvis-box start` 恢复。
- 重启前已可靠受理、尚未派发的事件在恢复后接续；已经派发但结果未知的事件先查证，不盲目重放。服务离线期间新到事件的重投由各平台决定，不能假定所有平台都会自动重投；禅道等不保证重投的平台需要接入操作者检查投递记录。**页面重启时正在运行的智能体会先被干净地中断并留下记录，但不会自动接着跑**：浏览器活不过重启，续跑要靠盒子恢复后到对应任务页面点「继续」。Native CLI 的显式 `jarvis-box update --force` 按中断收据恢复；默认升级不主动中断任务。
- 容器编排管理的盒子（`JARVIS_SERVICE_MANAGER=container`）在面板里只能保存、不能重启：Compose 拥有容器生命周期，容器内部重启不了自己，部署侧用 `scripts/deploy-production.sh <home> compose up -d --force-recreate jarvis-box`。

Delivery Metrics 默认继承 `JARVIS_RUNTIME_AGENT`。Status 服务为待分析 MR/PR 启动 `delivery-metrics` lane Task；后续 Start/Continue 都从 canonical runtime env 重新读取该 scope 的 Agent、命令、prefix args 和模型配置。操作步骤见 [Delivery Metrics 历史起点](delivery-metrics.md#选择判断-agent)。

Native 默认把依赖缓存放在 `${JARVIS_RUNTIME_ROOT}/dependency-cache`。`JARVIS_DEPENDENCY_CACHE_ROOT` 可显式覆盖，但 Docker 中该路径由 Compose 固定为 `/var/cache/jarvis-box`，不要在 `runtime.env` 重定义。Jarvis Box 把这个稳定根目录和各工具的原生缓存变量注入每个 Agent；各语言继续使用自己的缓存格式、锁和校验规则。在 Agent 启动前，Jarvis Box 为初始 Workspace 集合配置一次依赖缓存：实际使用 Yarn 的 Workspace 会生成未跟踪的 `.jarvis-yarnrc.yml`；初始集合中只有一个 Cargo Workspace 时，会通过 `CARGO_BUILD_BUILD_DIR` 把 Rust 中间构建产物放到按 repo identity 隔离的共享目录。能完整证明 Yarn 3+ 时加入 `nmMode: hardlinks-global`（含 vendored release 文件名证明：`.yarnrc.yml` 顶层 `yarnPath` 解析到 Workspace 内存在的 `yarn-<版本>.cjs` 常规文件、版本 major ≥ 3，并与 `packageManager` 声明交叉验证不冲突），其他 Yarn 版本只镜像原配置；`yarnPath` 为 `${ENV}` 插值、URL、非字符串、文件缺失或文件名无法解析时视为无法证明，保持不支持。C/C++、Python 等非 Yarn/Cargo Workspace 不会收到 Workspace policy。零/非 Yarn 初始 Task 不预置 `YARN_RC_FILENAME`，也不写空的配置归属收据；active Run 动态新增 Workspace 后不刷新 Yarn/Cargo policy。每次新 Run 准备检查完整登记集合：若 `.jarvis-yarnrc.yml` 已由 Workspace 持有，本次保留文件并跳过整个 Task 的自动 Yarn rc 策略，普通下载缓存继续生效。已登记为 Jarvis 持有的配置或归属收据损坏仍阻止启动。Operator 显式设置的缓存变量始终优先。

内置依赖缓存覆盖 XDG cache、Go，npm/Yarn/pnpm/Corepack/Bun/Deno，Playwright/Puppeteer/Cypress 浏览器缓存，Turbo/Nx task cache，pip/uv/Poetry/PDM/Pipenv/pre-commit/Ruff/mypy/Python pycache，Gradle/Maven/Coursier，Cargo，ccache/sccache，Conan/vcpkg，NuGet、Composer 和 Bundler。Jarvis 只设置工具原生缓存变量，缓存格式、校验和锁仍由对应工具负责；客户已设置的路径优先。服务启动时会创建由 Jarvis 管理的 vcpkg 默认二进制缓存目录，满足原生工具要求的目录前提；客户显式指定到其他位置的目录保持原配置。`CARGO_HOME` 会复用 crates registry/git 下载；Agent 默认设置 `CARGO_INCREMENTAL=0`，避免短生命周期 Rust Workspace 产生大量 `target/debug/incremental` 状态；运行环境里可找到 `sccache` 时，Jarvis 同时把 `RUSTC_WRAPPER` 设置为解析后的 sccache 可执行文件路径并复用 `SCCACHE_DIR`；单一 Cargo Workspace 使用 `CARGO_BUILD_BUILD_DIR` 共享 `debug/deps`、`debug/build` 等中间构建目录，但不改 `CARGO_TARGET_DIR`，因此最终 binary 仍在 Workspace 的 `target/`。当已配置可执行的 agent browser 时，Jarvis 还会把 Playwright 的 `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH` 和 Puppeteer 的 `PUPPETEER_EXECUTABLE_PATH` 指向该浏览器，并让 Puppeteer 跳过 install-time Chromium 下载；Playwright 仍按 `PLAYWRIGHT_BROWSERS_PATH` 维护自己的 revision cache，只有项目配置显式使用 `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH` 时才直接复用 agent browser。Bundler 同时使用持久的 `BUNDLE_USER_CACHE` 和 `BUNDLE_PATH`，后者让新 Workspace 直接复用已安装 gems，并由 Bundler 自身按 Ruby ABI 和 native extension 平台分层；使用 node-modules linker 的 Yarn 3+ Workspace 可以在文件系统支持时用硬链接复用 global cache 内容。Jarvis 不会把整个 `node_modules` 目录、Cargo `target/` 顶层输出、CMake build、`.next/`、`dist/` 等可变项目编译产物跨 Workspace 粗暴共享。客户自有构建工具同样始终收到 `JARVIS_DEPENDENCY_CACHE_ROOT`，并可通过 `JARVIS_WORKSPACE_DEPENDENCY_CONFIGURER` 在 checkout 后映射自己的原生缓存目录。

可选 workspace 准备程序的调用格式为 `<program> <repo> --configure-existing <workspace> [--base-branch <branch>]`。客户 Runtime Foundation 可以提供该程序；Jarvis Box 不生成、不猜测项目专用安装命令。需要在共享 Jarvis 运行时中按代码负责人设置 commit author/committer 时，也通过这个 workspace-local 入口写当前仓库的 `.git/config`，见 [代码归属与 Git 提交身份](code-attribution.md)。

以下是 Agent runtime preparer 合同。程序不带参数运行，并且必须只向 stdout 输出一个不超过 4096 bytes 的 JSON object：

```json
{"schema":"jarvis-agent-runtime-prepare/v1","status":"updated|unchanged|stale-valid","revision":"<opaque-revision>"}
```

Jarvis Box 在新 Task 的 Workspace/provider 和依赖准备完成后、Agent spawn 之前调用它，并为成功结果保存 Task-owned receipt；普通 `Continue` 会复用已成功的 receipt，不重复调用。将来若 sealed runtime-failure receipt 能力允许同一 Run 做 Agent failover，也只能复用已成功的 preparation receipt。若首次 prepare 失败，或旧 Task 尚无成功 receipt，后续 `Continue` 必须在 Workspace/provider 准备完成后重试。非零退出、超时或非法响应会阻止 Agent 启动，但不会阻止 Workspace 创建。该程序及其 repo/ref、锁、revision 判断和 Agent discovery-root 同步规则由客户 Runtime Foundation 拥有；Jarvis Box 不读取或拉取 Company Jarvis repo。Native 应配置当前服务用户可执行的 Foundation 路径；Docker 应配置持久 Agent HOME 内的容器绝对路径。

Provider allowlists are direct operator configuration. jarvis-box does not reconcile them against a Jarvis repo. Enabling a workflow lane does not provide the workflow; the Jarvis Runtime Foundation must first install it into native Agent discovery roots.

Compose injects state/log/workspace paths, service manager and image reference. Do not redefine those deployment-owned facts in `runtime.env`.
In container mode, `status`, `status --smart`, and `doctor` report container ownership and query the selected runtime's health endpoint; they do not query host launchd or systemd services.
Docker is the recommended multi-instance model. Native multi-instance maintenance is not recommended; when it is used for an approved migration or recovery window, `JARVIS_ENV_FILE` or `JARVIS_RUNTIME_ROOT` only selects runtime paths. `jarvis-box status --smart` confirms the effective runtime root, env file, and workspace root, but Native service lifecycle still requires separate systemd unit or launchd label proof.

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
