# Update Prisma Defender Version

## Production Procedure

- Run the below commands and replace the image tag with the appropriate image version:

```bash
docker pull registry-auth.twistlock.com/tw_j0lbkfh0m7cgfbxp0x1w7vn7jn2k7kk7/twistlock/defender:defender_33_03_138
docker tag registry-auth.twistlock.com/tw_j0lbkfh0m7cgfbxp0x1w7vn7jn2k7kk7/twistlock/defender:defender_33_03_138 harbor.cc.net.rogers.com/prisma/defender:defender_33_03_138
docker tag registry-auth.twistlock.com/tw_j0lbkfh0m7cgfbxp0x1w7vn7jn2k7kk7/twistlock/defender:defender_33_03_138 harbor.cc.net.rogers.com/prisma/defender:latest
docker push harbor.cc.net.rogers.com/prisma/defender:defender_33_03_138
docker push harbor.cc.net.rogers.com/prisma/defender:latest
```

- Restart all pods in the `twistlock` namespace on each workload TKG cluster

## Lab Procedure

- Run the below commands and replace the image tag with the appropriate apiVersion:

```bash
docker pull registry-auth.twistlock.com/tw_j0lbkfh0m7cgfbxp0x1w7vn7jn2k7kk7/twistlock/defender:defender_33_03_138
docker tag registry-auth.twistlock.com/tw_j0lbkfh0m7cgfbxp0x1w7vn7jn2k7kk7/twistlock/defender:defender_33_03_138 harbor.cc.vf.rogers.com/prisma/defender:defender_33_03_138
docker tag registry-auth.twistlock.com/tw_j0lbkfh0m7cgfbxp0x1w7vn7jn2k7kk7/twistlock/defender:defender_33_03_138 harbor.cc.vf.rogers.com/prisma/defender:latest
docker push harbor.cc.vf.rogers.com/prisma/defender:defender_33_03_138
docker push harbor.cc.vf.rogers.com/prisma/defender:latest
```

- Restart all pods in the `twistlock` namespace on each workload TKG cluster
