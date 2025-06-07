#!/bin/bash
# Health check script for Fargate visual processing container

set -e

# Check if Chrome is available
if ! command -v google-chrome &> /dev/null; then
    echo "ERROR: Google Chrome not found"
    exit 1
fi

# Check if ChromeDriver is available
if ! command -v chromedriver &> /dev/null; then
    echo "ERROR: ChromeDriver not found"
    exit 1
fi

# Check if Python can import required modules
python3 -c "
import sys
import selenium
import boto3
import google.generativeai
print('All required modules can be imported')
" || {
    echo "ERROR: Required Python modules not available"
    exit 1
}

# Check if we can start Chrome in headless mode
timeout 10s python3 -c "
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

options = Options()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--disable-gpu')

try:
    driver = webdriver.Chrome(options=options)
    driver.quit()
    print('Chrome WebDriver working correctly')
except Exception as e:
    print(f'Chrome WebDriver test failed: {e}')
    exit(1)
" || {
    echo "ERROR: Chrome WebDriver not working"
    exit 1
}

echo "Health check passed: Container is ready for visual processing"
exit 0 