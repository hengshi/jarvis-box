# 权限与安全边界

本页面向决定部署权限和网络边界的客户管理员。Jarvis Box 的 Runtime Agent 用于完成真实工程交付，因此必须按高权限主体来授权、审计和隔离；它不是低权限聊天机器人。

## 身份与主机权限

客户可以为正式 Agent 授予组织超级管理员权限，但必须在 deployment authorization checkpoint 中记录实际授予的 scope 和批准人。

- Native 使用安装者当前 OS 用户，不创建额外产品用户。
- 正式 Docker 容器使用安装者的数字 UID/GID，以非 root 身份运行。
- Docker socket 默认不挂载。显式挂载等价于授予宿主 root 能力，必须得到明确授权。

不要复制 Host 用户整个 HOME、SSH agent 或浏览器 profile。Native 使用当前安装用户的原生身份；Docker 通过正式的窄化导入或容器内登录，在独立持久 Agent HOME 中建立身份。Git author、GitHub/GitLab principal、Agent account 和来源凭据都应记录非 secret identifier 与 owner，便于审计、轮换和撤销。

## Secret 在哪里保存

- deployment config 不保存 Agent/provider-native credential material；
- `runtime.env` 只保存 webhook 验签和 connector client capability secrets，不保存 `gh`/`glab` 执行 token 或 Agent API key；
- `uv-im-connector` 独占 IM provider app secret/token；
- Agent 子进程只取得当前任务需要的环境，不取得 connector 原生 secrets；
- logs、Task artifacts、status API 和 writeback 必须做 redaction。

## 网络边界

监听和宿主端口发布以实际生效的部署配置为准。Docker 默认向受信任网络发布宿主 `0.0.0.0:8787`；只允许本机反向代理或 tunnel 时，在 `deployment.env` 设 `JARVIS_BIND_ADDRESS=127.0.0.1`。绑定地址不提供 TLS、认证或防火墙；外部入口必须由客户控制的网络边界保护，并按各平台协议启用来源认证和范围允许清单。具体规则见 [网络入口](../network-ingress.md)。

## 交付物完整性

OCI image 必须固定到 digest。Jarvis 和 repo-local skills 分别按各自 Git policy 交付，由 Runtime Foundation 同步到 Agent discovery roots。不要把 running-container edit 当作 source of truth，也不要用一个跨产品 lock 假装这些独立更新路径是原子部署。
