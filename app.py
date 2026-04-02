import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import numpy as np

# ========================= CONFIG =========================
st.set_page_config(
    page_title="BULL & BEAR TERMINAL",
    layout="wide",
    initial_sidebar_state="collapsed",
    page_icon="⚡"
)

# CSS Neon Terminal (migliorato)
st.markdown("""
    <style>
    .main { background-color: #05070a; font-family: 'Courier New', Courier, monospace; }
    [data-testid="stMetric"] {
        background-color: #0d1117;
        border: 1px solid #1f2937;
        padding: 18px;
        border-radius: 10px;
    }
    [data-testid="stMetricValue"] { color: #00f2ff !important; font-size: 1.9rem !important; font-weight: bold; }
    [data-testid="stMetricLabel"] { color: #8b949e !important; font-weight: bold; }
    
    .bull-glow { color: #22c55e; text-shadow: 0 0 25px #22c55e; font-size: 34px; font-weight: bold; text-align: center; }
    .bear-glow { color: #ef4444; text-shadow: 0 0 25px #ef4444; font-size: 34px; font-weight: bold; text-align: center; }
    .wait-glow { color: #f59e0b; text-shadow: 0 0 25px #f59e0b; font-size: 34px; font-weight: bold; text-align: center; }
    
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { background-color: #161b22; border-radius: 8px; }
    h1 { letter-spacing: 4px; text-shadow: 0 0 15px #00f2ff; }
    </style>
    """, unsafe_allow_html=True)

# ========================= INDICATORI TECNICI =========================
@st.cache_data(ttl=240)
def apply_tech_logic(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    df = df.copy()
    
    # EMAs
    df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
    
    # RSI
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = -delta.where(delta < 0, 0).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # ATR
    tr = pd.concat([df['high']-df['low'], 
                    abs(df['high']-df['close'].shift()), 
                    abs(df['low']-df['close'].shift())], axis=1).max(axis=1)
    df['atr'] = tr.rolling(14).mean()
    
    # ADX
    up = df['high'].diff()
    down = df['low'].diff()
    plus_dm = np.where((up > down) & (up > 0), up, 0)
    minus_dm = np.where((down > up) & (down > 0), down, 0)
    tr14 = tr.rolling(14).mean()
    plus_di = 100 * pd.Series(plus_dm).rolling(14).mean() / tr14
    minus_di = 100 * pd.Series(minus_dm).rolling(14).mean() / tr14
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di).replace(0, np.nan)
    df['adx'] = dx.rolling(14).mean()
    
    # MACD
    ema12 = df['close'].ewm(span=12, adjust=False).mean()
    ema26 = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = ema12 - ema26
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['macd_hist'] = df['macd'] - df['macd_signal']
    
    # Bollinger Bands
    bb_mid = df['close'].rolling(20).mean()
    bb_std = df['close'].rolling(20).std()
    df['bb_upper'] = bb_mid + 2 * bb_std
    df['bb_lower'] = bb_mid - 2 * bb_std
    df['bb_middle'] = bb_mid
    df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / bb_mid * 100
    
    # Stochastic
    low_min = df['low'].rolling(14).min()
    high_max = df['high'].rolling(14).max()
    df['stoch_k'] = 100 * (df['close'] - low_min) / (high_max - low_min)
    df['stoch_d'] = df['stoch_k'].rolling(3).mean()
    
    return df.dropna().reset_index(drop=True)

# ========================= FETCH DATA =========================
@st.cache_data(ttl=180)
def fetch_market_data(symbol: str, interval: str):
    try:
        api_key = st.secrets.get("X_RAPIDAPI_KEY")
        if not api_key:
            return None
            
        url = "https://twelve-data1.p.rapidapi.com/time_series"
        headers = {"x-rapidapi-key": api_key, "x-rapidapi-host": "twelve-data1.p.rapidapi.com"}
        params = {"symbol": symbol, "interval": interval, "outputsize": "120", "format": "json"}
        
        response = requests.get(url, headers=headers, params=params, timeout=12)
        if response.status_code != 200:
            return None
            
        data = response.json()
        if "values" not in data:
            return None
            
        df = pd.DataFrame(data["values"])
        
        # Parsing colonne (volume incluso quando presente)
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                
        df['datetime'] = pd.to_datetime(df['datetime'])
        df = df.sort_values('datetime').reset_index(drop=True)
        
        return apply_tech_logic(df)
        
    except:
        return None

# ========================= APP =========================
st.markdown("<h1 style='text-align: center; color: white;'>⚡ BULL & BEAR TERMINAL</h1>", unsafe_allow_html=True)
st.caption("Multi-Timeframe • Advanced Indicators • Neon Terminal")

assets = {
    "XAU/USD": "GOLD", 
    "EUR/USD": "EURUSD", 
    "GBP/USD": "GBPUSD", 
    "USD/JPY": "USDJPY", 
    "BTC/USD": "BITCOIN"
}

# ====================== LIVE SCANNER ======================
st.subheader("📡 LIVE SCANNER")
scanner_cols = st.columns(len(assets))
cache_main = {}

for i, (sym, name) in enumerate(assets.items()):
    with scanner_cols[i]:
        df = fetch_market_data(sym, "1h")
        if df is not None and not df.empty:
            cache_main[sym] = df
            last = df.iloc[-1]
            status = "🔥 TRADE" if last['adx'] > 25 else "⏳ WAIT"
            st.metric(
                label=name,
                value=f"{last['close']:.4f}",
                delta=status,
                delta_color="normal" if last['adx'] > 25 else "off"
            )
        else:
            st.metric(label=name, value="N/A", delta="OFFLINE")

st.divider()

# ====================== SELEZIONE ASSET ======================
sel_asset = st.selectbox("🎯 SELEZIONA ASSET", options=list(assets.keys()))

# ====================== TABS ======================
tab1, tab2, tab3 = st.tabs(["🚦 MULTI-TIMEFRAME", "📈 ADVANCED CHART", "📋 INDICATORS TABLE"])

# TAB 1 - MULTI-TIMEFRAME
with tab1:
    st.markdown("### 🚦 MULTI-TIMEFRAME TREND CHECK")
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
                st.metric(label=f"{tf.upper()}", value=trend, delta=f"ADX {last['adx']:.1f}")

# TAB 2 - ADVANCED CHART + VERDICT
with tab2:
    if sel_asset in cache_main:
        df = cache_main[sel_asset]
        last = df.iloc[-1]
        
        col_verdict, col_chart = st.columns([1.1, 2.9])
        
        with col_verdict:
            st.subheader("🏁 FINAL VERDICT")
            strong_trend = last['adx'] > 25
            bullish = last['close'] > last['ema20']
            
            # Confluence Score semplice
            score = 0
            if bullish: score += 25
            if last['rsi'] < 70 and last['rsi'] > 30: score += 15
            if last['macd'] > last['macd_signal']: score += 20
            if last['stoch_k'] > last['stoch_d'] and last['stoch_k'] < 80: score += 20
            if last['close'] > last['bb_middle']: score += 20
            
            if strong_trend and bullish:
                st.markdown('<div class="bull-glow">BUY NOW 🚀</div>', unsafe_allow_html=True)
            elif strong_trend and not bullish:
                st.markdown('<div class="bear-glow">SELL NOW 📉</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="wait-glow">⏳ WAIT FOR CONFLUENCE</div>', unsafe_allow_html=True)
            
            st.progress(score / 100)
            st.caption(f"Confluence Score: **{score}%**")
            
            # Trade Setup
            atr_dist = last['atr'] * 2
            entry = last['close']
            sl = entry - atr_dist if bullish else entry + atr_dist
            tp = entry + (atr_dist * 3.5) if bullish else entry - (atr_dist * 3.5)
            
            st.markdown(f"""
            **TRADE SETUP**
            - **Entry:** `{entry:.5f}`
            - **Stop Loss:** `{sl:.5f}`
            - **Take Profit:** `{tp:.5f}`
            - **R:R** → **1:3.5**
            """)
        
        with col_chart:
            # SUBPLOT CHART
            fig = make_subplots(rows=3, cols=1, 
                                row_heights=[0.55, 0.225, 0.225],
                                vertical_spacing=0.06,
                                shared_xaxes=True)
            
            # Row 1 - Price + Bollinger + EMA
            fig.add_trace(go.Candlestick(x=df['datetime'], open=df['open'], high=df['high'],
                                         low=df['low'], close=df['close'], name="Price"), row=1, col=1)
            fig.add_trace(go.Scatter(x=df['datetime'], y=df['bb_upper'], line=dict(color='#ff00ff', width=1), name="BB Upper"), row=1, col=1)
            fig.add_trace(go.Scatter(x=df['datetime'], y=df['bb_lower'], line=dict(color='#ff00ff', width=1), name="BB Lower"), row=1, col=1)
            fig.add_trace(go.Scatter(x=df['datetime'], y=df['ema20'], line=dict(color='#00f2ff', width=2), name="EMA 20"), row=1, col=1)
            fig.add_trace(go.Scatter(x=df['datetime'], y=df['ema50'], line=dict(color='#ff8800', width=1.5), name="EMA 50"), row=1, col=1)
            
            # Row 2 - MACD
            fig.add_trace(go.Scatter(x=df['datetime'], y=df['macd'], line=dict(color='#00ff88'), name="MACD"), row=2, col=1)
            fig.add_trace(go.Scatter(x=df['datetime'], y=df['macd_signal'], line=dict(color='#ff8800'), name="Signal"), row=2, col=1)
            fig.add_trace(go.Bar(x=df['datetime'], y=df['macd_hist'], name="Histogram", marker_color=np.where(df['macd_hist']>0, '#22c55e', '#ef4444')), row=2, col=1)
            
            # Row 3 - RSI + Stochastic
            fig.add_trace(go.Scatter(x=df['datetime'], y=df['rsi'], line=dict(color='#00f2ff'), name="RSI"), row=3, col=1)
            fig.add_trace(go.Scatter(x=df['datetime'], y=df['stoch_k'], line=dict(color='#22c55e'), name="Stoch %K"), row=3, col=1)
            fig.add_trace(go.Scatter(x=df['datetime'], y=df['stoch_d'], line=dict(color='#ff8800'), name="Stoch %D"), row=3, col=1)
            
            fig.update_layout(
                template="plotly_dark",
                height=680,
                paper_bgcolor="#05070a",
                plot_bgcolor="#05070a",
                margin=dict(l=0, r=0, t=20, b=0),
                xaxis_rangeslider_visible=False,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5)
            )
            
            fig.update_yaxes(title_text="Price", row=1, col=1)
            fig.update_yaxes(title_text="MACD", row=2, col=1)
            fig.update_yaxes(title_text="Oscillators", row=3, col=1)
            
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.error("Dati non disponibili per questo asset.")

# TAB 3 - INDICATORS TABLE
with tab3:
    if sel_asset in cache_main:
        df = cache_main[sel_asset]
        last = df.iloc[-1]
        
        st.markdown("### 📋 INDICATORI ATTUALI")
        
        data_table = {
            "Indicatore": ["EMA20", "EMA50", "RSI (14)", "ADX", "MACD", "Stochastic %K", "Stochastic %D", "BB Width"],
            "Valore": [
                f"{last['ema20']:.4f}",
                f"{last['ema50']:.4f}",
                f"{last['rsi']:.1f}",
                f"{last['adx']:.1f}",
                f"{last['macd']:.5f}",
                f"{last['stoch_k']:.1f}",
                f"{last['stoch_d']:.1f}",
                f"{last['bb_width']:.1f}%"
            ],
            "Segnale": [
                "BULLISH" if last['close'] > last['ema20'] else "BEARISH",
                "BULLISH" if last['close'] > last['ema50'] else "BEARISH",
                "OVERBOUGHT" if last['rsi'] > 70 else "OVERSOLD" if last['rsi'] < 30 else "NEUTRAL",
                "STRONG" if last['adx'] > 25 else "WEAK",
                "BULLISH" if last['macd'] > last['macd_signal'] else "BEARISH",
                "BULLISH" if last['stoch_k'] > last['stoch_d'] else "BEARISH",
                "BULLISH" if last['stoch_k'] > last['stoch_d'] else "BEARISH",
                "EXPANSION" if last['bb_width'] > 2 else "CONTRACTING"
            ]
        }
        
        st.dataframe(pd.DataFrame(data_table), use_container_width=True, hide_index=True)
    else:
        st.warning("Carica prima i dati dell'asset")

st.caption(f"Ultimo aggiornamento: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} | Powered by Twelve Data")
