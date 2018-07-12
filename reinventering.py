#! python

############################ METADATA ########################################
#   Creator: Ben Kooijman (mirakelsvampen)
#   Purpose: automation of csv file creation used for bulk copy and replace in Cisco prime
#   Date of last update:   2018/07/10
#   Developed and tested on Windows 10
#   Free for anyone to use
############################ METADATA ########################################

import os
import re
import json
import sys
import ssl
import time
import base64 # API tells that basic http authentication is used (base64)
import argparse
import itertools
import urllib.request as request

from pprint import pprint
from urllib.error import HTTPError

try: #   Non Python included libraries
    import paramiko
    import win32clipboard
    from netmiko import BaseConnection
except ImportError:
    import subprocess # provides headless interaction for pip installations, which is only needed if the required packages are missing from the client PC
    print(chr(27) + "[2J")  # Clear the screen
    print('Missing some required packages. No worries!\nPerforming a dependency check...')
    
    requirements = ['paramiko', 'pywin32', 'netmiko']
    installed_modules = subprocess.Popen(
            ['pip', 'list', 'installed'],
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
        ).communicate()[0]

    dependencies = re.findall(r'(paramiko[-expect]*|pywin32|netmiko)', installed_modules.decode())

    for package in requirements:
        if package in dependencies: # if the package is allready installed 
            pass
        elif not package in dependencies: # if the package is NOT allready installed
            print('Python package {} not found. Installing with pip...'.format(package))
            subprocess.call(
                ['pip', 'install', '{}'.format(package)]
            )
    print('Dependency check complete... Everything is installed. \n')

class Reinv(): # Class for modular use
    def prime(self, prime_usr, pwd, URL, a):
        basic_auth_str = '{}:{}'.format(prime_usr, pwd)
        basic_auth_str = basic_auth_str.encode()
        """
            Disable SSL cert verification because Prime uses a cert signed by a not well known CA
        """
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        try: 
            """
                Format credentials to fit with Primes Basic Auth
                https://<ip to prime>/webacs/api/v1/?id=authentication-doc

            """
            #   Authentication
            req = request.Request(URL)
            base64string = base64.b64encode(basic_auth_str)
            req.add_header("Authorization", "Basic %s" % base64string.decode())   
            query = request.urlopen(req, context=ssl_context)
            HTTPcode = query.getcode()
            result = query
            
            #   Parsing data returned by prime
            ap_list = []
            json_data = json.load(result)
            try:
                for ap in json_data['queryResponse']['entity']:
                    ap_list.append((ap['radioDetailsDTO']['apName'], ap['radioDetailsDTO']['baseRadioMac']))
                return [ap_ for ap_,_ in itertools.groupby(ap_list)]
            except KeyError:
                return [('ERROR {}'.format(ap), 'not found in prime')]

        except HTTPError as err:    # Error handling
            err = str(err)[11:-2]
            if err ==  '400':
                print('HTTP code 400 Bad Request (Make sure you have the correct APs in your clipboard)')
            elif err ==  '401':
                print('HTTP code 401 Unauthorized')
            elif err ==  '403':
                print('HTTP code 403 Forbidden')
            elif err ==  '404':
                print('HTTP code 404 Not Found')
            elif err ==  '406':
               print('HTTP code 406 Not Acceptable')
            elif err ==  '415':
               print('HTTP code 415 Unsupported Media Type')
            elif err ==  '500':
               print('HTTP code 500 Internal Server Error')
            elif err ==  '502':
               print('HTTP code 502 Bad Gateway')
            elif err ==  '503':
               print('HTTP code 503 Service Unavailable')
            return False

    def switch(self, hostname, username, password):
        #   Find all mac addresses and the associated ports
        mac_reg = re.compile(r'([a-z0-9]{4}\.[a-z0-9]{4}\.[a-z0-9]{4})\s+STATIC\s+(Gi\d+/\d+/\d+)')
        #   Switch connection options:
        switch_details = {
            'device_type':'cisco_ios',
            'host':hostname,
            'username':username,
            'password':password,
        }

        connection = BaseConnection(**switch_details)
        connection.write_channel('sh mac address-table | inc STATIC      Gi\n')
        time.sleep(1) # a short break to offload the connection
        out = connection.read_channel()
        ports = re.findall(mac_reg, out) # retrieve all ports with static MAC addresses
        connection.disconnect()
        ports = [list(x) for x in ports] # covert the tuples from re.findall to lists
        #   Now the interfaces must be sorted in numberical order
        #   Perform buble sorting
        n = len(ports)
        # Traverse through all array elements
        for i in range(n):
            for j in range(0, n-i-1):
                # traverse the array from 0 to n-i-1
                # Swap if the element found is greater
                # than the next element
                if int(ports[j][1][6:]) > int(ports[j+1][1][6:]): # Take the port number from port string (e.g. G1/0/22 = 22)
                    # ye olde switcharoo
                    ports[j][0], ports[j+1][0] = ports[j+1][0], ports[j][0] # switch mac addresses
                    ports[j][1], ports[j+1][1] = ports[j+1][1], ports[j][1] # switch interfaces
        return ports

    def port_range(self, port_ranges):
        """
            Create a set of interfaces from the input 
            the user gives. 1-8 will be transformed into Gi1/0/1, Gi1/0/2, Gi1/0/3 etc.
            Also different port ranges are taken into account. e.g. 1-8,11-21
        """
        ports = []
        port_ranges = port_ranges.split(',') # separate different ranges from each other
        try:
            for i in port_ranges:
                if len(i.split('-')) == 2:
                    try:
                        from_= int(i.split('-')[0]) # from number 1 
                        to =  int(i.split('-')[1]) + 1  # to number 25 (without the increment the range will end on e.g. 24 instead of 25)
                        if to > 49: # No more than 48 ports exist on the prepp swithes (Cisco Catalyst 3650)
                            return 'NonExistentPort'
                    except ValueError:
                        return 'IntFault'
                    a_range = ['Gi1/0/{}'.format(n) for n in range(from_, to)]
                elif len(i.split('-')) == 1:
                    a_range = ['Gi1/0/{}'.format(i)]
                #   Remove the nesting in order to return one single list 
                for port in a_range:
                    ports.append(port)
            return ports
        except IndexError:
            return 'IndexFault'

if __name__ == '__main__': # Start the script here.
    """
        Utilizes the Class Reinv in a modular approach. 
        For ease of use the code below is is written inside the same python file as 
        the reinvestering module itself. But the code below is only utilized if 
        this file is directy interpreted/executed. If the Reinv class is called 
        from another source file then the code below is ignored.

        The following code does the following:
        1. Get old Mac addresses from prime
        2. Get Ethernet mac adresses from switch
        3. Translate ethernet mac addresses to baseRadioMac addresses by asking prime
        4. format data and write to csv file

        the data is written to the csv file in the following manner:
            hostName,oldBaseRadioMac,hostName,newBaseRadioMac
        
    """
    get = Reinv() # init the gathering process

    print(chr(27) + "[2J")  # Start the script by clearing the screen
    
    print('Required dependencies all installed!')
    
    parser = argparse.ArgumentParser()
    parser.add_argument("Username", help="Username for Cisco Prime login portal, e.g. kalle1")
    parser.add_argument("Password", help="Password for Cisco Prime login portal, e.g. anka2")
    parser.add_argument("TACACSUsername", help="Username for TACACS, e.g. karl3")
    parser.add_argument("TACACSPassword", help=" Password for TACACS, e.g. alfred4")
    parser.add_argument("Switch", help="switchHostname/IP, can be DN/FQDN or IP")
    parser.add_argument("PortRange", help="Port range given in numbers separated with a hyphen (several ranges are seperated with use of a comma) e.g. 1-25,28-32")
    args = parser.parse_args()
    prime_usr = args.Username
    prime_pwd = args.Password
    tacacs_usr = args.TACACSUsername
    tacacs_pwd = args.TACACSPassword
    switch_name = args.Switch
    port_ranges=get.port_range(args.PortRange)
    print('\n')

    if port_ranges == 'IntFault':
        print('Invalid port ranges, (MUST be given in NUMBERS)')
        parser.print_help()
        sys.exit()
    elif port_ranges == 'IndexFault':
        print('Invalid port range...')
        parser.print_help()
        sys.exit()
    elif port_ranges == 'NonExistentPort':
        print('Given port range exceeds the number of the 48 physical ports...')

    #   Retrieve clipboard contents
    win32clipboard.OpenClipboard()
    data = win32clipboard.GetClipboardData()
    win32clipboard.CloseClipboard()

    existing_ap = {}
    new_ap = {}
    ap = [line for line in data.split('\r\n') if not line == '']
    if len(ap) > len(port_ranges):
        print('Error: The amount of data found in the clipboad exceeds the amount of specified ports!')
        parser.print_help()
        sys.exit()
    elif len(ap) < len(port_ranges):
        print('Error: The amount of specified ports exceeds the amount of data found in the clipboard!')
        parser.print_help()
        sys.exit()

    sitename = ''.join(i for i in ap[0] if not i.isdigit()) # Create a sitename which is later used for the csv file name

    print('Gathering baseRadioMac addresses for existing Access Points...')
    print('HOSTNAME     |       baseRadioMac')
    for a in ap:
        time.sleep(0.3) # Reduce stress upon Cisco Prime (Fast queries seem to introduce HTTP error 503)
        prime_url = 'https://<ip to prime>/webacs/api/v3/data/RadioDetails.json?.full=true&apName=startsWith({})'.format(a)
        result = get.prime(prime_usr, prime_pwd, prime_url, a)  
        if result == False:
            sys.exit()
        else:
            print('{} => {}'.format(result[0][0], result[0][1]))
            existing_ap[result[0][0]] = result[0][1]
        
    new_ap_ethernet = get.switch(switch_name, tacacs_usr, tacacs_pwd)
    print('\nGathering baseRadioMac addresses for new Access Points connected to switch {}...'.format(switch_name))
    print('HOSTNAME     |       baseRadioMac')
    if new_ap_ethernet == []:
        print(chr(27) + "[2J")
        print('No AP connected to switch...')
        sys.exit()
    
    try:
        for port in new_ap_ethernet:
            time.sleep(0.3) # Reduce stress upon Cisco Prime (Fast queries seem to introduce HTTP error 503)
            ethernet, interface = port # e.g. FF:FF:FF:00:11:22, Gi1/0/22
            if interface in port_ranges:
            #   format "7079.b3fd.0960" into "70:79:b3:fd:09:60"
                ethernet = ''.join(ethernet.split('.'))
                ethernet = ':'.join([ethernet[i:i+2] for i in range(0, len(ethernet), 2)])
                prime_url = 'https:<ip to prime>webacs/api/v3/data/RadioDetails.json?.full=true&ethernetMac=startsWith(%22{}%22)'.format(ethernet)
                result = get.prime(prime_usr, prime_pwd, prime_url, a='placehoder') # since the "a" argument is required by the called function, we'll pass a placeholer here
                if result == False:
                    sys.exit()
                else:
                    print('{} => {}'.format(result[0][0], result[0][1]))
                    new_ap[result[0][1]] = interface
            else:
                pass # ignore interface if it is not found in the list of specified physical ports
            
            if new_ap == {}: #  if Empty, then no AP where found on any switchports
                print('No AP found on any of the given switchports.')
                sys.exit()

    except TypeError:
        print(chr(27) + "[2J")  # Clear the screen
        print('Switch initialization failed. Check the parameter!')
        sys.exit()
    """
        Write the results to a csv file
    """
    print('\n') # just some separation for easier reading
    fh = open('{}.csv'.format(sitename), 'w')
    print('Dyno etiquettes layout:')
    for (hostname, old_mac), (new_mac, port_) in zip(existing_ap.items(), new_ap.items()):
        print('{} => {}'.format(hostname, port_))
        fh.write('{},{},{},{}\n'.format(hostname, old_mac, hostname, new_mac))
    
    print('\n')

    for files in os.listdir():
        if files == '{}.csv'.format(sitename):
            path = os.path.abspath('{}.csv'.format(sitename))
            print('{}.csv is found at location: {}'.format(sitename, path))

