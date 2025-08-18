#!/bin/bash

# Production Deployment Script for Ensumu Space AI-Powered Simulation Platform
# Integrates CopilotKit + Archon OS + NVIDIA PhysicsNemo

set -e

echo "🚀 Starting Ensumu Space Production Deployment"
echo "================================================"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="ensumu-space"
DOCKER_REGISTRY="your-registry.com/ensumu"
VERSION=${1:-"latest"}

# Functions
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
    exit 1
}

check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check if kubectl is installed
    if ! command -v kubectl &> /dev/null; then
        error "kubectl is not installed. Please install kubectl first."
    fi
    
    # Check if helm is installed
    if ! command -v helm &> /dev/null; then
        error "helm is not installed. Please install helm first."
    fi
    
    # Check if docker is installed
    if ! command -v docker &> /dev/null; then
        error "docker is not installed. Please install docker first."
    fi
    
    # Check cluster connectivity
    if ! kubectl cluster-info &> /dev/null; then
        error "Cannot connect to Kubernetes cluster. Please check your kubeconfig."
    fi
    
    log "✅ Prerequisites check passed"
}

setup_nvidia_gpu_support() {
    log "Setting up NVIDIA GPU support..."
    
    # Install NVIDIA GPU Operator if not present
    if ! kubectl get nodes -l gpu=nvidia &> /dev/null; then
        warn "No GPU nodes found. Installing NVIDIA GPU Operator..."
        
        helm repo add nvidia https://helm.ngc.nvidia.com/nvidia
        helm repo update
        
        helm install --wait --generate-name \
            -n gpu-operator --create-namespace \
            nvidia/gpu-operator \
            --set driver.enabled=true
            
        log "✅ NVIDIA GPU Operator installed"
    else
        log "✅ GPU nodes already available"
    fi
}

build_and_push_images() {
    log "Building and pushing Docker images..."
    
    # Frontend
    log "Building frontend image..."
    cd frontend
    docker build -t ${DOCKER_REGISTRY}/frontend:${VERSION} .
    docker push ${DOCKER_REGISTRY}/frontend:${VERSION}
    cd ..
    
    # Backend  
    log "Building backend image..."
    cd backend
    docker build -t ${DOCKER_REGISTRY}/backend:${VERSION} .
    docker push ${DOCKER_REGISTRY}/backend:${VERSION}
    cd ..
    
    log "✅ Images built and pushed successfully"
}

setup_secrets() {
    log "Setting up secrets and configuration..."
    
    # Check if secrets exist
    if kubectl get secret ensumu-secrets -n ${NAMESPACE} &> /dev/null; then
        warn "Secrets already exist. Skipping secret creation."
        return
    fi
    
    # Prompt for required secrets
    echo -e "${BLUE}Please provide the following secrets:${NC}"
    
    read -s -p "Database URL: " DATABASE_URL
    echo
    read -s -p "NVIDIA API Key: " NVIDIA_API_KEY
    echo
    read -s -p "OpenAI API Key: " OPENAI_API_KEY
    echo
    read -s -p "Supabase URL: " SUPABASE_URL
    echo
    read -s -p "Supabase Service Key: " SUPABASE_SERVICE_KEY
    echo
    
    # Create secrets
    kubectl create secret generic ensumu-secrets \
        --from-literal=database-url="${DATABASE_URL}" \
        --from-literal=nvidia-api-key="${NVIDIA_API_KEY}" \
        --from-literal=openai-api-key="${OPENAI_API_KEY}" \
        -n ${NAMESPACE}
    
    kubectl create secret generic archon-secrets \
        --from-literal=supabase-url="${SUPABASE_URL}" \
        --from-literal=supabase-service-key="${SUPABASE_SERVICE_KEY}" \
        --from-literal=openai-api-key="${OPENAI_API_KEY}" \
        -n ${NAMESPACE}
    
    log "✅ Secrets created successfully"
}

deploy_archon_os() {
    log "Deploying Archon OS..."
    
    # Clone Archon repository if not exists
    if [ ! -d "archon" ]; then
        git clone https://github.com/coleam00/Archon.git archon
    fi
    
    cd archon
    
    # Create Archon namespace and deploy
    kubectl create namespace archon-system --dry-run=client -o yaml | kubectl apply -f -
    
    # Deploy Archon using docker-compose equivalent
    docker-compose -f docker-compose.yml build
    docker-compose -f docker-compose.yml up -d
    
    cd ..
    
    log "✅ Archon OS deployed"
}

deploy_application() {
    log "Deploying Ensumu Space application..."
    
    # Create namespace
    kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -
    
    # Apply configuration
    kubectl apply -f k8s/secrets.yaml -n ${NAMESPACE}
    
    # Deploy application components
    kubectl apply -f k8s/production.yaml -n ${NAMESPACE}
    
    # Wait for deployments to be ready
    log "Waiting for deployments to be ready..."
    kubectl wait --for=condition=available --timeout=600s deployment/ensumu-frontend -n ${NAMESPACE}
    kubectl wait --for=condition=available --timeout=600s deployment/ensumu-backend -n ${NAMESPACE}
    kubectl wait --for=condition=available --timeout=600s deployment/archon-server -n ${NAMESPACE}
    kubectl wait --for=condition=available --timeout=600s deployment/physics-nemo -n ${NAMESPACE}
    
    log "✅ Application deployed successfully"
}

setup_monitoring() {
    log "Setting up monitoring and observability..."
    
    # Install Prometheus and Grafana
    helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
    helm repo update
    
    helm install prometheus prometheus-community/kube-prometheus-stack \
        --namespace monitoring \
        --create-namespace \
        --set grafana.adminPassword=admin123 \
        --wait
    
    # Apply custom monitoring configuration
    cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: ensumu-grafana-dashboard
  namespace: monitoring
data:
  dashboard.json: |
    {
      "dashboard": {
        "title": "Ensumu Space Platform Metrics",
        "panels": [
          {
            "title": "Active Simulations",
            "type": "stat",
            "targets": [
              {
                "expr": "sum(rate(simulation_requests_total[5m]))"
              }
            ]
          },
          {
            "title": "GPU Utilization",
            "type": "graph",
            "targets": [
              {
                "expr": "nvidia_gpu_utilization_percentage"
              }
            ]
          },
          {
            "title": "Archon Knowledge Base Size",
            "type": "stat",
            "targets": [
              {
                "expr": "archon_knowledge_entries_total"
              }
            ]
          }
        ]
      }
    }
EOF
    
    log "✅ Monitoring setup complete"
}

setup_ingress() {
    log "Setting up ingress and SSL certificates..."
    
    # Install nginx-ingress
    helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
    helm repo update
    
    helm install nginx-ingress ingress-nginx/ingress-nginx \
        --namespace ingress-nginx \
        --create-namespace \
        --set controller.replicaCount=2 \
        --wait
    
    # Install cert-manager for SSL
    kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml
    
    # Wait for cert-manager to be ready
    kubectl wait --for=condition=ready pod -l app=cert-manager -n cert-manager --timeout=300s
    
    # Create ClusterIssuer for Let's Encrypt
    cat <<EOF | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@ensumu-space.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
EOF
    
    log "✅ Ingress and SSL setup complete"
}

run_health_checks() {
    log "Running health checks..."
    
    # Check if all pods are running
    if ! kubectl get pods -n ${NAMESPACE} | grep -v Running | grep -v Completed | tail -n +2 | grep .; then
        log "✅ All pods are running"
    else
        warn "Some pods are not running properly"
        kubectl get pods -n ${NAMESPACE}
    fi
    
    # Check ingress endpoints
    FRONTEND_URL="https://ensumu-space.com"
    API_URL="https://api.ensumu-space.com/health"
    ARCHON_URL="https://archon.ensumu-space.com/health"
    
    log "Checking endpoints..."
    echo "Frontend: ${FRONTEND_URL}"
    echo "API: ${API_URL}"
    echo "Archon: ${ARCHON_URL}"
    
    log "✅ Health checks complete"
}

display_deployment_info() {
    log "Deployment Summary"
    echo "=================="
    echo "Frontend URL: https://ensumu-space.com"
    echo "API URL: https://api.ensumu-space.com"
    echo "Archon Dashboard: https://archon.ensumu-space.com"
    echo "Archon MCP: https://archon-mcp.ensumu-space.com"
    echo ""
    echo "Monitoring:"
    echo "Grafana: http://$(kubectl get svc prometheus-grafana -n monitoring -o jsonpath='{.status.loadBalancer.ingress[0].ip}'):3000"
    echo "Prometheus: http://$(kubectl get svc prometheus-kube-prometheus-prometheus -n monitoring -o jsonpath='{.status.loadBalancer.ingress[0].ip}'):9090"
    echo ""
    echo "Credentials:"
    echo "Grafana: admin / admin123"
    echo ""
    echo "Useful commands:"
    echo "kubectl get pods -n ${NAMESPACE}"
    echo "kubectl logs -f deployment/ensumu-backend -n ${NAMESPACE}"
    echo "kubectl port-forward svc/ensumu-frontend-service -n ${NAMESPACE} 8080:80"
}

# Main deployment flow
main() {
    log "Starting deployment with version: ${VERSION}"
    
    check_prerequisites
    setup_nvidia_gpu_support
    build_and_push_images
    setup_secrets
    deploy_archon_os
    deploy_application
    setup_monitoring
    setup_ingress
    
    log "Waiting for services to stabilize..."
    sleep 30
    
    run_health_checks
    display_deployment_info
    
    log "🎉 Ensumu Space deployment completed successfully!"
    log "Your AI-powered simulation platform is now running in production."
}

# Parse command line arguments
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "health")
        run_health_checks
        ;;
    "logs")
        kubectl logs -f deployment/ensumu-backend -n ${NAMESPACE}
        ;;
    "status")
        kubectl get all -n ${NAMESPACE}
        ;;
    "clean")
        read -p "Are you sure you want to delete the entire deployment? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            kubectl delete namespace ${NAMESPACE}
            log "Deployment cleaned up"
        fi
        ;;
    *)
        echo "Usage: $0 [deploy|health|logs|status|clean]"
        exit 1
        ;;
esac