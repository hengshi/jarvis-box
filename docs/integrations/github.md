# GitHub 接入

GitHub provider loop 用于把 GitHub issue comment 和 pull request 事件接入 Jarvis Box。

## 当前支持

| 事件 | 行为 |
| --- | --- |
| `issue_comment` | 评论包含 command mention，例如 `/jarvis`、`@jarvis` 或 `@jarvis-box` 时进入 command lane；没有 mention 且 subject 是 PR 时进入 follow-up lane；普通 issue 评论不触发 follow-up |
| `pull_request` | `opened`、`reopened`、`synchronize`、`ready_for_review` 进入 PR review lane；`closed` 先按 `merged` 归一为 Task `close/merge` 终态 |
| `pull_request_review` | `submitted` 且 review state 为 `changes_requested` 或 `commented`、正文非空时进入 follow-up lane |
| `pull_request_review_comment` | 新建的 PR inline review comment 进入 follow-up lane |
| `issues` | `opened` 在开启 `JARVIS_ISSUE_POST_CHECK_ENABLED` 后进入 post-check；其他非终态 update 不会重跑；`closed` 会终态化创建时绑定到该 issue 的 Task |

PR draft、未在 allowlist 内的仓库、重复 delivery、Jarvis marker、bot 自己的评论、空 review 和 `approved` review 会被跳过。`issue_comment` 先匹配 command，命中 mention 时不会重复进入 follow-up。

GitHub 与 GitLab 共用 provider-neutral `FollowupDispatcher` 状态机；provider adapter 只负责 webhook 归一化、实时 PR/MR 读取和状态评论写回。状态 identity 包含 provider、repository/project 和 PR/MR number，因此两个代码托管平台不会共用去重状态。GitHub fork PR 仍以 target repository + PR number 作为评论和状态写回目标，同时从 GitHub 实时 PR 数据取得 head repository clone URL 与 source branch，独立 checkout source workspace；运行身份没有 fork source branch 的读取或推送权限时，follow-up 会显式失败，不会静默改写 target repository。

GitHub issue/PR URL 在 Task 创建 claim 中登记为规范化 `task-state.subject`。`issues.closed` 和 `pull_request.closed` 只按该登记精确匹配已有 Task，然后走统一的进程终止和 `workspaces[]` 清理；不从 branch、Artifact 或目录名推断。Terminal delivery 在任何终态副作用前先持久化 Task 登记序号 cutoff 和不可变实例快照，retry 只重放该快照，不会清理 delivery 之后启动的任务或同路径的新 Task 实例。

## 配置运行时 env

生产启用 GitHub command lane 前，先确定三类 allowlist：

- repo allowlist：哪些 GitHub 仓库允许进入 Jarvis。
- review repo allowlist：哪些 GitHub 仓库允许 PR review lane。
- shared mention names：哪些文本触发 command lane，例如 `JARVIS_MENTION_NAMES=jarvis,jarvis-box`。
- command user allowlist：哪些 GitHub 用户允许通过 issue/PR comment 触发 command lane。

公开 GitHub 仓库必须配置 command user allowlist。GitHub HMAC 只证明 webhook 由 GitHub 发送，不证明评论作者是可信用户；公开仓库中的任意 GitHub 用户都可能产生合法 webhook。GitHub command user allowlist 支持 login 和 immutable numeric user id，生产推荐只写 numeric user id。

有组织成员读取权限时，可用 `gh` 获取成员 login 和 id：

```bash
gh api "orgs/OWNER/members?per_page=100" --paginate \
  --jq '.[] | [.login, (.id|tostring)] | @tsv'
```

如果组织成员列表受限，由组织管理员提供允许触发者 login 后逐个查询：

```bash
gh api users/LOGIN --jq '.id'
```

把真实配置写入 `JARVIS_ENV_FILE` 指向的运行时 env 文件，不要覆盖 sample：

```bash
GITHUB_REPOSITORIES=owner/repository
REVIEW_GITHUB_REPOSITORIES=owner/repository
GITHUB_WEBHOOK_SECRET=<shared-secret>
JARVIS_MENTION_NAMES=jarvis,jarvis-box
JARVIS_GITHUB_COMMAND_ALLOWED_USERS=301658716,2253581,1201463
GH_CMD=gh
```

`REVIEW_GITHUB_REPOSITORIES` 未设置时复用 `GITHUB_REPOSITORIES`。它不能包含不在 `GITHUB_REPOSITORIES` 里的仓库。
`JARVIS_MENTION_NAMES` 是 ChatBridge、GitLab command lane 和 GitHub command lane 共享触发名。每个名字在 GitLab/GitHub 中同时支持 `@name` 和 `/name`；未设置时默认为 `jarvis,jarvis-box`。
`JARVIS_GITHUB_COMMAND_ALLOWED_USERS` 是 GitHub issue/PR comment command lane 触发人 allowlist；GitHub 部署建议使用 numeric user id。GitLab note command lane 的触发人限制由 `JARVIS_GITLAB_COMMAND_ALLOWED_USERS` 单独配置。

## 配置 GitHub webhook

在每个仓库的 webhook 设置中添加：

| 字段 | 值 |
| --- | --- |
| Payload URL | `https://<jarvis-public-url>/webhooks/github` |
| Content type | `application/json` |
| Secret | `GITHUB_WEBHOOK_SECRET` |
| Events | `issue_comment`、`pull_request`、`pull_request_review`、`pull_request_review_comment`、`issues` |

兼容路径 `/github-webhook` 也可用，但新部署推荐 `/webhooks/github`。

有仓库 webhook 管理权限时，可用 `gh api` 创建 webhook：

```bash
gh api "repos/OWNER/REPO/hooks" \
  -X POST \
  -f name=web \
  -F active=true \
  -f 'events[]=issue_comment' \
  -f 'events[]=pull_request' \
  -f 'events[]=pull_request_review' \
  -f 'events[]=pull_request_review_comment' \
  -f 'events[]=issues' \
  -f "config[url]=$JARVIS_PUBLIC_URL/webhooks/github" \
  -f config[content_type]=json \
  -f "config[secret]=$GITHUB_WEBHOOK_SECRET"
```

如果仓库已有 Jarvis webhook，先查出 hook id，再用 `PATCH` 更新 URL、secret 和事件列表：

```bash
gh api "repos/OWNER/REPO/hooks" \
  --jq '.[] | [.id, .active, .config.url, (.events | join(","))] | @tsv'

gh api "repos/OWNER/REPO/hooks/HOOK_ID" \
  -X PATCH \
  -F active=true \
  -f 'events[]=issue_comment' \
  -f 'events[]=pull_request' \
  -f 'events[]=pull_request_review' \
  -f 'events[]=pull_request_review_comment' \
  -f 'events[]=issues' \
  -f "config[url]=$JARVIS_PUBLIC_URL/webhooks/github" \
  -f config[content_type]=json \
  -f "config[secret]=$GITHUB_WEBHOOK_SECRET"
```

`https://<jarvis-public-url>/webhooks/github` 里的端口和 path 是两层概念：公网或云安全组开放的是 TCP 端口，通常是 443；`/webhooks/github` 是该端口上的 HTTP path。生产推荐用反向代理只把 webhook path 转发到 jarvis-box，而不是把 jarvis-box 的 8787 端口整体裸露到公网。入口配置示例见 [network-ingress.md](../network-ingress.md)。

## 配置 gh 写回

Native 部署直接使用安装发起用户现有的 `gh` 认证：

```bash
gh auth login
gh auth status
```

Docker 部署由 `deploy-production.sh ... start` 自动导入当前宿主机身份；多账号宿主机用 `JARVIS_GITHUB_USER` 选择 machine user。Token 写入私有 `auth/github.token`，不写 `runtime.env`，也不挂载宿主机 HOME/Keychain。

token 至少需要目标仓库的 issue/PR 读取和评论权限；要执行 follow-up 修改，还需要读取并推送 PR head repository 的 source branch（fork PR 即 fork 仓库分支）。GitHub issue `opened` 的 post-check 会用 `gh api` 预取 issue 和分页评论。GitHub command/post-check lane 由 Agent 产出 GitHub-ready Markdown，再由 Jarvis Box 的 `ProviderActionExecutor` 使用 `gh issue comment` 或 `gh pr comment` 写回；Agent 不接收 provider mutation 命令。Task/Run 中的 `comment-post-action.txt` 与 provider 上的真实评论共同构成 writeback evidence。PR review 保留 review delivery owner，follow-up 通过 provider-neutral `FollowupProvider` adapter 写状态评论；两者与 command/post-check 共用全局回写开关和服务端 identity。follow-up 状态评论按 marker 查找并 POST/PATCH 同一条评论。

生产推荐使用专门的 GitHub machine user 或 GitHub App installation token，而不是个人高权限账号。写回身份必须拥有目标 repo 的 issue/PR 读取与评论权限；webhook secret 不能替代 `gh` 写回 token。

## 验证

按顺序做四层验证：

1. 本机 HMAC smoke：按 [network-ingress.md](../network-ingress.md) 验证 `POST http://127.0.0.1:8787/webhooks/github`，有效签名返回 200，错误签名返回 401。
2. 公网入口 smoke：从生产机器外部访问 `https://<jarvis-public-url>/webhooks/github`，确认 HTTPS、反向代理和 jarvis-box 串通，并确认 `/server/api/*` 与公网 `:8787` 不可访问。
3. GitHub delivery smoke：在 GitHub webhook 页面发送 ping，或用 `gh api "repos/OWNER/REPO/hooks/HOOK_ID/pings" -X POST` 触发 ping，再查看最新 delivery。ping 事件应返回 2xx，jarvis-box body 通常包含 `github_event_not_supported`，且不会启动 agent。
4. 真实 issue post-check 闭环：创建 allowlist 仓库的测试 issue，确认 `issues/opened` 启动且只启动一个 `post-check` Task，普通 edited/labeled 事件不会重跑，最终评论写回原 issue。
5. 真实 command 闭环：在 allowlist 仓库的测试 issue 或 PR 中，用 allowlist 用户评论 `/jarvis summarize this PR` 或配置的 mention 名称。打开 `/status` 确认出现 `source=github` work item，等待 GitHub issue/PR 出现 Jarvis 评论。
6. 真实 follow-up 闭环：在 allowlist 仓库的测试 PR 中创建 changes-requested review、普通 review 正文或 inline review comment；若使用 fork PR，先确认 Jarvis 运行身份可推送该 head repository source branch。确认 `/status` 出现 `lane=followup`，PR 中只有一条带 `jarvis-box-followup-status` marker 的状态评论，任务完成后该评论从“执行中”更新为“已完成”。

检查 artifact 时，不应出现 `GITHUB_WEBHOOK_SECRET`、`GH_TOKEN`、`GITHUB_TOKEN` 或 raw provider token。若真实闭环没有启动 agent，优先检查：

- `JARVIS_GITHUB_COMMAND_ALLOWED_USERS` 是否包含触发评论者的 GitHub numeric user id。
- `GITHUB_REPOSITORIES` 是否包含 `owner/repo`。
- webhook 是否选择了 `issue_comment` 事件。
- follow-up 测试是否同时选择了 `pull_request_review` 和 `pull_request_review_comment`；fork PR 还要检查运行身份对 head repository source branch 的推送权限。
- GitHub delivery 是否是重复 delivery。
- Native 的 `gh auth status` 是否在安装发起用户下通过，或 Docker `auth-import` 是否成功。

自动化 E2E 使用真实 `jarvis-box serve` 进程和真实本地监听端口覆盖 GitHub webhook ingress：

```bash
npm run e2e -- e2e/github-webhook.spec.ts
```

## 能力边界

GitHub 同时是 repository host 和 work-item provider。issue 提供 create/command/lifecycle/comment writeback，PR 另外提供 review/follow-up。GitHub issue 当前没有 Jarvis Box 内建的 label/status mutation adapter；workflow 请求 provider 不具备的 action 会在调用 `gh` 前 fail closed。
