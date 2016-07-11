#!/usr/bin/env python
'''

    Basic script to figure out what path a network flow takes via a given port-channel. Script will securely prompt
    for password.

    Example:
        python get-po-flow.py --switch 10.1.0.2 --interface po1 --source 10.1.32.11 --destination 10.1.32.45 --user svc.network

    returns: Traffic flowing from 10.1.32.11 to 10.1.32.45 will use physical interface Ethernet1/18

'''
# TODO eventually add support to crawl through network using CDP or LLDP hints

import xmltodict
from device import Device
import argparse
import getpass

def getargs():
    parser = argparse.ArgumentParser(description='A handy tool to identify the forwarding path of a given flow on a specific interface')
    parser.add_argument('--switch',
                        required=True,
                        action='store',
                        help='target device to identify forwarding path')
    parser.add_argument('-i', '--interface',
                        required=True,
                        action='store',
                        help='outbound portchannel interface')
    parser.add_argument('-s', '--source',
                        required=True,
                        action='store',
                        help='source of the traffic')
    parser.add_argument('-d', '--destination',
                        required=True,
                        action='store',
                        help='destination of the traffic')
    parser.add_argument('-u', '--user',
                        required=True,
                        action='store',
                        help='username on the device')
    args = parser.parse_args()
    return args

def get_lbalgo(sw):
    '''

    Determines actual load balancing algorithm in use on the physical device

    :param sw: Object containing switch connection parameters
    :return: ipv4 load balancing algorithm in use on the device

    '''

    #TODO response seems to differ depending on platform. Possible our 5ks are on too old of code?

    result = sw.show('show port-channel load-balance', )
    ipv4_lbalgo = xmltodict.parse(result[1])

    return ipv4_lbalgo['ins_api']['outputs']['output']['body']['ipv4-sel'][0]

def get_forwardingpath(sw, **kwargs):
    '''

    Takes in a series of keywords and checks which path the flow will take based on LB algorithm

    :param sw: Object containing switch connection parameters
    :param kwargs: keywords that are used as inputs to the device API
    :return: A string that will represent the physical device the specified flow will take


    '''
    # TODO add more load balancing algorithms here. Have limited support on NXOS simulator
    # TODO seems like NXOS simulator doesn't behave as expected so test this on real 9k hardware

    if kwargs['lbalgo'] == 'ip':
        i = kwargs['interface']
        s = kwargs['src']
        d = kwargs['dst']
        endpoints = 'show port-channel load-balance forwarding-path interface %s src-ip %s dst-ip %s' % (i, s, d)

        result = sw.show(endpoints)
        forwarding_path = xmltodict.parse(result[1])
        return forwarding_path['ins_api']['outputs']['output']['body']['outgoing-port-id']['port']


def main():
    '''

    Main loop to retrieve data

    :return:
    '''
    args = getargs()

    username = args.user

    if not username:
        username = raw_input("Device Username:")

    password = getpass.getpass('Device password:')

    switch = Device(ip=args.switch, username=username, password=password)

    switch.open()

    result = get_forwardingpath(switch,
                                interface=args.interface,
                                src=args.source,
                                dst=args.destination,
                                lbalgo='ip' )

    print 'Traffic flowing from %s to %s will use physical interface %s' % (args.source, args.destination, result)

if __name__ == '__main__':
    main()
