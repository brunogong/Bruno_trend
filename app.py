import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import numpy as np

# --- CONFIGURAZIONE INTERFACCIA ---
st.set_page_config(page_title="BULL & BEAR TERMINAL", layout="wide", initial_sidebar_state="collapsed")

# CSS per il look "Terminal Professionale" (Nero profondo e Neon)
st.markdown("""
    <style>
    .main { background-color: #05070a; font-family: 'Courier New', Courier, monospace; }
    [data-testid="stMetric"] {
        background-color: #0d1117;
        border: 1px solid #1f2937;
        padding: 15px;
        border-radius: 8px;
    }
    [data-testid="stMetricValue"] { color: #00f2ff !important; font-size: 1.8rem !important; }
    [data-testid="stMetricLabel"] { color: #8b949e !important; font-weight: bold; }
    .stAlert { background-color: #161b22 !important; color: white !important; border: 1px solid #30363d !important; }
    .bull-glow { color: #22c55e; text-shadow: 0 0 15px #22c55e; font-size: 28px; font-weight: bold; text-align: center; }
    .bear-glow { color: #ef4444; text-shadow: 0 0 15px #ef4444; font-size: 28px; font-weight: bold; text-align: center; }
    .wait-glow { color: #f59e0b; text-shadow: 0 0 15px #f59e0b; font-size: 28px; font-weight: bold; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# --- MOTORE TECNICO (LOGICA INDICATORI) ---
def apply_tech_logic(df):
    # EMA 20 (Trend Veloce) e 50 (Trend Istituzionale)
    df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
    
    # RSI (Relative Strength Index)
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['rsi'] = 100 - (100 / (1 + (gain/loss)))
    
    # ATR (Average True Range - Volatilità)
    tr = pd.concat([df['high']-df['low'], abs(df['high']-df['close'].shift()), abs(df['low']-df['close'].shift())], axis=1).max(axis=1)
    df['atr'] = tr.rolling(14).mean()
    
    # ADX (Average Directional Index - Forza Trend)
    up, dw = df['high'].diff(), df['low'].diff()
    pdm = np.where((up > dw) & (up > 0), up, 0)
    mdm = np.where((dw > up) & (dw > 0), dw, 0)
    tr_s = tr.rolling(14).mean()
    pdi = 100 * (pd.Series(pdm).rolling(14).mean() / tr_s)
    mdi = 100 * (pd.Series(mdm).rolling(14).mean() / tr_s)
    df['adx'] = (100 * abs(pdi - mdi) / (pdi + mdi)).rolling(14).mean()
    
    return df.dropna()

def fetch_market_data(symbol, interval):
    try:
        api_key = st.secrets["X_RAPIDAPI_KEY"]
        url = "https://twelve-data1.p.rapidapi.com/time_series"
        headers = {"x-rapidapi-key": api_key, "x-rapidapi-host": "twelve-data1.p.rapidapi.com"}
        params = {"symbol": symbol, "interval": interval, "outputsize": "150", "format": "json"}
        
        response = requests.get(url, headers=headers, params=params, timeout=15)
        data = response.json()
        
        if "values" in data:
            df = pd.DataFrame(data["values"])
            for col in ['open','high','low','close']:
                df[col] = pd.to_numeric(df[col])
            df['datetime'] = pd.to_datetime(df['datetime'])
            return apply_tech_logic(df.sort_values('datetime'))
    except Exception as e:
        return None
    return None

# --- APPLICAZIONE ---
st.markdown("<h1 style='text-align: center; color: white;'>⚡ BULL & BEAR TERMINAL</h1>", unsafe_allow_html=True)

# 1. SCANNER ORIZZONTALE (TOP BAR)
assets = {"XAU/USD": "GOLD", "EUR/USD": "EURUSD", "GBP/USD": "GBPUSD", "USD/JPY": "USDJPY", "BTC/USD": "BITCOIN"}
scanner_cols = st.columns(len(assets))

# Memorizziamo i dati per evitare doppie chiamate API
cache_main_tf = {}

for i, (sym, name) in enumerate(assets.items()):
    with st.spinner(''):
        d = fetch_market_data(sym, "1h")
        if d is not None:
            cache_main_tf[sym] = d
            last = d.iloc[-1]
            status = "🔥 TRADE" if last['adx'] > 25 else "⏳ WAIT"
            scanner_cols[i].metric(name, f"{last['close']:.2f}", status, delta_color="normal" if last['adx'] > 25 else "off")

st.divider()

# 2. SELEZIONE ASSET E ANALISI MULTI-TF
sel_asset = st.selectbox("🎯 SELECT TARGET ASSET:", list(assets.keys()))

st.markdown("### 🚦 MULTI-TIMEFRAME TREND CHECK")
mtf_cols = st.columns(3)
tfs = ["15min", "1h", "4h"]

for col, timeframe in zip(mtf_cols, tfs):
    # Se il dato è già in cache per 1h, usalo, altrimenti scarica
    if timeframe == "1h" and sel_asset in cache_main_tf:
        df_tf = cache_main_tf[sel_asset]
    else:
        df_tf = fetch_market_data(sel_asset, timeframe)
    
    if df_tf is not None:
        last_tf = df_tf.iloc[-1]
        is_bull = last_tf['close'] > last_tf['ema20']
        trend_label = "BULL 🐂" if is_bull else "BEAR 🐻"
        col.metric(f"TF: {timeframe}", trend_label, f"ADX: {last_tf['adx']:.1f}")

st.divider()

# 3. ANALISI DETTAGLIATA (1H)
if sel_asset in cache_main_tf:
    df_main = cache_main_tf[sel_asset]
    l = df_main.iloc[-1]
    
    st.markdown(f"### 🔍 TECHNICAL SPECS: {sel_asset} (1H)")
    i1, i2, i3 = st.columns(3)
    
    rsi_val = l['rsi']
    rsi_desc = "OVERBOUGHT ⚠️" if rsi_val > 70 else "OVERSOLD ✅" if rsi_val < 30 else "NEUTRAL 👍"
    i1.info(f"**MOMENTUM (RSI 14)**\n\nVAL: {rsi_val:.1f} | {rsi_desc}")
    
    structure = "BULLISH (Price > EMA20)" if l['close'] > l['ema20'] else "BEARISH (Price < EMA20)"
    i2.info(f"**STRUCTURE**\n\n{structure}")
    
    i3.info(f"**VOLATILITY (ATR)**\n\nValue: {l['atr']:.5f}")

    # 4. VERDETTO E GRAFICO
    st.divider()
    c_act, c_graph = st.columns([1, 2])
    
    with c_act:
        st.subheader("🏁 FINAL VERDICT")
        is_up = l['close'] > l['ema20']
        adx_strong = l['adx'] > 25
        
        if adx_strong:
            glow_class = "bull-glow" if is_up else "bear-glow"
            verdict_txt = "BUY NOW 🚀" if is_up else "SELL NOW 📉"
            st.markdown(f"<div class='{glow_class}'>{verdict_txt}</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='wait-glow'>⏳ WAIT FOR TREND</div>", unsafe_allow_html=True)
            
        # Money Management basato su ATR
        dist = l['atr'] * 2
        sl = l['close'] - dist if is_up else l['close'] + dist
        tp = l['close'] + (dist * 3.5) if is_up else l['close'] - (dist * 3.5)
        
        st.markdown(f"""
        **POSIZIONAMENTO:**
        - **ENTRY:** `{l['close']:.5f}`
        - **STOP LOSS:** `{sl:.5f}`
        - **TAKE PROFIT:** `{tp:.5f}`
        """)

    with c_graph:
        fig = go.Figure(data=[go.Candlestick(
            x=df_main['datetime'],
            open=df_main['open'],
            high=df_main['high'],
            low=df_main['low'],
            close=df_main['close'],
            name="Price"
        )])
        fig.add_trace(go.Scatter(x=df_main['datetime'], y=df_main['ema20'], line=dict(color='#00f2ff', width=1.5), name="EMA20"))
        fig.add_trace(go.Scatter(x=df_main['datetime'], y=df_main['ema50'], line=dict(color='#ff00ff', width=1), name="EMA50"))
        
        fig.update_layout(
            template="plotly_dark",
            xaxis_rangeslider_visible=False,
            height=500,
            paper_bgcolor="#05070a",
            plot_bgcolor="#05070a",
            margin=dict(l=0, r=0, t=0, b=0)
        )
        st.plotly_chart(fig, use_container_width=True)
else:
    st.error("Dati non ricevuti dall'API. Controlla la connessione o i segreti.")
