import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import numpy as np
from datetime import datetime

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="FX Trend Scanner Pro", layout="wide", page_icon="📈")

# Recupero API Key dai Secrets
try:
    API_KEY = st.secrets["X_RAPIDAPI_KEY"]
except:
    st.error("Configura 'X_RAPIDAPI_KEY' nei Secrets di Streamlit Cloud.")
    st.stop()

# --- MOTORE DI CALCOLO MATEMATICO (Sostituisce librerie esterne) ---
def apply_indicators(df):
    # 1. EMA (Exponential Moving Average)
    df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
    
    # 2. RSI (Relative Strength Index)
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # 3. ATR (Average True Range) - Per Volatilità e Stop Loss
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['atr'] = tr.rolling(14).mean()
    
    # 4. ADX (Average Directional Index) - Per Forza Trend
    up = df['high'] - df['high'].shift()
    down = df['low'].shift() - df['low']
    p_dm = np.where((up > down) & (up > 0), up, 0)
    m_dm = np.where((down > up) & (down > 0), down, 0)
    tr_s = tr.rolling(14).mean()
    p_di = 100 * (pd.Series(p_dm).rolling(14).mean() / tr_s)
    m_di = 100 * (pd.Series(m_dm).rolling(14).mean() / tr_s)
    dx = 100 * np.abs(p_di - m_di) / (p_di + m_di)
    df['adx'] = dx.rolling(14).mean()
    
    return df.dropna()

def fetch_data(symbol, interval="1h"):
    url = "https://twelve-data1.p.rapidapi.com/time_series"
    headers = {"x-rapidapi-key": API_KEY, "x-rapidapi-host": "twelve-data1.p.rapidapi.com"}
    params = {"symbol": symbol, "interval": interval, "outputsize": "150", "format": "json"}
    try:
        res = requests.get(url, headers=headers, params=params, timeout=10)
        data = res.json()
        if "values" in data:
            df = pd.DataFrame(data["values"])
            for col in ['open', 'high', 'low', 'close']: 
                df[col] = pd.to_numeric(df[col])
            df['datetime'] = pd.to_datetime(df['datetime'])
            return apply_indicators(df.sort_values('datetime'))
    except:
        return None
    return None

# --- LOGICA DI SEGNALE ---
def get_verdict(last_row):
    adx = last_row['adx']
    rsi = last_row['rsi']
    price = last_row['close']
    ema20 = last_row['ema20']
    
    trend_up = price > ema20
    is_strong = adx > 25
    
    if is_strong and trend_up and rsi < 65:
        return "🟢 BUY CONFIRMED", "green"
    elif is_strong and not trend_up and rsi > 35:
        return "🔴 SELL CONFIRMED", "red"
    else:
        return "🟡 ATTENDERE (Trend Debole o Iperesteso)", "blue"

# --- INTERFACCIA UTENTE ---
st.title("⚖️ Trading Terminal: Scanner & Signals")

# 1. MARKET SCANNER (Top Bar)
assets = {
    "XAU/USD": "Oro", "EUR/USD": "Euro", "GBP/USD": "Sterlina", 
    "USD/JPY": "Yen", "AUD/USD": "Aussie", "BTC/USD": "Bitcoin"
}

st.subheader("🔍 Real-Time Market Scanner")
cols = st.columns(len(assets))
all_data = {}

for i, (sym, name) in enumerate(assets.items()):
    df_asset = fetch_data(sym, "1h")
    if df_asset is not None:
        all_data[sym] = df_asset
        last = df_asset.iloc[-1]
        status = "🔥" if last['adx'] > 25 else "💤"
        cols[i].metric(sym, f"{last['close']:.2f}", f"{status} ADX:{last['adx']:.0f}")

st.divider()

# 2. ANALISI DETTAGLIATA
sel_sym = st.selectbox("Seleziona Asset per analisi tecnica profonda", list(assets.keys()))
df = all_data.get(sel_sym)

if df is not None:
    last = df.iloc[-1]
    verdict, color = get_verdict(last)
    
    # Header Segnale
    st.markdown(f"### Verdetto: :{color}[{verdict}]")
    
    # Griglia Indicatori
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("ADX (Forza)", f"{last['adx']:.1f}", "FORTE" if last['adx'] > 25 else "DEBOLE")
    c2.metric("RSI (Momento)", f"{last['rsi']:.1f}", "IPER" if last['rsi'] > 70 or last['rsi'] < 30 else "OK")
    c3.metric("ATR (Volatilità)", f"{last['atr']:.4f}")
    c4.metric("Trend EMA", "RIALZO" if last['close'] > last['ema20'] else "RIBASSO")

    # 3. LIVELLI OPERATIVI
    st.subheader("🎯 Piano d'Azione (Money Management)")
    entry = last['close']
    sl_dist = last['atr'] * 2 # Stop Loss basato su 2 volte la volatilità media
    is_buy = last['close'] > last['ema20']
    
    sl = entry - sl_dist if is_buy else entry + sl_dist
    tp = entry + (sl_dist * 3) if is_buy else entry - (sl_dist * 3) # Target 1:3

    o1, o2, o3 = st.columns(3)
    o1.info(f"**ENTRY:** \n`{entry:.5f}`")
    o2.error(f"**STOP LOSS:** \n`{sl:.5f}`")
    o3.success(f"**TAKE PROFIT:** \n`{tp:.5f}`")

    # 4. GRAFICO PROFESSIONALE
    fig = go.Figure(data=[go.Candlestick(
        x=df['datetime'], open=df['open'], high=df['high'],
        low=df['low'], close=df['close'], name="Prezzo"
    )])
    fig.add_trace(go.Scatter(x=df['datetime'], y=df['ema20'], line=dict(color='orange', width=1.2), name="EMA 20"))
    fig.add_trace(go.Scatter(x=df['datetime'], y=df['ema50'], line=dict(color='cyan', width=1.2), name="EMA 50"))
    
    fig.update_layout(
        template="plotly_dark", 
        xaxis_rangeslider_visible=False, 
        height=600,
        margin=dict(l=10, r=10, t=10, b=10)
    )
    st.plotly_chart(fig, use_container_width=True)

else:
    st.warning("⚠️ Caricamento dati fallito. Verifica la tua API Key o i limiti di Twelve Data.")
