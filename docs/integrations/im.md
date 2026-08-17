# IM 与 uv-im-connector

Jarvis Box 不直接持有 IM provider 的原生 credential。IM provider 由 `uv-im-connector` 连接，Jarvis Box 只消费统一事件并通过 connector 写回消息。

## 支持级别

- Jarvis Box 认证 adapter：企业微信（WeCom）、飞书/Lark、钉钉（DingTalk）。每个认证 adapter 都有 provider-native ingress → Jarvis core → provider-native writeback 的确定性阻塞 E2E。
- 统一协议支持：任何与当前锁定 `uv-im-connector` protocol 兼容的 provider 都可以接入 ChatBridge core。
- Connector capability：锁定版本二进制中存在但未列入认证 adapter 的 provider，只表示 connector 具备实现；在补齐 Jarvis Box 双向闭环、部署和脱敏 evidence 前，不宣称为 Jarvis Box 认证支持。

某套部署的 `UV_IM_PROVIDERS` 是认证集合的运行时子集。provider credential 出现在 `connector.env` 也不自动扩大产品支持边界。

## 为什么 IM 不需要暴露 Jarvis Box 公网 IP

很多 IM provider 使用长连接、WebSocket、事件订阅或平台托管 callback。`uv-im-connector` 负责与这些 provider 建立连接、维护认证、接收消息、下载附件和发送回复。

Jarvis Box 看到的是统一后的事件：

```text
provider + connector + conversation + sender + message + attachments
```

因此 Jarvis Box 不需要知道企业微信或飞书的原生 token，也不需要为每个 IM provider 实现一套 webhook parser。

## 配置 Jarvis Box

以下值写入 canonical `runtime.env`；不要在 `deployment.env` 重复声明 profile：

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

`JARVIS_CONNECTOR_PROFILE` 是唯一启用开关。仅保留 URL 不会启动 ChatBridge connector client；把 profile 设为空并通过正式部署脚本重建，会同时移除旧 connector service。

启动后 Jarvis Box 会读取 connector 的 `GET /v1/meta`，要求 `service=uv-im-connector` 且 protocol version 兼容。

## 会话语义

| 消息 | 行为 |
| --- | --- |
| `/start <prompt>` | Start：创建新 Task、AgentConversation 和首个 Run。 |
| 空 `/start` | 返回用法，不改变当前 Target binding。 |
| 首条普通消息 | 当前 Target 尚无 Task 时执行 Start。 |
| 后续普通消息 | Continue：优先继续引用消息所属 Task，否则继续 Target 的默认 Task。 |
| `/cancel` | Cancel：取消引用消息所属 Task；未引用消息时取消默认 Task。 |
| `/cancel <run-id>` | Cancel：只取消当前 Target 中拥有指定 Run 的 Task。 |
| `/cancel all` | Cancel：取消当前 Target 的所有非终态 Task。 |

Target 绑定按 provider、connector 和 conversation 组合隔离。同一个原生 conversation id 出现在不同 workspace 或 connector 中时，不会互相授权。Binding 只保存无明确目标时使用的默认 Task id/dir，不缓存 Run id、Run 状态或 runtime session。

`/start` 不停止旧 Task。一个单聊、群聊或频道可以并发运行多个 Task；每个 Run 保存自己的原始 message ref，完成后通过该 ref 回复，因此结果可以乱序到达而不会失去归属。`uv-im-connector` 提供 parent/root message id 时，ChatBridge 还会把每个入站消息和机器人回复映射回所属 Task。解析优先级是显式 Run id、引用消息、默认 Task。

Run id 是 compact canonical id，例如 `r_4P8X6C2N7J5K`。来源 provider、conversation、message、时间、Task 和 sequence 保存在结构化字段中，不编码进 id。

如果普通消息到达时已有 active Run，ChatBridge 在 Continue 内部先解决旧 Run ownership；`recovery-required` 时自动选择 recovery strategy。跨 agent 时不复制 native session id。

已取消 Task 不可 Continue；后续普通消息会提示使用 `/start <prompt>` 创建新 Task。完成但回复仍未送达的 IM Task 可以用 `/cancel` 明确放弃剩余 delivery。

## 附件

文件类消息由 connector 下载或代理。Jarvis Box 在 Run 启动前把附件保存到该 Run 的 `attachments/` 目录，并把本地路径注入给 agent。

这些内容不得进入 public artifact：

- provider 下载 URL；
- provider 文件密钥；
- connector `internal://` 资源 URL；
- raw IM payload；
- reply token；
- provider-native credential。

## 完成通知

GitLab、GitHub 或 Jira 触发的任务完成后，可以通过 IM 通知触发人：

```bash
JARVIS_NOTIFY_PROVIDER=wecom
JARVIS_COMMAND_NOTIFY_RECIPIENT_MODE=trigger_author_user_id
```

只有当 provider author 与 IM direct-message user id 有明确映射时，才使用 `trigger_author_user_id`。Jarvis Box 不自动同步通讯录。

`JARVIS_NOTIFY_PROVIDER` 是所有主动通知共享的 provider，例如 `wecom` 或 `lark`。
Jarvis Box 启动时会读取 UVIM 的 `/v1/meta`：当该 provider 只有一个实例时自动绑定；只有
同一 provider 配置了多个实例时，才需要用 `JARVIS_NOTIFY_CONNECTOR` 指定实例。provider 与
connector 必须是 UVIM 实际声明的一对，`wecom:lark` 这类拼接会被拒绝，不能跨 provider 组合。

旧的 `JARVIS_NOTIFY_CHANNEL=provider:connector`、`JARVIS_COMMAND_NOTIFY_CHANNEL` 和
`JARVIS_COMMAND_NOTIFY_CONNECTOR` 只作为迁移期 fallback 保留，并在 Status 中标记为 legacy。
新旧配置同时存在时 provider 必须一致，否则 Jarvis Box 拒绝启动，避免把消息发到错误渠道。

## JARVIS 心智进化周报

`cognitive-evolution` Task 始终生成本地周报。只有显式配置通知目标时才主动发送：

```bash
JARVIS_NOTIFY_PROVIDER=wecom
JARVIS_COGNITIVE_EVOLUTION_NOTIFY_TARGET=group:<provider-native-conversation-id>
```

目标也可以是 `direct:<provider-native-user-id>`。未配置目标时只保留周报 artifact；
`memory-consolidation` 和 `daily-reflection` 不发送通知。
