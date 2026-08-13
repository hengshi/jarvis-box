# 飞书项目接入

Jarvis Box 接收飞书项目 webhook，读取工作项及其评论，执行 post-check，再把最终 `comment.md` 发布到对应工作项。读写后端可以是飞书项目 plugin OpenAPI，也可以是官方 Meegle CLI。credential 只由 Jarvis Box 服务进程持有，不会传给 runtime agent。

## 配置

| 变量 | 必填 | 用途 |
| --- | --- | --- |
| `FEISHU_PROJECT_WEBHOOK_SECRET` | 是 | 与当前 webhook envelope 的 `header.token` 匹配的共享 token。 |
| `FEISHU_PROJECT_BACKEND` | 否 | `plugin` 或 `meegle-cli`；留空时默认 `meegle-cli`。plugin 必须显式指定。 |
| `FEISHU_PROJECT_ALLOWED_SPACES` | 否 | 逗号分隔的 project key；为空时允许全部 project。 |
| `JARVIS_FEISHU_PROJECT_COMMAND_ALLOWED_USERS` | 否 | 允许使用 `@jarvis` command 的用户标识；为空时允许所有非 bot 用户。 |
| `JARVIS_WORK_ITEM_REPOSITORIES` | 否 | provider-neutral work-item 到 GitLab/GitHub 仓库关联 JSON；同一空间可关联零个、一个或多个仓库。 |

### 使用 Meegle CLI（无 plugin）

现场已有 Meegle CLI 时使用以下配置：

```dotenv
FEISHU_PROJECT_WEBHOOK_SECRET=<webhook 中 header.token 的值>
FEISHU_PROJECT_MEEGLE_CMD=/usr/local/bin/meegle
FEISHU_PROJECT_ALLOWED_SPACES=space-a,space-b

# 推荐：给 Jarvis Box 服务账号注入独立 token
MEEGLE_HOST=project.feishu.cn
MEEGLE_USER_ACCESS_TOKEN=<user-access-token>
```

也可以复用 Jarvis Box 服务账号已经登录的 Meegle profile：

```dotenv
FEISHU_PROJECT_WEBHOOK_SECRET=<webhook 中 header.token 的值>
FEISHU_PROJECT_MEEGLE_CMD=/usr/local/bin/meegle
FEISHU_PROJECT_MEEGLE_PROFILE=jarvis
```

backend 留空时默认使用 `meegle-cli`，也可以显式写 `FEISHU_PROJECT_BACKEND=meegle-cli`。`FEISHU_PROJECT_MEEGLE_CMD` 默认是 `meegle`。Native/systemd 部署建议填写绝对路径；profile 模式要求运行 `jarvis-box serve` 的系统账号能访问该 profile/keychain。共享机器优先使用专门的短期 `MEEGLE_USER_ACCESS_TOKEN`，不要让 runtime agent 账号复用个人 profile。

启动前可用相同账号验证：

```bash
/usr/local/bin/meegle auth status --format json
```

`jarvis-box serve` 启动时也会执行这项认证预检；命令不存在、token 无效或服务不可达都会拒绝启动并给出明确错误。运行时调用以下官方命令：

- `meegle workitem get` 读取工作项；
- `meegle comment list --auto-paginate` 读取全部评论；
- `meegle comment add` 回写最终评论。

评论内容通过权限为 `0600` 的临时 JSON 文件传入，不拼 shell 命令。Meegle token、host、command 和 profile 均会从 runtime agent 环境中清除。

### 使用飞书项目 plugin

```dotenv
FEISHU_PROJECT_WEBHOOK_SECRET=<webhook 中 header.token 的值>
FEISHU_PROJECT_BACKEND=plugin
FEISHU_PROJECT_PLUGIN_ID=<plugin-id>
FEISHU_PROJECT_PLUGIN_SECRET=<plugin-secret>
FEISHU_PROJECT_USER_KEY=<user-key>
# 可选；默认 https://project.feishu.cn
FEISHU_PROJECT_API_BASE_URL=
```

plugin 模式必须显式配置 `FEISHU_PROJECT_BACKEND=plugin`，并完整提供 webhook secret、plugin ID、plugin secret 和 user key。只填写 plugin credential 而不指定 backend 会拒绝启动，避免误用默认的 Meegle CLI 后端。

## Webhook

Meegle CLI 不负责监听事件。事件入口使用飞书项目自带的自动化 Webhook，不需要创建飞书项目 plugin：

1. 在目标飞书项目空间中创建自动化规则，选择需要接入 Jarvis Box 的触发器，例如创建工作项、评论工作项、完成、终止或删除工作项；
2. 在自动化规则的执行动作中添加内置的 **Webhook**；不要选择需要开发 plugin 的自定义自动化操作；
3. 请求地址填写 `https://<jarvis-box-host>/webhooks/feishu-project`；Jarvis Box 必须能被飞书项目服务通过 HTTPS 访问；
4. Webhook token 填写一个独立的随机值，并把相同值配置为 Jarvis Box 的 `FEISHU_PROJECT_WEBHOOK_SECRET`；
5. 启用规则并发送测试事件，确认 Jarvis Box 日志中请求已被接收。

需要处理多种事件时，应在飞书项目自动化中为相应触发器配置 Webhook。plugin 只用于 `FEISHU_PROJECT_BACKEND=plugin` 的 OpenAPI 读写后端，或客户自行开发自定义自动化操作；使用默认 Meegle CLI 后端时不需要 plugin ID、plugin secret 或 user key。

Meegle CLI 的工作项与评论读取在后台执行；Jarvis Box 完成鉴权、body 校验和接收状态落账后立即返回 `202 Accepted`，避免飞书项目自动化等待 CLI 时触发 6 秒超时。后台处理使用独立的有界 context，不会因 webhook 客户端断开而取消，最终结果或失败会继续写入事件流、work ledger 和 Run Artifact。

以下两个 endpoint 等价：

- `https://<jarvis-box-host>/feishu-project-webhook`
- `https://<jarvis-box-host>/webhooks/feishu-project`

当前飞书项目 envelope 使用 `header.event_type`、`header.token` 和 `header.uuid`，工作项 identity 来自 `payload.id`、`payload.project_key` 与 `payload.work_item_type_key`。`WorkitemCreateEvent` 启动 post-check，带 `@jarvis` 的 `WorkitemCommentEvent` 启动 command Run，`WorkitemAbortedEvent`、`WorkitemFinishEvent` 与 `WorkitemDeleteEvent` 终止同一外部工作项下的 Task 并走统一 cleanup。Jarvis Box 用 UUID 原子 claim 保证幂等，并在持久化 payload 或 ledger 前删除 token。

`@jarvis` 只是 command mention，不是飞书专用 workflow。comment adapter 会先忽略 Jarvis 自身/bot 评论，再按 allowlist 和 comment UUID 去重，命中后与 GitLab/GitHub/Jira 一样进入 `jarvis-command` lane。

仓库关联使用空间 key 作为 source scope：

```dotenv
GITLAB_PROJECTS=group/backend
GITHUB_REPOSITORIES=acme/frontend
JARVIS_WORK_ITEM_REPOSITORIES={"feishu-project":{"space-a":[{"provider":"gitlab","project":"group/backend"},{"provider":"github","project":"acme/frontend"}]}}
```

创建事件和 command 都会获得全部已关联 workspace；未配置关联时仍是合法的 zero-workspace Task，不会默认猜测 GitLab 或 GitHub 仓库。

旧的 flat `EventCreate-*` payload 和 `X-Plug-In-Token` header 仅作为兼容入口保留。

## 读写边界

每个通过校验的 create event 按以下边界执行：

1. 服务端通过所选的 plugin OpenAPI 或 Meegle CLI 后端读取工作项；
2. 把工作项与已有评论写入私有 Run Artifact；
3. 在不携带飞书 credential 的情况下启动 runtime agent；
4. 校验 agent 生成的 `comment.md`，再由同一服务端后端创建工作项评论；
5. 把响应或失败写入 Run Artifact 和工作账本。

plugin 模式不会启动额外进程；`meegle-cli` 模式只启动配置的 Meegle CLI 子进程。Runtime agent 不应直接调用飞书项目或 Meegle CLI，也不应自行声明写回成功。
