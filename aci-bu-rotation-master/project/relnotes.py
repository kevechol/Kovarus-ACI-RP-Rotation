#!/usr/bin/env python

import argparse

import re

import xmltodict

from device import Device

import urllib2

from bs4 import BeautifulSoup

import webbrowser

import getpass


def getargs():
    '''
    :return: Returns argument values.
    '''
    parser = argparse.ArgumentParser()

    parser.add_argument('-i', '--ip',
                        required=True,
                        action='store',
                        help="Device IP address")
    parser.add_argument('-u', '--user',
                        required=False,
                        action='store',
                        help="Username on the device")

    args = parser.parse_args()

    return args


def show_version():
    '''
    :return: returns the version from the json return from a switch using provided nxapi modules.
    '''
    args = getargs()

    username = args.user

    if not username:
        username = raw_input("Username: ")

    password = getpass.getpass("Password: ")

    sw1 = Device(ip=args.ip, username=username, password=password)
    sw1.open()

    getversion = sw1.show('show version')

    result = xmltodict.parse(getversion[1])

    data = result['ins_api']['outputs']['output']['body']['kickstart_ver_str']

    return data


def normalize_version(nxosversion):
    '''
    :param nxosversion: feed it the NXOS version
    :return: a version with ().] stripped out of it so that we can search the release notes page URL's for it.
    '''
    if '6.' in nxosversion:
        version = re.sub('[().]', '', nxosversion)
    elif '7.' in nxosversion:
        version = re.sub('[()I.]', '', nxosversion)

    return version


def main():
    showversion = show_version()

    normalversion = normalize_version(showversion)

    result = ''

    url = urllib2.urlopen(
        'http://www.cisco.com/c/en/us/support/switches/nexus-9000-series-switches/products-release-notes-list.html')
    content = url.read()
    # You have to add lxml or bs4 will complain about not having an interpreter set. Ugh.
    soup = BeautifulSoup(content, "lxml")
    for a in soup.findAll('a', href=True):
        if re.findall(normalversion, a['href']):
            result = a['href']

    # This will open the release notes in a browser.
    webbrowser.open_new('https://www.cisco.com/' + result)


if __name__ == '__main__':
    main()
