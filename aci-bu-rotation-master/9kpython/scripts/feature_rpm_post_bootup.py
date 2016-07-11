#!/usr/bin/python

# This script will be started, in the background, by loadrpm.sh
# during boot-up.  It will poll periodically until the boot-up
# sequence has completed.  At this point, it will run all
# end-of-boot tasks required.

import argparse
import subprocess
import logging
import time

# Arg parser guts
class AppendAction(argparse.Action):
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        if nargs is not None:
            exit_with_error(ValueError, "nargs not allowed")
        super(AppendAction, self).__init__(option_strings, dest, **kwargs)

    def __call__(self, parser, namespace, cli_arg, option_string=None):
        setattr(namespace, self.dest, [elem for elem in cli_arg.split(',')])

def validate_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--platform', default='N9K', help="platform type")
    parser.add_argument('-t', '--task', action=AppendAction, default=[],
                        help="task list to perform at post-boot trigger")
    return parser.parse_args()

def exit_with_error(exception, error_string):
    logging.error(error_string)
    raise exception(error_string)

# The full format for every level will be logged to the log file.
# Error level messages will also be duplicated to stdout.
def enable_logging():
    logging.basicConfig(
            level = logging.DEBUG,
            filename = "/var/log/feature_rpm_events_local.log",
            format = '%(asctime)s [POST BOOTUP] %(levelname)-8s %(message)s',
            datefmt = '%m/%d/%Y %I:%M:%S %p')

    console = logging.StreamHandler()
    console.setLevel(logging.ERROR)
    formatter = logging.Formatter('RPM post-bootup: %(levelname)-8s %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)
    logging.info('')

# Compare local module query with active module query
def get_sup_role():
    proc = subprocess.Popen('/isan/bin/modutil -m',
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out_m, err = proc.communicate()
    if proc.returncode:
        exit_with_error('modutil -m failed')

    proc = subprocess.Popen('/isan/bin/modutil -u',
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out_u, err = proc.communicate()
    if proc.returncode:
        exit_with_error('modutil -u failed')

    if out_m == out_u:
        return 'Active'
    else:
        return 'Standby'

# Notification only valid for the Active sup - Standby never receives this msg
def poll_for_box_online():
    ONE_SECOND, ONE_MINUTE = 1, 60;
    box_online = False

    logging.info('starting periodic poll for bootup status')
    for idx in range(30 * ONE_MINUTE):
        proc = subprocess.Popen('/isan/bin/system_status BOX_ONLINE',
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = proc.communicate()
        # Log only once every 15 seconds, to track process state
        if idx % (15 * ONE_SECOND) == 0:
            logging.info('system_status (rc: %d) output: %s' %
                         (proc.returncode, out.strip()))
        if proc.returncode == 0:
            if idx % (15 * ONE_SECOND) != 0:
                # Log final status only if not already done
                logging.info('system_status (rc: %d) output: %s' %
                             (proc.returncode, out.strip()))
            box_online = True
            break
        time.sleep(ONE_SECOND)
    if not box_online:
        exit_with_error('system failed to boot within 30 minutes')

def task_createrepo_yum_groups(platform):
    logging.info('creating Yum Groups repository')
    if platform == 'N3K':
        logging.info('using N3K platform groups reference')
        groups_file = 'yum-groups-n3k.xml'
    else:
        logging.info('using default platform groups reference')
        groups_file = 'yum-groups.xml'

    command = "/usr/bin/createrepo -g /etc/%s /rpms" % (groups_file)
    proc = subprocess.Popen(command, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, shell=True)
    out, err = proc.communicate()
    if err != '' or proc.returncode != 0:
        logging.error('createrepo FAILED (rc: %d): %s' %
                      (proc.returncode, err.strip()))
    else:
        logging.info('createrepo succeeded')

# Main script entry point begins here
if __name__ == '__main__':
    enable_logging()
    logging.info('validating args')
    args = validate_args()

    # Tasks are delayed on the Active supervisor until all bootup operations
    # have completed, as notified by BOX_ONLINE.  However on Standby, there is
    # no current need to wait for HA sync since the entire system is still
    # usable from the Active sup.  So on Standby, perform tasks immediately.
    sup_role = get_sup_role()
    if sup_role == 'Active':
        logging.info('postponing tasks until Active boot completes')
        poll_for_box_online()

    logging.info('executing task list')
    for task in args.task:
        logging.info('executing: %s' % (task))
        # Forced to use an if-check for each task because, for some reason,
        # the mapping of symbol to function does not work on the platform
        if task == 'createrepo_yum_groups':
            task_createrepo_yum_groups(args.platform)
        else:
            logging.error('task %s not defined' % (task))

    logging.info('task list execution complete')
