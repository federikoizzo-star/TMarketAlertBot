# Bot Telegram Monitoraggio Mercati

Monitora crypto, azioni, ETF e obbligazioni (via ETF proxy) e ti manda una notifica su
Telegram quando rileva movimenti di prezzo o segnali tecnici significativi:
- Variazione % rilevante nelle 24h
- RSI in zona ipercomprato/ipervenduto
- Golden cross / death cross (medie mobili 50/200)
- Incrocio MACD
- Breakout delle Bollinger Bands
- Spike di volume anomalo

⚠️ **Non è un consulente finanziario**: il bot ti segnala dati e pattern tecnici,
non ti dice cosa comprare o vendere. Le decisioni restano sempre tue.

---

## 1. Crea il bot Telegram

1. Apri Telegram e cerca **@BotFather**
2. Manda il comando `/newbot` e segui le istruzioni (nome e username del bot)
3. BotFather ti darà un **token** tipo `123456789:AAExxxxxxxxxxxxxxxxxxxxxxx` → salvalo, ti servirà dopo

## 2. Trova il tuo Chat ID

1. Cerca su Telegram **@userinfobot** e avvialo: ti mostra subito il tuo **Chat ID** (un numero)
2. Salvalo, ti servirà anche questo

## 3. Carica il progetto su GitHub

1. Crea un account su [github.com](https://github.com) se non ce l'hai già
2. Crea un nuovo repository (può essere **pubblico**, così hai minuti Actions illimitati gratis)
3. Carica tutti i file di questo progetto nel repository (puoi trascinarli dall'interfaccia web di GitHub, oppure con `git push` se hai familiarità con git)

## 4. Configura i "Secrets" (le tue credenziali, in modo sicuro)

Nel tuo repository GitHub:
1. Vai su **Settings → Secrets and variables → Actions**
2. Clicca **New repository secret** e crea:
   - `TELEGRAM_BOT_TOKEN` → il token ottenuto da BotFather
   - `TELEGRAM_CHAT_ID` → il chat id ottenuto da userinfobot

## 5. Attiva il bot

Il workflow (`.github/workflows/monitor.yml`) è già configurato per girare **ogni 30 minuti**
automaticamente. Puoi anche:
- Andare su **Actions** nel tuo repository
- Selezionare "Market Monitor Bot"
- Cliccare **Run workflow** per testarlo subito manualmente

Se tutto è configurato bene, entro pochi minuti riceverai un messaggio su Telegram
(se ci sono segnali attivi in quel momento — altrimenti il bot resta silenzioso finché non
succede qualcosa di rilevante).

## 6. Personalizza cosa monitorare

Apri `config.py`:
- `CRYPTO_WATCHLIST`, `STOCKS_WATCHLIST`, `ETF_WATCHLIST`, `BONDS_WATCHLIST` → aggiungi/rimuovi asset
- `THRESHOLDS` → regola la sensibilità dei segnali (es. `pct_change_alert` per la soglia di variazione %)

Per i ticker azionari/ETF usa il formato Yahoo Finance (es. `AAPL`, `VWCE.DE` per un ETF quotato a
Francoforte, `ENEL.MI` per un titolo quotato a Milano).
Per le crypto usa l'ID CoinGecko (minuscolo, es. `bitcoin`, non `BTC`) — trovi la lista completa su
https://api.coingecko.com/api/v3/coins/list

## Note tecniche

- Lo stato delle notifiche già inviate è salvato in `state.json` (per evitare spam):
  ogni segnale ha un "cooldown" configurabile (`cooldown_hours`, default 12h) prima di poter
  essere rinotificato.
- CoinGecko in versione gratuita ha dei rate limit: con 5 crypto in watchlist e un check ogni
  30 minuti non dovresti avere problemi. Se aggiungi molte crypto e vedi errori 429, aumenta
  l'intervallo del cron o riduci la watchlist.
- yfinance è una libreria "non ufficiale" che legge dati pubblici di Yahoo Finance: è molto
  usata ma può occasionalmente avere interruzioni se Yahoo cambia qualcosa lato loro.

## Testare in locale (opzionale)

```bash
pip install -r requirements.txt
export TELEGRAM_BOT_TOKEN="il_tuo_token"
export TELEGRAM_CHAT_ID="il_tuo_chat_id"
python main.py
```
