# 开始使用 Jarvis Box

本指南面向第一次上线 Jarvis Box 的客户。完成后，你应当能确认服务健康、Runtime Agent 可运行，并让一条真实 provider 或 IM 任务完成接收、执行和原处回复。

先从[下载与安装指引](https://download.hengshi.com/jarvis-box/index.html)取得发布包、校验文件和 Docker 镜像包。无需访问 GitHub；`install.sh` 和完整使用说明在发布包中。Native 离线安装必须显式传入已下载的本地文件，命令见下载页的 [Native 安装步骤](https://download.hengshi.com/jarvis-box/index.html#native)。

## 1. 确认是否已有 Jarvis

### 还没有 Jarvis

Jarvis 建设与 Jarvis Box 运行时安装分开进行。若 Host Agent 已登录并获授权，可给它以下请求：

```text
请运行 git clone https://github.com/hengshi-jarvis/create-jarvis create-jarvis，读取本地 create-jarvis/SKILL.md，然后帮我构建并部署一套 Jarvis。
```

Host Agent 会先收集授权资料位置和连接信息，部署稳定版 Jarvis Box 并接通工作系统与 IM。随后可继续建设客户拥有的 Jarvis repo、repo-local skills 与 workflow，并接入 Runtime Foundation。完整知识建设不阻塞普通任务。

### 已经有 Jarvis

选择一种部署模式：

| 选择 | 何时选它 | 身份方式 |
| --- | --- | --- |
| Native | 需要最少配置，直接使用当前机器 | 使用安装者当前 OS 用户已有的认证。 |
| Docker | 需要隔离、可迁移的独立持久环境 | `start` 可窄化导入当前 Host 用户所需认证；也可以在容器的持久 Agent HOME 中直接登录。 |

不需要创建 `jarvis` 用户，不要把 token 写进文档，也不要复制整个用户 HOME。

## 2. 安装并启动

### Native

在已经校验的 release bundle 中执行：

```bash
sudo bash install.sh   # Linux
bash install.sh        # macOS：不要加 sudo
jarvis-box doctor
jarvis-box agent smoke
jarvis-box status
```

安装器使用发起安装的现有 OS 用户。macOS 使用 `sudo bash install.sh` 会让 launchd 域和运行时目录属于 root，服务无法以预期身份启动。

升级前先运行：

```bash
jarvis-box stop
```

有 active Task 时停服会被阻断。等待其完成，或者明确 Continue、取消任务；不要绕过 Task/Run 生命周期直接替换服务。

### Docker

创建一个 deployment home，按 release bundle 填写 `deployment.env`、`runtime.env` 和受管 connector 的可选 `connector.env`。如果连接共享 UVIM hub，使用 `JARVIS_CONNECTOR_PROFILE=uvim-external`，把 hub URL 与本 Box 独有的 scoped client token 写入私有 `runtime.env`，不创建本地 connector；具体步骤见 [IM 接入](../integrations/im.md#管理员-配置-jarvis-box-与-connector)。首次在 `runtime.env` 启用工作项自动检查与 provider 写回；用户和会话允许名单可以留空：

```dotenv
JARVIS_ISSUE_POST_CHECK_ENABLED=true
JARVIS_PROVIDER_WRITEBACK_ENABLED=true
```

再执行：

```bash
ops=/absolute/release/scripts/deploy-production.sh
home=/absolute/deployment-home

"$ops" "$home" start
"$ops" "$home" verify
```

`start` 会导入当前 Host 用户必要的认证。若有多个 GitHub 账号，在 `deployment.env` 选择明确的 machine user；不要进入容器复制 Host credential store。更多部署变量见 [部署参考](../deployment.md) 和 [配置参考](../configuration.md)。

## 3. 做一次真正的上线验证

在日常使用前，确认下列四件事都成立：

1. `health`、`jarvis-box doctor` 和 Agent smoke 均通过。
2. Runtime Agent 能执行实际请求；尚未安装 Company 或 repo-local skills 时，也能调查和完成普通任务。
3. 一条真实 provider 或 IM 任务经过 ingress、Task/Run、workspace、Agent，并把结果写回原对象或原会话。
4. Task 终态后，workspace 和外部资源按其所有权正确清理。

通用 health 通过只证明服务可用，不证明任务和回复链路已上线。Company 定制 workflow 的验证应单独记录，不能把它称为完整知识建设。日常停服、升级、认证、备份与故障处理见 [运维入口](../operations.md)。
