#!/usr/bin/env python3
# ***************************************************************************
# Copyright 2024 VMware, Inc.  All rights reserved. VMware Confidential.
# ***************************************************************************
'''
   Script to replace NSX Manager certificates.
'''
import os
import sys
import json
import re
import time
import logging
import datetime
import getpass
import ipaddress
import argparse
import warnings
from binascii import hexlify
from collections import OrderedDict
import requests
import urllib3
try:
    import paramiko
except ImportError:
    print('YOU NEED TO INSTALL PYTHON MODULE "paramiko"\n\n')
    sys.exit(1)
try:
    from cryptography import x509
except ImportError:
    print('YOU NEED TO INSTALL PYTHON MODULE "cryptography"\n\n')
    sys.exit(1)


from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes

warnings.filterwarnings("ignore", category=DeprecationWarning)

VERSION = "1.7"
WELCOME_MSG = '''\
*************************************************************
* replace_certs.py {}                                      *
*                                                           *
* This script will replace self-signed certificates on      *
* an NSX Manager cluster. The newly generated certificates  *
* will retain the properties of the replaced certificates.  *
*                                                           *
* The estimated execution time is 90 minutes if all         *
* certificates are replaced. During this time period do not *
* make any other configuration changes to the NSX Manager.  *
*                                                           *
* It is highly recommended to backup the NSX Manager before *
* running this script.                                      *
*************************************************************
'''

SHORT_WAIT_TIME = 15
LONG_WAIT_TIME = 150
LEAD_DAYS = 366

NODE_TYPE_GM = "NSX Global Manager"
NODE_TYPE_LM = "NSX Manager"

ENABLE_DISK_VALIDATIONS_FOR_CBM = True
CLUSTER_STABILIZATION_WAIT_TIME = 120
RESTART_WORKAROUND_WAIT_TIME = 15
CORFU_STABILIZATION_WAIT_TIME = 150

MAX_RETRY_COUNT_API = 30
API_TIMEOUT = 60
MAX_RETRY_COUNT_SSH = 5

CBM_CERT_ROOT_PATH = "/config/cluster-manager/"
CBM_CERT_KEYSTORE_FILE = "/private/keystore.jks"
CBM_CERT_KEYSTORE_PASSWORD = "/private/keystore.password"
CBM_CERT_TRUSTSTORE_FILE = "/public/truststore.jks"
CBM_CERT_TRUSTSTORE_PASSWORD = "/public/truststore.password"
CBM_CERT_ENTITYID_PATH = "/public/entityId"

node_id_ip_map = {}
node_ssh_info_map = {}
node_ip_password_map = {}

cbm_client_cert_path_dict = {
    'CBM_AR': 'ar',
    'CBM_CCP': 'ccp',
    'CBM_CLUSTER_MANAGER': 'cluster-manager',
    'CBM_CM_INVENTORY': 'cm-inventory',
    'CBM_IDPS_REPORTING': 'idps-reporting',
    # 'CBM_GM': 'gm', #Add if node type is GM
    'CBM_MESSAGING_MANAGER': 'messaging-manager',
    'CBM_MONITORING': 'monitoring',
    'CBM_MP': 'mp',
    'CBM_UPGRADE_COORDINATOR': 'upgrade-coordinator'}

cbm_server_cert_path_dict = {'CBM_CORFU': 'corfu'}

cbm_cert_path_dict = {}
cbm_cert_path_dict.update(cbm_client_cert_path_dict)
cbm_cert_path_dict.update(cbm_server_cert_path_dict)

# List of services that can cause HTTPS service on NSX to go down
critical_cbm_services = {'LM': ['CBM_MP', 'CBM_CLUSTER_MANAGER'],
                         'GM': ['CBM_AR', 'CBM_GM', 'CBM_MP',
                                'CBM_CLUSTER_MANAGER'],
                         'GM_AND_LM': ['CBM_AR', 'CBM_GM', 'CBM_MP',
                                       'CBM_CLUSTER_MANAGER']}

script_name = os.path.basename(os.path.abspath(__file__))
LOG_NAME = script_name.split('.')[0] + '.log'
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

logger.propagate = False

formatter = logging.Formatter('%(asctime)s: %(message)s', '%Y-%m-%d %H:%M:%S')
file_handler = logging.FileHandler(LOG_NAME)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


def replicate_cert(original_cert, validity_days):
    ''' Replace cert
    '''
    original_cert_data = original_cert.encode('utf-8')
    original_cert = x509.load_pem_x509_certificate(
        original_cert_data,
        default_backend()
    )

    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=original_cert.public_key().key_size,
        backend=default_backend()
    )
    private_key_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )

    builder = x509.CertificateBuilder()
    builder = builder.serial_number(original_cert.serial_number)
    builder = builder.issuer_name(original_cert.issuer)
    builder = builder.subject_name(original_cert.subject)
    builder = builder.not_valid_before(datetime.datetime.utcnow())
    builder = builder.not_valid_after(
        datetime.datetime.utcnow() +
        datetime.timedelta(days=validity_days)
    )
    builder = builder.public_key(private_key.public_key())

    for ext in original_cert.extensions:
        builder = builder.add_extension(ext.value, ext.critical)

    new_cert = builder.sign(
        private_key=private_key,
        algorithm=original_cert.signature_hash_algorithm,
        backend=default_backend()
    )

    return (
        new_cert.public_bytes(serialization.Encoding.PEM),
        private_key_bytes
    )


# pylint: disable=too-many-arguments
def rest_api(server, api_type, action, path, passwd, body=None):
    ''' NSX Manager REST API
    '''
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    prefix = 'https://' + server
    if api_type == 'mp':
        path = prefix + '/api/v1/' + path
    elif api_type == 'policy':
        path = prefix + '/policy/api/v1/' + path
    logger.info("Executing %s %s", action, path)
    if body:
        to_log = body
        if '"private_key":' in to_log:
            pattern = r'"private_key":\s*"[^"]+"'
            to_log = re.sub(pattern, '"private_key": "obfuscated"', to_log)
        elif '"license_key":' in to_log:
            pattern = r'"license_key":\s*"[^"]+"'
            to_log = re.sub(pattern, '"license_key": "obfuscated"', to_log)
        logger.info("--data \n%s\n", to_log)
    retry_count = 0
    resp = None
    api_start_time = time.time()
    while (retry_count <= MAX_RETRY_COUNT_API) or (time.time()
                                                   - api_start_time) >= 600:
        if action == 'GET':
            resp = requests.get(path, verify=False,
                                auth=('admin', passwd),
                                headers={'content-'
                                         'type': 'application/json'})
        elif action == 'POST':
            resp = requests.post(path, verify=False, auth=('admin', passwd),
                                 data=body,
                                 headers={'content-'
                                          'type': 'application/json'})
        elif action == 'PATCH':
            resp = requests.patch(path, verify=False, auth=('admin',
                                                            passwd),
                                  data=body,
                                  headers={'content-'
                                           'type': 'application/json'})
        elif action == 'PUT':
            resp = requests.put(path, verify=False, auth=('admin', passwd),
                                data=body,
                                headers={'content-'
                                         'type': 'application/json'})
        elif action == 'DELETE':
            resp = requests.delete(path, verify=False, auth=('admin', passwd),
                                   headers={'content-'
                                            'type': 'application/json'})
        if action == 'GET' or (resp and resp.status_code < 300):
            if resp:
                return resp
        if resp:
            logger.error("API ERROR %s", resp._content.decode('utf-8'))
        else:
            logger.error("API Error : Null response received")
        if retry_count >= MAX_RETRY_COUNT_API:
            raise RuntimeError('API Error on %s %s.' % (action, path), 'See ' +
                               LOG_NAME + ' for details')
        time.sleep(10)
        retry_count += 1
    return None


def validate_ipv4(ip):
    ''' Validate IPv4 address
    '''
    try:
        ipaddress.IPv4Address(ip)
        return True
    except ipaddress.AddressValueError:
        return False


def simplify_certs(cert_list):
    ''' Discard certificate meta-data this script doesn't need
    '''
    allowed_keys = {'pem_encoded', 'used_by', 'display_name', 'id'}
    return [{key: value for key, value in item.items()
            if key in allowed_keys} for item in cert_list]


def custom_sort(item):
    ''' Certificate sort function
    '''
    if item['used_by']['service_types'] == "CBM_CLUSTER_MANAGER":
        return (item['used_by']['node_id'], 2)
    if item['used_by']['service_types'] == "CBM_AR":
        return (item['used_by']['node_id'], 1)
    return (item['used_by']['node_id'], 0)


def sort_certs(data):
    ''' Sort certificates
    '''
    flattened_data = []
    for item in data:
        used_by_list = item['used_by']
        for used_by_item in used_by_list:
            service_types = used_by_item['service_types']
            for service_type in service_types:
                flattened_item = item.copy()
                flattened_item['used_by'] = used_by_item.copy()
                flattened_item['used_by']['service_types'] = service_type
                flattened_data.append(flattened_item)
    return sorted(flattened_data, key=custom_sort)


def get_certs_mapped_by_nodeId(sorted_certs):
    ''' Create a map of nodeIds and sorted certificates list
    '''
    sorted_cert_map = OrderedDict()
    for cert in sorted_certs:
        node_id = cert['used_by']['node_id']
        if node_id in sorted_cert_map:
            sorted_cert_map[node_id].append(cert)
        else:
            sorted_cert_map[node_id] = [cert]
    return sorted_cert_map


def filter_certs(certs, nsx_version, all_local_node_ids):
    ''' Filter certificates to remove unapplicable certs
        like CLIENT_AUTH, GM PI certs on LM etc.
    '''
    filtered_certs = []
    for cert in certs:
        used_by_list = cert['used_by']
        includeCert = False
        for used_by_item in used_by_list:
            if used_by_item['node_id'] not in all_local_node_ids:
                includeCert = False
                break
            # version specific filters can go here
            if (nsx_version.startswith("4.1.2") and
                    'CBM_API' in used_by_item['service_types']):
                includeCert = False
                break
            includeCert = True
        if includeCert:
            filtered_certs.append(cert)
    return filtered_certs


def cluster_stabilization(ip, pwd):
    ''' Wait for cluster to become stable
    '''
    print("Waiting for cluster to stabilize")
    logger.info("Waiting for cluster to stabilize, API call made on IP %s",
                ip)
    i = 0
    api_start_time = time.time()
    while True:
        if i == 90 or ((time.time() - api_start_time) > 900):
            print('Cluster does not reach stabilization in 15 minutes')
            print('Exiting')
            logger.error("Cluster does not reach stabilization in 15 minutes, "
                         "exiting")
            sys.exit(1)
        try:
            resp = rest_api(ip, 'mp', 'GET', 'cluster/status', pwd)
            resp.raise_for_status()
            data = resp.json()
        except RuntimeError:
            data = None
            logger.info("Failed to get cluster status, retrying ..")
        except requests.exceptions.RequestException:
            data = None
            logger.info("NSX UA %s not yet ready", ip)
        if (data and 'detailed_cluster_status' in data.keys()):
            if data['detailed_cluster_status']['overall_status'] == 'STABLE':
                print("Cluster is stable")
                logger.info("Cluster is stable")
                break
            non_stable_services = {}
            groups = data['detailed_cluster_status']['groups']
            for group in groups:
                if group['group_status'] != "STABLE":
                    group_type = group['group_type']
                    non_stable_services[group_type] = group['group_status']
            logger.info("NON STABLE Service List : %s",
                        non_stable_services)

        time.sleep(10)
        i += 1


def restart_cbm_service(ip, admin_pwd):
    ''' Restart CBM service post applying workaround 4.1.1.0 and 4.1.1.1
    '''
    logger.info("Restarting cluster-manager service on %s post fixing "
                "permissions", ip)
    print(f"Restarting cluster-manager service on {ip} post fixing "
          f"permissions")
    path = 'node/services/cluster_manager?action=restart'
    rest_api(ip, 'mp', 'POST', path, admin_pwd)
    logger.info("Sleeping for %s seconds post restart of cluster-manager "
                "service on node %s", CLUSTER_STABILIZATION_WAIT_TIME, ip)
    print(f"Sleeping for {CLUSTER_STABILIZATION_WAIT_TIME} seconds post "
          f"restart of cluster-manager service on node {ip}")
    time.sleep(CLUSTER_STABILIZATION_WAIT_TIME)
    cluster_stabilization(ip, admin_pwd)


def change_aph_file_ownership_and_permissions(hostname, password):
    try:
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(hostname, username='root', password=password, allow_agent=False)

        cmd = ('chown uproton:appl-proxy' +
               ' /etc/vmware/nsx-appl-proxy/appl-proxy-*.pem')

        _stdin, stdout, _stderr = ssh_client.exec_command(cmd)
        result = stdout.read().decode().strip()

        if result == "":
            logger.info('File ownership updated successfully.')
        else:
            print(f"Failed to change owner permissions: {result}")
            logger.error("Failed to change owner permissions: %s", result)

        cmd = 'chmod 660 /etc/vmware/nsx-appl-proxy/appl-proxy-*.pem'

        _stdin, stdout, _stderr = ssh_client.exec_command(cmd)
        result = stdout.read().decode().strip()

        if result == "":
            logger.info('APH files permissions updated successfully.')
        else:
            print(f"Failed to change APH files permissions: {result}")
            logger.error("Failed to change APH files permissions: %s", result)

        ssh_client.close()

    except paramiko.AuthenticationException:
        logger.error('SSH Authentication failed')
        print('SSH Authentication failed. Check your username and password')
    except paramiko.SSHException as e:
        logger.error("SSH error: %s", str(e))


def fix_and_check_aph_file_permissions(vip, pwd1):
    ''' Fix APH and APH-AR certificate and key file permissions.
    '''
    # Using ENABLE_DISK_VALIDATIONS_FOR_CBM as a flag to check if
    # cluster nodes info has been populated. If not populate it.
    if not ENABLE_DISK_VALIDATIONS_FOR_CBM:
        populate_cluster_nodes_ssh_info(vip, pwd1)

    for node_ip, password in node_ip_password_map.items():
        logger.info("Change file permission for node %s", node_ip)
        change_aph_file_ownership_and_permissions(node_ip, password)


def change_cbm_file_permissions(hostname, password):
    ''' Fix file permissions on the NSX Manager
    '''
    try:
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(hostname, username='root', password=password, allow_agent=False)

        cmd = 'sudo chmod -R 770 /config/cluster-manager/*/private/'

        _stdin, stdout, _stderr = ssh_client.exec_command(cmd)
        result = stdout.read().decode().strip()

        if result == "":
            logger.info('File permissions updated successfully for '
                        'private folders')
        else:
            print(f"Failed to change permissions for private folders: "
                  f"{result}")
            logger.error("Failed to change permissions for private folders: "
                         "%s", result)

        cmd = 'sudo chmod -R 770 /config/cluster-manager/*/public/'

        _stdin, stdout, _stderr = ssh_client.exec_command(cmd)
        result = stdout.read().decode().strip()

        if result == "":
            logger.info('File permissions updated successfully for public'
                        ' folders.')
        else:
            print(f"Failed to change permissions for public folders: "
                  f"{result}")
            logger.error("Failed to change permissions for public folders: "
                         "%s", result)

        group_membership_cmd = 'sudo usermod -a -G uproxy,uuc,uproton,' \
                               'nsx-messaging,ucminv,corfu,uphc,nsx-cbm,' \
                               'nsx-replicator,nsx-idps,nsx-sm,nsx nsx-cbm'

        _stdin, stdout, _stderr = ssh_client.exec_command(group_membership_cmd)
        result = stdout.read().decode().strip()

        if result == "":
            logger.info('Group memberships updated successfully.')
        else:
            print(f"Failed to update group memberships: {result}")
            logger.error("Failed to update group memberships: %s", result)

        cmd = 'cat /etc/group | grep "uproton" | grep "x:117"'
        _stdin, stdout, _stderr = ssh_client.exec_command(cmd)
        result = stdout.read().decode().strip()
        if 'nsx-cbm' in result:
            logger.info('nsx-cbm in uproton group')
        else:
            logger.error('nsx-cbm not in proton group')
            print('An error occurred in changing file permission')
            print('Please contact VMWare support')
        ssh_client.close()

    except paramiko.AuthenticationException:
        logger.error('Authentication failed')
        print('Authentication failed. Check your username and password')
    except paramiko.SSHException as e:
        logger.error("SSH error: %s", str(e))
        print("SSH error: %s", str(e))


def get_root_password_from_user(ip):
    while True:
        print()
        root_password = getpass.getpass("Enter root password for " + ip +
                                        " (will not be displayed): ")
        repeat_root_password = getpass.getpass("To confirm, re-enter the"
                                               " password for " + ip +
                                               " (will not be displayed): ")
        if root_password == repeat_root_password:
            break
        print("Passwords don't match. Try again")
    return root_password


def workaround_4102(used_by, ip, pwd):
    ''' Work-around for NSX 4.1.0.2
    '''
    if used_by['service_types'] == 'CBM_AR':
        path = 'node/services/site_manager?action=restart'
    elif used_by['service_types'] == 'CBM_CLUSTER_MANAGER':
        path = 'node/services/cluster_manager?action=restart'
    node_ip = rest_api(ip, 'mp', 'GET', 'cluster/nodes/' +
                       used_by['node_id'], pwd).json()['manager_role'][
                       'api_listen_addr']['ip_address']
    print(f"Restart {used_by['service_types']} service in node {ip}")
    logger.info("Restart %s service in node %s", used_by['service_types'], ip)
    rest_api(node_ip, 'mp', 'POST', path, pwd)
    print(f"Sleeping for {CLUSTER_STABILIZATION_WAIT_TIME} seconds ...")
    time.sleep(CLUSTER_STABILIZATION_WAIT_TIME)
    cluster_stabilization(ip, pwd)


def workaround_4110(vip, pwd):
    ''' Work-around for NSX 4.1.1.0 and 4.1.1.1
    '''
    if not ENABLE_DISK_VALIDATIONS_FOR_CBM:
        while True:
            rpwd1 = getpass.getpass("Enter the cluster's root password " +
                                    "(will not be displayed): ")
            rpwd2 = getpass.getpass("To confirm, re-enter the password " +
                                    "(will not be displayed): ")
            if rpwd1 == rpwd2:
                break
            print("Passwords don't match. Try again")
        nodes = rest_api(vip, 'mp', 'GET', 'cluster/nodes', pwd).json()
        for each in nodes['results']:
            if 'manager_role' in each:
                node_ip = each['manager_role']['api_listen_addr']['ip_address']
                logger.info("Change file permission for node %s", node_ip)
                change_cbm_file_permissions(node_ip, rpwd1)
                restart_cbm_service(node_ip, pwd)
    else:
        for node_ip, password in node_ip_password_map.items():
            logger.info("Change file permission for node %s", node_ip)
            change_cbm_file_permissions(node_ip, password)
            restart_cbm_service(node_ip, pwd)


def ask_backup_question():
    ''' Check if user has already backed up the NSX Manager prior to running
        this script.
    '''
    question1 = 'Have you backed up your system (Yes/No)? '
    question2 = 'Are you sure you want to omit the backup (Yes/No)? '
    prompt = "Invalid answer. Please enter 'Yes' or 'No'"

    backup = input(question1).strip().lower()
    while backup not in ['yes', 'no']:
        print(prompt)
        backup = input(question1).strip().lower()
    if backup == 'yes':
        return True

    omit_backup = input(question2).strip().lower()
    while omit_backup not in ['yes', 'no']:
        print(prompt)
        omit_backup = input(question2).strip().lower()
    if omit_backup == 'yes':
        return True

    return False


def _read_cert_chain_from_pem(pem_encoding):
    cert_chain = []
    text = str(pem_encoding)
    start_line = '-----BEGIN CERTIFICATE-----'
    cert_slots = text.split(start_line)
    for single_pem_cert in cert_slots[1:]:
        cert_pem = (start_line+single_pem_cert).encode('utf-8')
        cert = x509.load_pem_x509_certificate(cert_pem, default_backend())
        cert_chain.append(cert)
    return cert_chain


def _get_leaf_cert(cert_chain):
    """Return the leaf cert from the chain.  The leaf cert is the first cert
     in the chain."""
    return cert_chain[0]


def _is_cert_self_signed(cert):
    return cert.subject == cert.issuer


def _cert_expiry(cert):
    return cert.not_valid_after


def get_local_site_id(vip, pwd):
    ''' Collect UUID of NSX Manager nodes
    '''
    site_info = rest_api(vip, 'mp', 'GET', 'sites/self', pwd).json()
    local_site_id = site_info['site']['id']
    print(f"Local site id is: {local_site_id}")
    return local_site_id


def get_node_ids(vip, pwd):
    ''' Collect UUID of NSX Manager nodes
    '''
    nodes = rest_api(vip, 'mp', 'GET', 'cluster/nodes', pwd).json()
    node_ids = []
    for each in nodes['results']:
        if 'manager_role' in each:
            node_ids.append(each['external_id'])
    logger.info("Legitimate cluster node IDs are: %s", str(node_ids))
    return node_ids


def get_node_type(vip, pwd):
    self_site = rest_api(vip, 'mp', 'GET', 'sites/self', pwd).json()
    node_type = self_site['site']['node_type']
    return node_type


class SshCommandExecutor():
    def __init__(self, ip, password):
        self.ip = ip
        self.password = password
        try:
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(
                paramiko.AutoAddPolicy())
            self.ssh_client.connect(ip, username='root', password=password, allow_agent=False)
        except paramiko.AuthenticationException:
            logger.error('SshCommandExecutor: Authentication failed')
            print('SshCommandExecutor: Authentication failed. Check your '
                  'username and password.')
            raise
        except paramiko.SSHException as e:
            logger.error(f"SshCommandExecutor: SSH error: {str(e)}")
            print(f"SshCommandExecutor: SSH error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"SshCommandExecutor: An error occurred: {str(e)}")
            print(f"SshCommandExecutor: An error occurred: {str(e)}")
            raise

    def exec_command(self, cmd):
        retry_count = 1
        while retry_count <= MAX_RETRY_COUNT_SSH:
            try:
                _, stdout, stderr = self.ssh_client.exec_command(cmd)
                return stdout, stderr
            except Exception as e:
                logger.error(f"SshCommandExecutor: An error occurred: "
                             f"{str(e)}. Recreating SSH Client and retrying")
                print(f"SshCommandExecutor: An error occurred: {str(e)}. "
                      f"Recreating SSH Client and retrying")
                self.ssh_client = paramiko.SSHClient()
                self.ssh_client.set_missing_host_key_policy(
                    paramiko.AutoAddPolicy())
                self.ssh_client.connect(self.ip, username='root',
                                        password=self.password, allow_agent=False)
                if retry_count >= MAX_RETRY_COUNT_SSH:
                    print("Exiting script due to SSH failures, re-run script"
                          " to replace pending expired certificates")
                    logger.error("Exiting script due to SSH failures,"
                                 " script needs to be rerun to"
                                 " replace expired certificates")
                    sys.exit(1)
                retry_count = retry_count + 1
        return None, None

    def close(self):
        self.ssh_client.close()


def populate_cluster_nodes_ssh_info(vip, pwd):
    response = rest_api(vip, 'mp', 'GET', 'cluster/nodes', pwd).json()
    while True:
        choice = input('Is root password same for all nodes of the cluster'
                       ' (Yes/No)? ').strip().lower()
        if choice == 'yes':
            root_password = get_root_password_from_user(vip)
            for node in response['results']:
                if 'manager_role' in node:
                    node_ip = \
                        node['manager_role']['api_listen_addr']['ip_address']
                    node_id = node['external_id']
                    # validate if ssh is working fine
                    try:
                        ssh_exec = SshCommandExecutor(node_ip, root_password)
                    except Exception:
                        print(f"Unable to SSH to '{node_ip}'. Please fix it "
                              f"and rerun the script")
                        logger.info("Unable to ssh to %s, user needs to fix "
                                    "it and rerun the script", node_ip)
                        sys.exit(1)
                    node_id_ip_map[node_id] = node_ip
                    node_ssh_info_map[node_ip] = ssh_exec
                    node_ip_password_map[node_ip] = root_password
            logger.info("Node ID and IP Map %s", node_id_ip_map)
            break
        if choice == 'no':
            for node in response['results']:
                if 'manager_role' in node:
                    node_ip = \
                        node['manager_role']['api_listen_addr']['ip_address']
                    node_id = node['external_id']
                    root_password = get_root_password_from_user(node_ip)
                    # validate if ssh is working fine
                    try:
                        ssh_exec = SshCommandExecutor(node_ip, root_password)
                    except Exception:
                        print(f"Unable to SSH to Node '{node_ip}'. Please fix "
                              f"it and rerun the script")
                        logger.info("Unable to ssh to node %s, user needs to "
                                    "fix it and rerun the script", node_ip)
                        sys.exit(1)
                    node_id_ip_map[node_id] = node_ip
                    node_ssh_info_map[node_ip] = ssh_exec
                    node_ip_password_map[node_ip] = root_password
            logger.info("Node ID and IP Map %s", node_id_ip_map)
            break
        print("Invalid answer. Please enter 'Yes' or 'No'")


def check_if_file_exists(ssh_exec, file_path):
    stdout, _ = ssh_exec.exec_command("[ -f " + file_path + " ] && echo OK")
    if stdout.read():
        return True
    logger.info("File %s doesn't exist", file_path)
    return False


def get_cert_sha256_thumbprint(cert_str):
    cert = x509.load_pem_x509_certificate(
        cert_str.encode('utf-8'),
        default_backend()
    )
    sha256_thumbprint = canonical_thumbprint(hexlify(
        cert.fingerprint(hashes.SHA256())).decode('utf-8'))
    return sha256_thumbprint


def get_entity_id(cert_type, node_ip):
    if cert_type not in cbm_cert_path_dict:
        return None
    entity_id_path = (CBM_CERT_ROOT_PATH + cbm_cert_path_dict[cert_type] +
                      CBM_CERT_ENTITYID_PATH)
    ssh_exec = node_ssh_info_map[node_ip]
    cmd = 'cat %s 2>/dev/null' % entity_id_path
    stdout, stderr = ssh_exec.exec_command(cmd)
    cmd_error = stderr.read().decode().strip()
    if cmd_error:
        logger.info("Error encountered while running command  %s on node %s, "
                    "error : ", cmd, node_ip, cmd_error)
        raise RuntimeError(f"Failed to get entityId of service "
                           f"{cbm_cert_path_dict[cert_type]} and node"
                           f" '{node_ip}' ")
    entity_id = stdout.read().decode().strip()
    logger.info("EntityId corresponding to cert_type %s on node %s is %s",
                cert_type, node_ip, entity_id)
    return entity_id


def canonical_thumbprint(thumbprint):
    """Converts to canonical form so that thumbprints can be compared.
    """
    return thumbprint.lower().replace(':', '')


def validate_keystore(expected_sha256_thumbprint, cert_type, node_ip):
    if cert_type not in cbm_cert_path_dict:
        return
    print(f"Validating keystore post replacement of '{cert_type}' cert on node"
          f" '{node_ip}'")
    logger.info("Validating keystore post replacement of %s cert on node %s",
                cert_type, node_ip)
    ssh_exec = node_ssh_info_map[node_ip]

    keystore_file = CBM_CERT_ROOT_PATH + cbm_cert_path_dict[
        cert_type] + CBM_CERT_KEYSTORE_FILE
    keystore_password_file = CBM_CERT_ROOT_PATH + cbm_cert_path_dict[
        cert_type] + CBM_CERT_KEYSTORE_PASSWORD

    if not check_if_file_exists(ssh_exec, keystore_file):
        logger.info("Skipping keystore validations corresponding to %s cert "
                    "update on node %s, as certificate type"
                    " is not supported in this release", cert_type, node_ip)
        return
    cmd = 'keytool -list -v -alias self -keystore %s -storepass $(cat %s)' \
          ' 2>/dev/null | grep -i "SHA256:" | awk \'{print $2}\'' % \
          (keystore_file, keystore_password_file)

    i = 0
    keystore_sha256_thumbprint = ""
    while True:
        if i == 180:
            print(f"\nKeystore is not updated post replacement of "
                  f"'{cert_type}' cert on node '{node_ip}'."
                  f" [Expected thumbprint : {expected_sha256_thumbprint},"
                  f" Keystore thumbprint : {keystore_sha256_thumbprint}]")
            print('Exiting after a 15 minutes wait for certificate to be'
                  ' applied')
            logger.error("Keystore is not updated post replacement of %s cert"
                         " on node %s. [Expected thumbprint : %s, Keystore "
                         "thumbprint : %s]. Exiting after retrying for 15 "
                         "minutes", cert_type, node_ip,
                         expected_sha256_thumbprint,
                         keystore_sha256_thumbprint)
            sys.exit(1)
        stdout, stderr = ssh_exec.exec_command(cmd)
        # Handle error cases
        cmd_error = stderr.read().decode().strip()
        if cmd_error:
            logger.info("Error encountered while running command  %s on node "
                        "%s, error : %s", cmd, node_ip, cmd_error)
            raise RuntimeError(f"Failed to get sha256 thumbprint of cert "
                               f"{cert_type} and node '{node_ip}'")
        keystore_sha256_thumbprint = \
            canonical_thumbprint(stdout.read().decode().strip())
        if expected_sha256_thumbprint == keystore_sha256_thumbprint:
            logger.info("Keystore is correctly updated post replacement of %s"
                        " cert on node %s. [Expected thumbprint : %s, Keystore"
                        " thumbprint : %s]", cert_type, node_ip,
                        expected_sha256_thumbprint,
                        keystore_sha256_thumbprint)
            return
        logger.info("Keystore is not updated post replacement of %s cert"
                    " on node %s. [Expected thumbprint : %s, Keystore "
                    "thumbprint : %s]. Retrying in 5 secs",
                    cert_type, node_ip, expected_sha256_thumbprint,
                    keystore_sha256_thumbprint)
        if (i != 0) and (i % 6) == 0:
            print(f"Keystore is not updated post replacement of "
                  f"'{cert_type}' cert on node '{node_ip}'. "
                  f"[Expected thumbprint : {expected_sha256_thumbprint},"
                  f" Keystore thumbprint : {keystore_sha256_thumbprint}]. "
                  f"Rechecking ...")
        time.sleep(5)
        i += 1


def validate_truststore(target_service, target_node_ip, alias,
                        expected_sha256_thumbprint, cert_type, node_ip):
    if (cert_type not in cbm_cert_path_dict) or (target_service not in
                                                 cbm_cert_path_dict.values()):
        return
    print(f"Validating truststore of '{target_service}' on node "
          f"'{target_node_ip}' post replacement of cert '{cert_type}' on node"
          f" '{node_ip}'")
    logger.info("Validating truststore of  %s on node %s  post replacement of"
                " cert  %s on node %s",
                target_service, target_node_ip, cert_type, node_ip)
    ssh_exec = node_ssh_info_map[target_node_ip]

    truststore_file = (CBM_CERT_ROOT_PATH + target_service +
                       CBM_CERT_TRUSTSTORE_FILE)
    truststore_password_file = (CBM_CERT_ROOT_PATH + target_service +
                                CBM_CERT_TRUSTSTORE_PASSWORD)

    # Check for existence of keystore file, if file doesn't exist then skip
    if not check_if_file_exists(ssh_exec, truststore_file):
        logger.info("Skipping validations on truststore %s on node %s, as "
                    "this truststore is not supported in this release",
                    target_service, target_node_ip)
        return
    cmd = 'keytool -list -v -alias %s -keystore %s -storepass $(cat %s) ' \
          '2>/dev/null | grep -i "SHA256:" | awk \'{print $2}\'' % \
          (alias, truststore_file, truststore_password_file)

    i = 0
    truststore_sha256_thumbprint = ""
    while True:
        if i == 180:
            print(f"\nUpdate of '{cert_type}' cert on node '{node_ip}' is not"
                  f" reflected in truststore of '{target_service}' on node "
                  f"{target_node_ip}. [Expected thumbprint : "
                  f"{expected_sha256_thumbprint}, Truststore thumbprint :"
                  f" {truststore_sha256_thumbprint}]")
            print('Exiting after a 15 minute wait for certificate to be '
                  'applied')
            logger.error("Update of %s cert on node %s is not reflected in "
                         "truststore of %s on node %s. [Expected thumbprint :"
                         " %s, Truststore thumbprint : %s]. Exiting after "
                         "retrying for 15 minutes", cert_type, node_ip,
                         target_service, target_node_ip,
                         expected_sha256_thumbprint,
                         truststore_sha256_thumbprint)
            sys.exit(1)
        stdout, stderr = ssh_exec.exec_command(cmd)
        # Handle error cases
        cmd_error = stderr.read().decode().strip()
        if cmd_error:
            logger.info("Error encountered while running command  %s on node"
                        " %s, error : ", cmd, node_ip, cmd_error)
            raise RuntimeError(f"Failed to get sha256 thumbprint of alias"
                               f" {alias} from truststore of service "
                               f"{target_service} and node {target_node_ip}")
        truststore_sha256_thumbprint = \
            canonical_thumbprint(stdout.read().decode().strip())
        if expected_sha256_thumbprint == truststore_sha256_thumbprint:
            logger.info("Update of %s cert on node %s is correctly reflected "
                        "in truststore of %s on node %s. [Expected thumbprint "
                        ": %s, Truststore thumbprint : %s] ", target_service,
                        target_node_ip, cert_type, node_ip,
                        expected_sha256_thumbprint,
                        truststore_sha256_thumbprint)
            return
        logger.info("Update of %s cert on node %s is not reflected in "
                    "truststore of %s on node %s. [Expected thumbprint : "
                    "%s, Truststore thumbprint : %s]. "
                    "Rechecking in 5 secs ... ", target_service,
                    target_node_ip, cert_type, node_ip,
                    expected_sha256_thumbprint,
                    truststore_sha256_thumbprint)

        if (i != 0) and (i % 6) == 0:
            print(f"Update of cert '{cert_type} on node '{node_ip}' is "
                  f"not reflected in truststore of '{target_service}' on "
                  f"node {target_node_ip}. [Expected thumbprint : "
                  f"{expected_sha256_thumbprint}, Truststore thumbprint :"
                  f" {truststore_sha256_thumbprint}]. Rechecking ...")
        time.sleep(5)
        i += 1


def validate_truststores_and_keystores(cert_str, cert_type, node_ip):
    if cert_type not in cbm_cert_path_dict:
        return
    print(f"Validating truststores and keystores post replacement "
          f"of certificate {cert_type} on node {node_ip}")
    logger.info("Validating truststores and keystores post replacement"
                " of certificate %s on node %s", cert_type, node_ip)
    expected_sha256_thumbprint = \
        canonical_thumbprint(get_cert_sha256_thumbprint(cert_str))

    # Validate keystore first
    validate_keystore(expected_sha256_thumbprint, cert_type, node_ip)
    entity_id = get_entity_id(cert_type, node_ip)

    if cert_type in cbm_client_cert_path_dict:
        # Validates corfu server truststores of all 3 nodes
        for _, target_service in cbm_server_cert_path_dict.items():
            for target_node_ip in node_ssh_info_map:
                validate_truststore(target_service, target_node_ip,
                                    entity_id, expected_sha256_thumbprint,
                                    cert_type, node_ip)
    elif cert_type in cbm_server_cert_path_dict:
        # Validates clients truststores of all 3 nodes (42 clients at max)
        for _, target_service in cbm_client_cert_path_dict.items():
            for target_node_ip in node_ssh_info_map:
                validate_truststore(target_service, target_node_ip,
                                    entity_id, expected_sha256_thumbprint,
                                    cert_type, node_ip)
    else:
        logger.error("Unknown CBM certificate type %s received on node %s. "
                     "Skipping truststore validations for this cert type",
                     cert_type, node_ip)


def validate_node_truststores_and_keystores(node_ip, updated_node_cert_info):
    for cert_type in updated_node_cert_info:
        cert_str = updated_node_cert_info[cert_type]
        validate_truststores_and_keystores(cert_str, cert_type, node_ip)


if __name__ == "__main__":

    print(WELCOME_MSG.format(VERSION))
    logger.info("Starting to execute replace_certs.py. Current script "
                "version is %s", VERSION)

    parser = argparse.ArgumentParser(description="replace_certs.py "
                                                 "argument parser")
    parser.add_argument("--disableDiskValidations", default=False,
                        action='store_true')
    args = parser.parse_args()
    logger.info("Cbm disk validation flag : %s", args.disableDiskValidations)
    if args.disableDiskValidations:
        ENABLE_DISK_VALIDATIONS_FOR_CBM = False
        CLUSTER_STABILIZATION_WAIT_TIME = 150
        RESTART_WORKAROUND_WAIT_TIME = 150
        CORFU_STABILIZATION_WAIT_TIME = 150
    logger.info("Flags and timeouts in use "
                "[ENABLE_DISK_VALIDATIONS_FOR_CBM : %s, "
                "CLUSTER_STABILIZATION_WAIT_TIME : %s,"
                " RESTART_WORKAROUND_WAIT_TIME : %s, "
                "CORFU_STABILIZATION_WAIT_TIME : %s, "
                "SHORT_WAIT_TIME : %s, LONG_WAIT_TIME : %s]",
                ENABLE_DISK_VALIDATIONS_FOR_CBM,
                CLUSTER_STABILIZATION_WAIT_TIME, RESTART_WORKAROUND_WAIT_TIME,
                CORFU_STABILIZATION_WAIT_TIME, SHORT_WAIT_TIME,
                LONG_WAIT_TIME)

    WORKAROUND = False
    PATH = 'trust-management/certificates'
    SCRIPT_START = datetime.datetime.now()

    if (sys.version_info.major < 3 or sys.version_info.major == 3 and
            sys.version_info.minor < 6):
        print('Your python version is too low. Please upgrade the python to '
              'at least 3.6.x')

    while True:
        choice = input('Do you want to continue (Yes/No)? ').strip().lower()
        if choice == 'yes':
            break
        if choice == 'no':
            sys.exit(1)
        print("Invalid answer. Please enter 'Yes' or 'No'")

    if not ask_backup_question():
        sys.exit(1)

    while True:
        vip = input("Enter IP address of one of the manager nodes: ")
        if validate_ipv4(vip):
            break
        print(f"{vip} is not a valid IP address. Try again")
        logger.info("Invalid IP %s provided", vip)

    while True:
        pwd1 = getpass.getpass("Enter the cluster's admin password " +
                               "(will not be displayed): ")
        pwd2 = getpass.getpass("To confirm,  re-enter the password " +
                               "(will not be displayed): ")
        if pwd1 == pwd2:
            break
        print("Passwords don't match. Try again")

    try:
        node_output = rest_api(vip, 'mp', 'GET', 'node',
                               pwd1).json()
        if 'product_version' in node_output:
            nsx_version = node_output['product_version']
            logger.info("NSX product version is %s", nsx_version)
        elif 'node_version' in node_output:
            nsx_version = node_output['node_version']
            logger.info("NSX node version is %s", nsx_version)
        else:
            print("Unable to determine the NSX version. Please ensure the IP "
                  "address and password is correct")
            logger.error("Invalid IP/Admin Password combination provided "
                         "for %s", vip)
            sys.exit(1)
    except RuntimeError:
        print("Unable to determine the NSX version. Please ensure the IP "
              "address and password is correct")
        logger.error("Invalid IP/Admin Password combination provided for %s",
                     vip)
        sys.exit(1)

    node_type = node_output['node_type']
    print(f"\nNode Type is {node_type}")

    last_dot_index = nsx_version.rfind('.')
    release = int(nsx_version[:last_dot_index].replace('.', ''))
    logger.info("Version of NSX Cluster %s is %s", vip, nsx_version)

    if release < 41000:
        print('This script is only applicable for NSX 4.1.0.0.0 or later')
        sys.exit(1)

    # Get root password of all 3 nodes and ensure ssh to nodes works fine
    # Else fail and ask user to correct this and rerun the script
    if ENABLE_DISK_VALIDATIONS_FOR_CBM:
        populate_cluster_nodes_ssh_info(vip, pwd1)

    print(f"\nYou are about to replace the certificates in cluster {vip}")
    choice = input('Do you want to continue (Yes/No): ').strip().lower()
    if choice != 'yes':
        print('You have chosen not to proceed')
        sys.exit(1)

    if release in (41020, 41000):
        logger.info("Release %s. Workaround will be applied post certificate "
                    "replacement", release)
        WORKAROUND = True
    if release in (41100, 41110):
        logging.info('Fixing permission issues in NSX 4.1.1.0.0 before '
                     'replacing certificates')
        print('Fixing permission issues in NSX 4.1.1.0.0 before replacing '
              'certificates')
        workaround_4110(vip, pwd1)
    if release >= 40000:
        logging.info('\nFixing APH and APH-AR file permissions\n ')
        print('Fixing APH and APH-AR file permissions')
        fix_and_check_aph_file_permissions(vip, pwd1)

    certs_out = rest_api(vip, 'mp', 'GET', PATH, pwd1).json()
    logger.info('Cluster certificate snapshot prior to replacement')
    logger.info("%s\n\n", json.dumps(certs_out, indent=2))
    simplified_certs = simplify_certs(certs_out['results'])

    site_id = get_local_site_id(vip, pwd1)
    node_ids = get_node_ids(vip, pwd1)
    all_local_node_ids = node_ids + [site_id]
    filtered_certs = filter_certs(simplified_certs, nsx_version,
                                  all_local_node_ids)
    sorted_certs = sort_certs(filtered_certs)
    logger.info('A simplified version of cluster certificate snapshot')
    logger.info("%s\n\n", json.dumps(sorted_certs, indent=2))
    record = script_name[:-3] + '_record.txt'

    sorted_cert_map = get_certs_mapped_by_nodeId(sorted_certs)
    node_type = get_node_type(vip, pwd1)

    if 'GM' in node_type:
        cbm_client_cert_path_dict.update({'CBM_GM': "gm"})
        del cbm_client_cert_path_dict['CBM_CCP']
        del cbm_client_cert_path_dict['CBM_IDPS_REPORTING']
        cbm_cert_path_dict.update({'CBM_GM': "gm"})
        del cbm_cert_path_dict['CBM_CCP']
        del cbm_cert_path_dict['CBM_IDPS_REPORTING']

    with open(record, 'a', encoding="utf-8") as record_file:
        len_nodes = len(sorted_cert_map)
        node_count = 0
        for node_id, sorted_certs in sorted_cert_map.items():
            node_count += 1
            print(f"Replacing certificates in use by node {node_id}")
            logger.info("Replacing certificates in use by node %s", node_id)
            updated_cbm_cert_info = {}
            cert_count = 0
            len_certs = len(sorted_certs)
            for cert in sorted_certs:
                cert_count += 1
                cert_type = cert['used_by']['service_types']
                if cert_type == 'CBM_CORFU' and 'GM' in node_type\
                        and release < 42000:
                    print(f"Skipping replacement of corfu server cert, "
                          f"CBM_CORFU, as node type is {node_type}")
                    logger.info("Skipping replacement of corfu server cert, "
                                "CBM_CORFU, as node type is %s", node_type)
                    continue
                print(f"Replacing certificate for {cert_type} ({cert_count}"
                      f"/{len_certs}) of node {node_id} "
                      f"({node_count}/{len_nodes})")
                logger.info("Replacing certificate for %s (%s/%s) of node %s"
                            " (%s/%s)", cert_type, cert_count, len_certs,
                            node_id, node_count, len_nodes)

                cert_chain = _read_cert_chain_from_pem(cert['pem_encoded'])
                leaf_cert = _get_leaf_cert(cert_chain)
                if not _is_cert_self_signed(leaf_cert):
                    print(f"Skipping CA-signed {cert_type} certificate")
                    logger.info("Skipping CA-signed %s certificate", cert_type)
                    continue
                # skip if cert expires after LEAD_DAYS days
                if (SCRIPT_START + datetime.timedelta(days=LEAD_DAYS) <
                        _cert_expiry(leaf_cert)):
                    print(f"Skipping because {cert_type} certificate expires "
                          f"after {LEAD_DAYS} days")
                    logger.info("Skipping because %s certificate expires "
                                "after %s days", cert_type, LEAD_DAYS)
                    continue
                cluster_stabilization(vip, pwd1)
                # Generate new cert
                EXPIRY_DAYS = 36500 if 'CBM' in cert_type else 825
                print(f"Generating a self-signed certificate with expiry of "
                      f"{EXPIRY_DAYS} days for certificate {cert_type}")
                logger.info("Generating a self-signed certificate with expiry "
                            "of %s days for certificate %s of node %s",
                            EXPIRY_DAYS, cert_type, node_id)
                new_crt, new_key = replicate_cert(cert['pem_encoded'],
                                                  EXPIRY_DAYS)
                payload = {'display_name': cert['display_name'],
                           'pem_encoded': new_crt.decode('utf-8'),
                           'private_key': new_key.decode('utf-8')}
                crt_id = rest_api(vip, 'mp', 'POST', PATH + '?action=import',
                                  pwd1, json.dumps(payload)).json()[
                    'results'][0]['id']
                # Generate API command
                if cert_type not in ['MGMT_CLUSTER', 'LOCAL_MANAGER',
                                     'GLOBAL_MANAGER', 'K8S_MSG_CLIENT']:
                    path1 = PATH + '/' + crt_id + '/?action=' + \
                            'apply_certificate&service_type=' + \
                            cert['used_by']['service_types'] + '&node_id=' + \
                            cert['used_by']['node_id']
                else:
                    path1 = PATH + '/' + crt_id + '/?action=' + \
                            'apply_certificate&service_type=' + \
                            cert['used_by']['service_types']
                time.sleep(2)

                rest_api(vip, 'mp', 'POST', path1, pwd1)
                replacement_time = time.time()
                record_file.write(json.dumps(payload, indent=2))
                try:
                    rest_api(vip, 'mp', 'DELETE', PATH + '/' + cert['id'],
                             pwd1)
                except RuntimeError as ex:
                    # DELETE can fail because the cert is still being used.
                    # Ignore the DELETE failure and continue.
                    print("Ignore DELETE API error because certificate is "
                          "still in use")

                if 'CBM' in cert_type:
                    updated_cbm_cert_info[cert['used_by']['service_types']]\
                        = new_crt.decode('utf-8')

                # Validate disk data
                if ENABLE_DISK_VALIDATIONS_FOR_CBM and 'CBM' in cert_type:
                    node_ip = node_id_ip_map[node_id]
                    validate_truststores_and_keystores(
                        new_crt.decode('utf-8'),
                        cert['used_by']['service_types'], node_ip)

                current_time = time.time()
                time_elapsed_secs = current_time - replacement_time

                if 'CBM' not in cert_type:
                    print(f"Sleeping for {SHORT_WAIT_TIME} seconds for update "
                          f"of certificate corresponding to {cert_type}")
                    logger.info("Sleeping for %s seconds for update of "
                                "certificate corresponding to %s",
                                SHORT_WAIT_TIME, cert_type)
                    time.sleep(SHORT_WAIT_TIME)
                if WORKAROUND and cert_type in ['CBM_AR',
                                                'CBM_CLUSTER_MANAGER']:
                    print(f"Sleeping for {RESTART_WORKAROUND_WAIT_TIME} "
                          f"seconds before restarting services for update of "
                          f"certificate corresponding to {cert_type}")
                    logger.info("Sleeping for %s seconds before restarting "
                                "services after update of certificate "
                                "corresponding to %s",
                                RESTART_WORKAROUND_WAIT_TIME, cert_type)
                    time.sleep(RESTART_WORKAROUND_WAIT_TIME)
                    workaround_4102(cert['used_by'], vip, pwd1)
                elif cert_type in critical_cbm_services[node_type]:
                    print(f"Sleeping for {LONG_WAIT_TIME} seconds post "
                          f"replacement of certificate {cert_type} "
                          f"to stabilize NSX API service")
                    logger.info("Sleeping for %s seconds post replacement of "
                                "certificate %s for NSX to stabilize",
                                LONG_WAIT_TIME, cert_type)
                    time.sleep(LONG_WAIT_TIME)
                    cluster_stabilization(vip, pwd1)
                elif cert_type in ['CBM_CORFU']:
                    if time_elapsed_secs < CORFU_STABILIZATION_WAIT_TIME:
                        WAIT_TIME = CORFU_STABILIZATION_WAIT_TIME - \
                                    time_elapsed_secs
                        print(f"Sleeping for {WAIT_TIME} seconds post "
                              f"replacement of certificate {cert_type} "
                              f"to stabilize corfu service")
                        logger.info("Sleeping for %s seconds post replacement "
                                    "of certificate %s for corfu to stabilize",
                                    WAIT_TIME, cert_type)
                        time.sleep(WAIT_TIME)
                    cluster_stabilization(vip, pwd1)
                elif 'CBM' in cert_type:
                    if time_elapsed_secs < SHORT_WAIT_TIME:
                        WAIT_TIME = SHORT_WAIT_TIME - time_elapsed_secs
                        print(f"Sleeping for {WAIT_TIME} seconds post "
                              f"replacement of certificate {cert_type} for "
                              f"update to process")
                        logger.info("Sleeping for %s seconds post replacement "
                                    "of certificate %s for update to "
                                    "process", WAIT_TIME, cert_type)
                        # Sleep for short time for service restart to get
                        # triggered
                        time.sleep(WAIT_TIME)

            is_cbm_cert_updated = any("CBM" in cert for cert in
                                      updated_cbm_cert_info.keys())

            print(f"Replaced all certificates of node {node_id}")
            logger.info("Replaced all certificates of node %s", node_id)

            is_critical_cbm_service_updated = \
                any(x in critical_cbm_services[node_type]
                    for x in updated_cbm_cert_info.keys())
            if is_cbm_cert_updated and not is_critical_cbm_service_updated:
                print(f"Waiting {CLUSTER_STABILIZATION_WAIT_TIME} for cluster "
                      f"status to stabilize")
                logger.info("Waiting %s for cluster status to stabilize",
                            CLUSTER_STABILIZATION_WAIT_TIME)
                time.sleep(CLUSTER_STABILIZATION_WAIT_TIME)
                cluster_stabilization(vip, pwd1)

    record_file.close()
    for node_id, ssh_exec in node_ssh_info_map.items():
        ssh_exec.close()
    cluster_stabilization(vip, pwd1)
    logger.info("Replaced all certificates in cluster %s. Cluster status is "
                "stable", vip)
    print(f"Replaced all certificates in cluster '{vip}'. Cluster status "
          f"is stable")
