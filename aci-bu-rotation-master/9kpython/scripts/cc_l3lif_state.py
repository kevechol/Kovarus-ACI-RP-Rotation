#################################################
#
#      File:   cc_l3lif_state.py
#      Name:
#
#       Description: L3Lif consistency checker
#  
#
#
# Copyright (c) 1985-2015 by cisco Systems, Inc.
# All rights reserved.
#
#################################################


from onxos import *

def validateL3lifState(_ifindexList = None, _ifNameList = None):
    try:
        ok = []
        nok = []
        is_ns_port = 0
        print "L3 LIF Checks: L3 Vlan, CML Flags, IPv4 Enable"
        if _ifNameList is None:
            print "No interfaces found. Please check if module is present or online."
            return
        for name in _ifNameList:
            if "." in name:
                continue

            i = Nxos.Interface(name)
            if (i.ns_port != 255):
                is_ns_port = 1
                continue

            if i.swLayer == 2:
                continue

            if i.bundle_index != 0:
                ##Port is member port of Port-channel, continue
                continue

            try:
                if i.get_sw_link_state() == 0 and i.hwIf.get_hw_link_state() == 0:
                    continue
            except AttributeError:
                ##For down ports, hwIf returns NoneType, continue
                ## here to avoid error
                continue
            
            (rc, failures)  = i.validateL3LifSettings()
            if ( rc == True ):
                ok.append((i, failures))
            else:
                nok.append((i, failures))

        if len(nok) == 0:
            print "Consistency Check: PASSED"
            py_syslog(1, "CC_L3_LIF: Consistency Check: PASSED")
        else:
            print "Consistency Check: FAILED"
            py_syslog(1, "CC_L3_LIF: Consistency Check: FAILED")
            
        if ( len(ok) > 0 ):
            print "No inconsistencies found for:"
            for (i,fs) in ok:
                print "  ", i.longName

        if ( len(nok) > 0 ):
            print "Inconsistencies found for following interfaces:"
            for (i,fs) in nok:
                print "  ", i.longName
                for f in fs:
                    print "     ", f

        if (is_ns_port == 1):
            print("\nNote: CC not run on Expansion Module ports")

    except KeyError, err:
        print "Consistency checker had a problem:", err
        py_syslog(1, "CC_L3_LIF: Consistency Check: ABORTED. Please retry!")
