#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/_ha_env.sh"


HA_URL="${HA_URL:-http://localhost:8123}"
HA_TOKEN="${HA_TOKEN:-}"

if [ -z "$HA_TOKEN" ]; then
  echo "HA_TOKEN is not set. Export HA_TOKEN before running these scripts." >&2
  exit 1
fi
