# EnsumuSpace CAE Preprocessing - Deployment Guide

## 🚀 Production Deployment Guide

This guide covers deploying the enhanced EnsumuSpace platform with integrated CAE preprocessing capabilities.

## 📋 Prerequisites

### System Requirements
- **CPU**: 4+ cores recommended
- **RAM**: 8GB minimum, 16GB recommended
- **Storage**: 100GB+ for file uploads and processing
- **OS**: Ubuntu 20.04+ or similar Linux distribution

### Software Dependencies
- Docker 20.10+
- Docker Compose 2.0+
- Node.js 18+ (for frontend development)
- Python 3.11+ (for backend development)
- PostgreSQL 15+ (production database)
- Redis 7+ (caching and sessions)

### External Services
- **OpenAI API**: For AI agent functionality
- **Firebase**: For authentication (optional)
- **AWS S3**: For file storage (optional)
- **SMTP Server**: For email notifications

## 🔧 Environment Setup

### 1. Clone and Configure

```bash
git clone <repository-url>
cd ensumu-space

# Copy environment template
cp .env.example .env

# Edit configuration
nano .env
```

### 2. Required Environment Variables

```bash
# Core Configuration
ENVIRONMENT=production
OPENAI_API_KEY=your_openai_api_key
DATABASE_URL=postgresql://user:pass@localhost:5432/ensumu_space

# Security
SECRET_KEY=your_256_bit_secret_key
CORS_ORIGINS=https://yourdomain.com

# Performance
WORKER_PROCESSES=4
RATE_LIMIT_REQUESTS_PER_MINUTE=50
```

## 🐳 Docker Deployment

### Development Environment

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop services
docker-compose down
```

### Production Environment

```bash
# Start with production profile
docker-compose --profile production up -d

# Include monitoring
docker-compose --profile production --profile monitoring up -d

# Health check
curl http://localhost:8000/health
```

## 🔒 Security Configuration

### 1. SSL/TLS Setup

```bash
# Generate SSL certificates (Let's Encrypt)
sudo certbot certonly --standalone -d yourdomain.com

# Copy certificates
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ./ssl/
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem ./ssl/
```

### 2. Firewall Configuration

```bash
# Allow HTTP/HTTPS
sudo ufw allow 80
sudo ufw allow 443

# Allow SSH (if needed)
sudo ufw allow 22

# Enable firewall
sudo ufw enable
```

### 3. Database Security

```bash
# Create production database user
sudo -u postgres psql
CREATE USER ensumu_user WITH PASSWORD 'secure_password';
CREATE DATABASE ensumu_space OWNER ensumu_user;
GRANT ALL PRIVILEGES ON DATABASE ensumu_space TO ensumu_user;
```

## 📊 Monitoring Setup

### 1. Prometheus Configuration

Create `monitoring/prometheus.yml`:

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'ensumu-backend'
    static_configs:
      - targets: ['backend:8000']
    metrics_path: '/metrics'
```

### 2. Grafana Dashboards

- **API Performance**: Response times, error rates
- **System Resources**: CPU, memory, disk usage
- **CAE Workflows**: Active workflows, completion rates
- **User Activity**: Request patterns, file uploads

### 3. Log Management

```bash
# Configure log rotation
sudo nano /etc/logrotate.d/ensumu-space

# Content:
/var/log/ensumu-space/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 www-data www-data
}
```

## 🔄 Database Migration

### 1. Initial Setup

```bash
# Run migrations
cd backend
source .venv/bin/activate
alembic upgrade head

# Create initial data
python scripts/create_initial_data.py
```

### 2. Backup Strategy

```bash
# Daily backup script
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
pg_dump ensumu_space > /backups/ensumu_space_$DATE.sql
aws s3 cp /backups/ensumu_space_$DATE.sql s3://your-backup-bucket/
```

## 🚦 Health Checks

### 1. Application Health

```bash
# Backend health
curl http://localhost:8000/health

# Expected response:
{
  "overall_status": "healthy",
  "services": {
    "database": {"status": "healthy"},
    "ai_service": {"status": "healthy"},
    "file_system": {"status": "healthy"}
  }
}
```

### 2. Performance Metrics

```bash
# Get performance metrics
curl http://localhost:8000/metrics

# Monitor key metrics:
# - Response times < 2s
# - Error rate < 1%
# - CPU usage < 80%
# - Memory usage < 85%
```

## 🔧 Troubleshooting

### Common Issues

1. **OpenAI API Errors**
   ```bash
   # Check API key
   echo $OPENAI_API_KEY
   
   # Test API connection
   curl -H "Authorization: Bearer $OPENAI_API_KEY" \
        https://api.openai.com/v1/models
   ```

2. **Database Connection Issues**
   ```bash
   # Check database connectivity
   pg_isready -h localhost -p 5432
   
   # Test connection
   psql -h localhost -U ensumu_user -d ensumu_space
   ```

3. **File Upload Problems**
   ```bash
   # Check upload directory permissions
   ls -la uploads/
   
   # Fix permissions
   sudo chown -R www-data:www-data uploads/
   sudo chmod -R 755 uploads/
   ```

### Performance Optimization

1. **Database Optimization**
   ```sql
   -- Add indexes for common queries
   CREATE INDEX idx_projects_status ON projects(status);
   CREATE INDEX idx_workflows_created_at ON workflow_executions(created_at);
   ```

2. **Caching Strategy**
   ```python
   # Enable Redis caching
   REDIS_URL=redis://localhost:6379/0
   CACHE_TTL=300  # 5 minutes
   ```

3. **Load Balancing**
   ```nginx
   upstream backend {
       server backend1:8000;
       server backend2:8000;
       server backend3:8000;
   }
   ```

## 📈 Scaling Considerations

### Horizontal Scaling

1. **Multiple Backend Instances**
   - Use load balancer (Nginx/HAProxy)
   - Shared database and Redis
   - Stateless application design

2. **Database Scaling**
   - Read replicas for queries
   - Connection pooling
   - Query optimization

3. **File Storage Scaling**
   - Use S3 or compatible storage
   - CDN for file delivery
   - Async file processing

### Vertical Scaling

1. **Resource Allocation**
   - Monitor CPU/memory usage
   - Scale based on workflow demands
   - Optimize AI agent performance

## 🔐 Security Best Practices

1. **API Security**
   - Rate limiting enabled
   - Input validation
   - CORS properly configured
   - HTTPS enforced

2. **File Security**
   - File type validation
   - Size limits enforced
   - Virus scanning (optional)
   - Secure file storage

3. **Database Security**
   - Encrypted connections
   - Regular backups
   - Access controls
   - Query monitoring

## 📞 Support and Maintenance

### Regular Maintenance Tasks

1. **Weekly**
   - Review error logs
   - Check disk space
   - Monitor performance metrics

2. **Monthly**
   - Update dependencies
   - Review security patches
   - Backup verification

3. **Quarterly**
   - Performance optimization
   - Security audit
   - Capacity planning

### Emergency Procedures

1. **Service Outage**
   - Check health endpoints
   - Review recent deployments
   - Scale resources if needed

2. **Data Recovery**
   - Restore from backup
   - Verify data integrity
   - Communicate with users

For additional support, contact the development team or refer to the technical documentation.
