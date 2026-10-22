# Agent 帮助配置与使用 Jarvis Box

客户可以直接描述想要的行为，例如“修改 IM 开始处理的提示”“把完成通知改成分析已完成”“查看为什么收不到回复”。`jarvis-box` skill 负责查找对应版本的配置、解释生效方式、执行已授权的修改并验证结果，不要求客户记住变量名。

产品 skill 包包含四个入口：

| Skill | 用途 |
| --- | --- |
| `jarvis-box` | 按目标配置、使用和操作，包括 IM 文案、Agent、provider、通知、授权和升级 |
| `jarvis-box-init` | 引导首次配置与业务链路验收 |
| `jarvis-box-doctor` | 只读诊断指定部署 |
| `jarvis-box-monitor` | 只读汇总近期活动与待处理问题 |

## 独立安装和更新

产品 skills 与 Jarvis Box 二进制、Company Jarvis 的知识/workflow 分别安装。安装 skills 不启动服务、不升级二进制、不修改配置或 scheduler，也不访问其他机器。需要 Python 3，支持 Jarvis Box 的 macOS/Linux Agent 环境。

从公开客户仓库获取经过核对的 revision：

```bash
git clone https://github.com/hengshi/jarvis-box.git jarvis-box-customer
cd jarvis-box-customer
git rev-parse HEAD
python3 install-skills.py --skills-root /absolute/verified/agent/skills
python3 install-skills.py --skills-root /absolute/verified/agent/skills --check
```

也可使用包含该入口的 release bundle 根目录中的同名 `install-skills.py` 和 `skills/`。选择与目标运行时相符的 release 文档；skill 安装可以独立更新，不能假定新文档中的变量已被旧二进制支持。历史 bundle 没有这个入口时，不会因安装新版 skill 自动获得新版运行时功能。

`--skills-root` 必须是已确认、已存在、当前用户拥有的真实 Agent discovery 目录，可以重复传入；安装器不猜测 Agent 根目录、不创建新用户。比如本机已存在的 Codex 和 Claude Code 根可以分别传入 `"$HOME/.codex/skills"` 和 `"$HOME/.claude/skills"`。它只替换四个产品 skill 目录，移除这些目录内的过时文件，保留 Company 和其他 skills；`--check` 只检查内容差异。

再次更新时，从已核对的新 revision 或 release bundle 运行同一安装命令。在每个被更新的 Agent 中启动新会话确认发现。

Docker 运行时的 Agent skills 位于该 deployment 的持久 Agent HOME。把已核对的 skill 包送入选定 deployment 后，在容器内以实际 runtime 用户运行同一命令，显式传入容器里的 discovery roots。Host 上安装的副本不等于容器里的副本。多台机器各自执行安装；更新开发机不会更新另一台生产机。

## 与 Company skills 的边界

Jarvis Box 仓库拥有产品 skills，客户 Company Jarvis 拥有知识与 workflow。Company sync/prepare 应保留四个产品 skill 目录，不复制一份产品配置手册，也不替换产品 skills。仓库开发用的 `code-review`、`runtime-testing` 等 repo-local skills 不属于客户产品包。

本仓库另有一个不随产品包安装的 `jarvis-box-release-maintainer` skill，用于维护公开 release overlay；`install-skills.py` 仍固定只发布四个客户入口。四个产品 skills 的版本兼容、能力覆盖和隔离评测资产随产品目录一起发布，正常使用时只需按 `SKILL.md` 的按需链接读取。

启用 `JARVIS_AGENT_RUNTIME_PREPARE_COMMAND` 时，Jarvis Box 在新 Task 的 workspace/provider 和依赖准备完成后、首次启动 Agent 前调用 Company 的 preparer。Company 自己决定仓库版本与 skill 更新；普通 Continue 和同一 Run 的 Agent failover 不重复调用已有成功 prepare，缺少成功 receipt 时才重试。此 hook 不更新本产品 skill 包或 Jarvis Box 二进制。

已有 Company installer 曾管理 `jarvis-box-init/doctor/monitor` 时，需要先通过该 Company's 正式升级流程移交 ownership，再独立安装产品包；否则旧 Company prepare 仍可能覆盖同名目录。不要通过删除生产 discovery 目录来迁移。
