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


def build_best_pick_footer(all_signals: list[dict]) -> str:
    """
    Guarda TUTTI i segnali di questo scan (non solo quelli nuovi/non in cooldown)
    e, se un asset ha solo segnali rialzisti concordanti e nessun segnale ribassista
    in conflitto, lo segnala come "miglior asset del momento".
    Se non c'è un vincitore chiaro, ritorna stringa vuota (nessuna aggiunta al messaggio).
    """
    scores = {}
    for s in all_signals:
        asset = s.get("asset")
        direction = s.get("direction")
        if not asset or direction not in ("bullish", "bearish"):
            continue
        if asset not in scores:
            scores[asset] = {"bullish": 0, "bearish": 0}
        scores[asset][direction] += 1

    # Solo asset senza segnali ribassisti in conflitto, con almeno 1 segnale rialzista
    candidates = {
        asset: v["bullish"] for asset, v in scores.items()
        if v["bearish"] == 0 and v["bullish"] > 0
    }

    if not candidates:
        return ""

    best_asset = max(candidates, key=candidates.get)
    best_score = candidates[best_asset]

    # Richiedo almeno 2 segnali tecnici concordanti per essere abbastanza sicuri
    # da segnalarlo esplicitamente (1 solo segnale è troppo debole/rumoroso)
    if best_score < 2:
        return ""

    return (
        f"\n\n🎯 *Questa al momento è il miglior asset dove mettere i tuoi soldi:* "
        f"*{best_asset}*\n"
        f"({best_score} segnali tecnici rialzisti concordanti, nessun segnale contrario rilevato)\n"
        f"_Resta un segnale statistico basato su indicatori tecnici, non una garanzia — "
        f"decidi sempre tu quanto e come investire._"
    )


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

    footer = build_best_pick_footer(all_signals)

    send_telegram_message(bot_token, chat_id, header + body + footer)

    for s in new_signals:
        mark_sent(state, s["id"])
    save_state(state)


if __name__ == "__main__":
    main()
    
