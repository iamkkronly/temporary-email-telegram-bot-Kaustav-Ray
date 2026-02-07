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
import os
import sys
import logging
import requests
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Dict, List, Optional

from telegram import Update
from telegram.constants import ParseMode
from telegram.helpers import escape_markdown
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

# =========================
# LOGGING SETUP
# =========================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# =========================
# CONFIGURATION
# =========================

# HARDCODED BOT TOKEN
BOT_TOKEN = "PASTE_YOUR_TELEGRAM_BOT_TOKEN"

MAILTM_BASE = "https://api.mail.tm"
PING_PORT = int(os.getenv("PING_PORT", 8080))

OTP_REGEX = re.compile(r"\b\d{4,8}\b")

# In-memory active sessions (intentionally volatile)
ACTIVE_SESSIONS: Dict[int, Dict] = {}

# =========================
# MAIL.TM API HELPERS
# =========================


def get_domains() -> List[str]:
    try:
        response = requests.get(f"{MAILTM_BASE}/domains", timeout=10)
        response.raise_for_status()
        return [d["domain"] for d in response.json().get("hydra:member", [])]
    except requests.RequestException as e:
        logger.error(f"Error fetching domains: {e}")
        raise


def create_account(address: str, password: str) -> None:
    try:
        response = requests.post(
            f"{MAILTM_BASE}/accounts",
            json={"address": address, "password": password},
            timeout=10,
        )
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Error creating account: {e}")
        raise


def get_token(address: str, password: str) -> str:
    try:
        response = requests.post(
            f"{MAILTM_BASE}/token",
            json={"address": address, "password": password},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()["token"]
    except requests.RequestException as e:
        logger.error(f"Error getting token: {e}")
        raise


def fetch_messages(token: str) -> List[Dict]:
    try:
        response = requests.get(
            f"{MAILTM_BASE}/messages",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        response.raise_for_status()
        return response.json().get("hydra:member", [])
    except requests.RequestException as e:
        logger.error(f"Error fetching messages: {e}")
        return []


def read_message(token: str, message_id: str) -> Dict:
    try:
        response = requests.get(
            f"{MAILTM_BASE}/messages/{message_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Error reading message: {e}")
        return {}


def delete_message(token: str, message_id: str) -> None:
    try:
        response = requests.delete(
            f"{MAILTM_BASE}/messages/{message_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Error deleting message: {e}")

# =========================
# UTILITIES
# =========================


def random_string(length: int) -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


def detect_otp(text: str) -> Optional[str]:
    if not text:
        return None
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
        "📧 *Temporary Email Bot*\n\n"
        "/new – Create temp email\n"
        "/read – Read inbox\n"
        "/repair <token> – Recover inbox\n\n"
        "⚠️ Save your recovery token carefully.",
        parse_mode=ParseMode.MARKDOWN
    )


async def new_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    await update.message.reply_text("⏳ Creating temporary email...")

    try:
        domains = get_domains()
        if not domains:
            await update.message.reply_text("❌ No domains available. Try again later.")
            return

        domain = random.choice(domains)
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

        # Note: We do NOT escape email/token because they are inside backticks (code blocks)
        # Markdown V1 code blocks treat contents literally (except backticks).

        await update.message.reply_text(
            f"✅ *Temp Email Created*\n\n"
            f"📮 `{email}`\n\n"
            f"🔑 *Permanent Recovery Token*\n"
            f"`{recovery_token}`\n\n"
            f"Use `/repair <token>` if bot restarts.",
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception as e:
        logger.error(f"Error in new_email: {e}")
        await update.message.reply_text("❌ An error occurred while creating email.")


async def repair(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text("Usage: /repair <recovery_token>")
        return

    try:
        data = decode_recovery_token(context.args[0])
        # Validate data structure
        if not all(k in data for k in ("email", "password", "token")):
            raise ValueError("Invalid token structure")

        ACTIVE_SESSIONS[user_id] = data

        await update.message.reply_text(
            f"♻️ *Inbox recovered successfully*\n\n📮 `{data['email']}`",
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception:
        await update.message.reply_text("❌ Invalid recovery token.")
        return


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

    # Process messages (limit to 5 to avoid timeouts/limits)
    for msg in messages[:5]:
        full = read_message(session["token"], msg["id"])
        if not full:
            continue

        body = full.get("text", "") or "No text content"

        otp = detect_otp(body)
        otp_line = f"\n🔐 *OTP*: `{otp}`" if otp else ""

        # Truncate body to avoid hitting Telegram's 4096 char limit
        # Reduced to 2000 to allow room for Markdown escaping expansion
        if len(body) > 2000:
            body = body[:2000] + "... (truncated)"

        from_addr = escape_markdown(full.get('from', {}).get('address', 'Unknown'), version=1)
        subject = escape_markdown(full.get('subject', 'No Subject'), version=1)
        body_escaped = escape_markdown(body, version=1)

        output = (
            f"📨 *From*: {from_addr}\n"
            f"📝 *Subject*: {subject}\n"
            f"📜 *Message*:\n{body_escaped}{otp_line}\n\n"
        )

        try:
            await update.message.reply_text(output, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            await update.message.reply_text(f"📨 From: {full.get('from', {}).get('address')}\n(Content could not be displayed)")

        delete_message(session["token"], msg["id"])

# =========================
# UPTIMEROBOT PING SERVER
# =========================


class PingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive")

    def log_message(self, format, *args):
        return  # Suppress logging

def start_ping_server():
    try:
        server = HTTPServer(("0.0.0.0", PING_PORT), PingHandler)
        logger.info(f"Ping server started on port {PING_PORT}")
        server.serve_forever()
    except Exception as e:
        logger.error(f"Failed to start ping server: {e}")

# =========================
# MAIN ENTRYPOINT
# =========================


def main():
    if not BOT_TOKEN or BOT_TOKEN == "PASTE_YOUR_TELEGRAM_BOT_TOKEN":
        logger.critical("BOT_TOKEN is not set. Please edit bot.py and set the BOT_TOKEN variable.")
        sys.exit(1)

    threading.Thread(target=start_ping_server, daemon=True).start()

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("new", new_email))
    app.add_handler(CommandHandler("read", read))
    app.add_handler(CommandHandler("repair", repair))

    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
