# 代码归属与 Git 提交身份

Jarvis Box 可以部署在共享机器、共享容器或独立机器账号下。客户常见需求是：Jarvis 使用统一的服务身份读取 provider、写回评论或推送分支，但代码提交在 GitHub/GitLab 上归属到实际代码负责人，便于审计、工程统计和内部归属分析。

这个需求应建模为代码负责人/归属人配置，不是把 Jarvis 伪装成某个人。Jarvis Box 的 Task、Run、provider writeback 和 PR/MR 记录仍然保留 Jarvis 执行证据；Git commit identity 只表达新提交在代码仓库里的 author/committer 元数据。

## 身份模型

| 身份 | 控制内容 | 常见来源 |
| --- | --- | --- |
| Provider / push 身份 | `gh`、`glab` 或 Git credential 用谁读取、评论、推送分支 | Jarvis 机器用户、GitHub App、GitLab bot 或客户授权账号 |
| Runtime Agent 身份 | Codex、Claude 等 Agent 以哪个账号运行 | 客户持久 Agent HOME 和对应认证 |
| Git commit identity | 新 commit 的 `Author` / `Committer` 名称和邮箱 | 当前仓库 `.git/config` 的 `user.name` / `user.email`，或单次 commit 环境变量 |
| 代码负责人/归属人 | 组织希望把本次代码产出归属给谁 | 客户自有策略，例如仓库负责人、工作项 assignee、值班负责人或明确命令发起人 |
| Jarvis 执行证据 | 谁触发、哪个 Task/Run 执行、最终写回什么结果 | Jarvis Box Task state、Artifact、Status 和 provider 评论 |

`gh auth status` 或 `glab auth status` 不决定 Git commit author。Git 平台通常用 commit email 关联用户；如果要在 GitHub/GitLab UI 上显示为某个同事，`user.email` 必须是该同事在对应平台验证过的邮箱，或该平台支持的 noreply 邮箱。

## 推荐做法

在 workspace 准备阶段写当前仓库的 local Git config：

```bash
git -C "$workspace" config --local user.name "$owner_name"
git -C "$workspace" config --local user.email "$owner_email"
```

`--local` 会写入该 workspace 的 `.git/config`，只影响这个仓库后续新建的 commit。不要在共享 Jarvis 运行时里使用 `git config --global` 设置同事身份；global 配置会泄漏到同一机器上的其他 workspace 和任务。

Jarvis Box 已提供 workspace-local 准备入口：`JARVIS_WORKSPACE_DEPENDENCY_CONFIGURER`。它会在仓库 checkout 完成后、Agent 启动前调用；Agent 运行中通过 `jarvis-box workspace create` 动态新增仓库时，也会调用同一个入口。

调用格式：

```text
<program> <repo> --configure-existing <workspace> [--base-branch <branch>]
```

其中：

- `<repo>` 是仓库名，例如 `jarvis-box`；
- `<workspace>` 是已经 clone 或创建好的真实 workspace 路径；
- `--base-branch` 只在 Jarvis Box 已解析出 base branch 时出现；
- `JARVIS_PROJECT` 会在存在 project path 时提供原始值，例如 `group/project`；
- hook 失败会阻止首个 Run 启动，或让动态 `workspace create` 失败，避免 Agent 带着错误归属继续提交代码。

## 示例 configurer

下面示例使用客户维护的仓库归属策略。真实部署中可以把 `case` 替换成客户 Runtime Foundation 管理的配置文件或内部查询命令；关键是 owner 无法解析时 fail closed，不要默认落到 Jarvis 机器账号。

```bash
#!/bin/sh
set -eu

if [ "$#" -lt 3 ]; then
  echo "usage: configure-workspace <repo> --configure-existing <workspace> [--base-branch <branch>]" >&2
  exit 2
fi

repo="$1"
shift

if [ "${1:-}" != "--configure-existing" ] || [ -z "${2:-}" ]; then
  echo "usage: configure-workspace <repo> --configure-existing <workspace> [--base-branch <branch>]" >&2
  exit 2
fi

workspace="$2"
shift 2

base_branch=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --base-branch)
      base_branch="${2:-}"
      shift 2
      ;;
    *)
      echo "unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

case "$repo" in
  jarvis-box)
    owner_name="Alice Example"
    owner_email="123456+alice-example@users.noreply.github.com"
    ;;
  customer-portal)
    owner_name="Bob Example"
    owner_email="234567+bob-example@users.noreply.github.com"
    ;;
  *)
    echo "no code owner configured for repo=$repo project=${JARVIS_PROJECT:-}" >&2
    exit 20
    ;;
esac

git -C "$workspace" config --local user.name "$owner_name"
git -C "$workspace" config --local user.email "$owner_email"

printf 'configured git identity for repo=%s branch=%s\n' "$repo" "${base_branch:-unknown}"
```

配置到 `runtime.env`：

```bash
JARVIS_WORKSPACE_DEPENDENCY_CONFIGURER=<absolute-path-to-configure-workspace>
```

每个部署都必须提供自己的可执行绝对路径。Native 部署中该路径属于运行 Jarvis Box 的 OS 用户。Docker 部署中该路径必须存在于容器内的持久 Agent HOME 或客户显式挂载路径中。

## Author 与 Committer

普通 `git config --local user.name/user.email` 会让后续普通 `git commit` 的 `Author` 和 `Committer` 都使用同一个身份。这适合“本次代码产出归属到负责人”的统计模型。

如果客户需要表达“代码负责人是 Alice，但提交动作由 Jarvis 机器账号代执行”，应在客户 workflow 或 commit wrapper 中单独控制：

```bash
GIT_AUTHOR_NAME="$owner_name" \
GIT_AUTHOR_EMAIL="$owner_email" \
GIT_COMMITTER_NAME="Jarvis Bot" \
GIT_COMMITTER_EMAIL="jarvis-bot@example.com" \
git commit -m "$message"
```

这不是 Jarvis Box 默认行为；需要客户 Runtime Foundation 或 repo-local workflow 明确采用。

## 验证

在测试 workspace 中确认 local 配置来源和新 commit 元数据：

```bash
git -C "$workspace" config --show-origin --get user.name
git -C "$workspace" config --show-origin --get user.email
git -C "$workspace" show --no-patch --format='Author: %an <%ae>%nCommitter: %cn <%ce>' HEAD
```

如果发现 PR/MR 上的新 commit 显示成 Jarvis 机器账号，优先检查：

- workspace 的 `.git/config` 是否有 `user.name` / `user.email`；
- configurer 是否真的在该仓库 checkout 后运行；
- owner email 是否是 GitHub/GitLab 认可并可关联到用户的邮箱；
- 是否在 commit 前才修改配置；已存在 commit 需要 amend 或 rebase 才会改变元数据；
- 是否有 repo-local 脚本、commit wrapper 或环境变量覆盖了 Git config。

## 边界

- Git commit identity 不是 provider 权限。它不能授予读取、评论、push 或 merge 权限。
- Jarvis Box 不内置客户的人事、绩效或代码归属规则；归属策略由客户配置和 Runtime Foundation 拥有。
- 代码归属配置不应写入 secret、个人 token、SSH key、Keychain 路径或 Host HOME。
- 如果归属人无法确定，应让 workspace 准备失败，而不是默默用机器账号提交。
