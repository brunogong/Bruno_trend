import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from datetime import datetime
import numpy as np

# --- CONFIG ---
st.set_page_config(
    page_title="BULL & BEAR TERMINAL",
    layout="wide",
    initial_sidebar_state="collapsed",
    page_icon="⚡"
)

# Professional Terminal CSS
st.markdown("""
    <style>
    .main { background-color: #05070a; font-family: 'Courier New', Courier, monospace; }
    [data-testid="stMetric"] {
        background-color: #0d1117;
        border: 1px solid #1f2937;
        padding: 18px;
        border-radius: 8px;
    }
    [data-testid="stMetricValue"] { color: #00f2ff !important; font-size: 1.85rem !important; font-weight: bold; }
    [data-testid="stMetricLabel"] { color: #8b949e !important; font-weight: bold; }
    .stAlert { background-color: #161b22 !important; border: 1px solid #30363d !important; }
    
    .bull-glow { color: #22c55e; text-shadow: 0 0 20px #22c55e; font-size: 32px; font-weight: bold; text-align: center; }
    .bear-glow { color: #ef4444; text-shadow: 0 0 20px #ef4444; font-size: 32px; font-weight: bold; text-align: center; }
    .wait-glow { color: #f59e0b; text-shadow: 0 0 20px #f59e0b; font-size: 32px; font-weight: bold; text-align: center; }
    
    h1 { font-family: 'Courier New', monospace; letter-spacing: 2px; }
    </style>
    """, unsafe_allow_html=True)

# --- TECHNICAL INDICATORS ---
@st.cache_data(ttl=300)
def apply_tech_logic(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    
    df = df.copy()
    
    # EMAs
    df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
    
    # RSI with safety
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = -delta.where(delta < 0, 0).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # ATR
    tr1 = df['high'] - df['low']
    tr2 = abs(df['high'] - df['close'].shift())
    tr3 = abs(df['low'] - df['close'].shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df['atr'] = tr.rolling(14).mean()
    
    # ADX (simplified but robust)
    up = df['high'].diff()
    down = df['low'].diff()
    plus_dm = np.where((up > down) & (up > 0), up, 0)
    minus_dm = np.where((down > up) & (down > 0), down, 0)
    
    tr14 = tr.rolling(14).mean()
    plus_di = 100 * (pd.Series(plus_dm).rolling(14).mean() / tr14)
    minus_di = 100 * (pd.Series(minus_dm).rolling(14).mean() / tr14)
    
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di).replace(0, np.nan)
    df['adx'] = dx.rolling(14).mean()
    
    return df.dropna().reset_index(drop=True)

# --- DATA FETCH ---
@st.cache_data(ttl=180)  # Cache for 3 minutes
def fetch_market_data(symbol: str, interval: str):
    try:
        api_key = st.secrets.get("X_RAPIDAPI_KEY")
        if not api_key:
            st.error("❌ API key not found in secrets. Please add `X_RAPIDAPI_KEY` to `.streamlit/secrets.toml`")
            return None
            
        url = "https://twelve-data1.p.rapidapi.com/time_series"
        headers = {
            "x-rapidapi-key": api_key,
            "x-rapidapi-host": "twelve-data1.p.rapidapi.com"
        }
        params = {
            "symbol": symbol,
            "interval": interval,
            "outputsize": "120",   # Reduced a bit for speed
            "format": "json"
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=12)
        
        if response.status_code != 200:
            st.warning(f"API Error {response.status_code} for {symbol} ({interval})")
            return None
            
        data = response.json()
        
        if "values" not in data:
            st.warning(f"No data returned for {symbol} ({interval}). Response: {data.get('status', 'Unknown')}")
            return None
            
        df = pd.DataFrame(data["values"])
        for col in ['open', 'high', 'low', 'close']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
        df['datetime'] = pd.to_datetime(df['datetime'])
        df = df.sort_values('datetime').reset_index(drop=True)
        
        return apply_tech_logic(df)
        
    except Exception as e:
        st.error(f"Error fetching {symbol} ({interval}): {str(e)}")
        return None

# --- MAIN APP ---
st.markdown("<h1 style='text-align: center; color: white; letter-spacing: 3px;'>⚡ BULL & BEAR TERMINAL</h1>", 
            unsafe_allow_html=True)
st.caption("Professional Multi-Timeframe Technical Analysis Terminal")

assets = {
    "XAU/USD": "GOLD",
    "EUR/USD": "EURUSD",
    "GBP/USD": "GBPUSD",
    "USD/JPY": "USDJPY",
    "BTC/USD": "BITCOIN"
}

# 1. SCANNER (Top Bar)
st.subheader("📡 LIVE SCANNER")
scanner_cols = st.columns(len(assets))

cache_main = {}

for i, (sym, name) in enumerate(assets.items()):
    with scanner_cols[i]:
        with st.spinner(""):
            df = fetch_market_data(sym, "1h")
            if df is not None and not df.empty:
                cache_main[sym] = df
                last = df.iloc[-1]
                
                status = "🔥 TRADE" if last['adx'] > 25 else "⏳ WAIT"
                delta_color = "normal" if last['adx'] > 25 else "off"
                
                st.metric(
                    label=name,
                    value=f"{last['close']:.4f}",
                    delta=status,
                    delta_color=delta_color
                )
            else:
                st.metric(label=name, value="N/A", delta="ERROR")

st.divider()

# 2. ASSET SELECTION & MULTI-TF
sel_asset = st.selectbox("🎯 SELECT ASSET", options=list(assets.keys()), index=0)

st.markdown("### 🚦 MULTI-TIMEFRAME ANALYSIS")
mtf_cols = st.columns(3)
timeframes = ["15min", "1h", "4h"]

for col, tf in zip(mtf_cols, timeframes):
    with col:
        if tf == "1h" and sel_asset in cache_main:
            df_tf = cache_main[sel_asset]
        else:
            df_tf = fetch_market_data(sel_asset, tf)
        
        if df_tf is not None and not df_tf.empty:
            last = df_tf.iloc[-1]
            is_bull = last['close'] > last['ema20']
            trend = "BULL 🐂" if is_bull else "BEAR 🐻"
            
            st.metric(
                label=f"{tf.upper()}",
                value=trend,
                delta=f"ADX: {last['adx']:.1f}"
            )
        else:
            st.metric(label=f"{tf.upper()}", value="NO DATA")

st.divider()

# 3. DETAILED ANALYSIS (1H)
if sel_asset in cache_main:
    df = cache_main[sel_asset]
    last = df.iloc[-1]
    
    st.markdown(f"### 🔍 TECHNICAL BREAKDOWN — {sel_asset} (1H)")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        rsi = last['rsi']
        rsi_status = "OVERBOUGHT ⚠️" if rsi > 70 else "OVERSOLD ✅" if rsi < 30 else "NEUTRAL 👍"
        st.info(f"**RSI (14)**\n\n**{rsi:.1f}** — {rsi_status}")
    
    with col2:
        structure = "BULLISH STRUCTURE" if last['close'] > last['ema20'] else "BEARISH STRUCTURE"
        st.info(f"**TREND STRUCTURE**\n\n{structure}\nEMA20: {last['ema20']:.4f}")
    
    with col3:
        st.info(f"**VOLATILITY (ATR)**\n\n**{last['atr']:.5f}**")
    
    st.divider()
    
    # VERDICT + POSITIONING
    left, right = st.columns([1, 2])
    
    with left:
        st.subheader("🏁 FINAL VERDICT")
        strong_trend = last['adx'] > 25
        bullish = last['close'] > last['ema20']
        
        if strong_trend:
            if bullish:
                st.markdown('<div class="bull-glow">BUY NOW 🚀</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="bear-glow">SELL NOW 📉</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="wait-glow">⏳ WAIT FOR STRONGER TREND</div>', unsafe_allow_html=True)
        
        # Risk Management
        atr_dist = last['atr'] * 2.0
        entry = last['close']
        sl = entry - atr_dist if bullish else entry + atr_dist
        tp = entry + (atr_dist * 3.5) if bullish else entry - (atr_dist * 3.5)
        
        st.markdown(f"""
        **TRADE SETUP**
        - **Entry:** `{entry:.5f}`
        - **Stop Loss:** `{sl:.5f}`
        - **Take Profit:** `{tp:.5f}`
        - **Risk-Reward:** 1:3.5
        """)
    
    with right:
        # Candlestick Chart
        fig = go.Figure(data=[go.Candlestick(
            x=df['datetime'],
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name="OHLC"
        )])
        
        fig.add_trace(go.Scatter(x=df['datetime'], y=df['ema20'],
                                 line=dict(color='#00f2ff', width=2), name="EMA 20"))
        fig.add_trace(go.Scatter(x=df['datetime'], y=df['ema50'],
                                 line=dict(color='#ff00ff', width=1.5), name="EMA 50"))
        
        fig.update_layout(
            template="plotly_dark",
            height=520,
            paper_bgcolor="#05070a",
            plot_bgcolor="#05070a",
            margin=dict(l=0, r=0, t=30, b=0),
            xaxis_rangeslider_visible=False,
            legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
        )
        
        st.plotly_chart(fig, use_container_width=True)

else:
    st.error("⚠️ Could not load data for the selected asset. Please check your API key and connection.")

# Footer
st.caption(f"Last refreshed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Data via Twelve Data")
