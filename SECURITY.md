# 安全策略

## 受支持的版本

当前公开 `0.2.x` 线接收安全与安装程序更新。建议使用 [GitHub Releases](https://github.com/hengshi/jarvis-box/releases/latest) 中的最新稳定版本；更早的公开版本除非对应 Release 明确说明，否则不再接收常规修复。

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
