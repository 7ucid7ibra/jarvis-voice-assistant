#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/_ha_env.sh"



CAMERA_ENTITY=$1
TIME=$2

if [ -z "$TIME" ]; then
    TIME=$(date +%s%3N)
fi

curl -H "Authorization: Bearer $HA_TOKEN" "${HA_URL}/api/camera_proxy/$CAMERA_ENTITY?time=$TIME" -o camera_image.jpg
