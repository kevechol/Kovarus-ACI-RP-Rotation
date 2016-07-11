#/********************************************************************
 #*
 #*      File:   pyshow.c
 #*      Name:   Parag Deshpande
 #*
 #*       Description:
 #*        This file contains the cli call back functions for consistency checker.
 #*
 #* Copyright (c) 1985-2004, 2009, 2015 by cisco Systems, Inc.
 #* All rights reserved.
 #*
 #*
 #*********************************************************************
 #*/

from onxos import *
def show_port_mappings(_ifindexList = None, _ifNameList = None):                                                             
                                                                                                                             
   try:
    if _ifNameList == None:                                                                                   
        print "Found no interfaces to validate."                                
        return                                  
                       
    ok = []         
                                                    
    nok = []                                        

    print ""                    
    asic_type = get_asic_type()
    if asic_type is 'lac' or asic_type is 'dav':
        print "-------------------------------------------------------------------"
        print "%-10s %-8s %-4s %-4s %-5s %-5s %-5s %-5s %-5s %-5s"%("Name", "Ifindex", "Smod", "Unit", "HPort",
                                                                    "FPort", "NPort", "VPort", "Slice", "SPort")
        print "-------------------------------------------------------------------"
    # Broadcom is the default 
    else:
        print "-------------------------------------------------------------"                                             
        print "%-10s %-8s %-4s %-4s %-5s %-5s %-5s %-5s %-5s"%("Name", "Ifindex", "Smod", "Unit", "HPort",
                                                               "HName", "FPort", "NPort", "VPort")
        print "-------------------------------------------------------------"                              

    for name in _ifNameList:                                                    
        if "." in name:     
            continue   
                    
        if "Eth" not in name and "nnel" not in name:
            continue                                
                    
        i = Nxos.Interface(name)
        vp = -1
        if "nnel" in name:
            vp = i.hw_port + 1

        if asic_type is 'lac' or asic_type is 'dav':
            output = "%-10s %-8x %-4d %-4d %-5d %-5d %-5d %-5d %-5d %-5d"
            print output % (i.shortName, i.ifindex,i.dmod, i.unit, i.hw_port, i.ns_port, 
                                    i.nxos_port, vp, i.slice_num, i.port_on_slice)
        # Broadcom is the default 
        else:
            output = "%-10s %-8x %-4d %-4d %-5d %-5s %-5d %-5d %-5d"
            print output % (i.shortName, i.ifindex,i.dmod, i.unit, i.hw_port,
                            i.hwIf.obj.hw_name, i.ns_port, i.nxos_port, vp )

   except:
      print ""

