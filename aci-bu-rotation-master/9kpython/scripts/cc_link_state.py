#################################################
#
#      File:   cc_link_state.py
#      Name:   Parag Deshpande
#
#       Description: Link state consistency checker
#  
#
#
# Copyright (c) 1985-2013 by cisco Systems, Inc.
# All rights reserved.
#
#################################################

from onxos import *
import nxos_utils

def validate_link_state(_ifindexList = None, _ifNameList = None, slot = 1):                    
    try:
        if _ifNameList == None:
            print "Found no interfaces to validate."
            return
        cmd = "slot " + str(slot) + " debug hardware internal nsa show mac status"
        cmd_lines = None
        ns_cmd_output = 0
        ns_port_macn = 'MACN '
        ns_hw_link_state = 0

        ok = []                                                                      
        nok = []                                                                      
        print "Link State Checks: Link state only"
        for name in _ifNameList:                                                    
            if "." in name:
                continue

            i = Nxos.Interface(name)                                  

            if (i.ns_port != 255):
                if (ns_cmd_output != 1):
                    cmd_out_raw = nxos_utils.runVshCmd(cmd)
                    cmd_lines = cmd_out_raw.split("\n")
                    ns_cmd_output = 1

                macn = ns_port_macn + str(i.ns_port).rjust(2)
                for cmd_line in cmd_lines:
                    if (cmd_line.find(macn) > 0):
                        if (cmd_line.find("Link Up")>1):
                            ns_hw_link_state = 1
                        else:
                            ns_hw_link_state = 0 

                        if ( ns_hw_link_state == i.get_sw_link_state()):
                            ok.append(i)
                        else:
                            nok.append(i)
                        break
                continue


            s = i.validate_link_state()                                             
            if s == 0:                                                    
                ok.append(i)                                               
            else:    
                nok.append(i)                                               

        if len(nok) == 0:
            print "Consistency Check: PASSED"
            py_syslog(1, "CC_LINK_STATE: Consistency Check: PASSED")
        else:
            print "Consistency Check: FAILED"
            py_syslog(1, "CC_LINK_STATE: Consistency Check: FAILED")
            
        if len(ok) > 0:                                                              
            print "No inconsistencies found for:"
            for i in ok:                                                             
                print "  ", i.longName                                              

        if len(nok) > 0:                                                                       
            print "Inconsistencies found for following interfaces:"                
            for i in nok:                                                             
                print "  ", i.longName                                              
    except Exception, err:
        print "Consistency checker had a problem:", err
        py_syslog(1, "CC_LINK_STATE: Consistency Check: ABORTED. Please retry!")

