#!/usr/bin/env python
import csv
import json

csv_test = 'test.csv'

output = []

def get_patchplan(csv_file):
    for line in csv_file:
        if line['Device']:
            row = {}
            row['LocalPort'] = line['LocalPort']
            row['DestPort'] = line['DestPort']
            output.append(row)

    return json.dumps(output,indent=4)

with open(csv_test, 'r') as f:
    csv_file = csv.DictReader(f)
    print get_patchplan(csv_file)


