# 云效接入

本页面向接入云效 Region 版的管理员。Jarvis Box 有两个不同的 adapter：Projex 用于项目工作项，Codeup 用于代码仓库中的 Merge Request 或 commit 评论指令。先配置共同身份，再选择需要的入口。

鉴权、JSON 校验和可靠落盘成功后，webhook 返回 `202 Accepted`。响应的 `receipt_id` 仅表示投递已受理；Task 在后台创建。恢复与重投见[Webhook 受理与恢复](../storage-model.md#webhook-受理与恢复)。

## 共同配置与边界

```dotenv
YUNXIAO_API_BASE_URL=https://<org-region>.devops.aliyuncs.com
YUNXIAO_ORGANIZATION_ID=<organization-id>
YUNXIAO_ACCESS_TOKEN=<personal-access-token>
```

`YUNXIAO_API_BASE_URL` 是云效实例的公网根域名；只支持 Region 版，不支持中心版，也不能填写 `/api` 等 path。它必须是不含用户名、密码、query、fragment 的 HTTP(S) 地址。`YUNXIAO_ACCESS_TOKEN` 是云效 DevOps OpenAPI PAT，不是阿里云 AccessKey ID/Secret。

Jarvis Box 用 PAT 调用 Projex 与 Codeup API，并只将它交给对应的 Projex/Codeup Run，使 Agent 能按需读取实时上下文、评论、关联信息和附件。webhook secret 不会交给 Agent。Docker runtime 已预装固定版本的 `aliyun` 和 `aliyun-cli-devops`；Native 请按[官方 CLI 文档](https://help.aliyun.com/zh/yunxiao/developer-reference/how-to-install-initialize-and-use-the-apsara-devops-cli)安装。`YUNXIAO_CMD` 可指定 CLI，默认 `aliyun`。

为 CLI，Jarvis Box 注入 `ALIBABA_CLOUD_YUNXIAO_ACCESS_TOKEN` 与 `ALIBABA_CLOUD_YUNXIAO_API_BASE_URL`；后者是域名，不含服务 URL 的协议。它不把 organization ID 注入 CLI。Agent 通过 `devops --help` 与命令帮助发现读取操作，按需将文件下载到当前 Run，不能把 token 或签名链接写进结果。服务端保留初始快照和最终写回职责，Agent 不直接发布评论。CLI 令牌真实权限仍由 PAT 决定，prompt 的只读规则不是权限沙箱。

## Projex 工作项

```dotenv
YUNXIAO_PROJEX_WEBHOOK_SECRET=<projex-webhook-secret>
YUNXIAO_PROJEX_ALLOWED_PROJECTS=<project-id>
JARVIS_YUNXIAO_PROJEX_COMMAND_ALLOWED_USERS=
# 可选：关联 GitLab/GitHub workspace
JARVIS_WORK_ITEM_REPOSITORIES=
```

endpoint 为 `https://<jarvis-box-host>/webhooks/yunxiao-projex`，兼容路径为 `/yunxiao-projex-webhook`。认证可来自 body 的 `secret`、`token`、`header.token`，或 `X-Projex-Signature`、`X-Yunxiao-Token`、`X-Webhook-Token` header。创建事件启动 post-check；评论事件按 `JARVIS_MENTION_NAMES` 识别 command；关闭/完成/删除事件终止该外部 subject 下的活跃 Task。

Projex 是保留的基础 adapter，尚未承诺平台原生自动触发：接收端可处理完整事件类型和 identity 的创建/评论事件，评论解析、执行和写回已通过 API 评论回放验证，但平台自动评论回调尚未验证。Projex 内置 webhook 模板可针对状态和字段变更，不能针对新增评论；不提供评论轮询。因此，在 Projex 评论区单独输入 `@jarvis` 不是已支持的自动触发流程。标准自动化 Webhook 的 Secret 位于 `X-Projex-Signature`，反向代理必须转发它。参见[官方 Webhook 指南](https://help.aliyun.com/zh/yunxiao/user-guide/webhook-configuration-guide)。

服务端写入 `issue.json`、`notes.json` 并回写最终评论；可通过 `JARVIS_WORK_ITEM_REPOSITORIES` 关联 GitLab/GitHub。评论从富文本 `htmlValue` 提取可见文字，排除引用、代码与 HTML 属性中的 mention；回写把 Agent Markdown 转为含 `htmlValue` 的富文本，保留机器人标记并禁用原始 HTML 与危险链接。

## Codeup MR 与 commit 评论

```dotenv
YUNXIAO_CODEUP_WEBHOOK_SECRET=<codeup-webhook-secret>
YUNXIAO_CODEUP_ALLOWED_REPOSITORIES=<repository-id>
JARVIS_YUNXIAO_CODEUP_COMMAND_ALLOWED_USERS=
```

endpoint 为 `https://<jarvis-box-host>/webhooks/yunxiao-codeup`，兼容路径为 `/yunxiao-codeup-webhook`。Codeup 应发送 `Codeup-Event: Note Hook` 和 `X-Codeup-Token: <YUNXIAO_CODEUP_WEBHOOK_SECRET>`。

MR 或 commit 评论中出现 `@jarvis` 时执行指令，同一事项中的后续指令[继续原任务](../execution-model.md#从同一事项继续评论指令)。其他 note type、bot 评论或不带 mention 的评论会忽略。对 MR，Jarvis Box 在准入前读取同仓库/MR 当前状态：已关闭或合并时以 `subject-terminal` 忽略；读取失败、身份不符或状态未知时拒绝这次准入，不能把未知当作开放或关闭。已处理评论重投复用原 receipt，不依赖平台再次可读。commit 不做 MR 状态检查。

Codeup 首次执行评论指令时，工作区检出触发评论对应的 patchset 或提交。继续同一 Task 时保留工作区中的改动，每轮仍按该评论的触发版本读取差异，并回写到对应的 MR thread 或 commit。MR 关闭或合并后，Jarvis Box 终止该 MR 的活跃任务。自动代码审查和 follow-up 尚未接入。

Clone 使用已认证仓库 API 返回的 SSH 地址，可为 SCP 或带端口的 `ssh://`，不要求与 API 域名相同。PAT 不能替代 Git SSH 认证。Docker 须在 `$JARVIS_DEPLOYMENT_HOME/data/agent-home/.ssh`（容器内 `/home/jarvis/.ssh`）配置仓库私钥、SSH config 和已核对的 host trust；`auth-import` 不会复制 Host SSH 私钥。MR 输入写入 `codeup.json`、`notes.json`；commit 评论历史尚未接入，root commit 无父提交时会明确标出 diff 不可用。
