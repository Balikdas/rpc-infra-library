# Procedure for Updating TLS Certs on RNCC Elements

This document outlines the procedure for installing the RNCC Root CA on all RNCC elements (including workload VMs), as well as rotating RNCC management domain leaf certificates for each individual RNCC element.

The intent of installing the Root CA across all RNCC elements is to ensure that the leaf certificates signed by the RNCC Root CA (via it's intermediate CA) will be implicitly trusted by all network elements.

## Document Index

<!-- TOC -->

- [Procedure for Updating TLS Certs on RNCC Elements](#procedure-for-updating-tls-certs-on-rncc-elements)
  - [Document Index](#document-index)
  - [List of Targets for Root CA](#list-of-targets-for-root-ca)
    - [VMware vSphere/NSX Control Plane & Aria Suite VMs](#vmware-vspherensx-control-plane--aria-suite-vms)
    - [RedHat VMs](#redhat-vms)
    - [HPE OneView VMs](#hpe-oneview-vms)
    - [Backup Infra VMs](#backup-infra-vms)
    - [Windows VMs](#windows-vms)
    - [AVI Load Balancer VMs](#avi-load-balancer-vms)
    - [Tanzu Infrastructure VMs](#tanzu-infrastructure-vms)
    - [RNCC Utility VMs](#rncc-utility-vms)
  - [Individual Platform Root CA Install Procedure](#individual-platform-root-ca-install-procedure)
    - [vIDM](#vidm)
    - [vLCM](#vlcm)
    - [vRA](#vra)
    - [vRLI](#vrli)
    - [vRNI](#vrni)
    - [vROPS](#vrops)
    - [vCenters](#vcenters)
    - [vCD](#vcd)
    - [NSX Managers](#nsx-managers)
    - [RHEL Satellite](#rhel-satellite)
    - [HPE OneView](#hpe-oneview)
    - [AVI Load Balancer](#avi-load-balancer)
    - [TCA Appliances](#tca-appliances)
    - [Ubuntu Jumpboxes](#ubuntu-jumpboxes)

<!-- /TOC -->

## List of Targets for Root CA

Below are the network elements that require installation for the RNCC Root CA to be able to trust leaf certs signed by the CA.

### VMware vSphere/NSX Control Plane & Aria Suite VMs

- vIDM
- vLCM
- vRA
- vRLI
- vRNI
- vROPS
- vCenter
- vCD
- NSX Managers

### RedHat VMs

- Satellite
- RHEL Guest OS (VMs registered to Satellite)
- OCP Clusters

### HPE OneView VMs

- Global Dashboard
- OneView appliances
- ILO's (requires automation loop)

### Backup Infra VMs

- CommVault appliances
- CommVault VSA's

### Windows VMs

- Windows GuestOS (VMs registered to OSS-AD)

### AVI Load Balancer VMs

- AVI Control Planes

### Tanzu Infrastructure VMs

- TCA Appliances
- TKG management clusters (also disabling TLS verification on vsphere-cpi)
- TKG workload clusters (also disabling TLS verification on vsphere-cpi)
- Pinniped configurations
- Kapp controller configmaps
- Harbor registry instances (GuestOS and Docker containers)
- vRO Instances

### RNCC Utility VMs

- Bastion VMs
- DHCP VMs
- Jump servers (Ubuntu and Windows)
- Web servers
- Proxy servers
- vSphere/NSX backup servers

[Back to Index](#document-index)

## Individual Platform Root CA Install Procedure

The below steps are to install the RNCC Production or VF Lab Root CA to the nodes so that all the certs signed by the CA will be implicitly trusted. This should only be needed once every time the Root CA cert is rotated, such as if it has been revoked and regenerated, or after it expires in the year 2051.

### vIDM

- Login to vIDM admin console as any user with admin privs
- Navigate to Appliance Settings > Manage Configuration
- Enter the vIDM root password
- Navigate to Install SSL Certificates > Trusted CAs
- Paste the content of the Root CA and click Add

### vLCM

- Login to all vLCM appliances as root user
- Create a file `RNCC-Production-Root-CA.pem` (for prod) or `RNCC-VF-Lab-Root-CA.pem` (for lab) and populate it with the PEM formated CA
- Run the below command to import the cert. The keystore password is `changeit`

```bash
# Prod
/usr/java/jre-vmware/bin/keytool -importcert -alias "RNCC Production Root CA" -keystore /usr/java/jre-vmware/lib/security/cacerts -file RNCC-Production-Root-CA.pem

# Lab
/usr/java/jre-vmware/bin/keytool -importcert -alias "RNCC VF Lab Root CA" -keystore /usr/java/jre-vmware/lib/security/cacerts -file RNCC-VF-Lab-Root-CA.pem
```

### vRA

- Once the vRA application is back up, login to the UI and open the embedded vRO application
- Navigate to Workflows > Library > Configuration > SSL Trust Manager and run the workflow named "Import a trusted certificate from a file"
- Login to all vRA nodes as root via SSH
- Create a file named `RNCC-Production-Root-CA.pem` (prod) or `RNCC-VF-Lab-Root-CA.pem` (lab) in the `/etc/ssl/certs` directory and paste the content of the PEM formatted CA
- Run the `rehash_ca_certificates.sh` command
- Run the commands below to import the CA to the VRA Keystore:

```bash
# Prod
mkdir /usr/share/ca-certificates/
base64 -w0 /etc/ssl/certs/RNCC-Production-Root-CA.pem > /usr/share/ca-certificates/RNCC-Production-Root-CA.pem

# Lab
mkdir /usr/share/ca-certificates/
base64 -w0 /etc/ssl/certs/RNCC-VF-Lab-Root-CA.pem > /usr/share/ca-certificates/RNCC-VF-Lab-Root-CA.pem
```

- On the first vRA node, run the command `/opt/scripts/deploy.sh` to redeploy the vRA application

### vRLI

- Login to vRLI UI with a user that has admin privileges
- Navigate to Management > Certificates
- Click "Add New Certificate" and upload the PEM formatted Root CA file and name it `RNCC Production Root CA` (prod) or `RNCC VF Lab Root CA` (lab)

### vRNI

- Login to all vRNI nodes via SSH as `support` user and perform `sudo su -` to elevate to root.
- Copy the root CA for the appropriate environment (VF Lab or Prod) to the `/usr/local/share/ca-certificates/` directory
- Execute the command `update-ca-certificates` and then `reboot`

### vROPS

- Login to the vROPS UI as the local admin user (not your OSS-AD user)
- Navigate to Administration > Control Panel > Trusted Certificates
- Click Import and upload the file with the content of the Root CA

### vCenters

- Login to all vCenters UI as a user with administrator privs
- Click the Menu hamburger on the top left and navigate to Administration > Certificate Management > Trusted Root
- Click Add Trusted Root Certificate and upload the file with the contents of the Root CA

### vCD

- Login to the vCD Provider UI as a user with admin privs
- Navigate to Administration > Certificate Management > Trusted Certificates
- Click Import and upload the file with the contents of the Root CA, using Friendly Name as `RNCC-Production-Root-CA` (prod) or `RNCC-VF-Lab-Root-CA` (lab)

### NSX Managers

- Login to all NSX UIs as a user with admin privs
- Navigate to System > Certificates
- Click Import > CA Certificate
- Enter the following values:
  - Name: `RNCC Production Root CA` (prod) or `RNCC VF Lab Root CA` (lab)
  - Service Certificate: No
  - Certificate contents: Paste the PEM formatted CA or upload it as a file
  - Description: Leave blank
- Click Save

### RHEL Satellite

- Login to all RHEL Satellite servers via SSH with your OSS-AD credentials and `sudo -i` to root
- Create a file named `RNCC-Production-Root-CA.crt` (prod) or `RNCC-VF-Lab-Root-CA.crt` (lab) in the `/etc/pki/ca-trust/source/anchors` directory and paste the PEM formatted content of the CA
- Run the `update-ca-trust extract` command to install the CA

### HPE OneView

- Login to all HPE OneView Global Dashboard appliances as a user with admin privs
- Navigate to Settings > Certificate Trust Store
- Click the hamburger on the top right and select Add
- Paste the PEM formatted content of the CA and click Validate Certificate and then click Add
- Login to all HPE OneView appliances UI's as a user with admin privs
- Navigate to Settings > Security > Manage Certificates
- Click Add Certificates
- Paste the PEM formatted content of the Root CA and click Validate Certificate and then click Add

### AVI Load Balancer

- Login to all AVI UI's as a user with admin privs
- Navigate to Templates > Security > SSL/TLS Certificates
- Click Create > Root/Intermediate CA Certificate
- Enter the following vaules:
  - Name: `RNCC Production Root CA` (prod) or `RNCC VF Lab Root CA` (lab)
  - Certificate: Paste the PEM formatted content of the CA and click Validate then click Save

### TCA Appliances

**Note: TCA requires the Intermediate CA as well as the Root CA (i.e. the full CA chain) to trust the leaf certs signed by the Intermediate CA.**

- Login as `tca` user to the admin UI of all TCA appliances (port 9443 interface)
- Navigate to Administration > Trusted CA Certificate and click Import
- Select the Content radio button and paste the PEM formatted content of the Intermediate CA followed by the Root CA then click Apply
- Reboot the appliance

### Ubuntu Jumpboxes

- Login to all Ubuntu Jumpboxes as root user and create a file named `RNCC-Production-Root-CA.crt` (prod) or `RNCC-VF-Lab-Root-CA.crt` (lab) in the `/usr/local/share/ca-certificates/` directory and paste the content of the PEM formatted CA
- Run the `update-ca-certificates` command to install the CA

[Back to Index](#document-index)
