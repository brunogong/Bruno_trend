import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import numpy as np

# --- CONFIGURAZIONE MOBILE-FIRST ---
st.set_page_config(page_title="TrendMaster Mobile", layout="centered", initial_sidebar_state="collapsed")

# CSS per migliorare la leggibilità su smartphone
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 1.5rem; }
    .stMetric { background-color: #1e1e1e; padding: 10px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

try:
    API_KEY = st.secrets["X_RAPIDAPI_KEY"]
except:
    st.error("Inserisci la chiave nei Secrets.")
    st.stop()

# --- MOTORE TECNICO ---
def get_indicators(df):
    # EMA 20 (Trend Breve) e EMA 50 (Trend Medio)
    df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
    
    # RSI (Momento)
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['rsi'] = 100 - (100 / (1 + (gain/loss)))
    
    # ATR (Volatilità)
    tr = pd.concat([df['high']-df['low'], abs(df['high']-df['close'].shift()), abs(df['low']-df['close'].shift())], axis=1).max(axis=1)
    df['atr'] = tr.rolling(14).mean()
    
    # ADX (Forza)
    up, dw = df['high'].diff(), df['low'].diff()
    pdm = np.where((up > dw) & (up > 0), up, 0)
    mdm = np.where((dw > up) & (dw > 0), dw, 0)
    tr_s = tr.rolling(14).mean()
    pdi = 100 * (pd.Series(pdm).rolling(14).mean() / tr_s)
    mdi = 100 * (pd.Series(mdm).rolling(14).mean() / tr_s)
    df['adx'] = (100 * abs(pdi - mdi) / (pdi + mdi)).rolling(14).mean()
    
    return df.dropna()

def fetch_safe(symbol, interval):
    url = "https://twelve-data1.p.rapidapi.com/time_series"
    h = {"x-rapidapi-key": API_KEY, "x-rapidapi-host": "twelve-data1.p.rapidapi.com"}
    p = {"symbol": symbol, "interval": interval, "outputsize": "100", "format": "json"}
    try:
        r = requests.get(url, headers=h, params=p, timeout=10).json()
        if "values" in r:
            df = pd.DataFrame(r["values"])
            for c in ['open','high','low','close']: df[c] = pd.to_numeric(df[c])
            df['datetime'] = pd.to_datetime(df['datetime'])
            return get_indicators(df.sort_values('datetime'))
    except: return None

# --- UI APP ---
st.title("📈 TrendMaster Pro")

# Selettore Asset (Grosso per touch)
assets = {"ORO": "XAU/USD", "EUR/USD": "EUR/USD", "GBP/USD": "GBP/USD", "BITCOIN": "BTC/USD"}
sel_asset = st.selectbox("Scegli Mercato:", list(assets.keys()))
symbol = assets[sel_asset]

# Scelta TimeFrame Principale
tf = st.select_slider("Seleziona Time Frame di analisi:", 
                     options=["5min", "15min", "1h", "4h", "1day"], value="1h")

st.divider()

with st.spinner('Analizzando i mercati...'):
    df = fetch_safe(symbol, tf)

if df is not None:
    last = df.iloc[-1]
    
    # Analisi del Trend su TF selezionato
    is_up = last['close'] > last['ema20']
    strength = "FORTE 💪" if last['adx'] > 25 else "DEBOLE 😴"
    
    # Visualizzazione Mobile-Friendly (Metriche incolonnate)
    st.write(f"### Stato attuale ({tf})")
    c1, c2 = st.columns(2)
    c1.metric("Prezzo", f"{last['close']:.4f}")
    c2.metric("Forza ADX", f"{last['adx']:.1f}", strength)

    # Segnale Operativo
    if last['adx'] > 25:
        color = "green" if is_up else "red"
        action = "BUY" if is_up else "SELL"
        st.success(f"### SEGNALE: {action}")
    else:
        st.warning("### ATTENDERE: Trend non chiaro")

    # Box Livelli (Copiabili)
    st.subheader("🎯 Livelli Trading")
    dist = last['atr'] * 2
    sl = last['close'] - dist if is_up else last['close'] + dist
    tp = last['close'] + (dist * 3) if is_up else last['close'] - (dist * 3)
    
    st.code(f"ENTRY: {last['close']:.5f}\nSL:    {sl:.5f}\nTP:    {tp:.5f}")

    # Grafico (Ridimensionato per mobile)
    fig = go.Figure(data=[go.Candlestick(x=df['datetime'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], name="Price")])
    fig.add_trace(go.Scatter(x=df['datetime'], y=df['ema20'], line=dict(color='orange', width=1.5), name="EMA20"))
    fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=400, margin=dict(l=0,r=0,t=0,b=0))
    st.plotly_chart(fig, use_container_width=True)
else:
    st.error("Dati non disponibili. Controlla la tua API Key.")
