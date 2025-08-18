# SSL/TLS Certificate Management for EnsimuSpace Production

This directory contains SSL/TLS certificates and related configuration for production deployment.

## Directory Structure

```
ssl/
├── cert.pem          # Main SSL certificate
├── key.pem           # Private key for SSL certificate
├── ca-bundle.pem     # Certificate Authority bundle (if applicable)
├── dhparam.pem       # Diffie-Hellman parameters for enhanced security
├── generate-certs.sh # Script to generate self-signed certificates for development
└── renew-certs.sh    # Script to renew certificates (for Let's Encrypt)
```

## Production Setup

### Option 1: Let's Encrypt (Recommended)

1. Install Certbot:
   ```bash
   sudo apt-get update
   sudo apt-get install certbot python3-certbot-nginx
   ```

2. Generate certificates:
   ```bash
   sudo certbot --nginx -d your-domain.com -d www.your-domain.com
   ```

3. Set up automatic renewal:
   ```bash
   sudo crontab -e
   # Add: 0 12 * * * /usr/bin/certbot renew --quiet
   ```

### Option 2: Commercial SSL Certificate

1. Generate CSR (Certificate Signing Request):
   ```bash
   openssl req -new -newkey rsa:4096 -nodes -keyout key.pem -out domain.csr
   ```

2. Submit CSR to your Certificate Authority
3. Download and install the certificate files

### Option 3: Self-Signed Certificates (Development Only)

For development/testing purposes only:

```bash
./generate-certs.sh your-domain.com
```

## Certificate Installation

1. Place certificate files in this directory:
   - `cert.pem` - Your SSL certificate
   - `key.pem` - Your private key
   - `ca-bundle.pem` - Certificate authority bundle (optional)

2. Set proper permissions:
   ```bash
   chmod 644 cert.pem ca-bundle.pem
   chmod 600 key.pem
   chown root:ssl-cert cert.pem key.pem ca-bundle.pem
   ```

3. Generate Diffie-Hellman parameters:
   ```bash
   openssl dhparam -out dhparam.pem 2048
   ```

## Security Best Practices

- Use strong cipher suites (configured in nginx/haproxy)
- Enable HSTS (HTTP Strict Transport Security)
- Use OCSP stapling for better performance
- Regularly update and renew certificates
- Monitor certificate expiration dates

## Certificate Monitoring

The Prometheus alerts are configured to warn when certificates expire within 30 days.
Check the Grafana dashboard for certificate status monitoring.

## Troubleshooting

### Common Issues:

1. **Certificate not trusted**: Ensure ca-bundle.pem is properly configured
2. **Private key mismatch**: Verify key corresponds to certificate
3. **Permission denied**: Check file permissions and ownership
4. **Certificate expired**: Renew certificate using appropriate method

### Verification Commands:

```bash
# Check certificate details
openssl x509 -in cert.pem -text -noout

# Verify certificate and key match
openssl x509 -noout -modulus -in cert.pem | openssl md5
openssl rsa -noout -modulus -in key.pem | openssl md5

# Test SSL configuration
openssl s_client -connect your-domain.com:443 -servername your-domain.com
```

## Environment Variables

The following environment variables can be set in .env.production:

- `SSL_CERT_PATH=/etc/nginx/ssl/cert.pem`
- `SSL_KEY_PATH=/etc/nginx/ssl/key.pem`
- `SSL_CA_BUNDLE_PATH=/etc/nginx/ssl/ca-bundle.pem`
- `SSL_DHPARAM_PATH=/etc/nginx/ssl/dhparam.pem`

## Backup and Recovery

Regularly backup your private keys and certificates to a secure location.
Store backups encrypted and in multiple locations for redundancy.