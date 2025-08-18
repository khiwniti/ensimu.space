#!/bin/bash
# Generate self-signed SSL certificates for development/testing
# Usage: ./generate-certs.sh [domain_name]

set -e

DOMAIN=${1:-localhost}
CERT_DIR="$(dirname "$0")"
DAYS=365

echo "Generating self-signed SSL certificate for domain: $DOMAIN"
echo "Certificate will be valid for $DAYS days"

# Generate private key
echo "Generating private key..."
openssl genrsa -out "$CERT_DIR/key.pem" 4096

# Generate certificate signing request
echo "Generating certificate signing request..."
openssl req -new -key "$CERT_DIR/key.pem" -out "$CERT_DIR/cert.csr" -subj "/C=US/ST=State/L=City/O=EnsimuSpace/OU=IT Department/CN=$DOMAIN"

# Generate self-signed certificate
echo "Generating self-signed certificate..."
openssl x509 -req -in "$CERT_DIR/cert.csr" -signkey "$CERT_DIR/key.pem" -out "$CERT_DIR/cert.pem" -days $DAYS -extensions v3_req -extfile <(
cat <<EOF
[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no

[req_distinguished_name]
C = US
ST = State
L = City
O = EnsimuSpace
OU = IT Department
CN = $DOMAIN

[v3_req]
keyUsage = keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = $DOMAIN
DNS.2 = www.$DOMAIN
DNS.3 = localhost
DNS.4 = *.localhost
IP.1 = 127.0.0.1
IP.2 = ::1
EOF
)

# Generate Diffie-Hellman parameters
echo "Generating Diffie-Hellman parameters..."
openssl dhparam -out "$CERT_DIR/dhparam.pem" 2048

# Create a combined certificate file (cert + intermediate + root)
echo "Creating certificate bundle..."
cp "$CERT_DIR/cert.pem" "$CERT_DIR/ca-bundle.pem"

# Set proper permissions
chmod 644 "$CERT_DIR/cert.pem" "$CERT_DIR/ca-bundle.pem" "$CERT_DIR/dhparam.pem"
chmod 600 "$CERT_DIR/key.pem"

# Clean up CSR file
rm -f "$CERT_DIR/cert.csr"

echo "SSL certificates generated successfully!"
echo "Files created:"
echo "  - cert.pem (Certificate)"
echo "  - key.pem (Private Key)"
echo "  - ca-bundle.pem (Certificate Bundle)"
echo "  - dhparam.pem (DH Parameters)"
echo ""
echo "⚠️  WARNING: These are self-signed certificates for development only!"
echo "⚠️  Do NOT use in production. Use proper CA-signed certificates."
echo ""
echo "To verify the certificate:"
echo "  openssl x509 -in $CERT_DIR/cert.pem -text -noout"
echo ""
echo "To test SSL connection:"
echo "  openssl s_client -connect $DOMAIN:443 -servername $DOMAIN"