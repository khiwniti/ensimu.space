#!/bin/bash

# Run the copilot-api container with interactive authentication
echo "Starting Copilot API container with interactive authentication..."

# Create copilot-data directory if it doesn't exist
mkdir -p ./copilot-data

# Run without GitHub token to trigger interactive auth
docker run -it --rm \
  -p 4141:4141 \
  -v $(pwd)/copilot-data:/root/.local/share/copilot-api \
  copilot-api
