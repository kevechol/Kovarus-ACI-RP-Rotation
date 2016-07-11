#################################################
#
#      File:   cc_vlan_stp_state.py
#      Name:   Parag Deshpande
#
#       Description: STP State consistency checker
#  
#
#
# Copyright (c) 1985-2013 by cisco Systems, Inc.
# All rights reserved.
#
#################################################


from onxos import *
def validate_vlan_stp_state(_vlanList, _vlanNameList = ""):
    try:
        ok = []                                                                      
        nok = []                                                                      
        okList = []
        nokList = []
        donotexistList = []
        print "Checks: Spanning tree state"
        for vlan in _vlanList:                                                    
            vdict = getVlanDict(str(vlan))                     
            if len(vdict) == 0:                                
               print "VLAN", vlan, "does not exist"
               donotexistList.append(vlan)            
               return                                 
            v = Nxos.Vlan(vlan) 
            (ok, nok) = v.validate_vlan_spanning_tree_state()                                             

            if len(ok) > 0:                                                 
                okList.append((v,ok))
                                                                            
            if len(nok) > 0:                                                
                nokList.append((v,nok))

        if len(nokList) > 0:
            print "Consistency Check: FAILED"
            py_syslog(1, "CC_VLAN_STP_STATE: Consistency Check: FAILED")
        else:
            print "Consistency Check: PASSED"
            py_syslog(1, "CC_VLAN_STP_STATE: Consistency Check: PASSED")


        for (v,o) in okList:
                print " Vlan:%d, Hardware state consistent for:"%v.vlan
                for i in o:                                                
                    print "  ", i.longName                                  


        for (v,n) in nokList:
                print " Vlan:%d, Hardware state inconsistent for:"%v.vlan
                for i in n:                                               
                    print "  ", i.longName 
 
    except Exception, err:
        print "Consistency checker had a problem:", err
        py_syslog(1, "CC_VLAN_STP_STATE: Consistency Check: ABORTED. Please retry!")
