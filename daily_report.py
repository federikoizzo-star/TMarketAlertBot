"""
Report giornaliero: movimenti anomali di oggi, miglior asset del momento, e un
esperimento "in avanti" (paper trading reale, non backtest sul passato) che
segue i segnali del bot per 7 giorni a partire da quando parte per la prima
volta, confrontandolo con Bitcoin buy&hold nello stesso periodo. Dopo 7 giorni
il ciclo si chiude e ne parte uno nuovo automaticamente.

Lo stato dell'esperimento (giorno in corso, valore del portafoglio virtuale,
storico operazioni) viene salvato in paper_state.json e committato nel repo
a ogni esecuzione (vedi daily_report.yml).
"""
import os
import sys
import time
import json
from datetime import date

from config import CRYPTO_WATCHLIST, STOCKS_WATCHLIST, ETF_WATCHLIST, BONDS_WATCHLIST
from data_sources import fetch_crypto_history, fetch_yfinance_history, safe_fetch
from indicators import compute_indicators, evaluate_signals
from notifier import send_telegram_message

COINGECKO_DELAY_SECONDS = 2.0
EXPERIMENT_DAYS = 7
STARTING_CAPITAL = 100.0
MIN_BULLISH_SCORE = 2

TRADING_FEE_PCT = 0.001
CAPITAL_GAINS_TAX_PCT = 0.26

PAPER_STATE_FILE = "paper_state.json"


def pick_of_the_day(all_signals_today: list[dict]):
    scores = {}
    for s in all_signals_today:
        asset = s.get("asset")
        direction = s.get("direction")
        if not asset or direction not in ("bullish", "bearish"):
            continue
        scores.setdefault(asset, {"bullish": 0, "bearish": 0})
        scores[asset][direction] += 1
    candidates = {a: v["bullish"] for a, v in scores.items() if v["bearish"] == 0 and v["bullish"] > 0}
    if not candidates:
        return None, 0
    best = max(candidates, key=candidates.get)
    if candidates[best] < MIN_BULLISH_SCORE:
        return None, 0
    return best, candidates[best]


def load_paper_state():
    if os.path.exists(PAPER_STATE_FILE):
        with open(PAPER_STATE_FILE) as f:
            return json.load(f)
    return None


def save_paper_state(state):
    with open(PAPER_STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def apply_capital_gains_tax(final_value, starting_capital):
    gain = final_value - starting_capital
    if gain > 0:
        tax = gain * CAPITAL_GAINS_TAX_PCT
        return final_value - tax, tax
    return final_value, 0.0


def main():
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not bot_token or not chat_id:
        print("[ERRORE] Mancano TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID")
        sys.exit(1)

    # --- Scarico lo storico di tutti gli asset ---
    histories = {}

    print(f"Scarico storico per {len(CRYPTO_WATCHLIST)} crypto...")
    for i, coin_id in enumerate(CRYPTO_WATCHLIST):
        df = safe_fetch(fetch_crypto_history, coin_id)
        if df is not None:
            histories[coin_id.upper()] = df
        if i < len(CRYPTO_WATCHLIST) - 1:
            time.sleep(COINGECKO_DELAY_SECONDS)

    print(f"Scarico storico per {len(STOCKS_WATCHLIST)} azioni...")
    for ticker in STOCKS_WATCHLIST:
        df = safe_fetch(fetch_yfinance_history, ticker)
        if df is not None:
            histories[ticker] = df

    print(f"Scarico storico per {len(ETF_WATCHLIST)} ETF...")
    for ticker in ETF_WATCHLIST:
        df = safe_fetch(fetch_yfinance_history, ticker)
        if df is not None:
            histories[ticker] = df

    print(f"Scarico storico per {len(BONDS_WATCHLIST)} ETF obbligazionari...")
    for ticker in BONDS_WATCHLIST:
        df = safe_fetch(fetch_yfinance_history, ticker)
        if df is not None:
            histories[f"{ticker} (bond)"] = df

    if "BITCOIN" not in histories:
        print("[ERRORE] Impossibile scaricare Bitcoin, serve come benchmark.")
        sys.exit(1)

    today_str = date.today().isoformat()
    btc_today_price = float(histories["BITCOIN"]["close"].iloc[-1])

    # ============================================================
    # SEZIONE 1 — Movimenti anomali di OGGI
    # ============================================================
    print("\nCalcolo segnali di oggi...")
    today_signals = []
    for name, df in histories.items():
        if len(df) < 30:
            continue
        df_ind = compute_indicators(df)
        today_signals.extend(evaluate_signals(df_ind, name))

    # ============================================================
    # SEZIONE 2 — Miglior asset del momento
    # ============================================================
    best_pick, best_score = pick_of_the_day(today_signals)

    # ============================================================
    # SEZIONE 3 e 4 — Esperimento in avanti: carico/aggiorno lo stato
    # ============================================================
    state = load_paper_state()
    if state is None or state.get("day_number", 0) >= EXPERIMENT_DAYS:
        # Nuovo ciclo: si riparte da zero
        state = {
            "start_date": today_str,
            "day_number": 0,
            "portfolio_value": STARTING_CAPITAL,
            "btc_start_price": btc_today_price,
            "trade_log": [],
        }

    already_logged_today = any(entry.startswith(today_str) for entry in state["trade_log"])
    if not already_logged_today:
        if best_pick and best_pick in histories and len(histories[best_pick]) >= 2:
            prev_price = float(histories[best_pick]["close"].iloc[-2])
            today_price = float(histories[best_pick]["close"].iloc[-1])
            if prev_price > 0:
                day_return = (today_price / prev_price) - 1
                state["portfolio_value"] *= (1 - TRADING_FEE_PCT)
                state["portfolio_value"] *= (1 + day_return)
                state["portfolio_value"] *= (1 - TRADING_FEE_PCT)
                state["trade_log"].append(
                    f"{today_str}: {best_pick} ({day_return*100:+.2f}%) → €{state['portfolio_value']:.2f}"
                )
        else:
            state["trade_log"].append(f"{today_str}: nessuna operazione (nessun segnale valido)")
        state["day_number"] += 1

    save_paper_state(state)

    # --- Valori correnti (come se chiudessi oggi) ---
    bot_net_value, bot_tax = apply_capital_gains_tax(state["portfolio_value"], STARTING_CAPITAL)
    bot_gain = bot_net_value - STARTING_CAPITAL

    btc_gross_return = (btc_today_price / state["btc_start_price"]) - 1
    btc_value = STARTING_CAPITAL * (1 - TRADING_FEE_PCT) * (1 + btc_gross_return) * (1 - TRADING_FEE_PCT)
    btc_net_value, btc_tax = apply_capital_gains_tax(btc_value, STARTING_CAPITAL)
    btc_gain = btc_net_value - STARTING_CAPITAL

    day_number = state["day_number"]
    is_final_day = day_number >= EXPERIMENT_DAYS

    # ============================================================
    # Composizione del messaggio
    # ============================================================
    parts = []

    parts.append("📡 *Report giornaliero mercati*\n_Segnali tecnici automatici, non è consulenza finanziaria._")

    parts.append("━━━━━━━━━━━━━━\n🔎 *Movimenti anomali di oggi*")
    if today_signals:
        parts.append("\n\n".join(s["message"] for s in today_signals))
    else:
        parts.append("_Nessun movimento anomalo rilevato oggi._")

    parts.append("━━━━━━━━━━━━━━\n🎯 *Su cosa investire ora*")
    if best_pick:
        parts.append(
            f"*{best_pick}* — {best_score} segnali tecnici rialzisti concordanti, "
            f"nessun segnale contrario rilevato.\n"
            f"_Segnale statistico, non una garanzia — decidi sempre tu quanto e come investire._"
        )
    else:
        parts.append("_Nessun asset con segnale abbastanza forte in questo momento._")

    header_giorno = "🏁 *Settimana conclusa!*" if is_final_day else f"📊 *Esperimento in corso — Giorno {day_number}/{EXPERIMENT_DAYS}*"
    parts.append(
        f"━━━━━━━━━━━━━━\n{header_giorno}\n"
        f"€{STARTING_CAPITAL:.2f} → *€{bot_net_value:.2f}* netti se chiudessi oggi "
        f"({bot_gain:+.2f}€, {bot_gain/STARTING_CAPITAL*100:+.2f}%)\n"
        f"(commissioni {TRADING_FEE_PCT*100:.1f}%/operazione, tasse {CAPITAL_GAINS_TAX_PCT*100:.0f}% sulla plusvalenza se in guadagno)\n\n"
        f"📋 _Cosa ha comprato, giorno per giorno:_\n" + "\n".join(state["trade_log"])
    )

    parts.append(
        f"━━━━━━━━━━━━━━\n₿ *Bitcoin buy&hold, stesso periodo (dal {state['start_date']})*\n"
        f"€{STARTING_CAPITAL:.2f} → *€{btc_net_value:.2f}* netti se vendessi oggi "
        f"({btc_gain:+.2f}€, {btc_gain/STARTING_CAPITAL*100:+.2f}%)"
    )

    if is_final_day:
        parts.append("_Ciclo di 7 giorni completato — da domani ne parte uno nuovo da zero._")
    else:
        parts.append(
            f"_Valori \"se chiudessi oggi\": la posizione non è realmente chiusa, è solo una stima corrente. "
            f"{EXPERIMENT_DAYS - day_number} giorni rimanenti in questo ciclo._"
        )

    message = "\n\n".join(parts)
    print("\n\n" + message)
    send_telegram_message(bot_token, chat_id, message)


if __name__ == "__main__":
    main()
    
