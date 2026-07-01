#!/usr/bin/env bash
set -euo pipefail

PUBLIC_BASE="${JARVIS_PUBLIC_BASE_URL:-https://download.hengshi.com/jarvis-box}"
PUBLIC_BASE="${PUBLIC_BASE%/}"
IMPLEMENTATION_URL="${JARVIS_INSTALLER_URL:-$PUBLIC_BASE/installer/jarvis-box-install.sh}"

usage() {
  printf '%s\n' "Usage:"
  printf '%s\n' "  curl -fsSL https://download.hengshi.com/jarvis-box/install.sh | sudo bash"
  printf '%s\n' "  curl -fsSL https://download.hengshi.com/jarvis-box/install.sh | sudo JARVIS_VERSION=0.1.2 bash"
  printf '%s\n' ""
  printf '%s\n' "Examples:"
  printf '%s\n' "  JARVIS_VERSION=0.1.2 bash install.sh"
  printf '%s\n' "  JARVIS_PUBLIC_BASE_URL=https://download.example.com/jarvis-box bash install.sh"
  printf '%s\n' ""
  printf '%s\n' "Agent notes:"
  printf '%s\n' "  - Public installation targets Ubuntu 22.04/24.04 with systemd."
  printf '%s\n' "  - The public wrapper resolves latest.json, sets the public release base, and runs the versioned installer implementation."
  printf '%s\n' "  - Set JARVIS_VERSION for pinned installs."
}

case "${1:-}" in
  --help|-h|help)
    usage
    exit 0
    ;;
esac

require_command() {
  command -v "$1" >/dev/null 2>&1 || {
    printf '[install] ERROR: %s is required\n' "$1" >&2
    exit 1
  }
}

require_command curl
require_command python3
require_command bash

tmp_dir="$(mktemp -d)"
cleanup() {
  rm -rf "$tmp_dir"
}
trap cleanup EXIT HUP INT TERM

if [ -z "${JARVIS_VERSION:-}" ]; then
  latest_json="$tmp_dir/latest.json"
  curl -fsSL "$PUBLIC_BASE/latest.json" -o "$latest_json"
  JARVIS_VERSION="$(python3 -c 'import json, pathlib, sys; data=json.loads(pathlib.Path(sys.argv[1]).read_text()); version=str(data.get("version") or "").strip(); print(version) if version else sys.exit("latest.json missing version")' "$latest_json")"
  export JARVIS_VERSION
fi

export JARVIS_RELEASE_BASE="${JARVIS_RELEASE_BASE:-$PUBLIC_BASE/releases}"
export JARVIS_PUBLIC_INSTALL=1

curl -fsSL "$IMPLEMENTATION_URL" | bash -s -- "$@"
