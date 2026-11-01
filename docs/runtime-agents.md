# Runtime Agent

正式 Agent 是客户授权的高权限主体，可以接收代码、源码和 writeback 能力。Native 与 Docker 都使用发起安装的现有 OS 用户；Docker 以该用户的数字 UID/GID 非 root 运行，并通过 NSS 映射提供稳定的 `jarvis` 用户身份。默认 Compose 以 `IS_SANDBOX=1` 标记无 socket 的容器边界，使 Claude 可以使用非交互式 bypass 模式。Docker socket overlay 是独立的宿主 root 等价选项，并覆盖 `IS_SANDBOX=0`，使 Claude bypass fail closed。

## 身份

Native 服务复用该用户的原生 CLI 身份。Docker 不能继承 Host Keychain 或登录会话：将窄化的凭据快照导入由 `$JARVIS_DEPLOYMENT_HOME/data/agent-home` 提供的持久 `/home/jarvis`；绝不挂载 Host 用户的完整 credential store。

```bash
scripts/deploy-production.sh /absolute/deployment-home start
scripts/deploy-production.sh /absolute/deployment-home auth-import
```

`start` 已执行导入。使用显式命令轮换或选择其他 Host 身份，然后运行通用 `verify`。

Provider / push 身份、Runtime Agent 身份和 Git commit identity 是三件事。共享 Jarvis 运行时可以继续使用机器账号读取 provider、写回评论或推送分支，同时在每个 workspace 的 `.git/config` 中把新 commit 归属到客户定义的代码负责人。配置方式见 [代码归属与 Git 提交身份](code-attribution.md)。

## Native 宿主工具

Native Agent 使用宿主用户的命令行工具。macOS 默认没有 GNU `timeout`；工作流需要执行 `timeout …` 时，以该用户安装 [Homebrew coreutils](https://formulae.brew.sh/formula/coreutils)，并验证命令可用：

```bash
brew install coreutils
command -v timeout
timeout 2s /usr/bin/true
```

服务的 PATH 也必须包含安装目录；macOS 安装器已包含 Homebrew 的标准目录 `/opt/homebrew/bin` 和 `/usr/local/bin`。使用 GNU 实现保留其参数、信号和退出码语义；Jarvis Box 不另行实现 `timeout`，也不会为 Native 宿主自动安装 coreutils。仅需该命令时，无需把整个 coreutils `gnubin` 目录提前到 PATH。

## GitLab 工具指令

所有 lane 的共享 Agent 工具契约要求使用该 lane 配置的已认证 GitLab CLI，并保留配置的 host 和 project 范围。以下示例中的 `glab` 代表该可执行文件：

| 可执行文件 | API GET 与 JSON 查询 |
| --- | --- |
| Jarvis Box 受管 runtime shim | `glab api-get <endpoint> --jq '<filter>'` |
| Native 原生 CLI | `glab api <endpoint> \| jq '<filter>'` |

`api-get` 是受管 shim 的扩展，不能假定 Native 原生 CLI 支持它；`glab api` 不支持 `--jq`。无法确认可执行文件是受管 shim 时，使用 `api … | jq …` 管道。

## Agent 选择

`JARVIS_RUNTIME_AGENT` 和当前实例生效运行时环境文件中的可选 scope override 选择 Agent 可执行文件。环境文件由 `JARVIS_ENV_FILE` 指定，未设置时使用 `$JARVIS_RUNTIME_ROOT/envs/.env.jarvis-box`。变更属于 operator 配置变更，需要 doctor/smoke 加上受影响的 workflow 验证；不涉及 Jarvis context 或 deployment lock。

`custom-user-task` 使用与 `jarvis-command` 同类的 providerless prompt task 启动路径和 Runtime Agent scope。它不会携带 provider writeback contract；外部投递是否成功由 agent task 的结果证据表达。`job_id` 只影响任务身份、Status 展示和同 job 防并发，不参与 Runtime Agent 选择。

所有 Agent，包括 Codex、Claude、Copilot、OpenCode、Gemini 和 Qwen，都使用同一份 `exec-v1` 描述契约。发行包提供预设数据；新增兼容 CLI 不需要修改 Task、Provider 或 IM 逻辑。预设还包括 CodeBuddy（别名 WorkBuddy）、CodeArts、DevEco、OpenClaw、Hermes、Pi、Cursor、Kimi、Reasonix、DSH、Kiro、Antigravity、Qoder、QoderCN、TRAE、Grok、MCode、Muse、Dim、Devin、ZeroClaw 和 OMP。预设存在不代表 CLI 已安装、账户已登录或模型连接可用。各 CLI 的原生模型和工具能力仍需验证。QwenPaw 的原生 `task` 命令不支持文件和 Shell 工具，不能完成 Jarvis 任务所需的文件操作，未提供发行预设。可用 CLI 安装并完成原生配置后可选择使用：

```bash
jarvis-box agent list
jarvis-box agent smoke qwen
jarvis-box agent set qwen
jarvis-box agent set --scope delivery-metrics qwen
```

新选择用于后续启动。已有 Task 可以通过 `tasks continue <task-id> --agent <agent> --message "<新指令>"` 显式切换，保留 Task、工作区、文件产物和交付目标。跨 Agent 不转换历史聊天或传递原生会话句柄。

## Qwen Code

Native 使用服务用户安装的官方 `qwen` CLI，要求 Node.js 22 或更新版本。运行 `qwen` 按其交互提示完成认证，并先在该用户环境中确认可以执行任务。可执行文件不在服务 PATH 时，在 canonical env 中设置 `QWEN_CMD` 为绝对路径。

```bash
npm install -g @qwen-code/qwen-code@0.26.3
qwen
```

Jarvis Box 使用 Qwen 的非交互执行和结构化输出。模型、供应商和认证由 Qwen 的原生设置管理；可以通过工作类型的 prefix args 指定 `--model` 或 `--auth-type`。是否能查询账户额度不影响 Qwen 的执行能力。

Docker 应使用工具清单包含 `qwen` 的发行镜像，先通过 `jarvis-box tools status` 确认其可用。镜像提供固定版本基线，`jarvis-box tools update` 管理其在线更新；使用尚未包含该 CLI 的镜像时，通过[客户派生镜像](custom-docker-image.md)安装所需版本。Qwen 登录在该部署的持久 Agent HOME 内完成：

```bash
scripts/deploy-production.sh /absolute/deployment-home shell
qwen
```

Qwen 不参加宿主机便携认证快照导入；容器重建保留持久 Agent HOME 中的登录状态。Native 安装和升级由用户选择的包管理器负责。

Qwen 的个人技能目录为 `~/.qwen/skills`，项目技能目录为 `.qwen/skills`。客户 Runtime Foundation 向已确认的发现目录交付公司技能；切换前通过真实 Qwen 调用确认技能可用。目录规则见 [Qwen 官方技能文档](https://qwenlm.github.io/qwen-code-docs/en/users/features/skills/)。

## 自定义 Runtime Agent

`JARVIS_RUNTIME_AGENT_ADAPTERS` 在现有 canonical env 文件中保存版本化 JSON。版本 2 的 `agents` 是完整目录：既包含发行预设，也包含客户自定义项，不再把内置品牌作为另一套配置合并。1.1.0 升级通过停服 Flyway 将已发布的版本 1 配置物化为版本 2，保留原命令、选择、别名、模型参数、凭据和历史 Task/Run；与客户名称、别名或命令键冲突的新预设不会覆盖客户条目。已发布的旧格式继续可读。

Agent 没有额外的启用或禁用状态。1.1.0 迁移删除旧 `JARVIS_RUNTIME_AGENT_DISABLED` 配置及其排除含义；全局与作用域选择继续由各自配置决定。

`JARVIS_RUNTIME_AGENT_FALLBACK_ORDER` 是自动回退的完整候选顺序；空列表表示不自动切换，安装 CLI 或增加目录条目不会追加候选。每次自动切换前，Jarvis Box 先查询候选 Agent 实际计费账户的可用余额，再使用同一生效配置调用真实 Agent 和模型，在 30 秒内验证一次随机口令回复。探测后再次查询余额，并核对配置与原任务仍然有效，均通过后才派发原任务。查不到余额、余额不足、配置发生变化、CLI 或模型验证失败的候选均不会自动接手；订阅使用百分比不能代替可用余额。探测会产生一次模型调用。余额查询能力不足不妨碍用户直接选择该 Agent 执行任务。

首次升级还会将旧版直接继承、1.1.0 新纳入配置管理的原生会话目录、命令和模型供应商变量写入同一配置文件。仅补入文件中尚未声明且旧目录没有管理的变量；显式空值仍然有效。后续启动和升级读取该文件，不再次从进程环境导入这些值。

以下例子描述仅使用一个自定义 CLI 的完整目录。向已有部署增加 Agent 时，将该条目追加到现有 `agents` 数组，保留仍需使用的其他条目：

```dotenv
JARVIS_RUNTIME_AGENT_ADAPTERS='{"version":2,"agents":[{"name":"custom-agent","command":"/opt/bin/custom-agent","driver":"exec-v1","argv":{"start":["{prefix_args}","--prompt={prompt}"],"smoke":["--prompt={prompt}"]},"env_keys":["CUSTOM_AGENT_API_KEY"],"output":{"protocol":"text"},"capabilities":{}}]}'
```

```bash
jarvis-box agent list
jarvis-box agent smoke custom-agent
jarvis-box agent set custom-agent
```

| 字段 | 契约 |
| --- | --- |
| `name` | 唯一名称：以小写英文字母开头，只含小写英文字母、数字和连字符，最长 64 字符；目录内名称和别名不能冲突 |
| `command` | CLI 可执行文件名或绝对路径；工具安装和登录由该 CLI 的部署流程负责 |
| `env_key` | 可选的命令覆盖变量名，必须以 `_CMD` 结尾且不与其他命令键冲突；默认把名称转换为大写、连字符替换为下划线，再加 `_CMD` |
| `driver` | 所有条目均为 `exec-v1` |
| `argv` | `start` 必填；可声明 `resume`、`compact`、`plain_start`、`plain_resume`、`smoke`；每个执行模板恰好包含一个 `{prompt}` |
| `output` | 固定的版本化输出协议，可含 JSON 字段映射；不支持的协议明确拒绝 |
| `session` / `resume` | 原生 ID 来源、格式、选择与恢复协议；只有完整实现的组合才能声明恢复能力 |
| `model` / `resources` | 模型环境变量、原生配置来源及只读账户诊断路由元数据 |
| `env_defaults` | 已声明环境变量的字面量默认值；显式值（包括空值）优先，凭据不能写在描述默认值中 |
| `env_keys` | CLI 使用的模型与认证变量名；不能声明 Jarvis、Provider、Connector 或进程启动的保留变量 |
| `aliases` | 可选的唯一别名，与名称使用同一命名空间和格式 |
| `skills_dir` | 可选的技能发现目录元数据；不触发安装或同步 |
| `capabilities` | 由操作和协议校验出的能力投影；省略能力标志不授予额外权限，矛盾声明会被拒绝 |

模板直接构造进程参数，不经过 Shell 求值。`{prefix_args}` 必须独占一个数组元素，按原顺序插入该次运行的参数；标量占位符还包括 `{cwd}`、`{workspace}`、`{native_session_id}`、`{resume_session_id}`、`{output_last_message}`、`{resolved_model}` 和 `{max_autopilot_continues}`。提示词保留为一个参数，提示词里的占位符不再展开。建议采用 CLI 支持的 `--prompt={prompt}`，或把裸 `{prompt}` 放在 CLI 的 `--` 终止符之后，避免以短横线开头的提示词被当成选项。可选片段形如 `{"optional":"cwd","args":["--cwd","{cwd}"]}`；条件仅支持 `cwd`、`workspace`、`native-session`、`output-last-message`、`autopilot`、`model` 和 `structured-output`，不执行表达式。启动目录、进程归属和取消由 Jarvis Box 管理。

`text` 使用进程退出结果判断执行成败。`stream-json-v1` 要求 CLI 输出符合约定的逐行 JSON，终态由顶层 `type=result` 及 `is_error` 字段表达；助手或工具正文中引用的 JSON 不具有终态权限。未知协议、重复名称、非法模板或字段会明确报错，不会悄悄退回另一个 Agent。只有实际实现此协议的 CLI 才能选择它。

`jsonl-v1` 读取逐行 JSON，`json-v1` 在 EOF 读取一个有界完整 JSON 对象。字段映射只支持固定 JSON Pointer、顶层事件类型、存在/缺失条件和类型一致的标量字面量比较；数字按原 JSON 数值字面量精确比较，不作浮点舍入或数值格式转换。`null` 不等于字段缺失。映射可提取会话、模型、结果及普通执行终态，不能签发模型受限恢复或压缩权限。结果默认以最后一个匹配消息替换；原生协议只输出文本增量时，可设置 `jsonl.append_results=true` 按顺序拼接。单行、文档或拼接结果上限为 1 MiB，非法 UTF-8、超限或不完整数据不能证明成功。

`results` 提取的结果也作为工作台助手消息显示。其他消息可配置 `jsonl.messages`，例如 `{"match":{"type":"tool_event"},"path":"/payload","kind":"tool"}`；`kind` 支持 `assistant`、`think`、`tool`、`error`、`runtime`、`user`、`system`。匹配条件与结果使用同一种字段规则，多个消息映射取第一个有效匹配；未声明的事件作为运行记录显示，不据字段名称猜测权限。每次 Run 固定保存自己的消息解析配置，之后修改或删除 Agent 配置不影响历史消息。

Jarvis Box 只执行原生一次性命令，接收其输出并等待进程退出，不实现 ACP、MSP 或交互控制协议，也不内置其客户端包装器。CLI 只有交互或双向协议入口、一次性入口缺少任务所需工具时，不能作为本协议下的完整任务执行 Agent。

每次 Run 在一个生效配置快照内完成 Agent 选择、参数生成和派发。同 Agent Continue 保留已经固定的显式模型和 prefix args；后续操作可以重新读取 canonical 配置。原生恢复、压缩与输出能力取决于所选协议和实际 CLI 合同。未实现的能力不能通过填写 `capabilities` 启用。

`model.env_keys` 按顺序读取原生命令使用的模型标识；声明 `option_syntax=model-flags-v1` 时，显式 `--model` 参数优先。CLI 的内部模型标识与供应商请求中的模型名不同时，可用 `model.wire_env_keys` 声明该 CLI 实际消费的请求模型变量：命令参数使用内部标识，模型及账户诊断使用请求模型名。描述中的可选 `model` 参数片段可把解析结果传给原生命令，避免其保存的本地模型覆盖已声明的选择。

## 会话续接

会话存在不表示本次输入已被 Agent 接收。当前 `codex-exec-json-v1` 支持输入接收确认：未完成 Run 的已接受输入只有在确认尚未接收时才随 Continue 保留；回执未知时拒绝重放。其余协议尚不支持该确认，沿用原有 Continue 输入规则。

未接收输入包含已下载的 IM 附件。Continue 会把经来源 Run 身份校验的附件复制到本次 Run，使用本次消息的回复目标和输出目录。只有附件、没有文字的消息也是有效输入。准备失败仍保留已受理的用户文字；IM 失联恢复的授权指令不会替换用户的新要求。已发布 Run 缺少输入记录时继续沿用原规则，不从历史会话或进程提示重建用户输入。

原生恢复首先校验绑定 exact Run、Agent、AgentConversation 和会话协议的私有回执，再执行所声明的本地记录检查或原生 load/resume。Codex、Claude 和 Copilot 保留已发布的记录与 UUID 合同；Codex 归档会话仍按既有规则校验并恢复单个文件。不能取得可靠 handle 时，Continue 在原 Task 内创建新会话，保留工作区、已有交付文件、当前指令和回复目标；新会话不携带丢失的历史聊天上下文。已经启动的原生 load/resume 若被拒绝，本次 Run 失败并留下诊断，不在同一次派发中偷偷重试 prompt。跨 Agent 不复用原生句柄。其余协议按声明捕获和校验原生 opaque ID，不通过扫描日志猜测会话。Gemini、Qwen、OpenCode、OpenClaw、Hermes、Kiro、TRAE、Muse、Devin 和 ZeroClaw 的发行预设当前不支持原生上下文续接；Continue 会在同一 Task 中开始新原生会话。

## 运行结果与取消

当前任务使用无人值守执行方式。权限交互以独立 `ApprovalPolicy` 表达，当前只支持默认及 `unattended`；请求 `interactive` 或未知策略会在启动前拒绝。协议保留人工审批扩展位置，尚不提供审批对话、审批队列或应答命令。

普通 Agent 执行失败沿用原 Agent 自动 Continue，让 Agent 检查日志和已有产物、判断如何继续；与三类模型受限恢复共用最多五次的持久预算。会话、取消和交付保护遵循[有界自动 Continue 合同](execution-model.md#agent-中断的有界自动-continue)。

进程退出码为零不覆盖已选择输出协议中的可信终态失败事件。取消、超时、强制杀死或产物写入失败不会被原生成功事件覆盖。真实退出码和信号保留，不改写为虚假的零退出。助手仅引用错误文字不会改变运行结果。

取消会终止本次 Agent 及其已确认的子进程，包括工具自行建立的新进程组。停止前冻结原进程的启动身份和派生关系，并在发信号时用系统稳定身份复验，不按工作目录、同名命令或单独的数字 PID 扩大范围。无法确认归属或停止结果时保留错误，不能宣称已安全停止。

## 模型路由与计费额度

Agent、模型和计费账号是三个独立维度。Claude 可以通过 `ANTHROPIC_BASE_URL` 使用 DeepSeek，其他 CLI 可以通过各自原生配置使用第三方模型。Status 先解析 Agent 实际选中的模型、服务地址和凭据来源，再读取同一账户的额度，绝不根据 Agent 名称或另一个 Agent 的环境变量猜测计费方。

描述中没有可读取的路由信息、也没有声明默认计费方时，Status 将计费方显示为未知。其他 Agent 配置的全局密钥不会替代该 Agent 的原生路由证据。

`resources.json_config` 可声明原生 JSON 中的只读账户绑定：`env_key` 读取显式内联配置，`path` 指向配置文件（可引用 `${ENV_KEY}`）；非空内联配置优先。`model_path` 和 `provider_path` 读取选择，`base_url_path` 与 `credential_path` 读取同一记录的地址和凭据，或以 `credential_env_path` 读取该记录引用的环境变量名。字段使用 JSON Pointer，`{model}`、`{provider}` 可选择对象键或数组中唯一的 `id`；`model_separator` 可拆分 `provider/model` 选择。配置缺失、非 JSON、记录冲突或读取失败均保留未知语义，不改变 Agent 自身的执行能力。

OpenCode 预设读取显式 `OPENCODE_CONFIG_CONTENT` 或 `OPENCODE_CONFIG` 中选中的 provider；CodeBuddy（WorkBuddy）读取指定配置目录的 `models.json` 与实际 `--model` 选择；Qwen 读取原生 settings 中选中的认证类型和模型记录。存在 DeepSeek 模型名不代表已确认 DeepSeek 账户，临时测试配置通过也不表示日常服务已完成这些配置。

`/status` 的“系统设置 → 工作方式 → 模型资源与额度”展示当前可识别的关系。ChatGPT 登录的 Codex 通过本机 account/rate-limit 接口读取滚动窗口；指向官方 `api.deepseek.com` 的兼容路由使用 Agent 实际采用的 credential 读取 DeepSeek 钱包。同一 credential 被多个 Agent 使用时，它们显示相同的脱敏账户引用和同一份余额。其他计费方没有适用的安全公开接口时只显示模型/计费方和“不支持自动读取”，不会用本机 token 统计或模型列表伪装账户额度。

DeepSeek 兼容路由只使用所选 Agent 实际消费的凭据：例如 Claude 的 `ANTHROPIC_AUTH_TOKEN`，或原生模型记录中引用的环境变量。未取得该凭据时不使用其他全局密钥代查余额。响应仅返回不可逆的短账户引用。

`resources.opaque_credential_env_keys` 声明无法直接识别的原生凭据来源，例如获取密钥的命令或自定义请求头。配置这些来源后，Status 保留模型和供应商信息，但不执行命令、不生成账户引用，也不使用备用密钥查询余额。该限制不影响 Agent 使用自己的认证机制执行任务。

额度采集是只读、best-effort 的 Status 证据：不发起模型推理，不改变路由，不把原始账户身份、credential 或上游 body 写入 response。额度不可用不会把 Agent 命令本身改成 unavailable；当前实际启动使用入口明确解析的 Agent 配置和 Provider 自身准入，不存在从额度或 runtime 文案推导出的自动路由。

## Delivery Metrics

Delivery Metrics 使用普通 `delivery-metrics` lane Task 分析历史 MR/PR。它默认继承全局 Runtime Agent；以下命令设置或取消独立选择：

```bash
jarvis-box agent list
jarvis-box agent set --scope delivery-metrics codex
jarvis-box agent unset --scope delivery-metrics
```

`agent list` 的 `scoped runtime agents` 会显示 `delivery-metrics` 的 effective Agent、来源、命令和 prefix args。设置前运行 `jarvis-box agent doctor` 和 `jarvis-box agent smoke <agent>`。

Status 服务为每个待分析 MR/PR 启动一个 `delivery-metrics` lane Task，执行该分析的 exact Run 输出 `delivery-metrics-result.json`。Continue 使用同一个 lane scope 重新解析 Agent 配置；切换 Agent 或模型不会改写已经完成的历史 Run 分类结果。进度与恢复步骤见 [Delivery Metrics 历史起点](delivery-metrics.md)。

## Skill 发现

- 镜像自带的通用 `skill-creator` 链接到 Codex、Claude 和 Qwen 的个人技能目录；
- create-jarvis 绝不安装在正式运行时中；
- 客户 Jarvis skills 由该 Jarvis 的 Runtime Foundation 在持久 Agent HOME 中安装/更新；
- jarvis-box 不将 root skill、`JARVIS_HOME`、commit 或 workflow 路径注入 Run；
- identity 自有的已有 skills 不被镜像 entrypoint 覆盖。

Runtime Foundation onboarding 必须通过真实 Agent 调用来证明发现。仅有文件系统存在是不够的。

uv-im-connector 拥有 provider 原生 IM secrets 和长连接；jarvis-box 仅使用 connector protocol/token，不将 connector secrets 传递给 Agent 子进程。
