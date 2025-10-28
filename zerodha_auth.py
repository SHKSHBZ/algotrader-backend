#!/usr/bin/env python3
"""
Zerodha Authentication Module
Standalone authentication system for Zerodha KiteConnect API
Handles login, session management, and token persistence
"""

import json
import os
import webbrowser
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import pytz
from kiteconnect import KiteConnect

IST = pytz.timezone('Asia/Kolkata')

class ZerodhaAuth:
    def auto_authenticate(self):
        """
        Automatically authenticate: use valid session if available, else prompt for login.
        Returns True if authentication is successful, False otherwise.
        """
        # Load credentials
        if not self.load_credentials():
            print("No credentials found. Run setup first.")
            if not self.setup_credentials():
                return False
        # Try to load session
        if self.load_session():
            print("✅ Using existing session (auto)")
            return True
        # If session missing/expired, do fresh login
        print("Session expired or missing. Starting login...")
        return self.fresh_login()
    """
    Handles all Zerodha authentication and session management
    """
    
    def __init__(self):
        self.api_key = None
        self.api_secret = None
        self.access_token = None
        self.kite = None
        
        # File paths
        self.config_file = Path('zerodha_config.json')
        self.session_file = Path('zerodha_session.json')
        
        print("[AUTH] Zerodha Authentication System")
        print("=" * 40)
        
    def setup_credentials(self, api_key: str = None, api_secret: str = None):
        """
        Setup and save API credentials
        """
        if not api_key:
            print("\n[INFO] Get your credentials from: https://kite.trade/")
            print("   1. Login to Kite Connect")
            print("   2. Go to 'My Apps' section") 
            print("   3. Create new app or use existing")
            print("   4. Copy API Key and Secret")
            print()
            
            api_key = input("[KEY] Enter your API Key: ").strip()
            api_secret = input("[SECRET] Enter your API Secret: ").strip()
        
        if not api_key or not api_secret:
            print("[ERROR] Both API Key and Secret are required!")
            return False
        
        # Save credentials
        config_data = {
            'api_key': api_key,
            'api_secret': api_secret,
            'created_at': datetime.now(IST).isoformat(),
            'setup_version': '1.0'
        }
        
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config_data, f, indent=2)
            
            print(f"\n✅ Credentials saved to {self.config_file}")
            print(f"📱 API Key: {api_key}")
            
            self.api_key = api_key
            self.api_secret = api_secret
            return True
            
        except Exception as e:
            print(f"❌ Failed to save credentials: {e}")
            return False
    
    def load_credentials(self):
        """
        Load saved API credentials
        """
        try:
            if not self.config_file.exists():
                print("❌ No credentials found. Run setup first.")
                return False
            
            with open(self.config_file, 'r') as f:
                config = json.load(f)
            
            self.api_key = config.get('api_key')
            self.api_secret = config.get('api_secret')
            
            if self.api_key and self.api_secret:
                print(f"✅ Credentials loaded")
                print(f"📱 API Key: {self.api_key}")
                return True
            else:
                print("❌ Invalid credentials in config file")
                return False
                
        except Exception as e:
            print(f"❌ Error loading credentials: {e}")
            return False
    
    def authenticate(self):
        """
        Complete authentication process (uses auto_authenticate)
        """
        return self.auto_authenticate()
    
    def fresh_login(self):
        """
        Perform fresh Zerodha login with browser
        """
        try:
            # Initialize KiteConnect
            self.kite = KiteConnect(api_key=self.api_key)
            
            # Generate login URL
            login_url = self.kite.login_url()
            
            print(f"\n🌐 ZERODHA LOGIN PROCESS")
            print(f"=" * 30)
            print(f"1. Browser will open automatically")
            print(f"2. Login with your Zerodha credentials")
            print(f"3. Complete 2FA (PIN/TOTP)")
            print(f"4. Authorize the application")
            print(f"5. Copy the complete redirect URL")
            print(f"=" * 30)
            
            # Open browser
            print(f"\n🔗 Opening browser...")
            webbrowser.open(login_url)
            
            # Get redirect URL from user
            print(f"\n📋 After successful login and authorization:")
            redirect_url = input("📎 Paste the complete redirect URL here: ").strip()
            
            if not redirect_url:
                print("❌ No URL provided")
                return False
            
            # Extract request token
            parsed_url = urlparse(redirect_url)
            query_params = parse_qs(parsed_url.query)
            
            request_token = query_params.get('request_token', [None])[0]
            
            if not request_token:
                print("❌ No request token found in URL")
                print("💡 Make sure you copied the complete URL after authorization")
                return False
            
            print(f"🎟️ Request token extracted: {request_token[:10]}...")
            
            # Generate access token
            data = self.kite.generate_session(request_token, api_secret=self.api_secret)
            self.access_token = data['access_token']
            
            # Set access token
            self.kite.set_access_token(self.access_token)
            
            # Test the connection
            profile = self.kite.profile()
            
            print(f"\n✅ AUTHENTICATION SUCCESS!")
            print(f"👤 User: {profile['user_name']}")
            print(f"🏢 Broker: {profile.get('broker', 'ZERODHA')}")
            print(f"📧 Email: {profile.get('email', 'N/A')}")
            
            # Save session
            self.save_session(profile)
            
            return True
            
        except Exception as e:
            print(f"\n❌ Authentication failed: {e}")
            print(f"💡 Please check your credentials and try again")
            return False
    
    def save_session(self, profile=None):
        """
        Save session data for reuse
        """
        try:
            if not profile:
                profile = self.kite.profile() if self.kite else {}
            
            # Calculate expiry (6:00 AM next day)
            now = datetime.now(IST)
            next_6am = now.replace(hour=6, minute=0, second=0, microsecond=0)
            if now.hour >= 6:
                next_6am += timedelta(days=1)
            
            session_data = {
                'access_token': self.access_token,
                'api_key': self.api_key,
                'created_at': now.isoformat(),
                'expires_at': next_6am.isoformat(),
                'user_name': profile.get('user_name', 'Unknown'),
                'user_id': profile.get('user_id', 'Unknown'),
                'broker': profile.get('broker', 'ZERODHA'),
                'email': profile.get('email', 'N/A'),
                'session_version': '1.0'
            }
            
            with open(self.session_file, 'w') as f:
                json.dump(session_data, f, indent=2)
            
            print(f"💾 Session saved until: {next_6am.strftime('%Y-%m-%d 06:00:00')}")
            
        except Exception as e:
            print(f"❌ Failed to save session: {e}")
    
    def load_session(self):
        """
        Load and validate existing session
        """
        try:
            if not self.session_file.exists():
                return False
            
            with open(self.session_file, 'r') as f:
                session_data = json.load(f)
            
            # Check API key match
            if session_data.get('api_key') != self.api_key:
                print("⚠️ Session API key mismatch")
                return False
            
            # Check expiry
            expires_at = datetime.fromisoformat(session_data['expires_at'])
            now = datetime.now(IST)
            
            if now >= expires_at:
                print(f"⏰ Session expired at {expires_at.strftime('%Y-%m-%d %H:%M:%S')}")
                return False
            
            # Restore session
            self.access_token = session_data['access_token']
            
            # Test session
            self.kite = KiteConnect(api_key=self.api_key)
            self.kite.set_access_token(self.access_token)
            
            # Validate with API call
            profile = self.kite.profile()
            
            time_left = expires_at - now
            hours, remainder = divmod(time_left.total_seconds(), 3600)
            minutes = remainder // 60
            
            print(f"✅ Session restored for: {profile['user_name']}")
            print(f"⏰ Expires in: {int(hours)}h {int(minutes)}m")
            
            return True
            
        except Exception as e:
            print(f"⚠️ Session validation failed: {e}")
            # Clean up invalid session
            if self.session_file.exists():
                self.session_file.unlink()
            return False
    
    def is_session_valid(self) -> bool:
        """Return True if a saved session exists and is still usable."""
        try:
            if not self.load_credentials():
                return False
            return self.load_session()
        except Exception:
            return False

    def get_session_info(self):
        """
        Get current session information
        """
        if not self.session_file.exists():
            return {"status": "No session found"}
        
        try:
            with open(self.session_file, 'r') as f:
                session_data = json.load(f)
            
            created_at = datetime.fromisoformat(session_data['created_at'])
            expires_at = datetime.fromisoformat(session_data['expires_at'])
            now = datetime.now(IST)
            
            is_active = now < expires_at
            
            if is_active:
                time_left = expires_at - now
                hours, remainder = divmod(time_left.total_seconds(), 3600)
                minutes = remainder // 60
                time_str = f"{int(hours)}h {int(minutes)}m"
            else:
                time_str = "Expired"
            
            return {
                "status": "Active" if is_active else "Expired",
                "user_name": session_data.get('user_name', 'Unknown'),
                "created_at": created_at.strftime('%Y-%m-%d %H:%M:%S'),
                "expires_at": expires_at.strftime('%Y-%m-%d %H:%M:%S'),
                "time_left": time_str,
                "active": is_active
            }
            
        except Exception as e:
            return {"status": f"Error: {e}"}
    
    def clear_session(self):
        """
        Clear saved session
        """
        try:
            if self.session_file.exists():
                self.session_file.unlink()
                print("🗑️ Session cleared")
            else:
                print("ℹ️ No session to clear")
        except Exception as e:
            print(f"❌ Error clearing session: {e}")
    
    def get_kite_instance(self):
        """
        Get authenticated KiteConnect instance
        """
        if self.kite and self.access_token:
            return self.kite
        
        # Load credentials if not already loaded
        if not self.api_key:
            self.load_credentials()
        
        # Try to load existing session
        if self.load_session():
            return self.kite
            
        return None


def main():
    """
    Interactive authentication setup
    """
    auth = ZerodhaAuth()
    
    print("\n🚀 ZERODHA AUTHENTICATION SETUP")
    print("=" * 40)
    
    # Check existing session
    info = auth.get_session_info()
    if info["status"] == "Active":
        print(f"✅ Active session found!")
        print(f"👤 User: {info['user_name']}")
        print(f"⏰ Expires: {info['expires_at']}")
        print(f"🕐 Time left: {info['time_left']}")
        
        choice = input(f"\n🔄 Refresh session anyway? (y/n): ").strip().lower()
        if choice != 'y':
            print("✅ Using existing session")
            return
    
    # Perform authentication
    if auth.authenticate():
        print(f"\n🎉 SETUP COMPLETE!")
        print(f"✅ Your Zerodha session is ready")
        print(f"🚀 You can now run: python paper_trading.py")
        
        # Show session info
        info = auth.get_session_info()
        print(f"\n📊 Session Details:")
        print(f"   User: {info['user_name']}")
        print(f"   Valid until: {info['expires_at']}")
        
    else:
        print(f"\n❌ Authentication failed")
        print(f"💡 Please check your credentials and internet connection")


if __name__ == "__main__":
    main()