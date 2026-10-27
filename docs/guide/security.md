# 权限与安全边界

## Jarvis Agent 是高权限主体

正式 Agent 需要完成真实工程交付，因此不是低权限 bot。客户可以为它授予组织超级管理员权限；具体 scope 必须在 deployment authorization checkpoint 明确记录。

正式 Docker 容器内的 Agent 使用安装者的数字 UID/GID，以非 root 身份运行。Docker socket 默认不挂载；显式挂载仍等价授予宿主 root 能力，必须明确授权。Native 使用安装者当前 OS 用户，不创建额外产品用户。

## 独立而不是降权

不要复制 Host 用户整个 HOME、SSH agent 或浏览器 profile。Native 使用当前安装用户的原生身份；Docker 使用独立持久 Agent HOME，通过正式窄化导入或在容器内登录建立身份。Git author、GitHub/GitLab principal、Agent account 和 source credentials 分别记录非 secret identifier 与 owner，供审计、轮换与撤销。

## Secret ownership

- deployment config 不存 Agent/provider-native credential material；
- jarvis-box `runtime.env` 只持有 webhook 验签与 connector client capability secrets，不持有 `gh/glab` 执行 Token 或 Agent API key；
- uv-im-connector 独占 IM provider app secret/token；
- Agent 子进程只收到当前任务需要的环境，不收到 connector 原生 secrets；
- logs、Task artifacts、status API 和 writeback 必须执行 redaction。

## Network

监听与宿主端口发布以所选部署的生效配置为准。正式 Docker 默认向受信任网络发布宿主 `0.0.0.0:8787`；仅允许本机入口时显式配置 `JARVIS_BIND_ADDRESS=127.0.0.1`。地址绑定不提供 TLS、认证或防火墙；外部 ingress 应使用客户控制的网络边界，并按各平台协议启用来源认证及范围允许清单。签名与明文 token 入口的不同默认行为见[网络入口](../network-ingress.md)。

## Artifact integrity

OCI image 必须固定到 digest。Jarvis 与 repo-local skills 通过各自 Git policy 交付，并由 Jarvis Runtime Foundation 同步到 Agent discovery roots。不要用 running-container edits 作为 source of truth，也不要用一个跨产品 lock 把这些独立更新路径伪装成原子 deployment。
