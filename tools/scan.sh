#!/usr/bin/env bash
# Scan every generated project as its own Mend project.
#   tools/scan.sh cli  [parallel]   # Mend CLI, one `mend dep` per folder, retries on failure
#   tools/scan.sh ua   [jar]        # Unified Agent, projectPerFolder=true
# Requires MEND_URL/MEND_EMAIL/MEND_USER_KEY (CLI) or WS_APIKEY/WS_USERKEY (UA).
set -euo pipefail
cd "$(dirname "$0")/.."
mode=${1:-cli}
product=${MEND_PRODUCT:-mend-scale-monorepo}

case "$mode" in
  cli)
    # Keep parallelism low: every scan queues a server-side policy-compliance
    # check, and too many at once makes them miss the CLI's deadline.
    jobs=${2:-2}
    retries=${MEND_RETRIES:-3}
    find projects -mindepth 2 -maxdepth 2 -type d | sort |
      xargs -P "$jobs" -I{} sh -c '
        for try in $(seq 1 '"$retries"'); do
          mend dep --dir "$1" -u -s "*//'"$product"'//$(basename "$1")" --non-interactive >/dev/null 2>&1 &&
            { echo "ok   $1"; exit 0; }
          sleep $((try * 30))
        done
        echo "FAIL $1"' _ {} | tee scan-results.log
    ;;
  ua)
    jar=${2:-wss-unified-agent.jar}
    dirs=$(find projects -mindepth 2 -maxdepth 2 -type d | sort | paste -sd, -)
    java -jar "$jar" -c mend/wss-unified-agent.config -product "$product" -d "$dirs"
    ;;
  *) echo "usage: $0 cli [parallel] | ua [jar]" >&2; exit 2 ;;
esac
