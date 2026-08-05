# 开始使用 Jarvis Box

使用者只需要回答两个问题：是否已经有自己的 Jarvis，以及选择 Native 还是 Docker。

## 1. 还没有 Jarvis

不要先配置 webhook、env 文件或容器。让已经登录并获得授权的 Host Agent 执行：

```text
请运行 git clone https://github.com/hengshi/create-jarvis create-jarvis，读取本地 create-jarvis/SKILL.md，然后帮我构建并部署一套 Jarvis。
```

Host Agent 会盘点授权的数据源和代码仓库，建设客户拥有的 Jarvis repo、workflow 与 Runtime Foundation，然后引导选择部署模式。

## 2. 已经有 Jarvis

| 选择 | 何时使用 | 认证方式 |
| --- | --- | --- |
| Native | 希望最少配置，直接使用当前机器 | 复用安装者当前 OS 用户已有认证 |
| Docker | 希望隔离、可迁移和独立持久化 | 自动导入当前 Host 用户的必要认证 |

不需要创建 `jarvis` 用户，不需要把 token 写进文档，也不要复制整个用户 HOME。

## 3. Native 上线

在已校验的 release bundle 中执行：

```bash
sudo bash install.sh
jarvis-box doctor
jarvis-box agent smoke
jarvis-box status
```

如果是升级，必须先执行：

```bash
jarvis-box stop
```

有 active Task 时停服会被阻断。先等待任务完成，或明确继续、取消任务；不要绕过 Task/Run 生命周期直接替换服务。

## 4. Docker 上线

准备 deployment home，填写 release bundle 提供的 `deployment.env`、`runtime.env` 和可选 `connector.env`。首次使用只读模式：

```dotenv
JARVIS_SERVE_MODE=read-only
```

执行：

```bash
ops=/absolute/release/scripts/deploy-production.sh
home=/absolute/deployment-home

"$ops" "$home" start
"$ops" "$home" verify
```

`start` 自动导入当前 Host 用户的必要认证。多 GitHub 账号时在 `deployment.env` 选择明确的 machine user；不要进入容器复制 Host credential store。

随后由客户 Jarvis 的 Runtime Foundation 在正式环境中完成 bootstrap、sync、doctor 和真实 Agent discovery。全部通过并得到客户批准后，再切换：

```dotenv
JARVIS_SERVE_MODE=worker
```

只启用已经具备适用 workflow 的 provider lane。

## 5. 什么算真正上线

必须同时看到：

1. `health`、`jarvis-box doctor` 和 Agent smoke 通过；
2. Runtime Agent 能发现客户 Jarvis workflow；
3. 一条真实 provider 或 IM 任务完成 ingress、Task/Run、workspace、Agent 和 writeback；
4. Task 终态后 workspace 与外部资源按所有权正确清理。

Generic health 通过不等于客户 workflow 已经可用。

日常操作见 [运维入口](../operations.md)。Docker 详细合同见 [部署参考](../deployment.md)，变量解释见 [配置参考](../configuration.md)。
