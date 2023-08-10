#!/usr/bin/env python3
# ## http logging
# import logging
# try:
#     import http.client as http_client
# except ImportError:
#     # Python 2
#     import httplib as http_client
# http_client.HTTPConnection.debuglevel = 1
# logging.basicConfig()
# logging.getLogger().setLevel(logging.DEBUG)
# requests_log = logging.getLogger("requests.packages.urllib3")
# requests_log.setLevel(logging.DEBUG)
# requests_log.propagate = True
# ## end http logging
import json
import sys
import os
import re
import requests
import urllib3
from urllib3.exceptions import ResponseError
urllib3.disable_warnings()

# setup some basic global variables
# edit this to put in your api_key or import the os module and get the env variable like this
api_key = os.getenv('MERAKIAPIKEY')
base_url = 'https://n297.meraki.com/api/v1'
orgid = os.getenv('MERAKIORG')
headers = {'X-Cisco-Meraki-API-Key': api_key, 'Content-Type': 'application/json'}
changelist = []
meraki_nets = []

def get_meraki_net_id():
    print("Getting list of matching network devices...")
    path = '/organizations/{}/networks'.format(orgid)
    response = requests.get(base_url + path, headers=headers, verify=False)
    full_network_list = json.loads(response.content)
    input_dict = json.loads(response.content)
    meraki_nets = [y['id'] for y in input_dict if re.search('DHCP_CHANGE', str(y['tags']))]
    print("Done")
    if meraki_nets:
        get_vlan_info(meraki_nets, full_network_list)
    else:
        print("something went wrong")
        sys.exit(1)

def get_vlan_info(meraki_nets, full_network_list):
    print("Gathering vlan info for networks...")
    for network_id in meraki_nets:
        path = '/networks/{}/appliance/vlans'.format(network_id)
        response = requests.get(base_url + path, headers=headers, verify=False)
        input_dict = json.loads(response.content)
        for x in input_dict:
            subnet_pattern = r'^(\d+\.\d+\.\d+\.\d+)/(\d+)$'
            match = re.match(subnet_pattern, x['subnet'])
            if match:
                subnet_start = match.group(1)
                subnet_mask = match.group(2)
            if x['id'] == 2 or x['id'] == 3:
                changelist.append({'network_id': network_id, 'vlan_id': x['id'], 'start_ip': x['applianceIp'], 'subnet_start': subnet_start, 'subnet_mask': subnet_mask})
    print("Done")
    user_input(changelist, full_network_list)

def user_input(changelist, full_network_list):
    if changelist:
        print("\n**********")
        print("Ready to make changes to {} vlans".format((len(changelist))))
        print("**********\n")
        print("what would you like to do next?")
        print("1) do nothing, just print the matched vlans for change")
        print("2) change to Local dhcp")
        answer = input("3) change to relay dhcp servers\n")
        if answer == '1':
            dry_run(changelist, full_network_list)
        elif answer == '2':
            make_change_local_dhcp(changelist, full_network_list)
        elif answer == '3':
            make_change_relay_dhcp(changelist, full_network_list)
        else:
            print()
            print("Just a moment... I've just picked up a fault in the AE-35 unit. It's going to go 100{} failure within 72 hours.".format(chr(37)))
            sys.exit(1)
    else:
        sys.exit(0)

def dry_run(changelist, full_network_list):
    print("\nHere are the matched networks:")
    for index in changelist:
        print("Modify network: {}".format(index))
    sys.exit(0)

def make_change_local_dhcp(changelist, full_network_list):
    print('\nChanging to local DHCP server:')
    for index in changelist:
        ip_pattern = r'^(\d+\.\d+\.\d+)\.(\d+)$'
        match = re.match(ip_pattern, index['start_ip'])
        if match:
            first_three = match.group(1)
            last = match.group(2)
            last_range = int(last) + 20
        network_id = index['network_id']
        vlan_id = index['vlan_id']
        start_ip = index['start_ip']
        end_ip = first_three + "." + str(last_range)
        local_dhcp = {
                    "dhcpHandling": "Run a DHCP server",
                    "dhcpLeaseTime": "1 week",
                    "dhcpOptions": [
                        {
                            "code": "15",
                            "type": "text",
                            "value": "suncountry.com"
                            },
                        {
                            "code": "42",
                            "type": "ip",
                            "value": "10.1.100.51, 10.4.99.2"
                            },
                        {
                            "code": "119",
                            "type": "hex",
                            "value": "0a:73:75:6e:63:6f:75:6e:74:72:79:03:63:6f:6d:00"
                            }
                        ],
                    "reservedIpRanges": [
                        {
                            "comment": "reserved for static",
                            "end": end_ip,
                            "start": start_ip
                            }
                        ]
                    }

        path = ('/networks/{}/appliance/vlans/{}'.format(network_id, vlan_id))
        response = requests.put(base_url + path, headers=headers, data=json.dumps(local_dhcp), verify=False)
        for a in full_network_list:
            if a['id'] == network_id:
                match_name = a['name']
                print("{}, vlan_number: {} http_code: {}".format(match_name, vlan_id, response.status_code))
    sys.exit(0)

def make_change_relay_dhcp(changelist, full_network_list):
    print('\nChanging to relay DHCP server:')
    for index in changelist:
        network_id = index['network_id']
        vlan_id = index['vlan_id']
        dhcp_relay = {
                        "dhcpHandling": "Relay DHCP to another server",
                        "dhcpOptions": [],
                        "reservedIpRanges": [],
                        "dhcpRelayServerIps": [ "10.4.48.14", "10.4.48.15" ]
                    }

        path = ('/networks/{}/appliance/vlans/{}'.format(network_id, vlan_id))
        response = requests.put(base_url + path, headers=headers, data=json.dumps(dhcp_relay), verify=False)
        for a in full_network_list:
            if a['id'] == network_id:
                match_name = a['name']
                print("{}, vlan_number: {} http_code: {}".format(match_name, vlan_id, response.status_code))
    sys.exit(0)

get_meraki_net_id()
