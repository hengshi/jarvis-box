# 代码归属与 Git 提交身份

本文面向共享 Jarvis Box 运行时的客户管理员和 Runtime Foundation 集成方。它解决“服务用统一账号工作，但新 commit 应归属实际代码负责人”的问题。它不授予 GitHub/GitLab 权限，也不改变 Jarvis Box 的 Task、Run 或 provider 写回审计。

<a id="身份模型"></a>

## 先区分四种身份

| 身份 | 决定什么 | 例子 |
| --- | --- | --- |
| Provider / push 身份 | 读取、评论、push、merge 的权限 | `gh`、`glab`、Git credential、App 或 bot |
| Runtime Agent 身份 | Agent CLI 如何认证和运行 | 持久 Agent HOME 中的 Codex、Claude 等登录 |
| Git commit identity | 新 commit 的 `Author` 和 `Committer` 元数据 | 当前仓库 `.git/config` 的 `user.name`、`user.email` |
| 代码负责人 | 客户要把这次代码产出归属给谁 | assignee、仓库负责人或明确的任务发起人 |

`gh auth status` 和 `glab auth status` 不决定 commit author。若要让 GitHub/GitLab UI 将 commit 显示为某位同事，所用 email 必须能由该平台关联到那位同事（例如已验证邮箱或支持的 noreply 邮箱）。

<a id="推荐做法"></a>

## 推荐：在 workspace 写 local Git 配置

准备完 checkout 后，为当前 workspace 写 local 配置：

```bash
git -C "$workspace" config --local user.name "$owner_name"
git -C "$workspace" config --local user.email "$owner_email"
```

`--local` 只写当前仓库的 `.git/config`。不要在共享运行时用 `git config --global` 冒充同事：它会影响其他 Task 和 workspace。

Jarvis Box 为此提供 `JARVIS_WORKSPACE_DEPENDENCY_CONFIGURER`。它会在 checkout 后、Agent 启动前调用；Agent 在运行中使用 `jarvis-box workspace create` 新建仓库时，也会调用同一入口。将该变量写到实例实际生效的 canonical runtime env：`JARVIS_ENV_FILE` 指向的文件，默认为 `$JARVIS_RUNTIME_ROOT/envs/.env.jarvis-box`。

调用形式固定为：

```text
<program> <repo> --configure-existing <workspace> [--base-branch <branch>]
```

其中 `<repo>` 是仓库名；`<workspace>` 是已存在的真实 workspace 路径。若 base branch 已解析，才会传递 `--base-branch`。有 project path 时，环境变量 `JARVIS_PROJECT` 保留原始值（如 `group/project`）。配置程序失败会阻止首次 Run 启动，或让动态 workspace 创建失败；不要在负责人未知时静默回退到机器账号。

Docker 中，程序必须是持久 Agent HOME 或客户明确挂载路径中、容器可执行的绝对路径。Native 中，它必须由运行 Jarvis Box 的 OS 用户执行。配置本身见[配置参考](configuration.md#workspace-准备程序)。

<a id="示例-configurer"></a>

## 一个可审查的配置程序

下面是最小示例。真实客户可以把 `case` 替换为自己的版本化归属策略或内部查询，但找不到负责人时应退出失败。

```sh
#!/bin/sh
set -eu

usage='usage: configure-workspace <repo> --configure-existing <workspace> [--base-branch <branch>]'
[ "$#" -ge 3 ] || { echo "$usage" >&2; exit 2; }

repo="$1"
shift
[ "${1:-}" = '--configure-existing' ] && [ -n "${2:-}" ] || {
  echo "$usage" >&2; exit 2;
}
workspace="$2"
shift 2

base_branch=''
while [ "$#" -gt 0 ]; do
  [ "$1" = '--base-branch' ] && [ "$#" -ge 2 ] || {
    echo "$usage" >&2; exit 2;
  }
  base_branch="$2"
  shift 2
done

case "$repo" in
  customer-portal)
    owner_name='Alice Example'
    owner_email='123456+alice-example@users.noreply.github.com'
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

Set it with an absolute path:

```dotenv
JARVIS_WORKSPACE_DEPENDENCY_CONFIGURER=/absolute/path/to/configure-workspace
```

Do not store tokens, SSH keys, Keychain paths or a Host HOME path in this program or its configuration.

<a id="author-与-committer"></a>

## Author and Committer may differ

The local Git configuration above makes ordinary `git commit` use the same identity for author and committer. That is usually the clearest model for ownership reporting.

If the customer deliberately needs “Alice authored it; Jarvis Bot performed the commit,” their workflow must set both pairs immediately for that commit:

```bash
GIT_AUTHOR_NAME="$owner_name" \
GIT_AUTHOR_EMAIL="$owner_email" \
GIT_COMMITTER_NAME='Jarvis Bot' \
GIT_COMMITTER_EMAIL='jarvis-bot@example.com' \
git commit -m "$message"
```

This is customer workflow behavior, not a Jarvis Box default.

<a id="验证"></a>

## Verify and troubleshoot

In a test workspace, inspect the source of the active setting and the newest commit:

```bash
git -C "$workspace" config --show-origin --get user.name
git -C "$workspace" config --show-origin --get user.email
git -C "$workspace" show --no-patch --format='Author: %an <%ae>%nCommitter: %cn <%ce>' HEAD
```

If a PR/MR still shows the machine account, check the local config, whether the configurer ran after checkout, whether the email is platform-recognized, and whether a repo script or environment variable overrode Git config. Existing commits require amend or rebase to change metadata.

<a id="边界"></a>

## 边界

Commit identity remains metadata: it cannot grant provider read, comment, push or merge access. Jarvis Box also does not invent customer personnel or ownership policy; that decision belongs to the customer Runtime Foundation or repository policy.
