# AVI VIP IPv6 Setup

- Add IPv6 subnet to Infrastructure > Networks > vfsinSrv-vips (prefix `::/0` and static IP range set to only VIPs)
- Enable IPv6 Auto Configuration in vfsinSrv-vips
- Add IPv6 ULA gateway to NSX LB inside segment (fd00:100::1/64)
- Enable ND Snooping (address limit 5), DHCP IPv6 and VMware Tools IPv6 v6 in segment IP discovery profile
- Disable firewalld in VMs

```bash
systemctl stop firewalld
systemctl disable firewalld
systemctl mask firewalld
```

- Set following on LB inside interface on VMs:

```bash
nmcli con mod ens224 ipv6.addr-gen-mode eui64
nmcli con mod ens224 ipv6.ignore-auto-routes yes
nmcli con mod ens224 +ipv6.routes "fd00:100::/64 fd00:100::1"
nmcli con down ens224
nmcli con up ens224
```

- Add IPv6 address (fd00 one) of ens224 to the pool member list (syntax requires square brackets around IPv6 address e.g. `[fd00:100::250:56ff:fe9e:e8f2]:443`)
- Add IPv6 VIP to the existing VS VIP
