#!/bin/bash

# Enhanced installation script with timeout and network optimizations
# for resolving nvidia-nccl-cu12 package download timeout issues

set -e  # Exit on any error

# Color codes for output formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
MAX_RETRIES=3
RETRY_DELAY=10

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if UV is installed
check_uv_installation() {
    if ! command -v uv &> /dev/null; then
        print_error "UV package manager is not installed. Please install UV first."
        print_status "You can install UV with: curl -LsSf https://astral.sh/uv/install.sh | sh"
        exit 1
    fi
    print_status "UV package manager found: $(uv --version)"
}

# Function to create virtual environment with retry logic
create_venv() {
    print_status "Creating virtual environment..."
    
    local attempt=1
    while [ $attempt -le $MAX_RETRIES ]; do
        if uv venv; then
            print_success "Virtual environment created successfully"
            return 0
        else
            print_warning "Virtual environment creation failed (attempt $attempt/$MAX_RETRIES)"
            if [ $attempt -lt $MAX_RETRIES ]; then
                print_status "Retrying in $RETRY_DELAY seconds..."
                sleep $RETRY_DELAY
            fi
            ((attempt++))
        fi
    done
    
    print_error "Failed to create virtual environment after $MAX_RETRIES attempts"
    return 1
}

# Function to activate virtual environment
activate_venv() {
    print_status "Activating virtual environment..."
    if [ -f ".venv/bin/activate" ]; then
        source .venv/bin/activate
        print_success "Virtual environment activated"
    else
        print_error "Virtual environment activation script not found"
        return 1
    fi
}

# Function to install packages with enhanced timeout and retry logic
install_packages() {
    print_status "Installing packages from requirements.txt..."
    print_status "Using extended timeout (300s) for large packages like nvidia-nccl-cu12..."
    
    # Set UV HTTP timeout to 5 minutes (300 seconds) for large package downloads
    # This specifically addresses the nvidia-nccl-cu12 timeout issue
    export UV_HTTP_TIMEOUT=300
    
    # Additional UV optimization settings
    export UV_RETRIES=3              # Number of retries for failed downloads
    
    local attempt=1
    while [ $attempt -le $MAX_RETRIES ]; do
        print_status "Package installation attempt $attempt/$MAX_RETRIES"
        print_status "Timeout settings: UV_HTTP_TIMEOUT=${UV_HTTP_TIMEOUT}s, UV_RETRIES=${UV_RETRIES}"
        
        if uv pip install -r requirements.txt --verbose; then
            print_success "All packages installed successfully"
            return 0
        else
            local exit_code=$?
            print_warning "Package installation failed (attempt $attempt/$MAX_RETRIES) with exit code $exit_code"
            
            if [ $attempt -lt $MAX_RETRIES ]; then
                print_status "Cleaning pip cache before retry..."
                uv cache clean 2>/dev/null || true
                print_status "Retrying in $RETRY_DELAY seconds..."
                sleep $RETRY_DELAY
            fi
            ((attempt++))
        fi
    done
    
    print_error "Failed to install packages after $MAX_RETRIES attempts"
    print_error "This may be due to:"
    print_error "  - Network connectivity issues"
    print_error "  - Package repository unavailability"
    print_error "  - Insufficient timeout for large packages (nvidia-nccl-cu12)"
    print_error "  - Dependency conflicts"
    print_status "You can try running this script again or check your network connection"
    return 1
}

# Function to verify installation
verify_installation() {
    print_status "Verifying installation..."
    
    # Check if virtual environment is active
    if [[ "$VIRTUAL_ENV" != "" ]]; then
        print_success "Virtual environment is active: $VIRTUAL_ENV"
    else
        print_warning "Virtual environment may not be properly activated"
    fi
    
    # Try to import some key packages to verify installation
    python -c "
import sys
import pkg_resources

# List of critical packages to verify
critical_packages = ['fastapi', 'uvicorn', 'numpy', 'pandas']
failed_imports = []

for package in critical_packages:
    try:
        __import__(package)
        print(f'✓ {package} imported successfully')
    except ImportError as e:
        failed_imports.append(package)
        print(f'✗ {package} import failed: {e}')

if failed_imports:
    print(f'Warning: {len(failed_imports)} critical packages failed to import')
    sys.exit(1)
else:
    print('All critical packages verified successfully')
" 2>/dev/null
    
    if [ $? -eq 0 ]; then
        print_success "Package verification completed successfully"
    else
        print_warning "Some packages may not have installed correctly"
    fi
}

# Main execution
main() {
    print_status "Starting enhanced package installation process..."
    print_status "This script includes optimizations for large packages like nvidia-nccl-cu12"
    
    # Load environment variables if .env file exists
    if [ -f ".env" ]; then
        print_status "Loading environment variables from .env file..."
        set -a  # automatically export all variables
        source .env
        set +a  # stop automatically exporting
    fi
    
    # Execute installation steps
    check_uv_installation
    create_venv
    activate_venv
    install_packages
    verify_installation
    
    print_success "Installation process completed successfully!"
    print_status "Virtual environment is ready for use."
    print_status "To activate it manually, run: source .venv/bin/activate"
}

# Execute main function
main "$@"