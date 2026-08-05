#!/bin/sh
set -eu

base_url="${JARVIS_PUBLIC_BASE_URL:-https://download.hengshi.com/jarvis-box}"
version="${1:-}"
if [ -z "$version" ]; then
  version="$(curl -fsSL "${base_url%/}/latest.json" | sed -n 's/^[[:space:]]*"version": "\([^"]*\)".*/\1/p' | head -n 1)"
fi
version="${version#v}"
case "$version" in
  ''|*[!0-9.]*) printf 'Invalid Jarvis Box version: %s\n' "$version" >&2; exit 2 ;;
esac

case "$(uname -m)" in
  x86_64|amd64) arch=amd64 ;;
  arm64|aarch64) arch=arm64 ;;
  *) printf 'Unsupported Docker architecture: %s\n' "$(uname -m)" >&2; exit 2 ;;
esac

name="jarvis-box_${version}_linux_${arch}.docker.tar.gz"
url="${base_url%/}/releases/v${version}/${name}"
work="${TMPDIR:-/tmp}/jarvis-box-docker-load.$$"
archive="$work/$name"
checksum="$archive.sha256"
mkdir -m 0700 "$work"
cleanup() {
  rm -f "$archive" "$checksum"
  rmdir "$work" 2>/dev/null || true
}
trap cleanup EXIT HUP INT TERM

printf 'Downloading Jarvis Box v%s for linux/%s...\n' "$version" "$arch"
curl -fL --progress-bar "$url" -o "$archive"
curl -fsSL "$url.sha256" -o "$checksum"
if command -v sha256sum >/dev/null 2>&1; then
  (cd "$work" && sha256sum -c "$(basename "$checksum")")
elif command -v shasum >/dev/null 2>&1; then
  (cd "$work" && shasum -a 256 -c "$(basename "$checksum")")
else
  printf '%s\n' 'sha256sum or shasum is required' >&2
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  printf '%s\n' 'Docker must be usable by the current OS user; configure Docker access and rerun without sudo.' >&2
  exit 1
fi

gzip -dc "$archive" | docker load
image="hengshi/jarvis-box:v${version}"
docker image inspect "$image" >/dev/null
printf 'Jarvis Box Docker image is ready: %s\n' "$image"
