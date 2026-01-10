#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/_ha_env.sh"



DOMAIN=$1
SERVICE=$2
ENTITY_ID=$3
DATA=$4

if [ -z "$DATA" ]; then
    DATA="{\"entity_id\": \"$ENTITY_ID\"}"
fi

curl -X POST -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" -d "$DATA" "${HA_URL}/api/services/$DOMAIN/$SERVICE"
