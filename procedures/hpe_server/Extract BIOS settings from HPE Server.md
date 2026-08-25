# Extract BIOS Settings from HPE Server

This procedure outlines how to extract BIOS settigs from an HPE server using the iLORest tool. The extracted file (in JSON format) can then be used to load the BIOS settings on other HPE servers.

## Extract BIOS settings from existing server

First, set the BIOS settings as required on an existing HPE server of the same hardware configuration, then execute the commands below:

- Save BIOS configuration from existing server with intended configuration:

```bash
ilorest login ${ilo_fqdn} -u Administrator -p ${password}
ilorest save --select Bios. -f bios_config.json
```

- Modify the saved JSON file to remove the `Comments` object and lines containing `@odata.etag`, `ProductId` and `SerialNumber`:

```bash
vi bios_config.json
```

- Remove the first JSON object `Comments`:

```json
  {
    "Comments": {
      "BIOSDate": "01/09/2026",
      "BIOSFamily": "U30",
      "Manufacturer": "HPE",
      "Model": "ProLiant DL380 Gen10",
      "SerialNumber": "2M220603YW",
      "iLOVersion": "iLO 5 v3.17"
    }
  },
```

- Remove any lines with references to `@odata.`, `SerialNumber` or `ProductId`:

```json
        "@odata.etag": "W/\"5B8919BC1595AAAAAA9C96F8D3539627\"",
```

```json
          "SerialNumber": "2M220603YW",
```

```json
          "ProductId": "868704-B21",
```

- Save and quit:

```bash
:wq!
```

## Apply BIOS Settings to Another HPE Server

**Note:** The server the settings are being applied to must be of the same model (DL360 vs DL380 etc), same Generation (Gen10 vs Gen11 etc) and have the same hardware configuration as the source.

- Login to and apply the configuration to the destination server:

```bash
ilorest login ${ilo_fqdn} -u Administrator -p ${password}
ilorest load -f bios_config.json
```

- Reboot the server to apply settings
