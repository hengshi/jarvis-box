# Jarvis Box 运维入口

本文面向维护自己 Jarvis Box deployment 的客户 operator。先按目标选择操作；不要直接修改 Task state、ledger、迁移记录或 deployment data。架构和配置字典分别见[架构](architecture.md)和[配置参考](configuration.md)。

<a id="先定义-docker-命令"></a>
<a id="docker-deployment-边界"></a>

## 先选择目标实例

Native 在服务用户的维护 shell 中运行。Docker 在当前 shell 定义目标 release 和 deployment home：

```bash
ops=/absolute/release/scripts/deploy-production.sh
home=/absolute/deployment-home
```

后续 Docker 命令使用同一个 `"$ops" "$home"`。它只管理该 home 与已登记 Compose project，不会重启 Docker daemon、修改宿主网络/DNS、运行 Docker 全局 prune，或触碰其他 deployment。Docker、registry、DNS 或网络故障由宿主管理员在 Jarvis Box 之外恢复。

多实例 Host 优先 Docker。Native 中的 `JARVIS_ENV_FILE`/`JARVIS_RUNTIME_ROOT` 只选择 runtime paths；先运行 `jarvis-box status --smart`，再单独证明 systemd unit 或 launchd label。完整规则见[多实例部署](multi-instance.md)。

<a id="看状态"></a>

## 日常检查

### Native

```bash
jarvis-box status
jarvis-box doctor
jarvis-box agent smoke
jarvis-box logs
jarvis-box monitor
```

Status 默认本机地址为 `http://127.0.0.1:8787/status`。跨兼容线手工升级只可使用目标 release 的已校验 archive、`SHA256SUMS` 和安装器；不要从旧 runtime 的 `state/app` 运行安装器。

### Docker

```bash
"$ops" "$home" compose ps
"$ops" "$home" verify
"$ops" "$home" compose logs --tail=200 jarvis-box
"$ops" "$home" shell
```

Docker 默认发布到 Host 的所有接口，可从受信网络访问 `http://<docker-host>:8787/status`；`JARVIS_BIND_ADDRESS=127.0.0.1` 时只能在 Host 访问。使用受管 `uvim` profile 时另看 connector 日志：

```bash
"$ops" "$home" compose logs --tail=200 uv-im-connector
```

`uvim-external` 没有本地 connector 或它的日志。检查 Box 的 `verify` 结果，必要时请共享 hub 管理员提供本调用方的审计；不要从 Box deployment home 启停共享 hub。

`/status` 是诊断和操作界面，不是客户 Jarvis 的知识源。完成一个配置保存或系统设置操作后，以页面重新读取的结果、Task/Run ID 和日志为准；保存成功不等于真实 Provider 事件已经交付。

<a id="看日志"></a>
<a id="进入运行环境"></a>

## 日志与运行环境

Native 用 `jarvis-box logs` 和 `jarvis-box monitor` 查看服务信息；Docker 用 `"$ops" "$home" compose logs --tail=200 jarvis-box`，受管 `uvim` 的日志按前节单独查看。Native 直接使用服务用户的 shell；Docker 用 `"$ops" "$home" shell` 进入该实例。不要通过挂载 Host HOME、SSH agent 或 Keychain 修复认证。

<a id="使用-status-系统设置"></a>

## 使用 Status 系统设置

从 `/status` 顶部打开“系统设置”：

- **系统概览**：查看当前可用性、版本、路径、资源与脱敏配置。
- **处理问题**：先读取 doctor 失败项；消息连接可以重新连接。多步诊断/处理会创建可跟踪 Task/Run。
- **工作方式**：改默认 Agent 或某类工作的 Agent 覆盖。只影响后续 Run，不切换正在运行的 Agent。
- **接入配置**：按来源保存身份、scope 与 webhook 配置；根据页面提示重启服务使它生效。
- **数据维护**：先执行预检。确认清理不可恢复，但只删除超过保留期、已终态且 workspace disposal 完成的 Task artifact；不清 active Task、运行中 Agent、service log 或依赖缓存。

失败时保留页面错误与服务日志，按本文“故障恢复顺序”处理。

## 在线授权签到的使用统计

服务自动执行在线授权签到时，读取 Status 最近一次发布的历史指标快照。服务运行时，`jarvis-box license refresh` 会请服务立即签到。快照可用时，签到附带以下汇总。

| 上报字段 | 含义 |
| --- | --- |
| `historical_accepted_count` | 工作账本累计接入受理次数，不等于任务数 |
| `started_run_count` | 工作账本累计启动 Run 次数，包含同一任务的多次运行 |
| `completed_runtime_duration_ms` | 已完成运行的已知耗时合计，单位为毫秒 |
| `completed_duration_sample_count` | 有有效耗时的已完成运行记录数 |
| `completed_duration_missing_count` | 缺少有效耗时的已完成运行记录数 |
| `completed_runtime_status` | 耗时统计完整、有部分缺失、暂无记录或不可用 |

这些数值沿用 Status 的工作账本口径，任务清理不会减去已记录的运行次数。账本重置或更换后累计值可能降低。多次签到的累计值不能相加。可读的空账本上报实测 `0`，未知值为 `null`。部分耗时缺失时，合计表示已知下限。

没有可用快照时，签到省略汇总并照常续租。服务尚未发布快照、已发布的账本状态不可用，或停服后独立执行 `license refresh` 时，都适用这一规则。

上报内容只包含固定数值字段、统计状态及格式版本，不含提示词、回复、任务或运行标识、人员名单、项目名称、文件内容、路径或逐条账本记录。激活、停用、只读查看和离线授权不读取或发送这组统计。统计不影响授权判断或新运行准入。

授权服务只保存通过授权检查的实例用量。样本按签到历史保留期限清理，最近一次有效汇总随授权实例保留。接收时间表示服务端收到这份汇总的时间，同一份累计值可被多次接收。缺失或无效的汇总保留上次有效值及其接收时间。

<a id="查看或恢复-delivery-metrics-历史起点"></a>

## Task、Webhook 和 Delivery Metrics

先通过 `jarvis-box tasks list` 看默认的阻断 Task；历史排查使用 `jarvis-box tasks list --all`。详情、Continue、Cancel、webhook receipt 的恢复以及状态含义见[CLI 参考](cli.md)。不要删除 webhook/Task 文件来制造“未受理”状态。

Delivery Metrics 在服务启动、MR/PR 关闭/合并和定时补查时自动同步；打开页面或刷新 API 都不会启动分析。读取当前统计：

```bash
curl -fsS 'http://127.0.0.1:8787/status/api/value?provider=gitlab' |
  jq '{warnings, analysis_progress, totals: (.snapshot.totals // null)}'
```

GitHub 把 `provider` 改为 `github`。分析历史起点、lane 启停、Task Continue/Stop 和 Agent scope 见[Delivery Metrics 历史起点](delivery-metrics.md)。

<a id="受控补录-run-启动历史"></a>

## 受控补录 Run 启动历史

这是一项受授权的账本维护，不创建、Continue、Cancel 或恢复 Task/Run。先在私有工作目录收集已保留来源：

```bash
python3 scripts/collect-run-start-history.py --origin LABEL \
  [--ledger FILE] [--archive FILE SHA256] --output FILE
```

该路径相对解压的 release 根目录；Native 安装后为 `${JARVIS_STATE_DIR}/app/scripts/collect-run-start-history.py`。collector 会验证选定 archive 的压缩字节，再输出 manifest 的精确 `sha256`。将这个可信采集输出与 manifest 分开保存；manifest 自报内容不能替代它。

只有当 operator 能证明所选来源从某个 UTC 时刻起连续完整时，才在目标实例的 canonical runtime environment 内计划：

```bash
jarvis-box metrics backfill --origin LABEL --sources FILE \
  --expect-sources-sha256 SHA --coverage-from RFC3339 \
  --attest-complete --plan FILE
jarvis-box metrics backfill --apply FILE --expect-sha256 SHA
```

`--coverage-from` 和 `--attest-complete` 是 operator 的业务裁定；最早记录、文件日期、来源标签或 SHA 都不能推导它。计划不写账本；先审阅事实数、起点和 plan SHA。Apply 仅接受精确计划及审阅过的 SHA，并重验计划内事实、目标与账本前缀；不重新打开 archive/source。错误 SHA、改变目标或改变前缀都必须重新计划，不手改 manifest、plan 或 `work-ledger.jsonl`。

Docker 先在受控 Host/workstation 收集，再通过现有 deployment 的私有持久化位置提供材料；不要额外挂载 Host HOME、临时 bind mount 或 volume。然后用既有 transport：

```bash
"$ops" "$home" runtime-job jarvis-box metrics backfill --origin LABEL \
  --sources FILE --expect-sources-sha256 SHA --coverage-from RFC3339 \
  --attest-complete --plan FILE
"$ops" "$home" runtime-job jarvis-box metrics backfill --apply FILE --expect-sha256 SHA
```

先在独立候选实例与其账本副本演练；候选 plan 绝不能应用到正式实例。正式实例发布后重新计划、重新审阅并使用自己的 plan SHA。保留来源、可信采集输出、plan、裁定和应用输出作为私有运维证据。

## 停止或重启 Native 服务

```bash
jarvis-box stop
jarvis-box restart
```

维护预检按 TaskService 的生命周期判定阻断项。用 `jarvis-box tasks list` 查看当前阻断项，用 `jarvis-box tasks list --all` 查看历史。普通重启在预检通过后仍保留新 Run 的准入门，直到服务变更完成。已有 Run 等待磁盘时仍阻断维护。当前格式的 Run 失联后进入自动恢复，旧格式的 Run 仍可能显示 `recovery-required`。

`jarvis-box restart --force` 与 Native `update --force` 共用任务中断和恢复流程：先关闭新 Run 准入，在同一个两分钟窗口内等待已受理的任务完成准备、正在收尾的 Run 结算，以及暂时无法安全暂停的评审结束或原会话就绪。超时或请求取消时，服务和未中断的任务继续运行，准入重新开放。准备结束后，持久记录本轮中断清单；排队等待暂停的任务可以正常更新进度，维护仍须核验并只中断清单中的原运行。清单中的原运行已完整结束时，保留其结果，不再停止或重跑；全部活动运行停止、重新核验没有阻断工作后才停服。重启后按收据自动继续本轮实际中断的原任务。维护恢复尚待结算时，命令等待结果。若超过响应窗口，服务继续按同一收据恢复。维护命令在停服前退出时，原服务会在发起方及其正在执行的系统变更子进程退出后接管。安装或重启失败时，命令也尝试恢复已中断任务，并保留实际失败结果。仍未产生 Run 的等待任务和无法可靠中断的工作会阻断这两种维护操作，不自动取消。

并行代码评审的各进程使用独立会话。活动并行评审和原会话尚无法在本地验证的单会话评审，在预检期间继续运行。会话只能由 Agent CLI 解析时也等待该评审结束。等待窗口结束时仍无法安全暂停，命令会在停服前退出。可暂停的单会话评审沿用原会话、工作区和已保存的评审输入，恢复准备无需联网刷新讨论。后继 Run 的同 Agent 自动恢复也沿用原会话。当前并行评审配置在下一轮新评审时生效。

安装前的预检由当前服务执行。从缺少此检查的旧版本升级时，先等活动的并行评审结束。维护前保留运行中任务使用的 Agent 会话配置和目录，重启后的服务需要用这些设置访问原会话。

`jarvis-box stop --force` 保留停止语义：按 Task/Run 所有权停止活动 Run，并取消尚未产生 Run 的准入；停止后的工作需要显式继续。安装器本身没有 force 模式。

这些 Native lifecycle 命令适用于单 Native 实例。Native 多实例主机不能只靠 `JARVIS_ENV_FILE` 或 `JARVIS_RUNTIME_ROOT` 选择 systemd unit；Linux 内置路径操作安装时的 `jarvis-box` unit。长期同机多实例应使用 Docker deployment home。

## 升级

<a id="自动检查与下载"></a>

### 自动检查和确认安装

Native 与 Docker 的正式安装会设置独立宿主更新执行器。`JARVIS_AUTO_UPDATE_ENABLED=true`（默认）在首次成功在线授权签到后检查稳定 release，通常约每六小时一次并带抖动、退避。下载不会重启服务；Status 显示“更新已就绪”后由用户确认“更新并重启”。离线授权、未激活、签到失败或网络不可达时不下载，已有 Task 不受影响。

真正安装时才中断可安全暂停的 Task；安装、迁移和健康检查成功后按维护清单接续。无法安全暂停的 storage wait 或身份未核实工作会阻止更新。关闭开关只停止预取，不中断在运行 Task 或已确认的安装。

更新失败时查看 Status 显示的宿主日志、`doctor` 和维护恢复状态；不要删除 Task 或修改授权记录。恢复备份、卸载或手工维修前先停止本实例的宿主更新执行器，按实际部署路径调用 `install-update-agent.py stop --config ...`；维修后使用 `activate` 或重新运行正式安装器。正在安装时会拒绝停止。

<a id="手工更新"></a>

### Native 手工升级

先确认默认 `tasks list` 没有 blocking Task。`jarvis-box update --check` 显示可用源；`jarvis-box update` 会下载并校验目标 archive，然后只执行目标 archive 中的安装器。默认不会取消 Task；`update --force` 持久记录中断清单并在失败时恢复它们。

从 0.x 到 1.0 需要 `JARVIS_ALLOW_MAJOR_UPGRADE=1`。0.3.x 可在没有 active Task 时使用目标版本；0.2.x 不能运行旧 CLI 的无参或跨线 update，应校验目标 bundle 后直接运行目标 `install.sh`：

```bash
jarvis-box tasks list
jarvis-box stop
version=1.0.0
artifact=/absolute/path/to/downloaded-target-archive.tar.gz
checksums=/absolute/path/to/SHA256SUMS
target_installer=/absolute/path/to/extracted-target-bundle/install.sh
sudo env JARVIS_ALLOW_MAJOR_UPGRADE=1 \
  JARVIS_VERSION="$version" \
  JARVIS_ARTIFACT_FILE="$artifact" \
  JARVIS_SHA256SUMS_FILE="$checksums" \
  bash "$target_installer"
jarvis-box doctor
jarvis-box agent smoke
```

macOS 去掉 `sudo`，由现有安装用户运行；Linux 使用 `sudo`。安装器发现服务仍在运行时会停下并提示规范停服，它不会自动 Cancel Task。

<a id="使用宿主机自助升级入口"></a>

### Docker 升级与回滚

若 deployment home 有 release 安装的 `update.sh`，优先使用：

```bash
bash /absolute/deployment-home/update.sh [--version X.Y.Z]
```

`--force` 授权 updater 暂停可续接的任务，并在升级后按维护收据自动恢复。`--prepare <private-dir> --version X.Y.Z` 只预取/校验；`--apply-prepared <private-dir> --version X.Y.Z --force` 从该缓存应用。只有 `channels/v1/latest.json` 含 `docker_update` 才表示 latest 发布了这个入口；否则使用目标 bundle 的手工流程。

手工流程先获取、校验同版本 bundle、SHA256SUMS 与 `production-image.json`（私有 GitHub Release 不可用时使用对应公开 mirror），将目标 image 写入当前 `$home/deployment.env` 的 `JARVIS_IMAGE`，然后运行：

```bash
"$ops" "$home" deploy
"$ops" "$home" verify
```

`deploy` 和 `start` 在停服或重建前执行同一个 TaskService 维护预检。使用 `--force deploy` 或 `--force start` 时，脚本从正在运行的容器取得维护收据，在目标服务健康后按同一收据自动续接。暂停只完成了一部分时，脚本在原容器恢复已中断的 Run。强制部署先停止并保留原容器，迁移成功后再重建。失败时自动尝试启动原服务或已迁移的目标服务，并按同一收据恢复。使用支持维护锁的源服务时，Docker 调用方退出后原服务也会接管收据。从较旧版本升级时仍走原收据协议，由启动后的服务接管。服务仍无法启动时，收据保留在部署目录。Compose 直通命令的强制停止规则见[命令参考](cli.md)。

回滚需要匹配旧 release 的完整 deployment-home 备份（含 `auth/`、`data/connector-state/`、`data/runtime-hostname` 与其他 data），不只是旧 image digest。目标部署开始后按 updater 的备份/人工恢复指引处理。

<a id="更新认证"></a>

## 更新认证

Native 在服务用户下更新 `gh`、`glab`、Codex 或 Claude 登录，然后重跑受影响 `doctor`/`smoke`。Docker：

```bash
"$ops" "$home" auth-import
"$ops" "$home" verify
```

自动导入只复制获批准的可移植身份；IM secret 仍只在 `connector.env` 与 connector 边界。

<a id="备份"></a>

## 备份

正常升级使用 release updater 自己的恢复方式，不额外复制 runtime、workspace、cache 或 HOME。额外备份需要明确范围、预计大小、目标磁盘、停服时间与授权。Native 按生效配置选择 state/workspace/log 和明确需要的 Agent identity/config；不要复制整个 Host HOME。Docker 备份完整 deployment home，包括 `data/agent-home`、`workspaces`、`state`、`logs`、`config`、可选 `connector-state` 和 `runtime-hostname`。备份 helper 同样会 active-task preflight；不要绕过它直接停容器。

<a id="出问题时按这个顺序"></a>

## 故障恢复顺序

1. 用 Status 确认问题是 Provider、Task/Run、Agent、connector 还是 Delivery Metrics。
2. Native 运行 `jarvis-box doctor` 与 `jarvis-box agent smoke`；Docker 运行 `"$ops" "$home" verify`。
3. 查相应日志。Webhook 用 `jarvis-box webhooks show <receipt-id>`；需要离线分析时可重定向脱敏诊断，不先改 state。
4. 核对 Provider allowlist、认证 capability 和 exact Run delivery-effect receipt。
5. 仍不能恢复时，保留 Task state、event 与日志证据，再按错误原因处理或联系客户自己的宿主/Provider 管理员。
