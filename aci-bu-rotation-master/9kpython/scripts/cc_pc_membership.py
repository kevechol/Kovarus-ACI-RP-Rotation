#################################################
#
#      File:   cc_pc_membership.py
#      Name:   Parag Deshpande
#
#       Description: Port channel membership consistency checker
#  
#
#
# Copyright (c) 1985-2015 by cisco Systems, Inc.
# All rights reserved.
#
#################################################
import pprint
import sys
import signal
import pprint



def ctrlc_handler(signal, frame):
   # At this point stdout might be closed. 
   # We need to close both stderr and stdout 
   # to avoid getting a sys.excepthook error 
   # from all the subprocesses
   sys.stderr.write("\nConsistency checker gracefully interrupted.")
   sys.stdout.flush()
   try:
      sys.stdout.close()
   except: 
      pass
   try:
      sys.stderr.close()
   except:
      pass
   sys.exit(0)

from onxos import *                                    
import nxos_utils
def validate_pc_membership(_ifIndexes, _ifNames):                  
    signal.signal(signal.SIGINT, ctrlc_handler)
    try:
        nokList = []
        okList = []
        asic_type = nxos_utils.get_asic_type()
        if asic_type is 'dav' or asic_type is 'lac':
            print "Checks: Pif, vifstate, localmultipath, ucpcconfig and ucpcmember tables."
        else :    
            print "Checks: Trunk group and trunk membership table."
        mods = Nxos.Module.getOnlineFLCModules()

        nok = {}                                                  
        ok = {}                                                  
        notsup = []

        #Software to hardware mapping.
        for name in _ifNames:                                        

            if "." in name:
                continue

            pc = Nxos.Interface(name, _modList = mods)                                
            pcName = pc.longName
            fail = False
            if pc.fex == True:
                notsup.append(pc)
                continue


            #walk thru port channel members (sw state)
            for mem in pc.members:
                if mem.fex == True:
                    break

                for (m, u) in pc.hwIf.get_hwMemberPorts().keys():          
                    #this script is called for T2
                    #skip if unit is non-T2
                    hwDeviceId = HwDeviceId(m, u)
                    if hwDeviceId.getDevId() is not True:
                        continue

                    found = False                                    
                    for (hp, hm) in pc.hwIf.get_hwMemberPorts()[(m, u)]:
                        if mem.hwIf.get_hw_port() == hp and mem.dmod == hm:     
                            found = True                             
                    if found == False:                  
                        if (pcName,m,u) not in nok.keys():     
                            nok[(pcName,m,u)] = []            
                        nok[(pcName, m, u)].append(mem.longName)
                        fail = True
                    else:                               
                        if (pcName,m,u) not in ok.keys():     
                            ok[(pcName, m,u)] = []        
                        ok[(pcName, m, u)].append(mem.longName)

            if fail == True:
                nokList.append((pc, nok))            
                
            if fail == False:
                okList.append((pc, ok))            

        #Hardware to software mapping.
        tc = HwTrunkCollection(mods, _ifIndexes)
        tc.validate_pc_membership(mods, okList, nokList, ok, nok)
    
    except Exception, err:
        print "Consistency checker had a problem:", err
        py_syslog(1, "CC_PC_MEMBERSHIP: Consistency Check: ABORTED. Please retry!")
