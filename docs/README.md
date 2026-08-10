# Jarvis Box 文档

本目录随 Jarvis Box 公开发行同步，面向安装、使用和维护自己 Jarvis Box deployment 的客户。内容只描述客户可观察的产品行为和客户拥有的操作。

## 从这里开始

- [开始使用](guide/getting-started.md)：新客户、Native 和 Docker 的最短路径
- [运维入口](operations.md)：状态、日志、停服、升级、认证和备份
- [产品概览](product-overview.md)：jarvis-box 在 Jarvis 生态中的职责
- [三仓职责与发布关系](../REPOSITORY-MODEL.md)：create-jarvis、公开发行仓库和内网源码仓库的边界
- [认证](../AUTHENTICATION.md)：Native、Docker Host 导入和 Docker 内直接登录

第一次使用不需要阅读完整文档。客户还没有自己的 Jarvis 时，直接让 Host Agent 读取 [create-jarvis](https://github.com/hengshi/create-jarvis)。

## 接入 provider

- [GitHub](integrations/github.md)
- [GitLab](integrations/gitlab.md)
- [IM 与 uv-im-connector](integrations/im.md)
- [Jira](integrations/jira.md)
- [飞书项目](integrations/feishu-project.md)
- [网络入口](network-ingress.md)

## 按需查询

- [Docker 部署合同](deployment.md)
- [配置参考](configuration.md)
- [CLI 参考](cli.md)
- [Runtime Agent](runtime-agents.md)
- [Task/Run 执行模型](execution-model.md)
- [持久化与恢复](storage-model.md)
- [外部资源与清理](task-external-resource-lifecycle.md)
- [状态 API](status-api.md) 与 [状态页面](status-ui.md)
- [架构](architecture.md)

Native 和 Docker 是并列部署模式。Native 使用安装者当前 OS 用户；Docker 使用独立持久 runtime，既可导入当前 Host 用户的可移植认证，也可直接在容器的持久 Agent HOME 中登录。两种模式都不得创建未经客户决定的新 OS 用户，也不得复制整个 Host HOME。
