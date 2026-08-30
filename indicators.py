"""
Calcolo degli indicatori tecnici e valutazione dei segnali su una serie storica di prezzi.
"""
import pandas as pd
import ta
from config import THRESHOLDS


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    df deve avere almeno una colonna 'close' (e idealmente 'volume').
    Ritorna il df arricchito con le colonne degli indicatori.
    """
    df = df.copy()

    df["rsi"] = ta.momentum.RSIIndicator(
        close=df["close"], window=THRESHOLDS["rsi_period"]
    ).rsi()

    df["sma_short"] = df["close"].rolling(THRESHOLDS["sma_short"]).mean()
    df["sma_long"] = df["close"].rolling(THRESHOLDS["sma_long"]).mean()

    macd = ta.trend.MACD(
        close=df["close"],
        window_fast=THRESHOLDS["macd_fast"],
        window_slow=THRESHOLDS["macd_slow"],
        window_sign=THRESHOLDS["macd_signal"],
    )
    df["macd"] = macd.macd()
    df["macd_signal"] = macd.macd_signal()

    bb = ta.volatility.BollingerBands(
        close=df["close"],
        window=THRESHOLDS["bb_period"],
        window_dev=THRESHOLDS["bb_std"],
    )
    df["bb_high"] = bb.bollinger_hband()
    df["bb_low"] = bb.bollinger_lband()

    if "volume" in df.columns:
        df["volume_avg"] = df["volume"].rolling(20).mean()

    return df


def evaluate_signals(df: pd.DataFrame, asset_name: str) -> list[dict]:
    """
    Guarda le ultime due righe del df (oggi vs ieri) e ritorna una lista
    di segnali attivi, ognuno con un 'id' univoco (usato per il cooldown)
    e un messaggio leggibile in italiano.
    """
    if len(df) < 2:
        return []

    today = df.iloc[-1]
    yesterday = df.iloc[-2]
    signals = []

    # --- Variazione percentuale ---
    pct_change = (today["close"] - yesterday["close"]) / yesterday["close"] * 100
    if abs(pct_change) >= THRESHOLDS["pct_change_alert"]:
        direction = "rialzo" if pct_change > 0 else "ribasso"
        emoji = "🟢📈" if pct_change > 0 else "🔴📉"
        signals.append({
            "id": f"{asset_name}_pct_change",
            "message": f"{emoji} *{asset_name}*: {direction} del {pct_change:+.2f}% nelle ultime 24h "
                       f"(prezzo attuale: {today['close']:.4f})",
        })

    # --- RSI ipercomprato/ipervenduto ---
    if pd.notna(today["rsi"]):
        if today["rsi"] >= THRESHOLDS["rsi_overbought"]:
            signals.append({
                "id": f"{asset_name}_rsi_overbought",
                "message": f"⚠️ *{asset_name}*: RSI a {today['rsi']:.1f} — zona ipercomprato "
                           f"(possibile correzione al ribasso in arrivo)",
            })
        elif today["rsi"] <= THRESHOLDS["rsi_oversold"]:
            signals.append({
                "id": f"{asset_name}_rsi_oversold",
                "message": f"⚠️ *{asset_name}*: RSI a {today['rsi']:.1f} — zona ipervenduto "
                           f"(possibile rimbalzo al rialzo in arrivo)",
            })

    # --- Golden cross / Death cross (SMA50 vs SMA200) ---
    if pd.notna(today["sma_short"]) and pd.notna(today["sma_long"]) and \
       pd.notna(yesterday["sma_short"]) and pd.notna(yesterday["sma_long"]):
        crossed_up = yesterday["sma_short"] <= yesterday["sma_long"] and today["sma_short"] > today["sma_long"]
        crossed_down = yesterday["sma_short"] >= yesterday["sma_long"] and today["sma_short"] < today["sma_long"]
        if crossed_up:
            signals.append({
                "id": f"{asset_name}_golden_cross",
                "message": f"✨ *{asset_name}*: GOLDEN CROSS — la media a {THRESHOLDS['sma_short']} giorni "
                           f"ha superato quella a {THRESHOLDS['sma_long']} giorni (segnale tecnico rialzista di medio termine)",
            })
        if crossed_down:
            signals.append({
                "id": f"{asset_name}_death_cross",
                "message": f"💀 *{asset_name}*: DEATH CROSS — la media a {THRESHOLDS['sma_short']} giorni "
                           f"è scesa sotto quella a {THRESHOLDS['sma_long']} giorni (segnale tecnico ribassista di medio termine)",
            })

    # --- MACD crossover ---
    if pd.notna(today["macd"]) and pd.notna(today["macd_signal"]) and \
       pd.notna(yesterday["macd"]) and pd.notna(yesterday["macd_signal"]):
        macd_cross_up = yesterday["macd"] <= yesterday["macd_signal"] and today["macd"] > today["macd_signal"]
        macd_cross_down = yesterday["macd"] >= yesterday["macd_signal"] and today["macd"] < today["macd_signal"]
        if macd_cross_up:
            signals.append({
                "id": f"{asset_name}_macd_bullish",
                "message": f"📊 *{asset_name}*: MACD ha incrociato al rialzo la signal line "
                           f"(momentum a favore dei rialzisti)",
            })
        if macd_cross_down:
            signals.append({
                "id": f"{asset_name}_macd_bearish",
                "message": f"📊 *{asset_name}*: MACD ha incrociato al ribasso la signal line "
                           f"(momentum a favore dei ribassisti)",
            })

    # --- Bollinger Bands breakout ---
    if pd.notna(today["bb_high"]) and pd.notna(today["bb_low"]):
        if today["close"] > today["bb_high"]:
            signals.append({
                "id": f"{asset_name}_bb_breakout_up",
                "message": f"📈 *{asset_name}*: prezzo sopra la banda di Bollinger superiore "
                           f"(forte momentum rialzista o possibile ipercomprato)",
            })
        elif today["close"] < today["bb_low"]:
            signals.append({
                "id": f"{asset_name}_bb_breakout_down",
                "message": f"📉 *{asset_name}*: prezzo sotto la banda di Bollinger inferiore "
                           f"(forte momentum ribassista o possibile ipervenduto)",
            })

    # --- Spike di volume ---
    if "volume" in df.columns and pd.notna(today.get("volume_avg")):
        if today["volume_avg"] > 0 and today["volume"] >= today["volume_avg"] * THRESHOLDS["volume_spike_multiplier"]:
            signals.append({
                "id": f"{asset_name}_volume_spike",
                "message": f"🔊 *{asset_name}*: volume anomalo, {today['volume'] / today['volume_avg']:.1f}x "
                           f"la media — possibile mossa importante in corso",
            })

    return signals
