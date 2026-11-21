# 禅道 OSS 21 接入

本页面向运行禅道开源版 21.7.9 的管理员。Jarvis Box 接收原生 webhook，支持 Bug、用户故事、任务和测试用例：创建触发预检，评论中的显式 `@jarvis` 触发 command，结果回写到原工作项。代码仓库需要单独关联。

鉴权与 JSON 校验成功、投递可靠落盘后，入口返回 `202 Accepted`。`receipt_id` 只表示已受理；Task 会在后台创建。恢复规则见[Webhook 受理与恢复](../storage-model.md#webhook-受理与恢复)。

## 1. 配置服务身份和范围

在当前实例的私密运行配置（`0600`）中设置：

```dotenv
ZENTAO_BASE_URL=https://zentao.example.com
ZENTAO_ACCOUNT=jarvis
ZENTAO_PASSWORD=<service-account-password>
ZENTAO_CLI_COMMAND=zentao
JARVIS_ZENTAO_WEBHOOK_SECRET=<random-private-secret>
ZENTAO_ALLOWED_SCOPES=product:1,execution:2
ZENTAO_ALLOWED_USERS=
JARVIS_COMMAND_BOT_USERNAMES=jarvis
```

`ZENTAO_BASE_URL` 可含部署子目录，但不能包含 API path、userinfo、query 或 fragment。`ZENTAO_ACCOUNT` 需要目标工作项的读取和评论权限，无需管理员；`ZENTAO_PASSWORD` 必填，并且不交给 Agent。服务端用它从 `POST /api.php/v1/tokens` 获取 v1 token，401 时重新认证并只重试一次。token 只保存在进程会话，不回写配置，也不建立第二份 credential 文件；旧的 `ZENTAO_API_TOKEN` 不再支持。

`ZENTAO_ALLOWED_SCOPES` 是显式 allowlist，启用时不能为空。Bug、用户故事、用例使用 `product:<id>`；任务使用 `execution:<id>`。ID 必须为正十进制整数，且这些 scope 不能互换。服务端实时读取工作项来验证范围和操作者，payload 的 scope 或账号不能取代该检查。`ZENTAO_ALLOWED_USERS` 留空时允许 scope 内非 bot 用户发评论命令；`JARVIS_COMMAND_BOT_USERNAMES` 必须包括用于回写的账号，避免自身评论成环。

服务端不向 Agent 交付密码或 webhook secret。每个 Agent Run（含继续执行）开始前取得有效 token；CLI token cache 使用 Run artifacts 以外的私有临时 `ZENTAO_CONFIG_FILE`，进程结束后由 Runner 清理。认证错误会停止重复登录；网络、权限与业务错误不会被误认为 token 过期。`jarvis-box doctor` 会通过运行中的服务验证服务账号；交互式 `zentao login` 不能证明服务身份正常。

## 2. 安装 CLI

Docker image 固定内置 `zentao-cli` 0.2.0 和 `zentao-api` 0.4.1。Native 需要 Node.js 22+，可安装到服务用户目录：

```bash
zentao_tools="$HOME/.local/share/jarvis-box/zentao-cli"
npm install --prefix "$zentao_tools" --save-exact --ignore-scripts --no-audit --no-fund \
  zentao-cli@0.2.0 zentao-api@0.4.1
mkdir -p "$HOME/.local/bin"
ln -s "$zentao_tools/node_modules/.bin/zentao" "$HOME/.local/bin/zentao"
"$HOME/.local/bin/zentao" --version
```

也可把 `ZENTAO_CLI_COMMAND` 指向绝对路径。配置后运行 `jarvis-box doctor`，它会检查 CLI 可执行性和支持版本。工具版本随镜像升级，`jarvis-box tools update` 不会把它升级为其他禅道版本的 CLI。

## 3. 创建原生 webhook

地址格式为：

```text
https://jarvis:<url-encoded-private-secret>@<jarvis-box-host>/webhooks/zentao
```

密码使用 `JARVIS_ZENTAO_WEBHOOK_SECRET`；采用 URL-safe 随机值可避免编码歧义。禅道 native Others/default sender 通过 URL userinfo 发 Basic Authorization，反向代理必须保留该 header。密钥会存入禅道 webhook 配置，因此限制该配置和日志的访问。

必须在 webhook 参数中包含稳定 action `id`。禅道 21 页面没有该复选框时，由有 webhook 管理权限的账号用 v2 API 创建；这是管理员一次性操作，不修改 PHP/数据库，也不改变 Jarvis 日常服务账号：

```http
POST /api.php/v2/webhooks
Token: <zentao-api-token>
Content-Type: application/json
```

```json
{
  "type": "default",
  "name": "Jarvis Box",
  "url": "https://jarvis:<url-encoded-private-secret>@<jarvis-box-host>/webhooks/zentao",
  "domain": "https://zentao.example.com",
  "sendType": "sync",
  "params": ["id", "objectType", "objectID", "product", "project", "execution", "action", "actor", "date", "comment", "text"],
  "products": ["1"],
  "executions": []
}
```

发送端的 `products`/`executions` 是额外过滤条件，仍须通过 `ZENTAO_ALLOWED_SCOPES`；若两个发送端条件都配置，事件必须同时满足二者。`opened` 才自动触发预检；仅 `commented` 中可见正文的显式 mention 启动 command。普通编辑、解决 Bug、完成任务、评审不启动 Agent。关闭/取消只能在实时可读时终止同 type、同工作项 Task；无法读取或已删除的项目不推断状态也不取消。原生 sender 不保证 HTTP 失败会重投，Jarvis Box 只恢复已经受理的投递。

## 4. 工作区、读取和写回

关联仓库按 scope 配置，目标项目仍须在对应 GitLab/GitHub allowlist：

```dotenv
JARVIS_WORK_ITEM_REPOSITORIES={"zentao":{"product:1":[{"provider":"gitlab","project":"acme/api"}],"execution:2":[{"provider":"gitlab","project":"acme/api"}]}}
```

没有关联时可以创建 zero-workspace Task。站点、scope、object type 和 number 都会保留；更换接入站点不会把旧任务转移到新站点，旧任务要继续时恢复原站点配置。不同站点使用独立 deployment。

服务端通过 v2 view API 准备 `issue.json`、`notes.json`，保留动作历史与附件 metadata。Agent 可按用户任务和账号权限通过 CLI 读写禅道；Jarvis Box 不追加统一只读限制。CLI 0.2.0 对 Bug、故事和用例可能缺部分历史，即使 `--format raw` 也不保证完整；需要最新历史时读 v2 view。附件只能按已验证的文件 ID 调原生文件 API，不能把 token 发到正文任意 URL。

Agent 只生成 `comment.md`，`ProviderActionExecutor` 发布最终回复。自动回复不改变工作项状态；用户明确要求的修改可以由 Agent 的 CLI 执行。全局 `JARVIS_PROVIDER_WRITEBACK_ENABLED=false` 只停用自动评论，不会撤销 Agent CLI 的原生权限。写回对 401 会重新认证并读取历史核对 Run 标记，最多补写一次；未知结果仍走原有查证流程，不盲目重复。
