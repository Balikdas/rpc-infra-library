# vCenter Certificate Renewal Procedure

## 1 vCenter Certificate renewal on the vCenter Appliance

1. SSH to the vCenter appliance as root
2. Run Certificate Manager `/usr/lib/vmware-vmca/bin/certificate-manager`
3. Select option 8 `Reset all Certificates`
4. When asked to generate using configuration file choose Y then provide SSO credentials for example `Administrator@vsphere.local`
5. Enter values as prompted (change the vcenter fqdn accordingly)

```bash
Enter proper value for 'Country' [Default value : US] : CA
Enter proper value for 'Name' [Default value : CA] : rncc-vc-cp-sde-wlfdle-az02.cc.net.rogers.com
Enter proper value for 'Organization' [Default value : VMware] : Rogers Communications Inc
Enter proper value for 'OrgUnit' [optional] : Network Infra Platform Systems
Enter proper value for 'State' [Default value : California] : Ontario
Enter proper value for 'Locality' [Default value : Palo Alto] : Toronto
Enter proper value for 'IPAddress' (Provide comma separated values for multiple IP addresses) [optional] :
Enter proper value for 'Email' [Default value : email@acme.com] : network-infra-dl@rci.rogers.com
Enter proper value for 'Hostname' (Provide comma separated values for multiple Hostname entries) [Enter valid Fully Qualified Domain Name(FQDN), For Example: example.domain.com]: rncc-vc-cp-sde-wlfdle-az02.cc.net.rogers.com
Enter proper value for VMCA 'Name' : rncc-vc-cp-sde-wlfdle-az02.cc.net.rogers.com
Continue operation : Option[Y/N] ? : Y

You are going to reset by regenerating Root Certificate and replace all certificates using VMCA
Continue operation : Option[Y/N] ? : Y
```

## 2 Trust new Certs on Connected Endpoints

### 2.1 Common to All Environments (OneCloud, Telco, RNCC-SDE, RCMIN)

#### 2.1.1 VMware Aria Operations (use local admin only)

1. Sign in to the vROps UI using the local account username `admin`
2. Navigate to Administration - Integrations - vCenter - open the vCenter adapter instance
3. Choose Edit then Validate Connection
4. When prompted review details and Accept certificate then Save enable collection if needed

#### 2.1.2 VMware Aria Operations for Logs (vRLI)

1. Open Integrations - vSphere
2. Edit and do Test connection
3. Enter credentials then Accept certificate and Save

#### 2.1.3 NSX-T

1. In NSX Manager open System then Fabric then Compute Managers
2. Select the vCenter entry then Edit
3. Provide credentials if requested then Accept certificate or thumbprint and Save
4. Confirm Connection Status is Up

#### 2.1.4 VMware Aria Operations for Networks (vRNI)

1. Open Settings then Accounts and Data Sources
2. Select the vCenter data source then Edit and Re authenticate
3. Enter credentials then Accept certificate and Submit

#### 2.1.5 vRealize Automation (vRA)

1. Sign in to the Aria Automation UI
2. Go to Assembler - Infrastructure - Connections then Cloud Accounts
3. Open the vCenter cloud account then Re-enter the vCenter service account password - click validate
4. When prompted Accept certificate
5. Save and verify the account status

### 2.2 OneCloud Environment Only

#### 2.2.1 TCA Control Plane (TCA-CP) on 9443

1. Log in to TCA appliance manager at `https://<tca-cp-ip>:9443` (tca-cp or tca-wl based on the vCenter)
2. Go to Dashboard - vCenter - Manage - Edit
3. Provide credentials if requested then Accept certificate or thumbprint and Save.

#### 2.2.2 Updating vCenterprime on TKG clusters

1. SSH to TCA CP as admin `ssh admin@<tca-cp-ip>`
2. Retrieve helper script from here: [update-vc-thumbprint.sh](../../scripts/tanzu_k8s/update-vc-thumbprint.sh)
3. Run the update against the vCenter `./update-vc-thumbprint.sh -d <vcenter-fqdn-or-ip> -v`
4. If management clusters and workload clusters use different vCenters run step 4 once per vCenter first the management vCenter then the workload vCenter
5. In TCA-M open Connected Endpoints find the vCenter verify the status reflects the certificate change then dismiss the banner that acknowledges the change

#### 2.2.3 vRO CLI - only when CP vCenter certificate renews

1. SSH to the vROv appliance as root
2. Start the wizard `vracli vro authentication wizard`
3. Select 2 for vSphere
4. Enter values as prompted (Change the vCenter FQDN accordingly)

    ```bash
    Enter the hostname for the authentication provider: rncc-vc-cp-sde-wlfdle-az02.cc.net.rogers.com
    Enter an administrator username to authenticate with the provider: svc-vro-vsphere@oss.rogers.com
    Enter the password for svc-vro-vsphere@oss.rogers.com:
    Enter the domain for the Administrator group (i.e. vsphere.local): vsphere.local
    Enter the Administrator group name: Administrators

    Do you wish to accept the certificate? [YIN]; y
    ```

5. When prompted choose y to accept the certificate
6. After making any authentication changes, you must run the `/opt/scripts/deploy.sh` script so the change to the Automation Orchestrator Appliance is applied.
