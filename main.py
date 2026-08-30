"""
Script principale del bot di monitoraggio mercati.
Va eseguito periodicamente (es. via GitHub Actions cron) — vedi README.md.
"""
import os
import sys
import time

from config import CRYPTO_WATCHLIST, STOCKS_WATCHLIST, ETF_WATCHLIST, BONDS_WATCHLIST
from data_sources import fetch_crypto_history, fetch_yfinance_history, safe_fetch
from indicators import compute_indicators, evaluate_signals
from notifier import load_state, save_state, is_in_cooldown, mark_sent, send_telegram_message

# Pausa tra una chiamata CoinGecko e l'altra (piano gratuito ha rate limit basso,
# senza questa pausa la maggior parte delle richieste va in errore 429)
COINGECKO_DELAY_SECONDS = 2.0


def analyze_asset(name: str, df) -> list[dict]:
    if df is None or len(df) < 30:
        return []
    df = compute_indicators(df)
    return evaluate_signals(df, name)


def main():
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not bot_token or not chat_id:
        print("[ERRORE] Devi impostare le variabili d'ambiente TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID")
        sys.exit(1)

    state = load_state()
    all_signals = []

    print(f"Analizzo {len(CRYPTO_WATCHLIST)} crypto...")
    for i, coin_id in enumerate(CRYPTO_WATCHLIST):
        df = safe_fetch(fetch_crypto_history, coin_id)
        all_signals.extend(analyze_asset(coin_id.upper(), df))
        if i < len(CRYPTO_WATCHLIST) - 1:
            time.sleep(COINGECKO_DELAY_SECONDS)

    print(f"Analizzo {len(STOCKS_WATCHLIST)} azioni...")
    for ticker in STOCKS_WATCHLIST:
        df = safe_fetch(fetch_yfinance_history, ticker)
        all_signals.extend(analyze_asset(ticker, df))

    print(f"Analizzo {len(ETF_WATCHLIST)} ETF...")
    for ticker in ETF_WATCHLIST:
        df = safe_fetch(fetch_yfinance_history, ticker)
        all_signals.extend(analyze_asset(ticker, df))

    print(f"Analizzo {len(BONDS_WATCHLIST)} ETF obbligazionari...")
    for ticker in BONDS_WATCHLIST:
        df = safe_fetch(fetch_yfinance_history, ticker)
        all_signals.extend(analyze_asset(f"{ticker} (bond)", df))

    # Filtra i segnali già inviati di recente (cooldown)
    new_signals = [s for s in all_signals if not is_in_cooldown(state, s["id"])]

    if not new_signals:
        print("Nessun nuovo segnale da inviare.")
        save_state(state)
        return

    print(f"Invio {len(new_signals)} nuovi segnali...")
    header = "📡 *Report mercati*\n_Questo bot segnala movimenti e indicatori tecnici, non è consulenza finanziaria._\n\n"
    body = "\n\n".join(s["message"] for s in new_signals)
    send_telegram_message(bot_token, chat_id, header + body)

    for s in new_signals:
        mark_sent(state, s["id"])
    save_state(state)


if __name__ == "__main__":
    main()
