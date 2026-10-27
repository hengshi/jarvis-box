# 云效接入

鉴权及 JSON 校验成功、投递可靠落盘后，Webhook 立即返回 `202 Accepted`，不等待业务读取、Git 操作或 Agent 启动。响应中的 `receipt_id` 只标识投递受理，不表示 Task 已创建；后台处理和重投规则见[Webhook 受理与恢复](../storage-model.md#webhook-受理与恢复)。

Jarvis Box 的云效 adapter 覆盖两个入口：

- **Projex**：项目协作/需求缺陷工作项，行为类似 Jira、飞书项目、TAPD。
- **Codeup**：代码仓库和变更请求。目前支持 Merge Request 和 commit 评论里的 `@jarvis` command，并把最终 `comment.md` 回写到同一个变更请求。自动 MR 代码审查和 followup 需要后续接入 diff/checkout 后再启用。

## 通用配置

| 变量 | 必填 | 用途 |
| --- | --- | --- |
| `YUNXIAO_API_BASE_URL` | 是 | 云效实例公网访问域名，例如 `https://<org-region>.devops.aliyuncs.com`。 |
| `YUNXIAO_ORGANIZATION_ID` | 是 | 云效组织 ID。 |
| `YUNXIAO_ACCESS_TOKEN` | 是 | 云效个人访问令牌（PAT）。这是云效 DevOps OpenAPI token，不是阿里云 AccessKey ID / Secret。 |

Jarvis Box 使用 `YUNXIAO_ACCESS_TOKEN` 调用 Projex 和 Codeup OpenAPI。同一 PAT 通过官方 CLI 环境变量，只向对应的 Projex/Codeup Run 交付，以支持 Agent 按需读取实时上下文、评论、关联信息及附件。webhook 密钥不交付给 Agent。

Docker runtime base 预装固定版本的 `aliyun` CLI 和 `aliyun-cli-devops` 插件，客户部署仅配置 PAT 与接入点。Native 模式安装 `aliyun` CLI 和 `aliyun-cli-devops` 插件，参照 [官方 CLI 文档](https://help.aliyun.com/zh/yunxiao/developer-reference/how-to-install-initialize-and-use-the-apsara-devops-cli)。`YUNXIAO_CMD` 可指定 CLI 路径，默认为 `aliyun`。Jarvis Box 注入 `ALIBABA_CLOUD_YUNXIAO_ACCESS_TOKEN` 和 `ALIBABA_CLOUD_YUNXIAO_API_BASE_URL`；CLI 插件要求接入点为域名而非完整 URL，Jarvis Box 会去除服务端 URL 的协议前缀；仅支持 Region 版，使用实例域名，不向 CLI 注入组织 ID。Agent 通过 `devops --help` 和各命令帮助发现读取操作，按需下载文件到当前 Run 目录，禁止把凭证或签名链接写入结果。

服务端保留初始上下文快照及最终回写职责，不自动下载全部附件。Agent 不直接修改平台或发布评论；CLI 身份本身的权限由 PAT 决定，prompt 的只读约束不是权限沙箱。

## Projex 工作项

| 变量 | 必填 | 用途 |
| --- | --- | --- |
| `YUNXIAO_PROJEX_WEBHOOK_SECRET` | webhook 必填 | 与 Projex webhook body/header token 匹配的共享密钥。 |
| `YUNXIAO_PROJEX_ALLOWED_PROJECTS` | 否 | 逗号分隔的 project id；为空时允许全部项目。 |
| `JARVIS_YUNXIAO_PROJEX_COMMAND_ALLOWED_USERS` | 否 | 允许使用 mention command 的用户标识；为空时允许所有非 bot 用户。 |
| `JARVIS_WORK_ITEM_REPOSITORIES` | 否 | Projex 工作项到 GitLab/GitHub 仓库关联 JSON。 |

Webhook 地址：

- `https://<jarvis-box-host>/webhooks/yunxiao-projex`
- 兼容入口：`https://<jarvis-box-host>/yunxiao-projex-webhook`

Jarvis Box 接受 body 字段 `secret`、`token`、`header.token`，以及 header `X-Projex-Signature`、`X-Yunxiao-Token`、`X-Webhook-Token`。工作项 identity 读取 `space.id` / `project_id` / `projectId` 和 `work_item_id` / `workItemId` / `id`。创建事件启动 post-check，评论事件按 `JARVIS_MENTION_NAMES` 识别 command，关闭/完成/删除事件终止同一外部 subject 下的活跃 Task。

## Codeup 变更请求评论

| 变量 | 必填 | 用途 |
| --- | --- | --- |
| `YUNXIAO_CODEUP_WEBHOOK_SECRET` | webhook 必填 | 与 Codeup webhook header `X-Codeup-Token` 匹配的共享密钥。 |
| `YUNXIAO_CODEUP_ALLOWED_REPOSITORIES` | 否 | 逗号分隔的 Codeup repository id；为空时允许全部仓库。 |
| `JARVIS_YUNXIAO_CODEUP_COMMAND_ALLOWED_USERS` | 否 | 允许使用 mention command 的用户标识；为空时允许所有非 bot 用户。 |

Webhook 地址：

- `https://<jarvis-box-host>/webhooks/yunxiao-codeup`
- 兼容入口：`https://<jarvis-box-host>/yunxiao-codeup-webhook`

Codeup webhook 使用：

- `Codeup-Event: Note Hook`
- `X-Codeup-Token: <YUNXIAO_CODEUP_WEBHOOK_SECRET>`

Jarvis Box 从 payload 读取 `project_id` / repository id、`merge_request.local_id`、`object_attributes.note`、`object_attributes.noteable_type` 和 `related_patch_set.patch_set_biz_id`。Merge Request 和 commit 评论中的 `@jarvis` command 会启动 `jarvis-command` lane；其他类型、bot 评论、未 mention 的评论会被忽略。新的 MR 指令先读取同一仓库和 MR 的当前状态：已关闭或合并时以 `subject-terminal` 忽略，不创建 Task/Run；读取失败、身份不符或状态未知时明确拒绝本次准入，不把未知当作开放或关闭。已处理评论的重投复用原回执，不依赖平台再次可读。commit 不适用 MR 状态检查。任务完成后，Jarvis Box 使用同一个 patchset identity 调用 Codeup 评论接口回写最终结果。

## 示例

```dotenv
YUNXIAO_API_BASE_URL=https://<org-region>.devops.aliyuncs.com
YUNXIAO_ORGANIZATION_ID=<organization-id>
YUNXIAO_ACCESS_TOKEN=<personal-access-token>

YUNXIAO_PROJEX_WEBHOOK_SECRET=<projex-webhook-secret>
YUNXIAO_PROJEX_ALLOWED_PROJECTS=<project-id>

YUNXIAO_CODEUP_WEBHOOK_SECRET=<codeup-webhook-secret>
YUNXIAO_CODEUP_ALLOWED_REPOSITORIES=<repository-id>
```

服务地址只接受不含用户名、密码、查询参数或片段的 HTTP(S) 地址。本适配器仅支持 Region 版，不支持中心版。配置只接受实例根 URL，不接受 `/api` 等路径；API 使用实例域名和不含组织路径段的请求路径，不额外添加组织编号查询参数。

## 能力边界

Projex 保留基础 adapter，尚未完成平台自动触发接入：

- 接收端可处理带完整事件类型与身份的创建、评论事件；
- 评论解析、任务执行和回写已通过 API 评论回放验证；平台自动评论回调未验证，不承诺在评论区直接 `@jarvis` 能触发；
- 服务端读取当前工作项和评论，写入 `issue.json` / `notes.json`；
- 服务端回写最终评论；
- 通过 `JARVIS_WORK_ITEM_REPOSITORIES` 关联 GitLab/GitHub workspace。

Codeup adapter 当前支持：

- Merge Request 和 commit 评论中的 `@jarvis` command；
- 执行前读取仓库和主体信息，按触发版本读取 diff，检出对应提交到 Task workspace；
- MR 评论历史预取和同一评论线程回复；
- MR 关闭或合并事件通过 TaskService 终止对应主体的活跃任务；
- 服务端回写最终评论到同一个 Codeup 变更请求。

Codeup 尚未声明完整自动代码审查和 followup 能力；这些能力需要补齐专用 review/followup admission 和版本防护后再开放。

Codeup 支持合并请求和提交（commit）评论中的 `@jarvis` 指令。合并请求回复保留触发评论的 patchset 身份；提交回复写回同一仓库和提交 SHA。

Codeup workspace 使用已认证仓库接口返回的 SSH 地址，支持 SCP 与 `ssh://` 格式（含端口）；克隆域名不要求与 API 域名相同，需要服务进程用户具有该仓库的 SSH 访问权限。API PAT 不替代 Git SSH 认证。Docker 部署需在 `$JARVIS_DEPLOYMENT_HOME/data/agent-home/.ssh`（容器内 `/home/jarvis/.ssh`）配置仓库私钥、SSH config 和经核对的主机信任记录，并将对应公钥登记到 Codeup；`auth-import` 导入平台与 Agent 身份，不自动复制宿主机的 SSH 私钥。MR 上下文写入 `codeup.json` 和 `notes.json`；commit 评论历史尚未接入，根提交没有父提交时 diff 会明确标为不可用。

### Projex 事件配置与评论格式

Projex 内置 Webhook 模板提供状态变更、字段变更触发，未提供新增评论模板。接收端支持评论事件不代表平台会发出该事件；当前不提供评论轮询，单独在 Projex 评论区输入 `@jarvis` 不构成已支持的自动触发流程。标准自动化 Webhook 的 Secret 使用 `X-Projex-Signature`，反向代理必须转发该请求头。配置参见[官方 Webhook 指南](https://help.aliyun.com/zh/yunxiao/user-guide/webhook-configuration-guide)。

评论指令从富文本 JSON 的 `htmlValue` 提取可见文字，排除引用、代码和 HTML 属性中的 mention。Region API 评论回写采用包含 `htmlValue` 的富文本 JSON；Jarvis Box 将 Agent 的 Markdown 转成 HTML，保留机器人回写标记，禁用原始 HTML 和危险链接。
