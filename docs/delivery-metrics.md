# Delivery Metrics 历史起点操作手册

Delivery Metrics 统计当前 `glab` 或 `gh` 登录账号在已配置仓库中由自己 author 且已合并的 MR/PR，并判断合并前后的 source revision 是否被非 author、非 jarvis 的人类反馈纠正过。

这条分析是普通 `delivery-metrics` lane。服务启动后自动枚举 MR/PR，收到关闭或合并 webhook 后立即同步，并每分钟补查。分析完成后自动读取 selected exact Run 的 `delivery-metrics-result.json`、更新统计并接续尚无 Task owner 的 pending 项；无需打开 Status。它不维护全局 FIFO queue，也不创建私有分析生命周期。

已完成的历史分析保留原分析口径，升级软件或分析合同标记不会自动重算。相同 Provider、账号身份、MR/PR 与源 SHA 的有效结论继续复用，合并后的评论或元数据更新时间变化不会使结论失效。已发布的 schema 4/v7 结果文件及 v1 合同结论保持可读，原 Task 已清理时也保留这一保证；账号或代码事实变化仍不得串用。需要重新判断时由操作者明确发起。

## 一分钟检查

先打开 `http://127.0.0.1:8787/status`。Docker 用户改用受信任网络中的 `http://<docker-host>:8787/status`。选择 GitLab 或 GitHub 后，交付质量卡片会显示历史起点进度和当前正在分析的 MR/PR。

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
| `snapshot.runtime_token_usage` | 兼容字段；当前 release 恒定是空壳（`status=not_available`、`agents=[]`、各级计数与 token 数都是 0），按 runtime agent / model 的汇总要等 EM-METRIC-002 的 Run receipt 才能成立，`window` 固定为 `retained-task-state`；Status 页面不把它展示为 KPI。 |
| `analysis_progress.phase` | `discovering_history`、`task-running` 或 `complete`。 |
| `analysis_progress.current_batch` | 当前已由 Status 发现并等待 Task 结果的 MR/PR。 |
| `freshness` | `fresh` 使用当前快照，`stale` 使用 24 小时内的旧快照，`expired` 不再展示旧数据。 |
| `completeness` | `partial` 表示部分仓库或采集范围失败，此时聚合比例为 `null`。 |

`evidence_pending=0` 且 `analysis_progress.phase=complete` 表示历史起点完成。pending 未归零前，质量比例保持 `null`，页面显示 `-`。

## Lane Task 行为

GitHub 与 GitLab 使用相同的持久化准入：磁盘空间不足时保留原分析输入，显示资源等待，空间恢复后自动启动原分析 Task，不依赖页面刷新，也不会把已有 Task 的存在误当作分析正在执行。

后台每轮为每个 Provider 最多启动一个新的 `delivery-metrics` Task，同一 Provider 已有分析正在处理时等待其完成。完成、继续和取消事件唤醒后台同步；页面关闭时也会自动接续到 `pending=0`。已有 Task 的普通业务失败或无效结果保持 pending，由操作者明确 Continue 或 Cancel，后台扫描不自动付费重试。受信的三类原生终止只按[有界自动 Continue 合同](execution-model.md#原生终止的有界自动-continue)恢复，不授权其他错误重跑。Cancel 把该 canonical MR/PR 作为最终 `judgment-unknown` 计入统计，不创建替代 Task。普通 GET 与 `refresh=1` 只同步和读取统计，不启动分析。

如果读取期间 Task 正在变化，或暂时无法取得一致的 Task/Run 证据，本次读取保守返回 `evidence-unknown`，不将它缓存为最终分类；已经留存的该类缓存也按未命中处理，后续刷新会重新读取，避免临时读取问题掩盖已经完成的分析结果。

这些 Task 和其他 lane Task 一样：

- 正在执行或等待恢复时会出现在默认 `jarvis-box tasks list`；历史记录用 `jarvis-box tasks list --all --lane delivery-metrics` 查看；也会进入 `/status` 工作项列表；
- 可以用普通 Task detail 查看全部 Run、exact Run 的 bounded prompt/RunTrace 投影和事件；raw `prompt.txt`、`run-context.json` 不作为公开 Artifact 暴露；
- 可以 Continue 或 Cancel；
- Continue 后仍使用 `delivery-metrics` lane 和 `delivery-metrics` runtime-agent scope；
- 完成后由 Status 从完成该次分析的 exact Run 读取 `delivery-metrics-result.json`。

Cancel 终结该 canonical MR/PR 的分析 Task，并将其投影为最终不可判断结果；后续刷新不会为同一 subject 创建第二个 Task。取消是 retained state 内的最终操作；Agent 自主无法判断时仍应写出严格的 `{"classification":"judgment-unknown"}`，不要用 Cancel 代替正常结果。

Task prompt 的问题被限制为单个 MR/PR：

```text
查看这个 MR/PR 的后续 source revision 是否由 author/jarvis 之外的人类反馈促成。
促成条件是人类自己指出了原 MR/PR 的错误、遗漏需求、correctness 风险或具体需要改动的内容，并且后续 source revision 能和这条人类指正建立因果关系。
人类只是转述、确认或要求 agent 按 bot/Jarvis review 修复，不继承 bot/Jarvis review 的纠错内容；如果没有人类自己的实质纠错内容，发生过 revision 也归入 `self-revised`。
只要求 rebase/cherrypick 不算指正。
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

自由文本、Markdown、额外字段、缺字段或非法枚举都不会进入统计；该 MR/PR 会继续表现为 pending，可由 operator 在原 Task 上明确 Continue。

成功 Run 未形成可用的严格分析结果时，该 MR/PR 的 `evidence` 包含 `analysis-result-invalid`。这也涵盖结果文件缺失、不可安全读取或超出大小限制；表示需要显式 Continue 重新生成结果，不表示 Agent 仍在执行。Cancel 是否可用以原 Task 的公开 action policy 为准；已 completed 的 Task 不允许 Cancel。后台扫描不会为它创建替代 Task 或自动重试。

## 结果分类

后端从 classification 派生两个面向人的交付质量指标：

- `unchanged`：未发现后续 source revision。
- `self-revised`：发生过 revision，但未判断为人类指正原 MR/PR 错误后促成。
- `human-corrected`：非 author、非 jarvis 的人类自己写出实质纠错内容，并促成后续 source revision。
- `judgment-unknown`：Agent 无法按合同判断。
- `pending`：尚无有效 Task 结果，不是最终分类。

`未发现人工纠正 = unchanged + self_revised`，`发现人工纠正 = human_corrected`。两者共享 `correction_known = unchanged + self_revised + human_corrected` 分母。`judgment_unknown` 和 `evidence_pending` 不进入比例分母。

## 恢复和排障

1. 确认服务可用：Native 运行 `jarvis-box status`，Docker 运行部署脚本的 `verify`。
2. 服务启动后会自动读取当前账号和仓库历史；打开 `/status` 或读取 value API 查看后台分析进度。
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

普通 GET 会使用 15 分钟 fresh TTL；后台事件和每分钟补查会主动更新快照。`refresh=1` 会手动跳过 TTL 并重新同步 Provider 历史，但不提交分析任务：

```bash
curl -fsS "${status_url}/status/api/value?provider=${provider}&refresh=1" |
  jq '{status, freshness, completeness, warnings, analysis_progress}'
```

不要密集发送 `refresh=1`。它不是批量启动按钮；同一 Provider 已有刷新时，新请求会加入现有刷新。

## 启用和禁用 lane

`JARVIS_DELIVERY_METRICS_ENABLED` 控制 lane 是否接收新的启动请求，默认 `true`。修改 canonical 配置并重启后生效；涉及活动 Run 时，先完成任务或按普通服务维护流程中断，再对原 Task 显式 Continue 收尾。设为 `false` 并重启 jarvis-box 后：

- 后台和 Status 仍枚举 Provider 历史并统计 pending 数量，但不再启动新的 `delivery-metrics` Task；
- 操作台对 `delivery-metrics` lane 的直接 Start 请求返回 `409 delivery_metrics_lane_disabled`，恢复和 source-start 入口同样按 lane admission 拒绝；
- 已在运行的 Task 不受影响，继续按普通生命周期运行，Continue 仍可用于收尾；
- `snapshot.delivery_metrics.enabled` 变为 `false`，/status 页面的交付质量卡片会提示 lane 已禁用。

重新设为 `true` 并重启后，后台自动按 Provider 历史重新派生 pending 项，不需要迁移任何状态。

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

snapshot 保存当前快照、Provider scope、登录主体和 pending 数量；evidence 保存已完成的 typed classification 和固定 evidence code。实际分析过程属于 `delivery-metrics` Task；Task 根目录只保存首次 provider payload、typed state 和审计事件，每个 exact Run 保存自己的 prompt、run context、`delivery-metrics-result.json` 与其他 Run Artifact。

快照仅在 scope、actor 和 schema 均匹配时复用；scope 包含 Provider、Provider host、配置仓库集合和 Delivery Metrics 合同版本。相同 Provider、host、账号身份、仓库、MR/PR 和源 SHA 的有效结论继续复用，元数据 `updated_at` 变化不使结论失效。已发布的 schema 4/v7 证据键保留原更新时间字段，读取已知格式时忽略该字段的差异，无需重写原文件；原 Task 已清理时也可读取保留证据。不同账号、主体或源 SHA 的结果不得串用。

不要手工编辑派生状态。文件损坏、版本不兼容或 scope 不匹配时，服务会忽略不兼容的派生状态，并通过后台 Provider 同步重建快照；已有 Task 的失败或无效结果仍由操作者明确 Continue。

旧 `status-value/queues/` 不作为 Task/Run 事实导入，分析执行只属于普通 `delivery-metrics` Task。已发布 schema 4/v7 的有效结论及受支持的 v1 合同结论继续复用；不兼容的旧 schema evidence 和 snapshot 不作为当前结果读取。重建派生快照不会重跑已经完成的有效分析。

## 指标边界

- 观察窗口从当前 Provider 登录账号的 `created_at` 开始，到快照的 `generated_at` 为止。
- `actor_merged_change_requests` 只统计该账号作为 author 的已合并 MR/PR，不统计它在其他作者变更中的贡献。
- Provider merge 是工程交付 proxy，不代表终端客户业务验收。
- Jira、飞书项目、跨来源关联、聚合和去重均不在当前 response 中。

页面口径见 [Status UI](status-ui.md#累计产出与交付质量)，完整 response 合同见 [Status API](status-api.md#gitlab--github-provider-native-delivery-metrics-读模型)。
