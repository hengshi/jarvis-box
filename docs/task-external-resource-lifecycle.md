# Task 外部资源生命周期

本文面向编写 Runtime Foundation、workflow 或 Agent 集成的人。若一个 Task 创建的资源可能在 Agent 进程退出后继续存在，必须先把它登记为 Task-owned typed resource；Jarvis Box 只清理已登记的资源，绝不从目录、仓库名、marker 或命令习惯猜测所有权。

日常 operator 不需要手改 registry 或清理状态。Workspace 保留、Task 终态和手工/定时清理的总规则见[存储模型](storage-model.md)。

<a id="目的"></a>
<a id="权限"></a>

## 唯一的清理权限

| 事实 | 权威来源 |
| --- | --- |
| Task 与 current Run identity | `task-state.json` aggregate |
| Workspace 所有权 | append-only `workspaces[]` |
| 非进程外部资源的清理义务 | typed `external_resources[]` |
| 清理重试与完成事实 | Task state |

`external_resources[]` 保存数据，不保存 shell 命令。当前仅支持 `docker-compose-project`：

```json
{
  "kind": "docker-compose-project",
  "id": "docker-compose-project:project_ab12cd",
  "workspace_id": "primary",
  "project": "project_ab12cd",
  "registered_by_run_id": "run-...",
  "registered_at": "2026-07-30T10:00:00Z"
}
```

`project` 必须是小写安全标识，`id` 必须精确等于 `docker-compose-project:<project>`，workspace 必须已登记，`registered_by_run_id` 必须是同一 Task 的真实 Run。任何不支持 kind、冲突 identity、不安全 project、未知 workspace 或失效 Run 都会被拒绝。当前 schema 不使用 registry version；若将来不兼容变更，写侧 version 与读侧 fail-closed 检查必须一起发布，不能静默误读旧条目。

<a id="登记边界"></a>

## 在创建资源前登记

仅 active、受管 Run 可执行：

```bash
jarvis-box workspace resource register \
  --kind docker-compose-project \
  --workspace-id primary \
  --project project_ab12cd
```

命令验证当前 Task/Run ownership、已登记 workspace、kind/project 格式与 registry 幂等性。成功返回才表示清理义务已持久化；在此之前不得创建 Compose project。Run 失去 ownership、Task 已终态或输入不合法时命令 fail closed，且不得创建资源。

Jarvis Box 不会从 `.dev-data`、Compose file、repository/workspace 名、活动容器或 Docker working-directory label 推断登记。客户 Runtime Foundation 也不应绕过这个 registry 直接写清理状态。

<a id="清理决策表"></a>
<a id="顺序与恢复"></a>

## 清理顺序与可观察结果

清理前 Jarvis Box 依次证明：没有 current Run owner、没有仍存活的已登记进程身份、没有 terminalization intent；随后取得 Task 与 Workspace cleanup lease。对每个显式 resource，先处理外部资源，再处置其 workspace，最后保存证据并移除已解决条目。

| 情况 | Docker 动作 | Workspace 结果 |
| --- | --- | --- |
| 没有已登记资源 | 不调用 Docker | 通过常规 idle 检查后可处置已登记 workspace |
| 已登记 Compose project | 只按精确 `com.docker.compose.project=<project>` label 查询/移除 containers 与 networks | 只在精确缺失已验证后处置 |
| Docker 不可用 | 不删除 registry | 保留义务与 workspace，并持久化退避重试 |
| registry 无效 | 不调用 Docker | fail closed 并暴露修复证据 |

清理不会从未过滤的宿主全局 Docker scan 开始，也不会按工作目录、同名进程或单一 PID 扩大范围。失败是需要保留的义务，不改写 Provider 结果，也不进入热 terminalization 循环；手工与定时清理使用同一所有权证明和 finalizer。

<a id="不变量"></a>

## 完成与不变量

`workspace_disposal_completed=true` 只在每个已登记 workspace 和 external resource 都处置完成后写入。`tasks clean` 只消费这个完成凭证来退役 Task artifact；它不重新扫描或重新解释资源。

必须始终保持：

1. 客户名称、marker 文件与目录形状不创建资源所有权。
2. 空 registry 不触发 Docker 调用。
3. 已登记 project 仅按其精确、类型化 identity 清理。
4. Docker 故障同时保留 resource record 与关联 workspace。
5. Runtime Foundation 清理和宿主 scheduler 不读取或清理 Jarvis Box Task/Workspace/external-resource 状态。
6. Jarvis Box 不要求客户工具代为清理 Task-owned resource。
