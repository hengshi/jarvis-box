# Runtime Agent

本文面向选择、验证或扩展 Jarvis Box Runtime Agent 的客户 operator 和集成开发者。Runtime Agent 是客户授权的高权限主体：它可以接收源码、代码和已配置的 writeback 能力。Agent 选择、Provider/push 身份和 Git commit identity 是三件不同的事。

日常选择 Agent 从“选择和验证”开始。要定义新的 CLI adapter，阅读“自定义 Runtime Agent”完整契约；不要只凭 CLI 名称、已安装文件或模型名假设它可用。

<a id="身份"></a>

## 身份与运行边界

Native 复用安装者 OS 用户的 CLI 身份。Docker 以安装用户 UID/GID 的非 root 进程运行，容器内通过 NSS 映射为稳定 `jarvis` 身份；它不会继承 Host Keychain 或登录会话。导入身份使用 deployment home 的私有 `auth/` 和持久 `/home/jarvis`：

```bash
scripts/deploy-production.sh /absolute/deployment-home start
scripts/deploy-production.sh /absolute/deployment-home auth-import
```

`start` 已经执行导入。使用显式 `auth-import` 轮换或选择 Host 身份后，再运行 deployment `verify`。Docker socket 是独立的宿主 root 等价选项；默认无 socket 的容器以 `IS_SANDBOX=1` 运行，而 socket overlay 会将它设为 `0`，令 Claude 的 bypass fail closed。

Provider/push 身份决定读取、评论与 push 权限；Runtime Agent 身份决定 Agent CLI 的登录；Git commit identity 只决定 commit 的 Author/Committer 元数据。共享 runtime 若要把提交归属给负责人，在每个 workspace 的 local Git config 中设置它；流程见[代码归属与 Git 提交身份](code-attribution.md)。

<a id="agent-选择"></a>

## 选择和验证

全局选择来自 canonical runtime env 中的 `JARVIS_RUNTIME_AGENT`，lane 可有 scope override。有效 env 文件由 `JARVIS_ENV_FILE` 指定，默认 `$JARVIS_RUNTIME_ROOT/envs/.env.jarvis-box`。改变选择是 operator 配置变更：先检查、保存，再对受影响 workflow 做实际验证。

```bash
jarvis-box agent list
jarvis-box agent current
jarvis-box agent doctor
jarvis-box agent smoke qwen
jarvis-box agent set qwen
jarvis-box agent set --scope delivery-metrics qwen
```

`doctor` 检查命令与配置；`smoke` 真实调用选定 Agent。发行预设存在不表示 CLI 已安装、账户已登录、模型可达或具备所需工具。

`agent set <agent>` 或 `agent set --force <agent>` 每次保存全局 Agent 时都会清除所有 scope 和 Agent 描述器配置的前置参数。重复设置同一个全局 Agent 也会清除参数。`agent set --scope <scope> <agent>` 在该 scope 的有效 Agent 变化时清除它自己的前置参数，重复设置同一个有效 Agent 时保留参数。

需要自定义前置参数时，先选择 Agent，再填写适用的参数。自定义描述器应使用专用的参数键。若待清除的参数键同时用于命令路径、认证、模型或其他运行配置，保存会报出冲突键，原配置继续生效。

新选择只应用于后续 Start。已有 Task 可明确切换：

```bash
jarvis-box tasks continue <task-id> --agent <agent> --message 'continue with these instructions'
```

跨 Agent 不转换历史聊天或原生会话句柄。`custom-user-task` 使用 providerless prompt 启动路径和同一 Runtime Agent scope；`job_id` 只影响 Task 身份、Status 展示和同 job 防并发，不参与 Agent 选择或 provider writeback。

如果 Codex 明确拒绝音频输入，原任务会保留工作区和已保存的产物。先用 `jarvis-box tasks show <task-id>` 按 Run ID 核对失败记录。用上面的命令选择能够处理所需输入的 Agent，并在新消息中补充原要求和需要使用的材料。单独发送“继续”可能再次使用原 Codex 会话。

所有发行 Agent 使用 `exec-v1` 描述契约。预设包括 Codex、Claude、Copilot、OpenCode、Gemini、Qwen、CodeBuddy/WorkBuddy、CodeArts、DevEco、OpenClaw、Hermes、Pi、Cursor、Kimi、Reasonix、DSH、Kiro、Antigravity、Qoder、QoderCN、TRAE、Grok、MCode、Muse、Dim、Devin、ZeroClaw 和 OMP。QwenPaw 的原生 `task` 命令不具备 Jarvis 任务需要的文件/Shell 工具，未提供预设。

<a id="native-宿主工具"></a>

## Host 工具约定

Native Agent 使用服务用户的宿主工具。macOS 默认没有 GNU `timeout`；需要该命令的 workflow 由服务用户安装 Homebrew coreutils，并确认服务 PATH 可见：

```bash
brew install coreutils
command -v timeout
timeout 2s /usr/bin/true
```

macOS 安装器包含常见 Homebrew 目录 `/opt/homebrew/bin` 和 `/usr/local/bin`，但不会代为安装 coreutils，也不会重新实现 GNU `timeout`。

<a id="gitlab-工具指令"></a>

对于 Agent 的 GitLab API 读取，受管 runtime shim 提供 `glab api-get <endpoint> --jq '<filter>'`。Native 原生 `glab` 应使用：

```bash
glab api <endpoint> | jq '<filter>'
```

不要假定原生 `glab api` 支持 shim 的 `api-get` 或 `--jq` 扩展。

## Qwen Code

Native 使用服务用户安装并登录的官方 `qwen` CLI，要求 Node.js 22 或更新版本。命令不在 service PATH 时，在 canonical env 用绝对路径设置 `QWEN_CMD`：

```bash
npm install -g @qwen-code/qwen-code@0.26.3
qwen
```

Jarvis Box 使用 Qwen 的非交互执行与结构化输出。模型、供应商、认证和可选 `--model`/`--auth-type` 由 Qwen 原生配置和 scope prefix args 管理。

Docker 使用含 `qwen` 的 release image，先以 `jarvis-box tools status` 确认。image 提供固定基线，显式 `jarvis-box tools update` 管理在线更新；不含 CLI 的 image 用[客户派生镜像](custom-docker-image.md)添加。Qwen 登录保存在 deployment 的持久 Agent HOME：

```bash
scripts/deploy-production.sh /absolute/deployment-home shell
qwen
```

Qwen 不参加 Host portable-auth snapshot。它的用户技能目录为 `~/.qwen/skills`、项目技能目录为 `.qwen/skills`；客户 Runtime Foundation 在已验证 discovery root 交付客户技能。切换前必须用真实 Qwen 调用验证发现，不以目录存在替代。

## 自定义 Runtime Agent

`JARVIS_RUNTIME_AGENT_ADAPTERS` 在 canonical runtime env 保存版本化 JSON。当前 `version: 2` 的 `agents` 是完整目录，既包括发行预设也包括客户条目；已发布的旧格式由 release migration 兼容读取。新增 custom agent 时，把条目加入仍要保留的完整 `agents` 数组。

最小的单 custom-agent 示例：

```dotenv
JARVIS_RUNTIME_AGENT_ADAPTERS='{"version":2,"agents":[{"name":"custom-agent","command":"/opt/bin/custom-agent","driver":"exec-v1","argv":{"start":["{prefix_args}","--prompt={prompt}"],"smoke":["--prompt={prompt}"]},"env_keys":["CUSTOM_AGENT_API_KEY"],"output":{"protocol":"text"},"capabilities":{}}]}'
```

配置后必须检查并 smoke：

```bash
jarvis-box agent list
jarvis-box agent smoke custom-agent
jarvis-box agent set custom-agent
```

### Descriptor 字段

| 字段 | 合同 |
| --- | --- |
| `name` | 唯一，小写英文字母开头，只含小写字母、数字、连字符，最多 64 字符；与 aliases 同一命名空间。 |
| `command` | executable 名称或绝对路径；安装/登录由该 CLI 自己的部署流程负责。 |
| `env_key` | 可选命令覆盖变量，必须 `_CMD` 结尾且唯一；默认由 name 转大写并把 `-` 改 `_` 后加 `_CMD`。 |
| `driver` | 所有条目必须为 `exec-v1`。 |
| `argv` | `start` 必填；可有 `resume`、`compact`、`plain_start`、`plain_resume`、`smoke`。每个 template 恰好一个 `{prompt}`。 |
| `output` | 固定版本化输出协议；未知协议拒绝。 |
| `session` / `resume` | 原生会话 ID、格式、选择和恢复合同；没有完整实现不要声明。 |
| `recap` | 可选的原生任务标题证据协议。省略即不授权读取原生标题；只有发行版已声明并实现的版本化 protocol 可以填写。它不选择生成 Agent，也不启动私有标题进程。 |
| `model` / `resources` | 模型环境、原生配置与只读账户诊断路由元数据。 |
| `env_defaults` | 已声明 env 的字面默认值；显式值（含空值）优先，不能放 credential。 |
| `env_keys` | CLI 的模型/认证键；不得声明 Jarvis、Provider、Connector 或进程启动保留键。 |
| `aliases` / `skills_dir` | 可选唯一 alias；skills directory 只是元数据，不会触发安装或同步。 |
| `capabilities` | 由 protocol/operation 校验出的能力投影；省略不授予权限，矛盾声明被拒绝。 |

Template 直接形成进程参数，不经 Shell。`{prefix_args}` 必须独占一个数组元素；其余可用标量为 `{cwd}`、`{workspace}`、`{native_session_id}`、`{resume_session_id}`、`{output_last_message}`、`{resolved_model}`、`{max_autopilot_continues}`。推荐 `--prompt={prompt}`，或将裸 `{prompt}` 放在 CLI `--` 后，避免短横线提示词被解释为选项。可选片段形如 `{"optional":"cwd","args":["--cwd","{cwd}"]}`；条件仅支持 `cwd`、`workspace`、`native-session`、`output-last-message`、`autopilot`、`model`、`structured-output`，不执行表达式。

<a id="模型路由与计费额度"></a>

### 输出、模型和自动回退

`text` 以进程退出结果决定成功/失败。`stream-json-v1` 只接受顶层 `type=result` 与 `is_error` 的终态；正文中引用 JSON 没有终态权限。`jsonl-v1` 逐行读取 JSON，`json-v1` 在 EOF 读取一个对象。映射仅支持固定 JSON Pointer、顶层事件类型、存在/缺失条件及类型一致的标量比较；`null` 不等于缺失，数字不做浮点转换。非法 UTF-8、格式错误或不完整数据都不能证明成功。

结果默认采用最后一个匹配消息；原生协议只有增量文本时可设置 `jsonl.append_results=true`。`jsonl.messages` 可投影 `assistant`、`think`、`tool`、`error`、`runtime`、`user`、`system` 消息。每个 Run 固定自己的解析配置，之后改删 Agent 配置不影响历史 Run。

发起或续接工单命令时，Agent 将评论正文写入 `JARVIS_COMMAND_COMMENT_FILE`。Jarvis Box 为工单命令留空 `{output_last_message}`。自定义模板可将依赖该占位符的参数放入 `output-last-message` 可选片段，以便在路径为空时省略整组选项。启用自动回写时，Jarvis Box 校验评论文件后发布到原工单。缺少有效文件时，按工单命令的结果校验和恢复流程处理。

Jarvis Box 只执行一次性命令、读取输出并等待退出；它不实现 ACP、MSP 或交互控制协议。只有交互入口、或一次性入口缺少任务工具的 CLI 不能作为完整 Runtime Agent。

`JARVIS_RUNTIME_AGENT_FALLBACK_ORDER` 是自动回退的完整候选顺序；空值表示没有自动切换。每次切换前，系统必须确认候选实际计费账户的可用余额、在同一配置下做一次真实模型 probe，并在 probe 后再次核对余额、配置和原 Task。任何余额未知/不足、CLI/模型 probe 失败或配置变化都禁止自动接手；直接由用户选择 Agent 不要求余额诊断可用。

`model.env_keys` 按顺序读原生模型标识；`option_syntax=model-flags-v1` 时显式 `--model` 优先。CLI 内部模型标识与供应商请求名不同时，可用 `model.wire_env_keys` 说明实际 credential/model 路由。Status 只根据所选 Agent 的真实模型、服务地址和 credential source 做只读额度诊断；无法安全识别时显示未知或不支持，不影响 Agent 执行，也不使用其他 Agent 的 key 代查。

<a id="会话续接"></a>
<a id="运行结果与取消"></a>

## 会话、失败与取消

会话存在不代表这次输入已经被 Agent 接收。`codex-exec-json-v1` 支持输入接收确认；未知回执拒绝重放。其他协议按其已发布 Continue 规则。Continue 复制通过 source Run identity 校验的未接收 IM 附件，并保留本次回复目标和产物目录；不能从日志或旧聊天补造缺失输入。

恢复先校验 exact Run、Agent、AgentConversation 与 protocol 私有 receipt，再执行声明的原生 load/resume。Codex、Claude、Copilot 保留已有记录/UUID 合同；无法得到可靠 handle 时，在同一 Task 中启动新会话，保留 workspace、产物、本次指令与回复目标，但不假造旧聊天上下文。Gemini、Qwen、OpenCode、OpenClaw、Hermes、Kiro、TRAE、Muse、Devin、ZeroClaw 当前预设不支持原生上下文续接。

当前执行是无人值守的。服务接受默认和 `unattended` ApprovalPolicy，在启动前拒绝 `interactive` 或未知值。普通 Agent 执行失败由原 Agent 有界自动续跑，与模型受限恢复共用最多五次持久预算。Codex 明确拒绝音频输入时，该 Run 以失败结束且不会自动续跑。用户可在原任务上选择能处理所需输入的 Agent，带上本次要求显式续接。完整规则见[执行模型](execution-model.md#agent-中断的有界自动-continue)。

成功退出码不会覆盖输出协议中的可信终态失败。取消、超时、强杀或产物写入失败也不会报为成功。

取消只终止当前 Agent 与已确认子进程。服务冻结启动身份和派生关系，并在发送信号时重新验证；不会因同名命令、工作目录或单独数字 PID 扩大终止范围。不能确认归属或停止结果时保留错误，不宣称已安全停止。

<a id="任务摘要标题"></a>

## 任务摘要标题

任务稳定结算后，Jarvis Box 可以异步补充一个短标题，便于任务列表识别工作主题。这是展示元数据，不改变源 Task/Run 的成功、失败、恢复、交付或原生会话续接结果；标题生成失败、超时或不可用也不会重跑源任务。

系统先尝试读取该 Task 的 exact Run 已冻结的原生标题证据。当前只有 Claude 的显式 `custom-title` 记录属于这项证据；不会采用 AI 自动标题、会话列表排序、`threads.title`、消息预览、会话摘要、首条提示词或任意最近会话。读取会使用启动时写入回执的配置目录和精确 transcript 路径，不能扫描 `$HOME`、在多个 project 中挑选同一 session，或按文件修改时间选择会话。

首次 Run 可以使用其 session 中最新的显式 `custom-title`；有意清空标题时，不会恢复更早的名称。Continue 只会采用标题记录自身时间不早于该 Run 启动时间的内容；没有这个时间证明时，旧会话标题不会被归属给新的 Run。原生标题先脱敏，过长、包含控制字符、只是内部编号或无法验证的名称不会采用。

没有可用原生标题时，系统会为该稳定源 Run 创建或复用一个确定性关联的普通 `task-recap` Task。该 Task 在开始时按现有 lane 规则解析 `JARVIS_RUNTIME_AGENT_SCOPE_TASK_RECAP`、模型和启动参数。未设置覆盖时继承 `JARVIS_RUNTIME_AGENT`。可使用 `jarvis-box agent set --scope task-recap <agent>` 或状态页“工作方式”的“任务概括”设置。变更仅影响后续概括。

`task-recap` 是零源工作区的普通 lane Task。它从源 Task 已封存并脱敏的 `RecapInput` 取得标题材料，以普通 Agent Run 的版本化 JSON 最终答复返回候选标题；不会恢复源 Agent 会话或使用源工作区。生成沿用该 lane 所选 Agent 的模型、参数、认证和运行权限。Agent 不可用或生成失败时，系统保留已有可读标题。概括任务使用封存材料，用户可在原业务任务继续发送新指令。

源 Task 只接受与完整 Source Run 和 `RecapInput` 摘要匹配的关联 Analysis Run 标题结果；迟到、取消、无效 JSON 或失败的分析 Run 不会覆盖后继标题。用量沿关联普通 Task/Run 的既有投影口径归属，不进入源 Run；没有可核验 token/cost 事实时保持 unknown，不伪称为零或已知。升级、服务启动、页面读取和历史浏览不补造关联 Task，也不产生历史收费调用。

<a id="delivery-metrics"></a>

Delivery Metrics 使用独立的 `delivery-metrics` scope（如已配置）；它的选择、恢复和历史统计规则见[Delivery Metrics 历史起点](delivery-metrics.md)。该 lane 不创建另一套 Agent 生命周期。

<a id="skill-发现"></a>

## Skill 与 IM 边界

image 自带通用 `skill-creator`，并链接到 Codex、Claude、Qwen 的个人技能目录。create-jarvis 不安装进正式运行时；客户 Jarvis skill 由 Runtime Foundation 在持久 Agent HOME 中安装/更新，entrypoint 不覆盖 identity 自有的 skills。onboarding 必须使用真实 Agent 调用验证发现。

uv-im-connector 拥有 provider-native IM secret 和长连接。Jarvis Box 仅通过 connector protocol/token 使用它，且不会把 connector secret 传给 Agent。已准入群聊 Run 只会得到读取本轮原群历史范围的专属 capability；它不是平台 token、Task 控制权或通用配置，且不进入 prompt、准备快照或公开状态。Agent 主动输出自身环境仍可能进入其私有原始执行记录。
