#!/usr/bin/env python3
"""
Generate Device Access Authorization Link

This creates the URL you need to visit to authorize your Nest devices
with the Device Access project.
"""

import os
from dotenv import load_dotenv
from urllib.parse import urlencode

load_dotenv()

# Get credentials from environment
PROJECT_ID = os.getenv("SDM_PROJECT_ID")
CLIENT_ID = os.getenv("SDM_CLIENT_ID")

if not PROJECT_ID or not CLIENT_ID:
    print("ERROR: Missing SDM_PROJECT_ID or SDM_CLIENT_ID in .env file")
    exit(1)

# Build authorization URL
base_url = f"https://nestservices.google.com/partnerconnections/{PROJECT_ID}/auth"

params = {
    "redirect_uri": "https://www.google.com",
    "access_type": "offline",
    "prompt": "consent",
    "client_id": CLIENT_ID,
    "response_type": "code",
    "scope": "https://www.googleapis.com/auth/sdm.service"
}

auth_url = f"{base_url}?{urlencode(params)}"

print("=" * 80)
print("Device Access Authorization Link")
print("=" * 80)
print()
print("Visit this URL in your browser to authorize your Nest devices:")
print()
print(auth_url)
print()
print("=" * 80)
print("What happens next:")
print("1. You'll be asked to sign in with your Google account (use the one with Nest devices)")
print("2. You'll see a list of your Nest devices")
print("3. Select the devices you want to authorize")
print("4. Click 'Allow'")
print("5. You'll be redirected to google.com (you can ignore the page)")
print("6. Your devices will now appear in the SDM API")
print("=" * 80)
