#!/usr/bin/env python3
"""
Zerodha API Setup Utility
Easy setup for your Zerodha API credentials
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from paper_trading import ZerodhaLiveAPI
from pathlib import Path
import json

def main():
    print("=" * 60)
    print("🚀 ZERODHA API SETUP UTILITY")
    print("=" * 60)
    print()
    
    # Check if config already exists
    config_file = Path('zerodha_config.json')
    session_file = Path('zerodha_session.json')
    
    if config_file.exists():
        print("📁 Existing configuration found!")
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            print(f"   API Key: {config.get('api_key', 'Not found')}")
            print(f"   Created: {config.get('created_at', 'Unknown')}")
            print()
            
            choice = input("Do you want to update the configuration? (y/n): ").strip().lower()
            if choice != 'y':
                print("Setup cancelled.")
                return
        except Exception as e:
            print(f"⚠️  Error reading existing config: {e}")
    
    # Get session status
    if session_file.exists():
        api = ZerodhaLiveAPI()
        status = api.get_session_status()
        print(f"📊 Current Session Status: {status['message']}")
        if status['active']:
            print(f"   User: {status['user_name']}")
            print(f"   Expires: {status['expires_at']}")
            print(f"   Time left: {status['time_left']}")
        print()
    
    print("📋 To get your API credentials:")
    print("   1. Go to https://kite.trade/")
    print("   2. Login with your Zerodha account")
    print("   3. Go to 'My Apps' section")
    print("   4. Create a new app or use existing one")
    print("   5. Copy the API Key and API Secret")
    print()
    
    # Get credentials from user
    api_key = input("🔑 Enter your API Key: ").strip()
    if not api_key:
        print("❌ API Key is required!")
        return
    
    api_secret = input("🔐 Enter your API Secret: ").strip()
    if not api_secret:
        print("❌ API Secret is required!")
        return
    
    print()
    print("💾 Saving configuration...")
    
    # Save configuration
    try:
        config_file = ZerodhaLiveAPI.setup_config(api_key, api_secret)
        print()
        print("✅ Setup completed successfully!")
        print()
        print("📖 What happens next:")
        print("   • Your credentials are saved securely")
        print("   • The bot will automatically use these credentials")
        print("   • You'll only need to authenticate once per day")
        print("   • Session tokens are saved and reused")
        print()
        
        # Test authentication
        test_choice = input("🧪 Would you like to test the authentication now? (y/n): ").strip().lower()
        if test_choice == 'y':
            print()
            print("🔄 Testing authentication...")
            
            api = ZerodhaLiveAPI()
            if api.authenticate():
                print("✅ Authentication successful!")
                if api.load_instruments():
                    print("✅ Instrument data loaded!")
                
                # Show session status
                status = api.get_session_status()
                print(f"📊 Session Status: {status['message']}")
                print(f"   User: {status['user_name']}")
                print(f"   Valid until: {status['expires_at']}")
            else:
                print("❌ Authentication failed!")
                print("   Please check your credentials and try again")
        
    except Exception as e:
        print(f"❌ Setup failed: {e}")

if __name__ == "__main__":
    main()