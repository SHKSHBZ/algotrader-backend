# 🚀 Zerodha API Integration Setup

Complete guide for setting up persistent Zerodha API sessions that save your login credentials and tokens.

## 📋 Quick Setup (3 Simple Steps)

### Step 1: Get Your API Credentials
1. Go to [https://kite.trade/](https://kite.trade/)
2. Login with your Zerodha account
3. Go to "My Apps" section
4. Create a new app or use existing one
5. Copy your **API Key** and **API Secret**

### Step 2: Configure Your Credentials
```bash
python setup_zerodha.py
```
- Enter your API Key and Secret
- The setup will save your credentials securely
- Test authentication if prompted

### Step 3: Start Trading
```bash
python paper_trading.py
```
- The bot will automatically use your saved credentials
- No need to login again until session expires (6:00 AM next day)

## 🔧 Advanced Usage

### Check Session Status
```bash
python zerodha_status.py
```
Shows:
- Current session status
- User information
- Session expiry time
- Configuration details

### Manual Configuration
Create `zerodha_config.json`:
```json
{
  "api_key": "your_api_key_here",
  "api_secret": "your_api_secret_here",
  "created_at": "2025-09-16T11:30:00.000000"
}
```

## 📁 Files Created

### Configuration File: `zerodha_config.json`
```json
{
  "api_key": "xxxxxxxx",
  "api_secret": "xxxxxxxx", 
  "created_at": "2025-09-16T11:30:00.000000",
  "instructions": {
    "usage": "This file stores your Zerodha API credentials",
    "get_credentials": "Get your API key and secret from https://kite.trade/",
    "security": "Keep this file secure and do not share it"
  }
}
```

### Session File: `zerodha_session.json`
```json
{
  "access_token": "xxxxxxxx",
  "api_key": "xxxxxxxx", 
  "api_secret": "xxxxxxxx",
  "created_at": "2025-09-16T11:30:00.000000",
  "expires_at": "2025-09-17T06:00:00.000000",
  "user_name": "Your Name",
  "user_id": "XX1234",
  "broker": "ZERODHA",
  "session_version": "2.0"
}
```

## ⏰ Session Management

### How Sessions Work
- **Login Once**: Authenticate once, token saved automatically
- **Auto-Reuse**: Bot reuses saved token until expiry
- **Smart Expiry**: Tokens expire at 6:00 AM next day (Zerodha policy)
- **Auto-Cleanup**: Invalid sessions are automatically removed

### Session Lifecycle
1. **First Run**: Manual authentication required
2. **Subsequent Runs**: Automatic token reuse
3. **Token Expiry**: Re-authentication prompt
4. **Session Validation**: Every startup checks token validity

## 🛡️ Security Features

### Credential Protection
- API credentials stored locally only
- Session tokens automatically managed
- Invalid sessions auto-cleared
- No hardcoded credentials in code

### Session Validation
- Token validity checked on startup
- API calls test session health
- Expired sessions automatically detected
- Graceful fallback to local cache if needed

## 🔄 Authentication Flow

```
1. Check for saved session
   ↓
2. If valid session found → Use existing token
   ↓
3. If no session → Check for saved credentials
   ↓
4. If credentials found → Auto-authenticate
   ↓
5. If no credentials → Prompt for setup
   ↓
6. Save new session for future use
```

## 🚨 Troubleshooting

### Common Issues

**"No session found"**
- Run `python setup_zerodha.py` to configure
- Check if `zerodha_config.json` exists

**"Session expired"** 
- Normal behavior at 6:00 AM daily
- Re-run bot to authenticate again
- Check system clock accuracy

**"Authentication failed"**
- Verify API key and secret are correct
- Check if API app is active on kite.trade
- Clear session: `python zerodha_status.py`

**"Invalid session data"**
- Delete `zerodha_session.json` 
- Run setup again: `python setup_zerodha.py`

### Reset Everything
```bash
# Clear all saved data
rm zerodha_config.json zerodha_session.json

# Start fresh setup
python setup_zerodha.py
```

## 📞 Support Commands

```bash
# Setup credentials
python setup_zerodha.py

# Check session status  
python zerodha_status.py

# Start paper trading
python paper_trading.py

# Clear session only
python -c "from paper_trading import ZerodhaLiveAPI; ZerodhaLiveAPI().clear_session()"
```

## ✅ Benefits

- **One-Time Setup**: Configure once, use forever
- **Automatic Login**: No daily credential entry
- **Session Persistence**: Tokens saved and reused
- **Smart Expiry**: Handles Zerodha's 6:00 AM expiry
- **Fallback Support**: Local cache if Zerodha fails
- **Security**: Local storage, no cloud dependencies

## 🎯 What's Different Now

### Before (Manual Every Time)
```
1. Start bot
2. Enter API key
3. Enter API secret  
4. Open browser
5. Login to Zerodha
6. Authorize app
7. Copy redirect URL
8. Paste URL in terminal
```

### After (Automatic)
```
1. Start bot
2. ✅ Done! (Uses saved session)
```

Your Zerodha integration is now fully automated! 🎉