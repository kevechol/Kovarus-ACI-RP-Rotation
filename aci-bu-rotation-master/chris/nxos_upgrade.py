#!/usr/bin/env pythont

import json
from device import Device
import datetime
import time
import argparse
import getpass
import requests


def getargs():
	parser = argparse.ArgumentParser()
	parser.add_argument('-s', '--switch',
						required=True,
						action='store',
						help='Switch IP Address')
	parser.add_argument('-u', '--username',
						required=True,
						action='store',
						help='Switch Username')
	parser.add_argument('-t', '--tftp',
						required=True,
						action='store',
						help='Tftp server name')
	parser.add_argument('-f', '--filename',
						required=True,
						action='store',
						help='Upgrade Image File')
	args = parser.parse_args()
	return args

password = getpass.getpass("Switch Password:")

args = getargs()
ip = args.switch
switchuser = args.username
switchpassword = password
source_file = args.filename
response_header = {'content-type':'application/json'}
tftp = "tftp://" + ip
date = time.strftime("%Y%m%d")
url = "http://" + ip + "/ins"

def nsox_check_config_session():

	payload={
  	"ins_api": {
    "version": "1.0",
    "type": "cli_show_ascii",
    "chunk": "0",
    "sid": "1",
    "input": "show configuration session summary",
    "output_format": "json"
 	 }
	}

	r = requests.post(url,
					  data=json.dumps(payload),
					  headers=response_header,
					  auth=(switchuser, switchpassword)).json()

	return r


def nsox_backup_running_config():

	payload={
  	"ins_api": {
    "version": "1.0",
    "type": "cli_show_ascii",
    "chunk": "0",
    "sid": "1",
    "input": "copy running-config" + tftp + "/" + ip + "_running_cfg_" + date + ".bak",
    "output_format": "json"
  	  }
	}

	r = requests.post(url,
					  data=json.dumps(payload),
					  headers=response_header,
					  auth=(switchuser, switchpassword)).json()

	return r


def nsox_backup_startup_config():

	payload={
  	"ins_api": {
    "version": "1.0",
    "type": "cli_show_ascii",
    "chunk": "0",
    "sid": "1",
    "input": "copy running-config" + tftp + "/" + ip + "_startup_cfg_" + date + ".bak",
    "output_format": "json"
  	  }
	}

	r = requests.post(url,
					  data=json.dumps(payload),
					  headers=response_header,
					  auth=(switchuser, switchpassword)).json()
    
	return r

def nsox_copy_source():
	
	payload={
  	"ins_api": {
    "version": "1.0",
    "type": "cli_show_ascii",
    "chunk": "0",
    "sid": "1",
    "input": "copy" + ' ' + tftp + "/nxos/upgrade/" + source_file,
    "output_format": "json"
  	  }
	}

	r = requests.post(url,
					  data=json.dumps(payload),
					  headers=response_header,
					  auth=(switchuser, switchpassword)).json()

	return r

def nsox_check_compat(username, password, url, response_header):

    payload={
  			"ins_api": {
    		"version": "1.0",
    		"type": "cli_show",
    		"chunk": "0",
    		"sid": "1",
    		"input": "show incompatibility nxos" + ' ' + source_file,
    		"output_format": "json"
  			}
		}

    r = requests.post(url,
	                  data=json.dumps(payload),
				 	  headers=response_header,
				 	  auth=(switchuser, switchpassword)).json()


def nsox_copy_running_config():

	payload={
  	"ins_api": {
    "version": "1.0",
    "type": "cli_conf",
    "chunk": "0",
    "sid": "1",
    "input": "copy running-config start-config",
    "output_format": "json"
  		}	
	}

	r = requests.post(url,
    					data=json.dumps(payload),
					  	headers=response_header,
					  	auth=(switchuser, switchpassword)).json()

	return r

def main():
	
	args = getargs()
	ip = args.switch
	switchuser = args.username
	switchpassword = password
	source_file = args.filename
	response_header = {'content-type':'application/json'}
	tftp = "tftp://" + ip
	date = time.strftime("%Y%m%d")
	url = "http://" + ip + "/ins"

	# password = getpass.getpass("Switch Password:")

	# Check for active configuration sessions

	check_session = nsox_check_config_session()

	response = check_session['ins_api']['outputs']['output']

	if response['body'] == 'There are no actve configuration sessions\n':
		print "No active config sessions. Continue upgrade check..."
	else:
		print "There are active configuration sessions"
		print "Must kill active configuration sessions and restart"
		exit()

	# Backup running config


	running_config = nsox_backup_running_config(switchuser, switchpassword, response_header, url)

	response = running_config['ins_api']['outputs']['output']

	if response['code'] == 200:
		print "Running config backed up successfully"
	else:
		print "Warning: Running config not backed up successfully"
		print "Exiting script"
		exit()

	# Backup statup config

	startup_config = nsox_backup_startup_config(switchuser, switchpassword, response_header, url)

	response = startup_config['ins_api']['outputs']['output']

	if response['code'] == 200:
		print "Startup config backed up successfully"
	else:
		print "Warning: Startup config not backed up successfully"
		print "Exiting script"
		exit()

	# Copy upgrade software to switch

	source = nsox_copy_source(switchuser, switchpassword, response_header, url)

	response = source['ins_api']['outputs']['output']

	if response['code'] == 200:
		print "Upgrade image files uploaded successfully"
	else: 
		print "Upgrade file not uploaded successfully"
		print "Check path and try again"
		exit()

	# Run compatibility check on image file

	compat_check = nsox_check_compat(switchuser, switchpassword, response_header, url)

	response = compat_check['ins_api']['outputs']['output']
    

	if response['body'] == "no compat issues":
		print "No compatibility issues found"
		return r
	else:
		print "Upgrade not compatible"
		print "Exiting script"
    	exit()

if __name__ == '__main__':
	main()
