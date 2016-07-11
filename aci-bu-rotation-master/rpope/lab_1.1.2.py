#!/usr/bin/env python

router1 = {'os_version':'3.1.1','hostname':'nyc_router1','model':'nexus 9396','domain':'cisco.com','mgmt_ip':'10.1.50.11'}
router2 = dict( os_version='3.2.1', hostname='rtp_router2',model='nexus 9396',domain='cisco.com', mgmt_ip='10.1.50.12')
router3 = dict( os_version='3.1.1', hostname='ROUTER3',model='nexus 9504', domain='lab.cisco.com', mgmt_ip='10.1.50.13')

def getRouter(rtr):

    if rtr == 'router1':
        return router1
    elif rtr == 'router2':
        return router2
    elif rtr == 'router3':
        return router3


def get_router(hostname):
    router1 = {'os_version':'3.1.1','hostname':'nyc_router1','model':'nexus 9396','domain':'cisco.com','mgmt_ip':'10.1.50.11'}
    router2 = dict( os_version='3.2.1', hostname='rtp_router2',model='nexus 9396', domain='cisco.com', mgmt_ip='10.1.50.12')
    router3 = dict( os_version='3.1.1', hostname='ROUTER3',model='nexus 9504', domain='lab.cisco.com', mgmt_ip='10.1.50.13')

    router_list = [router1, router2, router3]

    for router in router_list:
        if hostname == router['hostname']:
            return router
    return 'No router found.'


test1 = get_router('nyc_router1')
test2 = get_router('router_blob')
test3 = get_router('ROUTER3')

print test1
print test2
print test3


