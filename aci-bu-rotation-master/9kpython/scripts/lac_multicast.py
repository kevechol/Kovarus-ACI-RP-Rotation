#* ---------------------------------------------------------------
# *      File : lac_multicast.py 
# *      Name : Nakul Shah 
# * 
# *      Description: This file contains script to dump lac hw tables. 
# *
# *      Copyright (c) 2015 by cisco Systems, Inc.
# *      All rights reserved.
# *
# *       ALL RIGHTS RESERVED. THESE SOURCE FILES ARE THE SOLE PROPERTY
# *       OF NUOVA SYTEMS, Inc. AND CONTAIN CONFIDENTIAL  AND PROPRIETARY
# *       INFORMATION.  REPRODUCTION OR DUPLICATION BY ANY MEANS OF ANY
# *       PORTION OF THIS SOFTWARE WITHOUT PRIOR WRITTEN CONSENT OF
# *       NUOVA SYSTEMS, Inc. IS STRICTLY PROHIBITED.
# *
# * $Id: $
# * $Source: $
# * $Author: $
# * ---------------------------------------------------------------
# ********************************************************************/

import nxos_utils
import pprint
import re
from operator import itemgetter

print("M=lac_multicast.dump(_mod=1, _unit = 0, _print_out=1)");
print("M.help()")

# Gets the prefix type.
def get_asic_type(_unit = 0):
    f = open("/proc/cmdline", "r")
    text = f.readline();
    f.close();
    text = text.replace('"', '//')
    text = text.replace('  ', ' ')

    cmd = text.split(' ')

    card_index = 0
    for vals in cmd:
        if "dummy_card_index" in vals:
            cardstr=vals.split("=")
            card_index = int(cardstr[1])
        elif "card_index=" in vals:
            cardstr=vals.split("=")
            card_index = int(cardstr[1])

    if card_index == 21123:
        return "dav"
    elif card_index == 21121:
        return "lac"
    elif card_index == 21125:
        return "dav"
    elif card_index == 21126:
        return "lac"

    return "Unknown"

# Run a tahoe non-fpx command.
def runtahoecmd(_change =True, _mod = 1, _unit=0, _slice=0, _index=0, _table="lua_piftable"):
    asic = get_asic_type(_unit)
    if "Unknown" in asic:
        return "Error"

    prefix = "slot %d quoted \"debug hardware internal %s dump asic %d slice %d " %(_mod, asic, _unit, _slice)
    if _change == True:
        cmd = prefix + "table tah_%s_%s %d changed field-per-line\"" %(asic, _table, _index)
    else:
        cmd = prefix + "table tah_%s_%s %d field-per-line\"" %(asic, _table, _index)

    print cmd
    return nxos_utils.runVshCmd(cmd)

# Run a tahoe fpx command.
def runtahoetilecmd(_change =True, _mod = 1, _unit=0, _slice=0, _fp = 0, _tile = 0, _index=0, _table="fpx_fptile"):
    asic = get_asic_type(_unit)
    if "Unknown" in asic:
        return "Error"

    prefix = "slot %d quoted \"debug hardware internal %s dump asic %d slice %d " %(_mod, asic, _unit, _slice)
    if _change == True:
        cmd = prefix + "fp %d table %d:tah_%s_%s %d changed field-per-line\"" %(_fp, _tile, asic, _table, _index)
    else:
        cmd = prefix + "fp %d table %d:tah_%s_%s %d field-per-line\"" %(_fp, _tile, asic, _table, _index)

    print cmd
    return nxos_utils.runVshCmd(cmd)

class dump:    
    mod = 1
    unit = 1
    print_out = 1 # Print to console or return to another function.
    changed = True # Print only changed entries.

    def __init__(self, _mod = 1,  _unit = 0, _print_out = 1, _change=False):
        self.mod = _mod
        self.unit = _unit
        self.print_out = _print_out
        self.changed = _change
        return

    def help(self):
        print "\t\t Table                             \t    INDEX"
        print "\t\tovtbl_detail(slice, index)    \t    mcidx"
        print "\t\tovtbl(slice, index)           \t    mcidx"
        print "\t\tmet_detail(slice, index)      \t    met_indx" 
        print "\t\tmet(slice, index)             \t    met_indx" 
        print "\t\tmcinfo(slice, fp, tile, index)\t    fp, tile, l2ptr"

    def ovtbl_detail(self, _slice = 0, _index = 0):
        out = runtahoecmd(self.changed, self.mod, self.unit, _slice, _index, "qsmt_ovtbl")
        if self.print_out== 1:
            outlines = out.split("\n")
            pprint.pprint(outlines)
            print("\n")

        else:
            return out

    def ovtbl(self, _slice = 0, _index = 0):
        out = runtahoecmd(self.changed, self.mod, self.unit, _slice, _index, "qsmt_ovtbl")
        if self.print_out== 1:
            outlines = out.split("\n")

            temp_str = out.split("data=")[1]

            port_bits = []
       	    port_list = temp_str.split(" \n")[0]
            port_list = int(port_list, 0)
            port_bits.append("member ports on slice are - ")
            i = 0
            while True:
                bit = 1 << i
                if(port_list & bit):
                    port_bits.append(i)
                i = i + 1
                if(i == 32):
                    break

            print(port_bits)

        else:
            return out

    def met_detail(self, _slice = 0, _index = 0):
        metout = []
        out = runtahoecmd(self.changed, self.mod, self.unit, _slice, _index, "qsmt_met")
        if self.print_out== 1:
            outlines = out.split("\n")
            pprint.pprint(outlines)
        else:
            metout.append(out)

        temp_str = out.split("ovidx=")[1]
       	mc_idx = temp_str.split(" \n")[0]
        mc_idx = int(mc_idx, 0)
        ov_tbl = self.ovtbl_detail(_slice, mc_idx)
        if self.print_out == 1:
            print("\n")
        else:
            metout.append(ov_tbl)
            metout.append("\n")
	
        while True:
            temp_str = out.split("next_ptr=")[1]
       	    nxt_met_idx = temp_str.split(" \n")[0]
            if(nxt_met_idx == '0x00000000'):
                break
            nxt_met_idx = int(nxt_met_idx, 0)
            out = runtahoecmd(self.changed, self.mod, self.unit, _slice, nxt_met_idx, "qsmt_met")
            if self.print_out== 1:
                outlines = out.split("\n")
                pprint.pprint(outlines)
            else:
                metout.append(out) 

            temp_str = out.split("ovidx=")[1]
       	    mc_idx = temp_str.split(" \n")[0]
            mc_idx = int(mc_idx, 0)
            ov_tbl = self.ovtbl_detail(_slice, mc_idx)
            if self.print_out == 1:
                print("\n")
            else:
                metout.append(ov_tbl)
                metout.append("\n")

        if self.print_out == 0:
            return metout

    def met(self, _slice = 0, _index = 0):
        metout = []
        out = runtahoecmd(self.changed, self.mod, self.unit, _slice, _index, "qsmt_met")

        temp_str = out.split("bd=")[1]
        bd = temp_str.split(" \n")[0]
        bd = int(bd, 0)

        temp_str = out.split("ovidx=")[1]
       	mc_idx = temp_str.split(" \n")[0]
        mc_idx = int(mc_idx, 0)

        if self.print_out == 1:
            print('Met ptr is   ' +  repr(_index))
            print('Bd is        ' + repr(bd))
            print('Mc_idx is    ' + repr(mc_idx))
        else:
            metout.append('Met ptr is ' +  repr(_index))
            metout.append('Mc_idx is ' + repr(mc_idx))

        ov_tbl = self.ovtbl(_slice, mc_idx)
        if self.print_out == 0:
            metout.append(ov_tbl)
            metout.append("\n")
	
        while True:
            temp_str = out.split("next_ptr=")[1]
       	    nxt_met_idx = temp_str.split(" \n")[0]
            if(nxt_met_idx == '0x00000000'):
                break
            nxt_met_idx = int(nxt_met_idx, 0)
            out = runtahoecmd(self.changed, self.mod, self.unit, _slice, nxt_met_idx, "qsmt_met")

            temp_str = out.split("bd=")[1]
            bd = temp_str.split(" \n")[0]
            bd = int(bd, 0)

            temp_str = out.split("ovidx=")[1]
       	    mc_idx = temp_str.split(" \n")[0]
            mc_idx = int(mc_idx, 0)

            if self.print_out == 1:
                print('Met index is ' + repr(nxt_met_idx))
                print('Bd is        ' + repr(bd))
                print('Mc_idx is    ' + repr(mc_idx))
            else:
                metout.append('Met index is ' + repr(nxt_met_idx))
                metout.append('Bd is ' + repr(bd))
                metout.append('Mc_idx is ' + repr(mc_idx))
                metout.append("\n")

            ov_tbl = self.ovtbl(_slice, mc_idx)
            if self.print_out == 0:
                metout.append(ov_tbl)
                metout.append("\n")

        if self.print_out == 0:
            return metout
        
    def mcinfo(self, _slice = 0, _fp = 0, _tile = 0, _index = 0):
        mcinfo_out = []
        out = runtahoetilecmd(self.changed, self.mod, self.unit, _slice, _fp, _tile, _index, "fpx_fptile")
        if self.print_out== 1:
            outlines = out.split("\n")
        for line in outlines:
            line = line.rstrip()
            if re.search('mcast', line):
                print line
                print("\n")
            else:
	            mcinfo_out.append(out)

        temp_str = out.split("tile_entry_l2_entry_ip_mcast_info_mcinfo_met_ptr=")[1]
        met_ptr = temp_str.split(" \n")[0]
        met_ptr = int(met_ptr, 0)
        met_info = self.met(_slice, met_ptr)
        if self.print_out == 1:
            print("\n")
        else:
            mcinfo_out.append(met_info)
            mcinfo_out.append("\n")

        if self.print_out == 0:
            return mcinfo_out
            

