# 构建客户派生 Docker 镜像

Docker 部署需要的系统编译器、头文件或共享库不在 Jarvis Box 基础镜像中时，以当前 Jarvis Box 正式镜像为基础构建客户派生镜像。不要在运行中的容器里执行 `apt install`：容器默认以非 root 用户运行，而且容器重建后系统层修改会消失。

只需要单个可执行文件且不依赖系统库时，仍优先安装到持久化的 `/home/jarvis/.local/bin`。派生镜像用于必须由 `apt` 管理的系统包。

## 1. 准备

准备以下内容：

- 目标 Jarvis Box 版本的 release bundle 和已校验的 `production-image.json`；
- 对正式 Jarvis Box 基础镜像的拉取权限；
- 对客户私有镜像仓库的推送和部署主机拉取权限；
- 部署主机对应的平台：`linux/amd64` 或 `linux/arm64`。

从 `production-image.json` 复制 `image_ref`。该 digest 地址是派生镜像唯一允许使用的基础镜像，不要改用浮动 tag。

## 2. 创建 Dockerfile

在一个客户自己版本管理的空目录中创建 `Dockerfile`：

```dockerfile
# syntax=docker/dockerfile:1

ARG JARVIS_BASE_IMAGE=invalid.invalid/jarvis-base-image-must-be-set
FROM ${JARVIS_BASE_IMAGE}

ARG JARVIS_BASE_IMAGE
LABEL org.opencontainers.image.base.name="${JARVIS_BASE_IMAGE}"

USER root

# 将示例包替换为客户代码仓库实际需要的包。
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      cmake \
      ninja-build \
    && rm -rf /var/lib/apt/lists/*

# 保留 Jarvis Box 镜像的非 root 默认身份。
USER 10001:10001
```

同一个 `RUN` 中完成 `apt-get update` 和安装。需要固定工具版本时使用 `package=version`，并确保客户 APT mirror 长期保留该版本。不要把 APT、registry 或源码仓库凭据写入 Dockerfile、build argument 或镜像层；私有 APT 源使用客户构建平台的 BuildKit secret。

## 3. 构建、推送并取得 digest

```bash
base_image='<production-image.json 中的 image_ref>'
target_repository='registry.example.com/customer/jarvis-box'
jarvis_version='<Jarvis Box 版本 X.Y.Z>'
target_tag="${target_repository}:${jarvis_version}-tools-1"
platform='linux/amd64' # ARM 服务器改为 linux/arm64

docker login ghcr.io
docker login registry.example.com

docker buildx build \
  --platform "$platform" \
  --build-arg JARVIS_BASE_IMAGE="$base_image" \
  --tag "$target_tag" \
  --push \
  .

digest="$(docker buildx imagetools inspect "$target_tag" | awk '$1 == "Digest:" { print $2; exit }')"
test -n "$digest"
derived_image="${target_repository}@${digest}"
printf '%s\n' "$derived_image"
```

同一派生镜像需要同时支持 AMD64 和 ARM64 时，把 `platform` 改为 `linux/amd64,linux/arm64`。任一平台缺少所需 APT 包时，构建应失败，不要发布只有部分平台成功的同名 tag。

部署始终使用最后打印的 `repository@sha256:...`，不要使用可被覆盖的 tag。

## 4. 部署和验证

把 `<deployment-home>/deployment.env` 中的 `JARVIS_IMAGE` 改为派生镜像 digest：

```dotenv
JARVIS_IMAGE=registry.example.com/customer/jarvis-box@sha256:<digest>
```

使用与基础镜像同版本 release bundle 中的部署脚本：

```bash
release_dir=/absolute/path/to/extracted-release
home=/absolute/path/to/deployment-home
ops="$release_dir/scripts/deploy-production.sh"

"$ops" "$home" deploy
"$ops" "$home" verify
"$ops" "$home" runtime-job bash -ceu '
  command -v cmake
  cmake --version
  command -v ninja
  ninja --version
'
```

`verify` 必须确认实际运行镜像与 `JARVIS_IMAGE` 的 digest 一致。最后一条命令验证客户工具在 Jarvis Box 正式非 root 运行身份下可发现并可执行；替换为客户实际安装的命令和最小编译检查。

## 5. 升级和回滚

升级 Jarvis Box 时：

1. 下载并校验目标版本的 release bundle 和 `production-image.json`；
2. 用目标版本的 `image_ref` 重新构建派生镜像；
3. 推送新 tag，记录新的派生镜像 digest；
4. 把 `deployment.env` 的 `JARVIS_IMAGE` 改为新 digest；
5. 使用目标版本 bundle 的 `deploy` 和 `verify`。

不要让旧派生镜像继续承载新版本 Jarvis Box，也不要在原 tag 上覆盖镜像后继续使用旧 digest。

回滚时恢复对应旧版本的 release bundle 和派生镜像 digest，再执行同一套 `deploy`、`verify` 和客户工具检查。部署前记录当前派生镜像 digest；完整 deployment home 保持不变。

## 6. 可靠性检查

- Dockerfile 和 APT 源配置由客户版本管理并接受代码审查；
- 基础镜像和部署镜像都使用 digest，tag 只用于构建和发布时辨识；
- 镜像最后保留 `USER 10001:10001`，运行时不依赖 root；
- 客户镜像进入正式环境前执行漏洞扫描和客户自己的供应链审批；
- 不在镜像中保存 Token、SSH key、Agent 凭据或 Company Jarvis 源码；
- 每次 Jarvis Box 升级重新构建、验证并记录派生镜像 digest；
- 安装共享库或编译器后，运行一条真实的最小编译命令，不只检查文件是否存在。
