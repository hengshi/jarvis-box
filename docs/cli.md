# CLI reference

## Runtime Agent

```bash
jarvis-box agent doctor
jarvis-box agent smoke
jarvis-box agent current
jarvis-box agent list
```

`doctor` 验证可执行文件/配置；`smoke` 执行真实 Agent 调用。Jarvis 发现由 Jarvis Runtime Foundation 拥有，通过 Agent 自身验证，而非 `jarvis-box jarvis validate` 命令。

`agent list --check` 与 `agent smoke <agent>` 共用 smoke 探测。退出 0 且有回复时，干净成功显示 `smoke-ok` / `smoke ok`；stderr 非空则显示 `smoke-warning` / `smoke warning`，仍退出 0。这只表示 Agent 已回复，不代表 Agent HOME 健康。退出 0 但清洗后没有可见回复也属于失败；`agent smoke` 退出 1，列表显示 `smoke-failed`。

smoke 诊断先移除终端控制字符并遮蔽常见凭据字段、认证头、URL 用户信息和私钥，再取首个非空行，最多输出 512 字节（含截断标记）。成功告警另附操作建议。遇到权限告警时，检查实际运行的 OS 用户以及 Agent HOME 的所有者和权限，由操作者人工修正后重跑 `jarvis-box agent smoke <agent>`；探测不会自动更改文件所有权或权限。

## Runtime tools

```bash
jarvis-box tools path
jarvis-box tools status
jarvis-box tools status --json
jarvis-box tools update
jarvis-box tools reset
```

Native 的 `path` 返回当前用户的工具目录，默认 `$HOME/.local/bin`，可由 `JARVIS_USER_TOOL_BIN` 指定绝对目录。`status` 检查本机工具；`--json` 返回 `jarvis-box-runtime-tools/v1` 清单，包含 `deployment_mode=native`、`update_supported=false`，以及各工具的路径、可用性、生效版本和 `source=host`。缺少可选工具只记录为不可用；已找到的工具版本探测失败、超时或无输出时返回非零退出码，JSON 清单仍可读取。Native 工具通过其原安装器或包管理器更新，`update` 和 `reset` 返回非零退出码及操作指引。

Docker 中 Jarvis 管理的官方工具通过持久化 overlay 原子更新，失败时继续使用镜像内基线。安装或升级会自动尝试一次更新，`update` 可手工重试，`reset` 回到镜像基线。Docker updater 缺失或执行失败时返回非零退出码。

客户自装的独立用户级工具放到 `${JARVIS_USER_TOOL_BIN:-$HOME/.local/bin}`；显式值必须是绝对目录，Jarvis 会把它加入每个 Agent 进程的 `PATH`，同时保留用户默认的 `.local/bin`。Docker 默认目录为 `/home/jarvis/.local/bin`，随 deployment home 持久化，容器重建后仍保留。需要 `apt` 管理的编译器、头文件或系统共享库通过[客户派生 Docker 镜像](custom-docker-image.md)提供。

## Server and Task/Run

```bash
jarvis-box serve
jarvis-box tasks list
jarvis-box tasks list --all --limit 50
jarvis-box tasks json --monitor-status ci-wait
jarvis-box tasks start <source-task-id> --reason "start from an existing Task"
jarvis-box tasks start --prompt "handoff to the managed runtime"
jarvis-box tasks start --prompt "send customer report" --lane custom-user-task --job-id customer-daily-report --reason scheduled-customer-daily-report
jarvis-box tasks continue <task-id> --agent codex --message "continue with these instructions"
jarvis-box tasks continue <task-id>
jarvis-box status
jarvis-box logs
jarvis-box doctor
jarvis-box monitor
```

Compose 配置 state/log/workspace 路径和 Agent 可执行文件，各来源按自身接入配置独立启用。jarvis-box 不将 Jarvis root skill 注入 Run。
`jarvis-box status` 始终输出 effective `runs_dir` 和 `workspace_root`；前者由 `JARVIS_RUN_DIR`（默认 `${JARVIS_STATE_DIR}/runs`）决定，后者由 `JARVIS_WORKSPACE_ROOT`（默认 `${JARVIS_RUNTIME_ROOT}/workspace`）决定。集成方必须读取这两个 effective 值，不得根据默认目录反推 Task 或 Workspace 根。
`status` 的 `tasks` 与 `runs` 分别统计正式登记的 Task 和 Run；`monitor` 的运行数量使用同一读取口径。收据、锁和普通目录不计为运行。`latest` 与 `monitor` 的最新运行按正式 Run 创建时间选择，产物读取精确 Run 目录，不使用 Task 根目录的旧结果。正式投影不可用时显示不可用，不根据目录猜测数量。

`jarvis-box status --smart` 同时输出 `runtime_root` 和 `env_file`。同一台机器运行多个实例时，优先使用 Docker deployment home。Native 维护 shell 可以通过 `JARVIS_ENV_FILE` 或 `JARVIS_RUNTIME_ROOT` 选定 runtime path，再读取 `status --smart` 确认 `runtime_root`、`env_file` 和 `workspace_root`；这不等于选择了 systemd unit。Native lifecycle 命令只适合单实例或已明确验证 service identity 的维护窗口。完整规则见 [多实例部署](multi-instance.md)。

`jarvis-box tasks start --prompt <text>` 是外部交互式 shell 和 Runtime Foundation job 共用的原子 admission。它只能在调用进程没有 `JARVIS_TASK_ID`、`JARVIS_TASK_DIR`、`JARVIS_RUN_ID`、`JARVIS_WORKSPACE_ROOT` 时使用；CLI 从 canonical runtime env 检查 loopback service health，然后用一次 Start 请求交付 prompt。服务端分配 Task identity、登记 intake、创建首 Run 并启动 Agent；调用方不创建 Task、不读取 `task_dir`，也不写 `prompt.txt`。成功 JSON 返回真实 `task_id`、`task_dir`、`run_id`、`run_dir` 和 effective `workspace_root`。

服务仅因磁盘余量不足而降级时，CLI 仍提交原始请求，由服务端保存为机器负责恢复的等待任务。此时返回 `waiting=true`、`wait_reason=storage-wait` 和真实 Task 身份，尚无 Run；空间满足该任务受理时的门槛后自动执行。其他健康故障或不可达仍返回错误。

`tasks list` 和 `tasks json` 默认只显示当前会阻断 lifecycle 操作的 Task，例如 active/running、waiting/storage-wait/duplicate-wait、ci-wait、finalizing 和 recovery-required。默认 `tasks json` 输出 operator 快速定位字段：`task_id`、`lane`、`status`、`monitor_status`、`current_run_id`、已知 `pid` 和 source reference。查看历史或调试时显式使用 `--all`，并可叠加 `--status`、`--monitor-status`、`--lane` 和 `--limit`。

`tasks verify` 逐项检查任务库。成功输出诊断报告时退出码为 0；库内存在坏项时，报告的 `ok=false`，`issues` 列出具体 Task、问题和处理建议，不能只用退出码判断完整性。命令本身无法完成读取或输出时返回非零。检查不会修改坏项；修复前保留其原始内容。

`tasks continue` 遵循服务端返回的 Task 操作策略。继续 Agent 时必须同时提供 `--agent` 和 `--message`；恢复丢失的运行或重试回写时不传这两个参数。恢复会根据已保存的恢复信息创建后续 Run，回写重试只处理原 Run 的失败回写，不重新运行 Agent。CLI 自动携带对应 Run 和当前 Task 版本；状态变化导致请求过期时，服务端会拒绝该请求。

Delivery Metrics 历史起点由 Status 服务管理枚举和节奏，实际分析是普通 `delivery-metrics` lane Task。正在执行或等待中的 Delivery Metrics Task 会出现在默认 `tasks list` 和 `monitor` 中；历史 Task 用 `tasks list --all --lane delivery-metrics` 查看。统计结果仍通过 `/status` 或 `/status/api/value?provider=gitlab|github` 查看。恢复中断分析见 [Delivery Metrics 历史起点](delivery-metrics.md)。

在 `tasks start --prompt` 中，`--lane` 仅用于 prompt Start。默认 lane 是 `jarvis-command`；`delivery-metrics` 是普通 lane，可由 Status 服务或 operator 通过同一 Start 入口创建。`custom-user-task` 是 operator 创建或宿主定时触发的 providerless prompt job lane；lane 表示运行时行为类，`--job-id` 表示用户任务身份，例如 `customer-daily-report`。任意自定义 lane 会被拒绝，`--job-id` 只允许与 `custom-user-task` 一起使用。同一 `job_id` 已有 active/running Task 时，新的 Start 返回可解释的 conflict，不创建第二个 Task。已完成的 `custom-user-task` 不能从 detail 上直接 Start 重跑；补跑必须显式发起新的 prompt Start，避免重复发送日报、周报或客户报告。`custom-user-task` 不注入 provider writeback contract；IM、webhook 或 GitLab 投递证据由 agent task 自己在结果中记录。`memory-consolidation`、`daily-reflection` 和 `cognitive-evolution` 等 scheduled lane 只接受服务端 loopback internal route，不存在调用方 authority flag。

## 升级前的历史 Run

已登记的 0.2 Task 属于支持的升级格式。运行时校验 Task 根的不可变登记、Run ID/sequence、同任务的精确 `run_created` 事件和创建时间后，将其已结束 Run 读入唯一的 canonical aggregate；下一次 TaskService 事务统一发布为 v2。即使此前事务已把 Task 根发布为 v2 而遗留旧 Run 文件，也适用同一校验。原 Task、Run、会话与工作区归属保留，不要求重新建任务。读取不会改写文件。

已发布的嵌套任务目录在迁移后仍保留原位置和 Task ID；格式转换不会要求重命名目录。旧工作区登记缺少登记版本时，由兼容读取和安装迁移补齐，后续清理由同一 Task 生命周期处理。

其他旧版本 Run 缺少完整的不可变登记时，不能直接作为当前 Run 继续执行。
需要浏览这些记录时，先确认 Task 已结束，并核对旧 `run-state.json` 与
`task-events.jsonl` 中的 Run ID、sequence，再显式列出需要保留的 Run：

```bash
jarvis-box migrate historical-runs --task task-example --runs r_example1:1,r_example2:2 --approval-id history-review-1 > approval.json
jarvis-box migrate historical-runs --apply approval.json
jarvis-box tasks json --all
```

第一步只验证并输出草稿，不修改 Task。执行第二步前检查草稿中的完整 Task 身份、
目录和 Run 清单；不要手工修改草稿字段，选择有误时重新生成。两个命令均可通过
`--runs-dir <dir>` 显式选择同一个存储根。草稿包含本地路径，应按本机维护资料保存。

应用通过现有 TaskService 事务登记只读历史，重复应用同一份 approval 不会重复登记。
活动 Task、身份不匹配或不满足历史证据要求的输入会被拒绝。登记后的 Run 可在
Status 中切换浏览，但不能继续、取消或成为当前 Run；安装和服务启动不会自动执行此批准。

## License

```bash
jarvis-box license status
jarvis-box license activate
jarvis-box license refresh
jarvis-box license deactivate --yes
jarvis-box license request --out request.json
jarvis-box license import license.json
```

授权服务地址编译在二进制里，不是配置项（见[配置参考](configuration.md#runtimeenv)）。这些命令在授权 Pending、Expired、Revoked、Invalid 时都能用——它们正是从这些状态里出来的手段，所以没有任何「先有有效授权才继续」的前置检查。

`request` 与 `import` 是不通外网的机器走的两个动作：本机出请求文件交给服务商、把服务商签回来的授权文件导入，两步都不发网络请求。离线授权的有效期由签发时写死（最长一年），到期或换机器同样由服务商重签一份。离线机器不需要配任何授权地址。完整流程见[离线授权](https://github.com/hengshi/jarvis-box/blob/main/CUSTOMER-OPERATIONS.md#9-离线授权不通外网的机器)。

`status` 不联网，只读本机状态，并且不创建状态目录、设备私钥或锁文件：以另一个用户（典型是 `sudo`）运行不会把状态目录里的文件改成那个用户的，服务用户随后拿到的是正常的「未激活」而不是 `EACCES`。未激活时如实报告「激活 否（本机还没有验签通过的决定）」并以退出码 `0` 结束——退出码不跟随授权状态，`status` 的职责是报告事实，不是替脚本下判断。

在线激活时，直接执行 `jarvis-box license activate`。命令显示 `激活码: ` 后，输入或粘贴激活码，按回车提交。输入不回显，按 Ctrl+C 取消；结束或取消后恢复终端。激活成功后显示本机授权状态。

Docker 使用相同的交互。通过 release bundle 的部署入口执行，会使用该实例的正式部署文件和环境：

```bash
scripts/deploy-production.sh /srv/jarvis-box compose exec jarvis-box jarvis-box license activate
```

已进入容器 shell 时，直接执行 `jarvis-box license activate` 即可。直接从 Host 执行 `docker exec` 时，必须带 `-it`，将 `CONTAINER` 替换为实际容器名：

```bash
docker exec -it CONTAINER jarvis-box license activate
```

自动化可用管道或文件重定向传入激活码，此时直接读标准输入，不显示交互提示：

```bash
printf '%s' "$CODE" | jarvis-box license activate
```

也可使用 `activate CODE` 或 `activate --code CODE`，两种写法不能同时使用。显式参数优先于标准输入；命令行参数可能留在 shell 历史或进程列表里。所有输入方式使用同一套激活码校验，命令输出不回显激活码。从管道传激活码或导入授权文件时，`docker exec` 带 `-i`，`docker compose exec` 带 `-T`；交互输入使用带 TTY 的命令。

macOS Native 安装后，直接运行授权命令会使用 `${JARVIS_RUNTIME_ROOT}/state/license`，默认是 `~/.jarvis-box/state/license`。服务、授权命令与诊断使用相同的状态目录解析规则，显式的 `JARVIS_STATE_DIR` 或 `JARVIS_LICENSE_STATE_DIR` 仍可覆盖默认值。

`refresh` 立即发起一次签到，换取新的签名决定。后台签到循环是常驻的，所以这是排障手段而不是日常操作：签到失败由 stderr 和状态页报告，不需要手工触发。

`deactivate` 在本地落停用标记并通知服务端，`--yes` 跳过一次性确认。旧授权文件不能撤销停用；恢复需要重新激活，或导入服务商重新签发的文件，文件签名中的签发时间必须晚于本机已经接受过的所有决定。通知服务端失败时，命令会重新读取本机状态再给结论：本地标记已落盘就是已经停用，未落盘才可以重试。

授权状态在 `jarvis-box license status` 和状态页的授权面板里是同一张字段表，`jarvis-box status` 另外输出一段 `key=value` 摘要供脚本读取。三处都不发网络请求。

## Task workspace

```bash
jarvis-box workspace create --id <stable-id> --project <group/repo> --base-branch <branch>
jarvis-box workspace create --id <stable-id> --remote <git-url> --base-branch <branch>
```

在 active Run 内可用只读入口查看权威 registry：

```bash
jarvis-box workspace list
```

该命令输出一个 JSON object，包含当前 `task_id`、`run_id` 和按登记顺序排列的
`task-state.workspaces[]`。它校验当前 Run ownership，不扫描目录，也不从 `cwd`、
`run-context.json` 或文件系统猜测 Workspace。

该创建命令仅在 active 受管 Task 中可用。它在创建 workspace 之前原子地登记服务端分配的路径。zero-workspace Task 的第一个 Workspace 必须使用保留 id `primary`；非空 registry 的后续 Workspace 使用普通 stable id。带 `--project` 的 repository 必须能通过已配置的 `GITLAB_HOST` 解析；GitHub 或其他 provider-neutral 仓库必须显式使用 `--remote`。repository source 会在 registry mutation 前验证，成功后目录必须是真实 Git worktree；无法解析的 `--project` 不会登记或发布空目录。只有同时省略 `--project` 和 `--remote` 才表示有意创建空的非 repository Workspace。

省略 `--base-branch` 且没有 Provider checkout ref 时，jarvis-box 从 remote symbolic `HEAD` 选择默认分支，执行非浅的单分支、no-tags clone。可用 repo-cache 会作为对象来源：Jarvis Box 先刷新 bare mirror，再通过非 local 的单分支 clone 从 cache 创建 Workspace，并把 `origin` 恢复为权威 remote；cache 不可用时才回退权威 remote。该 Workspace 不包含 tag ref、其他分支 ref 或其他分支独有历史。显式 branch/ref 使用声明的 checkout 合同。显式 base branch 在远端不存在时，新建与 Continue 重建均回退 remote 默认分支，并告知 Agent 请求分支、实际分支和原因。固定 review ref/commit 缺失仍拒绝执行。

## Release helpers

```bash
scripts/deploy-production.sh <deployment-home> start
scripts/deploy-production.sh <deployment-home> shell
scripts/deploy-production.sh <deployment-home> verify
scripts/deploy-production.sh <deployment-home> deploy
scripts/deploy-production.sh <deployment-home> --force deploy
scripts/deploy-production.sh <deployment-home> runtime-job <inner-command> [args...]
```

`deploy`、`start` 和会停止/重建服务的 `compose` 子命令会在 Docker service mutation 前执行 active-task preflight。存在未完成或需要恢复的 Task 时，命令会先退出；`--force` 只用于客户已确认放弃当前 Run 的场景，并要求设置 `JARVIS_DOCKER_UPGRADE_FORCE_STRATEGY`，脚本会先在 deployment home 下记录受影响 Run 和策略。

`runtime-job` 是 Jarvis 自有 Scheduler Adapter 的通用 Docker transport。它不识别、安装或验证内部命令。

Native 的 `start/stop/restart` 是正式服务运维入口，`setup gitlab` 是 GitLab 专有接入配置入口；迁移命令按各自公开的安装或审批合同执行。
