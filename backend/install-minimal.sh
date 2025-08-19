#!/bin/bash

# Minimal installation script for testing and development
# Installs only essential packages without heavy ML dependencies

set -e  # Exit on any error

# Color codes for output formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

print_status "Starting minimal package installation for testing..."
print_warning "This installs only essential packages without heavy ML dependencies"

# Check if uv is available
if command -v uv &> /dev/null; then
    print_status "UV package manager found: $(uv --version)"
    PACKAGE_MANAGER="uv"
else
    print_status "UV not found, using pip"
    PACKAGE_MANAGER="pip"
fi

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    print_status "Creating virtual environment..."
    if [ "$PACKAGE_MANAGER" = "uv" ]; then
        uv venv
    else
        python -m venv .venv
    fi
    print_success "Virtual environment created successfully"
else
    print_status "Virtual environment already exists"
fi

# Activate virtual environment
print_status "Activating virtual environment..."
source .venv/bin/activate
print_success "Virtual environment activated"

# Install packages
print_status "Installing minimal packages from requirements-minimal.txt..."

if [ "$PACKAGE_MANAGER" = "uv" ]; then
    print_status "Using UV with optimized settings..."
    UV_HTTP_TIMEOUT=120 uv pip install -r requirements-minimal.txt
else
    print_status "Using pip..."
    pip install -r requirements-minimal.txt --timeout 120
fi

if [ $? -eq 0 ]; then
    print_success "Minimal packages installed successfully!"
    print_status "You can now run basic tests and development tasks"
    print_warning "Note: Heavy ML features (sentence-transformers, chromadb, etc.) are not available"
    print_status "To install full dependencies later, use: ./install.sh"
else
    print_error "Installation failed"
    exit 1
fi

print_status "Installation completed!"
print_status "Next steps:"
echo "  1. Run tests: python run_tests.py --unit"
echo "  2. Start server: ./run.sh"
echo "  3. Run validation: python ../quick_validation_test.py"
