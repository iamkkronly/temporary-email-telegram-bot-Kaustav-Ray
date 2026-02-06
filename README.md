# temporary-email-telegram-bot-Kaustav-Ray

# Temporary Email Telegram Bot (mail.tm)

A stateless, privacy-first Telegram bot that provides temporary email addresses
using the free mail.tm API.

## ✨ Features

- One-tap temporary email creation
- Real-time inbox fetching
- Read & auto-delete emails
- OTP auto-detection (4–8 digits)
- Attachments support (via mail.tm)
- Permanent recovery token system
- Works after server restarts
- No database, no logs, no tracking
- UptimeRobot ping server

## 🔐 Recovery Token System

When a temp email is created, the bot generates a **Permanent Recovery Token**
containing:
- Email address
- Password
- mail.tm JWT token

The token is:
- Shown only once
- Stored by the user
- Used with `/repair <token>` to restore inbox after restart

The server stores nothing permanently.

## 🚀 Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt

2. Configure bot token
Edit bot.py:
Python
Copy code
BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
3. Run the bot
Bash
Copy code
python bot.py
4. UptimeRobot
URL: http://YOUR_SERVER_IP:8080
Method: GET
Interval: 5 minutes
📜 Commands
Command
Description
/start
Show help
/new
Create temp email
/read
Read inbox
/repair <token>
Recover inbox
🛡 Privacy Model
No database
No email content stored
No user identifiers logged
Stateless server design
mail.tm handles mailbox lifecycle
⚠ Security Notes
Recovery token grants full access
Treat it like a password
Token is base64-encoded (not encrypted)
Can be upgraded to AES encryption if needed
