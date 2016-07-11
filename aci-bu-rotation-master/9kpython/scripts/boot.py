#################################################
#
#      File:   boot.py
#
#
# Copyright (c) 2015 by cisco Systems, Inc.
# All rights reserved.
#
#################################################

import nxos_utils
from nxos_utils import *

show_mod_evh='show module internal event-history module 1'
tolerable_time_diff=0.35

def print_evh_times(vsh_evh_cmd):
    obj=createEventHistoryTableObject(cli_ex(vsh_evh_cmd))
    fsm_time=None
    lc_fsm=None
    for eseqs in obj.table:
        for seq in eseqs:
            if 'FSM:' in seq['TIME_STRING']:
                if 'FSM:<ID(258)' not in seq['TIME_STRING']:
                    lc_fsm=None
                    continue
                lc_fsm=True

            if lc_fsm != True:
                continue

            if 'FSM:<ID(258)' in seq['TIME_STRING']:
                if fsm_time == None:
                    fsm_time=seq['TIME']
                    continue

                time_took=(seq['TIME'] - fsm_time).total_seconds()
                if time_took > tolerable_time_diff:
                    print seq['Triggered event'].__str__().rjust(40), " took ", time_took.__str__().ljust(20) + " seconds"
                continue

            fsm_time=seq['TIME']

            for key in seq.keys():
                if 'E_MTS_TX' in key:
                    req_time=seq['TIME']
                if 'E_MTS_RX' in key:
                    time_took=(seq['TIME'] - req_time).total_seconds()
                    if time_took > tolerable_time_diff:
                        print seq['[E_MTS_RX] Src'].__str__().rjust(40), " took ", time_took.__str__().ljust(20) + " seconds"

def get_fsm_time(vsh_evh_cmd, fsm_id, fsm_event):
    obj=createEventHistoryTableObject(cli_ex(vsh_evh_cmd))
    for eseqs in obj.table:
        for seq in eseqs:
            if "FSM:" in seq['TIME_STRING'] and fsm_id in seq['TIME_STRING']:
                for key in seq.keys():
                    if fsm_event in seq[key].__str__():
                        return seq['TIME']
    return None


def show_boot_timings():
    module_start_time=get_fsm_time(show_mod_evh, 'node 0x0102', 'LCM_LC_ST_SUCCESSFUL_REGISTRATION_RECEIVED')
    module_online_time=get_fsm_time(show_mod_evh, 'node 0x0102', 'LCM_LC_ST_ONLINE')

    if module_online_time == None or module_start_time == None:
        print "Module 1 doesn't seem to be online"
        exit(1)


    print "LC Module took " + (module_online_time - module_start_time).total_seconds().__str__() + " seconds to come ONLINE"
    print "\nMODULE INSERTION SEQUENCES THAT TOOK MORE THAN " + tolerable_time_diff.__str__() + " SECONDS:"
    print_evh_times(show_mod_evh)

    print "\nVMM INSERTION SEQUENCES THAT TOOK MORE THAN " + tolerable_time_diff.__str__() + " SECONDS:"
    print_evh_times('show system internal vmm event-history module 1')

    print "\nLC SYSMGR BOOTUP STATS:"
    print cli_ex("slot 1 show system internal sysmgr bootupstats")
