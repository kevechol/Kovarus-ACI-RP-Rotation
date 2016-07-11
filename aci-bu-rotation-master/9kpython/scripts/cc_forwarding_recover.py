#################################################
#
#      File:   cc_l3lif_state.py
#      Name:
#
#       Description: L3Lif consistency checker
#
#
#
# Copyright (c) 1985-2013,2015 by cisco Systems, Inc.
# All rights reserved.
#
#################################################
import onxos
import nxos_utils
from libbcmshell import *
import re
import sys
import signal
import time
from onxos import *
import logging
import logging.handlers

log_name = '/tmp/fib_recovered_routes.log'
filehandler = logging.handlers.RotatingFileHandler(log_name, maxBytes=1024*512,backupCount=1)
formatter = logging.Formatter('%(asctime)s -- %(message)s')
filehandler.setFormatter(formatter)

logger = logging.getLogger('root')
logger.addHandler(filehandler)

signal.signal(signal.SIGINT, signal_handler_sigint)

def forwarding_recover(_val):
    """
    testing
    """
    inconsistent = 0
    cmd = "test consistency-checker forwarding vrf all"
    nxos_utils.runVshCmd(cmd)
    while True:
        time.sleep(2)
        cmd = "show consistency-checker forwarding vrf all"
        output = nxos_utils.runVshCmd(cmd)
        lines = output.split("\n")
        if ("Execution time") in lines[1]:
            break
    for line in lines:
        if "prefix" in line:
            inconsistent = inconsistent + 1
            re_pattern = 'prefix('
            words = line.split(re_pattern)
            words2 = words[1].split('),')
            ipnmask = words2[0]
            nxos_utils.runVshCmd("clear ip route vrf all " + ipnmask)
            log = "Recovered v4 route " + ipnmask
            print log
            logger.warning(log)

    cmd = "test consistency-checker forwarding ipv6 vrf all"
    nxos_utils.runVshCmd(cmd)
    while True:
        time.sleep(2)
        cmd = "show consistency-checker forwarding ipv6 vrf all"
        output = nxos_utils.runVshCmd(cmd)
        lines = output.split("\n")
        if ("Execution time") in lines[1]:
            break
    for line in lines:
        if "prefix" in line:
            inconsistent = inconsistent + 1
            re_pattern = 'prefix('
            words = line.split(re_pattern)
            words2 = words[1].split('),')
            ipnmask = words2[0]
            nxos_utils.runVshCmd("clear ipv6 route vrf all " + ipnmask)
            log = "Recovered v6 route " + ipnmask
            print log
            logger.warning(log)

    if inconsistent > 0:
        log = "Inconsistent Routes Recovered"
        print log
        logger.warning(log)
        py_syslog(4, "Inconsistent Routes Recovered")
    else:
        log = "No Inconsistent Routes to be Recovered"
        print log
        logger.warning(log)
        py_syslog(4, "No Inconsistent Routes to be Recovered")

    filehandler.close()
    logger.removeHandler(filehandler)
    logging.shutdown()

