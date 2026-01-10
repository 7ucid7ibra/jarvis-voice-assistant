#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/_ha_env.sh"



HANDLER=$1
DATA=$2

if [ -z "$DATA" ]; then
    DATA="{}"
fi

curl -X POST -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" -d "{\"handler\": \"$HANDLER\", \"data\": $DATA}" "${HA_URL}/api/config/config_entries/flow"
