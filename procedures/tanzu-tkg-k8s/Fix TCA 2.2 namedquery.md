# Fix TCA 2.2 namedquery

```javascript
db.namedquery.update(
  { name: "getVnfs" },
  {
    $set: {
      body: '{"collection":"Vnf","pipeline":[{"$match":{"$and":[{"$or":[{"\_id":{"$exists":"{{SKIP_VNF_INSTANCE_ID}}"}},{"id":{"$in":["{{VNF_INSTANCE_ID}}"]}}]},{"$or":[{"_id":{"$exists":"{{SKIP_VNF_INSTANCE_NAMES}}"}},{"vnfInstanceName":{"$in":["{{VNF_INSTANCE_NAMES}}"]}},{"nfInstanceName":{"$in":["{{VNF_INSTANCE_NAMES}}"]}}]},{"$or":[{"_id":{"$exists":"{{SKIP_vnfdId}}"}},{"vnfdId":"{{vnfdId}}"},{"descriptorId":"{{vnfdId}}"}]},{"$or":[{"_id":{"$exists":"{{SKIP_vimId}}"}},{"vimConnectionInfo.id":"{{vimId}}"}]},{"$or":[{"_id":{"$exists":"{{SKIP_rowType}}"}},{"rowType":"{{rowType}}"}]},{"$or":[{"_id":{"$exists":"{{SKIP_vimArray}}"}},{"vimConnectionInfo.id":{"$in":["{{vimArray}}",["0"]]}}]},{"$or":[{"_id":{"$exists":"{{SKIP_instantiationState}}"}},{"instantiationState":"{{instantiationState}}"}]}]}},{"$project":{"id":1,"rowType":1,"orchType":1,"deploymentName":1,"vnfInstanceName":1,"nfInstanceName":1,"vnfdId":1,"descriptorId":1,"vnfProvider":1,"nfProvider":1,"vnfProductName":1,"nfProductName":1,"vnfdVersion":1,"descriptorVersion":1,"vnfPkgId":1,"nfPkgId":1,"instantiationState":1,"instantiatedVnfInfo":1,"instantiatedNfInfo":1,"managedBy":{"$ifNull":["$managedBy",{"$literal":{"extensionSubtype":"VMWARE-TELCO-GVNFM","extensionName":"VMware"}}]},"lastUpdated":1,"creationDate":1,"creationUser":1,"creationEnterprise":1,"creationOrganization":1,"lcmOperation":1,"lcmOperationState":1,"vimConnectionInfo":1,"nfType":1,"tags":1,"\_links":1,"vnfSoftwareVersion":1,"vnfCatalogName":1}}]}',
    },
  },
);
```
