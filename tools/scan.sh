#!/usr/bin/env bash
# Scan every generated project as its own Mend project.
#   tools/scan.sh cli  [parallel]   # Mend CLI, one `mend dep` per folder
#   tools/scan.sh ua   [jar]        # Unified Agent, projectPerFolder=true
# Requires MEND_URL/MEND_EMAIL/MEND_USER_KEY (CLI) or WS_APIKEY/WS_USERKEY (UA).
set -euo pipefail
cd "$(dirname "$0")/.."
mode=${1:-cli}
product=${MEND_PRODUCT:-mend-scale-monorepo}

case "$mode" in
  cli)
    jobs=${2:-8}
    find projects -mindepth 2 -maxdepth 2 -type d | sort |
      xargs -P "$jobs" -I{} sh -c \
        'mend dep --dir "$1" -u -s "*//'"$product"'//$(basename "$1")" --non-interactive >/dev/null && echo "ok   $1" || echo "FAIL $1"' _ {}
    ;;
  ua)
    jar=${2:-wss-unified-agent.jar}
    dirs=$(find projects -mindepth 2 -maxdepth 2 -type d | sort | paste -sd, -)
    java -jar "$jar" -c mend/wss-unified-agent.config -product "$product" -d "$dirs"
    ;;
  *) echo "usage: $0 cli [parallel] | ua [jar]" >&2; exit 2 ;;
esac
