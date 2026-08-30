"""
Funzioni per scaricare i dati storici di prezzo per crypto, azioni, ETF e obbligazioni.
Ritornano sempre un pandas.DataFrame con almeno la colonna 'close' (indicizzato per data).
"""
import time
import requests
import pandas as pd
import yfinance as yf

from config import HISTORY_DAYS

COINGECKO_BASE = "https://api.coingecko.com/api/v3"


def fetch_crypto_history(coin_id: str) -> pd.DataFrame:
    """Scarica lo storico prezzi/volumi di una crypto da CoinGecko."""
    url = f"{COINGECKO_BASE}/coins/{coin_id}/market_chart"
    params = {"vs_currency": "usd", "days": HISTORY_DAYS, "interval": "daily"}
    resp = requests.get(url, params=params, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    prices = pd.DataFrame(data["prices"], columns=["timestamp", "close"])
    volumes = pd.DataFrame(data["total_volumes"], columns=["timestamp", "volume"])

    df = prices.merge(volumes, on="timestamp")
    df["date"] = pd.to_datetime(df["timestamp"], unit="ms")
    df = df.set_index("date").drop(columns=["timestamp"])
    return df


def fetch_yfinance_history(ticker: str) -> pd.DataFrame:
    """Scarica lo storico di un ticker (azione, ETF o ETF obbligazionario) da Yahoo Finance."""
    data = yf.download(
        ticker,
        period=f"{HISTORY_DAYS}d",
        interval="1d",
        progress=False,
        auto_adjust=True,
    )
    if data.empty:
        raise ValueError(f"Nessun dato ricevuto per {ticker}")

    # yfinance a volte ritorna colonne multi-livello se si passano più ticker insieme
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    df = data.rename(columns={"Close": "close", "Volume": "volume"})
    return df[["close", "volume"]]


def safe_fetch(fetch_fn, identifier: str, retries: int = 2, delay: float = 2.0):
    """Wrapper con retry per non far fallire tutto il bot se un singolo asset ha un errore temporaneo."""
    last_error = None
    for attempt in range(retries + 1):
        try:
            return fetch_fn(identifier)
        except Exception as e:
            last_error = e
            if attempt < retries:
                time.sleep(delay)
    print(f"[WARN] Impossibile scaricare dati per {identifier}: {last_error}")
    return None
