Cisco Prime scripts
=====

This repo contians various scripts which interact the the Cisco Prime API. 
The main focus of them all is management of WLAN devices. However, code such as
basic authentication (adding a base64 string "username"+"password" to the HTTP header) can be gathered from this repo.

copy-and-replace: Automation of csv file creation used for bulk copy and replace in Cisco prime
==
This script basically generates a csv file used for the bulk copy-and-replace service in Prime.
By looking up the hostnames of existing access-points the script gathers the correct Radio Mac address.
It then logs into a switch which has new access-points connected to it and proceeds to gather the Radio Mac addresses as well.
The outcome is a .csv file with the following structure:
```
HostName,OldBaseRadioAddress,Hostname,NewBaseRadioAddress
```


**Requirements:**

All involved accesspoints must be seen in Prime.

Python version 3.x.

python modules: __netmiko, urllib.request, win32clipboard, argparse__


**Troubleshooting**

Many errors can occur and are mostly handled by argparse and flow control. Besides those fixes, one common problem lies within Prime.
When new access points are connected to a switch it usually takes an undefined amount of time before
their appear in Prime. The discovery process is however faster if you manually sync your WLC.

mac to serial: Translate the mac addresses of mac address table to serial numbers
==
This script is mainly used for updating warehouse statuses. Instead of manually searching for the serial numbers for new access points, you can now just execute this script and specifiy a port range on a switch. The script will then translate the mac addresses to serial numbers by asking the Prime API.

**Requirements:**

All involved accesspoints must be seen in Prime.

Python version 3.x.

python modules: __netmiko, urllib.request, argparse__

**Troubleshooting**
This script does not have any error handling, most errors can be figured out by the http return codes. The important thing is that prime has synced with the corresponsing WLC. Otherwise some access points are not found.
