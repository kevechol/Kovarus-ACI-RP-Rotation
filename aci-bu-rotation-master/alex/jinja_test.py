#!/usr/bin/env python

import csv
from jinja2 import Template

csv_test = 'csv_test.csv'

output = []

def get_patchplan(csv_file):
    for line in csv_file:
        if line['Device']:
            row = {}
            row['LocalPort'] = line['LocalPort']
            row["VLAN"] = line['VLAN']
            row["Description"] = line['Device'] + ":" + line['DestPort'] + ":" + line['Purpose']
            output.append(row)

    return output

with open(csv_test, 'r') as f:
    csv_file = csv.DictReader(f)

    imported_vars = get_patchplan(csv_file)

    config_template = Template(open('l2_port_template.j2').read())
    print config_template.render(interfaces=imported_vars)