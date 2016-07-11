#!/usr/bin/env python

'''

    Tool used in response to potential security violation logged by the firewall
    This tool is meant to be executed by some other tool like stackstorm or splunk based on an event

    Tool makes a couple assumptions:
        1. There's an SVI in the VLAN with the offending machine
        2. The offending machine is using the switch as it's default gateway (so we can get the MAC from the ARP table)
        3. It's not a virtual machine on the other side of an ESXi host. This would most definitely work better
           with ISE or RADIUS or something.

'''

import xmltodict
from device import Device
import argparse
import string
import random

def getargs():
    parser = argparse.ArgumentParser(description='A handy tool to identify the forwarding path of a given flow on a specific interface')
    parser.add_argument('--switch',
                        required=True,
                        action='store',
                        help='target device to identify forwarding path')
    parser.add_argument('-s', '--source',
                        required=True,
                        action='store',
                        help='source of the traffic')
    parser.add_argument('-u', '--user',
                        required=True,
                        action='store',
                        help='username on the device')
    parser.add_argument('-p', '--password',
                        required=True,
                        action='store',
                        help='password of the device')
    args = parser.parse_args()
    return args

def get_mac(sw):

    ip = '10.1.4.11'

    result = sw.show('show ip arp')
    arp_table = xmltodict.parse(result[1])
    hostdata = {}

    for i in arp_table['ins_api']['outputs']['output']['body']['TABLE_vrf']['ROW_vrf']['TABLE_adj']['ROW_adj']:
        if i['ip-addr-out'] == ip:
            hostdata['ip'] = i['ip-addr-out']
            hostdata['mac'] = i['mac']
            hostdata['intf-out'] = i['intf-out']

    cmd = 'show mac address-table address %s' % hostdata['mac']

    mac = sw.show(cmd)
    locate_interface = xmltodict.parse(mac[1])

    # TODO need error handling here in case the MAC address ages out of the table
    hostdata['disp_port'] = locate_interface['ins_api']['outputs']['output']['body']['TABLE_mac_address']['ROW_mac_address']['disp_port']

    return hostdata

def id_generator(size=5, chars=string.ascii_lowercase + string.digits):
    return ''.join(random.choice(chars) for _ in range (size))

def quarantine(sw, **kwargs):

    # TODO take in an IP address then go hunt it down in mac tables
    # TODO set new VLAN
    # TODO create new vlan interface and place into quarantine vrf using randomly generated ID
    # TODO redo command set with a list and iterate through via for loop

    hostdata = get_mac(sw)

    ip = hostdata['ip']
    vlan_id = '14'
    default_gw = '10.1.4.1'
    target_vlan_id = '2501'
    q_interface = hostdata['disp_port']

    vrf_id = 'quarantine-' + id_generator()
    create_vrf = 'conf t ;vrf context %s' % vrf_id

    # TODO need to check if the vrf exists before creating it at some point in the future
    check_vrf = 'show vrf quarantine-%s' % vrf_id

    result = sw.conf(create_vrf)

    create_vlan = 'conf t ;vlan %s ;name %s' % (target_vlan_id, vrf_id)


    # TODO Get the old VLAN IP here
    # TODO should sort out HSRP as needed too
    create_l3 = 'conf t ;int vlan %s ;vrf member %s ;ip address %s ;no shut' % (target_vlan_id, vrf_id, default_gw)

    move_interface = 'conf t ;int %s ;switchport mode acc ;switchport acc vlan %s ;no shut' % (q_interface, target_vlan_id)

    message = 'Host with IP of %s isolated in VRF %s on VLAN %s' % (ip, vrf_id, vlan_id)

    return message

def main():
    '''

    Main loop to retrieve data

    :return:
    '''
    # args = getargs()
    #
    # username = args.user
    #
    # if not username:
    #     username = raw_input("Device Username:")

    # password = getpass.getpass('Device password:')

    # switch = Device(ip=args.switch, username=username, password=password)
    switch = Device(ip='10.1.0.2', username='svc.network', password='!Passw0rd')
    switch.open()

    print quarantine(switch)

if __name__ == '__main__':
    main()
