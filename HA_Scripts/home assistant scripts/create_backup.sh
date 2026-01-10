#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/_ha_env.sh"



NAME=$1

curl -X POST -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" -d "{\"name\": \"$NAME\"}" "${HA_URL}/api/hassio/backups"
