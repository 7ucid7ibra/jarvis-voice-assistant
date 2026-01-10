#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/_ha_env.sh"



SLUG=$1
CONFIG=$2

curl -X POST -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" -d "$CONFIG" "${HA_URL}/api/hassio/addons/$SLUG/options"
