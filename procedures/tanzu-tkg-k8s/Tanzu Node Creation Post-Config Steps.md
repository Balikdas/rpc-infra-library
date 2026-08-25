# Tanzu Node Creation Post-Config Steps

This document walks you through the post-provisioning tasks for the newly created Tanzu Kubernetes Grid (TKG) nodes.

**Note:** Before the activity, take screenshots of the current `AppId:Kubernetes` and `AppId:<$appId>` tags for all relevant VMs. The screenshots must have the 'Tag name', 'Scope' and 'Assigned to' VMs as displayed in NSX. This ensures that after the update, you can verify not only the number of tags but also that the correct tags with the correct scopes have been applied.

## 1. Apply NSX Tags

1. Log in to the NSX Global Manager UI.
2. Switch to **Local Manager** for your site → **Inventory** → **Tags**.
3. Locate the tags `AppId:Kubernetes` and `AppId:<$appId>` from your pre‑change screenshots.
4. Edit the following tags -> and add the newly created VMs.
   - `AppId:Kubernetes`
   - `AppId:<$appId>`
5. **Verify the scope** of each `AppId:<$appId>` tag matches the pre‑change state.
6. Assign each tag to the appropriate newly provisioned control‑plane and worker VMs.
7. If a tag is missing, re‑create it using the exact tag name and original scope, then assign it to the correct VMs as per the pre‑change configuration.

## 2. Disable VMware Tools Time Sync

1. Log in to your vCenter instance for the corresponding AZ.
2. Locate each newly provisioned VM and open the VMware Tools settings.
3. Uncheck **Synchronize Time Periodically**.

## 3. Run vRO Workflows

For each cluster, ensure to run ntp workflow (common for all clusters) + application specific workflows.

1. Log in to VMware vRealize Orchestorator (vRO) for the specific site.
2. Go to **Library** → **Workflows** -> **PSO** folder -> Expand **VMware Telco Cloud Orchestrator**
3. Choose either `runOnWorkers` (only workers) or `runOnAll` (control plane + workers) or `runOnMaster` (only control plane)
4. Fill out the Master node IP/Endpoint IP of the cluster, capv as the user name and password.
5. Under workflows, enter **common.ntp** workflow name.
6. If the application requires additional configurations (e.g., custom nodepool configurations), trigger its associated workflow for the new worker nodes. Each application that requires custom workflow will have a separate folder containing the workflows.
