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
radius_secret = os.getenv('RADIUSSECRET')
#base_url = 'https://api.meraki.com/api/v0'
base_url = 'https://n132.meraki.com/api/v0'
orgid = os.getenv('MERAKIORG')
headers = {'X-Cisco-Meraki-API-Key': api_key, 'Content-Type': 'application/json'}
new_radius = {'radiusServers': [{'host': '172.31.27.1', 'port': 1812, 'secret': radius_secret }, {'host': '10.202.52.100', 'port': 1812, 'secret': radius_secret }]}
old_radius = {'radiusServers': [{'host': '172.16.244.93', 'port': 1812, 'secret': radius_secret }, {'host': '172.19.250.123', 'port': 1812, 'secret': radius_secret }]}
changelist = []

def get_teleworker_id():
    print("Getting list of matching network devices...")
    path = '/organizations/%s/networks' % orgid
    response = requests.get(base_url + path, headers=headers, verify=False)
    full_network_list = json.loads(response.content)
    input_dict = json.loads(response.content)
    # teleworkers = [x['id'] for x in input_dict if re.search("Branch", x['tags'])]
    # teleworkers = [x['id'] for x in input_dict if re.search("Teleworker", x['tags'])]
    teleworkers = [x['id'] for x in input_dict if re.search("scott", x['tags'])]
    # teleworkers = [x['id'] for x in input_dict if re.search("GMDM", x['tags'])]
    # print( "Length %d" % len(teleworkers))
    # print(teleworkers)
    print("Done")
    if teleworkers:
        get_ssid_info(teleworkers, full_network_list)
    else:
        print("something went wrong")
        sys.exit(1)

def get_ssid_info(teleworkers, full_network_list):
    print("Gathering SSID info...")
    for network_id in teleworkers:
        path = '/organizations/%s/networks/%s/ssids' % (orgid, network_id)
        response = requests.get(base_url + path, headers=headers, verify=False)
        input_dict = json.loads(response.content)
        for x in input_dict:
            if 'errors' not in x:
                if x['name'] == 'TCB-USER' or x['name'] == 'TCB-GMDM':
                    ssid_id = x['number']
                    changelist.append({network_id: ssid_id})
    print("Done")
    # print(changelist)
    # print(len(changelist))
    user_input(changelist, full_network_list)

def user_input(changelist, full_network_list):
    if changelist:
        print("Ready to make changes to %s networks\n" % (len(changelist)))
        print("what would you like to do next?")
        print("1) do nothing, just print the API for the changes")
        print("2) change to ISE radius servers")
        answer = input("3) change to ACS radius servers\n")
        if answer == '1':
            dry_run(changelist, full_network_list)
        elif answer == '2':
            make_change_ISE(changelist, full_network_list)
        elif answer == '3':
            make_change_ACS(changelist, full_network_list)
        else:
            sys.exit(0)
    else:
        sys.exit(0)

def dry_run(changelist, full_network_list):
    for index in changelist:
        for netname,ssid_id in index.items():
            path = ('/organizations/%s/networks/%s/ssids/%s' % (orgid, netname, ssid_id))
            for a in full_network_list:
                if a['id'] == netname:
                    match_name = a['name']
                    print("%s HTTP PUT to: %s%s, headers=%s, data=%s, verify=False" % (match_name, base_url, path, headers, json.dumps(new_radius)))
    sys.exit(0)

def make_change_ISE(changelist, full_network_list):
    for index in changelist:
        for netname,ssid_id in index.items():
            path = ('/organizations/%s/networks/%s/ssids/%s' % (orgid, netname, ssid_id))
            response = requests.put(base_url + path, headers=headers, data=json.dumps(new_radius), verify=False)
            for a in full_network_list:
                if a['id'] == netname:
                    match_name = a['name']
                    print("%s, ssid_number: %s http_code: %s" % (match_name, ssid_id, response.status_code))
                    input_dict = json.loads(response.content)
                    print(input_dict['radiusServers'])
    sys.exit(0)

def make_change_ACS(changelist, full_network_list):
    for index in changelist:
        for netname,ssid_id in index.items():
            path = ('/organizations/%s/networks/%s/ssids/%s' % (orgid, netname, ssid_id))
            response = requests.put(base_url + path, headers=headers, data=json.dumps(old_radius), verify=False)
            for a in full_network_list:
                if a['id'] == netname:
                    match_name = a['name']
                    print("%s, ssid_number: %s http_code: %s" % (match_name, ssid_id, response.status_code))
                    input_dict = json.loads(response.content)
                    print(input_dict['radiusServers'])
    sys.exit(0)

get_teleworker_id()
