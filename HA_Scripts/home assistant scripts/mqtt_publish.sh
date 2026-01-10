#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/_ha_env.sh"



TOPIC=$1
PAYLOAD=$2

curl -X POST -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" -d "{\"topic\": \"$TOPIC\", \"payload\": \"$PAYLOAD\"}" "${HA_URL}/api/services/mqtt/publish"
