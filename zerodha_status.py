#!/usr/bin/env python3
"""
Zerodha Session Status Utility
Check your current Zerodha API session status
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from paper_trading import ZerodhaLiveAPI
from pathlib import Path
import json

def main():
    print("=" * 60)
    print("📊 ZERODHA SESSION STATUS")
    print("=" * 60)
    
    api = ZerodhaLiveAPI()
    
    # Check configuration
    config_file = Path('zerodha_config.json')
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            print(f"✅ Configuration Found")
            print(f"   API Key: {config.get('api_key', 'Not found')}")
            print(f"   Created: {config.get('created_at', 'Unknown')}")
        except Exception as e:
            print(f"❌ Configuration Error: {e}")
    else:
        print(f"❌ No configuration found")
        print(f"   Run 'python setup_zerodha.py' to configure")
    
    print()
    
    # Check session status
    status = api.get_session_status()
    
    if status['active']:
        print(f"✅ Session Active")
        print(f"   User: {status['user_name']}")
        print(f"   Created: {status['created_at'].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Expires: {status['expires_at'].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Time Left: {status['time_left']}")
    else:
        print(f"❌ {status['message']}")
        if 'expired' in status['message'].lower():
            print(f"   Re-run the paper trading bot to authenticate again")
    
    print()
    
    # Session management options
    if status['active']:
        print("🔧 Session Management:")
        choice = input("   Clear current session? (y/n): ").strip().lower()
        if choice == 'y':
            api.clear_session()
            print("   Session cleared!")
    else:
        print("🚀 Quick Actions:")
        print("   • Run 'python setup_zerodha.py' to configure API")
        print("   • Run 'python paper_trading.py' to start trading")
    
    print()

if __name__ == "__main__":
    main()