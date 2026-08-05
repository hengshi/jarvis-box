#!/bin/sh
set -eu

base_url="${JARVIS_PUBLIC_BASE_URL:-https://download.hengshi.com/jarvis-box}"
version="${1:-}"
work=""
latest_file=""

cleanup() {
  if [ -n "$work" ]; then
    rm -rf "$work"
  fi
  if [ -n "$latest_file" ]; then
    rm -f "$latest_file"
  fi
}
trap cleanup EXIT HUP INT TERM

fail() {
  printf 'Jarvis Box Docker image download failed: %s\n' "$*" >&2
  exit 1
}

download() {
  url="$1"
  output="$2"
  progress="${3:-0}"
  resume="${4:-0}"
  retries="${JARVIS_DOWNLOAD_RETRIES:-5}"
  delay="${JARVIS_DOWNLOAD_RETRY_DELAY:-2}"
  connect_timeout="${JARVIS_DOWNLOAD_CONNECT_TIMEOUT:-20}"
  low_speed_time="${JARVIS_DOWNLOAD_LOW_SPEED_TIME:-60}"
  low_speed_limit="${JARVIS_DOWNLOAD_LOW_SPEED_LIMIT:-1024}"
  attempt=0
  for value in "$retries" "$delay" "$connect_timeout" "$low_speed_time" "$low_speed_limit"; do
    case "$value" in ''|*[!0-9]*) fail 'download retry settings must be non-negative integers' ;; esac
  done
  while :; do
    status=0
    if [ "$progress" = 1 ]; then
      if [ "$resume" = 1 ] && [ -s "$output" ]; then
        curl -fL --progress-bar --connect-timeout "$connect_timeout" \
          --speed-time "$low_speed_time" --speed-limit "$low_speed_limit" \
          -C - "$url" -o "$output" || status=$?
      else
        curl -fL --progress-bar --connect-timeout "$connect_timeout" \
          --speed-time "$low_speed_time" --speed-limit "$low_speed_limit" \
          "$url" -o "$output" || status=$?
      fi
    else
      curl -fsSL --connect-timeout "$connect_timeout" \
        --speed-time "$low_speed_time" --speed-limit "$low_speed_limit" \
        "$url" -o "$output" || status=$?
    fi
    [ "$status" -ne 0 ] || return 0
    if [ "$status" -eq 33 ]; then
      rm -f "$output"
    fi
    attempt=$((attempt + 1))
    [ "$attempt" -le "$retries" ] || fail "download failed after $attempt attempt(s): $url"
    printf 'Download failed; retrying in %ss (retry %s/%s): %s\n' "$delay" "$attempt" "$retries" "$url" >&2
    sleep "$delay"
  done
}

if [ -z "$version" ]; then
  latest_file="${TMPDIR:-/tmp}/jarvis-box-latest.$$"
  download "${base_url%/}/latest.json" "$latest_file"
  version="$(sed -n 's/^[[:space:]]*"version": "\([^"]*\)".*/\1/p' "$latest_file" | head -n 1)"
  rm -f "$latest_file"
  latest_file=""
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

printf 'Downloading Jarvis Box v%s for linux/%s...\n' "$version" "$arch"
download "$url" "$archive" 1 1
download "$url.sha256" "$checksum"
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
