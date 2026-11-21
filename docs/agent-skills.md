# 用 Agent 配置和使用 Jarvis Box

本页面向已经有一个可运行 Agent 的 Jarvis Box 客户。产品 skill 让你可以用自然语言描述目标，例如“修改 IM 开始处理的提示”“把完成通知改成分析已完成”或“查看为什么收不到回复”。它会找到与已安装版本相符的配置、解释影响、在获得授权后执行修改并验证结果；你不必先记住所有变量名。

## 可安装的产品 skills

| Skill | 适用任务 |
| --- | --- |
| `jarvis-box` | 配置、使用和日常操作，包括 IM 文案、Agent、provider、通知、授权和升级。 |
| `jarvis-box-init` | 首次配置和业务链路验收。 |
| `jarvis-box-doctor` | 对指定部署做只读诊断。 |
| `jarvis-box-monitor` | 只读汇总近期活动和待处理问题。 |

这些是产品 skills，不等同于客户的 Company knowledge 或 workflow，也不包含仓库开发使用的 `code-review`、`runtime-testing` 等 repo-local skills。

## 安装或更新 product skill 包

安装 skills 不会启动服务、升级 Jarvis Box 二进制、修改运行配置或 scheduler，也不会访问另一台机器。它需要 Python 3，适用于受 Jarvis Box 支持的 macOS/Linux Agent 环境。

从已核对的公开客户仓库 revision 安装：

```bash
git clone https://github.com/hengshi/jarvis-box.git jarvis-box-customer
cd jarvis-box-customer
git rev-parse HEAD
python3 install-skills.py --skills-root /absolute/verified/agent/skills
python3 install-skills.py --skills-root /absolute/verified/agent/skills --check
```

也可以在 release bundle 根目录使用同名的 `install-skills.py` 和 `skills/`。选择与目标运行时匹配的 release 文档；更新 skill 包不会让旧二进制突然支持新版变量或功能。

`--skills-root` 必须是已确认、已存在且当前用户拥有的 Agent discovery 目录。可以重复传入，例如 `"$HOME/.codex/skills"` 和 `"$HOME/.claude/skills"`。安装器不猜测 Agent 根目录，也不创建用户；它只替换上述四个产品 skill 目录、清理这些目录内的旧文件，并保留其他 Company 和个人 skills。`--check` 只报告内容差异。更新后，在每个被更新的 Agent 启动一个新会话，确认其能发现新 skills。

Docker 部署的 skills 位于该 deployment 的持久 Agent HOME。将已经核对的 skill 包送入选定 deployment 后，进入容器，以实际 runtime 用户运行同一安装命令，并显式给出容器内的 discovery roots。Host 上的副本不会自动出现在容器中；多台机器需要分别安装。

## 与客户 Company skills 的边界

Jarvis Box 仓库拥有这四个产品 skills；客户 Company Jarvis 拥有自己的知识与 workflow。Company 的 sync/prepare 必须保留产品 skill 目录，不能复制另一套产品配置手册或覆盖产品 skills。

若启用 `JARVIS_AGENT_RUNTIME_PREPARE_COMMAND`，Jarvis Box 会在新 Task 的 workspace、provider 和依赖准备完成后、首次启动 Agent 前调用 Company preparer。Company 自己决定仓库版本和 skill 更新。普通 Continue 与同一 Run 的 Agent failover 不重复调用已经成功的 prepare；没有成功 receipt 时才会重试。这个 hook 不更新 Jarvis Box 二进制或本页的产品 skill 包。

旧 Company installer 若曾管理 `jarvis-box-init`、`jarvis-box-doctor` 或 `jarvis-box-monitor`，先按该 Company 的正式升级流程移交 ownership，再安装产品包。不要通过删除生产 discovery 目录迁移，否则旧 Company prepare 仍可能覆盖同名目录。
