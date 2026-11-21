# 配置参考

本文面向部署和维护 Jarvis Box 的客户管理员。它说明每个配置文件的所有权、常用变量和生效方式；首次安装按[开始使用](guide/getting-started.md)，Provider 参数按[接入工作系统与消息渠道](README.md#接入工作系统与消息渠道)中的对应文档配置。不要把 token、SSH key 或整个 Host HOME 写进这些文件。

## 配置文件与生效规则

| 文件 | 谁维护 | 用途 |
| --- | --- | --- |
| `deployment.env` | Docker operator | Compose project、image、端口、Host 身份导入和 Docker socket |
| canonical runtime env | operator | Jarvis Box、Provider、Agent、webhook 与 connector 的运行配置 |
| `connector.env` | IM connector operator | uv-im-connector 的 provider-native secret |
| `config/prompts/*.md` | workflow owner | Agent 的可编辑平台上下文与回复说明 |

Native 的 canonical runtime env 由 `JARVIS_ENV_FILE` 选择，默认是 `$JARVIS_RUNTIME_ROOT/envs/.env.jarvis-box`。Docker 的 canonical runtime env 是 `<deployment-home>/runtime.env`，容器内挂载为 `/etc/jarvis-box/runtime.env`。`jarvis-box status --smart` 会显示当前解析的 `env_file` 与有效路径；多实例机器先确认这一输出，再做任何维护动作。进程环境优先，runtime env 只补充未设置的值；不要因此再维护一份同一服务的配置。

写入 runtime env 不会改变已启动进程。除特别注明的 prompts 和后续 Start/Continue 读取项外，保存后重启服务才会生效。Status 的“接入配置”只能保存公开允许的键，并在保存前创建 `<env_file>.bak`；如果新配置导致服务无法启动，在同一实例恢复备份后再启动服务。

Docker 的 Compose-owned 路径、服务管理器和 image reference 由 Compose 注入，不能在 `runtime.env` 重定义。Native 与 Docker 都只应有一个 canonical runtime env，不要为同一服务另建 secret env。

<a id="deploymentenv"></a>

## Docker 的 `deployment.env`

`deployment.env` 是 deployment home 的私有 Compose 配置。每个 Docker 实例必须独有 deployment home、project name、端口、Provider webhook URL 和 runtime env 文件；不得共享 `auth/`、state 或 workspace。更多隔离规则见[多实例部署](multi-instance.md)。

| 变量 | 含义与限制 |
| --- | --- |
| `JARVIS_DEPLOYMENT_NAME` | Compose project name；每个实例唯一。 |
| `JARVIS_DEPLOYMENT_HOME` | 当前用户拥有的绝对 deployment home。 |
| `JARVIS_IMAGE` | 正式 image。可用任意 registry 的 `repository@sha256:<64 hex>`、正式 `ghcr.io/hengshi-jarvis/jarvis-box:vX.Y.Z`，或离线已加载的 `hengshi/jarvis-box:vX.Y.Z`。日常部署优先 digest。 |
| `JARVIS_BIND_ADDRESS` / `JARVIS_PORT` | HTTP 发布地址与端口；默认 `0.0.0.0:8787`。公开或不受信网络前应由客户网关保护。 |
| `JARVIS_AUTH_IMPORT` | `auto`（默认）导入当前 Host 的获批准可移植身份；`skip` 表示只在持久容器 Agent HOME 中登录。 |
| `JARVIS_GITHUB_USER` / `JARVIS_GITHUB_HOST` / `JARVIS_GITLAB_HOST` | 可选 Host CLI 身份选择器。 |
| `JARVIS_ENABLE_DOCKER_SOCKET` | 只能为 `0` 或 `1`；`1` 给予宿主 root 等价 Docker 能力，必须经过明确批准。 |

`deployment.env` 不保存 connector profile、Provider scope 或 Agent credential。身份导入只使用 `auth-import` 支持的窄化快照；不要挂载 Host HOME、Keychain、SSH agent 或完整 credential store。Docker 身份与两条登录路径见[部署合同](deployment.md#身份与认证)。

<a id="runtimeenv"></a>

## runtime env：运行、路径与准入

下表是常用运行参数。完整、无 secret 的模板在 `config/env.jarvis-box.sample` 与 `deploy/production/runtime.env.example`；新变量应先在匹配 release 的模板中确认。

| 变量 | 默认或约束 | 用途 |
| --- | --- | --- |
| `JARVIS_RUNTIME_ROOT` | Native `~/.jarvis-box` | Native 安装根；服务、CLI 和独立调度读取同一 canonical env。 |
| `JARVIS_STATE_DIR` | Native `${JARVIS_RUNTIME_ROOT}/state`；Docker `/var/lib/jarvis-box` | Task/Run、授权和诊断状态。 |
| `JARVIS_WORKSPACE_ROOT` | Native `${JARVIS_RUNTIME_ROOT}/workspace`；Docker `/workspace` | 受管 Workspace 根。 |
| `JARVIS_TASK_STORE_MIN_FREE_GB` | `10` | 新 Task/Workspace 的可用磁盘门槛；`0` 关闭余量保护。 |
| `JARVIS_TASK_WORKSPACE_CLEANUP_DELAY_MINUTES` | `20`，必须大于 0 | Run 释放后开始清理 Workspace 前的等待时间。 |
| `JARVIS_AUTO_UPDATE_ENABLED` | `true` | 只控制自动检查和下载；应用更新仍须确认。 |
| `JARVIS_STATUS_ASSETS_DIR` | Native state 下的 app assets；Docker image assets | 自定义 Status 静态资源的绝对可读目录。目录变化后重启；文件内容变化后刷新浏览器。 |
| `JARVIS_USER_TOOL_BIN` | 绝对路径；默认用户 `.local/bin` | 加入每个 Agent PATH 的客户可执行文件目录。系统包请用[客户派生镜像](custom-docker-image.md)。 |
| `AGENT_BROWSER_EXECUTABLE_PATH` | 可选绝对 executable | 专用自动化浏览器；macOS 缺少受管浏览器时 fail closed，不会启动桌面 Chrome。 |

`JARVIS_DEPENDENCY_CACHE_ROOT` 可覆盖 Native 默认 `${JARVIS_RUNTIME_ROOT}/dependency-cache`；Docker 固定为 `/var/cache/jarvis-box`，不要在 Docker runtime env 重定义。Jarvis 只设置工具的原生缓存变量，不共享 `node_modules`、顶层 Cargo target、CMake build、`.next` 或 `dist` 等可变编译产物。

## 终端容量

在部署实例的 canonical runtime env 中设置以下变量，重启后生效。变量接受正整数。留空使用默认值，非法值会在启动时提示具体配置项。

| 变量 | 默认 | 用途 |
| --- | ---: | --- |
| `JARVIS_STATUS_SSE_MAX_CONNECTIONS` | 320 | 所有 Status 实时订阅共用的连接上限。 |
| `JARVIS_STATUS_DIRECTORY_SSE_MAX_CONNECTIONS` | 80 | 任务目录订阅的子上限，计入总连接数。留空时自动取 80 和总上限中的较小值。 |
| `JARVIS_STATUS_CONVERSATION_MAX_READS` | 30 | HTTP 入口和正文读取器共用的并发额度，适用于当前和归档会话。留空时按显式设置的内存和运行记录数预算下调。 |
| `JARVIS_STATUS_CONVERSATION_CACHE_MIB` | 384 | 正文读取器的总内存预算，单位 MiB。留空时自动增加到能为每个并发读取预留 12 MiB。 |
| `JARVIS_STATUS_CONVERSATION_CACHE_RUNS` | 64 | 正文缓存保留的运行记录数。至少等于并发读取额度，以便保留冷读进度。留空时自动满足这一条件。 |
| `JARVIS_STATUS_TASK_VIEW_CACHE_MIB` | 64 | 完整任务视图的可淘汰缓存预算，单位 MiB。完整会话索引独立发布，缓存达到预算时仍可查找会话。 |

显式设置目录订阅数时，值须小于或等于总订阅数。显式设置正文内存预算时，至少为并发读取数的 12 倍。例如 24 个并发请求至少需要 288 MiB 的读取预算。批量打开冷会话较多时，同时考虑保留的运行记录数。可参考[终端性能与硬件选型](terminal-performance.md)选择起始额度，再按实际负载验证。

## Provider、webhook 与写回

先在对应集成文档决定所需平台及 scope，再填写下面的类别。空 allowlist 不自动表示所有项目；项目、仓库、禅道范围和类似 source scope 必须是实际授权范围。

| 范围 | 主要变量 | 注意事项 |
| --- | --- | --- |
| GitLab | `GITLAB_HOST`、`GITLAB_PROJECTS`、`REVIEW_GITLAB_PROJECTS`、`GITLAB_WEBHOOK_SECRET` | review scope 必须是 project allowlist 的子集。 |
| GitHub | `GH_HOST`、`GITHUB_REPOSITORIES`、`REVIEW_GITHUB_REPOSITORIES`、`GITHUB_WEBHOOK_SECRET`、`JARVIS_GITHUB_WEBHOOK_ENABLED` | `GH_HOST` 只填 hostname。GitHub 仅作为其他来源的 workspace target 时可将 webhook 开关设为 `false`。 |
| Jira | `JIRA_BASE_URL`、`JIRA_PROJECTS`、`JIRA_ISSUE_TYPES`、`JIRA_WEBHOOK_SECRET` | issue type 是收窄开关；名称可能本地化，稳定 ID 更适合跨语言配置。 |
| 禅道 | `ZENTAO_BASE_URL`、`ZENTAO_ACCOUNT`、`ZENTAO_PASSWORD`、`ZENTAO_ALLOWED_SCOPES`、`JARVIS_ZENTAO_WEBHOOK_SECRET` | 范围必须显式填写；密码是服务端配置，不传给 Agent。 |
| 飞书项目 | `FEISHU_PROJECT_*` | 选择 backend 后按[飞书项目接入](integrations/feishu-project.md)配置。 |
| TAPD / 云效 | `TAPD_*`、`YUNXIAO_*` | 按相应接入文档填写 token、scope 和 webhook secret。 |
| IM | `JARVIS_CONNECTOR_PROFILE` 与 `JARVIS_UV_IM_CONNECTOR_URL/TOKEN` | 空 profile 关闭 IM；`uvim` 管理本实例 connector；`uvim-external` 连接共享 hub，必须有 URL 和本实例独有的非空调用方 token。 |

`JARVIS_ISSUE_POST_CHECK_ENABLED` 控制 issue post-check lane；新安装样例为 `true`，省略时保留既有 `false` 默认。`JARVIS_PROVIDER_WRITEBACK_ENABLED` 默认 `true`，是 Jarvis Box 对原工作项的评论、标签、状态、review/follow-up 写回总开关；它不能限制高权限 Agent 自己使用原生 CLI。`JARVIS_*_COMMAND_ALLOWED_USERS` 是可选的非 bot 指令作者 allowlist；留空时，在 source scope 内的非 bot 作者可使用指令。

`JARVIS_WORK_ITEM_REPOSITORIES` 是 provider-neutral 的 JSON 映射，用于将工作项连接到已 allowlist 的 GitLab/GitHub 仓库。它不接受由调用者提供的 clone endpoint。具体 schema 以相关集成合同为准。

### 其他已发布的接入与通知键

下表保留不应由 central reference 猜测 schema 的公开键。填写值前，先查对应平台文档和匹配 release 的 env sample。

| 键 | 用途或约束 |
| --- | --- |
| `JARVIS_SELF_SKILLS_IMPROVE_ENABLED`、`JARVIS_SELF_IMPROVE_GITLAB_PROJECTS`、`JARVIS_SELF_IMPROVE_TARGET_BRANCHES` | GitLab/GitHub PR/MR 合并后的 repo-local self-improve lane；项目范围必须处于已接入范围内。 |
| `JARVIS_GITLAB_COMMAND_ALLOWED_USERS`、`JARVIS_GITHUB_COMMAND_ALLOWED_USERS`、`JARVIS_JIRA_COMMAND_ALLOWED_USERS`、`JARVIS_FEISHU_PROJECT_COMMAND_ALLOWED_USERS` | 对应来源的非 bot 指令作者 allowlist。 |
| `ZENTAO_CLI_COMMAND` | Agent 使用的禅道 CLI，默认 `zentao`；兼容版本要求以[禅道接入](integrations/zentao.md)为准。 |
| `ZENTAO_ALLOWED_USERS` | 可选禅道评论指令作者名单，不限制创建事件预检。 |
| `FEISHU_PROJECT_BACKEND`、`FEISHU_PROJECT_ALLOWED_SPACES`、`FEISHU_PROJECT_SIMPLE_NAMES` | 飞书项目 backend、space allowlist 和必要的 stable-key URL 映射。 |
| `JARVIS_UV_IM_CONNECTOR_NAME`、`JARVIS_UV_IM_CONNECTOR_URL`、`JARVIS_UV_IM_CONNECTOR_TOKEN` | 与已启用 connector 的连接。`uvim` 的 token 与 connector env 相同；`uvim-external` 使用 hub 为本 Box 分配的独有 scoped client token。 |
| `JARVIS_CHAT_ALLOWED_USERS`、`JARVIS_CHAT_ALLOWED_CONVERSATIONS`、`JARVIS_CHAT_REQUIRE_MENTION`、`JARVIS_MENTION_NAMES` | ChatBridge 的用户/会话限制、mention requirement 和触发名。 |
| `JARVIS_NOTIFY_PROVIDER`、`JARVIS_NOTIFY_CONNECTOR`、`JARVIS_COMMAND_NOTIFY_ENABLED`、`JARVIS_COMMAND_NOTIFY_RECIPIENT_MODE`、`JARVIS_COGNITIVE_EVOLUTION_NOTIFY_TARGET` | 既有通知目标与投递策略；不按任务名称自行推导收件人。 |
| `TAPD_*`、`YUNXIAO_*` | TAPD/云效 adapter 的命令、token、endpoint、scope 与 webhook 设置。 |
| `GIT_LFS_SKIP_SMUDGE` | workspace clone/checkout 默认 `1`，按需下载 LFS；显式 `0` 恢复全量 materialize。 |

## Runtime Agent、lane 与工具

| 变量 | 作用 |
| --- | --- |
| `JARVIS_RUNTIME_AGENT` | 全局默认 Runtime Agent。 |
| `JARVIS_RUNTIME_AGENT_ADAPTERS` | 版本化 Agent 目录 JSON；当前 release 的兼容迁移可读取旧格式，新增条目按[Runtime Agent](runtime-agents.md#自定义-runtime-agent)合同编写。 |
| `JARVIS_RUNTIME_AGENT_SCOPE_DELIVERY_METRICS` / `_PREFIX_ARGS` | Delivery Metrics lane 的 Agent 和前置参数覆盖。 |
| `JARVIS_DELIVERY_METRICS_ENABLED` | 默认 `true`。设为 `false` 后不再创建新的 Delivery Metrics Task；已有 Run 与 Continue 可以收尾。 |
| `JARVIS_RUNTIME_AGENT_FALLBACK_ORDER` | 自动回退的完整候选顺序；空值表示不自动切换。 |
| `JARVIS_RUNTIME_AGENT_SCOPE_*` / `_PREFIX_ARGS` | 其他发布的 lane/scope Agent 与前置参数覆盖；只填写该 release sample 列出的 scope，并确认对 effective Agent 有效。 |
| `*_CMD` | 对应 Agent CLI 的 executable 名称或绝对路径，例如 `QWEN_CMD`。 |

先用 `jarvis-box agent set` / `unset` 保存 Agent 选择，再按 [Agent 选择规则](runtime-agents.md#选择和验证)填写需要的前置参数。运行 `jarvis-box agent doctor` 和 `jarvis-box agent smoke <agent>` 检查配置。已有 Task 需显式 Continue 并选择 Agent。Delivery Metrics 的用户流程见[Delivery Metrics 历史起点](delivery-metrics.md)。

## Agent runtime preparer

`JARVIS_AGENT_RUNTIME_PREPARE_COMMAND` 是可选的绝对可执行路径，`JARVIS_AGENT_RUNTIME_PREPARE_TIMEOUT_SECONDS` 默认 `120`，必须大于零。Jarvis Box 在每个新 Task 第一次启动 Agent 前调用它，并把程序所在目录加入 Agent PATH。

程序不接收参数，只能向 stdout 输出一个不超过 4096 bytes 的 JSON object：

```json
{"schema":"jarvis-agent-runtime-prepare/v1","status":"updated","revision":"customer-runtime-r42"}
```

`status` 只能是 `updated`、`unchanged` 或 `stale-valid`；`revision` 是非空、不含换行、最多 256 字节的 opaque 值。失败、超时或非法输出阻止本次 Agent 启动，但不删除已准备的 Workspace。成功 receipt 被 Task 持有，普通 Continue 不会重新调用；若之前没有成功 receipt，Continue 会在准备后重试。程序的 repo/ref、同步和 discovery 判断属于客户 Runtime Foundation，不属于 Jarvis Box。

## workspace 准备程序

`JARVIS_WORKSPACE_DEPENDENCY_CONFIGURER` 是 checkout 后、Agent 启动前运行的可选程序。调用形式为：

```text
<program> <repo> --configure-existing <workspace> [--base-branch <branch>]
```

它适合配置客户依赖缓存或 workspace-local Git identity；不应猜测客户安装命令。程序失败会阻止该 Run 启动。共享运行时的 Git 身份配置见[代码归属与 Git 提交身份](code-attribution.md)。

## IM 显示与回复文案

`JARVIS_BRAND_NAME` 只改显示名，不改二进制、镜像、服务单元或变量名。它不能包含 `'`、`"`、`` ` ``、`\`、`<`、`>`、`&`、`%` 或控制字符；服务会拒绝不安全名称。

`JARVIS_CHAT_LAUNCH_REPLY_TEMPLATE` 必须保留一个 `%s`（Run ID）；`JARVIS_CHAT_QUEUED_REPLY_TEMPLATE` 保留两个 `%s`（等待原因、Task ID）；`JARVIS_CHAT_HELP_REPLY_TEMPLATE` 保留两个 `%s`（显示名、触发词）。字面量百分号写成 `%%`。`JARVIS_COMMAND_NOTIFY_COMPLETED_TEMPLATE` 是无格式替换的完成通知标题。

<a id="configprompts"></a>

## Prompts、connector 与授权

`$JARVIS_RUNTIME_ROOT/config/prompts/` 存放可编辑的 Agent 说明。Native 默认目录为 `~/.jarvis-box/config/prompts/`。服务补齐缺失文件，保留已有文件和空文件。留空可停用该段说明，删除可恢复发行版默认内容。模板使用 Go `text/template`，不会展开 shell 环境变量。请将连接参数和凭据保存在各自的配置位置。读取或渲染出错时，相应 Agent 不会启动。

平台说明和回复模板在 command 或 post-check 准备 Run 时读取，支持以下变量。

```text
{{.Provider}}
{{.BrandName}}
{{.RunDir}}
{{.CommentFile}}
{{.WritebackEnabled}}
```

| 文件 | 用途 |
| --- | --- |
| `gitlab.md`、`github.md`、`jira.md`、`zentao.md`、`tapd.md`、`feishu-project.md`、`yunxiao-projex.md`、`yunxiao-codeup.md` | 对应平台的 command/post-check 上下文与工具说明。 |
| `feishu-project-plugin.md` | 飞书项目 plugin backend 的服务端预取说明。 |
| `command-response.md`、`post-check-response.md` | command/post-check 的结果文件与自动发布说明。 |

GitHub 和 GitLab 在发起新一轮自动代码评审时共用以下文件。

- `mr-review.md` 提供每个评审进程共用的说明。
- `mr-review-angles.md` 中每个以 `## ` 开头的标题及其正文定义一个独立评审角度。发行版默认提供六项，文件至少需要保留一项带正文的评审角度。
- `mr-review-response.md` 提供各角度的交付说明。评审进程将 Markdown 原稿写到 `REVIEW_COMMENT_FILE`。证据不足时，正文说明缺口，并在 `REVIEW_COMMENT_ACTION_FILE` 写入 `blocked-comment`。
- `mr-review-summary.md` 提供最终短评的写法。留空会停用这段说明，Runtime Agent 仍会读取原稿并写出汇总。

各角度结束后，同一个已配置的 Runtime Agent 再执行一次，读取原稿并写一条原平台短评。每个需要作者处理的问题只写一次。没有问题时只回「无须处理。」。证据不足时，短评会简要注明缺口。

评审模板可使用 `Provider`、`RunDir`、`DiffFile`、`URL`、`Project`、`SourceBranch`、`TargetBranch`、`CommitSHA` 和 `Workspace`。保存后，下一轮新评审使用新内容，包括用 Continue 发起的新评审。强制更新或重启恢复单会话评审时，沿用原会话。

以下 Markdown 文件直接编辑正文，无需模板变量。

| 文件 | 可调整内容及生效时机 |
| --- | --- |
| `issue-post-check.md` | 调查步骤、证据要求和面向报告者的结论。新问题检查及续跑准备时读取。从历史 Run 重新发起时沿用来源 Run 已保存的提示词。 |
| `followup.md` | 如何核实和处理评审意见。跟进适配器准备新一批评论或恢复尚未启动的跟进工作时读取。 |
| `delivery-metrics.md` | 如何查找和对照人工纠错证据。后台受理新的分析任务时读取。分类及其含义见 [Delivery Metrics](delivery-metrics.md)。 |
| `task-recap.md` | Agent 生成任务标题的语言、长度偏好和风格。在受理新的标题分析时读取。已有可信原生会话标题时优先采用原生标题。 |

<a id="connectorenv"></a>

启用 `JARVIS_CONNECTOR_PROFILE=uvim` 时，`UV_IM_AUTH_TOKEN` 必须与 `JARVIS_UV_IM_CONNECTOR_TOKEN` 相同。Native 的 connector env 位于 `${JARVIS_RUNTIME_ROOT}/envs/.env.uv-im-connector`；Docker 使用 deployment home 的 `connector.env`。平台凭据只由 connector 保存。

`uvim-external` 不读取 `connector.env`，不启动、升级或停止共享 hub；URL 与本实例独有的调用方 token 只写入 canonical runtime env。Native installer 会停用已有受管 companion。profile 为空或 external 时，Docker helper 可能保留空的受限权限 `connector.env` 以满足 Compose 文件要求。完整接入与隔离规则见 [IM 配置](integrations/im.md#管理员-配置-jarvis-box-与-connector)。

授权也只读取 canonical runtime env。`JARVIS_LICENSE_URL` 仅开发构建有效；发布构建使用编译进二进制的授权服务，不能通过 env 覆盖或关闭。`JARVIS_LICENSE_STATE_DIR` 默认 `${JARVIS_STATE_DIR}/license`，必须持久化；`JARVIS_LICENSE_CHANNEL` 默认 `stable`，`JARVIS_LICENSE_DEPLOYMENT` 是 `native` 或 `docker`（Docker image 已设置）。激活码不要写入 env；使用 `jarvis-box license activate` 或离线 request/import 流程。

<a id="auth"></a>

`auth-import` 只从当前 Host 用户的选定 `gh`/`glab` token、Codex `auth.json`、Claude `.credentials.json` 或显式 headless key 创建可移植身份快照。Docker deployment home 的 `auth/` 目录为 `0700`、文件为 `0600`，只读挂载到 `/run/jarvis-host-auth` 后导入持久 Agent HOME；它不挂载 Host HOME、Keychain、SSH agent 或完整凭据库。

<a id="container-paths"></a>

## Docker 容器路径与派生变量

| 容器路径 | 内容 |
| --- | --- |
| `/etc/jarvis-box/runtime.env` | 挂载的 canonical runtime config |
| `/home/jarvis` | 持久 Agent identity/config、discovery roots、客户 Runtime Foundation |
| `/run/jarvis-host-auth` | 只读 Host portable-credential snapshot |
| `/workspace` | 持久 Task workspace |
| `/var/lib/jarvis-box` | Task/Run state |
| `/var/cache/jarvis-box` | 独立于 workspace 清理的依赖缓存 |
| `/var/log/jarvis-box` | Jarvis Box 日志 |

<a id="docker-自动派生变量"></a>

`JARVIS_UID`、`JARVIS_GID` 以及启用 socket 时的 `JARVIS_DOCKER_GID` 由 `scripts/deploy-production.sh` 按当前 OS 用户与 socket 自动派生，不是要手工维护的业务配置。用户只需能使用 Docker 并拥有 deployment home。
