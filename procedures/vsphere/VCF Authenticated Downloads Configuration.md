# VCF Authenticated Downloads Configuration

This document outlines how to configure VCF authenticated downloads on vCenter. The full procedure is documented in this KB: <https://knowledge.broadcom.com/external/article/390098>

- VCF Token (do not share outside our team): `xPPJUp0ioMKx348YGoT2ZcQZfRVAGuFI`

## VAMI Configuration

- Follow the steps in this KB: <https://knowledge.broadcom.com/external/article/390120>
- Update VAMI with the below URL (replace `${version}` with the vCenter version, e.g. `8.0.3.00500`)

```bash
https://dl.broadcom.com/xPPJUp0ioMKx348YGoT2ZcQZfRVAGuFI/PROD/COMP/VCENTER/vmw/8d167796-34d5-4899-be0a-6daade4005a3/${version}
```

## vCenter Configuration

- Follow the steps in this KB: <https://knowledge.broadcom.com/external/article/390121>
- Update vLCM with the following URLs:

```bash
https://dl.broadcom.com/xPPJUp0ioMKx348YGoT2ZcQZfRVAGuFI/PROD/COMP/ESX_HOST/main/vmw-depot-index.xml
https://dl.broadcom.com/xPPJUp0ioMKx348YGoT2ZcQZfRVAGuFI/PROD/COMP/ESX_HOST/addon-main/vmw-depot-index.xml
https://dl.broadcom.com/xPPJUp0ioMKx348YGoT2ZcQZfRVAGuFI/PROD/COMP/ESX_HOST/iovp-main/vmw-depot-index.xml
https://dl.broadcom.com/xPPJUp0ioMKx348YGoT2ZcQZfRVAGuFI/PROD/COMP/ESX_HOST/vmtools-main/vmw-depot-index.xml
```
