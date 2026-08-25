# Create or Renew Self Signed TLS Cert

This procedure will generate a CSR and new key to be used with the cert.

- Create the config file `selfsigned.conf`:

```conf
[CA_default]
copy_extensions = copy

[req]
default_bits = 4096
prompt = no
default_md = sha256
distinguished_name = req_distinguished_name
x509_extensions = v3_ca

[req_distinguished_name]
C = CA
ST = Ontario
L = Toronto
O = Rogers Communications Inc
OU = Cloud Engineering
emailAddress = network-infra-dl@rci.rogers.com
CN = cc.net.rogers.com

[v3_ca]
basicConstraints = CA:FALSE
keyUsage = digitalSignature, keyEncipherment
subjectAltName = @alternate_names

[alternate_names]
DNS.1 = cc.net.rogers.com
DNS.2 = *.cc.net.rogers.com
```

- Execute the `openssl` command to generate the key and CSR

```bash
openssl req -x509 -newkey rsa:4096 -sha256 -days 3650 -nodes -config selfsigned.conf -keyout server.key -out server.crt
```

- Make sure to store the cert and private key on the Sharepoint site PKI folder (password protected) for safekeeping
