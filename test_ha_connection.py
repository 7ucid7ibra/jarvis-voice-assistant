#!/usr/bin/env python3
"""
Quick test script to verify Home Assistant connection.
Run this to check if your HA credentials are working.
"""
from jarvis_assistant.config import cfg
from jarvis_assistant.ha_client import HomeAssistantClient
import sys

def test_connection():
    print("=" * 50)
    print("Home Assistant Connection Test")
    print("=" * 50)
    print(f"HA URL: {cfg.ha_url}")
    print(f"HA Token: {'*' * 20 if cfg.ha_token else '(not set)'}")
    print()
    
    if not cfg.ha_token:
        print("❌ ERROR: No HA token found!")
        print("Please update settings.json or set HA_TOKEN environment variable.")
        return False
    
    try:
        client = HomeAssistantClient()
        print("Testing connection by toggling test switch...")
        
        # Try to turn on the switch
        result = client.set_test_switch(True)
        print(f"✅ Successfully turned ON test switch!")
        print(f"Response: {result}")
        
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print()
        print("Troubleshooting:")
        print("1. Check if Home Assistant is running")
        print("2. Verify the URL is correct (e.g., http://192.168.x.x:8123)")
        print("3. Verify the token is valid")
        print("4. Make sure 'input_boolean.switch' exists in HA")
        return False

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
