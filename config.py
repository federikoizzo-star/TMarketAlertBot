"""
Configurazione del bot: watchlist e soglie per i segnali.
Modifica liberamente queste liste per personalizzare cosa monitorare.

Universo ampliato (v2 - moderato):
- Crypto: 40 tra le più liquide/capitalizzate
- Azioni: 50 (40 USA diversificate per settore + 10 FTSE MIB principali)
- ETF: 15 su varie asset class
- Obbligazionari: 4 ETF proxy
Totale asset monitorati: 109

NOTA: il cron in monitor.yml va tenuto a 30 minuti (non 10) con questo volume
di asset, per restare comodamente nei minuti gratuiti di GitHub Actions.
"""

# --- CRYPTO ---
# ID CoinGecko (non il ticker!). Lista completa: https://api.coingecko.com/api/v3/coins/list
CRYPTO_WATCHLIST = [
    "bitcoin", "ethereum", "tether", "ripple", "binancecoin", "solana", "usd-coin", "dogecoin",
    "cardano", "tron", "staked-ether", "chainlink", "avalanche-2", "the-open-network", "shiba-inu", "sui",
    "wrapped-bitcoin", "bitcoin-cash", "stellar", "polkadot", "hedera-hashgraph", "litecoin", "weth", "leo-token",
    "hyperliquid", "bitget-token", "uniswap", "near", "ethena-usde", "dai", "pepe", "aptos",
    "internet-computer", "mantle", "monero", "polygon-ecosystem-token", "okb", "cronos", "aave", "vechain",
]

# --- AZIONI ---
# yfinance usa "-" al posto di "." per le classi di azioni USA (es BRK-B)
# suffisso .MI per Borsa Italiana
STOCKS_WATCHLIST = [
    "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "AVGO",
    "JPM", "V", "MA", "UNH", "HD", "PG", "JNJ", "XOM",
    "CVX", "LLY", "MRK", "ABBV", "KO", "PEP", "WMT", "COST",
    "MCD", "NKE", "DIS", "NFLX", "ADBE", "CRM", "ORCL", "CSCO",
    "AMD", "INTC", "QCOM", "BA", "CAT", "GE", "GS", "BAC",
    "UCG.MI", "ISP.MI", "ENEL.MI", "ENI.MI", "RACE.MI", "STLAM.MI", "G.MI", "PST.MI",
    "LDO.MI", "STM.MI",
]

# --- ETF ---
ETF_WATCHLIST = [
    "SPY", "QQQ", "VTI", "VXUS", "VWCE.DE", "XLK", "XLF", "XLE",
    "XLV", "SMH", "GLD", "SLV", "ARKK", "ICLN", "SCHD",
]

# --- OBBLIGAZIONI (via ETF obbligazionari come proxy) ---
BONDS_WATCHLIST = [
    "TLT", "IEF", "AGG", "LQD",
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
