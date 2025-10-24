#!/bin/bash

# Georgia Dashboard - Vercel Deployment Script
# This script will deploy your dashboard to Vercel

echo "🚀 Georgia Dashboard - Vercel Deployment"
echo "========================================"
echo ""

# Check if in correct directory
if [ ! -f "vercel.json" ]; then
    echo "❌ Error: vercel.json not found"
    echo "Please run this script from the vercel-deploy directory:"
    echo "cd /Users/akbarchranya/georgiadashboard/gadash108/vercel-deploy"
    exit 1
fi

echo "✅ Found vercel.json"
echo ""

# Check if Vercel CLI is installed
if ! command -v vercel &> /dev/null; then
    echo "⏳ Vercel CLI not found, installing via npx..."
    echo ""
fi

# Deploy using npx (no global install needed)
echo "🚀 Deploying to Vercel..."
echo ""
echo "You will be asked to:"
echo "  1. Login to Vercel (opens browser)"
echo "  2. Confirm project settings"
echo "  3. Choose production deployment"
echo ""
echo "Press ENTER to continue..."
read

npx vercel --prod

echo ""
echo "✅ Deployment complete!"
echo ""
echo "Next steps:"
echo "1. Copy the deployment URL"
echo "2. Visit https://your-url.vercel.app/test.html"
echo "3. Run the infrastructure tests"
echo ""
