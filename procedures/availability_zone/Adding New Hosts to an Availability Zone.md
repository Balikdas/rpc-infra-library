# Adding New Hosts to an Availability Zone

This document outlines the high level steps to add new hosts to an existing AZ using the existing RNCC tools on bootstrap hosts.

Note that this document serves as a guide only. Please be sure to know what you are doing before you attempt any steps below. Making mistakes in the production environment can have disastrous consequences, so please reach out to a senior team member if you are not sure what you are doing.

**Do not attempt this procedure on your own without being shown how to do it by a senior team member first.**

## High Level Steps

1. Add DNS Entries for ILO and VMK0
2. Add DHCP Entries in RCMIN DHCP for ILO Interfaces
3. Add New Hosts to OneView
4. Create OneView Server Profiles
5. Stage Firmware on Bootstrap Host
6. Run Firmware Bundle on New Hosts
7. Stage ESXi ISO on Bootstrap Host
8. Run ESXi Install on New Hosts
9. Add DHCP Entries for VMK0 to Bootstrap DHCP
10. Configure Management VLAN Tagging and Hostname on New Hosts
11. Build Ansible Manifest for New Hosts
12. Run Ansbile Playbook to add New Hosts to vCenter
13. Post Validation Steps

## Detailed Steps

### Add DNS Entries for ILO and VMK0

In the RCMIN DHCP servers we have integration with the Rogers DNS platform which allows us to update DNS entries using Dynamic DNS (DDNS) updates. We have scripts that assist with this process on the WLFDLE DHCP server `rncc-dhcp-wlfdle`.

The first script is `nsupdate.sh` which can be used to add and remove single entries:

```bash
[root@rncc-dhcp-wlfdle ~]# ./nsupdate.sh 
ERROR: Incorrect number of arguments
Usage: ./nsupdate.sh {command} {fqdn} {type} {data}
command: {add|delete}
fqdn: {dns_fqdn}
type: {dns_rr_type}
data: {dns_data}
example: ./nsupdate.sh add bob.foo.com A 192.168.10.1
```

The other script is `nsupdate_batch.sh` which can be used to batch load entries:

```bash
[root@rncc-dhcp-wlfdle ~]# ./nsupdate_batch.sh 
ERROR: Incorrect number of arguments
Usage: ./nsupdate_batch.sh {operation} {hosts_file} {rrtype}
operation: {add|delete}
hsots_file: {path_to_file}
rrtype: {dns_rr_type}
{hosts_file} is a space delimited file in the format: {hostname} {ip}
example: ./nsupdate_batch.sh add hosts A
```

**Note:** In the `nsupdate.sh` script there are multiple DDNS servers configurable. It may be required to modify the script to try the alternate DDNS server if your request is failing. This is due to some DNS zones being authorative on one DNS server and some authorative on the other (Infra DNS vs RCMIN DNS).

Be sure to add forward (A record) and reverse (PTR record) DNS entries for all hosts ILO and VMK0 interface IPs and FQDNs. You can verify by using the `nslookup` command for the FQDN and IP of each interface.

An example data file for the `nsupdate_batch.sh` is shown below, as well as an example of adding forward and reverse DNS entries. Note that the full FQDN is required in the data file.

```csv
rnoc7003ru11r.cc.vf.rogers.com 172.30.250.233
rnoc7003ru13r.cc.vf.rogers.com 172.30.250.234
rnoc7003ru15r.cc.vf.rogers.com 172.30.250.235
rnoc7003ru17r.cc.vf.rogers.com 172.30.250.236
rnoc7003ru19r.cc.vf.rogers.com 172.30.250.237
rnoc7003ru21r.cc.vf.rogers.com 172.30.250.238
rnoc7003ru23r.cc.vf.rogers.com 172.30.250.239
rnoc7003ru11r-ilo.cc.vf.rogers.com 172.23.235.9
rnoc7003ru13r-ilo.cc.vf.rogers.com 172.23.235.10
rnoc7003ru15r-ilo.cc.vf.rogers.com 172.23.235.11
rnoc7003ru17r-ilo.cc.vf.rogers.com 172.23.235.12
rnoc7003ru19r-ilo.cc.vf.rogers.com 172.23.235.13
rnoc7003ru21r-ilo.cc.vf.rogers.com 172.23.235.14
rnoc7003ru23r-ilo.cc.vf.rogers.com 172.23.235.15
```

```bash
./nsupdate_batch.sh add ${data_file} A
./nsupdate_batch.sh add ${data_file} PTR
```

### Add DHCP Entries in RCMIN DHCP for ILO Interfaces

In the appropriate RCMIN DHCP server for the region your new hosts are located in, add the DHCP entries for the ILO interfaces.

* Create a CSV file consisting of 3 columns, example below:

```csv
rnoc7003ru11r-ilo,7c:a6:2a:64:0c:ba,172.23.235.9
rnoc7003ru13r-ilo,7c:a6:2a:63:3b:5a,172.23.235.10
rnoc7003ru15r-ilo,7c:a6:2a:63:2b:e4,172.23.235.11
rnoc7003ru17r-ilo,7c:a6:2a:63:fb:62,172.23.235.12
rnoc7003ru19r-ilo,7c:a6:2a:63:db:04,172.23.235.13
rnoc7003ru21r-ilo,7c:a6:2a:63:fb:a6,172.23.235.14
rnoc7003ru23r-ilo,7c:a6:2a:63:fb:58,172.23.235.15
```

Then run the `dhcp_generate.py` script on the DHCP server to generate the DHCP entries and add them to the `/etc/dhcp/dhcp_reservation.inc` file:

```bash
cp -p /etc/dhcp/dhcp_reservation.inc /etc/dhcp/dhcp_reservation.inc.<yyyymmdd>
./dhcp_generate.py ${csv_file} >> /etc/dhcp/dhcp_reservation.inc
```

Then validate the configuration and restart the DHCP service:

```bash
dhcpd -t
systemctl restart dhcpd
systemctl status dhcpd
```

### Add New Hosts to OneView

### Create OneView Server Profiles

### Stage Firmware on Bootstrap Host

### Run Firmware Bundle on New Hosts

### Stage ESXi ISO on Bootstrap Host

### Run ESXi Install on New Hosts

### Add DHCP Entries for VMK0 to Bootstrap DHCP

### Configure Management VLAN Tagging and Hostname on New Hosts

### Build Ansible Manifest for New Hosts

### Run Ansbile Playbook to add New Hosts to vCenter

### Post Validation Steps
