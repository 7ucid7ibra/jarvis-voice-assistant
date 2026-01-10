#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/_ha_env.sh"



START=$1

URL="${HA_URL}/api/logbook"
if [ -n "$START" ]; then
    URL="$URL/$START"
fi

curl -H "Authorization: Bearer $HA_TOKEN" "$URL"
