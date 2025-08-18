#!/bin/bash

echo "=== GitHub Copilot API Troubleshooting ==="
echo ""

# Check if GitHub token is valid
echo "1. Testing GitHub token validity..."
if [ -n "$1" ]; then
    TOKEN="$1"
    RESPONSE=$(curl -s -H "Authorization: token $TOKEN" https://api.github.com/user)
    if echo "$RESPONSE" | grep -q '"login"'; then
        echo "✅ GitHub token is valid"
        USERNAME=$(echo "$RESPONSE" | grep -o '"login": "[^"]*"' | cut -d'"' -f4)
        echo "   Authenticated as: $USERNAME"
    else
        echo "❌ GitHub token is invalid or expired"
        echo "   Response: $RESPONSE"
        exit 1
    fi
else
    echo "❌ No GitHub token provided"
    echo "   Usage: $0 <github_token>"
    exit 1
fi

echo ""
echo "2. Checking Copilot access..."
COPILOT_RESPONSE=$(curl -s -H "Authorization: token $TOKEN" https://api.github.com/copilot_internal/v2/token)
if echo "$COPILOT_RESPONSE" | grep -q '"token"'; then
    echo "✅ Copilot access confirmed"
else
    echo "❌ No Copilot access detected"
    echo "   Response: $COPILOT_RESPONSE"
    echo "   Please check:"
    echo "   - Your GitHub Copilot subscription at https://github.com/settings/copilot"
    echo "   - Your token has 'copilot' scope at https://github.com/settings/tokens"
fi

echo ""
echo "3. Recommended next steps:"
echo "   - If token is invalid: Create new token at https://github.com/settings/tokens"
echo "   - If no Copilot access: Subscribe at https://github.com/features/copilot"
echo "   - If everything looks good: Try the Docker container again"
