#################################################
#TAGS:'module failure','offline','failed','module', 'module insertion delays', 'slow bootup', 'reload'
#
#      File:   module.py
#      Name:   Parag Deshpande
#
#
# Copyright (c) 1985-2013 by cisco Systems, Inc.
# All rights reserved.
#
#Functions: ['debug_module_failure']
#Brief Description: 'Helps identify module failure reason.'
#
#################################################


import onxos
import nxos_utils
from operator import itemgetter

"""
Module.py exports following function for detecting module failures:
  Func:
    debug_module_failure(_slot)
  Usage:
    debug_module_failure(2)
  Description:
    Goes thru module/ifmgr/vmm/ethpm module event history and returns all the failures found.
"""

def debug_module_reload_delays(_slot, _delay_in_seconds = 1):
    """
    Usage: debug_module_reload_delays(2, _delay_in_seconds = 1)
    Description: Lists delays in module reload.
                 It looks at event history of LCM, IFMGR, VMM, ETHPM
                 Input: module number as seen in show module and delay in seconds.
    """
    eh = "event-history module " + str(_slot)
    fltr = ""
    mcmd_pfx = "show module internal " + eh + fltr
    ifcmd_pfx = "show system internal im " + eh + fltr
    vmcmd_pfx = "show system internal vmm " + eh + fltr
    ethcmd_pfx = "show system internal ethpm " + eh + fltr
                  
    cmds = []     
    cmds.append(fltr)
    cmds.append(mcmd_pfx)
    cmds.append(vmcmd_pfx)
    cmds.append(ethcmd_pfx)
    all = []
    slow = []
    once = False
    id = ''
    for cmd in cmds:
        id = '>>' + id
        out = nxos_utils.cli_ex(cmd)
        obj = nxos_utils.createEventHistoryTableObject(out)
              
        for esqs in obj.table:
            start_time = None
            last_seq = None
            for seq in esqs:
               if 'TIME' not in seq.keys():
                    continue

               if start_time == None:
                   start_time = seq['TIME']

               y = seq['TIME'] - start_time
               
               if y.seconds > _delay_in_seconds:
                   slow.append((id, seq))

                   if last_seq is not None:
                       slow.append((id, last_seq))
               
               start_time = seq['TIME']
               last_seq = seq


    newlist = sorted(slow, key=lambda (id, st): st['TIME'])

    print "Found following failures for module:%d"%_slot
    cnt = 1                                  
    for (id, i) in newlist:                      
            print "  ", id, "Delays %d)"%cnt                 
            cnt = cnt + 1                              
            for key in i.keys():                          
                print "   ", id, key, ":", i[key]


def debug_module_failure(_slot):
    """
    Usage: debug_module_failure(2)
    Description: Finds out all failures during module reload. 
                 It looks at event history of LCM, IFMGR, VMM, ETHPM
                 Input is the module number as seen in show module.
    """
    eh = "event-history module " + str(_slot)
    fltr = ""
    mcmd_pfx = "show module internal " + eh + fltr
    ifcmd_pfx = "show system internal im " + eh + fltr
    vmcmd_pfx = "show system internal vmm " + eh + fltr
    ethcmd_pfx = "show system internal ethpm " + eh + fltr
                  
    cmds = []     
    cmds.append(fltr)
    cmds.append(mcmd_pfx)
    cmds.append(vmcmd_pfx)
    cmds.append(ethcmd_pfx)
    all = []
    once = False
    id = ''
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


    newlist = sorted(all, key=lambda (id, st): st['TIME'])


    print "Found following failures for module:%d"%_slot
    cnt = 1                                  
    for (id, i) in newlist:                      
        if i['Ret'] != 'SUCCESS':                 
            print "  ", id, "Failure %d)"%cnt                 
            cnt = cnt + 1                              
            for key in i.keys():                          
                print "   ", key, ":", i[key]
