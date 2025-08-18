#!/bin/bash
# Production Deployment Verification Script for EnsimuSpace
# Verifies all configuration files and dependencies are in place

set -e

echo "🔍 EnsimuSpace Production Deployment Verification"
echo "================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
WARNING_CHECKS=0

# Function to print status
print_status() {
    local status=$1
    local message=$2
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    
    case $status in
        "PASS")
            echo -e "${GREEN}✓ PASS${NC}: $message"
            PASSED_CHECKS=$((PASSED_CHECKS + 1))
            ;;
        "FAIL")
            echo -e "${RED}✗ FAIL${NC}: $message"
            FAILED_CHECKS=$((FAILED_CHECKS + 1))
            ;;
        "WARN")
            echo -e "${YELLOW}⚠ WARN${NC}: $message"
            WARNING_CHECKS=$((WARNING_CHECKS + 1))
            ;;
        "INFO")
            echo -e "${BLUE}ℹ INFO${NC}: $message"
            ;;
    esac
}

# Function to check file exists
check_file() {
    local file=$1
    local description=$2
    
    if [ -f "$file" ]; then
        print_status "PASS" "$description: $file"
    else
        print_status "FAIL" "$description: $file (missing)"
    fi
}

# Function to check directory exists
check_directory() {
    local dir=$1
    local description=$2
    
    if [ -d "$dir" ]; then
        print_status "PASS" "$description: $dir"
    else
        print_status "FAIL" "$description: $dir (missing)"
    fi
}

# Function to check environment variable
check_env_var() {
    local var_name=$1
    local description=$2
    local required=${3:-true}
    
    if [ -n "${!var_name}" ]; then
        if [ "${!var_name}" = "CHANGE_ME"* ]; then
            print_status "WARN" "$description: $var_name (needs to be updated from default)"
        else
            print_status "PASS" "$description: $var_name"
        fi
    else
        if [ "$required" = "true" ]; then
            print_status "FAIL" "$description: $var_name (not set)"
        else
            print_status "WARN" "$description: $var_name (optional, not set)"
        fi
    fi
}

echo
echo "1. Environment Configuration"
echo "----------------------------"

# Check .env.production file
check_file ".env.production" "Production environment file"

# Load environment variables if file exists
if [ -f ".env.production" ]; then
    source .env.production
    
    # Check critical environment variables
    check_env_var "POSTGRES_PASSWORD" "PostgreSQL password"
    check_env_var "REDIS_PASSWORD" "Redis password"
    check_env_var "SECRET_KEY" "Application secret key"
    check_env_var "JWT_SECRET" "JWT secret key"
    check_env_var "OPENAI_API_KEY" "OpenAI API key"
    check_env_var "GRAFANA_PASSWORD" "Grafana admin password"
    check_env_var "DATABASE_URL" "Database URL"
    check_env_var "REDIS_URL" "Redis URL"
    check_env_var "POSTGRES_REPLICATION_PASSWORD" "PostgreSQL replication password"
fi

echo
echo "2. Docker Configuration"
echo "----------------------"

check_file "docker-compose.production.yml" "Production Docker Compose file"
check_file ".dockerignore" "Docker ignore file"

echo
echo "3. Configuration Directories and Files"
echo "--------------------------------------"

# Config directories
check_directory "config" "Main config directory"
check_directory "config/nginx" "Nginx config directory"
check_directory "config/haproxy" "HAProxy config directory"
check_directory "config/prometheus" "Prometheus config directory"
check_directory "config/grafana" "Grafana config directory"
check_directory "config/loki" "Loki config directory"
check_directory "config/promtail" "Promtail config directory"
check_directory "config/production" "Production config directory"
check_directory "config/backend" "Backend config directory"
check_directory "config/backup" "Backup config directory"
check_directory "config/security" "Security config directory"

# Config files
check_file "config/nginx/nginx.conf" "Nginx main configuration"
check_file "config/nginx/default.conf" "Nginx default server configuration"
check_file "config/haproxy/haproxy.cfg" "HAProxy configuration"
check_file "config/redis.conf" "Redis configuration"
check_file "config/prometheus/prometheus.yml" "Prometheus configuration"
check_file "config/prometheus/alert_rules.yml" "Prometheus alert rules"
check_file "config/grafana/provisioning/datasources/prometheus.yml" "Grafana datasources"
check_file "config/grafana/provisioning/dashboards/dashboard.yml" "Grafana dashboard provisioning"
check_file "config/loki/local-config.yaml" "Loki configuration"
check_file "config/promtail/config.yml" "Promtail configuration"
check_file "config/production/app.yml" "Production application configuration"
check_file "config/backend/gunicorn.conf.py" "Gunicorn configuration"
check_file "config/backup/backup-config.yml" "Backup configuration"
check_file "config/security/security-policy.yml" "Security policy configuration"

echo
echo "4. SSL/TLS Configuration"
echo "-----------------------"

check_directory "ssl" "SSL certificate directory"
check_file "ssl/README.md" "SSL documentation"
check_file "ssl/generate-certs.sh" "Certificate generation script"

# Check if SSL files exist (optional for development)
if [ -f "ssl/cert.pem" ] && [ -f "ssl/key.pem" ]; then
    print_status "PASS" "SSL certificates are present"
else
    print_status "WARN" "SSL certificates not found (run ssl/generate-certs.sh for development)"
fi

echo
echo "5. Auto-scaling Configuration"
echo "-----------------------------"

check_directory "autoscaler" "Auto-scaler directory"
check_file "autoscaler/autoscaler.py" "Auto-scaler implementation"

echo
echo "6. Monitoring Configuration"
echo "---------------------------"

check_directory "monitoring" "Monitoring directory"
check_file "monitoring/prometheus.yml" "Monitoring Prometheus config"

echo
echo "7. Docker Compose Services Validation"
echo "-------------------------------------"

if [ -f "docker-compose.production.yml" ]; then
    # Check if docker-compose can parse the file
    if docker-compose -f docker-compose.production.yml config > /dev/null 2>&1; then
        print_status "PASS" "Docker Compose file is valid"
    else
        print_status "FAIL" "Docker Compose file has syntax errors"
    fi
    
    # Check service definitions
    SERVICES=$(docker-compose -f docker-compose.production.yml config --services 2>/dev/null || echo "")
    if [ -n "$SERVICES" ]; then
        for service in $SERVICES; do
            print_status "PASS" "Service defined: $service"
        done
    fi
fi

echo
echo "8. Script Permissions"
echo "--------------------"

# Check script permissions
if [ -x "ssl/generate-certs.sh" ]; then
    print_status "PASS" "SSL certificate generation script is executable"
else
    print_status "WARN" "SSL certificate generation script is not executable (run: chmod +x ssl/generate-certs.sh)"
fi

echo
echo "9. Production Readiness Checklist"
echo "---------------------------------"

# Critical security checks
if [ -f ".env.production" ]; then
    source .env.production
    
    # Check for default passwords
    if [[ "$POSTGRES_PASSWORD" == *"CHANGE_ME"* ]]; then
        print_status "FAIL" "PostgreSQL password still has default value"
    fi
    
    if [[ "$REDIS_PASSWORD" == *"CHANGE_ME"* ]]; then
        print_status "FAIL" "Redis password still has default value"
    fi
    
    if [[ "$SECRET_KEY" == *"CHANGE_ME"* ]]; then
        print_status "FAIL" "Application secret key still has default value"
    fi
    
    if [[ "$JWT_SECRET" == *"CHANGE_ME"* ]]; then
        print_status "FAIL" "JWT secret still has default value"
    fi
    
    if [[ "$GRAFANA_PASSWORD" == *"CHANGE_ME"* ]]; then
        print_status "FAIL" "Grafana password still has default value"
    fi
    
    if [[ "$OPENAI_API_KEY" == *"CHANGE_ME"* ]]; then
        print_status "WARN" "OpenAI API key needs to be set for AI functionality"
    fi
fi

echo
echo "================================================="
echo "📊 Verification Summary"
echo "================================================="
echo -e "Total checks: ${BLUE}$TOTAL_CHECKS${NC}"
echo -e "Passed: ${GREEN}$PASSED_CHECKS${NC}"
echo -e "Failed: ${RED}$FAILED_CHECKS${NC}"
echo -e "Warnings: ${YELLOW}$WARNING_CHECKS${NC}"

if [ $FAILED_CHECKS -eq 0 ]; then
    if [ $WARNING_CHECKS -eq 0 ]; then
        echo -e "\n${GREEN}🎉 All checks passed! Your deployment is ready for production.${NC}"
        exit 0
    else
        echo -e "\n${YELLOW}⚠️  Deployment has warnings. Review and address them before production deployment.${NC}"
        exit 1
    fi
else
    echo -e "\n${RED}❌ Deployment verification failed. Fix the failed checks before proceeding.${NC}"
    exit 2
fi