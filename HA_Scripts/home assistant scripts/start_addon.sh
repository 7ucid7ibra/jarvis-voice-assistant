#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/_ha_env.sh"



SLUG=$1

curl -X POST -H "Authorization: Bearer $HA_TOKEN" "${HA_URL}/api/hassio/addons/$SLUG/start"
