#!/bin/bash
# Setup script for EC2 instances - installs Chrome, Python, and dependencies
# This script is used during EC2 instance initialization

set -e

echo "🛠️ Setting up EC2 instance for visual tweet processing..."
echo "📅 Started at: $(date)"

# Log all output
exec > >(tee /var/log/visual-processing-setup.log)
exec 2>&1

# Update system packages
echo "📦 Updating system packages..."
yum update -y

# Install basic packages
echo "📦 Installing basic packages..."
yum install -y python3.11 python3.11-pip git wget unzip curl

# Create symbolic links for python commands
ln -sf /usr/bin/python3.11 /usr/local/bin/python
ln -sf /usr/bin/python3.11 /usr/local/bin/python3
ln -sf /usr/bin/pip3.11 /usr/local/bin/pip
ln -sf /usr/bin/pip3.11 /usr/local/bin/pip3

# Install Chrome
echo "🌐 Installing Google Chrome..."
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | rpm --import -

cat > /etc/yum.repos.d/google-chrome.repo << 'EOF'
[google-chrome]
name=google-chrome
baseurl=http://dl.google.com/linux/chrome/rpm/stable/x86_64
enabled=1
gpgcheck=1
gpgkey=https://dl.google.com/linux/linux_signing_key.pub
EOF

yum install -y google-chrome-stable

# Verify Chrome installation
if command -v google-chrome &> /dev/null; then
    CHROME_VERSION=$(google-chrome --version)
    echo "✅ Chrome installed: $CHROME_VERSION"
else
    echo "❌ Chrome installation failed"
    exit 1
fi

# Install Python dependencies
echo "🐍 Installing Python dependencies..."
pip3.11 install --upgrade pip

# Core dependencies for visual processing
pip3.11 install \
    boto3==1.34.0 \
    selenium==4.15.2 \
    webdriver-manager==4.0.1 \
    pillow==10.1.0 \
    requests==2.31.0 \
    beautifulsoup4==4.12.2

# Verify Python installations
echo "🔍 Verifying Python installation..."
python --version
pip --version

# Test imports
python -c "import boto3, selenium, webdriver_manager, PIL; print('✅ All Python packages imported successfully')"

# Install CloudWatch agent
echo "📊 Installing CloudWatch agent..."
wget -q https://s3.amazonaws.com/amazoncloudwatch-agent/amazon_linux/amd64/latest/amazon-cloudwatch-agent.rpm
rpm -U ./amazon-cloudwatch-agent.rpm
rm -f ./amazon-cloudwatch-agent.rpm

# Create application directories
echo "📁 Creating application directories..."
mkdir -p /opt/visual-processing/{shared,logs,temp}
chown -R ec2-user:ec2-user /opt/visual-processing

# Create log directories
mkdir -p /var/log/visual-processing
chown ec2-user:ec2-user /var/log/visual-processing

# Configure Chrome for headless operation
echo "🖥️ Configuring Chrome for headless operation..."
mkdir -p /home/ec2-user/.config/google-chrome
chown -R ec2-user:ec2-user /home/ec2-user/.config

# Create Chrome preferences for better stability
cat > /home/ec2-user/.config/google-chrome/Preferences << 'EOF'
{
   "browser": {
      "check_default_browser": false
   },
   "distribution": {
      "import_bookmarks": false,
      "import_history": false,
      "import_search_engine": false,
      "make_chrome_default_for_user": false,
      "skip_first_run_ui": true
   },
   "first_run_tabs": [
      "about:blank"
   ]
}
EOF

chown ec2-user:ec2-user /home/ec2-user/.config/google-chrome/Preferences

# Set up environment variables for Chrome
cat >> /etc/environment << 'EOF'
DISPLAY=:99
CHROME_BIN=/usr/bin/google-chrome
CHROME_PATH=/usr/bin/google-chrome
EOF

# Create a test script to verify Chrome works in headless mode
cat > /opt/visual-processing/test-chrome.py << 'EOF'
#!/usr/bin/env python3
"""Test script to verify Chrome works in headless mode"""

import sys
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time

def test_chrome():
    print("🧪 Testing Chrome in headless mode...")
    
    # Configure Chrome options
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--disable-plugins')
    chrome_options.add_argument('--disable-images')
    chrome_options.add_argument('--disable-javascript')
    
    try:
        # Create driver
        driver = webdriver.Chrome(options=chrome_options)
        
        # Test navigation
        driver.get('https://httpbin.org/html')
        
        # Check if page loaded
        title = driver.title
        print(f"✅ Page loaded successfully. Title: {title}")
        
        # Take a screenshot test
        driver.save_screenshot('/tmp/test-screenshot.png')
        print("✅ Screenshot test successful")
        
        # Cleanup
        driver.quit()
        
        return True
        
    except Exception as e:
        print(f"❌ Chrome test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_chrome()
    sys.exit(0 if success else 1)
EOF

chmod +x /opt/visual-processing/test-chrome.py
chown ec2-user:ec2-user /opt/visual-processing/test-chrome.py

# Create a startup script for visual processing
cat > /opt/visual-processing/run-visual-processing.sh << 'EOF'
#!/bin/bash
# Main script to run visual processing on EC2

set -e

echo "🚀 Starting visual processing on EC2..."
echo "📅 $(date)"

# Set environment variables
export PYTHONPATH=/opt/visual-processing:/opt/visual-processing/shared
export DISPLAY=:99

# Change to application directory
cd /opt/visual-processing

# Download latest code if not present
if [ ! -f "visual_processing_service.py" ]; then
    echo "📥 Downloading application code from S3..."
    aws s3 cp "s3://${S3_BUCKET}/code/ec2-processing.tar.gz" . || {
        echo "❌ Failed to download application code"
        exit 1
    }
    
    tar -xzf ec2-processing.tar.gz
    mv ec2-processing/* .
    mv lambdas/shared/* shared/
    rm -rf ec2-processing lambdas ec2-processing.tar.gz
fi

# Run the visual processing
echo "🎯 Running visual processing..."
python visual_processing_service.py "$@"

echo "✅ Visual processing completed"
EOF

chmod +x /opt/visual-processing/run-visual-processing.sh
chown ec2-user:ec2-user /opt/visual-processing/run-visual-processing.sh

# Create systemd service for automatic shutdown after processing
cat > /etc/systemd/system/visual-processing.service << 'EOF'
[Unit]
Description=Visual Tweet Processing Service
After=network.target

[Service]
Type=oneshot
User=ec2-user
Group=ec2-user
WorkingDirectory=/opt/visual-processing
ExecStart=/opt/visual-processing/run-visual-processing.sh
StandardOutput=journal
StandardError=journal
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable visual-processing.service

# Test Chrome installation as ec2-user
echo "🧪 Testing Chrome installation..."
sudo -u ec2-user python3.11 /opt/visual-processing/test-chrome.py

if [ $? -eq 0 ]; then
    echo "✅ Chrome test passed"
else
    echo "❌ Chrome test failed"
    exit 1
fi

# Clean up temporary files
rm -f /tmp/test-screenshot.png

# Create completion marker
echo "✅ EC2 setup completed successfully at $(date)" > /opt/visual-processing/setup-complete.txt
chown ec2-user:ec2-user /opt/visual-processing/setup-complete.txt

echo ""
echo "🎉 EC2 setup completed successfully!"
echo "📋 Summary:"
echo "   ✅ System packages updated"
echo "   ✅ Python 3.11 and pip installed"
echo "   ✅ Google Chrome installed and tested"
echo "   ✅ Python dependencies installed"
echo "   ✅ CloudWatch agent installed"
echo "   ✅ Application directories created"
echo "   ✅ Visual processing service configured"
echo ""
echo "🔧 The instance is ready for visual tweet processing!"
echo "📝 Logs are available in /var/log/visual-processing-setup.log" 