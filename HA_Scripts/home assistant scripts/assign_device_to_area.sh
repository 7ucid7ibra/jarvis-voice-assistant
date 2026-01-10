#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/_ha_env.sh"



DEVICE_ID=$1
AREA_ID=$2

curl -X PUT -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" -d "{\"area_id\": \"$AREA_ID\"}" "${HA_URL}/api/devices/$DEVICE_ID"
