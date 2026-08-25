#!/usr/bin/python

# This script is used to generate DHCP static assignments configuration for the
# ISC DHCP Server. It takes a CSV file as an argument with the structure:
#
# {hostname},{mac},{ip}
#
# Example:
#
# rnoc7001ru01r,EFAB12F2C3FF,172.23.229.101

import sys
import os
import re
import csv
import ipaddress
import macaddress # https://pypi.org/project/macaddress

# functions
def usage():
  sys.stderr.write('Usage: ' + sys.argv[0] + ' <input_file>\n\n<input_file> - CSV file containing the following structure:\n\n{hostname},{mac},{ip}\n\n')

def is_valid_hostname(hostname):
    if len(hostname) > 255:
        return False
    if hostname[-1] == ".":
        hostname = hostname[:-1] # strip exactly one dot from the right, if present
    allowed = re.compile("(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)
    return all(allowed.match(x) for x in hostname.split("."))

def del_err_list(err_list):
  if len(err_list) > 0:
    err_list_uniq = list(set(err_list))
    err_list_uniq.sort(reverse=True)
    for i in err_list_uniq:
      del data[i]
  err_list.clear()

# parse args
if len(sys.argv) != 2:
  sys.stderr.write('ERROR: incorrect number of arguments\n\n')
  usage()
  exit(1)

try:
  datafile = open(sys.argv[1], "r")
except:
  sys.stderr.write('ERROR: file ' + sys.argv[1] + ' does not exist or is not readable\n\n')
  usage()
  exit(1)

# parse csv file into array
with datafile as csvfile:
  data = list(csv.reader(csvfile))

# create list of mac and ip data
dhcp_list = []
err_list = []

# normalize input to lowercase
x = 0
y = 0
for i in data:
  for n in i:
    data[x][y] = n.lower()
    y += 1
  x += 1
  y = 0

# validate column counts
n = 0
for i in data:
  if len(i) != 3:
    sys.stderr.write('WARNING: Skipping entry on line with incorrect format on line ' + str(n + 1) +'\n')
    err_list.append(n)
    n += 1
    continue

# validate hostname
  if not is_valid_hostname(i[0]):
    sys.stderr.write('WARNING: Skipping entry with invalid hostname ' + i[0] + ' on line ' + str(n + 1) +'\n')
    err_list.append(n)
    n += 1
    continue

# validate and normalize MAC format
  try:
    mac = macaddress.MAC(i[1])
  except:
    sys.stderr.write('WARNING: Skipping entry with invalid MAC ' + i[1] + ' on line ' + str(n + 1) +'\n')
    err_list.append(n)
    n += 1
    continue
  data[n][1] = str(mac).replace('-', ':').lower()

# validate IP address
  try:
    ip = ipaddress.ip_address(i[2])
  except:
    sys.stderr.write('WARNING: Skipping entry with invalid IP ' + i[2] + ' on line ' + str(n + 1) +'\n')
    err_list.append(n)
    n += 1
    continue
  if ip.version != 4:
    sys.stderr.write('WARNING: Skipping entry with invalid IP ' + i[2] + ' on line ' + str(n + 1) +'\n')
    err_list.append(n)
    n += 1
    continue
  n += 1

# clear bad entries
del_err_list(err_list)

# build dhcp configs
for i in data:
  dhcp_list.append('host ' + i[0] + ' {\n  option host-name "' + i[0] + '";\n  ddns-hostname "' + i[0] + '";\n  hardware ethernet ' + i[1] + ';\n  fixed-address ' + i[2] + ';\n}')

for i in dhcp_list:
  sys.stdout.write(i + '\n')

# close file handles
datafile.close()

# all done
exit(0)

