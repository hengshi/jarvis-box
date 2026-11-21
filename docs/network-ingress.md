# 网络入口与来源验证

本页面向公开 Jarvis Box webhook 或接入 IM 的部署管理员。先决定谁能从网络访问服务，再逐一配置来源认证、允许范围和真实闭环验证。

## 先选择端口暴露范围

正式 Docker 在容器内监听 `0.0.0.0:8787`，默认将宿主 `0.0.0.0:8787` 发布到该端口，受信任网络的其他机器可访问。若只让本机反向代理或 tunnel 访问，在 `deployment.env` 设置：

```dotenv
JARVIS_BIND_ADDRESS=127.0.0.1
```

`0.0.0.0` 只决定端口发布，不提供 TLS、认证或防火墙。用宿主防火墙、private network 或带访问控制的 TLS reverse proxy 限制入口；release 不会自动创建公网入口。

从旧 release 升级时，部署不会覆盖已有 `deployment.env`。若仍为 `JARVIS_BIND_ADDRESS=127.0.0.1` 而需要受信任网络访问，改为 `0.0.0.0` 后执行：

```bash
scripts/deploy-production.sh <deployment-home> compose up -d --force-recreate jarvis-box
```

## 工作系统 webhook

每个 GitLab、GitHub 或 Jira 接入都需要：项目/仓库 allowlist、命令作者 allowlist、正式 Agent 的 provider-native auth、可访问的 callback public URL，以及一条真实 webhook + writeback 验证。

```dotenv
GITLAB_HOST=gitlab.example.com
GITLAB_PROJECTS=group/project
REVIEW_GITLAB_PROJECTS=group/project
GITLAB_WEBHOOK_SECRET=   # 留空：不校验来源；仅适合可接受的内网部署

GITHUB_REPOSITORIES=owner/repository
REVIEW_GITHUB_REPOSITORIES=owner/repository
GITHUB_WEBHOOK_SECRET=   # 留空：拒绝所有 GitHub 入站事件
```

来源密钥按协议分两类：

| 入口 | secret 未配置时的行为 |
| --- | --- |
| GitLab `X-Gitlab-Token`；未带 `X-Hub-Signature` 的 Jira `X-Jira-Token` | 不校验并放行。GitLab/Jira 常部署于内网；需要校验时配置 `GITLAB_WEBHOOK_SECRET` 或 Jira secret。 |
| GitHub HMAC；飞书项目 | 拒绝。飞书项目 endpoint 返回 `503 feishu_project_not_configured`。 |

带 `X-Hub-Signature` 的 Jira 请求只做签名校验，不再使用明文 token。Jarvis Box 不会从客户 Jarvis repo 推导或验证 allowlist。

## IM：通过 uv-im-connector

使用受管 `uvim` profile 时，connector 与 Jarvis Box 在 private Compose network 中通信：

```text
IM provider
  → uv-im-connector（provider credential 与事件规范化）
  → jarvis-box ChatBridge（业务 allowlist 与 Task/Run）
  → Runtime Agent
  → jarvis-box
  → uv-im-connector outbound API
```

在 `runtime.env` 设置：

```dotenv
JARVIS_CONNECTOR_PROFILE=uvim
JARVIS_UV_IM_CONNECTOR_NAME=uvim
JARVIS_UV_IM_CONNECTOR_URL=http://uv-im-connector:8787
JARVIS_UV_IM_CONNECTOR_TOKEN=
JARVIS_CHAT_ALLOWED_USERS=
JARVIS_CHAT_ALLOWED_CONVERSATIONS=
JARVIS_CHAT_REQUIRE_MENTION=true
```

`connector.env` 保存 provider 原生 secrets。常规 verify 会检查 `/health`、经认证的 `/v1/meta` 以及 service/protocol version；它不取代实际 canary conversation。

共享 hub 使用 `uvim-external`，不启动本地 connector。每个 Box 的 URL 和独有 scoped client token 只保存在自己的私有 `runtime.env`，不复制 hub 凭据或状态。hub 必须按 token 隔离事件、回复、资源和身份关联；Box 只看到该调用方的 meta 与事件。配置和验证步骤见 [IM 接入](integrations/im.md#管理员-配置-jarvis-box-与-connector)。

## 审查信任边界并验收

- Jarvis Box Agent identity：代码、来源访问和 writeback 的高权限身份；
- uv-im-connector identity：IM provider app 与消息/资源；
- reverse proxy/tunnel identity：网络暴露；
- webhook secret：只证明入口来源，不等同于 writeback identity；
- Docker socket：与网络入口无关，启用即等价宿主 root。

不要把 Host HOME、Agent SSH socket、connector env 或 Docker socket 隐式挂到另一条边界。

网络可达不代表闭环完成。至少证明：缺 secret 或无效签名的签名入口被拒绝；已配置 secret 的明文 token 入口拒绝错误 token；越界 repo/user/conversation 被拒绝；合法事件只创建一个 Task；Agent 能发现所需 Jarvis skill；结果回到原 thread/issue；secret 没有进入日志或 artifacts。
