#!/usr/bin/python

# This script runs during Standby boot as part of system manager's patch-infra
# HA sync control phase.  Any NXOS feature RPMs found on the Active which require
# early install on Standby will force a Standby reload after package sync.

import os
import argparse
import logging
import subprocess
import shutil
import remoterpmDB
import atexit

# This reload value is not necessary since patch-infra will reload the
# supervisor on any non-zero exit value.  However this aids understanding
# of the relation between this script's activity and the reload value which
# a user will see on the console.
PATCH_INFRA_SYSMGR_RELOAD_VALUE = 132
ACTIVE_RPMSTORE = None
STANDBY_RPMSTORE = os.path.join('/bootflash', '.rpmstore')

# logfiles needed for HA Sync analysis should any errors occur
log_files = list()

# Patch-infra will reload the supervisor if this process exits with
# any non-zero value.  The value here is 1 (by default).
def exit_with_error(exception, error_string):
    logging.error(error_string)
    raise exception(error_string)

class CheckDirExistsAction(argparse.Action):
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        if nargs is not None:
            exit_with_error(ValueError, "nargs not allowed")
        super(CheckDirExistsAction, self).__init__(option_strings, dest, **kwargs)

    def __call__(self, parser, namespace, cli_arg, option_string=None):
        global ACTIVE_RPMSTORE
        ACTIVE_RPMSTORE = os.path.join(cli_arg, 'bootflash', '.rpmstore')
        if not os.path.isdir(ACTIVE_RPMSTORE):
            exit_with_error(ValueError,
                    "invalid sync_root %s does not lead to .rpmstore" %
                    (ACTIVE_RPMSTORE))
        setattr(namespace, self.dest, cli_arg)

def validate_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--sync-stdby', dest='sync_root',
                        action=CheckDirExistsAction,
                        help="location of Active-synced RPM root to sync")
    parser.parse_args()
    if not ACTIVE_RPMSTORE:
        exit_with_error(ValueError, "missing sync_root")

# Pass the activity log to the Active supervisor for analysis
def sync_logs_to_active_atexit():
    for log_file in log_files:
        local_path = os.path.join(log_file['dir'], log_file['local_name'])
        remote_path = os.path.join(log_file['dir'], log_file['remote_name'])

        logging.info("syncing {} to Active as {}".format(local_path, remote_path))
        try:
            shutil.copy2(local_path, remote_path)
        except:
            logging.error("failed to copy {}".format(log_file['local_name']))
            continue

        cmd_hdlr = remoterpmDB.remote_command(debuglevel=3)
        rc = cmd_hdlr.remote_copy_files([remote_path], log_file['dir'])
        if rc != 0:
            logging.error("failed to sync {} to Active".format(local_path))
            return
        logging.info("{} synced to Active".format(local_path))
        os.remove(remote_path)

# The full format for every level will be logged to the log file.
# Error level messages will also be duplicated to stdout (console).
def enable_logging():
    global log_files

    early_boot_log = dict()
    early_boot_log['dir'] = '/tmp'
    early_boot_log['local_name'] = 'rpm_install.log'
    early_boot_log['remote_name'] = 'rpm_install_remote.log'
    log_files.append(early_boot_log)

    rpm_events_log = dict()
    rpm_events_log['dir'] = '/var/log'
    rpm_events_log['local_name'] = 'feature_rpm_events_local.log'
    rpm_events_log['remote_name'] = 'feature_rpm_events_remote.log'
    log_files.append(rpm_events_log)

    logging.basicConfig(
            level = logging.DEBUG,
            filename = '/var/log/feature_rpm_events_local.log',
            format = '%(asctime)s [HA SYNC] %(levelname)-8s %(message)s',
            datefmt = '%m/%d/%Y %I:%M:%S %p')
    console = logging.StreamHandler()
    console.setLevel(logging.ERROR)
    formatter = logging.Formatter('RPM HA sync: %(levelname)-8s %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)
    logging.info('')

# Analyze the synced repo and determine if any synced packages were
# transferred after the point which they would be installed.
def is_reload_required(target_dir, source_dir):
    pkg_source_set = set(os.listdir(source_dir))
    pkg_target_set = set(os.listdir(target_dir))
    inactive_list = ""
    image_version = ""

    if os.path.isfile(source_dir + '/inactive_feature_rpms.inf'):
        try:
            # Get the inactive RPMs list
            with open(source_dir + '/inactive_feature_rpms.inf') as inf:
                inactive_list = inf.read()
        except StandardError:
            logging.info("No inactive RPMs found")

    proc = subprocess.Popen("/isan/bin/getimgver -i | cut -d ':' -f2", stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, shell=True)
    image_version, err = proc.communicate()
    if proc.returncode != 0:
        logging.error("Failed to get the image version err:{} (rc {})".format(err, proc.returncode))
    image_version = image_version.rstrip()

     # First, inspect incoming packages for installs and upgrades
    for dirent in os.listdir(source_dir):
        target_pkg = None
        source_pkg = os.path.join(source_dir, dirent)

        # Skip file analysis if file is not a package
        if os.path.islink(source_pkg) or not os.path.isfile(source_pkg) or \
                not source_pkg.endswith('.rpm') or dirent.find(image_version) == -1:
            logging.info("file {} not applicable to HA sync".format(dirent))
            pkg_source_set.remove(dirent)
            continue

        q_str = "/usr/bin/rpm -qp {} --queryformat " + \
                "'%{{NAME}} %{{VERSION}} %{{NXOSRPMOPERSTAGE}}'"
        proc = subprocess.Popen(q_str.format(source_pkg), stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, shell=True)
        out, err = proc.communicate()
        if proc.returncode != 0:
            logging.error("RPM query on file {} FAILED:".format(dirent))
            logging.error("    err:{} (rc {})".format(err, proc.returncode))
            pkg_source_set.remove(dirent)
            continue

        # Skip file analysis if package operation stage comes later than
        # the HA sync activity, implying it is not yet installed
        # Also remove from target pkg set to skip future processing
        p_name, incoming_version, p_operstage = out.split()
        if p_operstage != 'bootup-pre-sysmgr':
            logging.info("package {} to be installed after sync".format(dirent))
            pkg_source_set.remove(dirent)
            if dirent in pkg_target_set:
                pkg_target_set.remove(dirent)
            continue

        # Skip file analysis if the version of the early-install package
        # is the same installed as what is getting synced.  This implies
        # the package was already installed in a previous sync session.
        q_str = "/usr/bin/rpm -q {} --queryformat '%{{VERSION}}'"
        proc = subprocess.Popen(q_str.format(p_name), stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, shell=True)
        installed_version, err = proc.communicate()
        if proc.returncode != 0 and \
                err != "package {} is not installed".format(p_name):
            logging.error("RPM query for package {} FAILED:".format(p_name))
            logging.error("    err:{} (rc {})".format(err, proc.returncode))
            pkg_source_set.remove(dirent)
            continue
        elif installed_version == incoming_version:
            # Also remove from target pkg set to skip future processing
            logging.info("package {} already installed".format(dirent))
            pkg_source_set.remove(dirent)
            if dirent in pkg_target_set:
                pkg_target_set.remove(dirent)
            continue

        # Ignore if incoming is an inactive RPM
        if inactive_list.find(dirent) != -1:
            logging.info("Discarding inactive RPM {}".format(dirent))
            pkg_source_set.remove(dirent)
            if dirent in pkg_target_set:
                pkg_target_set.remove(dirent)
            continue

        # If the same package exists on the target, but it was already shown
        # earlier, that package version was not installed, then this indicates
        # an install failure and a very high chance for continuous reload.
        target_pkg = os.path.join(target_dir, dirent)
        if os.path.isfile(target_pkg):
            logging.warning("previous install/update may have failed for {}".format(p_name))
            logging.warning("continuous Standby reload likely")
            # Design decision was made to keep Standby in continuous reload,
            # rather than bail out of the HA sync and leave Standby in
            # a state incompatible with the Active

        # Note this dirent is NOT removed from pkg_source_set
        info_msg = "early install/update required for {} due to " + \
                "version mismatch: (installed) {} vs (incoming) {}"
        logging.info(info_msg.format(p_name, installed_version, incoming_version))

    # By this point, the pkg_source_set contains only packages which require
    # early install and would prompt a supervisor reload.  All that remains are
    # package/feature downgrades back to the image-default, identified by having
    # some newer version in the target localrepo, yet no version at all in the
    # source localrepo.

    # First, remove any redundancies in the target (local node) that were already
    # processed in the source (remote node incoming)
    pkg_target_set -= pkg_source_set
    for dirent in list(pkg_target_set):
        target_pkg = os.path.join(target_dir, dirent)

        # Skip file analysis if file is not a package
        if os.path.islink(target_pkg) or not os.path.isfile(target_pkg) or \
                not target_pkg.endswith('.rpm') or dirent.find(image_version) == -1:
            logging.info("file {} not applicable to HA sync".format(dirent))
            pkg_target_set.remove(dirent)
            continue

        q_str = "/usr/bin/rpm -qp {} --queryformat " + \
                "'%{{NAME}} %{{VERSION}} %{{NXOSRPMOPERSTAGE}}'"
        proc = subprocess.Popen(q_str.format(target_pkg), stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, shell=True)
        out, err = proc.communicate()
        if proc.returncode != 0:
            logging.error("RPM query on file {} FAILED:".format(dirent))
            logging.error("    err:{} (rc {})".format(err, proc.returncode))
            pkg_target_set.remove(dirent)
            continue

        # Skip file analysis if package operation stage comes later than
        # the HA sync activity, implying it is not yet installed
        p_name, physical_version, p_operstage = out.split()
        if p_operstage != 'bootup-pre-sysmgr':
            logging.info("package {} to be removed after sync".format(dirent))
            pkg_target_set.remove(dirent)
            continue

        # At this point, we have a feature RPM in our current repo but
        # does not exist in the syncing repo.  This implies we need to
        # reload for HA sync, after wiping out the current package, so
        # that the next boot will install the system-default version.
        logging.info("early removal/downgrade required for {}".format(p_name))

    # Finally, at the end of these two loops we have enough information
    # to determine why any HA reload is required based on package deltas
    if pkg_target_set | pkg_source_set:
        return True
    else:
        return False

def persist_synced_feature_rpm_packages(target_dir, source_dir):
    logging.info("local repo contents to be erased for sync:")
    logging.info(os.listdir(target_dir))
    logging.info("incoming repo contents to be copied for sync:")
    logging.info(os.listdir(source_dir))

    logging.info("erasing local repo contents")
    try:
        shutil.rmtree(target_dir)
    except:
        exit_with_error(OSError, "failed to remove " + target_dir)

    logging.info("copying incoming repo contents")
    try:
        shutil.copytree(source_dir, target_dir, symlinks=True)
    except:
        exit_with_error(OSError, "failed to copy " + source_dir)
    logging.info("local repo contents after sync:")
    logging.info(os.listdir(target_dir))

    logging.info("copying persistence files")
    try:
        shutil.copy2(os.path.join(ACTIVE_RPMSTORE, 'nxos_rpms_persisted'),
                     os.path.join(STANDBY_RPMSTORE, 'nxos_rpms_persisted'))
    except:
        exit_with_error(OSError, "failed to copy persistence file")

    if os.path.isfile(os.path.join(ACTIVE_RPMSTORE, 'nxos_preinstall_rpms_removed')):
        logging.info("copying nxos_preinstall_rpms_removed file")
        try:
            shutil.copy2(os.path.join(ACTIVE_RPMSTORE, 'nxos_preinstall_rpms_removed'),
                         os.path.join(STANDBY_RPMSTORE, 'nxos_preinstall_rpms_removed'))
        except:
            exit_with_error(OSError, "failed to copy nxos_preinstall_rpms_removed file")

    logging.info("repo file copy complete")

def persist_etc_files():
    etc_src = os.path.join(ACTIVE_RPMSTORE, 'config/etc')
    etc_dst = os.path.join(STANDBY_RPMSTORE, 'config/etc')

    if not os.path.isdir(etc_src):
        logging.info("config/etc not present, persist etc not required")
        return

    logging.info("copying persisted etc files")
    if os.path.isdir(etc_dst):
        try:
            shutil.rmtree(etc_dst)
        except:
            logging.error("Failed to remove " + etc_dst)

    try:
        shutil.copytree(etc_src, etc_dst, symlinks=False)
        os.system("cp -rf " + etc_dst + "/* /etc")
    except:
        logging.error("Failed to copy " + etc_src)


# Main script entry point begins here
if __name__ == '__main__':
    atexit.register(sync_logs_to_active_atexit)
    enable_logging()
    validate_args()
    feature_source_dir = os.path.join(ACTIVE_RPMSTORE, 'patching/localrepo')
    feature_target_dir = os.path.join(STANDBY_RPMSTORE, 'patching/localrepo')

    reload_required = is_reload_required(feature_target_dir, feature_source_dir)
    persist_synced_feature_rpm_packages(feature_target_dir, feature_source_dir)
    os.system("sync")
    if reload_required:
        logging.info("this supervisor is reloading for early install")
        exit(PATCH_INFRA_SYSMGR_RELOAD_VALUE)

    persist_etc_files()
    os.system("sync")
    logging.info("HA sync complete for feature RPMs")
