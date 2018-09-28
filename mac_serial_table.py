#! python

######  METADATA    ######
#   Author: mirakelsvampen
#   Date: 2018-09-28
#   Purpose: translate access point mac addresses to serial numbers
#   Tested on: Windows 10 only
#   Free for anyone to use/modify/conquer the world
######  METADATA    ######

import os
import re
import sys
import ssl
import json
import base64
import urllib.request as request
import argparse

from time import sleep
from pprint import pprint
from getpass import getpass
from netmiko import ConnectHandler

class Login():
    def __init__(self, username, password):
        basic_auth_str = '{}:{}'.format(username, password)
        basic_auth_str = basic_auth_str.encode()
        self.base64string = base64.b64encode(basic_auth_str)
        """
            Disable SSL cert verification because Prime uses a cert signed by a not well known CA
        """
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
        """
            Format credentials to fit with Primes Basic Auth
            https://<ip/name_to_prime>/webacs/api/v1/?id=authentication-doc
        """
        

    def prime(self,URL):
        #   get data
        req = request.Request(URL)
        req.add_header("Authorization", "Basic %s" % self.base64string.decode())   
        query = request.urlopen(req, context=self.ssl_context)
        HTTPcode = query.getcode()
        return query

class LoginSwitch():
    def __init__(self, switchdetails, port_ranges):
        self.summary  = {}
        self.ports = []
        #   log into switch
        
        self.connection = ConnectHandler(**switchdetails)
        self.port_ranges = port_ranges.split(',') # separate different ranges from each other
        for i in self.port_ranges:
            if len(i.split('-')) == 2:
                from_= int(i.split('-')[0]) # from number 1 
                to =  int(i.split('-')[1]) + 1  # to number 25
                if to > 49: # No more than 48 ports exist on the prepp swithes (Cisco Catalyst 3650)
                    print('Port range is to long; cannot exceed 48')
                a = [n for n in range(from_, to)] # 1,2,3,4,5,6 etc.
            elif len(i.split('-')) == 1:
                a = [i]
            #   Remove the nesting in order to return one single list
            self.ports += a
        self.ports = ['Gi1/0/{}'.format(i) for i in sorted([x for x in self.ports])] #  add interfacetype
        for interface in self.ports:
            self.summary[interface] = {
                'mac':'',
                'serial':''
            }

    def mac_address_table(self):
        mac_regex = re.compile(r'([0-9a-z]{4}.[0-9a-z]{4}.[0-9a-z]{4})\s+\w+')
        #   then return mac address table for a given switch as json
        #   (only look at active ports)
        for interface in self.summary.keys():
            table = self.connection.send_command("sh mac address-table interface %s" % (interface))
            mac = re.findall(mac_regex, table)[0]
            mac = ''.join(mac.split('.'))
            mac = ':'.join([mac[i:i+2] for i in range(0, len(mac), 2)])
            self.summary[interface]['mac'] = mac
        return self.summary

if __name__ == "__main__":
    def parse(data):
        # just return the serial number seen in the given access point details
        json_data = json.load(data)
        return json_data['queryResponse']['entity'][0]['accessPointDetailsDTO']['serialNumber']

    # global variables
    #   These can be set to static (hardcoded) values in order to prevent a prompt
    parser = argparse.ArgumentParser()
    parser.add_argument("Username", help="Username for Cisco Prime login portal, e.g. kalle1")
    parser.add_argument("Password", help="Password for Cisco Prime login portal, e.g. anka2")
    parser.add_argument("TACACSUsername", help="Username for TACACS, e.g. karl3")
    parser.add_argument("TACACSPassword", help=" Password for TACACS, e.g. alfred4")
    parser.add_argument("Switch", help="switchHostname/IP, can be DN/FQDN or IP")
    parser.add_argument("PortRange", help="Port range given in numbers separated with a hyphen (several ranges are seperated with use of a comma) e.g. 1-25,28-32")
    args = parser.parse_args()

    switchdetails = {
            'host':args.Switch,
            'device_type':'cisco_ios',
            'username':args.TACACSUsername,
            'password':args.TACACSPassword
    }

    gather = LoginSwitch(switchdetails, args.PortRange)
    summary = gather.mac_address_table()
    
    for k,v in summary.items():
        mac = v['mac']
        serial = v['serial']
        get = Login(args.Username, args.Password) # login to prime
        print('On %s, hold on...' % (mac))
        response = get.prime('https://<ip/name_to_prime>/webacs/api/v3/data/AccessPointDetails.json?.full=true&ethernetMac=%22{}%22'.format(mac))
        sleep(1)    # prevent http 503
        serial = parse(response)
        summary[k]['serial'] = serial
    pprint(summary)
    print('Done.')
