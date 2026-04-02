import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import numpy as np

# --- CONFIGURAZIONE UI ULTIMATE ---
st.set_page_config(page_title="TERMINAL BULL/BEAR", layout="wide", initial_sidebar_state="collapsed")

# CSS Custom per un look da vero Trader
st.markdown("""
    <style>
    .main { background-color: #05070a; font-family: 'Roboto Mono', monospace; }
    
    /* Box delle metriche stile Dashboard */
    [data-testid="stMetric"] {
        background-color: #0d1117;
        border: 2px solid #1f2937;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    
    [data-testid="stMetricValue"] { color: #00f2ff !important; font-size: 2rem !important; font-weight: 800; }
    [data-testid="stMetricLabel"] { color: #8b949e !important; text-transform: uppercase; letter-spacing: 1px; }

    /* Alert Personalizzati */
    .stAlert { background-color: #161b22 !important; border: 1px solid #30363d !important; color: white !important; }

    /* Segnale BULL/BEAR Glow */
    .bull-signal { color: #22c55e; text-shadow: 0 0 10px #22c55e; font-size: 24px; font-weight: bold; }
    .bear-signal { color: #ef4444; text-shadow: 0 0 10px #ef4444; font-size: 24px; font-weight: bold; }
    .wait-signal { color: #f59e0b; text-shadow: 0 0 10px #f59e0b; font-size: 24px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

try:
    API_KEY = st.secrets["X_RAPIDAPI_KEY"]
except:
    st.error("Errore: API KEY mancante nei Secrets.")
    st.stop()

# --- ENGINE TECNICO ---
def get_indicators(df):
    df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['rsi'] = 100 - (100 / (1 + (gain/loss)))
    tr = pd.concat([df['high']-df['low'], abs(df['high']-df['close'].shift()), abs(df['low']-df['close'].shift())], axis=1).max(axis=1)
    df['atr'] = tr.rolling(14).mean()
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
    p = {"symbol": symbol, "interval": interval, "outputsize": "120", "format": "json"}
    try:
        r = requests.get(url, headers=h, params=p, timeout=10).json()
        if "values" in r:
            df = pd.DataFrame(r["values"])
            for c in ['open','high','low','close']: df[c] = pd.to_numeric(df[c])
            df['datetime'] = pd.to_datetime(df['datetime'])
            return get_indicators(df.sort_values('datetime'))
    except: return None

# --- DASHBOARD ---
st.markdown("<h1 style='text-align: center; color: white;'>⚡ TERMINAL BULL & BEAR</h1>", unsafe_allow_html=True)

# 1. SCANNER TOP BAR
assets = {"XAU/USD": "GOLD", "EUR/USD": "EURUSD", "GBP/USD": "GBPUSD", "USD/JPY": "USDJPY", "BTC/USD": "BITCOIN"}
cols = st.columns(len(assets))

for i, (sym, name) in enumerate(assets.items()):
    d = fetch_data(sym, "1h")
    if d is not None:
        last = d.iloc[-1]
        label = "🔥 TRADE" if last['adx'] > 25 else "⏳ WAIT"
        cols[i].metric(name, f"{last['close']:.2f}", label, delta_color="normal" if last['adx'] > 25 else "off")

st.divider()

# 2. SELEZIONE ASSET E MULTI-TF
sel_asset = st.selectbox("🎯 TARGET SELECTION:", list(assets.keys()))

st.markdown("### 🚦 MULTI-TIMEFRAME TREND")
t1, t2, t3 = st.columns(3)
tfs = ["15min", "1h", "4h"]

for col, timeframe in zip([t1, t2, t3], tfs):
    data_tf = fetch_data(sel_asset, timeframe)
    if data_tf is not None:
        l_tf = data_tf.iloc[-1]
        is_bull = l_tf['close'] > l_tf['ema20']
        trend_txt = "BULL 🐂" if is_bull else "BEAR 🐻"
        col.metric(f"TF: {timeframe}", trend_txt, f"FORZA ADX: {l_tf['adx']:.1f}")

st.divider()

# 3. ANALISI DETTAGLIATA (Box info stilizzati)
data_main = fetch_data(sel_asset, "1h")
if data_main is not None:
    l = data_main.iloc[-1]
    
    i1, i2, i3 = st.columns(3)
    rsi_val = l['rsi']
    rsi_desc = "OVERBOUGHT ⚠️" if rsi_val > 70 else "OVERSOLD ✅" if rsi_val < 30 else "NEUTRAL 👍"
    i1.info(f"**MOMENTUM (RSI)**\n\n{rsi_val:.1f} - {rsi_desc}")
    
    cross = "EMA BULLISH ✅" if l['ema20'] > l['ema50'] else "EMA BEARISH ❌"
    i2.info(f"**STRUCTURE**\n\n{cross}")
    
    i3.info(f"**VOLATILITY (ATR)**\n\n{l['atr']:.5f}")

    # 4. PIANO D'AZIONE E GRAFICO
    st.divider()
    c_action, c_chart = st.columns([1, 2])
    
    with c_action:
        st.subheader("🏁 FINAL VERDICT")
        is_up = l['close'] > l['ema20']
        if l['adx'] > 25:
            sig_class = "bull-signal" if is_up else "bear-signal"
            sig_txt = "BUY NOW 🚀" if is_up else "SELL NOW 📉"
            st.markdown(f"<p class='{sig_class}'>{sig_txt}</p>", unsafe_allow_html=True)
        else:
            st.markdown("<p class='wait-signal'>⏳ NO TREND (WAIT)</p>", unsafe_allow_html=True)
            
        dist = l['atr'] * 1.5
        sl = l['close'] - dist if is_up else l['close'] + dist
        tp = l['close'] + (dist * 3) if is_up else l['close'] - (dist * 3)
        
        st.write(f"**ENTRY:** `{l['close']:.5f}`")
        st.write(f"**STOP LOSS:** `{sl:.5f}`")
        st.write(f"**TAKE PROFIT:** `{tp:.5f}`")

    with c_chart:
        fig = go.Figure(data=[go.Candlestick(x=data_main['datetime'], open=data_main['open'], high=data_main['high'], low=data_main['low'], close=data_main['close'])])
        fig.add_trace(go.Scatter(x=data_main['datetime'], y=data_main['ema20'], line=dict(color='#ff9900', width=2), name="EMA20"))
        fig.update_layout(template="plotly_dark", paper_bgcolor="#05070a", plot_bgcolor="#05070a", xaxis_rangeslider_visible=False, height=450, margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(fig, use_container_width=True)
