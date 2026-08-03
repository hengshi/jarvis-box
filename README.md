# Jarvis Box

Jarvis Box 是 Jarvis 的任务执行运行时。它接收 GitHub、GitLab、IM、Jira 等入口产生的工作，创建 Task/Run 和独立 workspace，调用已经认证的 Agent，并把结果写回原入口，最后清理 workspace。

它不保存客户知识，也不替客户临时生成运维规则。客户知识、workflow、maintenance 和 self-improve 由客户自己的 Company Jarvis 与 Runtime Foundation 拥有。

## 最快开始

还没有 Company Jarvis 时，让一个已经授权的 Host Agent 从 create-jarvis 最新稳定 Release 开始：

```text
请打开 https://github.com/hengshi/create-jarvis/releases/latest，下载并校验最新稳定 Release，解压后读取其中的 SKILL.md，然后帮我构建一套 Jarvis。
```

Host Agent 会引导你完成资料范围确认、Company Jarvis 构建、Runtime Foundation 安装和 Jarvis Box 正式部署。你只需要在部署阶段选择 Native 或 Docker，不需要自己编写 scheduler、maintenance 或 self-improve 脚本。

已经拥有 Company Jarvis 时，从 [GitHub Releases](https://github.com/hengshi/jarvis-box/releases/latest) 下载同一版本的 release bundle 和 `SHA256SUMS`，校验后再安装。

## 选 Native 还是 Docker

| | Native | Docker |
| --- | --- | --- |
| 推荐场景 | 单机部署、配置最少、直接复用当前用户 | 需要容器隔离、独立持久化或标准化迁移 |
| 运行身份 | 发起安装的现有 OS 用户 | 容器内持久 Agent HOME |
| 认证 | 直接复用该 OS 用户的原生登录 | 导入可移植 Host 身份，或直接在容器内登录 |
| 定时任务 | Host scheduler 直接执行 Runtime Foundation job | Host scheduler 经 `runtime-job` 执行容器内 job |

部署模式在首次正式部署时确定，之后只做同模式升级。Jarvis Box 不会在 Native 与 Docker 之间自动切换；发现另一模式的 scheduler 或配置残留时应停止并按正式迁移方案处理。

## Native 安装

先以准备运行 Jarvis Box 的当前 OS 用户完成所需认证，例如 `gh`、`glab`、Codex 或 Claude。然后执行：

```bash
curl -fsSL https://raw.githubusercontent.com/hengshi/jarvis-box/main/install.sh -o /tmp/install-jarvis-box.sh
sudo bash /tmp/install-jarvis-box.sh

jarvis-box doctor
jarvis-box agent smoke
jarvis-box status
```

安装器即使通过 `sudo` 启动，也会把服务安装为发起安装的现有 OS 用户，复用该用户的 HOME 和认证。它不会创建 `jarvis` 或 `jarvis-box` 服务用户。

## Docker 安装

Docker 必须使用 release 提供的 digest-pinned 正式镜像，不使用浮动 image tag：

```dotenv
JARVIS_IMAGE=<registry>/jarvis-box@sha256:<digest>
```

解压 release bundle 后，准备私有 deployment home，并选择一种认证路径：

- 路径 A：从当前 Host 用户导入受支持的可移植身份；
- 路径 B：Host 不保存身份，启动后直接在持久容器 Agent HOME 中登录。

```bash
release_dir=/absolute/path/to/extracted-release
deployment_home=/absolute/path/to/deployment-home
ops="$release_dir/scripts/deploy-production.sh"

"$ops" "$deployment_home" start
"$ops" "$deployment_home" verify
```

路径 B 在 `deployment.env` 设置 `JARVIS_AUTH_IMPORT=skip`，首次 `start` 后执行 `"$ops" "$deployment_home" shell` 完成原生登录，再执行 `verify`。不要挂载 Host HOME，也不要把 provider execution token 或 Agent credential 写入 `runtime.env`。

完整配置和认证步骤见[客户部署与运维指南](CUSTOMER-OPERATIONS.md)与[认证指南](AUTHENTICATION.md)。

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

同时记录当前 Jarvis Box 版本、Docker image digest（如适用）、部署模式、实际 runtime root 和 Runtime Foundation 状态命令，避免后续运维依赖猜测。

## 常用入口

- [客户部署与运维指南](CUSTOMER-OPERATIONS.md)：上线、日常操作、升级、回滚、备份和诊断
- [认证指南](AUTHENTICATION.md)：Native 身份以及 Docker 两种认证路径
- [仓库与发布模型](REPOSITORY-MODEL.md)：create-jarvis、私有工程源码、公开发行仓库和 Company Jarvis 的职责
- [更新日志](CHANGELOG.md)：当前版本的客户可见变化
- [安全策略](SECURITY.md)：支持版本和漏洞报告方式

## 许可证

Jarvis Box 依据 HENGSHI 商业许可证发行。
