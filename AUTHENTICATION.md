# 认证

Jarvis Box 使用实际执行工作的运行时的身份。Native 与 Docker 部署因此有不同的存储边界，但完成标准相同：所需 CLI 能够认证、访问目标仓库或 provider、执行真实 writeback，并在重启后保持该身份。

## Native

以已完成 `gh`、`glab`、Codex、Claude 或 Gemini 认证的现有 OS 用户身份安装和运行 Jarvis Box。Native 安装不得创建 `jarvis` 用户，也不得将服务迁移到其他用户的 HOME。

## Docker：选择任一注册路径

Docker 拥有独立的持久 Agent HOME。不要将 Host HOME、SSH agent、Keychain 或完整 credential store 挂载到容器内。部署前选择下列一条路径，不要在未清理旧身份的情况下混用。

### 路径 A：导入可移植 Host 凭据

适用于当前 Host 用户已完成所需登录的情况：

```bash
release_dir=/absolute/path/to/extracted-release
deployment_home=/srv/jarvis-box

"$release_dir/scripts/deploy-production.sh" "$deployment_home" auth-import
"$release_dir/scripts/deploy-production.sh" "$deployment_home" start
"$release_dir/scripts/deploy-production.sh" "$deployment_home" verify
```

`auth-import` 仅将受支持的可移植身份复制到私有部署 auth bundle。它不复制或挂载 Host HOME。无交互部署应通过当前 release 中的 `scripts/import-host-auth.sh --help` 查看受支持的输入，并且只向本次导入进程提供 secret，不写入任何部署 env 文件。

auth bundle 与 Agent HOME 是两个独立持久层。容器每次启动都会从 auth bundle 向 Agent HOME 写入受支持的 Agent 身份，并向 runtime process 提供 provider token。轮换 Host 导入身份时重新运行 `auth-import`；撤销时同时删除或替换 auth bundle 中的对应文件和 Agent HOME 中已导入的副本，然后重建容器。只删除 Agent HOME volume 不会撤销仍可由 auth bundle 恢复的身份。

### 路径 B：直接在 Docker 内认证

适用于客户不想在 Host 上认证的情况：

先在 `deployment.env` 明确设置：

```dotenv
JARVIS_AUTH_IMPORT=skip
```

这会跳过默认的 Host 身份导入，因此即使 Host 完全没有 `gh`、`glab`、Codex 或 Claude 认证，容器仍可先启动用于登录。当前正式 Docker 镜像不包含 Gemini CLI；Gemini 仅在 Native 安装者自行提供该 CLI 时属于可选 Runtime Agent。

```bash
release_dir=/absolute/path/to/extracted-release
deployment_home=/srv/jarvis-box

"$release_dir/scripts/deploy-production.sh" "$deployment_home" start
"$release_dir/scripts/deploy-production.sh" "$deployment_home" shell
```

在该 shell 中，仅运行部署所需的 provider 原生登录：

```bash
gh auth login
glab auth login --hostname gitlab.example.com
codex login
claude auth login
```

退出 shell 后从部署面验证：

```bash
"$release_dir/scripts/deploy-production.sh" "$deployment_home" verify
```

登录状态只存储在持久 Agent HOME volume 中，容器替换后仍然存在。`JARVIS_AUTH_IMPORT=skip` 会使 runtime 忽略已有 auth bundle；删除容器不等于删除运行时身份，删除 Agent HOME volume 才会删除这条路径创建的身份。若部署曾使用路径 A，仍应清理私有 auth bundle，避免以后重新启用路径 A 时恢复旧身份。

## 各文件职责

| 位置 | 允许的内容 |
| --- | --- |
| `deployment.env` | 镜像 digest、绑定地址、部署 identity 和 Compose 行为 |
| `runtime.env` | Jarvis 运行时行为、provider 路由、webhook verification secret 和 Jarvis Box 到 connector 的 shared verification secret；不包含 provider execution token 或 Agent credential |
| `connector.env` | 仅在启用对应 connector 时的 connector provider-native secrets |
| 私有 auth bundle | 由 `auth-import` 暂存的可移植身份 |
| 持久 Agent HOME | 为容器运行时创建或导入的 provider 原生登录状态 |

不要将 GitHub、GitLab、Codex、Claude 或其他 Runtime Agent 的 execution token/API key 放入 `runtime.env`。Docker start 会在启动前迁移路径 A 支持的旧凭据，或在路径 B 检测到任何执行凭据时 fail closed。Webhook secret 和 Jarvis Box 到 connector 的 shared verification token 属于服务端验证配置，可以保存在权限为 `0600` 的 `runtime.env`。发布自动化凭据如 `GH_TOKEN` 和 AWS 凭据属于独立的 release-plane identity，绝不能进入客户部署。

## 完成检查

单独的 `auth status` 是有用的诊断手段，但不是验收证据。投入生产使用前，运行一条真实任务，完成 ingress、Task/Run 创建、workspace 创建、Agent 执行、provider writeback 和 workspace cleanup。容器重建后重复能力检查，证明所选 Docker identity 是持久的。
