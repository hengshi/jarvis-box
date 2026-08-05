# 架构

## 产品边界

```text
create-jarvis method
  → customer-owned Jarvis repo
      ├── knowledge/workflows/runtime governance
      └── Runtime Foundation → Agent-native discovery roots

jarvis-box release
  → Native service or Docker image + Compose/operator helpers
      ├── jarvis-box Task/Run/control plane
      ├── Runtime Agent + generic toolchain
      └── optional uv-im-connector
```

Jarvis repo 与 jarvis-box 是独立演进的产品。jarvis-box 不知道 Jarvis remote/path/ref，不 clone、pull、sync、mount、校验或注入 Jarvis，也不读取 `runtime-governance.md`。Runtime Agent 从持久 Agent HOME 下的原生 discovery roots 发现 Jarvis skills。

## Runtime Foundation 接缝

客户 Jarvis repo 拥有 bootstrap、sync、doctor、Runtime Jobs 和 Scheduler Adapter。jarvis-box release 只提供通用 `runtime-job` transport：宿主 scheduler 通过它进入运行中的正式容器并执行一个内部命令。

```text
native scheduler ───────────────→ inner Runtime Job
host scheduler → runtime-job ───→ same inner Runtime Job in Docker
Agent already in Docker ─────────→ inner Runtime Job
```

内部任务不调用 Docker。它把 state/log 写进持久 Agent HOME；host scheduler 记录进入容器失败。jarvis-box 二进制不读取 host scheduler log。

## High-authority trust model

jarvis-box server 与其启动的 Agent 是同一高权限执行域，但容器进程以安装者的数字 UID/GID 非 root 运行，并通过 NSS 映射为稳定的 `jarvis` 身份。Docker socket 默认不挂载；显式挂载仍等价宿主 root。

- Native 与安装发起者保持同一 OS user/HOME；不创建产品专用用户；
- Docker 不绑定 Host HOME、Keychain 或 SSH agent，只导入窄化身份快照；
- Docker identity 在当前用户所有的 deployment-home Agent HOME 绑定目录中独立审计、轮换和撤销；
- connector 不获得 Agent HOME、Git credentials 或 Docker socket；
- provider allowlists 来自 `runtime.env`，不是 Jarvis manifest。

## Image content

正式 image 包含 jarvis-box、固定版本 uv-im-connector binary、选定 Agent CLI、常见工具链和 generic `skill-creator`。它不包含 create-jarvis、任何客户 Jarvis 或客户 Runtime Foundation。

Entrypoint 只把 image-owned generic skills 链接到 discovery roots，保留 identity-owned 内容。客户 Jarvis 由其 Runtime Foundation 在部署后写入持久 Agent HOME。

## Persistence

| Bind directory | Owner/content |
|---|---|
| Agent HOME (`/home/jarvis`) | Agent identity/config, native discovery roots, customer Runtime Foundation |
| workspace (`/workspace`) | Task workspaces |
| state (`/var/lib/jarvis-box`) | Task/Run/resume state |
| logs (`/var/log/jarvis-box`) | jarvis-box diagnostics |
| connector state | connector event/resource state |

Deployment home 保存 `deployment.env`、`runtime.env`、私有 `auth/`、可选 `connector.env`，以及当前用户所有的 `data/` 持久化目录。不存在 Jarvis mount、context、deployment lock 或 readiness state。

## Supported surface

正式新部署支持当前用户身份的 Ubuntu systemd/macOS launchd Native 服务，以及 digest-pinned、single-replica Docker Compose。其他 orchestrator 需要提供等价的 image、identity、persistent HOME/state/workspace/log、connector、probe、upgrade/rollback 和 runtime-job transport 后才能进入支持矩阵。
