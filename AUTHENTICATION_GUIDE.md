# 🔐 Zerodha Authentication Guide

## 🎯 **Simple 2-Step Process**

### **Step 1: Authenticate Once**
```bash
python authenticate_zerodha.py
```

### **Step 2: Start Trading**
```bash
python paper_trading.py
```

**That's it!** No more daily login hassles.

---

## 📋 **What Each File Does**

### **`authenticate_zerodha.py`** - Login Manager
- **Purpose**: Handle Zerodha login and save session
- **When to run**: Once per day (or when session expires)
- **What it does**:
  - Prompts for API Key/Secret (first time only)
  - Opens browser for Zerodha login
  - Saves session until 6:00 AM next day

### **`zerodha_auth.py`** - Authentication Engine
- **Purpose**: Core authentication logic
- **When it runs**: Automatically (you don't run this directly)
- **What it does**:
  - Manages session files
  - Handles token validation
  - Provides KiteConnect instance

### **`paper_trading.py`** - Trading Bot
- **Purpose**: Your main paper trading bot
- **When to run**: Daily for trading
- **What it does**:
  - Uses saved session automatically
  - Falls back to cache if no session
  - Executes your MTFA strategy

---

## 🚀 **Complete Workflow**

### **First Time Setup**
```bash
# Step 1: Run authentication
python authenticate_zerodha.py

# Follow prompts:
# 1. Enter API Key and Secret
# 2. Browser opens automatically
# 3. Login to Zerodha
# 4. Complete 2FA (PIN/TOTP)
# 5. Authorize the application
# 6. Copy redirect URL and paste

# Step 2: Start trading
python paper_trading.py
```

### **Daily Usage (After Setup)**
```bash
# Just run this - session is saved!
python paper_trading.py
```

### **If Session Expires (6:00 AM daily)**
```bash
# Re-authenticate (credentials remembered)
python authenticate_zerodha.py

# Then start trading
python paper_trading.py
```

---

## 📱 **Getting API Credentials**

### **1. Visit Kite Connect**
- Go to: https://kite.trade/
- Login with your Zerodha account

### **2. Create App**
- Click "My Apps" section
- Create new app or use existing
- Fill required details:
  - App name: "Paper Trading Bot"
  - App type: "Connect"
  - Redirect URL: `http://localhost:8080`

### **3. Get Credentials**
- Copy **API Key** 
- Copy **API Secret**
- Keep them safe!

---

## 💾 **Session Files Created**

### **`zerodha_config.json`** (Your Credentials)
```json
{
  "api_key": "your_api_key_here",
  "api_secret": "your_api_secret_here", 
  "created_at": "2025-09-16T15:30:00"
}
```

### **`zerodha_session.json`** (Active Session)
```json
{
  "access_token": "session_token_here",
  "user_name": "Your Name",
  "expires_at": "2025-09-17T06:00:00",
  "session_version": "1.0"
}
```

---

## 🕰️ **Session Timing**

### **Session Duration**
- **Created**: When you authenticate
- **Expires**: 6:00 AM next day (Zerodha policy)
- **Reuse**: Automatic until expiry

### **What Happens When Session Expires**
1. Paper trading bot shows: "No valid session found"
2. You run: `python authenticate_zerodha.py`
3. Quick browser login (credentials remembered)
4. Session saved for another day

---

## ✅ **Benefits**

### **Before (Old System)**
```
Daily Routine:
1. Run paper_trading.py
2. Enter API key
3. Enter API secret
4. Open browser
5. Login to Zerodha
6. Complete 2FA
7. Authorize app
8. Copy/paste URL
9. Finally start trading
```

### **After (New System)**
```
Daily Routine:
1. Run paper_trading.py
2. Done! (Uses saved session)

If session expired:
1. Run authenticate_zerodha.py
2. Quick browser login
3. Run paper_trading.py
4. Done!
```

---

## 🔧 **Troubleshooting**

### **"No valid session found"**
```bash
python authenticate_zerodha.py
```

### **"Authentication failed"**
- Check internet connection
- Verify API key/secret are correct
- Make sure you completed browser login properly

### **"Session expired"**
- Normal behavior (expires 6:00 AM daily)
- Just re-authenticate: `python authenticate_zerodha.py`

### **Reset Everything**
```bash
# Delete all saved data
rm zerodha_config.json zerodha_session.json

# Start fresh
python authenticate_zerodha.py
```

---

## 🎯 **Summary**

| **File** | **Purpose** | **When to Run** |
|----------|-------------|-----------------|
| `authenticate_zerodha.py` | Login & save session | Once per day (if session expired) |
| `paper_trading.py` | Main trading bot | Daily for trading |
| `zerodha_auth.py` | Core auth engine | Never (runs automatically) |

**Your authentication is now streamlined and persistent!** 🚀

No more daily credential entry - just authenticate once and trade all day!