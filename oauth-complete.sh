#!/bin/bash

# OAuth Completion Script for Dhan MCP
# Interactive guide to complete OAuth authentication

set -e

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║       Dhan Trading API - OAuth Authentication Setup        ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Check if HTTP server is running
echo "📋 Checking HTTP server status..."
if ! curl -s http://localhost:3005/health > /dev/null 2>&1; then
    echo "❌ HTTP server not running on port 3005"
    echo ""
    echo "Start it with:"
    echo "  docker-compose up -d http-server"
    echo ""
    exit 1
fi
echo "✅ HTTP server is running"
echo ""

# Check environment variables
echo "🔐 Checking credentials in .env..."
if [ ! -f ".env" ]; then
    echo "❌ .env file not found"
    echo ""
    echo "Create .env with:"
    echo "  DHAN_APP_ID=your_app_id"
    echo "  DHAN_APP_SECRET=your_app_secret"
    echo "  DHAN_CLIENT_ID=your_client_id"
    echo ""
    exit 1
fi

if ! grep -q "DHAN_APP_ID\|DHAN_APP_SECRET\|DHAN_CLIENT_ID" .env; then
    echo "❌ Missing OAuth credentials in .env"
    echo ""
    echo "Add to .env:"
    echo "  DHAN_APP_ID=your_app_id"
    echo "  DHAN_APP_SECRET=your_app_secret"
    echo "  DHAN_CLIENT_ID=your_client_id"
    echo ""
    exit 1
fi
echo "✅ Credentials configured in .env"
echo ""

# Step 1: Get login URL
echo "🔗 Step 1: Getting OAuth login URL..."
LOGIN_RESPONSE=$(curl -s http://localhost:3005/oauth/login)

if echo "$LOGIN_RESPONSE" | grep -q "error"; then
    echo "❌ Failed to get login URL"
    echo "$LOGIN_RESPONSE" | grep -o '"error":"[^"]*"'
    exit 1
fi

LOGIN_URL=$(echo "$LOGIN_RESPONSE" | grep -o '"login_url":"[^"]*"' | cut -d'"' -f4)
CONSENT_ID=$(echo "$LOGIN_RESPONSE" | grep -o '"consent_id":"[^"]*"' | cut -d'"' -f4)

echo "✅ Login URL generated"
echo ""
echo "════════════════════════════════════════════════════════════"
echo "🌐 STEP 1: Open this URL in your browser:"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "$LOGIN_URL"
echo ""
echo "════════════════════════════════════════════════════════════"
echo "👤 STEP 2: Log in with your Dhan credentials"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "1. Click the above link (or copy-paste into browser)"
echo "2. Log in with your Dhan trading account"
echo "3. Grant permission when prompted"
echo "4. You'll be redirected to a URL containing 'token_id='"
echo ""
echo "════════════════════════════════════════════════════════════"
echo "📋 STEP 3: Copy token_id from redirect URL"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "After login, look for a URL like:"
echo "  https://.../?token_id=abc123xyz789..."
echo ""
echo "Copy the part after 'token_id=' (the long string)"
echo ""

read -p "Paste token_id here: " TOKEN_ID

if [ -z "$TOKEN_ID" ]; then
    echo ""
    echo "❌ No token_id provided"
    exit 1
fi

echo ""
echo "════════════════════════════════════════════════════════════"
echo "🔄 STEP 4: Exchanging token for access token..."
echo "════════════════════════════════════════════════════════════"
echo ""

CALLBACK_RESPONSE=$(curl -s "http://localhost:3005/oauth/callback?token_id=$TOKEN_ID")

if echo "$CALLBACK_RESPONSE" | grep -q "error"; then
    echo "❌ Token exchange failed"
    echo ""
    ERROR=$(echo "$CALLBACK_RESPONSE" | grep -o '"error":"[^"]*"' | cut -d'"' -f4)
    echo "Error: $ERROR"
    echo ""
    echo "Possible causes:"
    echo "  - Token ID expired (tokens expire after ~5 minutes)"
    echo "  - Invalid token ID (copy-paste error?)"
    echo "  - Token already used"
    echo ""
    echo "Try again by running this script again"
    exit 1
fi

if echo "$CALLBACK_RESPONSE" | grep -q "Successfully authenticated"; then
    CLIENT_NAME=$(echo "$CALLBACK_RESPONSE" | grep -o '"client_name":"[^"]*"' | cut -d'"' -f4)
    echo "════════════════════════════════════════════════════════════"
    echo "✅ SUCCESS! You are authenticated!"
    echo "════════════════════════════════════════════════════════════"
    echo ""
    echo "User: $CLIENT_NAME"
    echo ""
    echo "✓ Access token acquired and stored"
    echo "✓ Ready to use trading API"
    echo "✓ MCP server can access authenticated endpoints"
    echo ""
    echo "════════════════════════════════════════════════════════════"
    echo "🚀 Next Steps"
    echo "════════════════════════════════════════════════════════════"
    echo ""
    echo "1. Try an API call:"
    echo "   curl http://localhost:3005/api/methods"
    echo ""
    echo "2. Or in Claude Code:"
    echo "   - MCP server auto-loads via .mcp.json"
    echo "   - Start using trading tools!"
    echo ""
    echo "3. Documentation:"
    echo "   - OAUTH_SETUP.md - Detailed OAuth guide"
    echo "   - MCP_SERVER_USAGE.md - How to use MCP server"
    echo "   - PRODUCTION_SETUP.md - Production deployment"
    echo ""
else
    echo "❌ Unexpected response from OAuth callback"
    echo ""
    echo "$CALLBACK_RESPONSE"
    exit 1
fi
