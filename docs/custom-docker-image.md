# 构建客户派生 Docker 镜像

本文面向 Docker 部署的客户管理员。客户仓库需要基础镜像中没有的编译器、头文件或系统共享库时，从当前 Jarvis Box 正式镜像构建一个客户镜像。若只需不依赖系统库的单个可执行文件，优先放到持久 `/home/jarvis/.local/bin`；不要为了它派生镜像。

不要在运行中的容器执行 `apt install`：运行时是非 root，重建容器后改动也会丢失。派生镜像不是放 token、SSH key、Agent 登录或客户 Jarvis 源码的位置。

<a id="1-准备"></a>

## 准备条件

准备目标版本的 release bundle、已校验的 `production-image.json`、基础 image 的拉取权限、客户 registry 的推送与部署主机拉取权限，以及目标平台（`linux/amd64` 或 `linux/arm64`）。从 `production-image.json` 复制 `image_ref`；它是构建基础镜像的唯一输入。不要用浮动 tag 替代正式 digest。

<a id="2-创建-dockerfile"></a>

## Dockerfile

在客户自己版本管理的目录中创建 Dockerfile：

```dockerfile
# syntax=docker/dockerfile:1

ARG JARVIS_BASE_IMAGE=invalid.invalid/jarvis-base-image-must-be-set
FROM ${JARVIS_BASE_IMAGE}

ARG JARVIS_BASE_IMAGE
LABEL org.opencontainers.image.base.name="${JARVIS_BASE_IMAGE}"

USER root

# Replace these example packages with packages your repositories actually need.
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      cmake \
      ninja-build \
    && rm -rf /var/lib/apt/lists/*

# Return to the Jarvis Box non-root runtime identity.
USER 10001:10001
```

Keep `apt-get update` and install in one layer. If a package version must be fixed, use `package=version` and retain that version in the customer APT mirror. Private APT credentials belong in the build platform's BuildKit secret, never in Dockerfile text, build args or image layers.

<a id="3-构建推送并取得-digest"></a>

## 构建、推送并记录 digest

```bash
base_image='<image_ref from production-image.json>'
target_repository='registry.example.com/customer/jarvis-box'
jarvis_version='<Jarvis Box version X.Y.Z>'
target_tag="${target_repository}:${jarvis_version}-tools-1"
platform='linux/amd64' # use linux/arm64 on ARM hosts

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

For one image that supports both platforms, use `linux/amd64,linux/arm64`. A required package missing on either platform must fail the build; do not publish a partially supported tag. Record the final `repository@sha256:...` value—the tag is only a build and release label.

<a id="4-部署和验证"></a>

## 部署并验证

Set the derived digest in that instance's `<deployment-home>/deployment.env`:

```dotenv
JARVIS_IMAGE=registry.example.com/customer/jarvis-box@sha256:<digest>
```

Use the deployment script from the same release bundle as the base image:

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

`verify` confirms that the running image agrees with `JARVIS_IMAGE`. The final command executes as the production non-root runtime identity; replace it with the actual tool and smallest meaningful build check for the customer workload.

<a id="5-升级和回滚"></a>
<a id="6-可靠性检查"></a>

## 升级、回滚与上线检查

For every Jarvis Box upgrade, obtain and verify the target release bundle, rebuild from its new `image_ref`, publish and record a new derived digest, set that digest, then run `deploy` and `verify`. Do not run a newer Jarvis Box version on an old derived base.

To roll back, restore the release bundle and derived digest that were built together, preserve the deployment home, then run the same deploy/verify/tool check. Image rollback and persistent-data recovery have additional safeguards; follow[运维入口](operations.md#升级) rather than swapping a running container image by hand.

Before production, review the Dockerfile and APT source, scan the image according to customer policy, keep image references digest-pinned, retain `USER 10001:10001`, and run a real minimal compilation or load check. The deployment user needs Docker/build and registry permissions; the running Jarvis container does not need root or a Docker socket merely to use these system packages.
