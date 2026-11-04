# 禅道 OSS 21 接入

联调基线为禅道开源版 21.7.9。Jarvis Box 接收禅道原生 Webhook，支持 Bug、用户故事、任务和测试用例。创建工作项触发预检，评论中的显式 `@jarvis` 触发指令，最终结果回写到原工作项。代码仓库通过关联配置独立选择。

鉴权与 JSON 校验成功、投递可靠落盘后，入口返回 `202 Accepted`。`receipt_id` 表示投递已受理，Task 在后台创建；恢复规则见[Webhook 受理与恢复](../storage-model.md#webhook-受理与恢复)。

## 配置身份与范围

配置写入当前实例的运行配置文件，文件保持 `0600`：

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

| 变量 | 用途 |
| --- | --- |
| `ZENTAO_BASE_URL` | 禅道站点根地址，可包含部署子目录；不含 API 路径、userinfo、query 或 fragment。 |
| `ZENTAO_PASSWORD` | 必填。服务端使用此密码自动获取 v1 API Token，读取遇到 401 时重新认证并重试一次。密码只保存在当前实例的私密运行配置中，不交付给 Agent。 |
| `ZENTAO_ACCOUNT` | 禅道原始服务账号，需有目标工作项的读取和评论权限；自动认证不要求管理员账号。 |
| `ZENTAO_CLI_COMMAND` | 官方 CLI 可执行命令，默认 `zentao`；支持版本为 0.2.0，SDK 固定 0.4.1。 |
| `JARVIS_ZENTAO_WEBHOOK_SECRET` | Webhook 的 HTTP Basic 密码；用户名固定为 `jarvis`。 |
| `ZENTAO_ALLOWED_SCOPES` | 显式允许范围，逗号分隔；启用时不能为空。 |
| `ZENTAO_ALLOWED_USERS` | 可选的评论指令账号允许名单，匹配禅道原始账号；留空允许范围内的非机器人账号，不限制自动创建预检。 |
| `JARVIS_COMMAND_BOT_USERNAMES` | 包含用于回写的禅道服务账号，防止其自身评论再触发任务。 |

Bug、用户故事、测试用例使用所属产品的 `product:<id>`。任务使用所属执行的 `execution:<id>`；产品、项目和执行 ID 不能互换。ID 使用正十进制整数，例如 `product:1`、`execution:2`。Jarvis Box 从实时工作项读取范围和操作者，载荷中的 scope 或账号不能替代实时校验。

服务端通过 `POST /api.php/v1/tokens` 使用服务账号密码获取 Token，并在进程内共用当前会话。Token 不回写配置、不建立第二份凭据文件；服务重启后自动重新认证。旧实例须在同一运行配置文件中补充 `ZENTAO_PASSWORD` 并移除 `ZENTAO_API_TOKEN`，按当前部署方式受控重启。缺少密码时明确拒绝启用，不继续运行无法恢复的静态 Token 接入。不要把密码发送到聊天或写进任务提示词。

评论写入收到 401 时自动重新认证，再读取原工作项历史核对同一 Run 标记，至多补写一次；已有评论则复用原 action ID，历史无法读取时停止。超时、断链和其他写入错误保留原有未知结果查证流程。

每次 Agent 启动（包括继续执行）前校验当前会话，向该 Run 注入有效 Token。发布评论前的实时历史读取也会自动恢复失效会话；并发请求共用恢复后的 Token。密码被服务端拒绝时停止重复登录，避免锁定账号；修正运行配置后受控重启。网络故障、权限拒绝和业务错误不会被当作 Token 过期无限重试。

`jarvis-box doctor` 与系统诊断除检查 CLI 版本外，还由运行中的 Jarvis 服务通过原生 API 验证当前配置的服务账号。两者共用服务端会话和错误密码的拒绝记录，重复执行命令或查看页面不重复提交已拒绝的密码；认证配置修改后提示受控重启，再验证新凭据。服务未启动或无法提供认证诊断时，`doctor` 报告检查失败，须先启动服务。交互式 `zentao login` 使用自己的配置，不能证明 Jarvis 服务的认证正常。

## 安装读取工具

Docker runtime base 内置官方 `zentao-cli` 0.2.0 与 `zentao-api` 0.4.1，依赖通过锁文件固定。该工具随镜像升级，`jarvis-box tools update` 不会将其升级到面向其他禅道版本的 CLI。

Native 服务用户可使用 Node.js 22 或更新版本，按固定版本安装到用户目录：

```bash
zentao_tools="$HOME/.local/share/jarvis-box/zentao-cli"
npm install --prefix "$zentao_tools" --save-exact --ignore-scripts --no-audit --no-fund \
  zentao-cli@0.2.0 zentao-api@0.4.1
mkdir -p "$HOME/.local/bin"
ln -s "$zentao_tools/node_modules/.bin/zentao" "$HOME/.local/bin/zentao"
"$HOME/.local/bin/zentao" --version
```

已有同名文件时，核对并维护原安装；也可将 `ZENTAO_CLI_COMMAND` 配成安装后的绝对路径。配置完成后运行 `jarvis-box doctor`，启用禅道的部署会检查 CLI 可执行性和支持版本。[官方 CLI](https://github.com/easysoft/zentao-cli)与[官方 SDK](https://github.com/easysoft/zentao-api)分别维护命令及 API 能力。

## 创建原生 Webhook

接收地址为：

```text
https://jarvis:<url-encoded-private-secret>@<jarvis-box-host>/webhooks/zentao
```

密码使用与 `JARVIS_ZENTAO_WEBHOOK_SECRET` 相同的值；选用 URL 安全字符组成的随机密钥可避免编码歧义。禅道原生 Others/default sender 通过 URL userinfo 发出 HTTP Basic Authorization。反向代理需要保留该请求头。密钥会保存在禅道 Webhook 配置中，应限制配置和日志的访问。

需要在 Webhook 参数中加入稳定的 action `id`。禅道 21 的页面复选框未列出 `id`，因此由具有 Webhook 管理权限的账号通过原生 v2 API 创建配置。管理员配置时可通过 v1 tokens 接口获取自己的 Token；该步骤独立于 Jarvis 日常服务账号的自动认证，不修改 PHP 或数据库：

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

`products` 和 `executions` 是禅道发送端的过滤条件；按实际产品和执行选择。Jarvis Box 仍独立校验 `ZENTAO_ALLOWED_SCOPES`。如果两个发送端过滤条件同时配置，事件必须同时满足二者。

禅道消息设置还需启用对应对象的创建和评论通知。草稿用户故事不会发送通知。原生 generic sender 不提供自定义鉴权头或 JSON HMAC；不要把聊天机器人专用的签名设置当作该 payload 的签名。

原生事件示例：

```json
{"id":42,"objectType":"case","objectID":3,"product":",1,","project":0,"execution":0,"action":"commented","actor":"alice","date":"2026-10-16 10:00:00","comment":"@jarvis 检查这个用例","text":"操作摘要"}
```

`id` 是动作/评论 ID，`objectID` 是工作项 ID。测试用例类型为 `case`。载荷的 `text` 会本地化，Jarvis Box 根据明确字段及实时 API 数据识别事件。缺少稳定 action ID 的事件不能进入执行流程。

只有 `opened` 自动触发预检，只有 `commented` 中可见正文的显式 mention 触发指令。普通编辑、解决 Bug、完成任务或评审不会启动 Agent。可实时读取的关闭或取消事件只终止对应类型的同一工作项任务；不同类型可以具有相同数字 ID，身份保持独立。

工作项已删除或不可读取时，Jarvis Box 拒绝推断状态，不据此取消任务。

任务保留原禅道站点、范围、对象类型和编号。修改接入站点后，旧任务不会转到新站点执行或回写；站点不匹配时，“继续执行”会被拒绝。需要继续旧任务时恢复原站点配置，多个站点使用独立部署。

禅道原生 sender 不保证在 HTTP 失败后重试。Jarvis Box 提供自身已受理投递的持久恢复；不要将非 2xx 响应理解为禅道一定会再次投递。

## 关联代码仓库

按名称空间范围配置关联，目标仓库仍需在相应 GitLab/GitHub allowlist 中：

```dotenv
JARVIS_WORK_ITEM_REPOSITORIES={"zentao":{"product:1":[{"provider":"gitlab","project":"acme/api"}],"execution:2":[{"provider":"gitlab","project":"acme/api"}]}}
```

没有关联仓库时，可以创建零工作区任务以分析工作项上下文。产品和执行 ID 不是代码仓库地址。

## 读取与评论回写

服务端使用原生 v2 view API 准备 `issue.json` 和 `notes.json`，保留完整动作历史及附件元数据。Agent 通过官方 CLI 读取实时详情；CLI 0.2.0 对 Bug、用户故事和用例会省略部分历史，即使使用 `--format raw` 也不保证完整。需要最新历史时，读取对应的 v2 view；附件按已验证的文件 ID 使用原生文件 API读取，不能把 Token 发送给正文提供的任意 URL。

Jarvis Box 只向禅道 Run 注入 `ZENTAO_URL`、`ZENTAO_ACCOUNT`、`ZENTAO_TOKEN` 和 `ZENTAO_CLI_COMMAND`。CLI 会缓存 Token，因此 `ZENTAO_CONFIG_FILE` 指向 Run 产物目录以外的私有临时文件；启动失败或进程结束后由 Runner 清理。它保留其他工具的 XDG 配置路径，避免影响关联仓库的认证；禅道密码与 Webhook 密钥不交付给 Agent。

结果由 `ProviderActionExecutor` 发布到原工作项，Agent 输出 `comment.md`。独立 comment API 创建备注并返回 action ID，保留工作项状态。备注只展示回复正文；服务端通过禅道保留的空命名锚点保存隐藏的 Run 去重标记，重试与自身 Webhook 识别共用该标记。禅道会过滤普通 HTML 注释，因此不能用 HTML 注释保存去重信息。全局 `JARVIS_PROVIDER_WRITEBACK_ENABLED=false` 时只保存本地结果，不向禅道发布评论。Agent CLI 身份的原生权限由令牌决定，只读提示词不是权限沙箱。
