# 仓库与发布模型

Jarvis 使用多个独立仓库，因为构建方法、运行时实现和公开发行各自有不同的所有者与安全边界。

## 仓库所有权

| 仓库 | 角色 | 拥有 | 不拥有 |
| --- | --- | --- | --- |
| [`hengshi/create-jarvis`](https://github.com/hengshi/create-jarvis) | 客户构建方法 | 已认证 Host Agent 用于构建客户自有 Company Jarvis、学习 repo-local skills、协调 workflow 并 onboarding 正式运行时的可恢复方法 | Jarvis Box 源码、控制面、运行时状态或客户凭据 |
| [`hengshi-jarvis/jarvis-box`](https://github.com/hengshi-jarvis/jarvis-box) | Jarvis Box 工程真源 | 完整源码、测试、CI、镜像构建、规范 source release artifact、生产门禁和内部部署 | 客户安装依赖或公开访问面 |
| [`hengshi/jarvis-box`](https://github.com/hengshi/jarvis-box) | 公开产品与发行面 | 公开安装与运维合同、完整客户文档、tag、Release、checksum 和经验证的 artifact | 完整私有源码树或 release artifact 的独立构建 |
| 客户 Company Jarvis 仓库 | 客户自有知识与策略 | 公司知识、workflow 定义、跨运行时治理和客户自有 skills | Jarvis Box 实现或 create-jarvis 方法内部 |

## 单向发布流

```text
私有 GitHub 规范源码与 Actions
  → 构建并验证不可变 artifact
  → 创建规范 source GitHub Release
  → 同步精选公开仓库 overlay
  → 创建匹配的 GitHub tag 与 Release
  → 上传完全相同的已验证 artifact
  → 发布版本化下载
  → 最后更新 latest.json
```

没有任何内容从公开 Jarvis Box 仓库回流到私有源码仓库。客户和 `create-jarvis` 仅消费公开 release 合同；他们永远不需要私有 GitLab 源码。

## 版本规则

- Jarvis Box 版本号如 `v0.1.38` 在 GitLab、GitHub 和公开下载服务上标识同一个运行时 release。
- 私有源码 tag 指向规范源码 commit。公开 GitHub tag 指向精选公开 overlay commit，因此两个 Git commit ID 预期不同。
- Release artifact 文件名与 SHA-256 digest 在私有 source Release、公开 GitHub Release 和公开下载服务上必须一致。
- `production-image.json` 将 release 绑定到规范源码 commit、已通过门禁的内部 manifest digest，以及两个公网 Docker archive；客户只通过一键加载脚本消费它。
- `create-jarvis` 以 commit 为核心标识。它记录 onboarding 时选择的精确 Jarvis Box release；不将运行时版本复用为自身标识。

## 完成不变量

仅有 source Release 或已部署的生产镜像不构成已完成的公开 release。只有在 GitHub tag workflow 验证每一个公开面后 release 才算完成。公开 GitHub 或下载服务的失败会使 release workflow 失败，而非留下隐藏的手工后续步骤。
