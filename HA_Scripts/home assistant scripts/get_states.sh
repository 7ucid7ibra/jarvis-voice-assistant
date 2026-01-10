#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/_ha_env.sh"



URL="${HA_URL}/api/states"

if [ $# -eq 1 ]; then
    URL="$URL/$1"
fi

curl -H "Authorization: Bearer $HA_TOKEN" "$URL"
