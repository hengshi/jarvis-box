# Runtime Agent

正式 Agent 是客户授权的高权限主体，可以接收代码、源码和 writeback 能力。Native 与 Docker 都使用发起安装的现有 OS 用户；Docker 以该用户的数字 UID/GID 非 root 运行，并通过 NSS 映射提供稳定的 `jarvis` 用户身份。默认 Compose 以 `IS_SANDBOX=1` 标记无 socket 的容器边界，使 Claude 可以使用非交互式 bypass 模式。Docker socket overlay 是独立的宿主 root 等价选项，并覆盖 `IS_SANDBOX=0`，使 Claude bypass fail closed。

## 身份

Native 服务复用该用户的原生 CLI 身份。Docker 不能继承 Host Keychain 或登录会话：将窄化的凭据快照导入由 `$JARVIS_DEPLOYMENT_HOME/data/agent-home` 提供的持久 `/home/jarvis`；绝不挂载 Host 用户的完整 credential store。

```bash
scripts/deploy-production.sh /absolute/deployment-home start
scripts/deploy-production.sh /absolute/deployment-home auth-import
```

`start` 已执行导入。使用显式命令轮换或选择其他 Host 身份，然后运行通用 `verify`。

Provider / push 身份、Runtime Agent 身份和 Git commit identity 是三件事。共享 Jarvis 运行时可以继续使用机器账号读取 provider、写回评论或推送分支，同时在每个 workspace 的 `.git/config` 中把新 commit 归属到客户定义的代码负责人。配置方式见 [代码归属与 Git 提交身份](code-attribution.md)。

## Agent 选择

`JARVIS_RUNTIME_AGENT` 和 `runtime.env` 中的可选 scope override 选择 Agent 可执行文件。变更属于 operator 配置变更，需要 doctor/smoke 加上受影响的 workflow 验证；不涉及 Jarvis context 或 deployment lock。

`custom-user-task` 使用与 `jarvis-command` 同类的 providerless prompt task 启动路径和 Runtime Agent scope。它不会携带 provider writeback contract；外部投递是否成功由 agent task 的结果证据表达。`job_id` 只影响任务身份、Status 展示和同 job 防并发，不参与 Runtime Agent 选择。

## 模型路由与计费额度

Agent、模型和计费账户是三个独立维度。Claude 可以通过 `ANTHROPIC_BASE_URL` 使用 DeepSeek，OpenCode/OpenClaw/Hermes 也可以通过各自 base URL 或 OpenAI/Anthropic 兼容变量使用第三方模型；Status 因此先解析 Agent 的有效模型路由，再读取该路由所属账户的额度，绝不根据 `claude`、`codex` 等 Agent 名称猜测计费方。

`/status` 的“系统操作 → 工作方式 → 模型资源与额度”展示当前可识别的关系。ChatGPT 登录的 Codex 通过本机 account/rate-limit 接口读取滚动窗口；指向官方 `api.deepseek.com` 的兼容路由使用 Agent 实际采用的 credential 读取 DeepSeek 钱包。同一 credential 被多个 Agent 使用时，它们显示相同的脱敏账户引用和同一份余额。其他计费方没有适用的安全公开接口时只显示模型/计费方和“不支持自动读取”，不会用本机 token 统计或模型列表伪装账户额度。

DeepSeek 兼容路由优先使用该 Agent 实际消费的 credential（例如 Claude 的 `ANTHROPIC_AUTH_TOKEN`、OpenCode 的 `OPENCODE_API_KEY`）；未配置 Agent 专用变量时再读取 canonical runtime env 中的 `DEEPSEEK_API_KEY` 或 `DEEPSEEK_SKEY`。这些变量只用于识别同一计费账户并查询官方余额，response 仅返回不可逆的短账户引用。

额度采集是只读、best-effort 的 Status 证据：不发起模型推理，不改变路由，不把原始账户身份、credential 或上游 body 写入 response。额度不可用不会把 Agent 命令本身改成 unavailable；实际启动仍由 Runtime Agent router 和 Provider 在调用时执行各自的准入。

## Delivery Metrics

Delivery Metrics 使用普通 `delivery-metrics` lane Task 分析历史 MR/PR。它默认继承全局 Runtime Agent；以下命令设置或取消独立选择：

```bash
jarvis-box agent list
jarvis-box agent set --scope delivery-metrics codex
jarvis-box agent unset --scope delivery-metrics
```

`agent list` 的 `scoped runtime agents` 会显示 `delivery-metrics` 的 effective Agent、来源、命令和 prefix args。设置前运行 `jarvis-box agent doctor` 和 `jarvis-box agent smoke <agent>`。

Status 服务为每个待分析 MR/PR 启动一个 `delivery-metrics` lane Task，Task 输出 `delivery-metrics-result.json`。Continue 使用同一个 lane scope 重新解析 Agent 配置；切换 Agent 或模型不会改写已经完成的分类结果。进度与恢复步骤见 [Delivery Metrics 历史基线](delivery-metrics.md)。

## Skill 发现

- 镜像自带的通用 `skill-creator` 链接到 Codex/Claude discovery roots；
- create-jarvis 绝不安装在正式运行时中；
- 客户 Jarvis skills 由该 Jarvis 的 Runtime Foundation 在持久 Agent HOME 中安装/更新；
- jarvis-box 不将 root skill、`JARVIS_HOME`、commit 或 workflow 路径注入 Run；
- identity 自有的已有 skills 不被镜像 entrypoint 覆盖。

Runtime Foundation onboarding 必须通过真实 Agent 调用来证明发现。仅有文件系统存在是不够的。

uv-im-connector 拥有 provider 原生 IM secrets 和长连接；jarvis-box 仅使用 connector protocol/token，不将 connector secrets 传递给 Agent 子进程。
