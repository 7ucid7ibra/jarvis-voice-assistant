#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/_ha_env.sh"



ID=$1

curl -X DELETE -H "Authorization: Bearer $HA_TOKEN" "${HA_URL}/api/config/script/config/$ID"
