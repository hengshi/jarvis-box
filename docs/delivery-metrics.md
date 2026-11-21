# Delivery Metrics 历史起点操作手册

本文面向查看或恢复 GitLab/GitHub 代码交付质量历史起点的客户 operator。它不是通用业务 KPI：它统计当前 `glab` 或 `gh` 登录账号在已配置仓库中由自己 author、且已合并的 MR/PR，并判断后续 source revision 是否由 author/Jarvis 之外的人类实质纠正促成。

分析使用普通 `delivery-metrics` lane Task。服务启动、MR/PR 关闭/合并和定时补查会同步历史；Status 读取完成 Run 的 `delivery-metrics-result.json` 并更新结果。它没有独立全局 queue 或第二套 Start/Continue/Cancel 生命周期。

<a id="一分钟检查"></a>

## 快速查看

Native 默认打开 `http://127.0.0.1:8787/status`；Docker 使用受信网络中的 `http://<docker-host>:8787/status`。选择 GitLab 或 GitHub 后，在交付质量卡查看进度与当前分析项。

需要结构化值时：

```bash
status_url=http://127.0.0.1:8787
provider=gitlab # or github

curl -fsS "${status_url}/status/api/value?provider=${provider}" |
  jq '{configured, status, freshness, completeness, warnings, analysis_progress,
       totals: (.snapshot.totals // null)}'
```

| 字段 | 如何使用 |
| --- | --- |
| `configured` | `false` 表示该 Provider 没有配置统计仓库。 |
| `snapshot.delivery_metrics.lane` | 应为 `delivery-metrics`。 |
| `snapshot.totals.actor_merged_change_requests` | 当前登录账号 author 的已合并 MR/PR 数。 |
| `snapshot.totals.evidence_pending` | 仍没有有效分析结果的数量。 |
| `analysis_progress.phase` | `discovering_history`、`task-running` 或 `complete`。 |
| `analysis_progress.current_batch` | 已发现且等待结果的 MR/PR。 |
| `freshness` | `fresh` 为当前快照；`stale` 仍可显示最多 24 小时旧快照；`expired` 不展示旧数据。 |
| `completeness` | `partial` 表示某些仓库/采集范围失败，聚合比例为 `null`。 |

`evidence_pending=0` 且 `phase=complete` 才表示历史起点完成。pending 未归零时质量比例必须保持 `null`，页面显示 `-`。`snapshot.runtime_token_usage` 是兼容空壳，当前 release 固定 `status=not_available`、`agents=[]` 且计数为零；不要将它作为模型或成本 KPI。

<a id="结果分类"></a>
<a id="指标边界"></a>

## 分类和指标口径

新分析同时给出人工纠正结论和交付来源。结果文件只接受一个严格 JSON 对象，例如：

```json
{"classification":"unchanged","origin":"original"}
```

`origin` 可用值为 `original`、`backport`、`self-improve`、`unknown`。结果文件和 `classification` 有效时，缺少来源或来源值无效的记录仍保留人工纠正结论。缺少可核验的复核结论时，来源标为待复核。
允许值与显示口径：

| 分类 | 含义 | 是否进入纠正比例 |
| --- | --- | --- |
| `unchanged` | 未发现后续 source revision | 是，未发现人工纠正 |
| `self-revised` | 有 revision，但没有人类自身实质纠正促成它 | 是，未发现人工纠正 |
| `human-corrected` | 非 author、非 Jarvis 的人类写出实质纠正，并促成后续 revision | 是，发现人工纠正 |
| `judgment-unknown` | Agent 无法按合同判断 | 否 |
| `pending` | 尚无有效 Task 结果 | 否 |

自由文本、Markdown、多余字段、缺字段或非法值不会进入统计，仍是 pending。人类只是转述或要求 Agent 按 bot/Jarvis review 修复，不继承 bot/Jarvis 的纠错内容；单纯 rebase/cherry-pick 也不是纠正。MR/PR 只能按单一对象分析。

观察窗口从当前 Provider 登录账号的 `created_at` 到 snapshot `generated_at`。这只是工程交付 proxy，不代表终端客户业务验收；Jira、飞书项目、跨来源合并/去重也不在此 response 中。

## 历史交付来源

已有完整复核依据的记录可通过本机 CLI 导入。输入文件须仅当前用户可读写，包含 `version: 1`、`scope` 和 `entries`。`scope` 指定 `provider`、`host`、`account_id`、`account` 和 RFC3339 的 `account_created_at`。每项 `entries` 指定小写仓库路径 `repository`、`number`、40 位小写的 `head_sha` 和确认后的 `origin`。源 SHA 缺失的历史条目继续暂计入。

```sh
jarvis-box metrics delivery-origins --file /path/to/review.json
jarvis-box metrics delivery-origins --file /path/to/review.json --apply --expect-sha256 <预览返回的摘要>
```

预览返回作用范围、按来源分类的数量和摘要。应用成功后，Status 在下一次采集中读取本机记录。同一账号范围接受同一文件的重试，已有复核文件时会拒绝不同内容。导入保留人工纠正结论，无需重新分析这些 MR/PR。

<a id="lane-task-行为"></a>
<a id="恢复和排障"></a>

## 运行、暂停与恢复

后台每轮每个 Provider 最多启动一个新分析 Task。同一 Provider 已有分析时等待它完成；完成、Continue、Cancel 事件会唤醒同步，关闭页面也不会中断。磁盘不足时保留原输入为 storage wait，空间恢复后自动启动，不依赖刷新。

活动或等待恢复的 Task 在 `jarvis-box tasks list` 和 `/status` 中出现；历史项用：

```bash
jarvis-box tasks list --all --lane delivery-metrics
jarvis-box tasks show <task-id>
```

结果无效、读取失败、Agent 失败或超时时，先查看该 Task，再按普通 Task 流程修复并 Continue。成功 Run 缺少有效结果时 evidence 为 `analysis-result-invalid`；它不表示 Agent 仍在跑，后台不会替它新建 Task。Stop 将该 canonical MR/PR 记为 `judgment-unknown` 并停止自动替代；显式 Continue 在同一 Task 里生成新的有效结果。Cancel 是否允许遵循该 Task 的公开 action policy，已 completed Task 不可 Cancel。

普通 GET 和 `refresh=1` 只同步和读取，绝不创建分析 Task：

```bash
curl -fsS "${status_url}/status/api/value?provider=${provider}&refresh=1" |
  jq '{status, freshness, completeness, warnings, analysis_progress}'
```

不要密集调用 `refresh=1`；同一 Provider 的并发刷新会合并。持续观察可轮询 `analysis_progress`，但后台每分钟补查和事件同步已会主动更新。

<a id="启用和禁用-lane"></a>

## 启用或禁用新分析

在 canonical runtime env 设置：

```dotenv
JARVIS_DELIVERY_METRICS_ENABLED=false
```

重启服务后，历史仍会被枚举，pending 仍会显示，但后台和 Status 不再启动新的 `delivery-metrics` Task，直接 Start/恢复入口返回 `409 delivery_metrics_lane_disabled`。已运行 Task 和 Continue 可以收尾。重新设为 `true` 并重启后，后台重新从 Provider 历史派生 pending 项，不需要迁移状态。

## 选择判断 Agent

默认继承全局 Runtime Agent。为此 lane 配置独立 Agent 前先检查它：

```bash
jarvis-box agent list
jarvis-box agent doctor
jarvis-box agent smoke codex
jarvis-box agent set --scope delivery-metrics codex
```

取消覆盖：

```bash
jarvis-box agent unset --scope delivery-metrics
```

`JARVIS_RUNTIME_AGENT_SCOPE_DELIVERY_METRICS_PREFIX_ARGS` 可添加此 scope 的模型或 runtime 参数。下一次 Start/Continue 读取新配置；已完成历史结论不会因此重算或改写。旧变量的迁移由升级处理，运行时不应继续设置旧 judgment-policy 变量。

<a id="持久化边界"></a>

## 持久化与缓存边界

派生状态位于 `JARVIS_STATE_DIR/status-value/`：

```text
snapshots/<provider>.json
evidence/<provider>/<hash>.json
```

snapshot 保存当前 scope、登录主体、快照和 pending 数量；evidence 保存完成后的 typed classification 和固定 evidence code。实际分析只在 Task/Run 中执行。scope 包含 Provider、host、仓库集合和合同版本；只有 scope、actor 和 schema 匹配时才复用。相同 Provider/host/account/repository/MR-or-PR/source SHA 的有效结论可继续复用，单纯 `updated_at` 变化不使它失效；账号、主体或 source SHA 不同则不可复用。

不要手工编辑 `status-value/`。损坏、版本不兼容或 scope 不匹配时服务忽略派生值，并在 Provider 同步时重建 snapshot；已有失败或无效 Task 仍须明确 Continue。旧 `status-value/queues/` 不是 Task/Run 事实，不能导入为当前分析执行状态。

页面字段定义见[Status UI](status-ui.md#累计产出与交付质量)，完整 response schema 见[Status API](status-api.md#gitlab--github-provider-native-delivery-metrics-读模型)。
