"""
Invio messaggi Telegram e gestione dello stato per evitare notifiche duplicate
(cooldown per ogni id di segnale).
"""
import json
import os
import requests
from datetime import datetime, timedelta

from config import THRESHOLDS

STATE_FILE = "state.json"


def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {}


def save_state(state: dict):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def is_in_cooldown(state: dict, signal_id: str) -> bool:
    last_sent = state.get(signal_id)
    if not last_sent:
        return False
    last_sent_dt = datetime.fromisoformat(last_sent)
    cooldown = timedelta(hours=THRESHOLDS["cooldown_hours"])
    return datetime.utcnow() - last_sent_dt < cooldown


def mark_sent(state: dict, signal_id: str):
    state[signal_id] = datetime.utcnow().isoformat()


def send_telegram_message(bot_token: str, chat_id: str, text: str):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }
    resp = requests.post(url, data=payload, timeout=20)
    if not resp.ok:
        print(f"[ERRORE] Invio Telegram fallito: {resp.status_code} {resp.text}")
    return resp.ok
