# 架构与产品边界

<a id="架构"></a>

本文面向部署 Jarvis Box、接入 Runtime Foundation 或审查运行边界的客户运维人员和集成方。它说明各组件负责什么；安装和日常维护请从[开始使用](guide/getting-started.md)和[运维入口](operations.md)开始，Task/Run 的状态与恢复规则以[执行模型](execution-model.md)为准。

<a id="产品边界"></a>

## 一眼看懂

```text
客户的 Jarvis repo 与 Runtime Foundation
  └─ 在持久 Agent HOME 中准备、同步并让 Agent 发现客户技能

Jarvis Box release
  └─ Native service 或 Docker Compose deployment
       ├─ Task/Run 控制面、状态与日志
       ├─ 选定的 Runtime Agent 和通用工具链
       └─ 可选的受管 uv-im-connector，或共享 hub 的独立调用方
```

Jarvis Box 是执行与运行控制产品，不是客户 Jarvis repo 的部署器。它不会 clone、pull、挂载、校验或注入客户 Jarvis，也不会读取客户的治理文件或选择客户 repo 的 remote、path、ref。客户 Runtime Foundation 负责这些事情；Jarvis Box 负责在受管 Task 中启动 Agent、保存 Task/Run 事实并执行已配置的通用准备接缝。

<a id="runtime-foundation-接缝"></a>

## 两个接缝

### Runtime Foundation

客户的 Runtime Foundation 可以拥有 bootstrap、同步、Agent discovery、客户 Runtime Job 与调度适配。Jarvis Box 不解释这些命令或客户技能。

首次 Agent 启动前，如已配置 `JARVIS_AGENT_RUNTIME_PREPARE_COMMAND`，Jarvis Box 会在 Workspace、Provider 和依赖准备完成后调用这个无参数程序。程序成功结果会成为该 Task 的 receipt；普通 Continue 会复用成功 receipt。程序失败、超时或返回非法 JSON 时，Workspace 仍保留，但 Agent 不会启动。这个接缝的配置和 JSON 合同见[配置参考](configuration.md#agent-runtime-preparer)。

Docker 中，客户的宿主调度器通过 `runtime-job` 把命令交给容器；容器内 Agent 也直接运行同一个内部 Runtime Job。内部任务不调用 Docker，状态和日志写入持久 Agent HOME。客户 Runtime Foundation 必须防止容器内再启动同一套 scheduler，否则接入应停止并修复。

### Provider 与 IM

Provider allowlist、webhook、写回开关和 connector 都由实例的 `runtime.env` 管理。`uvim` profile 管理本实例的 connector；`uvim-external` 只连接外部共享 hub，不管理它的进程、状态或平台凭据。两种方式的 connector 都不获得 Agent HOME、Git credentials 或 Docker socket。各 Provider 的具体权限和接入步骤在 `docs/integrations/` 中。

<a id="high-authority-trust-model"></a>

## 信任与身份边界

Jarvis Box 服务和它启动的 Agent 属于同一高权限执行域。因此，允许的 provider 身份、Agent 身份、工具和 Docker socket 都需要客户明确决定。

| 部署方式 | 运行身份 | 不会做的事 |
| --- | --- | --- |
| Native | 安装者当前 OS 用户和其 HOME | 不创建专用产品用户 |
| Docker | 安装者 UID/GID，对容器显示为非 root 的 `jarvis` | 不挂载 Host HOME、Keychain、SSH agent 或整套凭据库 |

Docker 的 `auth-import` 只导入获批准的可移植身份到 deployment home 内的私有 `auth/`，再写入持久 Agent HOME。默认不挂 Docker socket；设置 `JARVIS_ENABLE_DOCKER_SOCKET=1` 等同于向运行时授予宿主 root 级 Docker 控制能力。认证路径见[部署合同](deployment.md#身份与认证)。

Provider allowlist 只是 Jarvis Box 的接入边界，不替代 Agent 原生 CLI 的权限。Git commit author/committer 也不等于 provider 读取、评论或 push 权限；需要将提交归属给代码负责人时，使用[代码归属与 Git 提交身份](code-attribution.md)。

<a id="image-content"></a>

## Image content

正式镜像提供 Jarvis Box、固定版本的 `uv-im-connector` binary、选定的 Runtime Agent CLI、通用工具链和通用 `skill-creator`。它不包含 create-jarvis、任何客户 Jarvis repo 或客户 Runtime Foundation。Entrypoint 只把镜像自带的通用技能链接到 discovery roots，不覆盖 identity-owned 内容；客户 Runtime Foundation 在部署后把客户技能写入持久 Agent HOME。

<a id="persistence"></a>

## 持久数据归属

| 数据 | Docker 中的位置 | 用途 |
| --- | --- | --- |
| Agent HOME | `/home/jarvis` | Agent 登录、原生 discovery roots、客户 Runtime Foundation |
| Workspace | `/workspace` | 已登记 Task workspace |
| 状态 | `/var/lib/jarvis-box` | Task、Run、恢复和服务状态 |
| 依赖缓存 | `/var/cache/jarvis-box` | 跨 Task 的工具原生缓存 |
| 日志 | `/var/log/jarvis-box` | Jarvis Box 诊断 |
| connector state | connector 专用持久目录 | IM 事件与资源状态 |

Deployment home 另外保存 `deployment.env`、`runtime.env`、私有 `auth/` 和受管 connector 的可选 `connector.env`。共享 hub 的 URL 与本实例独有的调用方 token 只放在私有 `runtime.env`；hub 的凭据、状态和生命周期由 hub 管理员负责。不要把客户 Jarvis repo、临时 checkout、锁文件或 readiness state 混入 deployment home。持久化、保留和恢复细节见[存储模型](storage-model.md)。

<a id="supported-surface"></a>

## 支持范围

正式支持当前用户身份的 Ubuntu systemd/macOS launchd Native 服务，以及 digest 固定、单副本的 Docker Compose deployment。其他 orchestrator 只有在提供等价的镜像、身份边界、持久 HOME/state/workspace/log、connector、健康探针、升级/回滚和 `runtime-job` transport 后，才应当作为受支持的部署面。
