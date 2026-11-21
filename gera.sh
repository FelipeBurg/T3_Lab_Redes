#!/bin/sh
set -e

rm -rf certs
mkdir -p certs

openssl genrsa -out certs/ca.key 4096
openssl req -x509 -new -nodes -key certs/ca.key \
  -sha256 -days 365 -out certs/ca.crt \
  -subj "/CN=SimpleChat-Lab-CA"

openssl genrsa -out certs/server.key 2048
openssl req -new -key certs/server.key -out certs/server.csr \
  -subj "/CN=192.168.56.10"

cat > certs/server.ext <<'EOF'
basicConstraints=critical,CA:FALSE
keyUsage=critical,digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth
subjectAltName=IP:192.168.56.10
EOF

openssl x509 -req -in certs/server.csr \
  -CA certs/ca.crt -CAkey certs/ca.key -CAcreateserial \
  -out certs/server.crt -days 365 -sha256 \
  -extfile certs/server.ext

openssl verify -CAfile certs/ca.crt certs/server.crt
echo "Certificados gerados e validados com sucesso!"
