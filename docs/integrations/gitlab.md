# GitLab 接入

本页面向负责把 GitLab project 接入 Jarvis Box 的管理员。配置完成后，允许项目中的 issue、MR、note 或明确命令可创建受控 Task；结果由 Jarvis Box 使用服务身份写回原 GitLab subject。

完成鉴权、JSON 校验并可靠落盘后，webhook 立即返回 `202 Accepted`。响应的 `receipt_id` 只表示投递已受理，不表示 Task 已经创建、Agent 已经启动或写回已经完成。后台处理和重投见[Webhook 受理与恢复](../storage-model.md#webhook-受理与恢复)。

## 1. 准备身份、范围与 webhook

运行 Jarvis Box 的服务身份必须通过 `glab auth status`，并且只具有批准项目的权限。配置并创建/修复 webhook：

```bash
GITLAB_TOKEN=<token> jarvis-box setup gitlab --auth-only

GITLAB_HOST=gitlab.example.com \
GITLAB_PROJECTS=group/project \
JARVIS_PUBLIC_URL=https://jarvis.example.com \
jarvis-box setup gitlab --non-interactive
```

需要共享 webhook secret 时设置 `GITLAB_WEBHOOK_SECRET` 并使用 `--rotate-secret`。规范地址为 `https://<public-url>/gitlab-webhook`；`/webhooks/gitlab` 是等价路径。网络暴露与 token 未配置时的行为见 [网络入口](../network-ingress.md)。

`GITLAB_PROJECTS` 是事件和 workspace 的 operator allowlist；`REVIEW_GITLAB_PROJECTS` 指定其中要做 MR review 的项目；`JARVIS_GITLAB_COMMAND_ALLOWED_USERS` 可进一步收窄命令作者。Native 直接使用安装用户的 `glab` 身份。Docker 默认在 `start` 时导入当前 Host 用户身份；如设 `JARVIS_AUTH_IMPORT=skip`，在持久 Agent HOME 运行 `glab auth login --hostname <host>`。不要把 token 写进 `runtime.env`。

## 2. 哪些事件会启动或停止工作

| 事件 | 行为 |
| --- | --- |
| allowlist 中的 issue/work-item | 登记精确 provider subject，启动已配置的入口 workflow。 |
| allowlist 中的 MR | 非草稿 MR 创建、草稿转 ready 或源提交变化时，对该提交启动评审；普通标题/元数据变更不启动；同一提交不重复评审。close/merge 会终止绑定到该精确 subject 的 Task。 |
| review 项目中的非系统 MR note | 去重后启动通用 MR follow-up。 |
| 在 Issue 或 MR 评论中使用已配置的触发名 | 处理本条指令。同一发起人在该事项中的后续指令[继续原任务](../execution-model.md#从同一事项继续评论指令)。 |

Bot/系统 note 以及带 Jarvis Box writeback 标记的 note 被忽略，防止循环。GitLab adapter 不定义客户的状态、标签或 workflow 语义。

## 3. 执行和写回的边界

MR 评审为每个[配置的评审角度](../configuration.md#configprompts)启动一个独立的 Agent 进程，所有进程检查同一提交。每次完整运行由 Jarvis Box 汇总为一条新增评审评论，通过服务端 `glab` 身份写回，保留历史评论。读取 discussion 时会保留分页回复和 resolved 状态；读取失败不会假装为空历史。所有写回受同一个全局开关和服务身份控制，且都必须能从同一 Task/Run 证据链追溯到原 subject。`JARVIS_PROVIDER_WRITEBACK_ENABLED=false` 只跳过原 subject mutation，不跳过 Agent、workflow result 或本地审计。

启动客户 workflow 前，Jarvis Box 写入 v2 `workflow-input.json`，其中有不透明 provider 事件数据、精确 subject identity 与 Task/Run/workspace 句柄。Runtime Agent 写入 `workflow-result.json`；客户结果对 Jarvis Box 不透明。只有已验证的显式 action 会被执行并记录在 `workflow-actions.json`。已支持的 GitLab action 为原 subject 评论、加标签、变更 Work Item Status 和启动子 workflow；schema、artifact path 与精确 subject 都会校验。

若最终评论得到 HTTP 404，Jarvis Box 会用同一 `glab` 身份检查目标项目仍可访问。仅当项目仍可访问时，才把 writeback 记为 `subject-not-found / provider-subject-not-found`，清理已登记 workspace 与 typed external resource，并将 Task 置为 `cancelled`；已成功的 Agent Run 保持 `succeeded`。清理尚未完成时 Task 保持 `finalizing / retry-finalization`。项目查询失败、鉴权错误或配置错误仍是普通 writeback 失败，Status 显示 `needs-attention`。

Provider terminal event 仅匹配不可变 `task-state.subject` 与 Task 登记的 `workspaces[]`；分支名、artifact path 和目录扫描永远不能建立所有权。

## 4. 验证真实闭环

可用以下命令创建受控验证：

```bash
jarvis-box test 42 open "agent smoke" group/project
```

在批准的测试 subject 上确认：

1. 一次 provider delivery 只创建一个 Task 和一个 Run；
2. Runtime Agent 完成实际任务；有可用且已验证的客户 workflow 时能原生发现并使用，没有 Company 知识时仍可直接基于证据完成评估；
3. `workflow-input.json`、`workflow-result.json` 与 `workflow-actions.json` 指向同一精确 subject；
4. 请求的安全 writeback 出现在同一 GitLab subject；
5. 重放事件不会重复已完成 action。
