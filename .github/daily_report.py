"""
Report giornaliero unico: movimenti anomali di oggi, miglior asset del momento,
e backtest a 7 giorni (bot vs Bitcoin, al netto di commissioni e tasse).
Va eseguito una volta al giorno (vedi daily_report.yml).
"""
import os
import sys
import time

import pandas as pd

from config import CRYPTO_WATCHLIST, STOCKS_WATCHLIST, ETF_WATCHLIST, BONDS_WATCHLIST
from data_sources import fetch_crypto_history, fetch_yfinance_history, safe_fetch
from indicators import compute_indicators, evaluate_signals
from notifier import send_telegram_message

COINGECKO_DELAY_SECONDS = 2.0
BACKTEST_DAYS = 7
STARTING_CAPITAL = 100.0
MIN_BULLISH_SCORE = 2

TRADING_FEE_PCT = 0.001
CAPITAL_GAINS_TAX_PCT = 0.26


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
        return None
    best = max(candidates, key=candidates.get)
    if candidates[best] < MIN_BULLISH_SCORE:
        return None
    return best


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

    # --- Scarico lo storico di tutti gli asset (una volta, riusato sia per oggi che per il backtest) ---
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
    # SEZIONE 2 — Miglior asset del momento (stessa logica di oggi)
    # ============================================================
    best_pick = pick_of_the_day(today_signals)
    best_score = None
    if best_pick:
        scores = {}
        for s in today_signals:
            if s.get("asset") == best_pick and s.get("direction") == "bullish":
                scores[best_pick] = scores.get(best_pick, 0) + 1
        best_score = scores.get(best_pick, 0)

    # ============================================================
    # SEZIONE 3 e 4 — Backtest 7 giorni: bot vs Bitcoin
    # ============================================================
    print("\nBacktest ultimi 7 giorni...")
    btc_df = histories["BITCOIN"]
    all_days = pd.date_range(end=btc_df.index.max().normalize(), periods=BACKTEST_DAYS + 1, freq="D")

    aligned = {}
    for name, df in histories.items():
        s = df["close"].reindex(df.index.union(all_days)).sort_index().ffill()
        aligned[name] = s.reindex(all_days)

    portfolio_value = STARTING_CAPITAL
    trade_days = 0
    for d in range(1, len(all_days)):
        cutoff = all_days[d]
        day_signals = []
        for name, df in histories.items():
            df_slice = df[df.index <= cutoff]
            if len(df_slice) < 30:
                continue
            df_ind = compute_indicators(df_slice)
            day_signals.extend(evaluate_signals(df_ind, name))
        pick = pick_of_the_day(day_signals)
        if pick and pick in aligned:
            prev_price = aligned[pick].iloc[d - 1]
            today_price = aligned[pick].iloc[d]
            if pd.notna(prev_price) and pd.notna(today_price) and prev_price > 0:
                day_return = (today_price / prev_price) - 1
                trade_days += 1
                portfolio_value *= (1 - TRADING_FEE_PCT)
                portfolio_value *= (1 + day_return)
                portfolio_value *= (1 - TRADING_FEE_PCT)

    btc_start = aligned["BITCOIN"].iloc[0]
    btc_end = aligned["BITCOIN"].iloc[-1]
    btc_gross_return = (btc_end / btc_start) - 1
    btc_value = STARTING_CAPITAL * (1 - TRADING_FEE_PCT) * (1 + btc_gross_return) * (1 - TRADING_FEE_PCT)

    bot_net_value, bot_tax = apply_capital_gains_tax(portfolio_value, STARTING_CAPITAL)
    btc_net_value, btc_tax = apply_capital_gains_tax(btc_value, STARTING_CAPITAL)
    bot_gain = bot_net_value - STARTING_CAPITAL
    btc_gain = btc_net_value - STARTING_CAPITAL

    # ============================================================
    # Composizione del messaggio, nell'ordine richiesto
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

    parts.append(
        f"━━━━━━━━━━━━━━\n📊 *Simulazione: €{STARTING_CAPITAL:.0f} seguendo il bot (ultimi {BACKTEST_DAYS} giorni)*\n"
        f"{trade_days} operazioni · commissioni {TRADING_FEE_PCT*100:.1f}%/operazione · tasse {CAPITAL_GAINS_TAX_PCT*100:.0f}% sulla plusvalenza\n"
        f"€{STARTING_CAPITAL:.2f} → *€{bot_net_value:.2f}* netti ({bot_gain:+.2f}€, {bot_gain/STARTING_CAPITAL*100:+.2f}%)"
    )

    parts.append(
        f"━━━━━━━━━━━━━━\n₿ *Simulazione: €{STARTING_CAPITAL:.0f} su Bitcoin buy&hold (stesso periodo)*\n"
        f"€{STARTING_CAPITAL:.2f} → *€{btc_net_value:.2f}* netti ({btc_gain:+.2f}€, {btc_gain/STARTING_CAPITAL*100:+.2f}%)"
    )

    parts.append(
        "_7 giorni sono un campione piccolo, poco significativo statisticamente. "
        "Performance passata (anche simulata) non garantisce risultati futuri._"
    )

    message = "\n\n".join(parts)
    print("\n\n" + message)
    send_telegram_message(bot_token, chat_id, message)


if __name__ == "__main__":
    main()
    
