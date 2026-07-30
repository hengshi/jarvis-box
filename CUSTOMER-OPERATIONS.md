# Jarvis Docker 部署与运维指南

本文面向负责部署和维护客户 Jarvis 的管理员。客户不需要 jarvis-box 源码；正式交付物是一个公开 release bundle、一个固定 digest 的 jarvis-box 镜像，以及客户自己拥有的 Company Jarvis 和代码仓库 skills。

## 1. Jarvis 生态中的身份与边界

| 对象 | 所有者 | 作用 | 是否进入客户运行环境 |
|---|---|---|---|
| Jarvis 方案方 | 衡石 | 维护建设方法、正式运行时和发布物 | 只交付公开方法与正式 release |
| 客户 | 客户 | 拥有公司资料、代码、账号、部署机器、运行数据和最终授权 | 是 |
| `hengshi-jarvis` | 衡石 | 衡石自己的 Company Jarvis，也是方法演进的真实实例 | 否；不是客户依赖 |
| 客户 `<company-slug>-jarvis` | 客户 | 保存客户身份、产品能力、source、repo fleet、跨模块关系和客户 workflow | 是，以客户批准的 commit 进入 runtime |
| 客户代码仓库中的 repo-local skills | 客户 | 保存各代码仓库的工程执行知识、验证入口和历史学习结果 | 是，以固定 repo ref/commit 被 runtime 使用 |
| GitHub `hengshi/create-jarvis` | 衡石公开维护 | 供客户 Host Agent clone 的建设方法；协调 Company construction、Repository learning、workflow construction 和正式部署 | 只在建设阶段由 Host Agent 使用 |
| 衡石内部 jarvis-box GitLab 源码仓库 | 衡石 | jarvis-box 开发、测试、CI 和正式发布的 source of truth | 否；客户拿不到也不需要源码 |
| GitHub `hengshi/jarvis-box` | 衡石公开维护 | 客户发布窗口；提供版本说明和 release assets | 客户只消费 Releases，不 clone 源码 |
| jarvis-box release bundle | 衡石发布、客户持有 | 包含宿主机 binary、`compose.yaml`、部署脚本、配置模板和本文 | 是，保存在客户运维目录 |
| jarvis-box OCI image | 衡石发布、客户运行 | 包含 jarvis-box、Codex、Claude、Git 工具链和固定版本的 uv-im-connector | 是，由 Docker 按 digest 拉取 |
| uv-im-connector | 衡石维护、客户配置 | 连接飞书、企业微信、钉钉等 IM provider，保存 provider 原生凭据并提供统一消息/资源协议 | binary 已包含在 jarvis-box image；Compose 以独立服务运行 |

`create-jarvis` 与 `jarvis-box` 不是两个需要客户分别安装的软件。前者是 Host Agent 使用的建设方法，后者是建设结果达到可运行边界后的正式数字员工 runtime。

```text
客户 Host Agent + create-jarvis
  → 客户 Company Jarvis
  → 客户 repo-local skills
  → 客户 workflow
  → 固定 commits 与 image digest
  → jarvis-box Docker Compose
  → supervised shadow
  → active digital employee
```

## 2. 一个镜像、一个 Compose 项目、两个服务

客户只拉取一个 `JARVIS_IMAGE`。该镜像同时包含 `jarvis-box` 和 `uv-im-connector` 两个 executable。Compose 根据同一个 image digest 启动两个服务：

```text
Jarvis Compose project
├── jarvis-box
│   ├── server 与 Runtime Agent
│   ├── Company Jarvis 与 repo routing
│   ├── Task / Run / workspace / logs
│   └── Codex、Claude、gh、glab、Git 和工程工具链
└── uv-im-connector（可选 profile：uvim）
    ├── IM provider 长连接或 webhook
    ├── provider 原生凭据
    └── IM event 与 resource state
```

两个服务使用 Compose 私有网络通信。jarvis-box 默认访问 `http://uv-im-connector:8787`，两边使用相同的 shared token。connector 不挂载 Agent home、Git credentials、Company snapshot 或 Docker socket。

## 3. 客户拥有的三类本地数据

不要混淆 release 文件、deployment home 和 Docker volumes：

```text
<operator-root>/
├── releases/
│   └── <version>/                 # 解压后的只读 release bundle
└── deployments/
    └── <deployment-name>/         # 客户私有 deployment home
        ├── deployment.env
        ├── company-context.json
        ├── company/               # Company commit 的干净导出
        ├── runtime.env
        ├── connector.env
        └── lock/

Docker named volumes
├── jarvis-agent-home              # 正式 Codex/Claude、gh/glab 身份
├── jarvis-workspaces              # Task workspaces
├── jarvis-config                  # runtime 生成配置
├── jarvis-state                   # Task/Run state
├── jarvis-logs                    # runtime logs
└── connector-state                # IM events/resources
```

- release directory 随版本新增，不在原目录中覆盖升级。
- deployment home 由客户控制，包含部署事实和 secret 配置，不提交到 Company 或代码仓库。
- named volumes 保存容器重建后仍需保留的身份与运行数据。

## 4. 部署前提

部署机器需要：

- Linux amd64/arm64 或 macOS Intel/Apple Silicon；
- Docker Engine 或 Docker Desktop；
- Docker Compose v2，可通过 `docker compose version` 验证；
- 能访问 jarvis-box 下载地址、OCI registry、客户 Git provider 和所选 IM provider；
- 一个客户明确选择的私有绝对 deployment home；
- 客户 Company Jarvis 的批准 commit；
- workflow 所需 repo-local skills 的远端 ref 和 exact commit；
- 至少一个已经达到 `construction-ready` 的客户 workflow；
- 客户批准的正式 Agent identity 和 capability scope。

Docker socket 默认不挂载。只有客户 workflow 确实需要控制宿主 Docker daemon 且客户明确批准时才启用；该能力等价于宿主 root。

## 5. 下载 release bundle，不下载源码

在 [GitHub Releases](https://github.com/hengshi/jarvis-box/releases) 选择目标版本，并按部署机器选择一个 tarball：

| 部署机器 | artifact 后缀 |
|---|---|
| Linux x86_64 | `linux_amd64.tar.gz` |
| Linux arm64/aarch64 | `linux_arm64.tar.gz` |
| macOS Intel | `darwin_amd64.tar.gz` |
| macOS Apple Silicon | `darwin_arm64.tar.gz` |

同时下载 `SHA256SUMS` 和 `production-image.json`。例如：

```bash
version=<X.Y.Z>
artifact=jarvis-box_${version}_linux_amd64.tar.gz

curl -fLO "https://github.com/hengshi/jarvis-box/releases/download/v${version}/${artifact}"
curl -fLO "https://github.com/hengshi/jarvis-box/releases/download/v${version}/SHA256SUMS"
curl -fLO "https://github.com/hengshi/jarvis-box/releases/download/v${version}/production-image.json"

grep -E " (${artifact}|production-image[.]json)$" SHA256SUMS | sha256sum -c -
tar -xzf "$artifact"
```

macOS 使用：

```bash
grep -E " (${artifact}|production-image[.]json)$" SHA256SUMS | shasum -a 256 -c -
```

解压后，首次部署脚本位于：

```text
<release-dir>/scripts/deploy-production.sh
```

它是 release bundle 的正式组成部分，不来自 jarvis-box 源码 checkout。

## 6. 准备 deployment home

从 release bundle 复制模板到客户选择的私有绝对路径：

```bash
release_dir=/absolute/path/to/jarvis-box_<version>_<os>_<arch>
deployment_home=/absolute/path/to/<company>-jarvis-production

mkdir -p "$deployment_home/company" "$deployment_home/lock"
cp "$release_dir/deploy/production/deployment.env.example" "$deployment_home/deployment.env"
cp "$release_dir/deploy/production/runtime.env.example" "$deployment_home/runtime.env"
cp "$release_dir/deploy/production/connector.env.example" "$deployment_home/connector.env"
cp "$release_dir/deploy/production/company-context.example.json" "$deployment_home/company-context.json"
chmod 600 "$deployment_home"/*.env "$deployment_home/company-context.json"
chmod 700 "$deployment_home/lock"
```

### 6.1 Company snapshot

`company/` 必须是批准 commit 的干净导出，不能绑定 Host Agent 的 dirty checkout，也不能包含 `.git`：

```bash
company_checkout=/absolute/path/to/clean-company-checkout
company_commit=<approved-commit>

git -C "$company_checkout" archive "$company_commit" | tar -x -C "$deployment_home/company"
```

使用 release binary 计算 tree digest：

```bash
"$release_dir/jarvis-box" jarvis digest "$deployment_home/company"
```

把结果和批准 commit 写入 `company-context.json`。

### 6.2 `deployment.env`

从 `production-image.json` 读取完整的 `repository@sha256:...`，不要使用 `latest` 或普通 tag：

```dotenv
JARVIS_DEPLOYMENT_NAME=<company>-jarvis-production
JARVIS_DEPLOYMENT_HOME=/absolute/path/to/<company>-jarvis-production
JARVIS_IMAGE=registry.example.com/jarvis-box@sha256:<64-hex>
JARVIS_BIND_ADDRESS=127.0.0.1
JARVIS_PORT=8787
JARVIS_ENABLE_DOCKER_SOCKET=0
```

uv-im-connector 已包含在 `JARVIS_IMAGE` 中，不存在 `UVIM_IMAGE` 配置。
connector profile 不属于 `deployment.env`；部署脚本只从 canonical `runtime.env` 读取它。

### 6.3 `runtime.env`

选择 Codex 或 Claude，并只填写本部署需要的 provider/source allowlist：

```dotenv
JARVIS_RUNTIME_AGENT=codex
JARVIS_CONNECTOR_PROFILE=uvim
JARVIS_UV_IM_CONNECTOR_NAME=uvim
JARVIS_UV_IM_CONNECTOR_URL=http://uv-im-connector:8787
JARVIS_UV_IM_CONNECTOR_TOKEN=<random-shared-token>
```

`JARVIS_CONNECTOR_PROFILE` 是 connector service 与 jarvis-box client 的唯一启用开关：设为 `uvim` 时同一个 `runtime.env` 必须配置 URL；设为空时，即使文件里仍有 URL，runtime 也不会连接 connector，部署脚本还会移除旧 connector container。不要在 `deployment.env` 重复声明。

GitHub/GitLab、Agent 和 source 的交互式登录保存在持久 Agent home 中，不要把 Host 用户的整个 home、SSH agent 或 credential store 挂入容器。

### 6.4 `connector.env`

`UV_IM_AUTH_TOKEN` 必须与 `JARVIS_UV_IM_CONNECTOR_TOKEN` 完全一致。provider 原生 secret 只进入该文件。

飞书示例：

```dotenv
UV_IM_PROVIDERS=lark
UV_IM_AUTH_TOKEN=<same-random-shared-token>
UV_LARK_CONNECTOR_ID=main
UV_LARK_APP_ID=<app-id>
UV_LARK_APP_SECRET=<app-secret>
UV_LARK_REGION=feishu
```

企业微信示例：

```dotenv
UV_IM_PROVIDERS=wecom
UV_IM_AUTH_TOKEN=<same-random-shared-token>
UV_WECOM_CONNECTOR_ID=main
UV_WECOM_BOT_ID=<bot-id>
UV_WECOM_BOT_SECRET=<bot-secret>
```

其他 provider 的变量遵循 `UV_<PROVIDER>_*` 命名，并以 uv-im-connector 对应版本的配置文档为准。

### 6.5 `company-context.json`

该文件不保存 secret。它锁定：

- Company slug/name、批准 commit、tree digest 和 entry skill；
- 正式 Agent identity、runtime、credential profile 与 `authority: high`；
- 每个 required repository 的 canonical remote、fetchable ref、exact commit、repo-local entry 和读写要求；
- 准备部署的 workflow skill 与 `ready-for-shadow` 目标状态；
- 唯一的 `images.jarvis_box` digest。

uv-im-connector 是该 jarvis-box image 的内置组件，不需要单独的 connector image 字段。

## 7. 首次启动、登录和验证

首次启动会拉取同一个 jarvis-box image，并按 profile 启动 jarvis-box 与 uv-im-connector：

```bash
"$release_dir/scripts/deploy-production.sh" "$deployment_home" start
```

此时 health、日志和登录 shell 可用，但业务写入口保持 `deployment_not_ready`。

进入持久化的正式 Agent home：

```bash
"$release_dir/scripts/deploy-production.sh" "$deployment_home" shell
```

在容器内完成客户选择的正式身份登录，例如：

```bash
codex login
gh auth login
glab auth login --hostname <customer-gitlab-host>
```

退出 shell 后执行：

```bash
"$release_dir/scripts/deploy-production.sh" "$deployment_home" verify
```

`verify` 会验证 Company snapshot、workflow、repository refs、写权限、Agent smoke、内置 connector 版本、IM protocol、持久化和可选 Docker socket。全部通过后才写入：

```text
<deployment-home>/lock/deployment-lock.json
```

随后 jarvis-box 重启并进入 `ready-for-shadow`。验证失败不会生成新的 lock。

## 8. 客户手工 Docker Compose 运维

部署脚本用于首次 promotion、配置变更、凭据轮换和升级验证。状态、日志以及不改变容器配置的日常启停可以直接使用 Docker Compose。

每次打开新的运维 shell，先加载 deployment 配置：

```bash
release_dir=/absolute/path/to/jarvis-box_<version>_<os>_<arch>
deployment_home=/absolute/path/to/<company>-jarvis-production

test -f "$release_dir/compose.yaml"
test -f "$deployment_home/deployment.env"

set -a
. "$deployment_home/deployment.env"
set +a
export COMPOSE_PROJECT_NAME="${JARVIS_DEPLOYMENT_NAME:-jarvis-production}"

# 所有手工命令都由部署脚本加载同一组 Compose files/profile。
jarvis_compose() {
  "$release_dir/scripts/deploy-production.sh" "$deployment_home" compose "$@"
}
```

以上代码可在 Bash 中直接执行。`compose` action 与 `deploy/start/verify` 共用同一个 `runtime.env` parser，会接受 Compose `env_file` 支持的 `export`、引号和空白形式，并自动加入当前 `uvim` profile 与 Docker socket overlay。随后使用同一个 `jarvis_compose` helper：

```bash
# 查看两个服务的状态
jarvis_compose ps

# 查看所有日志
jarvis_compose logs -f --tail=200

# 分别查看日志
jarvis_compose logs -f --tail=200 jarvis-box
jarvis_compose logs -f --tail=200 uv-im-connector

# 不改变 image/env/mount 的进程重启
jarvis_compose restart

# 停止但保留容器和数据
jarvis_compose stop

# 重新启动同一批已存在、配置未变的容器
jarvis_compose start

# 删除容器和网络，但保留 named volumes
jarvis_compose down
```

不要把普通运维写成 `docker compose down -v`。`-v` 会删除正式 Agent identity、Task/Run state、workspaces、logs 和 connector state。

`restart` 和 `start` 不重新读取 `env_file`。执行过 `down`，或者修改了 image、env、mount、profile、identity/credential 后，不要直接 `up -d`；重新走 fail-closed 的部署边界：

```bash
"$release_dir/scripts/deploy-production.sh" "$deployment_home" start
"$release_dir/scripts/deploy-production.sh" "$deployment_home" verify
```

## 9. 健康检查与故障诊断

宿主机检查：

```bash
curl -fsS "http://${JARVIS_BIND_ADDRESS:-127.0.0.1}:${JARVIS_PORT:-8787}/health"
jarvis_compose ps
jarvis_compose logs --tail=200
```

容器内诊断：

```bash
"$release_dir/scripts/deploy-production.sh" "$deployment_home" shell

jarvis-box jarvis validate
jarvis-box jarvis show
jarvis-box agent doctor
jarvis-box agent smoke
jarvis-box status
jarvis-box doctor
```

常见定位顺序：

1. `docker compose ps`：容器是否存在、是否 healthy；
2. jarvis-box logs：Company context、deployment lock、Agent 或 repository 错误；
3. connector logs：IM app credential、长连接、webhook 或 provider API 错误；
4. `agent doctor`：CLI 和配置是否存在；
5. `agent smoke`：正式 Agent 账号是否仍可用；
6. 修改配置或轮换身份后重新执行 `verify`。

Compose 使用 `restart: unless-stopped`。Linux 上需要 Docker daemon 随系统启动；macOS 上需要 Docker Desktop 已启动。管理员显式执行 `stop` 后，在配置未变时用 `jarvis_compose start` 恢复。

## 10. 升级

升级不是在运行容器中执行 `apt install`、覆盖 binary 或拉取 floating tag。正式升级使用“版本化 release directory + 版本化 deployment home + 稳定 Compose project”模型：新的配置和 Company snapshot 放在新目录，同一个 `JARVIS_DEPLOYMENT_NAME` 让新旧版本复用原 named volumes；任何时刻只运行其中一个 deployment home。

1. 按第 12 节备份当前 deployment home 和 named volumes；
2. 下载并校验新 release bundle；
3. 按第 6 节创建新的 deployment home 和干净 Company snapshot/context；
4. 写入 `production-image.json` 中的新 image digest；
5. 保持 `JARVIS_DEPLOYMENT_NAME` 与旧部署完全相同，`JARVIS_DEPLOYMENT_HOME` 改为新目录；
6. 从新 release directory 执行 `deploy`。

```bash
old_release_dir="$release_dir"
old_deployment_home="$deployment_home"
stable_project="$COMPOSE_PROJECT_NAME"

new_release_dir=/absolute/path/to/new-release
new_deployment_home=/absolute/path/to/new-versioned-deployment-home

# new_deployment_home/deployment.env 中必须满足：
# JARVIS_DEPLOYMENT_NAME=$stable_project
# JARVIS_DEPLOYMENT_HOME=$new_deployment_home

"$new_release_dir/scripts/deploy-production.sh" "$new_deployment_home" deploy

# 新 deployment 已验证后，使旧目录中的 promotion evidence 失效；
# 回滚仍使用 deploy 重新生成，而不是复用旧 lock。
rm -f -- "$old_deployment_home/lock/deployment-lock.json"
```

`deploy` 会先用包含所有 profile 的 Compose 视图关闭并移除整个旧 project，再使候选 deployment home 中的 lock 失效、拉取新 digest、只按 `runtime.env` 的当前 profile 强制重建同一 Compose project，最后验证新 deployment set。把 `JARVIS_CONNECTOR_PROFILE` 从 `uvim` 改为空时，这一步会移除仍持有旧凭据的 connector；拉取或验证失败时也不会让旧进程继续带着内存中的 ready 状态工作。

一个 jarvis-box image digest 同时固定 jarvis-box 与 uv-im-connector。客户不单独升级 connector；兼容组合由正式 release 选择和验证。

## 11. 回滚

至少保留上一版的：

- release directory；
- deployment home 或完整只读备份；
- `deployment-lock.json` 的只读备份（旧活动目录中的 lock 在切换成功后删除）；
- image digest；
- Company/repo commits；
- named volume backup。

未发生不兼容数据迁移时，回滚使用旧 release directory 和旧 deployment home，继续复用同一个稳定 Compose project/named volumes：

```bash
"$old_release_dir/scripts/deploy-production.sh" "$old_deployment_home" deploy
```

该命令停止当前版本，按旧 image/context 强制重建并重新验证。若新版本 release notes 声明了不兼容的数据迁移，则必须先停止当前项目，再从升级前备份恢复 named volumes；不能让旧 binary 直接读取已迁移的新数据。不要只改 image tag，也不要把新 Company context 与旧 binary 随意组合。

## 12. 备份与恢复

备份必须同时覆盖：

1. deployment home；
2. 当前 Compose project 的 named volumes；
3. 客户 secret-management 系统中保存的原始 secret 或恢复凭据。

先通过以下命令确认 project 与 volume 名称：

```bash
jarvis_compose ps
docker volume ls --filter "label=com.docker.compose.project=$COMPOSE_PROJECT_NAME"
```

release bundle 中的备份脚本会停止当前 Compose project、归档 deployment home 和全部 project-owned named volumes、生成 `SHA256SUMS`，再重新启动原容器。volume 内容由容器 root 读取，但 tar stream 由宿主运维用户以 `umask 077` 创建，因此不会在 rootful Linux 上留下无法收紧权限的 `root:root 0644` 凭据归档。

`backup_root` 必须是 deployment home 之外的受限目录，最好位于另一块磁盘或客户备份系统中：

```bash
backup_root=/absolute/path/to/secure-backups
backup_dir="$(
  "$release_dir/scripts/backup-production.sh" \
    "$deployment_home" \
    "$backup_root"
)"
echo "backup completed: $backup_dir"
```

备份中包含正式 Agent identity、Git credentials 和 provider secret。完成后应加密或移入客户备份系统，不要上传到 Company Jarvis、代码仓库或普通工单附件。

恢复演练必须使用空的新 deployment home、新的 Compose project 和随机宿主端口。新项目可以在原项目运行时完成文件和 volume 恢复，但在启动任何恢复服务前必须停止原项目，避免两个数字员工同时消费同一 provider 事件。

```bash
set -euo pipefail

original_release_dir="$release_dir"
original_deployment_home="$deployment_home"

release_dir=/absolute/path/to/the-matching-jarvis-box-release
backup_dir=/absolute/path/to/one-verified-backup
restore_home=/absolute/path/to/new-restore-home
restore_project=<company>-jarvis-restore-test

test ! -e "$restore_home" || {
  echo "restore_home already exists: $restore_home" >&2
  exit 2
}

(
  cd "$backup_dir"
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum -c SHA256SUMS
  else
    shasum -a 256 -c SHA256SUMS
  fi
)

mkdir -p "$restore_home"
chmod 700 "$restore_home"
tar -C "$restore_home" -xzf "$backup_dir/deployment-home.tar.gz"

# 替换恢复实例的 home/project，并使用随机宿主端口避免端口冲突。
python3 - "$restore_home/deployment.env" "$restore_home" "$restore_project" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
replacement = {
    "JARVIS_DEPLOYMENT_HOME": sys.argv[2],
    "JARVIS_DEPLOYMENT_NAME": sys.argv[3],
    "JARVIS_PORT": "0",
}
seen = set()
result = []
for line in path.read_text(encoding="utf-8").splitlines():
    key = line.split("=", 1)[0]
    if key in replacement:
        result.append(f"{key}={replacement[key]}")
        seen.add(key)
    else:
        result.append(line)
for key, value in replacement.items():
    if key not in seen:
        result.append(f"{key}={value}")
path.write_text("\n".join(result) + "\n", encoding="utf-8")
PY

deployment_home="$restore_home"
set -a
. "$deployment_home/deployment.env"
set +a
export COMPOSE_PROJECT_NAME="$JARVIS_DEPLOYMENT_NAME"

restore_compose() {
  "$release_dir/scripts/deploy-production.sh" "$deployment_home" compose "$@"
}

# create 只创建容器和 nocopy named volumes，不启动服务。
restore_compose create

for archive in "$backup_dir"/volumes/*.tar.gz; do
  logical="$(basename "$archive" .tar.gz)"
  target="$(docker volume ls \
    --filter "label=com.docker.compose.project=$COMPOSE_PROJECT_NAME" \
    --filter "label=com.docker.compose.volume=$logical" \
    --format '{{.Name}}')"
  test -n "$target" || {
    echo "restore target volume not found: $logical" >&2
    exit 1
  }
  docker run --rm \
    --env "ARCHIVE=${logical}.tar.gz" \
    --mount "type=volume,src=$target,dst=/target" \
    --mount "type=bind,src=$backup_dir/volumes,dst=/backup,readonly" \
    --entrypoint sh \
    "$JARVIS_IMAGE" -ceu \
    'test -z "$(find /target -mindepth 1 -maxdepth 1 -print -quit)"; tar -C /target -xzf "/backup/$ARCHIVE"'
done

# 恢复数据完成后才停止原项目，确保只有一个项目连接外部 provider。
# stop 或 lock invalidation 任一步失败都禁止启动恢复项目。
if ! (
  set -euo pipefail
  "$original_release_dir/scripts/deploy-production.sh" \
    "$original_deployment_home" \
    compose stop
  rm -f -- "$original_deployment_home/lock/deployment-lock.json"
); then
  echo "original deployment did not stop cleanly; restore project will not start" >&2
  exit 1
fi

# start 先使备份中的旧 lock 失效并强制重建；verify 重新证明恢复实例。
if ! "$release_dir/scripts/deploy-production.sh" "$deployment_home" start \
  || ! "$release_dir/scripts/deploy-production.sh" "$deployment_home" verify; then
  echo "restore verification failed; returning to the original deployment" >&2
  if ! restore_compose down; then
    echo "restore project is still running; refusing to start the original deployment" >&2
    exit 1
  fi
  "$original_release_dir/scripts/deploy-production.sh" "$original_deployment_home" deploy
  exit 1
fi
```

以上命令会在恢复启动或验证失败时自动关闭恢复项目并回切原 deployment。如果终端或宿主机在自动回切前中断，重新加载恢复项目配置将其 `down`，再用原完整 deployment set 恢复服务：

```bash
restore_compose down \
  && "$original_release_dir/scripts/deploy-production.sh" "$original_deployment_home" deploy
```

恢复演练成功后必须二选一：

- 仅做演练：执行上面的两条命令，回到原项目；
- 把恢复项目作为正式 failover：保持原项目停止，在 `restore_home/deployment.env` 中把 `JARVIS_PORT=0` 改为批准的正式端口，再对恢复项目重新执行 `deploy`。绝不能同时启动原项目。

`nocopy` 是正式 Compose volume contract 的一部分，保证新 restore volume 不从镜像目录预填数据；恢复脚本仍会拒绝覆盖任何非空目标 volume。

## 13. 凭据轮换

`docker compose restart` 不会重新读取 `env_file`，删除 lock 也不能改变已经运行进程的内存状态。所有轮换和 profile 切换统一使用 `deploy-production.sh start`：它先清理完整旧 project（包括当前配置已隐藏的旧 profile service），再删除 lock、拉取固定 digest 并按当前 profile 强制重建服务；验证成功前业务始终 fail closed。

- Codex/Claude、gh/glab 或 source identity：先执行 `start`，进入 `shell` 完成 provider-native 轮换，再 `verify`；
- IM app secret：修改 `connector.env` 后执行 `start` 和 `verify`；
- shared token：同步修改 `runtime.env` 与 `connector.env` 后执行 `start` 和 `verify`；
- webhook secret：同步修改 runtime 配置和外部 sender 后执行 `start` 和 `verify`。

```bash
"$release_dir/scripts/deploy-production.sh" "$deployment_home" start

# 仅当本次轮换需要交互式 provider-native 登录时执行：
"$release_dir/scripts/deploy-production.sh" "$deployment_home" shell

"$release_dir/scripts/deploy-production.sh" "$deployment_home" verify
```

不要打印、提交或复制 credential value 到 Company Jarvis、代码仓库、construction journal、deployment lock 或运维工单。

## 14. 卸载与数据保留

仅删除运行容器和网络、保留全部数据：

```bash
jarvis_compose down
```

永久删除前必须明确确认已经备份 deployment home 和所有 named volumes。`down -v`、删除 deployment home 或删除 release directory 是三个不同动作，不要把它们组合成一个无确认的清理命令。

## 15. 客户与 Host Agent 的协作方式

客户可以完全手工维护，也可以让已授权的 Host Agent读取本文后执行同样的操作。Agent 可以自动完成下载、校验、生成配置、启动和诊断，但以下动作必须由客户明确批准或参与：

- 正式 Agent identity 的权限范围；
- Codex/Claude、GitHub/GitLab、registry 和 source 的交互式登录；
- IM provider app/bot 的创建及原生 secret；
- Docker socket 等宿主 root-equivalent 能力；
- shadow → active promotion；
- 删除 volume、deployment home 或其他不可恢复数据。

无论由人还是 Agent 操作，运行事实都来自同一个 release bundle、deployment home、image digest 和 deployment lock。
