# 仓库与发布模型

Jarvis 使用多个独立仓库，因为构建方法、运行时实现和客户知识各自有不同的所有者与安全边界。

## 仓库所有权

| 仓库 | 角色 | 拥有 | 不拥有 |
| --- | --- | --- | --- |
| [`hengshi-jarvis/create-jarvis`](https://github.com/hengshi-jarvis/create-jarvis) | 客户构建方法 | 已认证 Host Agent 用于构建客户自有 Company Jarvis、学习 repo-local skills、协调 workflow 并 onboarding 正式运行时的可恢复方法 | Jarvis Box 源码、控制面、运行时状态或客户凭据 |
| [`hengshi-jarvis/jarvis-box`](https://github.com/hengshi-jarvis/jarvis-box) | Jarvis Box 工程真源与正式分发面 | 完整源码、测试、CI、镜像构建、规范 GitHub Release、release bundle、checksum、`production-image.json` 和私有 GHCR image | 客户知识、Company Jarvis workflow 或客户运行时 license 判定 |
| `https://download.hengshi.com/jarvis-box` | 公开 S3 fallback mirror | 与规范 GitHub Release 同名的 release bundle、`SHA256SUMS`、`production-image.json` 和 `latest.json` 元数据 | 源码、授权判定、私有 GHCR pull 权限、公开 GitHub repo 同步 |
| 公开 Jarvis Box 仓库 | 产品说明与 onboarding stub | 客户文档、issue 入口、获取私有 GitHub access 的指引和版本说明 | 二进制 artifact、checksum、安装脚本、镜像包或完整私有源码树 |
| 客户 Company Jarvis 仓库 | 客户自有知识与策略 | 公司知识、workflow 定义、跨运行时治理和客户自有 skills | Jarvis Box 实现或 create-jarvis 方法内部 |

## 单向发布流

```text
私有 GitHub 规范源码与 Actions
  → 构建并验证不可变 release bundle
  → 推送私有 GHCR production image
  → 写入 production-image.json
  → 创建私有 GitHub Release
  → 同步公开 S3 fallback mirror
  → 同步精选公开仓库 overlay 文档
```

没有任何内容从公开 Jarvis Box 仓库回流到私有源码仓库。客户和 `create-jarvis` 消费的是私有 `hengshi-jarvis/jarvis-box` GitHub Release 合同；公开 S3 mirror 只作为同名 release 文件的下载 fallback，公开仓库不承载 release artifact。

## 版本规则

- Jarvis Box 版本号如 `v0.2.16` 在私有 GitHub Release、release bundle、`production-image.json` 和私有 GHCR image tag 上标识同一个运行时 release。
- 私有源码 tag 指向规范源码 commit。公开仓库 overlay commit 只代表文档同步点，不是可安装制品来源。
- Release artifact 文件名与 SHA-256 digest 以私有 GitHub Release 为规范来源，公开 S3 mirror 保持同名文件和同一份 `SHA256SUMS`。
- `production-image.json` 将 release 绑定到规范源码 commit、通过门禁的 manifest digest，以及 digest-pinned 私有 GHCR image。
- `create-jarvis` 以 commit 为核心标识。它记录 onboarding 时选择的精确 Jarvis Box release；不将运行时版本复用为自身标识。

## 完成不变量

只有私有 GitHub Release 同时包含四平台 release bundle、`SHA256SUMS`、`production-image.json`，公开 S3 mirror 已同步同名文件，并且 GitHub Actions release gate 已验证 source、image 和部署合同后，正式 release 才算完成。公开仓库同步失败会阻断文档/onboarding 面，但不会成为另一个二进制分发面。
