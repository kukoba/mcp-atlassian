#!/usr/bin/env python3
"""Diagnostic script to check Confluence configuration."""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv

# Load .env file
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    print(f"✓ Loading .env from: {env_file}")
    load_dotenv(env_file)
else:
    print(f"⚠️  No .env file found at: {env_file}")

print("\n" + "="*60)
print("CONFLUENCE CONFIGURATION DIAGNOSTICS")
print("="*60 + "\n")

# Check environment variables
print("1. CHECKING ENVIRONMENT VARIABLES:")
print("-" * 60)

confluence_url = os.getenv("CONFLUENCE_URL")
confluence_username = os.getenv("CONFLUENCE_USERNAME")
confluence_api_token = os.getenv("CONFLUENCE_API_TOKEN")
confluence_personal_token = os.getenv("CONFLUENCE_PERSONAL_TOKEN")
oauth_enable = os.getenv("ATLASSIAN_OAUTH_ENABLE")
oauth_client_id = os.getenv("ATLASSIAN_OAUTH_CLIENT_ID")
oauth_client_secret = os.getenv("ATLASSIAN_OAUTH_CLIENT_SECRET")
oauth_redirect_uri = os.getenv("ATLASSIAN_OAUTH_REDIRECT_URI")
oauth_scope = os.getenv("ATLASSIAN_OAUTH_SCOPE")
oauth_cloud_id = os.getenv("ATLASSIAN_OAUTH_CLOUD_ID")
oauth_access_token = os.getenv("ATLASSIAN_OAUTH_ACCESS_TOKEN")

def mask_value(value, show_chars=4):
    """Mask sensitive values."""
    if not value:
        return None
    if len(value) <= show_chars:
        return "***"
    return f"{value[:show_chars]}...{value[-show_chars:]}"

print(f"CONFLUENCE_URL:               {confluence_url or '❌ NOT SET'}")
print(f"CONFLUENCE_USERNAME:          {confluence_username or '❌ NOT SET'}")
print(f"CONFLUENCE_API_TOKEN:         {mask_value(confluence_api_token) or '❌ NOT SET'}")
print(f"CONFLUENCE_PERSONAL_TOKEN:    {mask_value(confluence_personal_token) or '❌ NOT SET'}")
print(f"ATLASSIAN_OAUTH_ENABLE:       {oauth_enable or '❌ NOT SET'}")
print(f"ATLASSIAN_OAUTH_CLIENT_ID:    {mask_value(oauth_client_id) or '❌ NOT SET'}")
print(f"ATLASSIAN_OAUTH_CLIENT_SECRET:{mask_value(oauth_client_secret) or '❌ NOT SET'}")
print(f"ATLASSIAN_OAUTH_REDIRECT_URI: {oauth_redirect_uri or '❌ NOT SET'}")
print(f"ATLASSIAN_OAUTH_SCOPE:        {mask_value(oauth_scope, 10) or '❌ NOT SET'}")
print(f"ATLASSIAN_OAUTH_CLOUD_ID:     {oauth_cloud_id or '❌ NOT SET'}")
print(f"ATLASSIAN_OAUTH_ACCESS_TOKEN: {mask_value(oauth_access_token) or '❌ NOT SET'}")

# Determine URL type
print(f"\n2. CHECKING URL TYPE:")
print("-" * 60)

from mcp_atlassian.utils.urls import is_atlassian_cloud_url

if confluence_url:
    is_cloud = is_atlassian_cloud_url(confluence_url)
    print(f"URL Type: {'☁️  CLOUD (*.atlassian.net)' if is_cloud else '🏢 SERVER/DATA CENTER'}")
else:
    print("❌ Cannot determine URL type - CONFLUENCE_URL not set")
    is_cloud = None

# Check authentication configuration
print(f"\n3. CHECKING AUTHENTICATION CONFIGURATION:")
print("-" * 60)

auth_methods = []

# OAuth Full
if all([oauth_client_id, oauth_client_secret, oauth_redirect_uri, oauth_scope, oauth_cloud_id]):
    auth_methods.append("✓ OAuth 2.0 (Full Config) - AVAILABLE")
# OAuth BYOT
elif oauth_access_token and oauth_cloud_id:
    auth_methods.append("✓ OAuth 2.0 (Bring Your Own Token) - AVAILABLE")
# OAuth Minimal
elif oauth_enable and oauth_enable.lower() in ("true", "1", "yes"):
    auth_methods.append("✓ OAuth 2.0 (Minimal - user-provided tokens) - AVAILABLE")
else:
    auth_methods.append("❌ OAuth 2.0 - NOT CONFIGURED")

# Basic Auth (Cloud)
if is_cloud and confluence_username and confluence_api_token:
    auth_methods.append("✓ Basic Auth (Cloud - API Token) - AVAILABLE")
elif is_cloud:
    auth_methods.append("❌ Basic Auth (Cloud) - INCOMPLETE (need USERNAME + API_TOKEN)")

# PAT (Server/DC)
if not is_cloud and is_cloud is not None:
    if confluence_personal_token:
        auth_methods.append("✓ Personal Access Token (Server/DC) - AVAILABLE")
    else:
        auth_methods.append("❌ Personal Access Token (Server/DC) - NOT SET")

    # Basic Auth for Server/DC
    if confluence_username and confluence_api_token:
        auth_methods.append("✓ Basic Auth (Server/DC) - AVAILABLE")

for method in auth_methods:
    print(method)

# Try to load configuration
print(f"\n4. TESTING CONFIGURATION LOADING:")
print("-" * 60)

try:
    from mcp_atlassian.confluence.config import ConfluenceConfig

    config = ConfluenceConfig.from_env()
    print(f"✓ Configuration loaded successfully")
    print(f"  - Auth Type: {config.auth_type}")
    print(f"  - URL: {config.url}")
    print(f"  - Is Cloud: {config.is_cloud}")

    # Check if auth is configured
    is_auth_ok = config.is_auth_configured()
    if is_auth_ok:
        print(f"✅ Authentication is FULLY CONFIGURED and READY")
    else:
        print(f"❌ Authentication is INCOMPLETE or INVALID")
        print(f"   Config details:")
        print(f"   - auth_type: {config.auth_type}")
        print(f"   - username: {bool(config.username)}")
        print(f"   - api_token: {bool(config.api_token)}")
        print(f"   - personal_token: {bool(config.personal_token)}")
        print(f"   - oauth_config: {bool(config.oauth_config)}")

except Exception as e:
    print(f"❌ Failed to load configuration: {e}")
    import traceback
    traceback.print_exc()

# Test service availability
print(f"\n5. TESTING SERVICE AVAILABILITY CHECK:")
print("-" * 60)

try:
    from mcp_atlassian.utils.environment import get_available_services

    services = get_available_services()
    confluence_available = services.get("confluence", False)

    if confluence_available:
        print(f"✅ Confluence service is AVAILABLE")
    else:
        print(f"❌ Confluence service is NOT AVAILABLE")
        print(f"   This means environment variables don't match any supported auth pattern")

except Exception as e:
    print(f"❌ Failed to check service availability: {e}")

# Summary
print(f"\n" + "="*60)
print("SUMMARY & RECOMMENDATIONS:")
print("="*60)

if confluence_url:
    print(f"\n✓ CONFLUENCE_URL is set: {confluence_url}")
    if is_cloud:
        print(f"\n☁️  You're using Confluence CLOUD")
        print(f"\nRequired for Cloud:")
        if confluence_username and confluence_api_token:
            print(f"  ✅ CONFLUENCE_USERNAME: set")
            print(f"  ✅ CONFLUENCE_API_TOKEN: set")
        else:
            print(f"  {'✅' if confluence_username else '❌'} CONFLUENCE_USERNAME: {'set' if confluence_username else 'MISSING'}")
            print(f"  {'✅' if confluence_api_token else '❌'} CONFLUENCE_API_TOKEN: {'set' if confluence_api_token else 'MISSING'}")
            print(f"\n🔧 FIX: Set both CONFLUENCE_USERNAME and CONFLUENCE_API_TOKEN in your .env")
            print(f"   Example:")
            print(f"   CONFLUENCE_USERNAME=your.email@company.com")
            print(f"   CONFLUENCE_API_TOKEN=your_api_token_here")
    else:
        print(f"\n🏢 You're using Confluence SERVER/DATA CENTER")
        print(f"\nRequired for Server/DC (choose one):")
        if confluence_personal_token:
            print(f"  ✅ CONFLUENCE_PERSONAL_TOKEN: set (RECOMMENDED)")
        else:
            print(f"  ❌ CONFLUENCE_PERSONAL_TOKEN: MISSING")
            print(f"  OR")
            if confluence_username and confluence_api_token:
                print(f"  ✅ CONFLUENCE_USERNAME + CONFLUENCE_API_TOKEN: set")
            else:
                print(f"  ❌ CONFLUENCE_USERNAME + CONFLUENCE_API_TOKEN: incomplete")

            if not confluence_personal_token and not (confluence_username and confluence_api_token):
                print(f"\n🔧 FIX: Set CONFLUENCE_PERSONAL_TOKEN in your .env")
                print(f"   Example:")
                print(f"   CONFLUENCE_PERSONAL_TOKEN=your_pat_here")
else:
    print(f"\n❌ CONFLUENCE_URL is NOT SET")
    print(f"\n🔧 FIX: Add CONFLUENCE_URL to your .env file")
    print(f"   Example for Cloud:")
    print(f"   CONFLUENCE_URL=https://your-company.atlassian.net/wiki")
    print(f"   Example for Server/DC:")
    print(f"   CONFLUENCE_URL=https://confluence.your-company.com")

print(f"\n" + "="*60)
print("Run this script again after making changes to verify the fix!")
print("="*60 + "\n")
