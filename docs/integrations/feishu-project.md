# 飞书项目接入

本页面向将飞书项目工作项接入 Jarvis Box 的管理员。系统接收飞书项目 webhook，执行 post-check 或显式 mention command，再把 Agent 的 `comment.md` 写回对应工作项。先选择读写 backend，再在飞书项目自动化中配置事件。

鉴权、JSON 校验和可靠落盘后，webhook 立即返回 `202 Accepted`。`receipt_id` 仅表示受理，不等待读取、Git 操作或 Agent 启动；后台恢复见[Webhook 受理与恢复](../storage-model.md#webhook-受理与恢复)。

## 选择 backend

默认是 `meegle-cli`；已有 Meegle CLI 和服务身份时优先选它。它让 Runtime Agent 用已认证 CLI 读取实时正文、完整评论、附件和关联工作项。`plugin` 是例外路径：Jarvis Box 用 plugin OpenAPI 预取输入，plugin credential 不进入 Agent。

| 变量 | 说明 |
| --- | --- |
| `FEISHU_PROJECT_WEBHOOK_SECRET` | 必填；必须与 webhook envelope `header.token` 相同。 |
| `FEISHU_PROJECT_BACKEND` | `meegle-cli`（默认）或 `plugin`；使用 plugin 时必须显式设置。 |
| `FEISHU_PROJECT_ALLOWED_SPACES` | 可选，逗号分隔 project key；留空允许所有。 |
| `FEISHU_PROJECT_SIMPLE_NAMES` | plugin 使用稳定 project key 时必填；将其映射为页面 URL 的 `simple_name`。 |
| `JARVIS_MENTION_NAMES` | command 触发名；未设默认 `jarvis,jarvis-box`。 |
| `JARVIS_FEISHU_PROJECT_COMMAND_ALLOWED_USERS` | command 作者 allowlist；留空允许非 bot 用户。 |
| `JARVIS_WORK_ITEM_REPOSITORIES` | 可选，空间到 GitLab/GitHub workspace 关联 JSON。 |

### 默认 Meegle CLI backend

```dotenv
FEISHU_PROJECT_WEBHOOK_SECRET=<webhook header.token>
FEISHU_PROJECT_MEEGLE_CMD=/usr/local/bin/meegle
FEISHU_PROJECT_ALLOWED_SPACES=space-a,space-b

# 推荐使用独立短期 token；也可以配置已有 profile。
MEEGLE_HOST=project.feishu.cn
MEEGLE_USER_ACCESS_TOKEN=<user-access-token>
# FEISHU_PROJECT_MEEGLE_PROFILE=jarvis
```

backend 留空或设为 `meegle-cli`。`FEISHU_PROJECT_MEEGLE_CMD` 默认 `meegle`；Native/systemd 推荐绝对路径。profile 模式要求运行 `jarvis-box serve` 的系统账号及其启动的飞书项目 Agent 能访问该 profile/keychain。共享机器优先使用独立短期 token，不复用个人 profile。启动前可用相同身份运行：

```bash
/usr/local/bin/meegle auth status --format json
```

Jarvis Box 会快速预检 CLI 身份；命令不存在、未认证、token 无效或无法证明可用时，服务继续启动并审计 webhook，但在身份修复前 Meegle 读写不可用。它使用 `meegle workitem get`、`comment list --auto-paginate`、`relation list`、`attachment +download` 与 `comment add`。收到稳定 project key 后，服务会用同一身份解析并缓存页面链接所需的 `simple_name`；API 读写仍使用稳定 key。Agent 只在匹配的飞书项目 Run 中得到 Meegle CLI 能力，必须刷新实时输入；这些 credential 不会注入 GitLab、GitHub、Jira、plugin 或其他 provider 的 Run。最终评论仍由服务端写入，内容经权限为 `0600` 的临时 JSON 文件传递，不拼接到 shell 命令中。

### Plugin backend

```dotenv
FEISHU_PROJECT_WEBHOOK_SECRET=<webhook header.token>
FEISHU_PROJECT_BACKEND=plugin
FEISHU_PROJECT_PLUGIN_ID=<plugin-id>
FEISHU_PROJECT_PLUGIN_SECRET=<plugin-secret>
FEISHU_PROJECT_USER_KEY=<user-key>
FEISHU_PROJECT_SIMPLE_NAMES={"<stable-project-key>":"<simple_name>"}
# 可选，默认 https://project.feishu.cn
FEISHU_PROJECT_API_BASE_URL=
```

plugin 必须完整配置所有上述 credential。只填 plugin credential 而未设 `FEISHU_PROJECT_BACKEND=plugin` 会拒绝启动；stable project key 缺 `simple_name` 映射时事件 fail closed，避免生成不可访问链接。

## 配置飞书项目自动化 webhook

Meegle CLI 不监听事件。每个需要的触发器按下面步骤配置内置 **Webhook**（不是需要自建 plugin 的自定义自动化操作）：

1. 在目标空间创建自动化规则，选择创建、评论、完成、终止或删除等触发器；
2. 添加内置 **Webhook** 动作；
3. 地址填写 `https://<jarvis-box-host>/webhooks/feishu-project`；飞书项目必须能经 HTTPS 访问；
4. 填一个独立随机 token，并将相同值设置为 `FEISHU_PROJECT_WEBHOOK_SECRET`；
5. 启用规则并发送测试事件，在 Jarvis Box 日志确认接收。

等价 endpoint 是 `/feishu-project-webhook`。`WorkitemCreateEvent` 启动 post-check；带配置 mention 的 `WorkitemCommentEvent` 启动 command（bot 自身评论与不在 allowlist 的作者不会启动）；`WorkitemAbortedEvent`、`WorkitemFinishEvent`、`WorkitemDeleteEvent` 终止同一外部工作项 Task 并执行 cleanup。UUID 原子 claim 保证幂等，payload/ledger 持久化前会删除 token。CLI 初始读取在后台执行，避免自动化等待它超时；Agent 启动后仍须刷新实时输入。旧 flat `EventCreate-*` payload 与 `X-Plug-In-Token` 仅保留兼容。

可用空间 key 关联仓库：

```dotenv
GITLAB_PROJECTS=group/backend
GITHUB_REPOSITORIES=acme/frontend
JARVIS_GITHUB_WEBHOOK_ENABLED=false
JARVIS_WORK_ITEM_REPOSITORIES={"feishu-project":{"space-a":[{"provider":"gitlab","project":"group/backend"},{"provider":"github","project":"acme/frontend"}]}}
```

上例的 GitHub 仅作 workspace，关闭 GitHub webhook 后不需要 GitHub webhook secret。没有关联仍是合法 zero-workspace Task，系统不会猜测仓库。

## 读取和写回边界

Meegle create/post-check 与 command Agent 必须从 CLI 读取当前工作项、全部评论、需要的附件和关联；触发时 `issue.json`/`notes.json` 仅是快照。Plugin 路径由 Jarvis Box 预取：预取失败时不启动 Agent。嵌套 customer workflow 只有在同一飞书 subject 且为 Meegle backend 时继承 Meegle CLI；plugin 或非飞书 subject 不注入该能力。

所有路径由 Agent 显式生成 `comment.md`，Jarvis Box 校验后按所选 backend 发布。Agent 的 stdout/stderr 和终端回复不会覆盖 provider-facing 文件，Agent 不直接发布或声称已经写回。该 response owner 是行为与审计合同，不把高权限 Runtime Agent 伪装成权限沙箱：Meegle CLI 身份仍可能有 mutation 权限；prompt 的只读要求和 `JARVIS_PROVIDER_WRITEBACK_ENABLED=false` 都不撤销原生身份。需要强制只读时，为所有适用 provider 配置独立只读身份或受限 wrapper/proxy。
