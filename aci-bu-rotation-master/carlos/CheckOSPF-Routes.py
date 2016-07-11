import requests
import json


url='http://10.1.0.2/ins'
switchuser='svc.network'
switchpassword='!Passw0rd'

myheaders={'content-type':'application/json'}
payload={
  "ins_api": {
    "version": "1.2",
    "type": "cli_show",
    "chunk": "0",
    "sid": "1",
    "input": "show ip route",
    "output_format": "json"
  }
}
response = requests.post(url,data=json.dumps(payload), headers=myheaders,auth=(switchuser,switchpassword)).json()

for x in response['ins_api']['outputs']['output']['body']['TABLE_vrf']['ROW_vrf']['TABLE_addrf']['ROW_addrf']['TABLE_prefix']['ROW_prefix']:
    for y in x['TABLE_path']['ROW_path']:
            if y['clientname'] == 'ospf-1':
                  print y['ipnexthop'] + ' ' + x['ifname'] + ' ' + x['uptime'] + ' ' + str(x['pref']) + ' ' + str(x['metric']) + ' ' + x['clientname'] + ' ' + x['type']