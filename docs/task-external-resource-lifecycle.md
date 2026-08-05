# Task 外部资源生命周期

## 目的

Task 可以创建超出其 agent 进程寿命的资源。jarvis-box 必须处置其拥有的资源，而不能从客户仓库名、文件、目录或命令约定猜测。

## 权限

| 关注点 | 权限来源 |
| --- | --- |
| Task 和当前 Run identity | `task-state.json` |
| Workspace 所有权 | append-only `workspaces[]` |
| 外部清理义务 | typed `external_resources[]` |
| 清理重试状态 | Task state |

`external_resources[]` 是非进程外部资源的唯一权限来源。它包含数据，绝不是 shell 命令。初始支持的 kind 为 `docker-compose-project`：

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

`external_resource_registry_version = 1` 标识 schema。Task 初始时 registry 有意为空。

## 登记边界

active Run 在依赖资源之前通过 jarvis-box 类型化资源面登记资源。登记时验证：

```bash
jarvis-box workspace resource register \
  --kind docker-compose-project \
  --workspace-id primary \
  --project project_ab12cd
```

- 当前 Task 和 Run identity；
- 引用的已登记 Workspace；
- 支持的 resource kind 和安全的 project 标识；
- 结果 registry 条目的幂等性。

命令只允许当前拥有 Task 的 Run 调用。调用成功表示清理义务已经持久化；外部资源只能在成功返回后创建。Run 已失去 ownership、Task 已终态、Workspace 未登记或 registry schema 不受支持时，命令 fail closed，且不得创建资源。

jarvis-box 不从 `.dev-data`、Compose file、仓库名、workspace 名、运行中容器或 Docker working-directory 标签推断登记。客户 Runtime Foundation 任务不读取或写入此 registry。

## 清理决策表

| Task 状态 | Docker 动作 | Workspace 结果 |
| --- | --- | --- |
| 无已登记外部资源 | 无 | 通过常规 idle 检查后处置已登记 Workspace |
| 已登记 Compose project | 仅查询/移除具有该精确 project 标签的资源 | 仅在验证精确缺失后处置 |
| 已登记资源但 Docker 不可用 | 无 | 保留义务和 Workspace；退避重试 |
| 无效 registry | 无 | fail closed 并暴露修复证据 |

清理绝不从无过滤的宿主全局 Docker 扫描开始。

## 顺序与恢复

1. 解析受管 Run 进程组和同 Run 后代进程。
2. 证明没有当前 Run owner、存活的已登记进程身份或 terminalization intent。
3. 取得 Task 和 Workspace cleanup lease。
4. 逐一完成每个显式登记的外部资源。
5. 处置已登记 Workspace。
6. 移除已解决的资源条目并持久化清理证据。

Workspace 或资源失败是保留的义务，附带持久化指数退避。它不改写 provider 结果，也不进入热 terminalization 循环。手工和定时清理使用相同的所有权证明和 finalizer。

`workspace_disposal_completed=true` 仅在每一个已登记 Workspace 和外部资源都被处置后写入。`tasks clean` 消费该凭证来退役 Task artifact；它不重新发现资源或重新解释清理状态。

## 不变量

1. 客户名称、marker 文件和目录形状永不创建所有权。
2. 空类型化 registry 不触发任何 Docker 调用。
3. 已登记 project 仅通过精确类型化 identity 被完成。
4. Docker 故障同时保留资源记录和其 Workspace。
5. Runtime Foundation 清理和宿主 scheduler 绝不检查 jarvis-box Task、Workspace 或外部资源状态。
6. jarvis-box 绝不要求客户工具清理 Task 拥有的资源。
