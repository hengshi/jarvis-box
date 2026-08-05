# 权限与安全边界

## Jarvis Agent 是高权限主体

正式 Agent 需要完成真实工程交付，因此不是低权限 bot。客户可以为它授予组织超级管理员权限；具体 scope 必须在 deployment authorization checkpoint 明确记录。

容器内 Agent 以 root 运行。没有 Docker socket 时，root 限于容器；挂载 socket 后等价宿主 root，必须显式批准。

## 独立而不是降权

不要复制 Host 用户整个 home、SSH agent 或浏览器 profile。为正式 Agent 激活独立 identity，以便单独审计、轮换与撤销。Git author、GitHub/GitLab principal、Agent account 和 source credentials 都记录非 secret identifier 与 owner。

## Secret ownership

- deployment config 不存 Agent/provider-native credential material；
- jarvis-box `runtime.env` 只持有 webhook 验签与 connector client capability secrets，不持有 `gh/glab` 执行 Token 或 Agent API key；
- uv-im-connector 独占 IM provider app secret/token；
- Agent 子进程只收到当前任务需要的环境，不收到 connector 原生 secrets；
- logs、Task artifacts、status API 和 writeback 必须执行 redaction。

## Network

默认只绑定 `127.0.0.1`。外部 ingress 应使用客户控制的 TLS/reverse proxy/tunnel，并启用 provider signature、project/repository allowlist、user/conversation allowlist。

## Artifact integrity

OCI image 必须固定到 digest。Jarvis 与 repo-local skills 通过各自 Git policy 交付，并由 Jarvis Runtime Foundation 同步到 Agent discovery roots。不要用 running-container edits 作为 source of truth，也不要用一个跨产品 lock 把这些独立更新路径伪装成原子 deployment。
