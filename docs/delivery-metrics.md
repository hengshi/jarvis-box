# Delivery Metrics 历史基线操作手册

Delivery Metrics 统计当前 `glab` 或 `gh` 登录账号在已配置仓库中由自己 author 且已合并的 MR/PR，并判断合并前后的 source revision 是否被非 author、非 jarvis 的人类反馈纠正过。

这条分析是普通 `delivery-metrics` lane。Status 服务只负责枚举 MR/PR、按节奏启动 pending 项对应的 Task、读取 Task 根目录的 `delivery-metrics-result.json` 并写入统计缓存。它不维护全局 FIFO queue，也不创建私有分析生命周期。

## 一分钟检查

先打开 `http://127.0.0.1:8787/status`。Docker 用户改用受信任网络中的 `http://<docker-host>:8787/status`。选择 GitLab 或 GitHub 后，交付质量卡片会显示历史基线进度和当前正在分析的 MR/PR。

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

把 `provider` 改成 `github` 可查看 GitHub。关键字段：

| 字段 | 判断方法 |
| --- | --- |
| `configured` | `false` 表示该 Provider 没有统计仓库配置。 |
| `snapshot.delivery_metrics.lane` | 必须是 `delivery-metrics`。 |
| `snapshot.totals.actor_merged_change_requests` | 当前 Provider 登录账号作为 author 的历史已合并 MR/PR 数。 |
| `snapshot.totals.evidence_pending` | 尚未取得 Delivery Metrics Task 结果的数量。 |
| `snapshot.runtime_token_usage` | 兼容字段；当前保留 Task 记录内按 runtime agent / model 汇总的 token 用量，`window=retained-task-state`；Status 页面暂不把它展示为 KPI。 |
| `analysis_progress.phase` | `discovering_history`、`task-running` 或 `complete`。 |
| `analysis_progress.current_batch` | 当前已由 Status 发现并等待 Task 结果的 MR/PR。 |
| `freshness` | `fresh` 使用当前快照，`stale` 使用 24 小时内的旧快照，`expired` 不再展示旧数据。 |
| `completeness` | `partial` 表示部分仓库或采集范围失败，此时聚合比例为 `null`。 |

`evidence_pending=0` 且 `analysis_progress.phase=complete` 表示历史基线完成。pending 未归零前，质量比例保持 `null`，页面显示 `-`。

## Lane Task 行为

Status 每次 Provider 刷新最多启动一个新的 `delivery-metrics` Task，避免一次性塞满任务列表。已有 Task 未完成或结果无效时，Status 保持该 MR/PR 为 pending，并在页面和 API 中展示当前批次。`delivery-metrics` Task 的完成或 Continue 事件会让 fresh snapshot 在下一次普通 GET 时重新刷新，从而读取结果文件并准入下一个 pending 项；打开的 Status 页面收到完成事件后会自动发出这个 GET，并逐项续跑到 `pending=0`。Cancel 事件也会触发刷新，但 cancelled Task 的结果不会进入统计，仍 pending 的 MR/PR 可启动替代 Task。这不是后台 queue；页面关闭时，API 仍保持一次 GET 最多启动一个 Task 的边界。

这些 Task 和其他 lane Task 一样：

- 正在执行或等待恢复时会出现在默认 `jarvis-box tasks list`；历史记录用 `jarvis-box tasks list --all --lane delivery-metrics` 查看；也会进入 `/status` 工作项列表；
- 可以用普通 Task detail 查看 `prompt.txt`、`run-context.json`、事件和 Run；
- 可以 Continue 或 Cancel；
- Continue 后仍使用 `delivery-metrics` lane 和 `delivery-metrics` runtime-agent scope；
- 完成后由 Status 读取 Task 根目录 `delivery-metrics-result.json`。

Cancel 只终结当前分析 Task，不终结该 MR/PR 派生出来的统计项。若这个 MR/PR 仍是 pending，下一次 Provider 刷新可以启动替代 Task；要把它作为最终不可判断结果计入基线，应让 Task 写出严格的 `{"classification":"judgment-unknown"}`。

Task prompt 的问题被限制为单个 MR/PR：

```text
查看这个 MR/PR 的后续 source revision 是否由 author/jarvis 之外的人类反馈促成。
促成条件是人类指正了原 MR/PR 的错误；只要求 rebase/cherrypick 不算指正。
```

Agent 必须只返回严格 JSON object：

```json
{"classification":"unchanged"}
```

`classification` 只能是：

- `unchanged`
- `self-revised`
- `human-corrected`
- `judgment-unknown`

自由文本、Markdown、额外字段、缺字段或非法枚举都不会进入统计；该 Task 会继续表现为 pending，可由 operator Continue 或 Cancel。

## 结果分类

后端从 classification 派生两个面向人的交付质量指标：

- `unchanged`：未发现后续 source revision。
- `self-revised`：发生过 revision，但未判断为人类指正原 MR/PR 错误后促成。
- `human-corrected`：非 author、非 jarvis 的人类指正原 MR/PR 错误，并促成后续 source revision。
- `judgment-unknown`：Agent 无法按合同判断。
- `pending`：尚无有效 Task 结果，不是最终分类。

`未发现人工纠正 = unchanged + self_revised`，`发现人工纠正 = human_corrected`。两者共享 `correction_known = unchanged + self_revised + human_corrected` 分母。`judgment_unknown` 和 `evidence_pending` 不进入比例分母。

## 恢复和排障

1. 确认服务可用：Native 运行 `jarvis-box status`，Docker 运行部署脚本的 `verify`。
2. 打开 `/status`，或对目标 Provider 执行一次普通 value API GET。首次请求会读取当前账号和仓库历史，并启动一个 pending Task。
3. 查看 `analysis_progress.current_batch`，再到 `jarvis-box tasks list --all --lane delivery-metrics` 找对应历史 `delivery-metrics` Task；若该 Task 仍在执行或等待恢复，默认 `jarvis-box tasks list` 也会显示。
4. 如果 Task 失败、超时或结果无效，按普通 Task 处理：查看 detail，修复 Agent 或 prompt 后 Continue；不需要操作任何私有 queue。
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

普通 GET 会使用 15 分钟 fresh TTL；如果收到 `delivery-metrics` Task 事件，下一次普通 GET 会跳过 fresh hit 并重新同步。`refresh=1` 会手动跳过 TTL，重新同步 Provider 历史，并尝试为新的 pending 项启动一个 Task：

```bash
curl -fsS "${status_url}/status/api/value?provider=${provider}&refresh=1" |
  jq '{status, freshness, completeness, warnings, analysis_progress}'
```

不要密集发送 `refresh=1`。它不是批量启动按钮；同一 Provider 已有刷新时，新请求会加入现有刷新。

## 启用和禁用 lane

`JARVIS_DELIVERY_METRICS_ENABLED` 控制 lane 是否接收新的启动请求，默认 `true`。设为 `false` 并重启 jarvis-box 后：

- Status 刷新仍枚举 Provider 历史并统计 pending 数量，但不再启动新的 `delivery-metrics` Task；
- 操作台对 `delivery-metrics` lane 的直接 Start 请求返回 `409 delivery_metrics_lane_disabled`，恢复和 source-start 入口同样按 lane admission 拒绝；
- 已在运行的 Task 不受影响，继续按普通生命周期运行，Continue 仍可用于收尾；
- `snapshot.delivery_metrics.enabled` 变为 `false`，/status 页面的交付质量卡片会提示 lane 已禁用。

重新设为 `true` 并重启后，下一次刷新按 Provider 历史重新派生 pending 项，不需要迁移任何状态。

## 选择判断 Agent

Delivery Metrics 默认继承全局 Runtime Agent。你可以为它设置独立 scope：

```bash
jarvis-box agent list
jarvis-box agent doctor
jarvis-box agent smoke codex
jarvis-box agent set --scope delivery-metrics codex
```

取消 override：

```bash
jarvis-box agent unset --scope delivery-metrics
```

`JARVIS_RUNTIME_AGENT_SCOPE_DELIVERY_METRICS_PREFIX_ARGS` 可为该 scope 增加模型等参数。下一次 Start 或 Continue 会读取新配置，不需要重启服务。

升级时，`jarvis-box update` 会执行 Flyway migration，把旧 `JARVIS_RUNTIME_AGENT_SCOPE_VALUE_JUDGE` 和 `JARVIS_RUNTIME_AGENT_SCOPE_VALUE_JUDGE_PREFIX_ARGS` 一次性改写为 Delivery Metrics scope 变量，并移除旧的自定义 judgment policy 变量。运行时不继续兼容旧变量名。

## 持久化边界

Jarvis Box 把 Delivery Metrics 派生状态放在 `JARVIS_STATE_DIR/status-value/`：

```text
snapshots/<provider>.json
evidence/<provider>/<hash>.json
```

snapshot 保存当前快照、Provider scope、登录主体和 pending 数量；evidence 保存已完成的 typed classification 和固定 evidence code。实际分析过程属于 `delivery-metrics` Task，Task 根目录保存 prompt、run context、Run artifact 和 `delivery-metrics-result.json`。

服务只复用 scope、actor 和 schema 均匹配的状态。scope 包含 Provider、Provider host、配置仓库集合和 Delivery Metrics 合同版本。单个 MR/PR 的 SHA 或 `updated_at` 变化会创建新 evidence key。

不要手工编辑派生状态。文件损坏、版本不兼容或 scope 不匹配时，服务会忽略旧状态并在下一次 Provider 请求中重建。

旧 value-judge 的已分析状态不会迁入新的 lane task 结果。新版只接受 `delivery-metrics` Task 产生的 `delivery-metrics-result.json`；旧 `status-value/queues/`、旧 schema evidence 和 snapshot 都会按版本/合同不匹配处理为可重建状态。

## 指标边界

- 观察窗口从当前 Provider 登录账号的 `created_at` 开始，到快照的 `generated_at` 为止。
- `actor_merged_change_requests` 只统计该账号作为 author 的已合并 MR/PR，不统计它在其他作者变更中的贡献。
- Provider merge 是工程交付 proxy，不代表终端客户业务验收。
- Jira、飞书项目、跨来源关联、聚合和去重均不在当前 response 中。

页面口径见 [Status UI](status-ui.md#累计产出与交付质量)，完整 response 合同见 [Status API](status-api.md#gitlab--github-provider-native-delivery-metrics-读模型)。
