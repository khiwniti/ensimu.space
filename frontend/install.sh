#!/bin/bash

# Frontend installation script for ensimu-space
set -e

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

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_status "Starting frontend installation..."

# Check if yarn is installed
if ! command -v yarn &> /dev/null; then
    print_error "Yarn is not installed. Please install Yarn first."
    print_status "You can install Yarn with: npm install -g yarn"
    exit 1
fi

print_status "Yarn found: $(yarn --version)"

# Install dependencies
print_status "Installing dependencies with Yarn..."
if yarn install; then
    print_success "Dependencies installed successfully"
else
    print_error "Failed to install dependencies"
    exit 1
fi

print_success "Frontend installation completed successfully!"
print_status "To start development server, run: yarn dev"