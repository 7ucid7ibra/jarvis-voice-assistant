#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/_ha_env.sh"



TEMPLATE=$1

curl -X POST -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" -d "{\"template\": \"$TEMPLATE\"}" "${HA_URL}/api/template"
