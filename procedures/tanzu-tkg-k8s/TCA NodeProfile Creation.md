# TCA NodeProfile Template Creation

TCA NodeProfiles are used to ensure the node customization is kept in sync in a declarative way. It uses nodeconfig operator to handle configuration of the nodes via the CRD `nodepolicies.acm.vmware.com` and Kind `NodePolicy`.

The NodeProfile template needs to be loaded into the TCA-M node, and then they are available to be applied to Node Pools in TCA UI.

## Login to TCA API

* Login to the TCA API and get the value of the `x-hm-authorization` header returned:

```bash
curl -v -k -H "Accept: application/json" -H "Content-Type: application/json" -d '{"username": "${oss_ad_username}@oss.rogers.com", "password": "${oss_ad_password}"}' https://tca.cc.net.rogers.com/tca/global/api/v1/sessions
```

## Get All Current NodeProfile Templates

* Query TCA to get all existing NodeProfile templates, which can be used as a template.

```bash
curl -k -H "Accept: application/json" -H "x-hm-authorization: ${value_of_x-hm-authorization_header}" https://tca.cc.net.rogers.com/tca/caas/api/v3/orgs/default/policyprofiles?type=nodeprofile
```

## Create New NodeProfile Template

* Copy and paste an existing NodeProfile template in to a JSON file, and remove the metadata fields `uid`, `generation`, `creationTimestamp`, `updateTimestamp`, `creationTenantId` and set the value of the label `telco.vmware.com/preloaded` to `false`.

* Save the file and send a POST to the TCA API to create the policy:

```bash
curl -k -X POST -H "Content-Type: application/json" -H "Accept: application/json" -H "x-hm-authorization: ${value_of_x-hm-authorization_header}" -d @${json_file_path}$ https://tca.cc.net.rogers.com/tca/caas/api/v3/orgs/default/policyprofiles
```

## Delete a NodeProfile Template

* To delete an existing NodeProfile template, first it must not be in use by any existing node pools, then send a DELETE to the API with the UID of the NodeProfile template being deleted in the URL path:

```bash
curl -k -X DELETE -H "Accept: application/json" -H "x-hm-authorization: ${value_of_x-hm-authorization_header}" https://tca.cc.net.rogers.com/tca/caas/api/v3/orgs/default/policyprofiles/${uid_of_profile_to_delete}
```

## Example TCA NodeProfile Template

The below example should work well in any scenario as it allows to use raw YAML to create the NodeProfile template. This is the template used in RNCC lab and prod.

```json
{
  "metadata": {
    "name": "rncc-nodepolicy-template",
    "labels": {
      "telco.vmware.com/owner": "caas",
      "telco.vmware.com/preloaded": "false"
    }
  },
  "spec": {
    "type": "nodeprofile",
    "version": "1.0.0",
    "variables": [
      {
        "name": "raw_nodepolicy_spec",
        "schema": {
          "openAPIV3Schema": {
            "properties": {
              "spec": {
                "description": "NodePolicySpec YAML",
                "UICustomizedName": "NodePolicy Spec",
                "UIRenderType": "rawyaml",
                "default": "# The below are examples only. For details of what values are accepted, refer \n# to the CRD \"nodepolicies.acm.vmware.com\" on the TKG Management Cluster.\n# \n# Author: K. McColm \n# Date: 2026-07-16\n\nfileInjection:\n  - path: \"/etc/chrony.conf\"\n    fileMode: \"0644\"\n    fileOwner: \"root:root\"\n    postAction: \"systemctl enable chronyd && systemctl restart chronyd\"\n    content: |\n      server 172.19.254.12\n      driftfile /var/lib/chrony/drift\n      makestep 1.0 3\n      rtcsync\n      ntsdumpdir /var/lib/chrony\n      logdir /var/log/chrony\n\n  - path: /etc/sysctl.d/99-tca-node-customization.conf\n    fileMode: \"0644\"\n    fileOwner: \"root:root\"\n    postAction: \"systemctl restart systemd-sysctl\"\n    content: |\n      vm.max_map_count = 262144\n\n  - path: /etc/modules-load.d/99-tca-node-customization.conf\n    fileMode: \"0644\"\n    fileOwner: \"root:root\"\n    postAction: \"systemctl restart systemd-modules-load\"\n    content: |\n      sctp\n\n  - path: \"/root/custom_script.sh\"\n    fileMode: \"0750\"\n    fileOwner: \"root:root\"\n    postAction: \"/root/custom_script.sh\"\n    content: |\n      #!/bin/bash\n      mkdir -p -m 700 /var/lib/consul\n      chown 100:1000 /var/lib/consul\n"
              }
            }
          }
        }
      }
    ],
    "templates": [
      {
        "name": "template.yaml",
        "resources": "#@ load(\"@ytt:data\", \"data\")\n#@ load(\"@ytt:template\", \"template\")\n\napiVersion: acm.vmware.com/v1alpha1\nkind: NodePolicy\nspec: #@ data.values.raw_nodepolicy_spec.spec"
      }
    ]
  }
}
```
