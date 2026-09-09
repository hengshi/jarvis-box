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

没有 Company Jarvis 时，从 create-jarvis 最新代码开始：

```text
https://github.com/hengshi-jarvis/create-jarvis
```

## 2. 选择部署模式

| | Native | Docker |
| --- | --- | --- |
| 适合 | 单机、最少配置、复用当前用户 | 容器隔离、独立持久化、标准化迁移 |
| runtime owner | 发起安装的现有 OS 用户 | 容器内持久 runtime identity |
| 认证 | 当前用户已有的原生认证 | 导入可移植 Host 身份，或直接在容器内登录 |
| Jarvis Box state | 安装器报告的实际 runtime root | deployment home 下的 `data/` 持久目录 |
| Runtime Foundation scheduler | Host 直接执行 inner job | Host 经 `runtime-job` 执行容器内 inner job |

不要创建默认 `jarvis` 用户，不要复制或挂载整个 Host HOME，不要把 Token 写入 Company Jarvis 仓库、Construction Workspace 或镜像。

部署模式是正式部署选择，不是 scheduler failover。首次部署后只允许同模式升级；从 Native 迁移到 Docker 或反向迁移必须作为单独的停服、备份、验证和回滚项目处理，安装器不会自动完成。

同一台机器运行多个 Jarvis Box 实例时，推荐使用 Docker。每个 Docker 实例必须有独立的 deployment home、端口、runtime env file、state、workspace 和 credential 边界。Native 多实例不推荐；即使 runtime env 已选中，service lifecycle 仍需要单独证明 systemd unit 或 launchd label。完整规则见 [多实例部署](docs/multi-instance.md)。

## 3. 下载并校验 release

向 HENGSHI 申请 `hengshi-jarvis/jarvis-box` 私有 GitHub repository access 后，从该私有仓库的目标 GitHub Release 下载同一版本的：

- 当前平台 release bundle；
- `SHA256SUMS`；
- `production-image.json`。

如果 GitHub Release 下载不可用，可从公开 S3 fallback mirror 下载同名文件：

```text
https://download.hengshi.com/jarvis-box/releases/v<version>/
```

两条路径都以 `SHA256SUMS` 校验为准；mirror 可读性不替代运行时 license enforcement。

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

### Docker 镜像包：公开下载并加载

从 v0.2.30 起，Docker 镜像包可从同一个下载站直接获取，无需 GitHub 账号或 GHCR 登录。先下载与安装包相同版本、匹配 Docker 主机架构的镜像包：

```bash
version=0.2.31
arch=amd64
# Linux ARM64 或 Apple 芯片 Mac 使用 arch=arm64
base="https://download.hengshi.com/jarvis-box/releases/v$version"
image_archive="jarvis-box_${version}_linux_${arch}.docker.tar.gz"
curl -fLO "$base/$image_archive"
curl -fLO "$base/$image_archive.sha256"
sha256sum -c "$image_archive.sha256"
docker load --input "$image_archive"
```

macOS 将校验命令替换为 `shasum -a 256 -c "$image_archive.sha256"`。校验成功后才运行 `docker load`。

在 `deployment.env` 中填写导入后的镜像标签：

```dotenv
JARVIS_IMAGE=hengshi/jarvis-box:v0.2.31
```

然后按第 5 节使用同版本安装包内的部署脚本。镜像包不能代替安装包；`docker load` 只导入镜像，不创建运行中的服务。

版本目录中的 `docker-images.json` 列出镜像包 URL、SHA-256、大小、导入后的标签以及对应 GHCR source digest；`latest.json` 的 `docker_images.url` 指向最新镜像包清单。镜像包有各自的 `.sha256` 文件，安装包仍使用原来的 `SHA256SUMS`。

### GHCR 直接拉取

拥有 GHCR pull access 的客户也可继续使用 `production-image.json` 中的 `image_ref` 作为 `JARVIS_IMAGE`。这条路径需要 `docker login ghcr.io`；公开镜像包路径不需要 registry 认证。

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

### 5.1 安装或升级

从私有 GitHub Release 下载并校验 release bundle、`SHA256SUMS` 和 `production-image.json`。首次部署先创建当前用户拥有的私有 deployment home，再从 bundle 复制配置样例：

```bash
release_dir=/absolute/path/to/extracted-release
deployment_home=/absolute/deployment-home
ops="$release_dir/scripts/deploy-production.sh"

install -d -m 0700 "$deployment_home"
install -m 0600 "$release_dir/deploy/production/deployment.env.example" "$deployment_home/deployment.env"
install -m 0600 "$release_dir/deploy/production/runtime.env.example" "$deployment_home/runtime.env"
# 仅启用 IM connector 时复制并填写：
# install -m 0600 "$release_dir/deploy/production/connector.env.example" "$deployment_home/connector.env"
```

在 `deployment.env` 中把 `JARVIS_DEPLOYMENT_HOME` 改为上面的绝对路径，把 `JARVIS_IMAGE` 改为已校验并加载的 `hengshi/jarvis-box:v<version>`，或 GHCR 路径的 `production-image.json` 中的 `image_ref`，并设置当前实例唯一的 `JARVIS_DEPLOYMENT_NAME`、端口和认证选择。在 `runtime.env` 中填写所需 Agent、provider、allowlist 和 verification secret；首次保持 read-only。配置完成后执行：

```bash
"$ops" "$deployment_home" deploy
"$ops" "$deployment_home" verify
```

升级时保留原 deployment home，先校验并加载新版本镜像包，再更新 `deployment.env` 的 `JARVIS_IMAGE` 为新版本标签；GHCR 路径则使用新版本 `production-image.json` 中的 `image_ref`，然后使用新 bundle 的同一部署命令。脚本会在停服或重建前拒绝 active、waiting、finalizing、CI-wait 或 recovery-required Task，并保留客户配置和 `data/` 持久目录。

客户代码仓库需要基础镜像未包含的编译器、头文件或系统共享库时，先按[客户派生 Docker 镜像](docs/custom-docker-image.md)从当前 release 的正式 digest 构建并推送客户镜像，再把派生镜像 digest 写入 `JARVIS_IMAGE`。不要在运行中的容器里执行 `apt install`。

选择客户控制的私有绝对路径：

```text
<deployment-home>/
├── deployment.env
├── runtime.env
├── auth/              # 仅 Host 身份导入路径使用，目录 0700、文件 0600
├── data/              # Agent HOME、state、workspace、cache、logs 等持久目录
└── connector.env      # 仅启用 IM connector 时存在
```

`deployment.env` 保存已校验并加载的镜像标签或 GHCR digest 引用、绑定地址、端口和部署行为。`runtime.env` 保存 Jarvis Box 行为和 webhook/connector verification secret，不保存 provider execution token 或 Agent credential。deployment home 必须位于任意 Git checkout、`jarvis-build/` 和 Company Jarvis 源码目录之外，不保存 Host HOME dump 或临时 context。
同机多个 Docker 实例必须使用不同的 `JARVIS_DEPLOYMENT_HOME`、`JARVIS_DEPLOYMENT_NAME`、`JARVIS_PORT` 和 provider webhook URL，不共享 `auth/` 或 `data/`。

首次 onboarding 在 `runtime.env` 保持：

```dotenv
JARVIS_SERVE_MODE=read-only
JARVIS_PROVIDER_WRITEBACK_ENABLED=false
```

切换到 worker 做安装验收时也可继续保持回写关闭：Agent 和 post-check 仍运行，本地结果与审计仍保留，但不会向 GitLab、GitHub、Jira 或飞书项目原 subject 写评论、标签、状态或 review/follow-up 更新。完成隔离测试并确认 provider identity 后再显式设为 `true`。

如果客户 Runtime Foundation 提供 task-start preparer，在切换为 worker 前把容器内绝对路径写入 `runtime.env`：

```dotenv
JARVIS_AGENT_RUNTIME_PREPARE_COMMAND=/home/jarvis/.company-jarvis/bin/company-jarvis-prepare
JARVIS_AGENT_RUNTIME_PREPARE_TIMEOUT_SECONDS=120
```

该 hook 在每个新 Task 的 Workspace/provider 和依赖准备完成后、首次 Agent 启动前运行；成功后普通 `Continue` 不重复运行，首次失败或旧 Task 尚无成功 receipt 时会在 Workspace/provider 准备完成后重试。它负责检查 Company repo 默认分支 revision，并按客户自己的 ownership 规则更新 Agent discovery roots。Jarvis Box 不读取 Company repo；hook 超时、失败或响应非法时 Task 保留已准备的 Workspace，但不会启动 Agent。Native 使用服务用户可执行的 Host 绝对路径，Docker 使用持久 Agent HOME 内的容器路径。

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

部分 provider CLI 的加密文件存储还依赖容器 hostname。`deploy-production.sh` 将该机器身份保存在 `<deployment-home>/data/runtime-hostname`；首次接管旧容器时会先记录旧 hostname，再执行替换。不要绕过该脚本重建正式容器，也不要单独删除、复制或编辑该文件。持久身份与现存容器不一致时，脚本会在 `down` 前失败，需恢复匹配的完整 deployment home 或容器后再重试。

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

create-jarvis 生成的 Company Jarvis 已包含版本化的 JARVIS 记忆固化、日省和心智进化 jobs、prompts 与 scheduler manager。Runtime Agent 按模板安装，客户不需要自己编写脚本或 cron。

| 部署模式 | 唯一 scheduler owner | 调用方式 |
| --- | --- | --- |
| Native | 当前 OS 用户的 Host scheduler | 直接调用 Runtime Foundation inner job |
| Docker | Host scheduler | `deploy-production.sh ... runtime-job` → 容器内同一个 inner job |

Docker 容器内不运行第二套 scheduler。Host label 已加载也不等于健康；Docker 状态还必须证明 `runtime-job` 和容器内 inner job 可达。

onboarding 完成记录必须写明实际 Runtime Foundation root，以及当前 Company Jarvis Runtime Foundation 提供的准确 status/doctor 命令。Jarvis Box release 不提供或规定这条客户命令；它在 Docker 模式只提供通用 `runtime-job` transport。

如果状态报告的 scheduler owner 与 Jarvis Box 部署模式不一致，停止处理并修复残留，不要自动切换部署模式。

## 7. IM connector

IM 是可选能力。只在需要企业微信、飞书或钉钉等入口时设置 `JARVIS_CONNECTOR_PROFILE=uvim`，并按 release 中的 example 填写私有 `connector.env`。

Native 安装包已内置并由 installer 管理 `uv-im-connector` companion service，不需要客户单独下载二进制。把 provider secret 写入 `${JARVIS_RUNTIME_ROOT}/envs/.env.uv-im-connector`；不要写入主 `.env.jarvis-box`。

- provider-native secret 只属于 connector；
- Jarvis Box 只持有 connector URL 和 shared verification token；
- connector 不共享 Agent HOME、Git identity、Docker socket 或 Jarvis Box state；
- 禁用 connector profile 时，同时移除对应 connector service；
- 上线验收必须从真实 IM 平台发送消息并确认收到真实回复；本地模拟请求不能代替 provider 认证。

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

#### 宿主机自助升级

Docker 安装不会在宿主机安装 `jarvis-box` 命令。包含此能力的 release 会在每个 deployment home 写入独立的 `update.sh`，升级时只需运行：

```bash
bash /absolute/deployment-home/update.sh
bash /absolute/deployment-home/update.sh --version X.Y.Z
```

首次使用的旧 Docker 部署可从公开 mirror 的 `latest.json` 读取 `docker_update`，下载其中的 `url`，并用同一版本 `sha256sums_url` 指向的 `SHA256SUMS` 校验 `update.sh`。只有 `latest.json` 明确包含 `docker_update` 时才表示自助入口已经随 release 发布；没有该字段时，继续使用本节下方的手工 bundle/镜像包升级流程，不要拼接或猜测下载 URL。bootstrap 需要当前部署用户可执行的 Bash、Python 3、`curl`、`tar` 和本机 Docker Compose；它不要求宿主机有 `jarvis-box`，也不支持远程 Docker daemon。

```bash
(
set -euo pipefail
work="$(mktemp -d "${TMPDIR:-/tmp}/jarvis-box-docker-update.XXXXXX")"
trap 'rm -rf "$work"' EXIT
curl -fL https://download.hengshi.com/jarvis-box/latest.json -o "$work/latest.json"
python3 - "$work/latest.json" "$work" <<'PY'
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

latest_path, work = Path(sys.argv[1]), Path(sys.argv[2])
data = json.loads(latest_path.read_text(encoding="utf-8"))
update = data.get("docker_update") or {}
version = data.get("version")
if (not isinstance(update.get("url"), str) or
    not isinstance(data.get("sha256sums_url"), str) or
    not re.fullmatch(r"[0-9a-fA-F]{64}", str(update.get("sha256", ""))) or
    not re.fullmatch(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", str(version or ""))):
    raise SystemExit("latest release does not publish valid docker_update")
update_path, sums_path = work / "update.sh", work / "SHA256SUMS"
subprocess.run(["curl", "-fL", update["url"], "-o", str(update_path)], check=True)
subprocess.run(["curl", "-fL", data["sha256sums_url"], "-o", str(sums_path)], check=True)
manifest_sha = next((line.split()[0] for line in sums_path.read_text().splitlines()
                     if len(line.split()) >= 2 and line.split()[1].lstrip("*") == "update.sh"), "")
expected_sha = update["sha256"].lower()
if not re.fullmatch(r"[0-9a-fA-F]{64}", manifest_sha) or manifest_sha.lower() != expected_sha:
    raise SystemExit("SHA256SUMS does not match latest Docker updater metadata")
actual_sha = hashlib.sha256(update_path.read_bytes()).hexdigest()
if actual_sha != expected_sha:
    raise SystemExit("downloaded Docker updater checksum mismatch")
update_path.chmod(0o700)
subprocess.run(["bash", str(update_path), "--deployment-home", "/absolute/deployment-home", "--version", version], check=True)
PY
)
```

脚本只支持官方标准 Compose 和官方 Jarvis Box image；客户派生 image、自定义 Compose 或其他布局继续走下方手工流程。原有 Compose 文件和 profile 选择必须保留并能通过目标 release 的合同校验，脚本拒绝 downgrade，并解析当前实例和目标版本，在停服前下载、校验并加载所有需要的 release 与 Docker 制品；active、waiting、finalizing、CI-wait 或 recovery-required Task 会阻止停服。它只接管指定的已有标准 deployment home，不会调用 Native 安装器或创建新实例。升级成功后继续使用 `<deployment-home>/update.sh`；旧镜像、bundle 和完整备份会保留。目标部署已经开始后若失败，不会只替换镜像进行自动回滚，应按输出的备份和人工恢复指引处理。

执行同一个安装命令；不要直接运行 `docker compose down`、`stop` 或 `up --force-recreate`：

```bash
"$ops" "$home" deploy
"$ops" "$home" verify
```

先校验并加载目标版本镜像包，将对应标签写入 `deployment.env` 的 `JARVIS_IMAGE`；GHCR 路径则填写目标版本 `production-image.json` 中的 `image_ref`，再使用目标版本 bundle 的部署脚本。脚本会保留 deployment config 和 `data/`、使用指定镜像、重建服务并验证；最后重跑一条真实业务链路。发现 active、waiting、finalizing、CI-wait 或 recovery-required Task，无法读取 Task state，或配置属于其他 deployment home 时，部署脚本会在任何停服/重建前拒绝升级并打印阻断 Run。

只有客户明确决定放弃当前运行时，才使用：

```bash
"$ops" "$home" --force deploy
```

force 要求 jarvis-box 容器仍在运行，并要求设置 `JARVIS_DOCKER_UPGRADE_FORCE_STRATEGY` 记录客户认可的取消/恢复策略。脚本会把策略和受影响 Run 写入 `<deployment-home>/data/upgrade-preflight/` 后再停止 Run、继续服务变更。若容器不可用，先按 Task 的 Continue/Cancel/恢复路径处理，不要用 Docker shutdown 代替 Task 决策。

Docker 同模式升级必须保留完整 deployment home。部署脚本在重建前解析并固定 `data/runtime-hostname`，确保依赖容器机器身份的加密 provider profile 可继续解密；身份缺失、非法或与现存容器冲突时不会执行替换。

部署脚本在容器重建后自动更新 Jarvis 管理的官方工具；失败时保留上一套可用工具并让部署失败，修复网络或上游问题后重跑同一个部署命令。可在容器内使用 `jarvis-box tools status` 查看状态、`jarvis-box tools update` 手工重试、`jarvis-box tools reset` 回到镜像基线。客户自装的独立用户级工具放在 `/home/jarvis/.local/bin`，不要覆盖 Jarvis 管理的官方同名命令；该目录属于持久化 deployment home，升级和容器重建后仍保留。需要 `apt` 管理的编译器、头文件或系统共享库通过[客户派生 Docker 镜像](docs/custom-docker-image.md)提供。

回滚时不能只恢复旧 image digest：必须下载并校验匹配的旧版本私有 release bundle 和 image metadata，同时恢复同一 deployment home 的完整备份（包括 `auth/`、`data/connector-state/`、`data/runtime-hostname` 以及其他 `data/` 状态），再恢复对应 release tag，执行同样的部署、验证和真实链路检查。升级目标已经开始后不自动替换 image 或 state；按 updater 输出的备份与人工恢复指引操作。Company Jarvis/Runtime Foundation 的版本升级由其自身合同管理，不随 Jarvis Box 镜像偷偷变化。

## 10. 备份

Native 备份安装器报告的实际 runtime root。不要假设客户使用某个历史目录，也不要只备份当前 shell 中 `which jarvis-box` 指向的位置。

Docker 备份完整 deployment home；其中的持久数据目录包括：

- `<deployment-home>/data/agent-home`
- `<deployment-home>/data/workspaces`
- `<deployment-home>/data/state`
- `<deployment-home>/data/logs`
- `<deployment-home>/data/config`
- `<deployment-home>/data/connector-state`（启用 IM 时）
- `<deployment-home>/data/runtime-hostname`

备份可变数据前先规范停服，或使用客户批准的一致性方案。不要把备份写回 release bundle 或公共仓库。

## 11. 故障诊断

Delivery Metrics 历史基线分析使用普通 `delivery-metrics` lane Task。正在执行或等待恢复时会出现在默认 `jarvis-box tasks list`；历史排查使用 `jarvis-box tasks list --all --lane delivery-metrics`。进度、恢复入口和重试错误码见 [Delivery Metrics 历史基线操作手册](docs/delivery-metrics.md)。

| 现象 | 先看哪里 |
| --- | --- |
| Agent 无法启动或认证 | `jarvis-box doctor`、Agent smoke、实际 runtime identity |
| 历史 Task 消失 | 服务使用的实际 runtime root/state，而不是另一个空目录 |
| Task/Run 失败 | `/status`、Task state/event、Jarvis Box logs |
| GitHub/GitLab 无写回 | `JARVIS_PROVIDER_WRITEBACK_ENABLED`、provider allowlist、导入身份、真实 CLI capability |
| IM 无消息或写回 | connector health、connector logs、provider credential |
| 记忆固化/日省/心智进化不运行 | 部署模式、Host scheduler owner、Runtime Foundation status、Docker transport reachability |
| 新 Task 停在 Agent runtime prepare | Runtime Foundation prepare 命令、Company repo 网络/认证、discovery root 健康和 Task preparation event |
| Docker helper 无法进入环境 | Host operator/scheduler logs、容器状态和 inner job 是否安装 |

不要先手工修改 state 文件，不要用挂载 Host HOME 的方式修复认证。先保留 Task state、event、日志、版本、部署模式和路径证据，再处理恢复。

## 12. 安全边界

- Docker socket 默认关闭；容器 root 加 Docker socket 等价 Host root。
- Provider execution token 和 Agent credential 不进入 `runtime.env`。
- Webhook verification secret 与 Jarvis Box 到 connector 的 shared verification secret 可以保存在权限为 `0600` 的 `runtime.env`。
- IM provider secret 只属于 connector，不传给 Agent child process。
- Jarvis Box 不拥有客户知识和 workflow，不读取 Company Jarvis repo。
- `/status` 是运行诊断面，不是客户业务知识源。

## Docker 权限与备份原则

- 只用负责长期运行服务的现有普通 OS 用户部署，禁止用 `root` 或 `sudo`。
- 不创建 `jarvis` 系统用户；容器使用当前用户的数字 UID/GID。
- 所有持久化目录都在 `$JARVIS_DEPLOYMENT_HOME/data/`，由部署脚本预创建并校验所有权。
- 不使用 Docker named volume，也没有旧 volume 迁移步骤。
- 使用 `JARVIS_DEPLOYMENT_HOME=/absolute/path scripts/backup-production.sh` 停服、归档整个 deployment home 并恢复服务。
- Docker socket 是独立的高权限显式开关，默认关闭。
