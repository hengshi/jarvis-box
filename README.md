# Jarvis Box

Jarvis Box 是 Jarvis 的任务执行运行时。它接收 GitHub、GitLab、IM、Jira 等入口产生的工作，创建 Task/Run 和独立 workspace，调用已经认证的 Agent，并把结果写回原入口，最后清理 workspace。

它不保存客户知识，也不替客户临时生成运维规则。客户知识、workflow，以及 JARVIS 记忆固化、日省和心智进化由客户自己的 Company Jarvis 与 Runtime Foundation 拥有。

## 最快开始

还没有 Company Jarvis 时，让一个已经授权的 Host Agent 从 create-jarvis 最新代码开始：

```text
请用 git clone https://github.com/hengshi-jarvis/create-jarvis 获取最新代码，记录 commit 和提交信息，读取其中的 SKILL.md，然后帮我构建一套 Jarvis。
```

Host Agent 会引导你完成资料范围确认、Company Jarvis 构建、Runtime Foundation 安装和 Jarvis Box 正式部署。你只需要在部署阶段选择 Native 或 Docker，不需要自己编写 scheduler 或定时认知工作脚本。

已经拥有 Company Jarvis 时，向 HENGSHI 申请 `hengshi-jarvis/jarvis-box` 私有 GitHub repository access。正式 release bundle、`SHA256SUMS`、`production-image.json` 和私有 GHCR image 以该私有仓库的 GitHub Release 为规范来源；`https://download.hengshi.com/jarvis-box` 仅作为公开 S3 fallback mirror，提供同名 release 文件和 `latest.json` 元数据。公开仓库只保留产品说明、客户文档和 issue 入口，不提交二进制 artifact。

GitHub seat/repository access 只控制 release 制品下载权限，不等同于客户运行时 license enforcement。License 是否允许启动和使用 Jarvis Box 是部署后的独立产品边界。

## 选 Native 还是 Docker

| | Native | Docker |
| --- | --- | --- |
| 推荐场景 | 单机部署、配置最少、直接复用当前用户 | 需要容器隔离、独立持久化或标准化迁移 |
| 运行身份 | 发起安装的现有 OS 用户 | 容器内持久 Agent HOME |
| 认证 | 直接复用该 OS 用户的原生登录 | 导入可移植 Host 身份，或直接在容器内登录 |
| 定时任务 | Host scheduler 直接执行 Runtime Foundation job | Host scheduler 经 `runtime-job` 执行容器内 job |

部署模式在首次正式部署时确定，之后只做同模式升级。Jarvis Box 不会在 Native 与 Docker 之间自动切换；发现另一模式的 scheduler 或配置残留时应停止并按正式迁移方案处理。

## 获取 Release

1. 确认当前 GitHub 账号可以访问 `hengshi-jarvis/jarvis-box`。
2. 从该私有仓库的目标 GitHub Release 下载当前平台 release bundle、`SHA256SUMS` 和 `production-image.json`；GitHub Release 下载不可用时，从 `https://download.hengshi.com/jarvis-box/releases/v<version>/` 下载同名 mirror 文件。
3. 按 [客户部署与运维指南](CUSTOMER-OPERATIONS.md) 校验 checksum，并使用 bundle 内的 `install.sh` 或 `scripts/deploy-production.sh` 完成部署。
4. Docker 模式使用 `production-image.json` 中的私有 GHCR digest；运行部署脚本的账号或主机需要具备相应 GHCR pull access。

## 上线完成标准

`doctor`、`verify` 或 `auth status` 只能证明局部能力。正式投入使用前必须完成至少一条真实链路：

```text
GitHub / GitLab / IM / Jira ingress
  → Task/Run
  → workspace
  → Agent
  → 原入口 writeback
  → terminal state
  → workspace cleanup
```

同时记录当前 Jarvis Box 版本、Docker release tag（如适用）、部署模式、实际 runtime root 和 Runtime Foundation 状态命令，避免后续运维依赖猜测。

## 常用入口

- [完整使用文档](docs/README.md)：Provider 接入、配置、执行模型、状态和清理合同
- [客户派生 Docker 镜像](docs/custom-docker-image.md)：通过 `apt` 增加客户代码仓库需要的编译器、头文件和系统共享库
- [Delivery Metrics 历史基线](docs/delivery-metrics.md)：查看分析进度、恢复中断基线和处理重试
- [多实例部署](docs/multi-instance.md)：同一台机器运行多个 Jarvis Box 实例时的隔离规则；Docker 推荐，Native 多实例不推荐
- [客户部署与运维指南](CUSTOMER-OPERATIONS.md)：上线、日常操作、升级、回滚、备份和诊断
- [认证指南](AUTHENTICATION.md)：Native 身份以及 Docker 两种认证路径
- [仓库与发布模型](REPOSITORY-MODEL.md)：create-jarvis、私有工程源码、公开产品仓库和 Company Jarvis 的职责
- [更新日志](CHANGELOG.md)：当前版本的客户可见变化
- [安全策略](SECURITY.md)：支持版本和漏洞报告方式

## 许可证

Jarvis Box 依据 HENGSHI 商业许可证发行。
