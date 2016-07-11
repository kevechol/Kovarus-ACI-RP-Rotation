#!/usr/bin/env python
import csv
import json

csv_test = 'csv_test.csv'

output = []

def get_patchplan(csv_file):
    for line in csv_file:
        if line['Device']:
            row = {}
            row['LocalPort'] = line['LocalPort']
            row["VLAN"] = [x.strip() for x in line["VLAN"].split(',')]
            row["Description"] = line['Device']+":"+line['DestPort']+":"+line['Purpose']
            output.append(row)

    return json.dumps(output,indent=4)

with open(csv_test, 'r') as f:
    csv_file = csv.DictReader(f)
    print get_patchplan(csv_file)

'''import csv
import json

csv_test = 'csv_test.csv'

csv_file = csv.DictReader(open(csv_test, 'rb'))

# LocalPort,Device,DestPort,Purpose,VLAN

output = []

for line in csv_file:
    if line['Device']:
        row = {}
        row['LocalPort'] = line['LocalPort']
        row['DestPort'] = line['DestPort']
        output.append(row)

x = json.dumps(output,indent=4)
print x'''





'''csvfile = open('csv_test.csv', 'r')

fieldnames = ("LocalPort","Device","DestPort","Purpose","VLAN")
reader = csv.DictReader( csvfile, fieldnames)
for row in reader:
    y = json.dumps(row,indent=4)
    print y'''