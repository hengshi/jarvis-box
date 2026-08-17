# Runtime Agent

正式 Agent 是客户授权的高权限主体，可以接收代码、源码和 writeback 能力。Native 与 Docker 都使用发起安装的现有 OS 用户；Docker 以该用户的数字 UID/GID 非 root 运行，并通过 NSS 映射提供稳定的 `jarvis` 用户身份。默认 Compose 以 `IS_SANDBOX=1` 标记无 socket 的容器边界，使 Claude 可以使用非交互式 bypass 模式。Docker socket overlay 是独立的宿主 root 等价选项，并覆盖 `IS_SANDBOX=0`，使 Claude bypass fail closed。

## 身份

Native 服务复用该用户的原生 CLI 身份。Docker 不能继承 Host Keychain 或登录会话：将窄化的凭据快照导入由 `$JARVIS_DEPLOYMENT_HOME/data/agent-home` 提供的持久 `/home/jarvis`；绝不挂载 Host 用户的完整 credential store。

```bash
scripts/deploy-production.sh /absolute/deployment-home start
scripts/deploy-production.sh /absolute/deployment-home auth-import
```

`start` 已执行导入。使用显式命令轮换或选择其他 Host 身份，然后运行通用 `verify`。

## Agent 选择

`JARVIS_RUNTIME_AGENT` 和 `runtime.env` 中的可选 scope override 选择 Agent 可执行文件。变更属于 operator 配置变更，需要 doctor/smoke 加上受影响的 workflow 验证；不涉及 Jarvis context 或 deployment lock。

## Delivery Metrics value-judge

Delivery Metrics 使用 `value-judge` scope 分批判断历史 MR/PR。它默认继承全局 Runtime Agent；以下命令设置或取消独立选择：

```bash
jarvis-box agent list
jarvis-box agent set --scope value-judge codex
jarvis-box agent unset --scope value-judge
```

`agent list` 的 `scoped runtime agents` 会显示 `value-judge` 的 effective Agent、来源、命令和 prefix args。设置前运行 `jarvis-box agent doctor` 和 `jarvis-box agent smoke <agent>`。

服务在每个判断批次前从 canonical runtime env 解析 Agent、命令、prefix args 和模型配置。修改后下一批会采用新配置，无需重启；执行配置变化不会使已经分析的 evidence 失效。`JARVIS_RUNTIME_AGENT_SCOPE_VALUE_JUDGE_PREFIX_ARGS` 只影响该 scope。

`JARVIS_STATUS_VALUE_JUDGMENT_POLICY` 改变判断口径。服务启动时读取该策略；修改后重启会生成新的 policy digest，并按新口径分批分析历史记录。进度与恢复步骤见 [Delivery Metrics 历史基线](delivery-metrics.md)。

## Skill 发现

- 镜像自带的通用 `skill-creator` 链接到 Codex/Claude discovery roots；
- create-jarvis 绝不安装在正式运行时中；
- 客户 Jarvis skills 由该 Jarvis 的 Runtime Foundation 在持久 Agent HOME 中安装/更新；
- jarvis-box 不将 root skill、`JARVIS_HOME`、commit 或 workflow 路径注入 Run；
- identity 自有的已有 skills 不被镜像 entrypoint 覆盖。

Runtime Foundation onboarding 必须通过真实 Agent 调用来证明发现。仅有文件系统存在是不够的。

uv-im-connector 拥有 provider 原生 IM secrets 和长连接；jarvis-box 仅使用 connector protocol/token，不将 connector secrets 传递给 Agent 子进程。
