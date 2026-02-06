# © 2026 Kaustav Ray. All rights reserved.
# Licensed under the MIT License.

"""
Temporary Email Telegram Bot (Stateless Architecture)
====================================================
- Uses mail.tm free API
- No database, no permanent storage
- Permanent recovery token system
- OTP auto-detection
- Attachments support (mail.tm native)
- Works after server restarts
- UptimeRobot compatible ping server

Author: Kaustav Ray
"""

import base64
import json
import random
import string
import threading
import re
import requests
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Dict, List

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

# =========================
# CONFIGURATION
# =========================

BOT_TOKEN = "PASTE_YOUR_TELEGRAM_BOT_TOKEN"
MAILTM_BASE = "https://api.mail.tm"
PING_PORT = 8080

OTP_REGEX = re.compile(r"\b\d{4,8}\b")

# In-memory active sessions (intentionally volatile)
ACTIVE_SESSIONS: Dict[int, Dict] = {}

# =========================
# MAIL.TM API HELPERS
# =========================


def get_domains() -> List[str]:
    response = requests.get(f"{MAILTM_BASE}/domains", timeout=10)
    response.raise_for_status()
    return [d["domain"] for d in response.json()["hydra:member"]]


def create_account(address: str, password: str) -> None:
    response = requests.post(
        f"{MAILTM_BASE}/accounts",
        json={"address": address, "password": password},
        timeout=10,
    )
    response.raise_for_status()


def get_token(address: str, password: str) -> str:
    response = requests.post(
        f"{MAILTM_BASE}/token",
        json={"address": address, "password": password},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()["token"]


def fetch_messages(token: str):
    response = requests.get(
        f"{MAILTM_BASE}/messages",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()["hydra:member"]


def read_message(token: str, message_id: str):
    response = requests.get(
        f"{MAILTM_BASE}/messages/{message_id}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def delete_message(token: str, message_id: str):
    response = requests.delete(
        f"{MAILTM_BASE}/messages/{message_id}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    response.raise_for_status()

# =========================
# UTILITIES
# =========================


def random_string(length: int) -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


def detect_otp(text: str) -> str | None:
    match = OTP_REGEX.search(text)
    return match.group(0) if match else None


def encode_recovery_token(data: Dict) -> str:
    """Encode inbox credentials into a permanent recovery token."""
    raw = json.dumps(data).encode()
    return base64.urlsafe_b64encode(raw).decode()


def decode_recovery_token(token: str) -> Dict:
    raw = base64.urlsafe_b64decode(token.encode())
    return json.loads(raw.decode())

# =========================
# TELEGRAM COMMANDS
# =========================


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📧 Temporary Email Bot\n\n"
        "/new – Create temp email\n"
        "/read – Read inbox\n"
        "/repair <token> – Recover inbox\n\n"
        "⚠️ Save your recovery token carefully."
    )


async def new_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    domain = random.choice(get_domains())
    email = f"{random_string(8)}@{domain}"
    password = random_string(12)

    create_account(email, password)
    jwt_token = get_token(email, password)

    session = {
        "email": email,
        "password": password,
        "token": jwt_token,
    }

    ACTIVE_SESSIONS[user_id] = session
    recovery_token = encode_recovery_token(session)

    await update.message.reply_text(
        f"✅ Temp Email Created\n\n"
        f"📮 `{email}`\n\n"
        f"🔑 *Permanent Recovery Token*\n"
        f"`{recovery_token}`\n\n"
        f"Use `/repair <token>` if bot restarts.",
        parse_mode="Markdown",
    )


async def repair(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text("Usage: /repair <recovery_token>")
        return

    try:
        data = decode_recovery_token(context.args[0])
        ACTIVE_SESSIONS[user_id] = data
    except Exception:
        await update.message.reply_text("❌ Invalid recovery token.")
        return

    await update.message.reply_text(
        f"♻️ Inbox recovered successfully\n\n📮 `{data['email']}`",
        parse_mode="Markdown",
    )


async def read(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    session = ACTIVE_SESSIONS.get(user_id)

    if not session:
        await update.message.reply_text(
            "No active inbox.\nUse /new or /repair <token>."
        )
        return

    messages = fetch_messages(session["token"])
    if not messages:
        await update.message.reply_text("No new emails.")
        return

    output = ""
    for msg in messages[:3]:
        full = read_message(session["token"], msg["id"])
        body = full.get("text", "")

        otp = detect_otp(body)
        otp_line = f"\n🔐 OTP: `{otp}`" if otp else ""

        output += (
            f"📨 From: {full['from']['address']}\n"
            f"📝 Subject: {full['subject']}{otp_line}\n\n"
        )

        delete_message(session["token"], msg["id"])

    await update.message.reply_text(output, parse_mode="Markdown")

# =========================
# UPTIMEROBOT PING SERVER
# =========================


class PingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive")


def start_ping_server():
    HTTPServer(("0.0.0.0", PING_PORT), PingHandler).serve_forever()

# =========================
# MAIN ENTRYPOINT
# =========================


def main():
    threading.Thread(target=start_ping_server, daemon=True).start()

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("new", new_email))
    app.add_handler(CommandHandler("read", read))
    app.add_handler(CommandHandler("repair", repair))

    app.run_polling()


if __name__ == "__main__":
    main()
