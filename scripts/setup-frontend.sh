#!/bin/bash

# Script to prepare the existing frontend for static deployment
# This adapts the current Next.js app to work with the serverless backend

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}🔧 Setting up frontend for static deployment${NC}"

# Check if frontend directory exists
if [ ! -d "frontend" ]; then
    echo "❌ Frontend directory not found. Please run this from the project root."
    exit 1
fi

# Copy frontend to frontend-static
echo -e "${YELLOW}📁 Copying frontend to frontend-static...${NC}"
cp -r frontend/* frontend-static/ 2>/dev/null || true

# Navigate to frontend-static
cd frontend-static

# Update package.json for static export
echo -e "${YELLOW}📝 Updating package.json for static export...${NC}"

# Create a backup of package.json
cp package.json package.json.backup

# Add static export configuration
cat > next.config.js << 'EOF'
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  trailingSlash: true,
  images: {
    unoptimized: true
  },
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
  }
}

module.exports = nextConfig
EOF

# Update the subscription service to use the new API
echo -e "${YELLOW}🔄 Updating API calls for serverless backend...${NC}"

# Create updated subscription service
mkdir -p src/utils
cat > src/utils/api.js << 'EOF'
import config from '../../config.js';

class ApiService {
  constructor() {
    this.baseUrl = config.API_BASE_URL;
  }

  async subscribe(email) {
    try {
      const response = await fetch(`${this.baseUrl}${config.SUBSCRIPTION_ENDPOINT}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email }),
      });

      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.message || 'Subscription failed');
      }

      return data;
    } catch (error) {
      console.error('Subscription error:', error);
      throw error;
    }
  }

  async getSubscriberCount() {
    try {
      const response = await fetch(`${this.baseUrl}/subscriber-count`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        return { subscriber_count: 0 };
      }

      return await response.json();
    } catch (error) {
      console.error('Error fetching subscriber count:', error);
      return { subscriber_count: 0 };
    }
  }
}

export default new ApiService();
EOF

# Install dependencies if package.json exists
if [ -f "package.json" ]; then
    echo -e "${YELLOW}📦 Installing dependencies...${NC}"
    npm install
fi

# Build the static site
echo -e "${YELLOW}🏗️  Building static site...${NC}"
npm run build

echo -e "${GREEN}✅ Frontend setup completed!${NC}"
echo ""
echo "📋 Next steps:"
echo "1. Update the API_BASE_URL in frontend-static/config.js with your actual API Gateway URL"
echo "2. Upload the 'out' directory to your S3 website bucket"
echo "3. Test the subscription functionality"

cd .. 