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
#import json
import sys
import os
import requests
import urllib3
urllib3.disable_warnings()

# setup some basic global variables
# edit this to put in your api_key or import the os module and get the env variable like this
api_key = os.getenv('MERAKIAPIKEY')
#api_key = ''

# list of names use on the script, do regex tag match on next one
matchlist = [
    "TELEWORKER-MN-BOUTSC",
    "TELEWORKER-MN-NETLAB"
]
base_url = 'https://n132.meraki.com/api/v0'
orgid = os.getenv('MERAKIORG')
new_dns_servers = '172.16.241.8\n10.201.10.17'
headers = {
    'X-Cisco-Meraki-API-Key': api_key,
    'Content-Type': 'application/json'
}
# a couple of empty lists to add to later
netlist = []
othererror = []
changelist = []

def display_errors():
    if othererror:
        for name in othererror:
            for a in full_network_list:
                if a['id'] == name:
                    error_name = a['name']
                    print()
                    print("something didn't work with this one: %s" % error_name)
                    sys.exit(1)
    else:
        sys.exit(1)


# set the path to get the list of network names in the TCF org
path = '/organizations/%s/networks' % orgid
#path = '/organizations/{0}/networks'.format(orgid)
response = requests.get(base_url + path, headers=headers, verify=False).json()
full_network_list = response
#print(response)

#compare the list we made above called matchlist to the items returned
for y in matchlist:
    for x in response:
        if x['name'] == y:
            #only append matching network names to the list netlist
            netlist.append(x['id'])
#print(netlist)

# get the names netlist list
for net_name in netlist:
    path = '/organizations/%s/networks/%s/vlans' % (orgid, net_name)
    response = requests.get(base_url + path, headers=headers, verify=False)
    if response:
        response = response.json()
        if 'errors' in response:
            print("ERR %s %s" % (net_name, response))
        elif response:
            # loop through the list of dicts
            for index in response:
                if 'id' in index.keys():
                    networkname = index['networkId']
                    vlanid = index['id']
                    dnsservers = index['dnsNameservers']
                    oneline_dns = dnsservers.replace('\n',' ')
                    #print("%s, %s, %s" % (networkname, vlanid, dnsservers))

                    # Here is where we checked if the nameservers are not the new ones and dump the
                    # networkid and vlan number into a list of dicts for use later
                    if dnsservers != new_dns_servers and dnsservers != 'opendns': # filter out opendns vlans
                        changelist.append({networkname: vlanid})
                        print("Adding %s, vlan: %s DNS: %s" % (networkname, vlanid, oneline_dns))
    else:
        othererror.append(net_name)

def do_change():
    for index in changelist:
        for netname,vlan in index.items():
            path = '/organizations/%s/networks/%s/vlans/%s' % (orgid, netname, vlan)
            data = '{"dnsNameservers": "%s"}' % new_dns_servers
            response = requests.put(base_url + path, headers=headers, data=data, verify=False)
            #status code 200 would be OK, meaning it was a success
            if response.status_code == 200:
                status_code = "OK"
            else:
                status_code = response.status_code
            print("Network_Name: %s, Vlan: %s, Changed: %s" % (netname, vlan, status_code))

if changelist:
    answer = input("Do you want to change the above items? (yes/no) ")
    if answer == 'yes' or answer == 'Yes' or answer == 'YES':
        do_change()
    else:
        print()
        print("No changes made")
        display_errors()
display_errors()
