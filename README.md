=====
Cisco Prime scripts

This repo contians various scripts which interact the the Cisco Prime API. 
The main focus of them all is management of WLAN devices. However, code such as
basic authentication (adding a base64 string "username"+"password" to the HTTP header) can be gathered from this repo.

===
copy-and-replace: Automation of csv file creation used for bulk copy and replace in Cisco prime

This script basically generates a csv file used for the bulk copy-and-replace service in Prime.
By looking up the hostnames of existing access-points the script gathers the correct Radio Mac address.
It then logs into a switch which has new access-points connected to it and proceeds to gather the Radio Mac addresses as well.
The outcome is a .csv file with the following structure:
```
HostName,OldBaseRadioAddress,Hostname,NewBaseRadioAddress
```

==
Requirements:
All involved accesspoints must be seen in Prime
python3, netmiko, urllib.request, win32clipboard

=
Troubleshooting

The script does handle many errors. But most often the problem lies within Prime.
When new access points are connected to a switch it usually takes an undefined amount of time before
their appear in Prime. The discovery process is however faster if you manually sync your WLC.


