import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import numpy as np

# --- CONFIGURAZIONE UI PROFESSIONALE ---
st.set_page_config(page_title="Bruno Trend Pro", layout="wide", initial_sidebar_state="collapsed")

# CSS Avanzato per contrasto elevato e leggibilità mobile
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    /* Forza il colore bianco puro per le etichette delle metriche */
    [data-testid="stMetricLabel"] {
        color: #ffffff !important;
        font-size: 1.1rem !important;
        font-weight: 700 !important;
    }
    /* Valore numerico in Verde Neon */
    [data-testid="stMetricValue"] {
        color: #00ffcc !important;
        font-size: 1.8rem !important;
    }
    /* Sfondo scuro solido per i box metriche */
    [data-testid="stMetric"] {
        background-color: #161b22;
        border: 1px solid #30363d;
        padding: 15px;
        border-radius: 10px;
    }
    /* Fix per i testi scuri nei box info */
    .stAlert {
        background-color: #1f2937 !important;
        color: #ffffff !important;
        border: 1px solid #3b82f6 !important;
    }
    .stAlert p { color: #ffffff !important; font-weight: 500; }
    </style>
    """, unsafe_allow_html=True)

try:
    API_KEY = st.secrets["X_RAPIDAPI_KEY"]
except:
    st.error("Inserisci X_RAPIDAPI_KEY nei Secrets.")
    st.stop()

# --- FUNZIONI DI CALCOLO ---
def calculate_tech(df):
    # EMA 20 e 50
    df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['rsi'] = 100 - (100 / (1 + (gain/loss)))
    # ATR
    tr = pd.concat([df['high']-df['low'], abs(df['high']-df['close'].shift()), abs(df['low']-df['close'].shift())], axis=1).max(axis=1)
    df['atr'] = tr.rolling(14).mean()
    # ADX
    up, dw = df['high'].diff(), df['low'].diff()
    pdm = np.where((up > dw) & (up > 0), up, 0)
    mdm = np.where((dw > up) & (dw > 0), dw, 0)
    tr_s = tr.rolling(14).mean()
    pdi = 100 * (pd.Series(pdm).rolling(14).mean() / tr_s)
    mdi = 100 * (pd.Series(mdm).rolling(14).mean() / tr_s)
    df['adx'] = (100 * abs(pdi - mdi) / (pdi + mdi)).rolling(14).mean()
    return df.dropna()

def fetch_data(symbol, interval):
    url = "https://twelve-data1.p.rapidapi.com/time_series"
    h = {"x-rapidapi-key": API_KEY, "x-rapidapi-host": "twelve-data1.p.rapidapi.com"}
    p = {"symbol": symbol, "interval": interval, "outputsize": "150", "format": "json"}
    try:
        r = requests.get(url, headers=h, params=p, timeout=10).json()
        if "values" in r:
            df = pd.DataFrame(r["values"])
            for c in ['open','high','low','close']: df[c] = pd.to_numeric(df[c])
            df['datetime'] = pd.to_datetime(df['datetime'])
            return calculate_tech(df.sort_values('datetime'))
    except: return None

# --- DASHBOARD ---
st.title("⚖️ Bruno Trend: Terminal Intelligence")

# 1. SCANNER ORIZZONTALE (Visibile e Contrasto Alto)
assets = {"XAU/USD": "ORO", "EUR/USD": "EURUSD", "GBP/USD": "GBPUSD", "USD/JPY": "USDJPY", "BTC/USD": "BTC"}
cols = st.columns(len(assets))
scanner_dfs = {}

for i, (sym, name) in enumerate(assets.items()):
    data = fetch_data(sym, "1h")
    if data is not None:
        scanner_dfs[sym] = data
        last = data.iloc[-1]
        status = "🔥 TRADABILE" if last['adx'] > 25 else "⏳ ATTESA"
        cols[i].metric(label=name, value=f"{last['close']:.2f}", delta=status, delta_color="normal" if last['adx'] > 25 else "off")

st.divider()

# 2. SELEZIONE E MULTI-TIMEFRAME (Riempiamo lo spazio vuoto dello screenshot)
sel_asset = st.selectbox("🎯 Analisi Asset:", list(assets.keys()))

st.markdown("### ⏱️ Multi-Timeframe Check (Trend Primario)")
t1, t2, t3 = st.columns(3)
tfs = ["15min", "1h", "4h"]

for col, timeframe in zip([t1, t2, t3], tfs):
    d_tf = fetch_data(sel_asset, timeframe)
    if d_tf is not None:
        l_tf = d_tf.iloc[-1]
        trend_label = "RIPIAZZO 📈" if l_tf['close'] > l_tf['ema20'] else "RIBASSO 📉"
        col.metric(f"Grafico: {timeframe}", trend_label, f"ADX Forza: {l_tf['adx']:.1f}")

st.divider()

# 3. ANALISI TECNICA (Risolto problema scritte scure)
if sel_asset in scanner_dfs:
    df_main = scanner_dfs[sel_asset]
    last = df_main.iloc[-1]
    
    st.markdown(f"### 🔍 Indicatori Dettagliati: {sel_asset} (1h)")
    i1, i2, i3 = st.columns(3)
    
    rsi_stat = "IPERCOMPRATO ⚠️" if last['rsi'] > 70 else "IPERVENDUTO ✅" if last['rsi'] < 30 else "NEUTRO 👍"
    i1.info(f"**RSI (14):** {last['rsi']:.1f}\n\nStato: {rsi_stat}")
    
    ema_stat = "BULLISH" if last['ema20'] > last['ema50'] else "BEARISH"
    i2.info(f"**Trend Medie:** {ema_stat}\n\nEMA20 > EMA50")
    
    i3.info(f"**ATR (Volatilità):**\n\n{last['atr']:.5f}")

    # 4. PIANO D'AZIONE E GRAFICO
    st.divider()
    col_act, col_chart = st.columns([1, 2])
    
    with col_act:
        st.markdown("### 🚀 Verdetto Operativo")
        is_up = last['close'] > last['ema20']
        
        if last['adx'] > 25:
            st.success(f"**SEGNALE ATTIVO: {'BUY 🚀' if is_up else 'SELL 📉'}**")
        else:
            st.warning("**⏳ IN ATTESA DI BREAKOUT: Forza trend debole**")
            
        dist = last['atr'] * 2
        sl = last['close'] - dist if is_up else last['close'] + dist
        tp = last['close'] + (dist * 3) if is_up else last['close'] - (dist * 3)
        
        st.markdown(f"""
        - **ENTRY:** `{last['close']:.5f}`
        - **STOP LOSS:** `{sl:.5f}`
        - **TAKE PROFIT:** `{tp:.5f}`
        """)

    with col_chart:
        fig = go.Figure(data=[go.Candlestick(x=df_main['datetime'], open=df_main['open'], high=df_main['high'], low=df_main['low'], close=df_main['close'])])
        fig.add_trace(go.Scatter(x=df_main['datetime'], y=df_main['ema20'], line=dict(color='orange', width=1.5), name="EMA20"))
        fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=450, margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(fig, use_container_width=True)
