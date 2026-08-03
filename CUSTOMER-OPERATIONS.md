# Jarvis Box 客户部署与运维指南

本文面向实际安装和维护 Jarvis Box 的客户。按顺序完成首次部署即可；日常运维直接查对应章节，不需要理解私有源码或发布流水线。

## 1. 首次部署清单

1. 使用 create-jarvis 构建并发布客户自己的 Company Jarvis。
2. 在正式部署时选择 Native 或 Docker，一旦投入使用不自动切换模式。
3. 下载同一版本的 release bundle、`SHA256SUMS` 和 `production-image.json` 并完成校验。
4. 按所选模式完成 Agent 与 GitHub/GitLab 等 provider 的原生认证。
5. 安装 Jarvis Box 和 Company Jarvis Runtime Foundation。
6. 先以 read-only 或受监督方式运行一条完整真实链路。
7. 记录版本、部署模式、实际 runtime root、Runtime Foundation root、状态命令和 Docker image digest（如适用）。

没有 Company Jarvis 时，从 create-jarvis 最新稳定 Release 开始，不跟随浮动默认分支：

```text
https://github.com/hengshi/create-jarvis/releases/latest
```

## 2. 选择部署模式

| | Native | Docker |
| --- | --- | --- |
| 适合 | 单机、最少配置、复用当前用户 | 容器隔离、独立持久化、标准化迁移 |
| runtime owner | 发起安装的现有 OS 用户 | 容器内持久 runtime identity |
| 认证 | 当前用户已有的原生认证 | 导入可移植 Host 身份，或直接在容器内登录 |
| Jarvis Box state | 安装器报告的实际 runtime root | 独立 named volume |
| Runtime Foundation scheduler | Host 直接执行 inner job | Host 经 `runtime-job` 执行容器内 inner job |

不要创建默认 `jarvis` 用户，不要复制或挂载整个 Host HOME，不要把 Token 写入 Company Jarvis 仓库、Construction Workspace 或镜像。

部署模式是正式部署选择，不是 scheduler failover。首次部署后只允许同模式升级；从 Native 迁移到 Docker 或反向迁移必须作为单独的停服、备份、验证和回滚项目处理，安装器不会自动完成。

## 3. 下载并校验 release

从 [GitHub Releases](https://github.com/hengshi/jarvis-box/releases/latest) 下载同一版本的：

- 当前平台 release bundle；
- `SHA256SUMS`；
- `production-image.json`。

Linux：

```bash
artifact=jarvis-box_<version>_<platform>.tar.gz
grep -E "  (${artifact}|production-image.json)$" SHA256SUMS | sha256sum -c -
tar -xzf "$artifact"
```

macOS：

```bash
artifact=jarvis-box_<version>_<platform>.tar.gz
grep -E "  (${artifact}|production-image.json)$" SHA256SUMS | shasum -a 256 -c -
tar -xzf "$artifact"
```

Docker 从 `production-image.json` 读取正式镜像，并使用 `repository@sha256:...`。不要使用 `latest` 或仅写版本 tag。

## 4. Native 上线

### 4.1 准备身份

以将要运行 Jarvis Box 的现有 OS 用户完成任务需要的认证，例如：

```bash
gh auth status
glab auth status
```

Codex、Claude、Gemini 等 Agent 只需认证实际选用的项。认证必须属于这个 OS 用户；不要另建服务用户。

### 4.2 安装和验收

在解压后的 release bundle 中执行：

```bash
sudo bash install.sh
jarvis-box doctor
jarvis-box agent smoke
jarvis-box status
```

安装器通过 `sudo` 获得系统服务安装权限，但服务仍以发起安装的现有 OS 用户运行并复用其 HOME。安装器不会创建 `jarvis` 或 `jarvis-box` 用户，也不会强制迁移到某个固定历史目录。

记录安装器报告的实际 binary、runtime root、state 路径和服务定义。不要根据 `which` 的历史路径猜测哪套 state 正在使用，以 `doctor` 和服务定义报告为准。

## 5. Docker 上线

### 5.1 准备 deployment home

选择客户控制的私有绝对路径：

```text
<deployment-home>/
├── deployment.env
├── runtime.env
├── auth/              # 仅 Host 身份导入路径使用，目录 0700、文件 0600
└── connector.env      # 仅启用 IM connector 时存在
```

`deployment.env` 保存镜像 digest、绑定地址、端口和部署行为。`runtime.env` 保存 Jarvis Box 行为和 webhook/connector verification secret，不保存 provider execution token 或 Agent credential。deployment home 不保存 Company Jarvis checkout、Host HOME dump 或临时 context。

首次 onboarding 在 `runtime.env` 保持：

```dotenv
JARVIS_SERVE_MODE=read-only
```

### 5.2 选择一种 Docker 认证路径

**路径 A：导入当前 Host 用户的可移植身份**

保持：

```dotenv
JARVIS_AUTH_IMPORT=auto
```

然后执行：

```bash
release_dir=/absolute/path/to/extracted-release
home=/absolute/path/to/deployment-home
ops="$release_dir/scripts/deploy-production.sh"

"$ops" "$home" start
"$ops" "$home" verify
```

`start` 会导入当前 Host 用户受支持的 `gh`、`glab` 和可移植 Agent 身份。多 GitHub 账号时，在 `deployment.env` 设置 `JARVIS_GITHUB_USER` 明确选择账号。不要把这些凭据手工写入 `runtime.env`。

**路径 B：直接在容器内认证**

Host 不保存运行时身份时设置：

```dotenv
JARVIS_AUTH_IMPORT=skip
```

然后执行：

```bash
"$ops" "$home" start
"$ops" "$home" shell
```

在容器 shell 中只运行需要的原生命令，例如：

```bash
gh auth login
glab auth login --hostname gitlab.example.com
codex login
claude auth login
```

退出后执行：

```bash
"$ops" "$home" verify
```

认证状态属于持久 Agent HOME，删除容器不会删除它。路径 A 还使用私有 auth bundle；撤销身份时要同时处理 auth bundle 与 Agent HOME。完整边界见[认证指南](AUTHENTICATION.md)。

### 5.3 Docker 上线验收

依次通过：

1. `"$ops" "$home" verify`；
2. Company Jarvis Runtime Foundation doctor；
3. 真实 Agent discovery；
4. 一条受监督的 provider ingress → Task/Run → workspace → Agent → writeback → cleanup 链路。

得到客户批准后，将 `JARVIS_SERVE_MODE` 改为 `worker`，只启用已经存在适用 workflow 的业务 lane，再执行：

```bash
"$ops" "$home" start
```

## 6. Runtime Foundation 与定时任务

create-jarvis 生成的 Company Jarvis 已包含版本化的 maintenance/self-improve jobs、prompts 和 scheduler manager。Runtime Agent 按模板安装，客户不需要自己编写脚本或 cron。

| 部署模式 | 唯一 scheduler owner | 调用方式 |
| --- | --- | --- |
| Native | 当前 OS 用户的 Host scheduler | 直接调用 Runtime Foundation inner job |
| Docker | Host scheduler | `deploy-production.sh ... runtime-job` → 容器内同一个 inner job |

Docker 容器内不运行第二套 scheduler。Host label 已加载也不等于健康；Docker 状态还必须证明 `runtime-job` 和容器内 inner job 可达。

onboarding 完成记录必须写明实际 Runtime Foundation root，以及当前 Company Jarvis Runtime Foundation 提供的准确 status/doctor 命令。Jarvis Box release 不提供或规定这条客户命令；它在 Docker 模式只提供通用 `runtime-job` transport。

如果状态报告的 scheduler owner 与 Jarvis Box 部署模式不一致，停止处理并修复残留，不要自动切换部署模式。

## 7. IM connector

IM 是可选能力。只在需要企业微信、飞书或钉钉等入口时设置 `JARVIS_CONNECTOR_PROFILE=uvim`，并按 release 中的 example 填写私有 `connector.env`。

- provider-native secret 只属于 connector；
- Jarvis Box 只持有 connector URL 和 shared verification token；
- connector 不共享 Agent HOME、Git identity、Docker socket 或 Jarvis Box state；
- 禁用 connector profile 时，同时移除对应 connector service；
- 上线验收必须使用真实 IM ingress 和真实回复，不能用内部 transport stub 代替 provider 认证。

## 8. 日常操作

### Native

```bash
jarvis-box status
jarvis-box logs
jarvis-box doctor
jarvis-box agent smoke
jarvis-box restart
```

### Docker

```bash
"$ops" "$home" compose ps
"$ops" "$home" compose logs --tail=200 jarvis-box
"$ops" "$home" verify
"$ops" "$home" shell
```

路径 A 更新身份：

```bash
"$ops" "$home" auth-import
"$ops" "$home" verify
```

路径 B 在 `shell` 中使用 provider 原生命令登录、轮换或退出，再执行 `verify`。

## 9. 升级与回滚

### Native

升级：

```bash
jarvis-box stop
sudo bash install.sh
jarvis-box doctor
jarvis-box agent smoke
jarvis-box status
```

有 active Task 时，`jarvis-box stop` 会阻断。等待任务完成，或先明确取消任务；安装器没有 `--force` 升级模式。已有服务仍在运行时，安装器会在替换 artifact 前退出。升级会复用安装器发现的现有 runtime root 和 state，不应另建一套空 state。

回滚时下载并校验目标旧 release，停止服务后从该 release bundle 执行同一个 `install.sh`，再运行 `doctor`、Agent smoke、`status` 和一条真实业务链路。回滚前备份实际 runtime root；不要通过替换 state 目录制造一个空运行时。

### Docker

1. 确认没有 active Task；
2. 停止正式服务；
3. 备份 deployment config 和需要保留的 volumes；
4. 下载并校验新 release；
5. 将 `JARVIS_IMAGE` 更新为新 release 的 digest；
6. 执行 `deploy` 和 `verify`；
7. 重跑一条真实业务链路。

回滚时恢复旧 digest，并执行同样的部署、验证和真实链路检查。Company Jarvis/Runtime Foundation 的版本升级由其自身合同管理，不随 Jarvis Box 镜像偷偷变化。

## 10. 备份

Native 备份安装器报告的实际 runtime root。不要假设客户使用某个历史目录，也不要只备份当前 shell 中 `which jarvis-box` 指向的位置。

Docker 备份 deployment home 以及需要保留的 volumes：

- `jarvis-agent-home`
- `jarvis-workspaces`
- `jarvis-state`
- `jarvis-logs`
- `jarvis-config`
- `connector-state`（启用 IM 时）

备份可变数据前先规范停服，或使用客户批准的一致性方案。不要把备份写回 release bundle 或公共仓库。

## 11. 故障诊断

| 现象 | 先看哪里 |
| --- | --- |
| Agent 无法启动或认证 | `jarvis-box doctor`、Agent smoke、实际 runtime identity |
| 历史 Task 消失 | 服务使用的实际 runtime root/state，而不是另一个空目录 |
| Task/Run 失败 | `/status`、Task state/event、Jarvis Box logs |
| GitHub/GitLab 无写回 | provider allowlist、导入身份、真实 CLI capability |
| IM 无消息或写回 | connector health、connector logs、provider credential |
| maintenance/self-improve 不运行 | 部署模式、Host scheduler owner、Runtime Foundation status、Docker transport reachability |
| Docker helper 无法进入环境 | Host operator/scheduler logs、容器状态和 inner job 是否安装 |

不要先手工修改 state 文件，不要用挂载 Host HOME 的方式修复认证。先保留 Task state、event、日志、版本、部署模式和路径证据，再处理恢复。

## 12. 安全边界

- Docker socket 默认关闭；容器 root 加 Docker socket 等价 Host root。
- Provider execution token 和 Agent credential 不进入 `runtime.env`。
- Webhook verification secret 与 Jarvis Box 到 connector 的 shared verification secret 可以保存在权限为 `0600` 的 `runtime.env`。
- IM provider secret 只属于 connector，不传给 Agent child process。
- Jarvis Box 不拥有客户知识和 workflow，不读取 Company Jarvis repo。
- `/status` 是运行诊断面，不是客户业务知识源。
