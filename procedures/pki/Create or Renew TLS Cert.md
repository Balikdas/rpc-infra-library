# Create or Renew TLS Cert

This procedure will generate a CSR and new key to be used with the cert.

- Create the config file `req.conf`:

```conf
[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no
[req_distinguished_name]
C = CA
ST = Ontario
L = Toronto
O = Rogers Communications Inc
OU = Cloud Engineering
CN = cc.net.rogers.com
[v3_req]
subjectAltName = @alt_names
[alt_names]
DNS.1 = cc.net.rogers.com
DNS.2 = *.cc.net.rogers.com
```

- Execute the `openssl` command to generate the key and CSR

```bash
openssl req -new -out cc.net.rogers.com.csr -newkey rsa:4096 -nodes -sha256 -keyout cc.net.rogers.com.key -config req.conf
```

- Send the CSR to the CA to be signed
- Store the Private Key on the Sharepoint site PKI folder for safekeeping
- When the Cert is received, install it in the server with the private key
- Make sure to store the cert and private key on the Sharepoint site PKI folder for safekeeping
