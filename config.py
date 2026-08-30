"""
Configurazione del bot: watchlist e soglie per i segnali.
Modifica liberamente queste liste per personalizzare cosa monitorare.
"""

# --- CRYPTO ---
# ID CoinGecko (non il ticker!). Lista completa: https://api.coingecko.com/api/v3/coins/list
CRYPTO_WATCHLIST = [
    "bitcoin",
    "ethereum",
    "solana",
    "ripple",
    "cardano",
]

# --- AZIONI ---
STOCKS_WATCHLIST = [
    "AAPL",   # Apple
    "MSFT",   # Microsoft
    "NVDA",   # Nvidia
    "GOOGL",  # Alphabet
    "TSLA",   # Tesla
]

# --- ETF ---
ETF_WATCHLIST = [
    "SPY",    # S&P 500
    "QQQ",    # Nasdaq 100
    "VWCE.DE",  # FTSE All-World (Vanguard, Xetra) - molto usato in Europa
]

# --- OBBLIGAZIONI (via ETF obbligazionari come proxy) ---
BONDS_WATCHLIST = [
    "TLT",    # Treasury USA lunga scadenza (20+ anni)
    "IEF",    # Treasury USA media scadenza (7-10 anni)
    "AGG",    # Aggregate Bond Market USA
    "LQD",    # Corporate Bond investment grade USA
]

# --- SOGLIE SEGNALI ---
THRESHOLDS = {
    # Variazione percentuale che scatena un alert (in %, su intervallo 24h)
    "pct_change_alert": 5.0,

    # RSI: sopra questo valore = ipercomprato, sotto = ipervenduto
    "rsi_overbought": 70,
    "rsi_oversold": 30,

    # Periodo RSI (numero di candele/giorni)
    "rsi_period": 14,

    # Medie mobili per golden cross / death cross
    "sma_short": 50,
    "sma_long": 200,

    # MACD (parametri standard)
    "macd_fast": 12,
    "macd_slow": 26,
    "macd_signal": 9,

    # Bollinger Bands
    "bb_period": 20,
    "bb_std": 2,

    # Spike di volume: quante volte la media per essere considerato anomalo
    "volume_spike_multiplier": 2.0,

    # Ore di "silenzio" prima di poter rimandare lo stesso identico segnale
    # per lo stesso asset (evita spam di notifiche ripetute)
    "cooldown_hours": 12,
}

# Numero di giorni di storico da scaricare per calcolare gli indicatori
HISTORY_DAYS = 250  # serve margine per SMA200
