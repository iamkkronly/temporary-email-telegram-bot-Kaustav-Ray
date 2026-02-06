# Temporary Email Telegram Bot (mail.tm)

A stateless, privacy-first Telegram bot that provides temporary email addresses using the free [mail.tm](https://mail.tm) API.

## ✨ Features

- **One-tap creation**: Generate temporary emails instantly.
- **Privacy-first**: No database, no logs, no tracking. Stateless architecture.
- **Permanent Recovery**: Restore your session even after bot restarts using a recovery token.
- **OTP Auto-detection**: Automatically highlights 4–8 digit codes in emails.
- **Inbox Management**: Read and auto-delete emails.
- **UptimeRobot Support**: Built-in ping server to keep the bot alive on free hosting.

## 🔐 Recovery Token System

Since the bot is stateless (no database), it doesn't remember your email after a restart. Instead, it generates a **Permanent Recovery Token** when you create an email. This token contains your credentials (encrypted via Base64).

- **Save your token!** It is shown only once.
- **Recover session**: Use `/repair <token>` to restore your inbox.

## 🚀 Setup

### Prerequisites

- Python 3.8+
- A Telegram Bot Token (from [@BotFather](https://t.me/BotFather))

### Installation

1.  **Clone the repository**
    ```bash
    git clone https://github.com/yourusername/temporary-email-bot.git
    cd temporary-email-bot
    ```

2.  **Install dependencies**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configuration**
    You can configure the bot using environment variables or by editing `bot.py` (not recommended for production).

    **Environment Variables:**
    - `BOT_TOKEN`: Your Telegram Bot Token.
    - `PING_PORT`: Port for the keep-alive server (default: 8080).

    Example:
    ```bash
    export BOT_TOKEN="123456789:ABCdefGHIjklMNOpqrsTUVwxyZ"
    ```

4.  **Run the bot**
    ```bash
    python bot.py
    ```

## 📜 Commands

| Command | Description |
| :--- | :--- |
| `/start` | Show help and introduction |
| `/new` | Create a new temporary email address |
| `/read` | Fetch and read the latest emails (auto-deletes after reading) |
| `/repair <token>` | Recover your inbox using a recovery token |

## 🛡 Privacy Model

- **No Database**: The bot does not store any user data or email content.
- **Stateless**: Active sessions are held in memory and lost on restart (unless recovered).
- **Direct Communication**: Emails are fetched directly from mail.tm and sent to you.

## ⚠️ Security Notes

- The **Recovery Token** grants full access to the temporary email account. Treat it like a password.
- The token is Base64-encoded, not encrypted. Anyone with the token can access the inbox.
- Avoid using temporary emails for sensitive accounts.

## ☁️ Deployment (UptimeRobot)

To keep the bot running 24/7 on free hosting services:

1.  Deploy the bot.
2.  Set up an [UptimeRobot](https://uptimerobot.com/) monitor.
3.  **URL**: `http://YOUR_SERVER_IP:8080`
4.  **Method**: HTTP GET
5.  **Interval**: 5 minutes

## 📝 License

This project is licensed under the MIT License.
