import sys, os, django
import argparse
import iptools
import netaddr
import ipaddress

sys.path.append('/opt/avi/python/bin/portal')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'portal.settings_local')

django.setup()

from django.db import transaction
from api.models import Network
from api.models import NetworkRuntime
from api.models import VsVip
from api.models import ServiceEngine
from avi.protobuf import options_pb2
from avi.protobuf import common_pb2
from avi.rest.pb2model import protobuf2model
from avi.rest.pb_utils import get_pb_if_exists

INDENT = "    "

def get_nw_cfg_and_rt():
    nws = Network.objects.all()
    nw_rts = NetworkRuntime.objects.all()
    nw_map = {}
    nw_rt_map = {}
    for nw in nws:
        nw_pb = nw.protobuf()
        nw_map[nw_pb.uuid] = nw_pb
    for nw_rt in nw_rts:
        nw_rt_pb = nw_rt.protobuf()
        nw_rt_map[nw_rt_pb.uuid] = nw_rt_pb
    return nw_map, nw_rt_map

def get_matching_subnet_rt(nw_rt, subnet_cidr):
    for subnet_rt in nw_rt.subnet_runtime:
        sub_cidr = subnet_rt.prefix.ip_addr.addr + '/' + str(subnet_rt.prefix.mask)
        if sub_cidr == subnet_cidr:
            return subnet_rt
    return None

"""
Checks:
-network runtime matches config
-allocated IPs point to existing objects
-allocated IPs are in the proper subnet
-if IP is in invalid subnet, is there a valid duplicate in another subnet
"""
@transaction.atomic
def check_cfg_rt_match(fixup):
    print("===================== Start: Network Config and Runtime Check =====================")
    nw_map, nw_rt_map = get_nw_cfg_and_rt()
    nw_missing_in_rt = []
    nw_missing_in_cfg = []
    sub_missing_in_rt = []
    sub_missing_in_cfg = []
    ips_alloced_valid = {}
    ips_alloced_invalid_obj = {}
    ips_alloced_invalid_subnet = {}
    # Network configs
    for nw_uuid in nw_map:
        nw_pb = nw_map.get(nw_uuid)
        nw_rt_pb = nw_rt_map.get(nw_uuid)
        # Network in config but not runtime
        if nw_rt_pb is None:
            nw_missing_in_rt.append(nw_uuid)
            continue
        for subnet in nw_pb.configured_subnets:
            found = False
            for subnet_rt in nw_rt_pb.subnet_runtime:
                if subnet.prefix == subnet_rt.prefix:
                    found = True
                    break
            # Subnet in config but not runtime
            if not found:
                sub_missing_in_rt.append(subnet.prefix.ip_addr.addr + '/' + str(subnet.prefix.mask))
    # Network runtimes
    for nw_uuid in nw_rt_map:
        nw_rt_pb = nw_rt_map.get(nw_uuid)
        nw_pb = nw_map.get(nw_uuid)
        # Network in runtime but not config
        if nw_pb is None:
            nw_missing_in_cfg.append(nw_uuid)
            continue
        for subnet_rt in nw_rt_pb.subnet_runtime:
            matching_subnet = None
            for subnet in nw_pb.configured_subnets:
                if subnet_rt.prefix == subnet.prefix:
                    matching_subnet = subnet
                    break
            # Subnet in runtime but not config
            if not matching_subnet:
                sub_missing_in_cfg.append(subnet_rt.prefix.ip_addr.addr + '/' + subnet_rt.prefix.mask)
                continue
            # Form static IP pool based on config
            ip_ranges = [iptools.IpRange(ip_range.range.begin.addr, ip_range.range.end.addr)
                            for ip_range in matching_subnet.static_ip_ranges]
            ip_pool = set(iptools.IpRangeList(*ip_ranges))
            # Check alloced IPs
            for ipr in subnet_rt.ip_range_runtimes:
                for ip_alloced in ipr.allocated_ips:
                    ip_entry = { "ip": ip_alloced.ip.addr,
                                "obj": ip_alloced.obj_uuid,
                                "network": nw_uuid,
                                "subnet": matching_subnet.prefix.ip_addr.addr + '/' + str(matching_subnet.prefix.mask) }
                    # Check if the IP points to valid object
                    valid_obj = False
                    if ip_alloced.obj_info == "vip":
                        vsvip_pb = get_pb_if_exists(VsVip, ip_alloced.obj_uuid)
                        if vsvip_pb:
                            valid_obj = True
                    # For oshiftk8s, obj_info will be pod key
                    # TODO: check if pod key is valid?
                    elif ":" not in ip_alloced.obj_info:
                        valid_obj = True
                    else:
                        se_pb = get_pb_if_exists(ServiceEngine, ip_alloced.obj_uuid)
                        if se_pb:
                            valid_obj = True
                    if not valid_obj:
                        if ip_alloced.ip.addr in ips_alloced_invalid_obj:
                            ips_alloced_invalid_obj[ip_alloced.ip.addr].append(ip_entry)
                        else:
                            ips_alloced_invalid_obj[ip_alloced.ip.addr] = [ip_entry]
                        continue
                    # Check if IP is within configured IP pool
                    if ip_alloced.ip.addr not in ip_pool:
                        if ip_alloced.ip.addr in ips_alloced_invalid_subnet:
                            ips_alloced_invalid_subnet[ip_alloced.ip.addr].append(ip_entry)
                        else:
                            ips_alloced_invalid_subnet[ip_alloced.ip.addr] = [ip_entry]
                        continue
                    # Valid IP
                    if ip_alloced.ip.addr in ips_alloced_valid:
                        ips_alloced_valid[ip_alloced.ip.addr].append(ip_entry)
                    else:
                        ips_alloced_valid[ip_alloced.ip.addr] = [ip_entry]
    invalid_ips_with_dup_valid = {}
    # For each invalid IP, check for valid duplicate IP
    for ip in ips_alloced_invalid_subnet:
        if ip in ips_alloced_valid:
            invalid_ips_with_dup_valid[ip] = ips_alloced_invalid_subnet[ip]
    for nw in nw_missing_in_rt:
        print("Network %s in config but not runtime" % nw)
    for nw in nw_missing_in_cfg:
        print("Network %s in runtime but not config" % nw)
    for sub in sub_missing_in_rt:
        print("Subnet %s in config but not runtime" % sub)
    for sub in sub_missing_in_cfg:
        print("Subnet %s in runtime but not config" % sub)
    ips_alloced_invalid_obj_net_sub = organize_by_network_subnet(ips_alloced_invalid_obj)
    invalid_ips_with_dup_valid_net_sub = organize_by_network_subnet(invalid_ips_with_dup_valid)
    for ip in ips_alloced_valid:
        if len(ips_alloced_valid[ip]) > 1:
            print("Valid duplicate IPs found for %s: " % ip)
            for ip_entry in ips_alloced_valid[ip]:
                print((ip + ", "), end=' ')
            print()
    for nw_uuid in ips_alloced_invalid_obj_net_sub:
        print("=====ERROR===== Allocated IPs for non-existent objects in network %s" % nw_uuid)
        print("=====NOTE===== These IPs will be deleted from the database if -f flag is set")
        for sub_cidr in ips_alloced_invalid_obj_net_sub[nw_uuid]:
            print("%sSUBNET %s" % (INDENT, sub_cidr))
            for ip_str in ips_alloced_invalid_obj_net_sub[nw_uuid][sub_cidr]:
                for ip_entry in ips_alloced_invalid_obj_net_sub[nw_uuid][sub_cidr][ip_str]:
                    print(("%s%sip[%s], obj[%s]" % (INDENT, INDENT, ip_str, ip_entry['obj'])))
            print()
    for nw_uuid in invalid_ips_with_dup_valid_net_sub:
        print("=====ERROR===== Invalid IPs found in network %s" % nw_uuid)
        print("=====NOTE===== These IPs are outside the range of the configured subnet, and there is a valid duplicate IP "
             "in another subnet. These invalid IPs will be deleted from the database if -f flag is set")
        for sub_cidr in invalid_ips_with_dup_valid_net_sub[nw_uuid]:
            print("%sSUBNET %s" % (INDENT, sub_cidr))
            for ip_str in invalid_ips_with_dup_valid_net_sub[nw_uuid][sub_cidr]:
                for ip_entry in invalid_ips_with_dup_valid_net_sub[nw_uuid][sub_cidr][ip_str]:
                    # Flag if duplicate VIPs point to different objs
                    valid_ips = ips_alloced_valid[ip_str]
                    matching_obj = False
                    for ip_entry_valid in valid_ips:
                        if ip_entry_valid['obj'] == ip_entry['obj']:
                            matching_obj = True
                            break
                    print("%s%sip[%s], obj[%s], matching obj[%s]" % (INDENT, INDENT, ip_str, ip_entry['obj'], matching_obj))
            print()

    if (ips_alloced_invalid_obj or invalid_ips_with_dup_valid) and fixup:
        uinput = input("Delete invalid IPs? (yes/no):")
        if uinput.lower() == "yes":
            print("Deleting invalid IPs")
        else:
            print("Not deleting any invalid IPs")
            print("===================== Done: Network Config and Runtime Check =====================")
            return
    else:
        print("===================== Done: Network Config and Runtime Check =====================")
        return

    modified_networks = set()

    # Delete IPs assigned to non-existent objects
    for ip_str in ips_alloced_invalid_obj:
        for ip_entry in ips_alloced_invalid_obj[ip_str]:
            nw_rt_pb = nw_rt_map.get(ip_entry['network'])
            if not nw_rt_pb:
                print("Error! Did not get associated network[%s] runtime pb" % ip_entry['network'])
                continue
            matching_subnet_rt = get_matching_subnet_rt(nw_rt_pb, ip_entry['subnet'])
            if not matching_subnet_rt:
                print("Error! Did not get associated subnet[%s] runtime" % ip_entry['subnet'])
                continue
            for ipr in matching_subnet_rt.ip_range_runtimes:
                for idx, ip_alloced in enumerate(ipr.allocated_ips):
                    if ip_alloced.ip.addr == ip_str:
                        del ipr.allocated_ips[idx]
                        ipr.free_ip_count += 1
                        modified_networks.add(ip_entry['network'])
                        break

    # Delete invalid duplicate IPs which has a valid IP in another subnet
    for ip_str in invalid_ips_with_dup_valid:
        for ip_entry in invalid_ips_with_dup_valid[ip_str]:
            nw_rt_pb = nw_rt_map.get(ip_entry['network'])
            if not nw_rt_pb:
                print("Error! Did not get associated network[%s] runtime pb" % ip_entry['network'])
                continue
            matching_subnet_rt = get_matching_subnet_rt(nw_rt_pb, ip_entry['subnet'])
            if not matching_subnet_rt:
                print("Error! Did not get associated subnet[%s] runtime" % ip_entry['subnet'])
                continue
            for ipr in matching_subnet_rt.ip_range_runtimes:
                for idx, ip_alloced in enumerate(ipr.allocated_ips):
                    if ip_alloced.ip.addr == ip_str:
                        del ipr.allocated_ips[idx]
                        ipr.free_ip_count += 1
                        modified_networks.add(ip_entry['network'])
                        break

    for nw_uuid in modified_networks:
        nw_rt = nw_rt_map[nw_uuid]
        # Refill obj_uuid in network runtime
        nw_rt.ClearField('obj_uuids')
        se_set = set()
        for subnet_rt in nw_rt.subnet_runtime:
            for ipr in subnet_rt.ip_range_runtimes:
                for ip_alloc in ipr.allocated_ips:
                    se_set.add(ip_alloc.obj_uuid)
        for obj_uuid in se_set:
            nw_rt.obj_uuids.append(obj_uuid)
        protobuf2model(nw_rt, None, True)
        print("Modified network[%s] in the database" % nw_uuid)

    print("===================== Done: Network Config and Runtime Check =====================")

@transaction.atomic
def check_vsvips(fixup):
    print("===================== Start: VsVip Check  =====================")
    _, nw_rt_map = get_nw_cfg_and_rt()
    vsvip_objs = VsVip.objects.all()
    # VIP addr not found in alloced IPs in subnet runtime
    vip_missing_in_nw_rt = []
    # VIP addr found in alloced IPs in subnet runtime, but pointing to a different vsvip
    vip_duplicate_in_nw_rt = []
    for vsvip_obj in vsvip_objs:
        vsvip_pb = vsvip_obj.protobuf()
        for vip_pb in vsvip_pb.vip:
            # Only check Avi IPAM allocated VIPs
            if not vip_pb.auto_allocate_ip or not vip_pb.ipam_network_subnet:
                continue
            vip_addr = vip_pb.ip_address.addr
            subnet = vip_pb.ipam_network_subnet.subnet
            subnet_cidr = subnet.ip_addr.addr + "/" + str(subnet.mask)
            nw_rt_pb = nw_rt_map[vip_pb.ipam_network_subnet.network_uuid]
            found = False
            for subnet_rt in nw_rt_pb.subnet_runtime:
                if subnet_rt.prefix.ip_addr.addr + "/" + str(subnet_rt.prefix.mask) != subnet_cidr:
                    continue
                for ipr in subnet_rt.ip_range_runtimes:
                    for ip_alloced in ipr.allocated_ips:
                        # IP match
                        if ip_alloced.ip.addr == vip_addr:
                            if ip_alloced.obj_info != "vip":
                                print("ip_alloced[%s] obj_info should be vip, but is %s" % (ip_alloced.ip.addr, ip_alloced.obj_info))
                                break
                            # Found the VIP IP, but alloced IP points to another VIP uuid
                            if ip_alloced.obj_uuid != vsvip_pb.uuid:
                                vip_duplicate_in_nw_rt.append({ "vsvip_uuid": vsvip_pb.uuid,
                                                                "vip": vip_addr,
                                                                "nw_uuid": vip_pb.ipam_network_subnet.network_uuid,
                                                                "subnet": subnet_cidr,
                                                                "dup_vsvip_uuid": ip_alloced.obj_uuid })
                            found = True
                            break
                    break
            # VIP IP not found in network runtime
            if not found:
                vip_missing_in_nw_rt.append({ "vsvip_uuid": vsvip_pb.uuid,
                                                "vip": vip_addr,
                                                "nw_uuid": vip_pb.ipam_network_subnet.network_uuid,
                                                "subnet": subnet_cidr })
    # Reformat for printing
    organized_vips_errors = {}
    for vip_missing in vip_missing_in_nw_rt:
        nw_uuid = vip_missing["nw_uuid"]
        subnet_cidr = vip_missing["subnet"]
        if nw_uuid not in organized_vips_errors:
            organized_vips_errors[nw_uuid] = {}
        if subnet_cidr not in organized_vips_errors[nw_uuid]:
            organized_vips_errors[nw_uuid][subnet_cidr] = {}
        if "vip_missing" not in organized_vips_errors[nw_uuid][subnet_cidr]:
            organized_vips_errors[nw_uuid][subnet_cidr]["vip_missing"] = []
        organized_vips_errors[nw_uuid][subnet_cidr]["vip_missing"].append(vip_missing)
    for vip_dup in vip_duplicate_in_nw_rt:
        nw_uuid = vip_dup["nw_uuid"]
        subnet_cidr = vip_dup["subnet"]
        if nw_uuid not in organized_vips_errors:
            organized_vips_errors[nw_uuid] = {}
        if subnet_cidr not in organized_vips_errors[nw_uuid]:
            organized_vips_errors[nw_uuid][subnet_cidr] = {}
        if "vip_dup" not in organized_vips_errors[nw_uuid][subnet_cidr]:
            organized_vips_errors[nw_uuid][subnet_cidr]["vip_dup"] = []
        organized_vips_errors[nw_uuid][subnet_cidr]["vip_dup"].append(vip_dup)

    add_missing_vips = False
    missing_vips = False

    # Add missing VIP IPs to network runtime in database
    for nw_uuid in organized_vips_errors:
        print("====ERROR===== Network %s" % nw_uuid)
        for subnet_cidr in organized_vips_errors[nw_uuid]:
            print("%sSubnet %s" % (INDENT, subnet_cidr))
            if "vip_missing" in organized_vips_errors[nw_uuid][subnet_cidr]:
                print("%s%sThere are %d vips which are missing in network runtime" % (INDENT, INDENT, len(organized_vips_errors[nw_uuid][subnet_cidr]["vip_missing"])))
                missing_vips = True
                for vip_missing in organized_vips_errors[nw_uuid][subnet_cidr]["vip_missing"]:
                    print("%s%s%svsvip[%s], vip[%s]" % (INDENT, INDENT, INDENT, vip_missing["vsvip_uuid"], vip_missing["vip"]))
            if "vip_dup" in organized_vips_errors[nw_uuid][subnet_cidr]:
                print("%s%sThere are %d vips in network runtime which point to a different vsvip" % (INDENT, INDENT, len(organized_vips_errors[nw_uuid][subnet_cidr]["vip_dup"])))
                for vip_dup in organized_vips_errors[nw_uuid][subnet_cidr]["vip_dup"]:
                    print("%s%s%svsvip[%s], vip[%s], allocated_to[%s]" % (INDENT, INDENT, INDENT, vip_dup["vsvip_uuid"], vip_dup["vip"], vip_dup["dup_vsvip_uuid"]))

    if missing_vips and fixup:
        uinput = input("Add missing vips to network runtime? (yes/no):")
        if uinput.lower() == "yes":
            add_missing_vips = True

    if not add_missing_vips:
        print("===================== Done: VsVip Check  =====================")
        return

    modified_networks = set()

    for nw_uuid in organized_vips_errors:
        for subnet_cidr in organized_vips_errors[nw_uuid]:
            if "vip_missing" in organized_vips_errors[nw_uuid][subnet_cidr]:
                nw_rt_pb = nw_rt_map[nw_uuid]
                if not nw_rt_pb:
                    print("Error! Did not get associated network[%s] runtime pb" % nw_uuid)
                    continue
                matching_subnet_rt = get_matching_subnet_rt(nw_rt_pb, subnet_cidr)
                if not matching_subnet_rt:
                    print("Error! Did not get associated subnet[%s] runtime" % subnet_cidr)
                for vip_missing in organized_vips_errors[nw_uuid][subnet_cidr]["vip_missing"]:
                    add_ip = matching_subnet_rt.ip_alloced.add()
                    add_ip.ip.addr = vip_missing["vip"]
                    ip = netaddr.IPAddress(vip_missing["vip"])
                    if ip.version == 4:
                        add_ip.ip.type = options_pb2.IpAddrType.Value("V4")
                    else:
                        add_ip.ip.type = otions_pb2.IpAddrType.Value("V6")
                    add_ip.obj_info = "vip"
                    add_ip.obj_uuid = vip_missing["vsvip_uuid"]
                    matching_subnet_rt.free_ip_count -= 1
                    modified_networks.add(nw_uuid)

    for nw_uuid in modified_networks:
        nw_rt = nw_rt_map[nw_uuid]
        # Refill obj_uuid in network runtime
        nw_rt.ClearField('obj_uuids')
        se_set = set()
        for subnet_rt in nw_rt.subnet_runtime:
            for ipr in subnet_rt.ip_range_runtimes:
                for ip_alloc in ipr.allocated_ips:
                    se_set.add(ip_alloc.obj_uuid)
        for obj_uuid in se_set:
            nw_rt.obj_uuids.append(obj_uuid)
        protobuf2model(nw_rt, None, True)
        print("Modified network[%s] in the database" % nw_uuid)

    print("===================== Done: VsVip Check  =====================")


"""
Check ServiceEngine IPs which are statically allocated by the Controller for:
-IPs which are not in the network's configured static IP pool
-IPs which are missing in network runtime
-IPs which are in network runtime but allocated to another object
"""

@transaction.atomic
def check_serviceengines(fixup):
    print("===================== Start: ServiceEngine Check  =====================")
    nw_map, nw_rt_map = get_nw_cfg_and_rt()
    se_objs = ServiceEngine.objects.all()
    # [vnw_uuid] = set of static IPs
    nw_ip_pools = {}
    # [vrf_uuid][nw_uuid] = set of alloced IPs
    alloced_ips = {}
    se_ips_not_in_static_pool = []
    missing_se_ips_in_nw_rt = []
    se_ips_pointing_to_other_obj = []

    # Network configs
    for nw_uuid in nw_map:
        nw_pb = nw_map.get(nw_uuid)
        nw_ip_pool = set()
        for subnet in nw_pb.configured_subnets:
            ip_ranges = [iptools.IpRange(ip_range.range.begin.addr, ip_range.range.end.addr)
                            for ip_range in subnet.static_ip_ranges]
            ip_pool = set(iptools.IpRangeList(*ip_ranges))
            nw_ip_pool.update(ip_pool)
        if nw_pb.vrf_context_uuid not in nw_ip_pools:
            nw_ip_pools[nw_pb.vrf_context_uuid] = {}
        nw_ip_pools[nw_pb.vrf_context_uuid][nw_uuid] = nw_ip_pool

    # Network runtimes
    for nw_uuid in nw_rt_map:
        nw_pb = nw_map.get(nw_uuid)
        nw_rt_pb = nw_rt_map.get(nw_uuid)
        ip_alloced_map = {}
        for subnet_rt in nw_rt_pb.subnet_runtime:
            for ipr in subnet_rt.ip_range_runtimes:
                for ip_alloced in ipr.allocated_ips:
                    ip_alloced_map[ip_alloced.ip.addr] = ip_alloced
        if nw_pb.vrf_context_uuid not in alloced_ips:
            alloced_ips[nw_pb.vrf_context_uuid] = {}
        alloced_ips[nw_pb.vrf_context_uuid][nw_uuid] = ip_alloced_map

    # Service engines
    for se_obj in se_objs:
        se_pb = se_obj.protobuf()
        vnic_list = []
        vnic_list.append(se_pb.mgmt_vnic)
        vnic_list.extend(se_pb.data_vnics)
        for vnic in vnic_list:
            for vnic_network in vnic.vnic_networks:
                if not vnic_network.ctlr_alloc or vnic_network.mode != common_pb2.STATIC:
                    continue
                ip_summary = {"name": se_pb.name,
                              "uuid": se_pb.uuid,
                              "mgmt": vnic.is_mgmt,
                              "vrf": vnic.vrf_uuid,
                              "nw": vnic.network_name,
                              "nw_uuid": vnic.network_uuid,
                              "ip": vnic_network.ip.ip_addr.addr + "/" + str(vnic_network.ip.mask),
                              "obj_info": vnic.mac_address}
                ip_summary['subnet_cidr'] = str(ipaddress.ip_network(ip_summary['ip'], strict=False))
                if (vnic.vrf_uuid not in nw_ip_pools) or (
                        vnic.network_uuid not in nw_ip_pools[vnic.vrf_uuid]) or (
                        vnic_network.ip.ip_addr.addr not in nw_ip_pools[vnic.vrf_uuid][vnic.network_uuid]):
                    se_ips_not_in_static_pool.append(ip_summary)
                    continue
                if (vnic.vrf_uuid not in alloced_ips) or (
                        vnic.network_uuid not in alloced_ips[vnic.vrf_uuid]) or (
                        vnic_network.ip.ip_addr.addr not in alloced_ips[vnic.vrf_uuid][vnic.network_uuid]):
                    missing_se_ips_in_nw_rt.append(ip_summary)
                    continue
                if (alloced_ips[vnic.vrf_uuid][vnic.network_uuid][vnic_network.ip.ip_addr.addr].obj_info !=
                    vnic.mac_address) or (alloced_ips[vnic.vrf_uuid][vnic.network_uuid][vnic_network.ip.ip_addr.addr].obj_uuid !=
                    se_pb.uuid):
                    ip_summary['nw_rt_obj_info'] = alloced_ips[vnic.vrf_uuid][vnic_network.ip.ip_addr.addr].obj_info
                    ip_summary['nw_rt_obj_uuids'] = alloced_ips[vnic.vrf_uuid][vnic_network.ip.ip_addr.addr].obj_uuid
                    se_ips_pointing_to_other_obj.append(ip_summary)
                    continue
    if se_ips_not_in_static_pool:
        print("=====ERROR===== SE w/ static IPs which are not in the network's static pool")
        for se_summary in se_ips_not_in_static_pool:
            print("%sname[%s], uuid[%s], mgmt[%s], vrf[%s], nw[%s], ip[%s], obj_info[%s]" %
                    (INDENT, se_summary['name'], se_summary['uuid'], se_summary['mgmt'], se_summary['vrf'],
                     se_summary['nw'], se_summary['ip'], se_summary['obj_info']))
    if missing_se_ips_in_nw_rt:
        print("=====ERROR===== SE static IPs which are missing in network runtime")
        for se_summary in missing_se_ips_in_nw_rt:
            print("%sname[%s], uuid[%s], mgmt[%s], vrf[%s], nw[%s], ip[%s], obj_info[%s]" %
                    (INDENT, se_summary['name'], se_summary['uuid'], se_summary['mgmt'], se_summary['vrf'],
                     se_summary['nw'], se_summary['ip'], se_summary['obj_info']))
    if se_ips_pointing_to_other_obj:
        print("=====ERROR===== SE static IPs which are in network runtime, but point to another object")
        for se_summary in se_ips_pointing_to_other_obj:
            print("%sname[%s], uuid[%s], mgmt[%s], vrf[%s], nw[%s], ip[%s], obj_info[%s], nw_rt_obj_info[%s], nw_rt_obj_uuid[%s]" %
                    (INDENT, se_summary['name'], se_summary['uuid'], se_summary['mgmt'], se_summary['vrf'],
                     se_summary['nw'], se_summary['ip'], se_summary['obj_info'], se_summary['nw_rt_obj_info'], se_summary['nw_rt_obj_uuid']))

    if se_ips_not_in_static_pool:
        print("Please add the missing static IP pools into the network's configured subnets and re-run the script")
        print("===================== Done: ServiceEngine Check  =====================")
        return

    add_missing_static_ips = False

    if missing_se_ips_in_nw_rt and fixup:
        uinput = input("Add missing SE static IPs to network runtime? (yes/no):")
        if uinput.lower() == "yes":
            add_missing_static_ips = True

    if not add_missing_static_ips:
        print("===================== Done: ServiceEngine Check  =====================")
        return

    modified_networks = set()

    for ip_summary in missing_se_ips_in_nw_rt:
        nw_rt_pb = nw_rt_map[ip_summary['nw_uuid']]
        if not nw_rt_pb:
            print("Error! Did not get associated network[%s] runtime pb" % nw_uuid)
            continue
        matching_subnet_rt = get_matching_subnet_rt(nw_rt_pb, ip_summary['subnet_cidr'])
        if not matching_subnet_rt:
            print("Error! Did not get associated subnet[%s] runtime" % ip_summary['subnet_cidr'])
        add_ip = matching_subnet_rt.ip_alloced.add()
        ip = ip_summary["ip"].split('/')[0]
        add_ip.ip.addr = ip
        ip = netaddr.IPAddress(ip)
        if ip.version == 4:
            add_ip.ip.type = options_pb2.IpAddrType.Value("V4")
        else:
            add_ip.ip.type = otions_pb2.IpAddrType.Value("V6")
        add_ip.obj_info = ip_summary['obj_info']
        add_ip.obj_uuid = ip_summary['uuid']
        matching_subnet_rt.free_ip_count -= 1
        modified_networks.add(ip_summary['nw_uuid'])

    for nw_uuid in modified_networks:
        nw_rt = nw_rt_map[nw_uuid]
        # Refill obj_uuid in network runtime
        nw_rt.ClearField('obj_uuids')
        se_set = set()
        for subnet_rt in nw_rt.subnet_runtime:
            for ipr in subnet_rt.ip_range_runtimes:
                for ip_alloc in ipr.allocated_ips:
                    se_set.add(ip_alloc.obj_uuid)
        for obj_uuid in se_set:
            nw_rt.obj_uuids.append(obj_uuid)
        protobuf2model(nw_rt, None, True)
        print("Modified network[%s] in the database" % nw_uuid)


def organize_by_network_subnet(ip_map):
    organized_map = {}
    for ip_str in ip_map:
        for ip_entry in ip_map[ip_str]:
            if ip_entry['network'] not in organized_map:
                organized_map[ip_entry['network']] = {}
            nw_map = organized_map[ip_entry['network']]
            if ip_entry['subnet'] not in nw_map:
                nw_map[ip_entry['subnet']] = {}
            sub_map = nw_map[ip_entry['subnet']]
            if ip_str in sub_map:
                sub_map[ip_str].append(ip_entry)
            else:
                sub_map[ip_str] = [ip_entry]
    return organized_map

def main():
    parser = argparse.ArgumentParser(description="Script to test for invalid IPs in network runtime of the DB")
    parser.add_argument("-f", "--fixup", dest="fixup", action="store_true", help="fixup")
    args = parser.parse_args()
    check_cfg_rt_match(args.fixup)
    check_vsvips(args.fixup)
    check_serviceengines(args.fixup)

if __name__ == "__main__":
    main()