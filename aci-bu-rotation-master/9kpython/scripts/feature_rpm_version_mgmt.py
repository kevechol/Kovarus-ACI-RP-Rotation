#!/usr/bin/python

# This script will be called by NXOS feature RPMs twice for each package in
# a transaction - both pre-transaction, and post-transaction.  The actual
# transaction consists of file manipulation performed by RPM.

import argparse
import subprocess
import json
import re
import logging
import os
import remoterpmDB
import sys

# Files reserved for state persistence
TRANSACTION_DELTA_FILE = "/var/tmp/yum_transaction_delta"
TRANSACTION_FSS_FILE_PREFIX = "/var/tmp/pkg_transaction_fss_"
ROLLBACK_CMDS_FILE_PREFIX = "/var/tmp/pkg_rollback_cmds_"

# Sentinel file installed by loadrpm.sh during boot-up
# When this file is present, skip most commands
TRANSACTION_BOOTUP_NO_YUM_FILE = "/var/tmp/loadrpm_bootup_no_yum"

# For internal Standby installation testing, locality may be overridden
LOCALITY_OVERRIDE_FILE = "/var/tmp/pkg_locality_override"

# There are two scenarios where a Standby package operation
# will occur a second time in a transaction.
# 1. In a partial failure where one or more packages failed
#       to install, but also one or more succeeded.
# 2. In a failure of any type on the Active node, after
#       the Standby node has seen no failures.
# In either situation, the Standby package operation will be
# "replayed" in reverse.  This requires swapping the responsibility
# of pre-phase and post-phase global commands.  This file
# will be created and destroyed by the Active Yum plugin.
STBY_RECOVERY_MODE_FILE = "/var/tmp/yum_stby_recovery_mode"

# YUM NAEVR format
(PKG_NAME, PKG_ARCH, PKG_EPOCH, PKG_VERSION, PKG_REVISION) = range(5)

# package metadata format
(PKG_VERSION_OLD, PKG_VERSION_NEW) = range(2)

# package update meta-command collection
syscmd = {
        'reparse': '/isan/bin/sysmgr_cmds -o reparse',
        'cli': '/isan/bin/routing-sw/clis_feature_load {0} {1}',
        'svc': '/isan/bin/patching_utils.py --{0}services={1}',
        'ftr': "/isan/bin/vsh -c 'config term ; {0} feature {1}' -w",
        'install': "/isan/bin/vsh -c 'config term ; {0} install feature-set fcoe-npv' -w",
        'fcoe_ftr': "/isan/bin/vsh -c 'config term ; {0} feature-set fcoe-npv' -w"    
        }

# Cache system state data for use throughout this script invocation
# otherwise, too many calls to remoterpmDB will overload vsh
# and throw an error.
system_state_cache = {
        'operation_stage':'unknown',
        'is_standby':False,
        'standby_ready':False
        }

# Remote command handler need only be initialized once
remote_command_handler = None

# This custom parser action filters arguments before accepting them.
# This prevents malicious insertion of arbitrary code,
# so the args may be used later without further filtering.
class FilterAppendAction(argparse.Action):
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        if nargs is not None:
            exit_with_error(ValueError, "nargs not allowed")

        self._regex_filter = re.compile('^[A-Za-z0-9.,+-_/~#]+$')
        super(FilterAppendAction, self).__init__(option_strings, dest, **kwargs)

    def __call__(self, parser, namespace, cli_arg, option_string=None):
        if not re.match(self._regex_filter, cli_arg):
            exit_with_error(ValueError,
                    "invalid format for argument: %d" % (cli_arg))
        setattr(namespace, self.dest, [elem for elem in cli_arg.split(',')])

# Mandatory argument order must be honored by script callers
def validate_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('pkg_stage', help="update stage",
                        choices=['pre-inst', 'post-inst', 'pre-rm', 'post-rm'])
    parser.add_argument('pkg_name', help="package name")
    parser.add_argument('pkg_count', type=int, choices=[0, 1, 2],
                        help="total count of packages involved")
    parser.add_argument('-c', '--cli_file', action=FilterAppendAction, default=[],
                        help="CLI file to be installed or removed")
    parser.add_argument('-s', '--service', action=FilterAppendAction, default=[],
                        help="service to be stopped or started")
    parser.add_argument('-f', '--feature', action=FilterAppendAction, default=[],
                        help="feature to be disabled or enabled")
    parser.add_argument('-n', '--name', action=FilterAppendAction, default=[],
                        help="feature name to be checked in show commands")
    parser.add_argument('-o', '--clioverride', action=FilterAppendAction, default=[],
                        help="cli file override for bug-fix upgrade")
    return parser.parse_args()

def exit_with_error(exception, error_string):
    logging.error(error_string)
    raise exception(error_string)

# The full format for every level will be logged to the log file.
# Error level messages will also be duplicated to stdout (console).
def enable_logging():
    logging.basicConfig(
            level = logging.DEBUG,
            filename = "/var/log/feature_rpm_events_local.log",
            format = '%(asctime)s [VERSION MGMT] %(levelname)-8s %(message)s',
            datefmt = '%m/%d/%Y %I:%M:%S %p')

    console = logging.StreamHandler()
    console.setLevel(logging.ERROR)
    formatter = logging.Formatter('RPM version mgmt: %(levelname)-8s %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)
    logging.info('')

# Callback for remote_command utility from remoterpmDB
def cmd_logger(level, CONDUIT_UNUSED, message):
    if level == 'ERROR':
        logging.error("REMOTE CMD: %s" % (message))
    else:
        logging.info("REMOTE CMD: %s" % (message))

# Runs a command based on locality
# Local will open subprocess
# Remote will call remoterpmDB which calls rsh
#
# Call this if you ONLY care for the return code
def run_locality_based_command(locality, command):
    if locality == 'local':
        proc = subprocess.Popen(command, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, shell=True)
        out, err = proc.communicate()
        return proc.returncode
    else:
        if not remote_command_handler:
            logging.error("remote command called before handler init")
            return -1
        returncode = remote_command_handler.run_remote_cmd(command)
        return returncode

# If sysmgr and VSH are not yet available, mark the install-stage as
# the earliest known state, and return.  Otherwise query VSH for system info.
#
# Each call to system_state queries VSH.  We need this cache, otherwise
# the fast rate of VSH querying at boot-up will overload VSH, which
# throws an error and forces loadrpm.sh to abort.
def cache_system_state():
    global remote_command_handler
    global system_state_cache

    remote_command_handler = remoterpmDB.remote_command(3, cmd_logger, None)

    proc = subprocess.Popen("echo $(runlevel)", stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, shell=True)
    out, err = proc.communicate()
    if proc.returncode != 0 or err != "":
        exit_with_error(OSError, "runlevel echo failed: %s (rc = %d)" %
                        (err, proc.returncode))
    elif out.rstrip() != "N 3":
        system_state_cache['operation_stage'] = 'bootup-pre-sysmgr'
        return
    elif os.path.isfile(TRANSACTION_BOOTUP_NO_YUM_FILE):
        system_state_cache['operation_stage'] = 'bootup-post-sysmgr'
    else:
        system_state_cache['operation_stage'] = 'post-bootup'

    logging.info("operation_stage - %s" % 
                 (system_state_cache['operation_stage']))

    # This data not available if install-stage is bootup-pre-sysmgr
    ss = remoterpmDB.system_state()
    if ss.am_i_standby():
        system_state_cache['is_standby'] = True
    if ss.is_standby_ready():
        system_state_cache['standby_ready'] = True

# Transaction delta file generated in YUM plugin localrpmDB.py
def generate_metadata(pkg_name):
    logging.info("generating metadata from YUM transaction delta")
    if not os.path.isfile(TRANSACTION_DELTA_FILE):
        exit_with_error(OSError,
                "missing YUM transaction delta %s - feature requires YUM" %
                (TRANSACTION_DELTA_FILE))
    with open(TRANSACTION_DELTA_FILE, 'r') as ytdf:
        yum_naevr_meta = json.load(ytdf)

    package_naevr_meta = []
    for package in yum_naevr_meta:
        if package[PKG_NAME] == pkg_name:
            version_string = package[PKG_VERSION] + '.' + package[PKG_REVISION][1:]
            package_naevr_meta.insert(0, version_string)
    if len(package_naevr_meta) == 1: package_naevr_meta.insert(0, None)
    return package_naevr_meta

# The YUM NAEVR metadata for both feature versions, old and new, are compared.
# The highest-order difference in version will determine the update severity.
def derive_update_severity(feature_metadata):
    if not feature_metadata[PKG_VERSION_OLD]:
        exit_with_error(ValueError, "missing old package version metadata")

    v_new, v_old = [map(int, v_string.split('.',3)[0:3]) for v_string in feature_metadata]
    for idx, sev_level in enumerate(['major', 'minor', 'bug-fix']):
        if v_new[idx] != v_old[idx]:
            return sev_level
    exit_with_error(OSError,
            "transactions for two packages of the same version are not allowed")

# Persist the udpate state in the pre- phase, so the post- phase
# may return the system back to the proper state which it was before the update
#
# On a redundant setup, Standby should save the state and sync to Active.
# Active should only save state when the Standby is not available.
# This is becuase Standby runs first and remembers which features it had
# disabled - otherwise Active would toggle features indiscriminately
def save_feature_system_state(pkg_name, feature_system_state):
    if not system_state_cache['is_standby'] and system_state_cache['standby_ready']:
        logging.info("skipping save of feature system state on Active")
        logging.info("post-phase will instead use state from Standby")
        return

    if os.path.isfile(STBY_RECOVERY_MODE_FILE):
        logging.info("transaction in recovery mode, skipping save of system state")
        return

    logging.info("saving feature system state for post-phase")
    with open(TRANSACTION_FSS_FILE_PREFIX + pkg_name, 'w') as ytff:
        json.dump(feature_system_state, ytff)

    if system_state_cache['is_standby']:
        rc = remote_command_handler.remote_copy_files(
                [TRANSACTION_FSS_FILE_PREFIX + pkg_name], "/var/tmp")
        if rc != 0:
            exit_with_error(OSError, "failed to sync feature state to Active")
        logging.info("feature system state synced to the Active")

# Retrieve the persisted update state from the pre- phase, so the post- phase
# may return the system back to the proper state which it was before the update
#
# On a redundant setup, Standby and Active will both load the Standby state
def load_feature_system_state(pkg_name):
    logging.info("loading feature system state from previous phase")
    if not os.path.isfile(TRANSACTION_FSS_FILE_PREFIX + pkg_name):
        exit_with_error(OSError, "transaction fss file missing - %s" %
                        (TRANSACTION_FSS_FILE_PREFIX + pkg_name))
    with open(TRANSACTION_FSS_FILE_PREFIX + pkg_name, 'r') as ytff:
        feature_system_state = json.load(ytff)
    return feature_system_state

# Leverage the dictionary of pre-written system meta-commands
# defined at the top of this script.  This will avoid typos in
# duplication of command injection for the different phases.
#
# Some commands must only run on the Active node.
# The system state data from remoterpmDB determines
# the locality of said commands, which are provided along with
# the literal command to call.
def generate_command_lists(feature_system_state, phase):
    update, rollback = [], []

    if os.path.isfile(LOCALITY_OVERRIDE_FILE):
        pre_phase_global_location = 'local'
        post_phase_global_location = 'local'
    elif system_state_cache['operation_stage'] == 'bootup-pre-sysmgr':
        pre_phase_global_location = 'skip'
        post_phase_global_location = 'skip'
    elif system_state_cache['is_standby']:
        if os.path.isfile(STBY_RECOVERY_MODE_FILE):
            pre_phase_global_location = 'skip'
            post_phase_global_location = 'remote'
        else:
            pre_phase_global_location = 'remote'
            post_phase_global_location = 'skip'
    elif not system_state_cache['standby_ready']:
        # Standalone, no HA
        pre_phase_global_location = 'local'
        post_phase_global_location = 'local'
    else:
        # Active node with HA Standby
        pre_phase_global_location = 'skip'
        post_phase_global_location = 'local'

    logging.info("generating system update and rollback commands")
    if phase == 'post-install':
        if system_state_cache['operation_stage'] == 'bootup-post-sysmgr':
            logging.info('system booting, only loading CLI file if Active sup')
            if not system_state_cache['is_standby']:
                for cli_file in feature_system_state['cli']:
                    update.append(('local', syscmd['cli'].format('-a', cli_file)))
                    rollback.insert(0, ('local', syscmd['cli'].format('-r', cli_file)))
        else:
            update.append(('local', syscmd['reparse']))
            rollback.insert(0, ('local', syscmd['reparse']))
            for cli_file in feature_system_state['cli']:
                update.append((post_phase_global_location,
                               syscmd['cli'].format('-a', cli_file)))
                rollback.insert(0, (post_phase_global_location,
                                    syscmd['cli'].format('-r', cli_file)))
            for feature in feature_system_state['ftr']:
                update.append((post_phase_global_location,
                               syscmd['ftr'].format('', feature)))
                rollback.insert(0, (post_phase_global_location,
                                    syscmd['ftr'].format('no', feature)))

    # Mutually exclusive update severities will prevent any case where
    # a set of commands contains both features and services to toggle
    elif phase == 'pre-update':
        if system_state_cache['operation_stage'] == 'bootup-post-sysmgr':
            logging.info('system booting, only unloading CLI file if Active sup')
            if not system_state_cache['is_standby']:
                for cli_file in feature_system_state['cli']:
                    update.append(('local', syscmd['cli'].format('-r', cli_file)))
                    rollback.insert(0, ('local', syscmd['cli'].format('-a', cli_file)))
        else:
            for service in feature_system_state['svc']:
                update.append(('local', syscmd['svc'].format('stop', service)))
                rollback.insert(0, ('local', syscmd['svc'].format('start', service)))
            for feature in feature_system_state['ftr']:
                update.append((pre_phase_global_location,
                               syscmd['ftr'].format('no', feature)))
                rollback.insert(0, (pre_phase_global_location,
                                    syscmd['ftr'].format('', feature)))
            for cli_file in feature_system_state['cli']:
                update.append((pre_phase_global_location,
                               syscmd['cli'].format('-r', cli_file)))
                rollback.insert(0, (pre_phase_global_location,
                                    syscmd['cli'].format('-a', cli_file)))

    # Mutually exclusive update severities will prevent any case where
    # a set of commands contains both features and services to toggle
    elif phase == 'post-update':
        if system_state_cache['operation_stage'] == 'bootup-post-sysmgr':
            logging.info('system booting, only loading CLI file if Active sup')
            if not system_state_cache['is_standby']:
                for cli_file in feature_system_state['cli']:
                    update.append(('local', syscmd['cli'].format('-a', cli_file)))
                    rollback.insert(0, ('local', syscmd['cli'].format('-r', cli_file)))
        else:
            update.append(('local', syscmd['reparse']))
            rollback.insert(0, ('local', syscmd['reparse']))
            for cli_file in feature_system_state['cli']:
                update.append((post_phase_global_location,
                               syscmd['cli'].format('-a', cli_file)))
                rollback.insert(0, (post_phase_global_location,
                                    syscmd['cli'].format('-r', cli_file)))
            for feature in feature_system_state['ftr']:
                update.append((post_phase_global_location,
                               syscmd['ftr'].format('', feature)))
                rollback.insert(0, (post_phase_global_location,
                                    syscmd['ftr'].format('no', feature)))
            for service in feature_system_state['svc']:
                update.append(('local', syscmd['svc'].format('start', service)))
                rollback.insert(0, ('local', syscmd['svc'].format('stop', service)))

    elif phase == 'pre-remove':
        if system_state_cache['operation_stage'] == 'bootup-post-sysmgr':
            logging.info('system booting, only loading CLI file if Active sup')
            if not system_state_cache['is_standby']:
                for cli_file in feature_system_state['cli']:
                    update.append(('local', syscmd['cli'].format('-r', cli_file)))
                    rollback.insert(0, ('local', syscmd['cli'].format('-a', cli_file)))
        else:
            for feature in feature_system_state['ftr']:
                #If fcoe , then disable and uninstall feature-set
                if args.pkg_name == 'fcoe':
                    update.append((pre_phase_global_location,
                               syscmd['fcoe_ftr'].format('no')))
                    rollback.insert(0, (pre_phase_global_location,
                                    syscmd['fcoe_ftr'].format('')))
                    update.append((pre_phase_global_location,
                                   syscmd['install'].format('no')))
                    rollback.insert(0, (pre_phase_global_location,
                                   syscmd['install'].format('')))
                else:    
                    update.append((pre_phase_global_location,
                               syscmd['ftr'].format('no', feature)))
                    rollback.insert(0, (pre_phase_global_location,
                                    syscmd['ftr'].format('', feature)))
            for cli_file in feature_system_state['cli']:
                update.append((pre_phase_global_location,
                               syscmd['cli'].format('-r', cli_file)))
                rollback.insert(0, (pre_phase_global_location,
                                    syscmd['cli'].format('-a', cli_file)))

    elif phase == 'post-remove':
        if system_state_cache['operation_stage'] == 'bootup-post-sysmgr':
            logging.info('system booting, skip...')
        else:
            update.append(('local', syscmd['reparse']))
            rollback.insert(0, ('local', syscmd['reparse']))

    logging.info('transaction phase command count: %d' % len(update))
    return {'update':update, 'rollback':rollback}

# In event of transaction failure *after* the pre-phase has finished,
# the YUM plugin localrpmDB.py will leverage this saved rollback command list
# and return the system to its previous stable state.
#
# Since the version mgmt runs last in an RPM pre- and post- phase scriptlet,
# and since the commands are run at the end of the version mgmt,
# there is no current need to persist the post-phase rollback commands.
def save_rollback_commands(pkg_name, rollback_list):
    logging.info("saving rollback commands for this phase to file: %s" %
                    (ROLLBACK_CMDS_FILE_PREFIX + pkg_name))
    with open(ROLLBACK_CMDS_FILE_PREFIX + pkg_name, 'w') as ypcf:
        json.dump(rollback_list, ypcf)

# Return the number of commands which succceeded, so that any captured
# failures will propogate up to the caller, which will take appropriate
# action based on the phase.
def run_update_commands(command_lists):
    commands_succeeded = 0

    for locality, command in command_lists['update']:
        if locality == 'skip':
            logging.info("skipping command: %s" % (command))
        else:
            logging.info("updating with %s command: %s" % (locality, command))
            rc = run_locality_based_command(locality, command)
            if rc != 0:
                logging.error("%s command FAILED with rc %d" % (locality, rc))
                break
        commands_succeeded += 1
    return commands_succeeded

# Only rollback commands for the *same* phase are called here.
# If this is a post- phase failure, the pre- phase rollback
# commands will instead be invoked by the YUM plugin localrpmDB.py
def run_rollback_commands(command_lists, command_index):
    # start the rollback sequence with the most recent successful index
    for rollback_index in range(command_index - 1, -1, -1):
        locality, command = command_lists['rollback'][rollback_index]
        if locality == 'skip':
            logging.info("skipping command: %s" % (command))
            continue
        logging.info("rolling back with %s command: %s" % (locality, command))
        rc = run_locality_based_command(locality, command)
        if rc != 0:
            logging.error("%s command FAILED with rc %d" % (locality, rc))
            break

# Post install transaction phase occurs immediately after the physical
# installation of package files with no previous installed version.
def run_post_install(args):
    if os.path.isfile(STBY_RECOVERY_MODE_FILE):
        # Recover from previous erasure on Standby
        feature_system_state = load_feature_system_state(args.pkg_name)
    else:
        feature_system_state = {'cli':args.cli_file, 'ftr':[]}

    cmd_lists = generate_command_lists(feature_system_state, 'post-install')
    success_count = run_update_commands(cmd_lists)
    if success_count < len(cmd_lists['update']):
        run_rollback_commands(cmd_lists, success_count)
        exit_with_error(OSError, "update command failed")

# Pre update transaction phase occurs immediately before the physical
# installation of package files, which overwrites an older version.
def run_pre_update(args):
    curr_feature_system_state = {'cli':[], 'svc':[], 'ftr':[]}

    # The boot process skips Yum, so we must assume worst case scenario
    # that the update is major.  However, system manager may not be ready
    # to query, and no features are running anyways, so bypass the feature
    # checks and just deal with the CLI file unloading
    if system_state_cache['operation_stage'] != 'post-bootup':
        curr_feature_system_state['cli'] = args.cli_file
    else:
        # Ensure VSH is available before querying for features / services up
        # otherwise, failures in VSH queries will be undiscernable from
        # grep failures, which are indicative of missing features / services
        # and are NOT systemic failures
        if system_state_cache['is_standby'] == True:
            locality = 'remote'
        else:
            locality = 'local'
        rc = run_locality_based_command(locality, "/isan/bin/vsh -c 'show copyright'")
        if rc != 0:
            exit_with_error(OSError, "VSH unavailable (rc %d)" % (rc))
        logging.info("VSH check passed")

        pkg_meta = generate_metadata(args.pkg_name)
        sev = derive_update_severity(pkg_meta)
        logging.info('pre-updating between %s and %s, severity %s' %
                (pkg_meta[PKG_VERSION_OLD], pkg_meta[PKG_VERSION_NEW], sev))

        if sev in ['major', 'minor']:
            curr_feature_system_state['cli'] = args.cli_file
            query_cmd = "/isan/bin/vsh -c " + \
                "'show feature' | grep '{} ' | grep 'enabled'"
            for index, feature in enumerate(args.feature):
                logging.info("checking if feature {} is enabled".format(feature))
                feature_name = feature 
                if args.name:
                    feature_name = args.name[index]
                rc = run_locality_based_command(locality, query_cmd.format(feature_name))
                if rc == 0:
                    curr_feature_system_state['ftr'].append(feature)
        elif sev == 'bug-fix':
        # only if override cli file is given, add to ops 
            if args.clioverride:
                curr_feature_system_state['cli'] = args.clioverride
            query_cmd = "/isan/bin/vsh -c " + \
                "'show system internal sysmgr service running' | grep '{} '"
            for service in args.service:
                svc_name = re.search('\w+$', service).group(0) # strip path
                logging.info("checking if service {} is running".format(svc_name))
                rc = run_locality_based_command(locality, query_cmd.format(svc_name))
                if rc == 0:
                    curr_feature_system_state['svc'].append(service)

    cmd_lists = generate_command_lists(curr_feature_system_state, 'pre-update')
    success_count = run_update_commands(cmd_lists)
    if success_count < len(cmd_lists['update']):
        run_rollback_commands(cmd_lists, success_count)
        exit_with_error(OSError, "update command failed")

    save_rollback_commands(args.pkg_name, cmd_lists['rollback'])
    save_feature_system_state(args.pkg_name, curr_feature_system_state)

# Post update transaction phase occurs immediately after the physical
# installation of package files, which overwrites an older version.
def run_post_update(args):
    curr_feature_system_state = {'cli':[], 'svc':[], 'ftr':[]}
    prev_feature_system_state = load_feature_system_state(args.pkg_name)

    # The boot process skips Yum, so we must assume worst case scenario
    # that the update is major.  However, system manager may not be ready
    # to query, and no features are running anyways, so bypass the feature
    # checks and just deal with the CLI file loading
    if system_state_cache['operation_stage'] != 'post-bootup':
        curr_feature_system_state['cli'] = prev_feature_system_state['cli']
    else:
        pkg_meta = generate_metadata(args.pkg_name)
        sev = derive_update_severity(pkg_meta)
        logging.info('post-updating between %s and %s, severity %s' %
                (pkg_meta[PKG_VERSION_OLD], pkg_meta[PKG_VERSION_NEW], sev))

        if sev in ['major', 'minor']:
            curr_feature_system_state['ftr'] = prev_feature_system_state['ftr']
            curr_feature_system_state['cli'] = prev_feature_system_state['cli']
        elif sev == 'bug-fix':
            curr_feature_system_state['svc'] = prev_feature_system_state['svc']
            if args.clioverride:
                curr_feature_system_state['cli'] = args.clioverride

    cmd_lists = generate_command_lists(curr_feature_system_state, 'post-update')
    success_count = run_update_commands(cmd_lists)
    if success_count < len(cmd_lists['update']):
        run_rollback_commands(cmd_lists, success_count)
        exit_with_error(OSError, "update command failed")

    if os.path.isfile(ROLLBACK_CMDS_FILE_PREFIX + args.pkg_name):
        os.remove(ROLLBACK_CMDS_FILE_PREFIX + args.pkg_name)

# Pre remove transaction phase occurs immediately before the physical
# removal of package files, which erases all contents from the system.
def run_pre_remove(args):
    feature_system_state = {'cli':[], 'ftr':[]}

    # Ensure VSH is available before querying for features / services up
    # otherwise, failures in VSH queries will be undiscernable from
    # grep failures, which are indicative of missing features / services
    # and are NOT systemic failures
    if system_state_cache['is_standby'] == True:
        locality = 'remote'
    else:
        locality = 'local'
    rc = run_locality_based_command(locality, "/isan/bin/vsh -c 'show copyright'")
    if rc != 0:
        exit_with_error(OSError, "VSH unavailable (rc %d)" % (rc))
    logging.info("VSH check passed")

    feature_system_state['cli'] = args.cli_file
    query_cmd = "/isan/bin/vsh -c 'show feature' | grep '{} ' | grep 'enabled'"
    if args.pkg_name == 'fcoe':
        query_cmd = "/isan/bin/vsh -c 'show feature-set' | grep '{}' | grep 'enabled'"
    for index, feature in enumerate(args.feature):
        logging.info("checking if feature {} is enabled".format(feature))
        feature_name = feature 
        if args.name:
           feature_name = args.name[index]
        rc = run_locality_based_command(locality, query_cmd.format(feature_name))
        if rc == 0:
            feature_system_state['ftr'].append(feature)

    cmd_lists = generate_command_lists(feature_system_state, 'pre-remove')
    success_count = run_update_commands(cmd_lists)
    if success_count < len(cmd_lists['update']):
        run_rollback_commands(cmd_lists, success_count)
        exit_with_error(OSError, "update command failed")

    save_rollback_commands(args.pkg_name, cmd_lists['rollback'])
    save_feature_system_state(args.pkg_name, feature_system_state)

# Post remove transaction phase occurs immediately after the physical
# removal of package files, which erases all contents from the system.
def run_post_remove(args):
    cmd_lists = generate_command_lists(None, 'post-remove')
    success_count = run_update_commands(cmd_lists)
    if success_count < len(cmd_lists['update']):
        run_rollback_commands(cmd_lists, success_count)
        exit_with_error(OSError, "update command failed")

    if os.path.isfile(ROLLBACK_CMDS_FILE_PREFIX + args.pkg_name):
        os.remove(ROLLBACK_CMDS_FILE_PREFIX + args.pkg_name)

# Main script entry point begins here
if __name__ == '__main__':
    enable_logging()
    logging.info('validating args and caching system state')
    args = validate_args()
    cache_system_state()

    if system_state_cache['operation_stage'] == 'bootup-pre-sysmgr':
        logging.info('running before system manager - nothing to do')
        exit(0)

    logging.info('begin %s phase for package %s' % \
            (args.pkg_stage, args.pkg_name))
    if args.pkg_stage == 'pre-inst':
        if args.pkg_count == 1:
            pass
        elif args.pkg_count == 2:
            run_pre_update(args)
    elif args.pkg_stage == 'post-inst':
        if args.pkg_count == 1:
            run_post_install(args)
        elif args.pkg_count == 2:
            run_post_update(args)
    elif args.pkg_stage == 'pre-rm':
        run_pre_remove(args)
    elif args.pkg_stage == 'post-rm':
        run_post_remove(args)
    logging.info('end %s phase for package %s' % \
            (args.pkg_stage, args.pkg_name))
