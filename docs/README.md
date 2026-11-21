# Jarvis Box 文档

这套文档面向负责安装、接入和日常使用一套 Jarvis Box 的客户。它只说明客户可观察的产品行为和客户需要完成的操作；公司内部的发布、CI 和运维流程不在这里。

## 新客户从这里开始

1. [下载与安装指引](https://download.hengshi.com/jarvis-box/index.html)：获取发布包、校验文件和 Docker 镜像包，不需要访问 GitHub。
2. [开始使用](guide/getting-started.md)：选择 Native 或 Docker，完成首次上线和一条真实任务验证。
3. [常见场景](guide/scenarios.md)：按“刚收到工作项”“需要继续任务”“排查为什么没有回复”等目标选择下一步。
4. [产品概览](product-overview.md)：确认 Jarvis Box 在现有 Jarvis 体系中的职责和边界。
5. [运维入口](operations.md)：查看状态、日志、停服、升级、认证和备份。

尚未拥有 Jarvis 时，可让已经登录且获授权的 Host Agent 按 [create-jarvis](https://github.com/hengshi-jarvis/create-jarvis) 建设客户自己的 Jarvis。Jarvis Box 不会自动克隆、注入或维护这份客户仓库。

## 按要完成的事阅读

| 目标 | 文档 |
| --- | --- |
| 安装后开始接收任务 | [开始使用](guide/getting-started.md) |
| 让 Agent 用自然语言协助配置或诊断 | [Agent skills](agent-skills.md) |
| 选择 Native 或 Docker 的运行方式 | [Docker 部署合同](deployment.md)、[多实例部署](multi-instance.md) |
| 按终端使用量选择 Mac mini | [终端性能与硬件选型](terminal-performance.md) |
| 配置运行时变量或命令行 | [配置参考](configuration.md)、[CLI 参考](cli.md) |
| 查看任务、恢复、外部资源和状态 | [Task/Run 执行模型](execution-model.md)、[持久化与恢复](storage-model.md)、[外部资源与清理](task-external-resource-lifecycle.md)、[状态页面](status-ui.md) |
| 部署多个实例 | [多实例部署](multi-instance.md) |

Native 和 Docker 是并列的部署模式。Native 使用安装者当前 OS 用户；Docker 使用独立、持久的运行时环境，可以窄化导入当前 Host 用户的认证，也可以在容器中直接登录。两种模式都不会创建未经客户决定的新 OS 用户，也不会复制整个 Host HOME。

## 接入工作系统与消息渠道

先阅读 [网络入口](network-ingress.md)，确认公开地址、反向代理和来源认证边界，再按实际来源选择一篇接入文档：

- [GitHub](integrations/github.md)
- [GitLab](integrations/gitlab.md)
- [IM 与 uv-im-connector](integrations/im.md)
- [Jira](integrations/jira.md)
- [TAPD](integrations/tapd.md)
- [禅道 OSS 21](integrations/zentao.md)
- [云效](integrations/yunxiao.md)
- [飞书项目](integrations/feishu-project.md)

每篇接入文档都应以一条批准的真实工作项或消息验证：事件被接受、只创建一个 Task、Agent 完成实际工作，并把结果回到原对象或原会话。仅通过健康检查或 webhook 连通性检查不代表链路已上线。

## 深入了解产品边界

- [Runtime Agent](runtime-agents.md)：Agent 的运行范围。
- [代码归属与 Git 提交身份](code-attribution.md)：负责人、commit author 和机器账号的边界。
- [Delivery Metrics 历史起点](delivery-metrics.md)：进度、恢复中断分析和重试。
- [状态 API](status-api.md) 与 [架构](architecture.md)：供需要集成或审计的人查阅。
- [客户派生 Docker 镜像](custom-docker-image.md)：在保持 digest 固定、非 root 运行和可回滚升级的前提下增加系统依赖。

## 在本地打开文档

安装并启动 Jarvis Box 后，直接打开同一服务地址下的 `/docs/`。例如本机默认地址为 `http://127.0.0.1:8787/docs/`。状态页 `/status` 顶部的“产品文档”也会打开这里；文档导航中的“返回工作台”回到本实例的状态页。

文档随 Native 安装包和 Docker 镜像交付，与服务一起升级。浏览、搜索、图片和字体均使用本实例的静态文件，不需要访问公共文档网站，也不需要另外安装 Node.js 或启动文档服务器。文中的外部参考和下载链接仍需相应网络连接。

远程阅读使用客户自己的 Jarvis Box 地址，并沿用该地址的访问保护；无需为文档配置公网域名。访问入口和保护方式见[网络入口](network-ingress.md)。
