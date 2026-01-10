#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/_ha_env.sh"



NAME=$1
USERNAME=$2
PASSWORD=$3
IS_ADMIN=$4

curl -X POST -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" -d "{\"name\": \"$NAME\", \"username\": \"$USERNAME\", \"password\": \"$PASSWORD\", \"is_admin\": $IS_ADMIN}" "${HA_URL}/api/users"
