#!/usr/bin/env bash
set -euo pipefail

fail() {
  printf 'jarvis-box Docker install failed: %s\n' "$*" >&2
  exit 1
}

usage() {
  cat <<'EOF'
Usage:
  curl -fsSL https://download.hengshi.com/jarvis-box/docker-install.sh \
    | bash -s -- <version> <deployment-home>

The deployment home must be an absolute, current-user-owned directory outside
every Git checkout. Existing deployment.env, runtime.env and connector.env are
preserved. A new deployment home is initialized from the selected release and
must be configured before the same command is run again.
EOF
}

version="${1:-}"
deployment_home="${2:-${JARVIS_DEPLOYMENT_HOME:-}}"
case "$version" in
  -h|--help|help) usage; exit 0 ;;
esac
printf '%s' "$version" | grep -Eq '^[0-9]+[.][0-9]+[.][0-9]+$' \
  || { usage >&2; fail 'version must be X.Y.Z'; }
case "$deployment_home" in
  /*) ;;
  *) usage >&2; fail 'deployment home must be an absolute path' ;;
esac
[ "$(id -u)" -ne 0 ] || fail 'run as the existing OS user; do not use sudo'

require() {
  command -v "$1" >/dev/null 2>&1 || fail "$1 is required"
}

require curl
require docker
require python3
require tar
docker compose version >/dev/null 2>&1 || fail 'Docker Compose v2 is required'
docker info >/dev/null 2>&1 || fail 'Docker must be usable by the current OS user'

case "$(uname -s)" in
  Linux) os_name=linux ;;
  Darwin) os_name=darwin ;;
  *) fail "unsupported host OS: $(uname -s)" ;;
esac
case "$(uname -m)" in
  x86_64|amd64) arch=amd64 ;;
  arm64|aarch64) arch=arm64 ;;
  *) fail "unsupported host architecture: $(uname -m)" ;;
esac

download_base="${JARVIS_DOWNLOAD_BASE_URL:-https://download.hengshi.com/jarvis-box}"
release_home="${JARVIS_RELEASE_HOME:-$HOME/.local/share/jarvis-box/releases}"
artifact="jarvis-box_${version}_${os_name}_${arch}"
release_dir="$release_home/v$version/$artifact"
archive="$artifact.tar.gz"
tmp="${TMPDIR:-/tmp}/jarvis-box-docker-install.$$"
cleanup() { rm -rf "$tmp"; }
trap cleanup EXIT HUP INT TERM
mkdir -m 0700 -p "$tmp" "$release_home/v$version"

download() {
  curl --fail --location --silent --show-error \
    --retry 4 --retry-delay 2 --retry-all-errors "$1" -o "$2"
}

if [ ! -x "$release_dir/scripts/deploy-production.sh" ]; then
  download "$download_base/releases/v$version/$archive" "$tmp/$archive"
  download "$download_base/releases/v$version/SHA256SUMS" "$tmp/SHA256SUMS"
  expected="$(awk -v name="$archive" '$2 == name || $2 == "*" name { print $1; exit }' "$tmp/SHA256SUMS")"
  [ -n "$expected" ] || fail "release checksum is missing for $archive"
  actual="$(python3 - "$tmp/$archive" <<'PY'
import hashlib
import pathlib
import sys

digest = hashlib.sha256()
with pathlib.Path(sys.argv[1]).open("rb") as stream:
    for block in iter(lambda: stream.read(1024 * 1024), b""):
        digest.update(block)
print(digest.hexdigest())
PY
)"
  [ "$actual" = "$expected" ] || fail "release checksum mismatch for $archive"
  tar -xzf "$tmp/$archive" -C "$tmp"
  [ -x "$tmp/$artifact/scripts/deploy-production.sh" ] \
    || fail 'release archive does not contain the Docker deployment script'
  rm -rf "$release_dir"
  mv "$tmp/$artifact" "$release_dir"
fi

created=0
if [ ! -e "$deployment_home" ]; then
  mkdir -m 0700 -p "$deployment_home"
  created=1
fi
[ -d "$deployment_home" ] && [ ! -L "$deployment_home" ] && [ -O "$deployment_home" ] && [ -w "$deployment_home" ] \
  || fail "deployment home must be a current-user-owned physical directory: $deployment_home"
deployment_home="$(cd -P -- "$deployment_home" && pwd -P)"
ancestor="$deployment_home"
while [ "$ancestor" != / ]; do
  [ ! -e "$ancestor/.git" ] || fail "deployment home must not be inside a Git checkout: $deployment_home"
  ancestor="$(dirname "$ancestor")"
done

if [ "$created" -eq 1 ]; then
  install -m 0600 "$release_dir/deploy/production/deployment.env.example" "$deployment_home/deployment.env"
  install -m 0600 "$release_dir/deploy/production/runtime.env.example" "$deployment_home/runtime.env"
  install -m 0600 "$release_dir/deploy/production/connector.env.example" "$deployment_home/connector.env"
  python3 - "$deployment_home/deployment.env" "$deployment_home" "$version" <<'PY'
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
home = sys.argv[2]
version = sys.argv[3]
text = path.read_text(encoding="utf-8")
text = text.replace("JARVIS_DEPLOYMENT_HOME=/absolute/path/to/acme-jarvis-deployment", f"JARVIS_DEPLOYMENT_HOME={home}")
text = text.replace("JARVIS_IMAGE=hengshi/jarvis-box:vREPLACE_WITH_VERSION", f"JARVIS_IMAGE=hengshi/jarvis-box:v{version}")
path.write_text(text, encoding="utf-8")
PY
  printf 'Docker deployment configuration initialized at %s\n' "$deployment_home"
  printf 'Configure deployment.env, runtime.env and connector.env, then run the same command again.\n'
  exit 0
fi

for config in deployment.env runtime.env; do
  path="$deployment_home/$config"
  [ -f "$path" ] && [ ! -L "$path" ] && [ -O "$path" ] \
    || fail "missing current-user-owned deployment configuration: $path"
done

env_value() {
  python3 - "$1" "$2" <<'PY'
import pathlib
import sys

result = ""
for raw in pathlib.Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():
    line = raw.strip()
    if not line or line.startswith("#"):
        continue
    if line.startswith("export "):
        line = line[7:].lstrip()
    key, separator, value = line.partition("=")
    if separator and key.strip() == sys.argv[2]:
        result = value.strip().strip("'\"")
print(result, end="")
PY
}

configured_home="$(env_value "$deployment_home/deployment.env" JARVIS_DEPLOYMENT_HOME)"
[ -z "$configured_home" ] || [ "$configured_home" = "$deployment_home" ] \
  || fail "deployment.env belongs to another deployment home: $configured_home"
project="$(env_value "$deployment_home/deployment.env" JARVIS_DEPLOYMENT_NAME)"
[ -n "$project" ] || project=jarvis-production
containers="$(docker ps \
  --filter "label=com.docker.compose.project=$project" \
  --filter 'label=com.docker.compose.service=jarvis-box' \
  --format '{{.ID}}')"
if [ -n "$containers" ]; then
  [ "$(printf '%s\n' "$containers" | awk 'NF { count++ } END { print count+0 }')" -eq 1 ] \
    || fail "multiple running jarvis-box containers belong to Compose project $project"
  status_json="$tmp/status.json"
  docker exec "$containers" curl -fsS http://127.0.0.1:8787/status/api/tasks >"$status_json" \
    || fail 'running service status is unavailable; refusing to replace it'
  active="$(python3 - "$status_json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as stream:
    payload = json.load(stream)
print(int(payload.get("counts", {}).get("active", 0)))
PY
)"
  [ "$active" -eq 0 ] || fail "$active active Task Run(s) must finish or be cancelled before upgrade"
fi

download "$download_base/docker-load.sh" "$tmp/docker-load.sh"
bash "$tmp/docker-load.sh" "$version"

python3 - "$deployment_home/deployment.env" "$deployment_home" "$version" <<'PY'
import pathlib
import re
import sys

path = pathlib.Path(sys.argv[1])
home = sys.argv[2]
version = sys.argv[3]
text = path.read_text(encoding="utf-8")

def assign(source, name, value):
    pattern = re.compile(rf"(?m)^(?:export\s+)?{re.escape(name)}=.*$")
    if pattern.search(source):
        return pattern.sub(f"{name}={value}", source, count=1)
    return source.rstrip() + f"\n{name}={value}\n"

text = assign(text, "JARVIS_DEPLOYMENT_HOME", home)
text = assign(text, "JARVIS_IMAGE", f"hengshi/jarvis-box:v{version}")
temporary = path.with_name(path.name + ".tmp")
temporary.write_text(text, encoding="utf-8")
temporary.chmod(0o600)
temporary.replace(path)
PY

"$release_dir/scripts/deploy-production.sh" "$deployment_home" deploy
printf 'Jarvis Box v%s is installed and verified.\n' "$version"
printf 'operations=%s/scripts/deploy-production.sh\n' "$release_dir"
