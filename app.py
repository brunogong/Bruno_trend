import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import numpy as np

# --- CONFIGURAZIONE UI ---
st.set_page_config(page_title="Trading Terminal Pro", layout="wide")

# CSS Personalizzato per Leggibilità e Mobile
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div[data-testid="stMetricValue"] { color: #00ffcc !important; font-size: 1.8rem !important; }
    div[data-testid="stMetricDelta"] { color: #ffffff !important; }
    .stAlert { background-color: #1e1e1e; border: 1px solid #333; color: white; }
    .tradabile { color: #00ff00; font-weight: bold; }
    .attesa { color: #ffcc00; }
    </style>
    """, unsafe_allow_html=True)

try:
    API_KEY = st.secrets["X_RAPIDAPI_KEY"]
except:
    st.error("Configura X_RAPIDAPI_KEY nei Secrets.")
    st.stop()

# --- MOTORE DI CALCOLO ---
def calculate_all(df):
    # EMA
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
    p = {"symbol": symbol, "interval": interval, "outputsize": "100", "format": "json"}
    try:
        r = requests.get(url, headers=h, params=p, timeout=10).json()
        if "values" in r:
            df = pd.DataFrame(r["values"])
            for c in ['open','high','low','close']: df[c] = pd.to_numeric(df[c])
            df['datetime'] = pd.to_datetime(df['datetime'])
            return calculate_all(df.sort_values('datetime'))
    except: return None

# --- DASHBOARD ---
st.title("⚖️ Trading Intelligence Terminal")

# 1. SCANNER VALUTE (In alto, visibile subito)
st.subheader("📡 Opportunity Scanner (TF: 1h)")
assets = {"XAU/USD": "ORO", "EUR/USD": "EURUSD", "GBP/USD": "GBPUSD", "USD/JPY": "USDJPY", "BTC/USD": "BTC"}
cols = st.columns(len(assets))

for i, (sym, name) in enumerate(assets.items()):
    d = fetch_data(sym, "1h")
    if d is not None:
        l = d.iloc[-1]
        is_tradable = l['adx'] > 25
        label = "🔥 TRADABILE" if is_tradable else "😴 ATTESA"
        cols[i].metric(name, f"{l['close']:.2f}", label)

st.divider()

# 2. SELEZIONE E MULTI-TIMEFRAME
sel_asset = st.selectbox("Seleziona Asset per Analisi Profonda:", list(assets.keys()))

st.write("### ⏱️ Multi-Timeframe Trend Check")
t1, t2, t3 = st.columns(3)
timeframes = ["15min", "1h", "4h"]
dfs = {}

for col, timeframe in zip([t1, t2, t3], timeframes):
    data = fetch_data(sel_asset, timeframe)
    if data is not None:
        dfs[timeframe] = data
        last = data.iloc[-1]
        trend = "RIPIAZZO 📈" if last['close'] > last['ema20'] else "RIBASSO 📉"
        col.metric(f"TF: {timeframe}", trend, f"ADX: {last['adx']:.1f}")

# 3. DETTAGLIO INDICATORI (Asset Selezionato su TF 1h)
if "1h" in dfs:
    df_main = dfs["1h"]
    last = df_main.iloc[-1]
    
    st.subheader(f"🎯 Analisi Tecnica: {sel_asset} (1h)")
    
    # BOX INDICATORI
    i1, i2, i3 = st.columns(3)
    
    # RSI
    rsi_val = last['rsi']
    rsi_status = "IPERCOMPRATO ⚠️" if rsi_val > 70 else "IPERVENDUTO ✅" if rsi_val < 30 else "NEUTRO 👍"
    i1.info(f"**RSI (14):** {rsi_val:.1f}\n\nStato: {rsi_status}")
    
    # EMA CROSS
    ema_status = "BULLISH" if last['ema20'] > last['ema50'] else "BEARISH"
    i2.info(f"**Trend Medie:** {ema_status}\n\nEMA20 > EMA50")
    
    # VOLATILITA
    i3.info(f"**ATR (Volatilità):**\n\n{last['atr']:.5f}")

    # 4. LIVELLI OPERATIVI E GRAFICO
    st.divider()
    res_col, chart_col = st.columns([1, 2])
    
    with res_col:
        st.write("### 🚀 Piano d'Azione")
        is_buy = last['close'] > last['ema20']
        adx_strong = last['adx'] > 25
        
        if adx_strong:
            st.success(f"**SEGNALE: {'BUY' if is_buy else 'SELL'}**")
        else:
            st.warning("**NON TRADABILE: Forza Trend insufficiente**")
            
        dist = last['atr'] * 2
        sl = last['close'] - dist if is_buy else last['close'] + dist
        tp = last['close'] + (dist * 3) if is_buy else last['close'] - (dist * 3)
        
        st.write(f"**ENTRY:** {last['close']:.5f}")
        st.write(f"**STOP LOSS:** {sl:.5f}")
        st.write(f"**TAKE PROFIT:** {tp:.5f}")

    with chart_col:
        fig = go.Figure(data=[go.Candlestick(x=df_main['datetime'], open=df_main['open'], high=df_main['high'], low=df_main['low'], close=df_main['close'])])
        fig.add_trace(go.Scatter(x=df_main['datetime'], y=df_main['ema20'], line=dict(color='orange', width=1.5), name="EMA20"))
        fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=450, margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(fig, use_container_width=True)
