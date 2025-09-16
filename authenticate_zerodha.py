#!/usr/bin/env python3
"""
Zerodha Authentication Script
Simple script to authenticate with Zerodha and save session for your paper trading bot
"""

import sys
import os
from zerodha_auth import ZerodhaAuth

def main():
    """
    Main authentication function
    """
    print("🔐 ZERODHA AUTHENTICATION FOR PAPER TRADING")
    print("=" * 50)
    print("This script will authenticate you with Zerodha and save")
    print("the session for your paper trading bot to use.")
    print("=" * 50)
    print()
    
    # Initialize authentication
    auth = ZerodhaAuth()
    
    # Check current session status
    info = auth.get_session_info()
    
    if info.get("active"):
        print("✅ ACTIVE SESSION FOUND!")
        print(f"👤 User: {info['user_name']}")
        print(f"⏰ Valid until: {info['expires_at']}")
        print(f"🕐 Time remaining: {info['time_left']}")
        print()
        
        choice = input("🔄 Do you want to refresh the session? (y/n): ").strip().lower()
        if choice != 'y':
            print()
            print("✅ Your session is already active!")
            print("🚀 You can now run: python paper_trading.py")
            return
        
        print()
        print("🔄 Refreshing session...")
        auth.clear_session()
    
    else:
        print("ℹ️  No active session found")
        print("🔑 Starting authentication process...")
        print()
    
    # Perform authentication
    try:
        if auth.authenticate():
            print()
            print("🎉 AUTHENTICATION SUCCESSFUL!")
            print("=" * 30)
            
            # Show session details
            info = auth.get_session_info()
            print(f"👤 User: {info['user_name']}")
            print(f"📅 Session created: {info['created_at']}")
            print(f"⏰ Valid until: {info['expires_at']}")
            print(f"🕐 Duration: {info['time_left']}")
            print()
            print("✅ Your session has been saved!")
            print("🚀 You can now run: python paper_trading.py")
            print()
            print("💡 Your paper trading bot will automatically use this session")
            print("💡 Session will expire at 6:00 AM tomorrow")
            
        else:
            print()
            print("❌ AUTHENTICATION FAILED!")
            print("=" * 25)
            print("Please check:")
            print("• Your API key and secret are correct")
            print("• You have internet connection")
            print("• You completed the browser login properly")
            print()
            print("💡 Get your API credentials from: https://kite.trade/")
            
    except KeyboardInterrupt:
        print()
        print("🛑 Authentication cancelled by user")
    except Exception as e:
        print()
        print(f"❌ Authentication error: {e}")
        print("💡 Please try again or check your credentials")

if __name__ == "__main__":
    main()