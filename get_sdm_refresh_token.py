#!/usr/bin/env python3
"""
OAuth Helper Script - Get SDM Refresh Token

This script helps you obtain a refresh token for the Google Smart Device Management API.
Run this ONCE to get your refresh token, then add it to your .env file.

Usage:
    python get_sdm_refresh_token.py
"""

import os
import json
from google_auth_oauthlib.flow import InstalledAppFlow
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# SDM API scope
SCOPES = ['https://www.googleapis.com/auth/sdm.service']

# OAuth credentials from environment
CLIENT_ID = os.getenv('SDM_CLIENT_ID')
CLIENT_SECRET = os.getenv('SDM_CLIENT_SECRET')
SDM_PROJECT_ID = os.getenv('SDM_PROJECT_ID')

def main():
    print("=" * 60)
    print("Google Smart Device Management API - OAuth Setup")
    print("=" * 60)
    print()

    # Validate environment variables
    if not CLIENT_ID or not CLIENT_SECRET or not SDM_PROJECT_ID:
        print("ERROR: Missing required environment variables in .env file:")
        if not CLIENT_ID:
            print("  - SDM_CLIENT_ID")
        if not CLIENT_SECRET:
            print("  - SDM_CLIENT_SECRET")
        if not SDM_PROJECT_ID:
            print("  - SDM_PROJECT_ID")
        print()
        print("Please add these to your .env file and try again.")
        return

    print(f"Project ID: {SDM_PROJECT_ID}")
    print(f"Client ID: {CLIENT_ID}")
    print()

    # Create OAuth client config
    client_config = {
        "installed": {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost:3000/auth/callback", "http://localhost:8080/"]
        }
    }

    print("Starting OAuth flow...")
    print("A browser window will open for you to authorize the application.")
    print()

    try:
        # Run OAuth flow
        flow = InstalledAppFlow.from_client_config(
            client_config,
            scopes=SCOPES
        )

        # This will open a browser window
        credentials = flow.run_local_server(port=3000)

        print()
        print("=" * 60)
        print("SUCCESS! Authorization complete.")
        print("=" * 60)
        print()
        print("Your refresh token:")
        print("-" * 60)
        print(credentials.refresh_token)
        print("-" * 60)
        print()
        print("NEXT STEPS:")
        print("1. Copy the refresh token above")
        print("2. Add it to your .env file:")
        print(f"   SDM_REFRESH_TOKEN={credentials.refresh_token}")
        print()
        print("3. Restart your application")
        print()

        # Optionally save to a file
        save = input("Save credentials to sdm_credentials.json? (y/n): ").lower()
        if save == 'y':
            creds_data = {
                "refresh_token": credentials.refresh_token,
                "token_uri": credentials.token_uri,
                "client_id": credentials.client_id,
                "client_secret": credentials.client_secret,
                "scopes": credentials.scopes
            }

            with open('sdm_credentials.json', 'w') as f:
                json.dump(creds_data, f, indent=2)

            print("Saved to sdm_credentials.json (add this to .gitignore!)")

    except Exception as e:
        print()
        print("=" * 60)
        print("ERROR during OAuth flow:")
        print("=" * 60)
        print(str(e))
        print()
        print("Troubleshooting:")
        print("1. Make sure your OAuth Client ID redirect URIs include:")
        print("   - http://localhost:3000/auth/callback")
        print("   - https://www.google.com")
        print()
        print("2. Make sure you're using the correct Google account")
        print("   (the one that owns the Nest devices)")
        print()

if __name__ == '__main__':
    main()
