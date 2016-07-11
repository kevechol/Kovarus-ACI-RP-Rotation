#################################################
#TAGS:'error disable','failed','failure','interface','err-dis', 'interface delays', 'sequence delays', 'delay'
#
#      File:   interface.py
#      Name:   Parag Deshpande
#
#
# Copyright (c) 1985-2013 by cisco Systems, Inc.
# All rights reserved.
#
#Functions: ['debug_interface_error_disable']
#Brief Description: 'Helps identify interface error disable reason.'
#
#################################################


import nxos_utils
from operator import itemgetter

def debug_interface_delays(_ifName, _port_channel_member = False, _lacp = False, _delay_in_seconds = 1):
    """
    Usage:  debug_interface_delays("Ethernet2/1", _port_channel_member = False, _lacp = False, _delay_in_seconds = 1)
            debug_interface_delays("Port-channel1", _port_channel_member = False, _lacp = False, _delay_in_seconds = 1)
    Description: Finds delays in interface bringup or bring down.
                 Looks at ETHPM, PCM(if bundle or bundle member), LACP(if lacp enabled)
    """
    eh = "event-history interface " + (_ifName)
    fltr = ""
    ethcmd_pfx = "show system internal ethpm " + eh + fltr
    pcmcmd_pfx = "show port-channel internal " + eh + fltr
    lacpcmd_pfx = "show lacp internal " + eh + fltr
                  
    cmds = []     
    cmds.append(ethcmd_pfx)
    if "hannel" in _ifName or _port_channel_member == True:
        cmds.append(pcmcmd_pfx)

    if "thernet" in _ifName and _lacp == True:
        cmd.append(lacpcmd_pfx)

    all = []
    slow = []
    once = False
    last_seq = None
    id = ''
    for cmd in cmds:
        id = '>>' + id
        out = nxos_utils.cli_ex(cmd)
        obj = nxos_utils.createEventHistoryTableObject(out)

        for esqs in obj.table:
            start_time = 0
            last_seq = None
            for seq in esqs:
               if 'TIME' not in seq.keys():
                    continue

               if start_time == 0:
                   start_time = seq['TIME']
               
               if (seq['TIME'] - start_time).total_seconds() > _delay_in_seconds:
                   slow.append((id, seq))

                   if last_seq is not None:
                       slow.append((id, last_seq))
               
               start_time = seq['TIME']
               last_seq = seq


    newlist = sorted(slow, key=lambda (id,st): st['TIME'])


    print "Found following failures for interface:%s"%_ifName
    cnt = 1                                  
    for (id, i) in newlist:                      
            print "  ", id, "Delays %d)"%cnt                 
            cnt = cnt + 1                              
            for key in i.keys():                          
                print "   ", id, key, ":", i[key]
    return

def debug_interface_error_disable(_ifName, _port_channel_member = False, _lacp = False):
    """
    Usage:  debug_interface_error_disable("Ethernet2/1", _port_channel_member = False, _lacp = False)
            debug_interface_error_disable("Port-channel1", _port_channel_member = False, _lacp = False)
    Description: Finds errors in interface bringup or bring down.
                 Looks at ETHPM, PCM(if bundle or bundle member), LACP(if lacp enabled)
    """
    eh = "event-history interface " + (_ifName)
    fltr = ""
    ethcmd_pfx = "show system internal ethpm " + eh + fltr
    pcmcmd_pfx = "show port-channel internal " + eh + fltr
    lacpcmd_pfx = "show lacp internal " + eh + fltr
                  
    cmds = []     
    cmds.append(ethcmd_pfx)
    if "channel" in _ifName or _port_channel_member == True:
        cmds.append(pcmcmd_pfx)

    if "thernet" in _ifName and _lacp == True:
        cmd.append(lacpcmd_pfx)

    all = []
    id = ''
    once = False
    for cmd in cmds:
        id = '>>' + id
        out = nxos_utils.cli_ex(cmd)
        obj = nxos_utils.createEventHistoryTableObject(out)

        for esqs in obj.table:
            for seq in esqs:
               #if 'ethpm' in cmd and 'Ret' in seq.keys() and once == False:
               #    seq['Ret'] = 'Failed due to timeout'
               #    once = True

               if 'TIME' in seq.keys():
                   all.append((id, seq))


    newlist = sorted(all, key=lambda (id,st): st['TIME'])


    print "Found following failures for interface:%s"%_ifName
    cnt = 1                                  
    for (id, i) in newlist:                      
        if i['Ret'] != 'SUCCESS':                 
            print "  ", id, "Failure %d)"%cnt                 
            cnt = cnt + 1                              
            for key in i.keys():                          
                print "   ", id, key, ":", i[key]
