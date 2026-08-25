# Fix vCenter vpxd session timeout

The vCenter API via vpxd that is used by Tanzu and other components can experience session exhaustion with the default settings. Changing the session timeout to 30 minutes and allowing up to 10,000 connections is usually sufficient but the numbers can be adjusted as required.

## Procedure

* SSH to the vCenter and edit the vpxd.cfg file:

```bash
vi /etc/vmware-vpx/vpxd.cfg
```

* Inside the `<vmacore>` block, add the following `<soap>` block:

```bash
  <vmacore>
    [...]
    <soap>
      <sessionTimeout>30</sessionTimeout>
      <maxSessionCount>10000</maxSessionCount>
    </soap>
    [...]
  </vmacore>
```

* Also replace the `<threadPool>` block with the following:

```bash
    <threadPool>
      <TaskMax>1024</TaskMax>
      <threadNamePrefix>vpxd</threadNamePrefix>
    </threadPool>
```

* Increase the RAM allocated to VPXD service to 32G:

```bash
cloudvm-ram-size -C 32768 vmware-vpxd
```

* Restart the vpxd service:

```bash
service-control --stop vmware-vpxd && service-control --start vmware-vpxd
```
