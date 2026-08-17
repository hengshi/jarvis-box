# Delivery Metrics 历史基线操作手册

Delivery Metrics 统计当前 `glab` 或 `gh` 登录账号在已配置仓库中的历史合并交付，并用 Runtime Agent 分批判断公开人类反馈是否促成了后续代码修订。

这套分析由 Status 服务管理。它不创建 Task、Run 或 Workspace，因此不会出现在 `jarvis-box tasks list`，也不能用 Start、Continue 或 Cancel 控制。打开 `/status` 或读取 value API，服务就会加载持久化进度并继续未完成的基线。

## 一分钟检查

先打开 `http://127.0.0.1:8787/status`。Docker 用户改用受信任网络中的 `http://<docker-host>:8787/status`。选择 GitLab 或 GitHub 后，交付质量卡片会显示历史基线进度、当前阶段、使用的 Agent、当前批次和重试信息。

需要结构化结果时运行：

```bash
status_url=http://127.0.0.1:8787
provider=gitlab

curl -fsS "${status_url}/status/api/value?provider=${provider}" |
  jq '{
    configured,
    status,
    freshness,
    completeness,
    warnings,
    analysis_progress,
    totals: (.snapshot.totals // null)
  }'
```

把 `provider` 改成 `github` 可查看 GitHub。结果中的关键字段：

| 字段 | 判断方法 |
| --- | --- |
| `configured` | `false` 表示该 Provider 没有统计仓库配置。 |
| `snapshot.totals.actor_merged_change_requests` | 当前 Provider 登录账号作为 author 的历史已合并 MR/PR 数。 |
| `snapshot.totals.evidence_pending` | 尚待后台分析的数量。大于 0 表示基线仍在建立。 |
| `analysis_progress.analyzed / total` | 已分析数量与本轮历史总数。 |
| `analysis_progress.phase` | 当前阶段。`retry_wait` 需要结合错误码处理。 |
| `freshness` | `fresh` 使用当前快照，`stale` 使用 24 小时内的旧快照，`expired` 不再展示旧数据。 |
| `completeness` | `partial` 表示部分仓库或采集范围失败，此时聚合比例为 `null`。 |

`evidence_pending=0` 且 `analysis_progress.phase=complete` 表示历史基线完成。`pending` 未归零前，质量比例保持 `null`，页面显示 `—`。

## 分析阶段

| `phase` | 服务正在做什么 | 你需要做什么 |
| --- | --- | --- |
| `discovering_history` | 验证 Provider 登录主体，并枚举观察窗口内的已合并 MR/PR。 | 等待本轮采集。若最终返回 unavailable，检查 `warnings`。 |
| `scheduled` | 快照、待分析队列和游标已经落盘，服务等待下一批。 | 等到 `next_attempt_at`。 |
| `collecting_evidence` | 服务为 `current_batch` 读取 commit、评论、review 和时间线证据。 | 无需操作。 |
| `judging` | `analysis_progress.agent` 正在判断当前批次。 | 无需操作。 |
| `persisting` | 服务写入分类结果并推进队列游标。 | 不要编辑 state 文件。 |
| `retry_wait` | 本批失败，服务等待退避后重试。 | 按 `last_error_code` 排查，并参考 `next_attempt_at`。 |
| `complete` | 待分析数已经归零。 | 无需操作。 |

每批最多分析 5 个 MR/PR。正常批次间隔约 10 秒；失败后通常等待约 1 分钟。Provider 历史量较大时，基线会持续较长时间。页面和 API 会显示真实进度。

## 恢复中断的基线

1. 确认服务可用：Native 运行 `jarvis-box status`，Docker 运行部署脚本的 `verify`。
2. 打开 `/status`，或对目标 Provider 执行一次普通 value API GET。首次请求会加载可兼容的 snapshot、队列和 cursor，并安排下一批。
3. 查看 `analysis_progress`。`scheduled`、`collecting_evidence`、`judging` 和 `persisting` 都表示恢复链正在工作。
4. 遇到 `retry_wait` 时处理错误码，等待 `next_attempt_at`。服务会保留 pending 项并重试。
5. 看到 `pending=0` 和 `phase=complete` 后结束观察。

需要持续观察时可运行：

```bash
while :; do
  date
  curl -fsS "${status_url}/status/api/value?provider=${provider}" |
    jq '.analysis_progress // {phase: "unavailable"}'
  sleep 10
done
```

按 `Ctrl-C` 停止观察。

普通 GET 是恢复入口。`refresh=1` 会绕过 15 分钟快照 TTL，重新同步 Provider 历史，然后生成或更新待分析队列。修复 Provider 认证、仓库配置或旧快照问题后再使用它：

```bash
curl -fsS "${status_url}/status/api/value?provider=${provider}&refresh=1" |
  jq '{status, freshness, completeness, warnings, analysis_progress}'
```

不要连续发送 `refresh=1`。它不是 Continue 按钮，也不会创建 Task；同一 Provider 已有刷新时，新请求会加入现有刷新。

服务重启不会丢失已落盘的结果。新进程在第一次读取该 Provider 时恢复兼容的队列和 cursor。若旧快照超过 TTL，服务会先执行一次有界刷新，并复用仍然有效的 evidence。

## 错误码处理

| `last_error_code` | 含义 | 处理 |
| --- | --- | --- |
| `judge_timeout` | Runtime Agent 在判断时超时。 | 运行 `jarvis-box agent list`、`jarvis-box agent doctor` 和目标 Agent 的 smoke；必要时切换 `value-judge` scope。 |
| `judge_failed` | Agent 启动、退出或返回结构不符合判断合同。 | 查看 `jarvis-box logs`，验证 Agent，再等待下一次重试。 |
| `persistence_failed` | snapshot、queue、cursor 或 evidence 没有完成持久化。 | 检查 state 所在磁盘的空间和权限，运行 doctor 并查看日志。不要手工推进 cursor。 |
| `evidence_retry` | Provider 证据读取遇到限流、5xx、超时或其他瞬时失败。 | 检查 Provider CLI 认证和网络，等待退避。不要用密集 refresh 加重限流。 |

`analysis_progress` 之外的采集问题写在 `warnings`。常见处理如下：

| 现象或 warning | 处理 |
| --- | --- |
| `projects_not_configured` | 为 GitLab 配置 `GITLAB_PROJECTS`，或为 GitHub 配置 `GITHUB_REPOSITORIES`，然后重启服务。 |
| `gitlab_auth_failed` / `github_auth_failed` | 在 Jarvis Box 使用的同一 OS 用户或 Docker runtime 中运行 `glab auth status` / `gh auth status`。修复后使用一次 `refresh=1`。 |
| `collection_timeout`、Provider unavailable 或全部仓库失败 | 检查 Provider 可达性、allowlist 和服务日志。24 小时内仍有旧快照时，API 会返回 `stale`。 |
| `snapshot_expired` | 修复 Provider 问题后使用一次 `refresh=1`；服务不会展示超过 24 小时的旧快照。 |
| `evidence_pending` 不变且没有 `analysis_progress` | 运行 `jarvis-box version` 和 `jarvis-box update --check`。v0.2.11 及以上会为未完成基线返回进度；按[升级手册](operations.md#升级)升级旧版本。 |
| Delivery Metrics 没有出现在 `jarvis-box tasks list` | 这是正常行为。使用 `/status` 或 value API 查看和恢复。 |

升级会检查 active Task。先等待、Continue 或 Cancel 这些 Task，再规范停服和升级。Delivery Metrics 本身不会阻止升级；不要只为恢复基线使用强制停服。

## 选择判断 Agent

Delivery Metrics 默认继承全局 Runtime Agent。你可以为它设置独立 scope：

```bash
jarvis-box agent list
jarvis-box agent doctor
jarvis-box agent smoke codex
jarvis-box agent set --scope value-judge codex
```

后续批次会读取新的 Agent 选择，不需要重启服务。切换 Agent 或模型不会重算已经完成的历史结果；`analysis_progress.agent` 显示当前批次使用的 Agent。

你也可以取消 override，让它继续继承全局 Agent：

```bash
jarvis-box agent unset --scope value-judge
```

`JARVIS_RUNTIME_AGENT_SCOPE_VALUE_JUDGE_PREFIX_ARGS` 可为该 scope 增加模型等参数。修改 prefix args 或模型配置后，下一批会读取新配置，无需重启服务。

`JARVIS_STATUS_VALUE_JUDGMENT_POLICY` 定义“公开人类反馈是否促成后续修订”的判断口径。修改策略后必须重启服务，历史记录会按新策略分批重新分析。先评审口径，再修改 canonical runtime env。完整变量说明见[配置参考](configuration.md#runtimeenv)，Agent 行为见 [Runtime Agent](runtime-agents.md#delivery-metrics-value-judge)。

## 持久化与重建边界

Jarvis Box 把以下派生状态放在 `JARVIS_STATE_DIR/status-value/`：

```text
snapshots/<provider>.json
queues/<provider>/<generation>/manifest.json
queues/<provider>/<generation>/<shard>.json
evidence/<provider>/<hash>.json
```

snapshot 保存快照与 cursor，queue 保存待分析 MR/PR，evidence 保存已完成的 typed 分类。服务只在以下范围仍匹配时复用状态：Provider host、仓库集合、当前登录账号、schema、判断合同和判断策略。

这些文件不属于 Task Artifact。`jarvis-box tasks clean` 不处理它们，Task 的 Continue 和 Cancel 也不会影响它们。不要手工编辑、移动或只删除 cursor。持久化数据损坏或不兼容时，服务会忽略它并从 Provider 重建；先保留副本和日志，再执行恢复。

以下变化会影响复用范围：

| 变化 | 结果 |
| --- | --- |
| Provider 登录账号变化 | 服务使旧账号的 snapshot 和队列失效，并为新账号建立基线。 |
| Provider host 或统计仓库集合变化 | 服务忽略旧 scope，按新范围刷新。 |
| 判断策略、判断合同或 schema 变化 | 服务按新口径分批重新分析。 |
| 单个 MR/PR 的 SHA 或 `updated_at` 变化 | 服务只重新分析变化后的证据键。 |
| Runtime Agent 或模型变化 | 已分析 evidence 保持有效，未完成批次使用新的 Agent 选择。 |

存储细节见[持久化与恢复](storage-model.md#delivery-metrics-派生状态)，完整 response 合同见 [Status API](status-api.md#gitlab--github-provider-native-delivery-metrics-读模型)。

## 指标边界

- 观察窗口从当前 Provider 登录账号的 `created_at` 开始，到快照的 `generated_at` 为止。
- `actor_merged_change_requests` 只统计该账号作为 author 的已合并 MR/PR，不统计它在其他作者变更中的贡献。
- Provider merge 是工程交付 proxy，不代表终端客户业务验收。
- `unchanged`、`self-revised` 和 `human-corrected` 由当前判断口径定义；`judgment_unknown` 与 `evidence_unknown` 不进入比例分母。

页面口径见 [Status UI](status-ui.md#累计产出与交付质量)。
