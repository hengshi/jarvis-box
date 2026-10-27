# IM 与 uv-im-connector

Jarvis Box 不直接持有 IM provider 的原生 credential。IM provider 由 `uv-im-connector` 连接，Jarvis Box 只消费统一事件并通过 connector 写回消息。

## 支持级别

- Jarvis Box 认证 adapter 候选：企业微信（WeCom）、飞书/Lark、钉钉（DingTalk）。某个 adapter 只有在对应版本取得 provider-native ingress → Jarvis core → provider-native delivery 的确定性阻塞 E2E 证据后，才可对外宣称为已认证。
- 统一协议支持：任何与当前锁定 `uv-im-connector` protocol 兼容的 provider 都可以接入 ChatBridge core。
- Connector capability：锁定版本二进制中存在但未列入认证 adapter 的 provider，只表示 connector 具备实现；在补齐 Jarvis Box 双向闭环、部署和脱敏 evidence 前，不宣称为 Jarvis Box 认证支持。

某套部署的 `UV_IM_PROVIDERS` 是认证集合的运行时子集。provider credential 出现在 `connector.env` 也不自动扩大产品支持边界。

## 为什么 IM 不需要暴露 Jarvis Box 公网 IP

很多 IM provider 使用长连接、WebSocket、事件订阅或平台托管 callback。`uv-im-connector` 负责与这些 provider 建立连接、维护认证、接收消息、下载附件和发送回复。

Jarvis Box 看到的是统一后的事件：

```text
provider + connector + conversation + sender + message + attachments
```

其中 conversation 和 sender 都保留 provider-native 稳定 ID，并可携带 `channel.name`、`user.name` / `user.display_name` 展示快照。Jarvis Box 把名称写入任务运行上下文供 Status 展示和搜索，但 Target 绑定、ACL、排重与回复路由始终只使用稳定 ID。名称查询失败或旧事件没有名称时，任务仍正常执行，Status 回退到带 provider 前缀的 ID。

飞书/Lark 名称由 `uv-im-connector` 使用应用 OpenAPI 做短时、可失败的缓存查询。企业微信 AI Bot 长连接只返回 `userid` / `chatid`，Bot secret 不能查询企业通讯录或群名；需要名称的部署应在 connector 侧配置显式 ID→名称映射，Jarvis Box 不直接持有企业微信目录凭据。

因此 Jarvis Box 不需要知道企业微信或飞书的原生 token，也不需要为每个 IM provider 实现一套 webhook parser。

## 配置 Jarvis Box

以下值写入当前实例实际生效的运行时环境文件：Native 由 `JARVIS_ENV_FILE` 指定，默认 `$JARVIS_RUNTIME_ROOT/envs/.env.jarvis-box`；Docker 使用 deployment home 管理的 `runtime.env`。不要在 `deployment.env` 重复声明 profile：

```bash
JARVIS_CONNECTOR_PROFILE=uvim
JARVIS_UV_IM_CONNECTOR_URL=http://127.0.0.1:19090
JARVIS_UV_IM_CONNECTOR_TOKEN=<optional-token>
JARVIS_CHAT_ALLOWED_USERS=wecom:wecom:alice,lark:lark:bob
JARVIS_CHAT_ALLOWED_CONVERSATIONS=wecom:wecom:room-1
```

这里的三段式只用于入站 ACL 主体身份：`provider:connector:subject`。connector 不是任意渠道名，
而是 UVIM `/v1/meta` 中该 provider 实际声明的实例；例如默认企业微信实例可能正好是
`wecom:wecom`。主动通知配置不要求把这两个名字重复书写。

`JARVIS_CONNECTOR_PROFILE` 是 IM connector 的唯一启用开关。仅保留 URL 不会启动 ChatBridge connector client；把 profile 设为空并通过正式部署脚本重建，会同时移除旧 connector service。

它只决定 IM：webhook 派发不看 profile，GitLab、GitHub、Jira 各自由 `GITLAB_HOST`+`GITLAB_PROJECTS`、`GITHUB_REPOSITORIES`、`JIRA_BASE_URL`+`JIRA_PROJECTS` 启用，同一台盒子可以既聊天又接 webhook。没有配置的入口保持未配置（HTTP 501），与 `/health` 的 `providers.*.configured` 同一判据。

`JARVIS_BRAND_NAME` 可选，用来替换客户看到的助手显示名（默认 `Jarvis`）。它同时作用于 IM 回执与完成通知、发给 Agent 的提示词、写回 MR/PR 的评论和 Status 页面的助手文案；定时认知任务保留固定产品名称：JARVIS 记忆整理、JARVIS 每日复盘、JARVIS 经验积累。二进制名、镜像、systemd/launchd 单元、安装路径和所有 `JARVIS_*` 变量名不随之改变。改显示名后，群聊里 `@` 的对象也要和 `JARVIS_MENTION_NAMES`（默认 `jarvis,jarvis-box`）保持一致。这个值会被写进 Status 页面的 JavaScript 字符串和 HTML 标记，也会拼进下面几条默认文案的格式串，所以不能包含 `'` `"` `` ` `` `\` `<` `>` `&` `%` 或控制字符；含这些字符时服务启动失败，并在错误里指出是哪个字符。

以下三条模板可选，用来替换 IM 文案，留空即使用默认值：

| 变量 | 默认 | `%s` 依次替换为 |
| --- | --- | --- |
| `JARVIS_CHAT_LAUNCH_REPLY_TEMPLATE` | `<助手名> 已开始处理。run_id: %s` | run id |
| `JARVIS_CHAT_QUEUED_REPLY_TEMPLATE` | `<助手名> 已接收任务，%s。task_id: %s` | 等待原因、task id |
| `JARVIS_CHAT_HELP_REPLY_TEMPLATE` | `<助手名> 未被唤起。请在群聊中 @<助手名>，或用 \`<触发词> ...\` / \`/start ...\` 开始。` | 助手显示名、触发词 |

模板中的 `%s` 数量必须符合上表。缺少或多写 `%s`、使用其他格式符都会导致启动失败，并指出配置变量。字面量 `%` 写成 `%%`。

IM 任务开始处理或进入等待时发送回执，完成后回复最终结果。运行中的进展可在 Status 页面查看。

`JARVIS_COMMAND_NOTIFY_COMPLETED_TEMPLATE` 不同：它是纯文本标题，不做格式替换，也不做 `%s` 校验，用来替换任务完成通知的首行（默认 `<助手名> 任务已完成`）。

启动后 Jarvis Box 会读取 connector 的 `GET /v1/meta`，要求 `service=uv-im-connector` 且 protocol version 兼容。

网络断线后，connector 在进程内对失败的 provider runner 独立持续重试，采用从 1 秒开始、最多 1 分钟并带抖动的指数退避；其他 provider 和 HTTP API 保持运行。WeCom、Lark 及 DingTalk Stream 启动失败使用同一监督入口；DingTalk 已建立 Stream 后的重连由 SDK 负责，webhook provider 继续通过 HTTP 接收事件。`/health` 表示进程存活，各 provider 状态通过 `/v1/meta` 检查。

Jarvis Box 到 connector 的连接同样持续重试，长时间断线只报告降级，不会退出主进程请求 supervisor 重启。进程崩溃或被杀仍需要 service manager 拉起；若 launchd 已抑制 KeepAlive，操作员应核实 service identity 后执行一次 `launchctl kickstart`。进程内重连不能恢复已停止的进程。

## 会话语义

| 消息 | 行为 |
| --- | --- |
| `/start <prompt>` | Start：创建新 Task、AgentConversation 和首个 Run。 |
| 空 `/start` | 返回用法，不改变当前 Target binding。 |
| 未知 `/命令` | 在原消息回复支持的用法，不创建 Task/Run，不交给 Agent 执行。群聊仍遵守唤起要求。 |
| 首条普通消息 | 当前 Target 尚无 Task 时执行 Start。 |
| 后续普通消息 | Continue：优先继续引用消息所属 Task，否则继续 Target 的默认 Task。 |
| `/cancel` | Cancel：取消引用消息所属 Task；未引用消息时取消默认 Task。 |
| `/cancel <run-id>` | Cancel：只取消当前 Target 中拥有指定 Run 的 Task。 |
| `/cancel all` | Cancel：取消当前 Target 的所有非终态 Task。 |

Target 绑定按 provider、connector 和 conversation 组合隔离。同一个原生 conversation id 出现在不同 workspace 或 connector 中时，不会互相授权。Binding 只保存无明确目标时使用的默认 Task id/dir，不缓存 Run id、Run 状态或 runtime session。

同时带有多个引用时，按 parent、root、thread 顺序查找本会话的消息记录；缺省或未命中时查下一项，重复消息 id 只查一次。命中后的身份冲突必须拒绝。引用续话不会把该 Task 设为默认；显式 `/cancel <run-id>` 优先使用指定 Run，不改用引用或默认 Task。

同一原生控制消息不会因重投再次取消任务、清空默认选择或重复回复。控制消息的记录不授予 Task 引用，也不表示操作完成或回执已送达；若操作途中进程中断，请查看任务当前状态后发送新的命令，原消息重投不会重新选择后来创建的任务。

发送人和会话必须先通过允许清单校验。同一群内已授权成员共享该会话的任务引用；不会因为任务由另一名群成员发起就额外拒绝。普通消息引用另一会话的消息或未知消息时，不能选中外部任务或借用其回复凭据；未命中本会话引用记录的合法普通输入仍继续本会话默认任务，没有默认任务时创建新任务。已经找到的绑定若身份不符则明确拒绝，不回退默认任务。

`/cancel` 携带引用时必须找到本会话中该引用所属的任务；找不到时说明原因，不取消默认任务。只有没有引用的 `/cancel` 才使用默认任务。`/cancel <run-id>` 找不到本会话对应 Run 时同样不回退。

`/start` 不停止旧 Task。一个单聊、群聊或频道可以并发运行多个 Task；每个 Run 保存自己的原始 message ref，完成后通过该 ref 回复，因此结果可以乱序到达而不会失去归属。`uv-im-connector` 提供 parent/root message id 时，ChatBridge 还会把每个入站消息和机器人回复映射回所属 Task。解析优先级是显式 Run id、引用消息、默认 Task。

Run id 是 compact canonical id，例如 `r_4P8X6C2N7J5K`。来源 provider、conversation、message、时间、Task 和 sequence 保存在结构化字段中，不编码进 id。

如果普通消息到达时已有 active Run，ChatBridge 在 Continue 内部先解决旧 Run ownership；无法证明旧 owner 已停止时请求 fail closed。Lost-Run recovery 由内部进程证据链收敛旧 Run，不伪装成无输入的 Continue。跨 agent 时不复制 native session id。

绑定的 Task 处于 Lost-Run recovery 时，普通消息照样是 Continue：ChatBridge 取回 TaskService 签发的 sealed recovery 计划，在同一条 Task、同一个 Agent、保留原工作区的前提下起新 Run，并先回一句「检测到当前 Run 已失联，正在同一 Task 中继续。」。这条 Run 的指令仍是用户这句话——sealed 计划给的是授权与身份，不是给 Agent 的措辞。

拒绝必须说出来，沉默不是答案：Continue 落在不允许继续的状态上时回「当前 Task 状态不允许继续；可从 Status 页面继续或取消。」；落在起飞、准入、收尾这些窗口期（Task 正在动，几秒后自己落地）回「当前 Task 正在启动或收尾，这句话没有被接收；请稍后重发。」——窗口期不能指用户去 Status 页面，那等于叫他取消一条正在正常收尾的 Task；`/cancel` 没取消掉时回「Task 取消失败，最近一次 run_id: <run-id>」。`/cancel all` 例外——它回一条汇总（「已取消 N 个 Task：…；M 个取消失败：…」），不逐 Task 回执。

创建任务或续跑被授权校验拒绝时，Jarvis 会通过原消息的回复通道说明原因。未激活时回复「Jarvis 尚未激活，请联系管理员激活后使用。」；授权停用、租约过期或其他授权问题也会提示联系管理员处理。入口授权拒绝不分配 Task/Run；若准备期间授权失效，会保留带拒绝原因的失败 Run，但不启动 Agent。内部路径和原始上游响应不发给聊天用户。

已取消 Task 不可 Continue；后续普通消息会提示使用 `/start <prompt>` 创建新 Task。Agent Run 成功但回复未送达时，Run 仍保持 `succeeded`；IM Task 从该 exact Run 的 typed effect receipt 投影 delivery 结果。definite failed/retryable delivery 显示为 `needs-attention`，Status Continue 使用 sealed writeback strategy 重试同一 Run 的 final reply effect，不创建新 Run、不重放公开 `reply-error.json`。`unknown` 表示结果不可证明，不自动重发；`/cancel` 可以明确放弃剩余 delivery。

回复凭据在运行期间自然过期时不延长期限；只有 connector 声明主动发送能力且原目标仍可信，才向该目标发送。目标或能力预检在发送接口调用前失败时，结果明确为 `failed/not-attempted`，保留成功 Run 和原结果；修复条件后可在原 Run 重试交付。已发出请求而结果不明的故障仍为 `unknown`，不能据此安全重发。

原回复权限证明缺失或损坏时拒绝发送，不从公开任务信息补造权限。恢复原证明后，可以显式 Continue 交付同一成功 Run 的原结果；已有版本将这类发送前失败标为不可重试的历史记录也支持恢复，不改写旧交付事实、不自动发送或重跑 Agent。

connector 未声明附件上传能力，或未声明支持所需附件类型时，属于发送前的能力预检失败。此时未尝试上传或发送附件，不要求用户确认是否收到；恢复能力后通过 Continue 重试原 Run 的交付，不重新运行 Agent。

`POST /v1/message.create` 的外层 HTTP 502 只说明 `uv-im-connector` 没有完成发送，不能据此判断是哪个 provider 返回了 502。Jarvis Box 只消费 response 的 `failure`；`failure.http_status` 才是上游 provider HTTP 状态，`provider_code` 是 provider 业务码。两者缺失时仍有 `category`、`retryable` 和 `delivery_state`，无需读取 connector 日志来决定生命周期。

附件上传失败也保留 connector 对是否发送及能否重试的明确判断。确定未发送且允许重试时，只重试原 Run 的交付；不会因错误包装丢失该判断而要求用户裁定是否收到。交付失败或未知时，用户仍可取消 Task，表示放弃剩余交付，不代表确认送达。

送达确认支持「全部收到」「全部未收到」，以及「未收到的附件：a.txt、b.txt」或「只缺a.txt」这样的明确名单。具名选择要求原内容仍与该 Run 的私有交付回执一致、文件名在完整集合中唯一、名单为尚未确认文件的非空子集；只补名单中的文件，其余按原用户明确的“只缺”裁定记为已收到，不新增 Run 或 Agent。未知、重名、不匹配或包含已有确认文件的名单会向原用户澄清并保持等待；普通新指令仍按 Continue 处理。补发前内容变化时不发送，恢复原字节后可在同一 Run 重试，已有确认集合保持。已有原交付回执的文件暂时缺失或不可读时，明确记录未发送；恢复原文件及读取权限后，可以在原 Run 重试交付，不重新执行 Agent，也不重问是否收到。首次发送前文件暂时不可读时，只有系统已保存原回复文本和该 Run 的私有预检凭据，才可在修复文件后通过同一操作交付；系统会重新核实原文本、合法文件和原目标，不把尚未读取的附件当作已封存内容。

## 附件

发出的文件受当前 IM 渠道的大小和图片尺寸限制。超限时 Jarvis 保留原文件，在原会话说明文件名、实际大小或尺寸及渠道限制，并询问可访问的云盘、对象存储等交付位置；该 Task 等待用户回复，管理员无需代为处理。

Agent 在回复中链接同一 Task 的公开 `artifacts/` 文件时，Jarvis 会将该文件作为实际附件交付，不要求用户访问主机本地路径。相对链接以该 Run 的 `reply.md` 所在目录解析。符号链接逃逸、私有目录和其他 Task 的文件不获得发送权限。

附件发送超时而无法确认送达时，Jarvis 在原会话询问是否全部收到，不直接重复发送附件。用户明确回复“全部收到”后完成原 Task；明确回复“全部没收到”后只重试原 Run 尚未确认送达的附件，不重新运行 Agent。已处理的送达确认不再回复“已忽略该消息”。只缺部分文件时按上述具名格式回复；符合原回执的名单只重试列出的缺失文件，其余文件按原用户裁定保留，不将名单交给 Agent 重跑。

送达确认仅接受发起该次 Run 的原用户；同群另一名已授权成员可以正常引用和续话，但不能替原用户裁定是否收到。身份依据该 Run 的私有记录校验，不能用群目标或 Task 首创者代替。历史记录未保存且无法可靠恢复发送者时，原结果、文件和普通续话仍保留；可在 Status 核实接收结果后记录送达裁定，在原 Run 收尾或重试，不要求重跑 Agent。等待状态仍属于原用户，Status 裁定是可选补救。

送达确认已处理且该次交付完成后，迟到的明确确认即使带有新的消息ID，也只回复已处理说明，不再执行任务、追加Run或补发文件。具名确认须匹配原交付中可以核实的附件名，“只缺最后一步，请补充计算过程”等新的工作要求仍正常续话。原Task、Run和交付历史保持；这不重新授予送达裁定或补发权限。显式`/start`或`/new`按对应命令处理。

文件类消息由 connector 下载或代理。Jarvis Box 在 Run 启动前把附件保存到该 Run 的 `attachments/` 目录，并把本地路径注入给 agent。

每次聊天执行都向 Agent 明确提供本条消息已准备的附件路径及文件回传方式；续聊和等待恢复使用当前 Run 的资料。Agent 不需要遍历用户主目录、其他任务或源码仓库寻找附件和发送办法。附件不可读时应明确说明，不能用找到的同名文件替代用户上传内容。

单聊与群聊共用附件处理路径。Jarvis Box 不额外限制入站附件数量、单文件大小或单条消息的附件总大小；下载流式写入磁盘，所有附件记录和本地路径都交给 Agent。默认 connector HTTP client 不设置传输总超时，下载响应调用方 context 的取消或 deadline。IM 平台自身的限制、访问权限以及部署主机的可用磁盘空间仍然适用。

这些内容不得进入 public artifact：

- provider 下载 URL；
- provider 文件密钥；
- connector `internal://` 资源 URL；
- raw IM payload；
- reply token；
- provider-native credential。

## 完成通知

外部平台触发的 `jarvis-command` 任务，以及显式启用完成通知的 `post-check` 任务，在任务收尾后向触发人发送 IM 单聊提醒。提醒包含运行状态、项目、目标链接和 Run ID；发送提醒不改变原平台的评论写回结果。本地手动任务、IM 聊天任务、机器人触发以及显式关闭通知的任务不会产生这条额外提醒。

```bash
JARVIS_NOTIFY_PROVIDER=wecom
JARVIS_COMMAND_NOTIFY_RECIPIENT_MODE=trigger_author_user_id
```

`JARVIS_COMMAND_NOTIFY_ENABLED` 默认 `true`，设为 `false` 可关闭完成提醒。触发人的平台用户名直接用作 IM 收件人 ID，因此两端标识必须对应；`trigger_author` 与 `trigger_author_user_id` 都不进行通讯录转换。Jarvis Box 不自动同步通讯录。

收件人与通知内容来源在 Run 启动前固定。发送前通过 TaskService 校验完整 Task/Run 身份和终态归属，成功后保存私有投递回执。重复回调不会重复发送；发送中断或响应丢失时保留结果未知，不自动重发。升级前启动、缺少通知来源记录的历史 Run 不补发提醒。

`JARVIS_NOTIFY_PROVIDER` 是所有主动通知共享的 provider，例如 `wecom` 或 `lark`。
Jarvis Box 启动时会读取 UVIM 的 `/v1/meta`：当该 provider 只有一个实例时自动绑定；只有
同一 provider 配置了多个实例时，才需要用 `JARVIS_NOTIFY_CONNECTOR` 指定实例。provider 与
connector 必须是 UVIM 实际声明的一对，`wecom:lark` 这类拼接会被拒绝，不能跨 provider 组合。

旧的 `JARVIS_NOTIFY_CHANNEL=provider:connector`、`JARVIS_COMMAND_NOTIFY_CHANNEL` 和
`JARVIS_COMMAND_NOTIFY_CONNECTOR` 只作为迁移期 fallback 保留，并在 Status 中标记为 legacy。
新旧配置同时存在时 provider 必须一致，否则 Jarvis Box 拒绝启动，避免把消息发到错误渠道。

## JARVIS 经验积累周报

`cognitive-evolution` Task 始终生成本地周报。0.3 尚未接入周报主动通知，配置通知目标也不会发送；`memory-consolidation` 和 `daily-reflection` 不发送通知。以下配置保留为目标合同：

```bash
JARVIS_NOTIFY_PROVIDER=wecom
JARVIS_COGNITIVE_EVOLUTION_NOTIFY_TARGET=group:<provider-native-conversation-id>
```

目标也可以是 `direct:<provider-native-user-id>`。当前版本只保留周报 artifact。

从 0.2 升级到 0.3 后，普通消息和引用旧消息继续接续原 Task，不要求用户发送 `/new`。运行时只为具有已登记 0.2 Task 来源的旧绑定补齐 TaskRef：原目录、会话 Target 和绑定创建时间必须与登记事实相符，旧 Run 还须通过精确的 Run ID、sequence 和创建事件验证。可验证的 Codex 原生会话继续使用原会话；新 Run 由 TaskService 正常创建。补齐绑定保留原会话选择与引用关系，不重新处理旧消息。

旧版本在首次 Task 登记前保存的绑定，必须与首个已验证 Run 的原始消息绑定具有相同 Task、目录和精确创建时间，才允许接续。缺少登记来源、部分缺失的现代身份、目录或 Target 冲突，以及无法通过该原始消息证明的提前绑定仍会拒绝自动接续，防止误接被删除重建的任务。`/new` 用于用户主动开启新任务，不是正常升级的必需操作。

原 Task 已被历史清理移除时，普通消息按新 Task 处理，无需先发送 `/new`；当前消息、附件及回复目标交给新 Task，不会恢复已移除 Task 的上下文。原 Task 仍存在但登记身份、目录或 Target 不匹配时，继续拒绝自动接续。
