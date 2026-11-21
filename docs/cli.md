# CLI 参考

<a id="cli-reference"></a>

本文是 Jarvis Box 已安装实例的命令参考。日常服务维护从[运维入口](operations.md)开始；Task/Run 状态、允许的操作和恢复语义以[执行模型](execution-model.md)为准。下面将“operator 在 shell 中使用的命令”和“仅当前受管 Agent Run 可调用的协议”分开说明。

## 先确认操作的是哪一个实例

```bash
jarvis-box status --smart
jarvis-box status
jarvis-box doctor
```

`status --smart` 输出 effective `runtime_root`、`env_file`、`runs_dir`、`state_dir`、`log_dir` 和 `workspace_root`。脚本和集成必须使用输出的有效路径，不能从 `$HOME`、当前目录或默认端口猜 Task/Workspace 根。

Docker 多实例应始终通过该实例的 release 脚本和 deployment home 操作；Native 中设置 `JARVIS_ENV_FILE` 或 `JARVIS_RUNTIME_ROOT` 只能选择路径，不等于选择 systemd unit 或 launchd label。详情见[多实例部署](multi-instance.md)。

命令失败时，查看 stderr 中的失败阶段、底层错误和该命令提供的只读检查。通过本机 API 执行操作的命令还会保留 HTTP 状态和错误响应。操作可能已受理时，先按原 Task、Run、Webhook 或维护收据核对结果，再决定是否重试。自动化按各命令定义的退出码和机器回执判断结果。比如 `ci wait` 退出 `2` 时表示流水线需要人工操作，应查看它报告的流水线中的手动任务或审批。

<a id="runtime-agent"></a>
<a id="runtime-tools"></a>

## Agent 与工具

```bash
jarvis-box agent list
jarvis-box agent list --check
jarvis-box agent current
jarvis-box agent doctor
jarvis-box agent smoke [<agent>]
jarvis-box agent set [--scope delivery-metrics] <agent>
jarvis-box agent unset --scope delivery-metrics

jarvis-box tools path
jarvis-box tools status [--json]
jarvis-box tools update
jarvis-box tools reset
```

`doctor` 检查 Agent executable 与配置；`smoke` 做一次真实 Agent 调用。`agent list --check` 使用同一 smoke 探测：有可见答复且退出 `0` 显示 `smoke-ok`，stderr 非空时显示 `smoke-warning` 但仍成功；空答复、命令失败或无法执行均是 `smoke-failed`。这只证明 Agent 有答复，不证明 Agent HOME 健康。输出会删控制字符并遮蔽常见凭据，只保留首个非空行（最多 512 bytes）；它不自动修改 Agent HOME 的 owner 或权限。

`agent set` 影响后续 Start；已有 Task 必须用 `tasks continue ... --agent ...` 明确切换。Runtime Agent 目录、协议与 scope 说明见[Runtime Agent](runtime-agents.md)。

Native 的 `tools path` 默认是当前用户的 `$HOME/.local/bin`，或绝对 `JARVIS_USER_TOOL_BIN`。Native 的 `tools update/reset` 会失败并提示使用原安装器或包管理器。Docker 只有明确执行 `tools update` 才下载和原子更新受管工具；失败时保留最后有效版本，`reset` 回到 image 基线。客户自装的用户级工具放入 `JARVIS_USER_TOOL_BIN`，需要 `apt` 的系统依赖使用[客户派生 Docker 镜像](custom-docker-image.md)。

Native 的 `tools status` 读取已安装工具的版本输出：成功命令优先使用标准输出，标准输出为空时使用标准错误输出。命令失败、超时或两个输出流均为空时保留工具错误，并返回非零退出码。

<a id="server-and-taskrun"></a>

## 查看、启动和接续 Task

```bash
jarvis-box serve
jarvis-box tasks list
jarvis-box tasks list --all --limit 50
jarvis-box tasks json --monitor-status ci-wait
jarvis-box tasks json --all --compact --limit 50
jarvis-box tasks show <task-id>
jarvis-box tasks start <source-task-id> --reason 'start from an existing Task'
jarvis-box tasks start --prompt 'write customer report'
jarvis-box tasks start --prompt 'write daily report' \
  --lane custom-user-task --job-id customer-daily-report \
  --reason scheduled-customer-daily-report --notify-target direct:<id>
jarvis-box tasks continue <task-id>
jarvis-box tasks continue <task-id> --agent codex --message 'continue with these instructions'
jarvis-box tasks verify
jarvis-box monitor
jarvis-box logs
jarvis-box status
jarvis-box doctor
```

`tasks list` 和 `tasks json` 默认使用维护预检的生命周期阻断判定筛选 Task。`--all` 才读取历史；`--compact` 只压缩 JSON，仍可和 `--status`、`--monitor-status`、`--lane` 和 `--limit` 组合。详情使用 `tasks show`，不要从 monitor 文本推断责任或状态。

`status` 始终返回 effective `runs_dir` 和 `workspace_root`；默认分别为 `${JARVIS_STATE_DIR}/runs` 和 `${JARVIS_RUNTIME_ROOT}/workspace`。`status`/`monitor` 只统计正式登记的 Task 和 Run，不把收据、锁或普通目录当成运行；最新运行按正式创建时间选择，产物读取精确 Run 目录。`tasks show` 只投影安全的 event-subscription 聚合，不能读取或伪造 sender、reply credential、webhook body、token、私有 journal，也不能从本机 CLI 重发订阅。

`tasks verify` 只读检查任务库。若能输出诊断报告，即使 `ok=false` 退出码仍为 0；脚本必须同时读取报告的 `ok` 与 `issues`。命令不会修复或删除坏项。


### 从外部 shell 启动 prompt Task

`tasks start --prompt` 是外部 shell 和 Runtime Foundation job 的原子入口。调用进程可以加载 canonical runtime env，包括实例级 `JARVIS_WORKSPACE_ROOT`；工作区根目录不代表 Task 身份。调用环境中存在非空的 `JARVIS_TASK_ID`、`JARVIS_TASK_DIR` 或 `JARVIS_RUN_ID` 时，命令会拒绝提交并指出具体变量，应从宿主调度器或外部 shell 发起。CLI 向 canonical runtime env 中的 loopback 服务提交一次 Start；服务分配 Task/Run 身份、登记输入并启动 Agent。调用者不得创建 Task 目录、读取 `task_dir` 或写 `prompt.txt`。

成功 JSON 返回真实 `task_id`、`task_dir`、`run_id`、`run_dir` 和 effective `workspace_root`。磁盘空间不足时，服务可以接受请求并返回 `waiting=true`、`wait_reason=storage-wait` 和真实 Task identity。Run 登记前发现空间不足时没有 Run；在启动进程前发现余量不足时已登记的 Run ID 会保留。空间恢复后自动执行原请求。其他服务健康问题仍是错误。

`--lane` 只适用于 prompt Start。默认 lane 是 `jarvis-command`；允许的额外 lane 是 `delivery-metrics` 和 `custom-user-task`。`custom-user-task` 是 providerless 用户任务，`--job-id` 仅能和它一起使用；同一 active job ID 的新 Start 返回 conflict，已完成 job 要补跑时显式创建新的 prompt Task。`--notify-target direct:<id>|group:<id>` 仅把成功 Run 的最终答复交给现有 IM 通道；它不替其他业务动作选择收件人。

### Continue

`tasks continue` 提交新输入或恢复原 Task。运行中会先停止当前 Run；若处于启动、准备、收尾、替换或清理阶段，返回 `waiting=true, wait_reason=instruction-accepted` 表示输入已保存并会衔接，无需重发。恢复丢失 Run 或重试写回时不要传 `--agent` / `--message`。服务会核对当前 Task version，状态变更后过期请求会被拒绝。

Delivery Metrics 也是普通 lane Task：活动项出现在默认列表，历史项用 `tasks list --all --lane delivery-metrics` 查看。其 Status 结果、Continue/Stop 和恢复步骤见[Delivery Metrics 历史起点](delivery-metrics.md)。

<a id="webhook-已收到但任务没有启动"></a>

## Webhook 已接收却未启动

```bash
jarvis-box webhooks list
jarvis-box webhooks show <receipt-id>
jarvis-box webhooks retry <receipt-id>
```

`list` 与 `show` 只读；`retry` 恢复原始已认证请求。它先查询原 Task/Run，已创建即复用，不以超时或错误猜测“没有创建”，也不删除去重记录。

| 结果 | 操作 |
| --- | --- |
| 有 `task_id` | `tasks show <task_id>`；不要重建。 |
| `pending` / `dispatching` | 查看 `message`，稍后再查询。 |
| `pending-comment` | 修复 `detail` 中的错误后对原 receipt 执行 `retry`；只恢复这条评论。 |
| `failed` | 按 `detail` 修复认证、网络、授权或存储，再运行 `doctor` 后 retry。 |
| `admission_outcome_unknown` | 对原 receipt 执行 `retry`，让服务查询并补结原 Task；不编辑任何账本。 |
| 明确未启动且自动恢复已用尽 | 修复具体依赖后 retry；它只授权原 receipt 的一个新尝试。 |
| 原始请求未保留 | 在来源平台重发同一已认证事件，再对该 receipt retry。 |
| 升级导入的历史去重记录 | 历史输入不自动重跑；如确需新工作，在原工作项提交新的 `@jarvis` 指令。 |
| `retry` 返回 202 | 只是恢复已提交；继续执行响应中的 `next_command`。 |
| `webhook_runtime_mismatch` 或 receipt 不存在 | `status --smart` 确认实例/任务库，再查该实例的 `webhooks list`。 |
| 记录无法读取 | 保留文件，按 `doctor` 的路径、权限和存储错误修复；不要删除记录制造未受理假象。 |

受理格式 `version` 是 Jarvis 持久数据格式，Task `revision` 是并发保护；两者都不是 Provider 用户需要配置的版本号。旧记录缺少当前协议证明时不会自动重放；`show` 会给出可用恢复命令。诊断输出不显示请求 body、认证头或 token。

<a id="补录已核验的-run-启动历史"></a>

## 受控补录 Run 启动历史

这是受授权 operator 的账本维护，不创建、Continue、Cancel 或重跑 Task/Run。完整背景和 Docker 传递边界见[运维入口](operations.md#受控补录-run-启动历史)。

```bash
python3 scripts/collect-run-start-history.py --origin LABEL \
  [--ledger FILE] [--archive FILE SHA256] --output FILE

jarvis-box metrics backfill --origin LABEL --sources FILE \
  --expect-sources-sha256 SHA --coverage-from RFC3339 \
  --attest-complete --plan FILE
jarvis-box metrics backfill --apply FILE --expect-sha256 SHA
```

Collector 从 release 根目录执行；Native 安装后位于 `${JARVIS_STATE_DIR}/app/scripts/collect-run-start-history.py`。它成功输出 manifest 精确字节的 `sha256`；把这项可信采集输出与 manifest 分开保存。archive/member 摘要或临时对改变后的 manifest 重新算的 SHA 都不能替代它。

生成计划需要 `--origin`、UTC `--coverage-from`、`--attest-complete` 和 `--plan`；`--sources` 和 `--expect-sources-sha256` 必须同时出现。`--attest-complete` 是 operator 对所选保存来源从该时刻起连续完整的裁定，最早记录、文件日期、来源标签或摘要不能推导它。计划只读、不写账本；先审阅事实数、覆盖起点和计划 SHA-256。

Apply 只能接收精确计划和已审阅 SHA。它重验封存在计划中的输入、目标和账本前缀，不重新打开 archive/source。目标、环境或账本前缀改变时重新计划；中断只能用原计划重试。历史材料、manifest 与计划应保留在私有受控位置，绝不手改 `work-ledger.jsonl` 或计划文件来绕开拒绝。

## License

```bash
jarvis-box license status
jarvis-box license activate [CODE|--code CODE]
jarvis-box license refresh
jarvis-box license deactivate --yes
jarvis-box license request --out request.json
jarvis-box license import license.json
```

授权地址编译在发布二进制中，不能通过 runtime env 改写。所有命令都可在 Pending、Expired、Revoked、Invalid 状态下执行。

`status` 不联网、不创建状态目录或设备私钥，且无论激活状态都以退出码 0 报告事实。在线激活默认安全读取终端输入；命令行 `CODE` 可能留在 shell history 或进程列表。离线机器用 `request` 生成请求、由服务商签发后 `import`，两个动作都不联网。`deactivate --yes` 写本地停用标记并通知服务端，恢复须重新激活或导入更新签发时间的授权文件。

`refresh` 用于立即检查授权。服务运行时，CLI 通过所选实例的公开接口沿用服务的签到身份；服务停服时，持有同一运行目录锁后独立检查，结束即释放。服务不可达、端口或目录归属不符时明确失败，不另起签到进程；先修正实例配置或恢复服务再重试。在线授权联系正式签到服务，离线授权只检查本地签名。后台也会定期检查；此命令不启动、停止或切换服务，不会绕过许可拒绝。

Docker 通过 deployment script 在实例中交互运行：

```bash
scripts/deploy-production.sh /absolute/deployment-home \
  compose exec jarvis-box jarvis-box license activate
```

已在 container shell 时直接运行；直接 `docker exec` 需要 `-it`。管道输入用 `-i`（或 `docker compose exec -T`）且不显示交互提示。

## 仅当前 Agent Run 可调用的接口

下面的命令不是 operator shell API。服务向当前 active、受管 Run 注入 capability；不能通过手工设置 Task/Run/recipient/credential 参数获得权限。

### Workspace 和外部资源

<a id="task-workspace"></a>

```bash
jarvis-box workspace list
jarvis-box workspace create --id <stable-id> --project <group/repo> [--base-branch <branch>]
jarvis-box workspace create --id <stable-id> --remote <git-url> [--base-branch <branch>]
jarvis-box workspace resource register \
  --kind docker-compose-project --workspace-id <workspace-id> --project <compose-project>
```

`workspace list` 返回当前 Task 的权威 registry，不扫描目录。创建命令先原子登记再创建路径；初始 Task 没有 workspace 时，第一个必须用保留 ID `primary`。`--project` 只用于能由 `GITLAB_HOST` 解析的仓库；GitHub 或其他仓库使用权威 `--remote`。省略两者时才有意创建空 workspace。命令输出的路径才是可用 workspace 路径。

要创建生命周期可能超过 Run 的 Docker Compose project，先成功执行 resource register，才创建外部资源。当前只支持 `docker-compose-project`，并且 project 名会校验为安全标识。登记、清理与失败保留规则见[Task 外部资源生命周期](task-external-resource-lifecycle.md)。

### 群历史、用户问题与受控发布

<a id="im-群历史回查"></a>

```bash
jarvis-box im context search --from RFC3339 --sender <stable-id> --keyword <word>
jarvis-box im context materialize --handle <opaque-handle>
jarvis-box task question --file question.json
jarvis-box task stage-publication --file manifest.json
```

群历史仅限当前已准入的原群/原话题、触发消息之前的资料。查询结果可能是 native 完整历史或 connector 保留的已收消息；空结果和 `scan_limited` 都不能证明没有历史。媒体只有专属 opaque handle 时才能 materialize；不能传 URL、下载 key 或路径。完整筛选、游标、时限和错误处理见[IM 接入](integrations/im.md#按需回查群历史)。

<a id="agent-请求原用户补充信息"></a>

`task question` 每 Run 只可封存一个有界问题 JSON，prompt/help 各最多 2 KiB、最多八个选项，文件最多 32 KiB。`staged` 只说明已保存；只有 Run 正常成功并确认送达后 Task 才等待原请求者答复。

<a id="agent-原生内容发布"></a>

`stage-publication` 同样只封存受原用户绑定授权的 artifact manifest（最多 32 KiB、16 个已有 Run artifact）；它不等于已经写入 Provider。服务在 Run 成功收尾时按精确 artifact SHA、目标 binding、marker 和 ordinal 执行，未知结果不会盲目重发。

### GitHub Actions 订阅

<a id="agent-github-actions-订阅"></a>

```bash
jarvis-box task subscription --file subscription.json
```

此协议只接受当前 Run 已得到的精确 GitHub Actions execution tuple（authority、repository ID、workflow ID、run ID、attempt、run number、head SHA），不接受分支、PR、URL 或 `latest` 推断。请求可登记 1–8 条唯一规则，时长 60 秒到 30 天；`registered` 只表示登记成功，不代表已经通知或继续。用户侧查看/撤销仍由原会话的控制文本处理。

<a id="升级前的历史-run"></a>

## 历史 Run 与 Docker release helper

支持的 0.2 Task/Run 格式会按已登记身份读入当前 aggregate，不要求重建 Task。缺乏完整不可变登记的更旧 Run 只能在 Task 已结束后用显式审批登记为只读历史：

```bash
jarvis-box migrate historical-runs --task task-example \
  --runs r_example1:1,r_example2:2 --approval-id history-review-1 > approval.json
jarvis-box migrate historical-runs --apply approval.json
```

先审阅草稿中 Task 身份、目录与 Run 清单；不要手改草稿。登记后 Run 仅供浏览，不能 Continue、Cancel 或成为 current Run。

<a id="release-helpers"></a>

Docker release helper 的常用入口为：

```bash
scripts/deploy-production.sh <deployment-home> start
scripts/deploy-production.sh <deployment-home> shell
scripts/deploy-production.sh <deployment-home> verify
scripts/deploy-production.sh <deployment-home> deploy
scripts/deploy-production.sh <deployment-home> --force deploy
scripts/deploy-production.sh <deployment-home> runtime-job <inner-command> [args...]
```

`deploy`、`start` 和会停止或重建服务的 `compose` 子命令都执行维护预检。对 `deploy` 和 `start` 使用 `--force` 时，脚本用同一维护收据暂停并自动恢复原运行。直接对 `compose` 使用 `--force` 会明确停止运行，脚本用 `JARVIS_DOCKER_UPGRADE_FORCE_STRATEGY` 记录这项操作和受影响的 Run。`runtime-job` 只是客户 Scheduler Adapter 的 Docker transport，不识别或验证客户内部命令。
