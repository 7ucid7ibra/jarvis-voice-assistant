#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/_ha_env.sh"



MESSAGE=$1

curl -X POST -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" -d "{\"entity_id\": \"media_player.lg_oled_tv\", \"message\": \"$MESSAGE\"}" "${HA_URL}/api/services/tts/google_translate_say"
