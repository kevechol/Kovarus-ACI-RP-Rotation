#!/usr/bin/python

# This script runs during Standby boot as part of system manager's patch-infra
# HA sync control phase.  Any RPM pubkey found on the Active will be synced to
# the Standby.

import os
import argparse
import logging
import subprocess
import shutil
import remoterpmDB
import atexit
import feature_rpm_ha_sync 
from feature_rpm_ha_sync import exit_with_error  
from feature_rpm_ha_sync import CheckDirExistsAction, validate_args

PATCH_INFRA_SYSMGR_RELOAD_VALUE = 132
ACTIVE_RPMSTORE = None
STANDBY_RPMSTORE = os.path.join('/bootflash', '.rpmstore')
LOCAL_LOGFILE = os.path.join('/var', 'log', 'rpm_pubkey_events_local.log')
REMOTE_LOGFILE = os.path.join('/var', 'log', 'rpm_pubkey_events_remote.log')
SYSTEM_PUBKEY_DIR = os.path.join('/etc', 'pki', 'rpm-gpg')

# The full format for every level will be logged to the log file.
# Error level messages will also be duplicated to stdout (console).
# Duplicated the code from feature_rpm_ha_sync and changed the message frormat.
def enable_logging():
    logging.basicConfig(
            level = logging.DEBUG,
            filename = LOCAL_LOGFILE,
            format = '%(asctime)s [RPM PUBKEY SYNC] %(levelname)-8s %(message)s',
            datefmt = '%m/%d/%Y %I:%M:%S %p')
    console = logging.StreamHandler()
    console.setLevel(logging.ERROR)
    formatter = logging.Formatter('RPM PUBKEY Sync: %(levelname)-8s %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)
    logging.info('')

# Sync the rpm publick to the persistent directory 
# /bootflash/.rpmstore/config/etc/pki/rpm-gpg
def persist_sync_rpm_pubkey():
    global ACTIVE_RPMSTORE 
    
    ACTIVE_RPMSTORE = feature_rpm_ha_sync.ACTIVE_RPMSTORE
    source = os.path.join(ACTIVE_RPMSTORE, 'config/etc/pki/rpm-gpg')
    target = os.path.join(STANDBY_RPMSTORE, 'config/etc/pki/rpm-gpg')

    if not os.path.exists(source):
        logging.info("No pubkey contents need to be synced:")
        exit()

    #Check if the persistent folder exists:
    if os.path.isdir(target):
        logging.info("pubkey contents before sync:")
        logging.info(os.listdir(target))
    else:
        if os.path.isfile(target):
            os.remove(target)
        logging.info("Target pubkey directory doesn't exist, create it now")
        #create the pubkey dir if not exists
        try:
            os.makedirs(target)
        except OSError as exc:
            if exc.errno != errno.EEXIST or not os.path.isdir(target):
                exit_with_error("Failed to create dir %s with rc=%d"%
                                (target, exc.errno))   
    try:
        shutil.rmtree(target)
    except:
        exit_with_error(OSError, "failed to remove " + target)

    logging.info("copying synced pubkey")
    try:
        shutil.copytree(source, target, symlinks=True)
    except:
        exit_with_error(OSError, "failed to copy " + source)
    logging.info("pubkey contents after sync:")
    logging.info(os.listdir(target))

    #Check if the run-time pubkey folder exists 
    if os.path.isdir(SYSTEM_PUBKEY_DIR):
        logging.info("system pubkey contents before update:")
        logging.info(os.listdir(SYSTEM_PUBKEY_DIR))
    else:
        if os.path.isfile(SYSTEM_PUBKEY_DIR):
            os.remove(SYSTEM_PUBKEY_DIR)
        logging.info("system pubkey directory doesn't exist, create it now")
        #create the pubkey dir if not exists
        try:
            os.makedirs(SYSTEM_PUBKEY_DIR)
        except OSError as exc:
            if exc.errno != errno.EEXIST or not os.path.isdir(SYSTEM_PUBKEY_DIR):
                exit_with_error("Failed to create dir %s with rc=%d"%
                                (target, exc.errno))   
    
    logging.info("update system pubkey directory")
    try:
        shutil.rmtree(SYSTEM_PUBKEY_DIR)
    except:
        exit_with_error(OSError, "failed to remove " + SYSTEM_PUBKEY_DIR)
    try:
        shutil.copytree(source, SYSTEM_PUBKEY_DIR, symlinks=True)
    except:
        exit_with_error(OSError, "failed to copy to" + SYSTEM_PUBKEY_DIR)
    logging.info("system pubkey contents after dir:")
    logging.info(os.listdir(target))

    # Import the keys which may be needed by loadrpm.sh
    proc = subprocess.Popen("/usr/bin/rpm --import %s/*" % (SYSTEM_PUBKEY_DIR), 
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, shell=True)
    out, err = proc.communicate()
    if (proc.returncode != 0 or err != "") and proc.returncode != 1:
        # Code 1 means it has been installed before. 
        exit_with_error(OSError, "rpm key import failed: %s (rc = %d)" %
                        (err, proc.returncode))
    

# Pass the activity log to the Active supervisor for analysis
# Duplicate the code from feature_rpm_ha_sync because we 
# need to use the global variables defiend in this module.
def sync_log_to_active_atexit():
    logging.info("syncing log to Active")
    try:
        shutil.copy2(LOCAL_LOGFILE, REMOTE_LOGFILE)
    except:
        logging.error("failed to copy local log to remote")
        return
    cmd_hdlr = remoterpmDB.remote_command(3, None, None)
    rc = cmd_hdlr.remote_copy_files([REMOTE_LOGFILE], "/var/log")
    if rc != 0:
        logging.error("failed to sync log to Active")
        return
    logging.info("log synced to Active")
    os.remove(REMOTE_LOGFILE)

# Main script entry point begins here
if __name__ == '__main__':
    atexit.register(sync_log_to_active_atexit)
    enable_logging()
    validate_args()

    persist_sync_rpm_pubkey()

    logging.info("rpm pubkey sync complete")
