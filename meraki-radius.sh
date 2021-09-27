#!/usr/bin/env bash
command -v curl >/dev/null 2>&1 || { echo >&2 "I require curl but it's not installed.  Aborting."; exit 1; }
command -v jq >/dev/null 2>&1 || { echo >&2 "I require jq but it's not installed.  Aborting."; exit 1; }
org_id="${MERAKIORG}"
RADIUSSECRET="${RADIUSSECRET}"
base_url="https://n132.meraki.com/api/v0"
api_key="${MERAKIAPIKEY}"
new_radius='{"radiusServers":[{"host":"172.31.27.1","port":1812,"secret":"'${RADIUSSECRET}'"},{"host":"10.202.52.100","port":1812,"secret":"'${RADIUSSECRET}'"}]}'
old_radius='{"radiusServers":[{"host":"172.16.244.93","port":1812,"secret":"'${RADIUSSECRET}'"},{"host":"172.19.250.123","port":1812,"secret":"'${RADIUSSECRET}'"}]}'
declare -A net_ssid_id
spin() {
    spinner="/|\\-/|\\-"
    while :
    do
        for i in `seq 0 7`
        do
            echo -n "${spinner:$i:1}"
            echo -en "\010"
            sleep 0.3
        done
    done
    }

get_teleworker_id() {
    # just get the unique networkId for the matching tag
    echo "Getting list of matching network devices..."
# Match tag Teleworker
#    teleworkers=$(curl -k -s --location --request GET ''${base_url}'/organizations/'${org_id}'/networks' --header 'X-Cisco-Meraki-API-Key: '${api_key}'' --header 'Content-Type: application/json' | jq -r '.[] | select(.tags|test(".Teleworker.?")) | .id')
# Match tag TEST
#    teleworkers=$(curl -k -s --location --request GET ''${base_url}'/organizations/'${org_id}'/networks' --header 'X-Cisco-Meraki-API-Key: '${api_key}'' --header 'Content-Type: application/json' | jq -r '.[] | select(.tags|test(".TEST.?"))| .id')
# just scott
    teleworkers=$(curl -k -s --location --request GET ''${base_url}'/organizations/'${org_id}'/networks' --header 'X-Cisco-Meraki-API-Key: '${api_key}'' --header 'Content-Type: application/json' | jq -r '.[] | select(.tags|test(".scott.?"))| .id')

    echo "Done"
    }

get_ssid_info() {
    # find the SSID number for TCB-USER if it exists and store it with the networkId
    echo "Gathering SSID info..."
    spin &
    spin_pid=$!
    for i in ${teleworkers}
        do
            tcb_user_id=$(curl -k -s --location --request GET ''${base_url}'/organizations/'${org_id}'/networks/'${i}'/ssids' --header 'X-Cisco-Meraki-API-Key: '${api_key}'' --header 'Content-Type: application/json' | jq -r '.[] | select(.name == "TCB-USER"?) | .number')
            if [[ -n ${tcb_user_id} && ${i} ]]; then
                net_ssid_id+=([${i}]=${tcb_user_id})
            fi
        done
    $(kill -9 $spin_pid)
    wait $spin_pid 2>/dev/null
    return
}

dry_run() {
    echo "These would be the commands to make the change"
    #echo ${net_ssid_id[*]}
    for key in "${!net_ssid_id[@]}"
        do
            #echo "$key, value: ${net_ssid_id[$key]}
            echo "curl -k -s --location --request PUT '${base_url}/networks/${key}/ssids/${net_ssid_id[$key]}' --header 'Accept: */*' --header 'X-Cisco-Meraki-API-Key: ${api_key}' --header 'Content-Type: application/json' --data '${new_radius}'"
        done
}

make_change_ISE() {
    for key in "${!net_ssid_id[@]}"
        do
            output=$(curl -k -w "\n%{http_code}" -s --location --request PUT ''${base_url}'/networks/'${key}'/ssids/'${net_ssid_id[$key]}'' --header 'Accept: */*' --header 'X-Cisco-Meraki-API-Key: '${api_key}'' --header 'Content-Type: application/json' --data ''${new_radius}'')
            http_code=$(tail -n1 <<< ${output})
            content=$(sed '$ d' <<< ${output})
            echo "$key, ssid_number: ${net_ssid_id[$key]} http_code: ${http_code}"
            echo $(echo ${content} | jq '.radiusServers')
        done
}

make_change_ACS() {
    for key in "${!net_ssid_id[@]}"
        do
            output=$(curl -k -w "\n%{http_code}" -s --location --request PUT ''${base_url}'/networks/'${key}'/ssids/'${net_ssid_id[$key]}'' --header 'Accept: */*' --header 'X-Cisco-Meraki-API-Key: '${api_key}'' --header 'Content-Type: application/json' --data ''${old_radius}'')
            http_code=$(tail -n1 <<< "$output")
            content=$(sed '$ d' <<< "$output")
            echo "$key, ssid_number: ${net_ssid_id[$key]} http_code: ${http_code}"
            echo $(echo ${content} | jq '.radiusServers')
        done
}

get_teleworker_id
get_ssid_info

echo "Ready to make changes to ${#net_ssid_id[@]} devices"
printf "what would you like to do next?\n"
printf "1) do nothing, just print the curl commands for the changes\n"
printf "2) change to ISE radius servers\n"
printf "3) change to ACS radius servers\n"
read change_choice

if [[ ${change_choice} == "1" ]]; then
    dry_run
fi
if [[ ${change_choice} == "2" ]]; then
    make_change_ISE
fi
if [[ ${change_choice} == "3" ]]; then
    make_change_ACS
    else
        exit
fi
