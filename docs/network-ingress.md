# Network ingress

正式 Docker 部署在容器内监听 `0.0.0.0:8787`，并默认将宿主机 `0.0.0.0:8787` 发布到该端口，受信任网络中的其他机器可直接使用宿主机地址访问。只允许本机 reverse proxy 或 tunnel 访问时，在 `deployment.env` 中显式设置 `JARVIS_BIND_ADDRESS=127.0.0.1`。

`0.0.0.0` 只控制端口发布，不提供 TLS、认证或防火墙。Operator 必须用宿主机防火墙、private network 或带访问控制的 TLS reverse proxy 限制入口；部署 release 不自动创建公网入口。

从旧 release 升级时，部署不会覆盖 Operator 已有的 `deployment.env`。如果该文件仍是 `JARVIS_BIND_ADDRESS=127.0.0.1`，将其改为 `JARVIS_BIND_ADDRESS=0.0.0.0`，再执行 `scripts/deploy-production.sh <deployment-home> compose up -d --force-recreate jarvis-box` 使新的宿主机发布地址生效。

## GitLab/GitHub/Jira

每个 provider 必须配置：

1. project/repository allowlist；
2. command author allowlist（公开仓库尤其需要）；
3. 正式 Agent identity 的 provider-native auth；
4. callback public URL；
5. 一条真实 webhook 与 writeback probe。

**Webhook secret 分两类，两类对「未配置」的反应不同，这是有意为之：**

- **明文 token 入口**：GitLab 的 `X-Gitlab-Token`，以及不带 `X-Hub-Signature` 的 Jira `X-Jira-Token`。secret 为空时不校验，请求直接放行。GitLab、Jira 通常部署在内网，留空是允许的部署选择；确实需要校验来源时再配 `GITLAB_WEBHOOK_SECRET`。
- **签名入口**：GitHub 的 HMAC，以及飞书项目。secret 未配置时一律拒绝（飞书项目端点直接返回 503 `feishu_project_not_configured`）。这一类入口面向 SaaS，不允许裸奔。

带 `X-Hub-Signature` 的 Jira 请求走签名校验，此时明文 token 不再参与判定。

GitHub/GitLab allowlist 由 operator 在 `runtime.env` 中明确配置。jarvis-box 不从 Jarvis repo 推导或校验 fleet。

```dotenv
GITLAB_HOST=gitlab.example.com
GITLAB_PROJECTS=group/project
REVIEW_GITLAB_PROJECTS=group/project
GITLAB_WEBHOOK_SECRET=   # 留空 = 不校验来源，内网部署可接受

GITHUB_REPOSITORIES=owner/repository
REVIEW_GITHUB_REPOSITORIES=owner/repository
GITHUB_WEBHOOK_SECRET=   # 留空 = 拒绝所有入站事件，启用端点前必须填
```

## uv-im-connector

uv-im-connector 与 jarvis-box 在 private Compose network 通信：

```text
IM provider
  → uv-im-connector (provider credential + normalization)
  → jarvis-box ChatBridge (business allowlist + Task/Run)
  → high-authority Agent
  → jarvis-box
  → uv-im-connector outbound API
```

`runtime.env` 用 `JARVIS_CONNECTOR_PROFILE=uvim` 同时启用 connector service 与 runtime client；`connector.env` 持有 provider 原生 secrets；`runtime.env` 中相关配置为：

```dotenv
JARVIS_CONNECTOR_PROFILE=uvim
JARVIS_UV_IM_CONNECTOR_NAME=uvim
JARVIS_UV_IM_CONNECTOR_URL=http://uv-im-connector:8787
JARVIS_UV_IM_CONNECTOR_TOKEN=
JARVIS_CHAT_ALLOWED_USERS=
JARVIS_CHAT_ALLOWED_CONVERSATIONS=
JARVIS_CHAT_REQUIRE_MENTION=true
```

正式 generic verify 检查 `/health`、authenticated `/v1/meta` 和 service/protocol version；真实 canary conversation 由 onboarding 单独记录。

## Trust boundaries

- jarvis-box Agent identity：代码/source/writeback 高权限；
- uv-im-connector identity：IM provider apps 与 message/resources；
- reverse proxy/tunnel identity：network exposure；
- webhook secret：验证入口，不等于 writeback identity；
- Docker socket：与 network ingress 无关，启用后等价宿主 root。

不要将 Host home、Agent SSH socket、connector env 或 Docker socket隐式挂进其他边界。

## 验收

网络可达不等于闭环完成。至少验证：签名入口在 secret 缺失或签名无效时拒绝、明文 token 入口在配了 secret 时错误 token 拒绝、越界 repo/user/conversation 拒绝、合法事件只建一个 Task、Runtime Agent 能原生发现所需 Jarvis skill、结果写回原始 thread/issue、secret 不出现在日志与 artifacts。
