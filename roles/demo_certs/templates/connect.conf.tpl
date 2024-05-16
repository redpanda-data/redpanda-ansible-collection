# OpenSSL node configuration file for keystore generation
[ req ]
prompt = no
distinguished_name = distinguished_name
x509_extensions = extensions

[ distinguished_name ]
organizationName = Vectorized
commonName = {{ ansible_hostname }}

[ extensions ]
basicConstraints = CA:FALSE
keyUsage = critical, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth, clientAuth
subjectAltName = DNS:{{ ansible_hostname }},DNS:{{ ansible_fqdn }},IP:{{ inventory_hostname }},IP:{{ private_ip }}
