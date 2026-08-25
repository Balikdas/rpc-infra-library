#!/bin/bash
ilo_user=$1
ilo_pwd=$2
ilo_host=$3
fan_speed=$4
if [[ $# -ne 4 ]]; then
  echo "Usage: $0 {ilo_user} {ilo_pwd} {ilo_host} {fan_speed_percent}"
  exit 1
fi

curl_data="{\"Oem\":{\"Hpe\":{\"FanPercentMinimum\":${fan_speed}}}}"

/usr/bin/curl --insecure -u "${ilo_user}:${ilo_pwd}" \
  "https://${ilo_host}/redfish/v1/Chassis/1/Thermal" \
  -X PATCH -H 'Accept: application/json' -H 'Content-Type: application/json' \
  --data-raw ${curl_data}

echo ""
