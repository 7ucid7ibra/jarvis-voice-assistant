#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/_ha_env.sh"



ENTITY_ID=$1
MESSAGE=$2

curl -X POST -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" -d "{\"entity_id\": \"$ENTITY_ID\", \"message\": \"$MESSAGE\"}" "${HA_URL}/api/services/tts/google_translate_say"
