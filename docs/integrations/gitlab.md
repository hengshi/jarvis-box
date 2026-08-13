# GitLab 接入

GitLab 是事件、subject 与安全 writeback 的 provider adapter。它不定义客户状态、标签或 workflow 语义。

## 认证与 webhook 协调

服务身份必须通过 `glab auth status` 且仅拥有批准的项目权限。

```bash
GITLAB_TOKEN=<token> jarvis-box setup gitlab --auth-only

GITLAB_HOST=gitlab.example.com \
GITLAB_PROJECTS=group/project \
JARVIS_PUBLIC_URL=https://jarvis.example.com \
jarvis-box setup gitlab --non-interactive
```

需要共享 webhook secret 时使用 `GITLAB_WEBHOOK_SECRET` 和 `--rotate-secret`。规范端点为 `https://<public-url>/gitlab-webhook`；`/webhooks/gitlab` 是等价路由。

## 事件路由

| 事件 | 产品行为 |
| --- | --- |
| 允许的 issue/work-item 事件 | 登记精确的 provider subject 并启动配置的入口 workflow |
| 允许的 MR 事件 | 启用时启动通用 MR review；close/merge 终止绑定到该精确 subject 的 Task |
| 允许的 review 项目中的非系统 MR note | 去重后启动通用 MR follow-up |
| 配置的 command mention | 启动 command lane |

`GITLAB_PROJECTS` 与 `REVIEW_GITLAB_PROJECTS` 是 operator allowlist。`JARVIS_GITLAB_COMMAND_ALLOWED_USERS` 可选地收窄 command 作者范围。Bot/系统 note 和 jarvis-box writeback 标记被忽略以防止循环。

Native 部署直接复用安装用户的 `glab` 身份。Docker 可以由 `start` 自动导入宿主机当前用户身份，也可以设置 `JARVIS_AUTH_IMPORT=skip` 后在持久 Agent HOME 中执行 `glab auth login --hostname <host>`；Token 不写入 `runtime.env`。

GitLab command 与 post-check lane 由 Agent 产出 `comment.md`，再由 Jarvis Box 的 `ProviderActionExecutor` 使用服务端 `glab` 身份写回。MR review 保留 review delivery owner，follow-up 通过 provider-neutral `FollowupProvider` adapter 写状态评论；三条路径都消费同一个全局回写开关和服务端 identity。Agent 不接收 provider 评论 endpoint，也不负责生成成功回执。所有写回都必须由同一个 Task/Run 证据链关联到原始 subject。

MR follow-up 不限于特定客户 workflow 创建的 MR，也不搜索 `bugfix-result.json`。Runtime Agent 通过原生 discovery 选择适用的客户或 repo-local workflow。

Provider terminal 事件仅匹配不可变的 `task-state.subject` 元组与 Task 已登记的 `workspaces[]`。分支名、artifact 路径和目录扫描永不建立所有权。

## Workflow Runtime Contract

在启动客户 workflow 之前，jarvis-box 写入 v2 `workflow-input.json`。v2 不再生成 action grants；既有 v1 Run 仅为升级兼容保留读取和原 grant 校验，不用于新写入。input 包含：

- 不透明的 provider 事件数据；
- 精确的 provider subject identity；
- Task/Run/Workspace 句柄；

Runtime Agent 写入 `workflow-result.json`。客户定义的结果对 jarvis-box 不透明。仅经验证的显式 action 被执行并记录在 `workflow-actions.json` 中。

受支持的 GitLab action 包括精确 input subject 的评论、标签添加、Work Item Status 变更和子 workflow 启动。Jarvis Box 验证 action schema、artifact 路径和精确 subject；客户状态、标签及 workflow 路由语义仍由 Runtime Foundation 定义。`JARVIS_PROVIDER_WRITEBACK_ENABLED=false` 会跳过所有原 subject provider mutation，但不跳过 Agent、workflow result 或本地审计。

状态变更使用 GitLab 的 provider 操作和实时回读验证。失败或模糊的回读仍为失败 action，并通过其 action 幂等记录重试，不被视为客户 workflow 成功。

## 验证

```bash
jarvis-box test 42 open "agent smoke" group/project
```

真实 onboarding 证明应使用批准的测试 subject 并确认：

1. provider delivery 创建了一个 Task 和一个 Run；
2. Runtime Agent 从持久 Agent HOME 中原生发现了客户 workflow；
3. `workflow-input.json`、`workflow-result.json` 和 `workflow-actions.json` 指向同一个精确 subject；
4. 请求的安全 writeback 出现在同一 provider subject 上；
5. 重放不会重复已完成的 action。
