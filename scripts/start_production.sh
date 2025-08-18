#!/bin/bash

# Production startup script for EnsumuSpace CAE Preprocessing Platform
# This script handles the complete production deployment process

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        error "This script should not be run as root for security reasons"
        exit 1
    fi
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check if .env file exists
    if [[ ! -f .env ]]; then
        error ".env file not found. Please copy .env.example to .env and configure it."
        exit 1
    fi
    
    success "Prerequisites check passed"
}

# Validate environment configuration
validate_environment() {
    log "Validating environment configuration..."
    
    # Source environment variables
    source .env
    
    # Check required variables
    required_vars=("OPENAI_API_KEY" "DATABASE_URL" "SECRET_KEY")
    
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var}" ]]; then
            error "Required environment variable $var is not set"
            exit 1
        fi
    done
    
    # Check if ENVIRONMENT is set to production
    if [[ "$ENVIRONMENT" != "production" ]]; then
        warning "ENVIRONMENT is not set to 'production'. Current value: $ENVIRONMENT"
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    success "Environment validation passed"
}

# Setup directories and permissions
setup_directories() {
    log "Setting up directories and permissions..."
    
    # Create necessary directories
    mkdir -p uploads logs backups ssl
    
    # Set proper permissions
    chmod 755 uploads logs backups
    chmod 700 ssl  # SSL certificates should be more restrictive
    
    success "Directories setup completed"
}

# Database initialization
initialize_database() {
    log "Initializing database..."
    
    # Start database service first
    docker-compose up -d db redis
    
    # Wait for database to be ready
    log "Waiting for database to be ready..."
    sleep 10
    
    # Run database migrations
    log "Running database migrations..."
    docker-compose run --rm backend alembic upgrade head
    
    # Initialize data
    log "Initializing default data..."
    docker-compose run --rm backend python scripts/initialize_data.py
    
    success "Database initialization completed"
}

# Build and start services
start_services() {
    log "Building and starting services..."
    
    # Build images
    log "Building Docker images..."
    docker-compose build --no-cache
    
    # Start all services
    log "Starting all services..."
    docker-compose --profile production up -d
    
    # Wait for services to be ready
    log "Waiting for services to start..."
    sleep 30
    
    success "Services started successfully"
}

# Health checks
perform_health_checks() {
    log "Performing health checks..."
    
    # Check backend health
    log "Checking backend health..."
    for i in {1..10}; do
        if curl -f http://localhost:8000/health &> /dev/null; then
            success "Backend is healthy"
            break
        fi
        if [[ $i -eq 10 ]]; then
            error "Backend health check failed after 10 attempts"
            return 1
        fi
        sleep 5
    done
    
    # Check frontend health
    log "Checking frontend health..."
    for i in {1..10}; do
        if curl -f http://localhost:3000/health &> /dev/null; then
            success "Frontend is healthy"
            break
        fi
        if [[ $i -eq 10 ]]; then
            error "Frontend health check failed after 10 attempts"
            return 1
        fi
        sleep 5
    done
    
    # Check database connectivity
    log "Checking database connectivity..."
    if docker-compose exec -T db pg_isready -U postgres &> /dev/null; then
        success "Database is accessible"
    else
        error "Database connectivity check failed"
        return 1
    fi
    
    success "All health checks passed"
}

# Setup monitoring (optional)
setup_monitoring() {
    if [[ "$1" == "--with-monitoring" ]]; then
        log "Setting up monitoring..."
        docker-compose --profile monitoring up -d
        
        log "Waiting for monitoring services..."
        sleep 15
        
        # Check Prometheus
        if curl -f http://localhost:9090/-/healthy &> /dev/null; then
            success "Prometheus is running at http://localhost:9090"
        else
            warning "Prometheus health check failed"
        fi
        
        # Check Grafana
        if curl -f http://localhost:3001/api/health &> /dev/null; then
            success "Grafana is running at http://localhost:3001 (admin/admin)"
        else
            warning "Grafana health check failed"
        fi
    fi
}

# Display deployment summary
show_summary() {
    log "Deployment Summary"
    echo "===================="
    echo
    echo "🚀 EnsumuSpace CAE Preprocessing Platform is now running!"
    echo
    echo "📍 Service URLs:"
    echo "   Frontend:  http://localhost:3000"
    echo "   Backend:   http://localhost:8000"
    echo "   API Docs:  http://localhost:8000/docs"
    echo "   Health:    http://localhost:8000/health"
    echo
    if [[ "$1" == "--with-monitoring" ]]; then
        echo "📊 Monitoring URLs:"
        echo "   Prometheus: http://localhost:9090"
        echo "   Grafana:    http://localhost:3001 (admin/admin)"
        echo
    fi
    echo "📋 Management Commands:"
    echo "   View logs:     docker-compose logs -f"
    echo "   Stop services: docker-compose down"
    echo "   Restart:       docker-compose restart"
    echo
    echo "🔧 Database Management:"
    echo "   Connect to DB: docker-compose exec db psql -U postgres ensumu_space"
    echo "   Backup DB:     docker-compose exec db pg_dump -U postgres ensumu_space > backup.sql"
    echo
    success "Deployment completed successfully!"
}

# Cleanup function for errors
cleanup_on_error() {
    error "Deployment failed. Cleaning up..."
    docker-compose down
    exit 1
}

# Main deployment function
main() {
    echo "🚀 Starting EnsumuSpace CAE Preprocessing Platform Deployment"
    echo "=============================================================="
    echo
    
    # Set error trap
    trap cleanup_on_error ERR
    
    # Run deployment steps
    check_root
    check_prerequisites
    validate_environment
    setup_directories
    initialize_database
    start_services
    perform_health_checks
    setup_monitoring "$1"
    show_summary "$1"
}

# Script entry point
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
