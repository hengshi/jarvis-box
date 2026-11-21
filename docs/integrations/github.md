# GitHub 接入

接入后，你可以在 GitHub Issue 或 PR 评论中向 Jarvis 发出指令，让它评审 PR、处理后续反馈，并把结果回复到原处。你也可以在已经接入的 IM 会话中订阅一次 GitHub Actions 运行结果。

本文面向配置 GitHub 集成的部署维护人员。日常聊天操作见 [IM 使用说明](im.md)；任务身份与恢复规则见[执行模型](../execution-model.md)。

## 接入前准备

准备允许 Jarvis 处理的仓库、可供 GitHub 访问的 HTTPS 地址，以及以下权限：

- 配置人员能管理仓库 Webhook，用于设置回调地址、事件和共享密钥。
- Jarvis 运行时使用的 GitHub 账号能读取目标 Issue/PR 和评论，并发表评论。
- 需要修改代码时，运行账号还能读取和推送 PR 的来源分支。fork PR 的来源分支位于 fork 仓库中。
- 需要订阅 Actions 结果时，同一运行账号还能读取 **Actions 运行记录和仓库 Webhook 配置**。

Webhook 密钥核验 GitHub 发来的事件；`gh` 登录凭据用于读取仓库和回复评论，两者不能互相替代。推荐使用专门的 GitHub machine user 或 GitHub App installation token，按需要授予仓库权限。

## 配置仓库范围和触发方式

把配置写入 `JARVIS_ENV_FILE` 指向的环境文件，不要修改 sample：

```dotenv
JARVIS_PUBLIC_URL=https://jarvis.example.com
GITHUB_REPOSITORIES=owner/repository
REVIEW_GITHUB_REPOSITORIES=owner/repository
JARVIS_GITHUB_WEBHOOK_ENABLED=true
GITHUB_WEBHOOK_SECRET=<shared-secret>
JARVIS_MENTION_NAMES=jarvis,jarvis-box
JARVIS_GITHUB_COMMAND_ALLOWED_USERS=
GH_CMD=gh
```

将 `owner/repository` 换成实际仓库，`<shared-secret>` 换成自行生成的密钥。

| 配置 | 用途 |
| --- | --- |
| `JARVIS_PUBLIC_URL` | 这套 Jarvis Box 对外提供的 HTTPS 基础地址，必须与 Webhook 回调地址一致 |
| `GITHUB_REPOSITORIES` | 允许接入的仓库；范围外的事件不启动工作 |
| `REVIEW_GITHUB_REPOSITORIES` | 允许自动评审 PR 的仓库；不设置时沿用上述范围，不能包含范围外的仓库 |
| `JARVIS_GITHUB_WEBHOOK_ENABLED` | 是否接收 GitHub Webhook，默认 `true` |
| `GITHUB_WEBHOOK_SECRET` | 接收事件时验证签名，启用 Webhook 必须配置 |
| `JARVIS_MENTION_NAMES` | 指令触发名，默认 `jarvis,jarvis-box`；每个名字同时支持 `@名字` 和 `/名字` |
| `JARVIS_GITHUB_COMMAND_ALLOWED_USERS` | 可选的发起人限制；留空允许接入仓库内所有非机器人作者，填写时支持 login 或数字用户 ID |
| `GH_CMD` | Jarvis 使用的 `gh` 命令 |

公开仓库允许任何人发表评论时，允许名单留空也会允许这些非机器人用户发起指令。需要收窄范围时再填写名单，不必为普通接入逐个登记成员。

触发名与 IM、GitLab 共享；GitLab 的发起人限制由 `JARVIS_GITLAB_COMMAND_ALLOWED_USERS` 单独配置。开启 `JARVIS_SELF_SKILLS_IMPROVE_ENABLED` 后，符合条件的已合并 PR 也使用评审仓库范围进行技能回填，无需另设 GitHub 仓库变量。

如果 GitHub 仓库仅用于其他工作项的代码工作区，不需要接收 GitHub 事件，可设置 `JARVIS_GITHUB_WEBHOOK_ENABLED=false`。此时 Webhook 返回 `404`，无需配置共享密钥，但仓库仍须在 `GITHUB_REPOSITORIES` 内。

## 配置 GitHub Webhook

在仓库的 Webhook 设置中填写：

| 字段 | 值 |
| --- | --- |
| Payload URL | `${JARVIS_PUBLIC_URL}/github-webhook` |
| Content type | `application/json` |
| Secret | 与 `GITHUB_WEBHOOK_SECRET` 相同 |
| Events | `issue_comment`、`pull_request`、`pull_request_review`、`pull_request_review_comment`、`issues`；需要订阅 Actions 时再包含 `workflow_run` |

`JARVIS_PUBLIC_URL` 应是完整的 HTTPS 地址，例如 `https://jarvis.example.com`。普通 GitHub 事件也兼容 `/webhooks/github`；Actions 订阅要求仓库中有启用的 `workflow_run` Webhook，且地址精确匹配 `${JARVIS_PUBLIC_URL}/github-webhook`。按表中的地址统一配置即可。公网端口和反向代理的设置见[网络入口](../network-ingress.md)。

有仓库 Webhook 管理权限时，可以用 `gh` 创建。下面示例同时启用 Actions 事件；只需要普通工作项处理时，省略 `workflow_run` 那一行。执行前，在当前终端将 `JARVIS_PUBLIC_URL` 和 `GITHUB_WEBHOOK_SECRET` 设置为环境文件中的相同值：

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
  -f 'events[]=workflow_run' \
  -f "config[url]=$JARVIS_PUBLIC_URL/github-webhook" \
  -f 'config[content_type]=json' \
  -f "config[secret]=$GITHUB_WEBHOOK_SECRET"
```

`OWNER/REPO` 要替换为实际仓库。已有 Webhook 时，先查询 ID，避免重复创建：

```bash
gh api "repos/OWNER/REPO/hooks" \
  --jq '.[] | [.id, .active, .config.url, (.events | join(","))] | @tsv'
```

将查到的 `HOOK_ID` 填入下面命令，更新已有 Webhook。事件列表同样包含可选的 `workflow_run`：

```bash
gh api "repos/OWNER/REPO/hooks/HOOK_ID" \
  -X PATCH \
  -F active=true \
  -f 'events[]=issue_comment' \
  -f 'events[]=pull_request' \
  -f 'events[]=pull_request_review' \
  -f 'events[]=pull_request_review_comment' \
  -f 'events[]=issues' \
  -f 'events[]=workflow_run' \
  -f "config[url]=$JARVIS_PUBLIC_URL/github-webhook" \
  -f 'config[content_type]=json' \
  -f "config[secret]=$GITHUB_WEBHOOK_SECRET"
```

## 配置 Jarvis 使用的 GitHub 账号

Native 部署使用安装发起用户现有的 `gh` 认证。首次由该用户登录后，检查账号是否正确：

```bash
gh auth login
gh auth status
```

Docker 部署通过 `deploy-production.sh ... start` 导入当前宿主机身份；宿主机有多个账号时，用 `JARVIS_GITHUB_USER` 指定账号。凭据保存在私有的 `auth/github.token` 中，不写入 `runtime.env`，也不挂载宿主机 HOME 或 Keychain。完整步骤见[运维说明](../operations.md)。

Jarvis 会在订阅登记和处理 Actions 结果时检查运行读取权限及 Webhook 配置，不会替你创建或修改 Webhook。缺少条件时会说明订阅没有登记，不能把这当成已经开始等待。

## GitHub 中如何触发工作

| 操作或事件 | Jarvis 的行为 |
| --- | --- |
| 在 Issue/PR 评论中写 `/jarvis`、`@jarvis` 或已配置的触发名 | 按评论要求处理并在原 Issue/PR 回复。同一发起人在该事项中的后续指令[继续原任务](../execution-model.md#从同一事项继续评论指令) |
| PR 打开、重新打开、提交更新或从草稿转为可评审 | 在允许自动评审的仓库中启动 PR 评审 |
| 提交非空的 `changes_requested` 或 `commented` 评审，或新建行内评审评论 | 处理后续反馈 |
| 在 PR 中新增不含指令的普通评论 | 作为后续反馈处理；普通 Issue 评论不触发此类处理 |
| Issue 创建 | 开启 `JARVIS_ISSUE_POST_CHECK_ENABLED` 时进行初步检查；普通编辑或标签变更不会反复启动 |
| Issue/PR 关闭或 PR 合并 | 结束与该工作项绑定的工作，并清理其登记的工作区和外部资源 |

草稿 PR 不触发自动评审。机器人自身评论、重复投递、空评审和 `approved` 评审不会触发后续处理；指令评论不会同时触发一次普通反馈处理。

PR 评审针对事件受理时的提交和分支，评论读取失败会阻止准备，不会假装没有历史反馈。每个[配置的评审角度](../configuration.md#configprompts)由一个独立的 Agent 进程检查同一提交，汇总后追加一条新评论。后续反馈处理会更新同一条状态评论。fork PR 的读取或推送权限不足时会明确失败，不会转而修改目标仓库分支。

### 回复时 Issue 或 PR 已被删除

回复返回 `404` 时，Jarvis 会用同一个运行账号检查仓库。仓库可访问而工作项已不存在时，该任务取消并清理已登记资源；已经成功完成的执行结果保留。清理失败只重试清理，不重新运行 Agent 或重复发表评论。

仓库本身不可访问、账号权限不足或配置有误时，保留待处理状态和失败原因，供维护人员排查。

## 在 IM 中订阅一次 Actions 运行结果

适合“这个 CI 结束后提醒我，失败则继续排查”的情况。订阅针对一个工作流运行，不把整个 PR 的所有检查、分支或“最新一次”当成同一个运行。

### 先验证一次运行结束事件

完成 Webhook 和账号配置后，在这个仓库执行一次 Actions 工作流并等待结束。到 GitHub Webhook 的近期投递记录中确认 `workflow_run`、`action=completed` 事件已经发给这套 Jarvis Box，响应为 `200` 且正文包含 `accepted: true`；这表示 Jarvis 已验签、读取并核对同一次运行后受理了事件。不能仅凭 HTTP 成功状态判断验证通过。

只有这条真实事件与读取验证通过，才可以登记订阅。创建 Webhook、列出配置或 ping 连通性检查均不能代替它。修改回调地址或签名配置后，需要重新完成这一步。

### 登记、查看和取消

验证通过后，在原 IM 会话中发送：

```text
@jarvis 订阅 当前
@jarvis 订阅 https://github.com/OWNER/REPO/actions/runs/RUN_ID 下一次 2h
@jarvis 这个 CI 结束提醒我，失败继续排查
@jarvis 查看订阅
@jarvis 取消订阅 <查询结果中的订阅编号>
```

把示例链接换成真实的 Actions 运行详情页地址，去掉 `?` 或 `#` 后缀；地址须属于已接入的 GitHub host。指定一次重新运行时，可使用 `/actions/runs/RUN_ID/attempts/ATTEMPT`，Jarvis 不会自动换成另一次尝试。`当前` 只适用于这项工作已关联唯一运行的情况；有多个运行时，回复会给出可选择的链接。

订阅登记两项一次性处理：结束结论不是 `failure` 时提醒原会话；结论为 `failure` 时，在原任务仍允许继续的前提下继续排查，结果也回到原会话。任务已取消、权限失效或不再允许继续时，只记录受阻原因，不另建任务。运行结束却没有可用结论时，记录结果暂不可用，不自动续跑。

默认期限为 24 小时，可指定 1 分钟至 30 天。默认处理所选运行：尚未结束就等待，已经结束则处理一次；明确写“下一次”才等待同一工作流、同一提交的新运行或重新尝试。登记回执会列出运行链接、处理方式、接收会话、期限和订阅编号。

重复登记不延长期限，也不重新打开已结束的订阅。取消只停止未来动作，已撤销或到期的订阅不会自动恢复。重启后会恢复等待，重复完成事件不会再次处理。提醒是否送达无法确认时保留未知结果，不盲目补发；可在原会话查询订阅状态。存储和去重细节见[持久化与恢复](../storage-model.md)。

## 验证和排查

按下面顺序核对接入结果：

1. **账号**：在 Jarvis 实际使用的 Native 用户或 Docker 环境检查 `gh auth status`，确认仓库可读、Issue/PR 可评论。不要只检查另一台电脑或另一个用户的登录状态。
2. **入口**：按[网络入口](../network-ingress.md)验证 HTTPS 和转发配置。签名有效的新任务事件受理后返回 `202`；已处理的重复投递可返回 `200`，签名错误返回 `401`。Actions 结束事件的成功回执为 `200` 和 `accepted: true`。受理回执不表示工作已经完成。
3. **投递**：在 GitHub Webhook 页面触发 ping 并查看 delivery。ping 只检查连通性，不启动 Agent，响应可包含 `github_event_not_supported`。
4. **指令和回复**：在接入的测试仓库中评论 `/jarvis summarize this PR`。到 [Terminal 工作台](../status-ui.md#终端工作台)核对新工作，并确认结果回到同一 Issue/PR。
5. **自动处理**：按已启用能力创建测试 Issue、更新非草稿 PR 或提交评审反馈，检查工作和原处回复。fork PR 还要验证来源分支推送权限。
6. **Actions 提醒**：用已配置 `workflow_run` 的仓库和精确运行链接登记订阅；先确认收到登记回执，再核对原会话提醒或允许的继续处理。重复事件不应产生重复提醒或重复执行。

没有触发时，优先检查仓库范围、事件选择、触发名和可选的发起人限制。没有回复时，检查运行账号对原 Issue/PR 的评论权限；没有 Actions 提醒时，再检查运行读取权限、Webhook 地址，以及订阅是否已到期或撤销。

不要把 `GITHUB_WEBHOOK_SECRET`、`GH_TOKEN`、`GITHUB_TOKEN` 或其他原始凭据粘贴到公开评论和日志。GitHub Issue 当前不支持由 Jarvis 内建操作自动修改标签或状态。配置的完整列表见[配置参考](../configuration.md)。
