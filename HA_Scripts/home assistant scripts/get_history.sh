#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/_ha_env.sh"



START=$1
ENTITY=$2

URL="${HA_URL}/api/history/period"
if [ -n "$START" ]; then
    URL="$URL/$START"
fi
if [ -n "$ENTITY" ]; then
    URL="$URL?filter_entity_id=$ENTITY"
fi

curl -H "Authorization: Bearer $HA_TOKEN" "$URL"
