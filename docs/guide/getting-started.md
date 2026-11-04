# 开始使用 Jarvis Box

使用者只需要回答两个问题：是否已经有自己的 Jarvis，以及选择 Native 还是 Docker。

先打开[下载与安装指引](https://download.hengshi.com/jarvis-box/index.html)：发布包、校验文件和 Docker 镜像包均可从衡石下载站获取，无需访问 GitHub。`install.sh` 和完整使用文档在发布包内。Native 无 GitHub 安装须显式传入已下载的本地文件，命令见[Native 安装步骤](https://download.hengshi.com/jarvis-box/index.html#native)。

## 1. 还没有 Jarvis

Company Jarvis 建设与运行时安装分别进行。可访问 GitHub 时，让已经登录并获得授权的 Host Agent 执行：

```text
请运行 git clone https://github.com/hengshi-jarvis/create-jarvis create-jarvis，读取本地 create-jarvis/SKILL.md，然后帮我构建并部署一套 Jarvis。
```

Host Agent 先收集授权资料位置和连接信息，部署最新稳定版 Jarvis Box 并接通工作系统与 IM；已验证入口即可使用。随后继续建设客户拥有的 Jarvis repo、repo-local skills 与 workflow，再安装并接入 Runtime Foundation。完整知识构建不阻塞普通任务。

## 2. 已经有 Jarvis

| 选择 | 何时使用 | 认证方式 |
| --- | --- | --- |
| Native | 希望最少配置，直接使用当前机器 | 复用安装者当前 OS 用户已有认证 |
| Docker | 希望隔离、可迁移和独立持久化 | 自动导入当前 Host 用户的必要认证 |

不需要创建 `jarvis` 用户，不需要把 token 写进文档，也不要复制整个用户 HOME。

## 3. Native 上线

在已校验的 release bundle 中执行：

```bash
sudo bash install.sh   # Linux
bash install.sh        # macOS：不要加 sudo
jarvis-box doctor
jarvis-box agent smoke
jarvis-box status
```

安装器使用发起安装的现有 OS 用户。macOS 上 `sudo bash install.sh` 会把 launchd 域与运行时目录落到 root 名下，服务起不来。

如果是升级，必须先执行：

```bash
jarvis-box stop
```

有 active Task 时停服会被阻断。先等待任务完成，或明确继续、取消任务；不要绕过 Task/Run 生命周期直接替换服务。

## 4. Docker 上线

准备 deployment home，填写 release bundle 提供的 `deployment.env`、`runtime.env` 和可选 `connector.env`。首次在 `runtime.env` 启用任务与回写，用户和会话允许名单留空：

```dotenv
JARVIS_ISSUE_POST_CHECK_ENABLED=true
JARVIS_PROVIDER_WRITEBACK_ENABLED=true
```

执行：

```bash
ops=/absolute/release/scripts/deploy-production.sh
home=/absolute/deployment-home

"$ops" "$home" start
"$ops" "$home" verify
```

`start` 自动导入当前 Host 用户的必要认证。多 GitHub 账号时在 `deployment.env` 选择明确的 machine user；不要进入容器复制 Host credential store。

验证实际任务执行和原处回复后即可使用。客户知识随后交付，由 Runtime Foundation 完成 bootstrap、sync、doctor 和真实知识 discovery；尚未安装 Foundation 时 prepare hook 留空，缺少 Company 或 repo-local skills 不阻塞普通任务。Company 知识投递使用现有部署，不重建 Jarvis Box。

## 5. 什么算真正上线

必须同时看到：

1. `health`、`jarvis-box doctor` 和 Agent smoke 通过；
2. Runtime Agent 能执行实际请求；没有 Company/repo-local 知识时也能直接调查和完成任务；
3. 一条真实 provider 或 IM 任务完成 ingress、Task/Run、workspace、Agent 和 writeback；
4. Task 终态后 workspace 与外部资源按所有权正确清理。

Generic health 通过不等于任务与回复链路已可用。Company 定制 workflow 的验证另行记录，不冒充完整知识建设已完成。

日常操作见 [运维入口](../operations.md)。Docker 详细合同见 [部署参考](../deployment.md)，变量解释见 [配置参考](../configuration.md)。
