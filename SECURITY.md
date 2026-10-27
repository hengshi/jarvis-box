# 安全策略

## 受支持的版本

| 版本线 | 维护范围 | 部署用途 |
| --- | --- | --- |
| 1.0.x | 功能演进、bug 与安全修复 | 新客户和新部署的默认稳定版本 |
| 0.3.x | 仅 bug 与安全修复，不增加新功能 | 已有部署的维护版本，须显式选择版本 |
| 0.2.x | 仅 bug 与安全修复，不增加新功能 | 已有部署的维护版本，须显式选择版本 |

新部署使用私有 `hengshi-jarvis/jarvis-box` GitHub Release 或公开 S3 fallback mirror 中的最新 1.0 稳定版。维护线发布不会替换新部署的默认版本。更早版本除非对应 Release 明确说明，否则不再接收常规修复。

维护范围不改变已发布数据的升级合同。升级已有部署时，保留原 Task、Run、会话、授权和已完成结果，并按[升级步骤](CUSTOMER-OPERATIONS.md#native-1)执行；跨版本升级仍需要显式授权，不能通过替换数据目录重新建空实例。

## 报告漏洞

请私下报告安全问题。不要在公开 GitHub issue 中包含漏洞细节、secrets、客户数据或私有环境信息。

请发送报告至：

- hi@hengshi.com

请包含：

- 受影响的 jarvis-box 版本
- 安装面：Ubuntu systemd、macOS launchd、容器、Kubernetes 或 Helm
- 复现步骤
- 观察到的影响
- 已移除 token、私有 URL、本地路径和 agent-native session 标识后的所有日志

## 敏感数据

请勿公开：

- GitLab access token、webhook secret、IM app secret 或 runtime agent credential
- 未经脱敏的原始 `task-state.json`、`task-events.jsonl`、`run-context.json` 或 provider payload
- runtime-native session 文件或私有 resume handle
- 客户源材料或专有仓库 URL
