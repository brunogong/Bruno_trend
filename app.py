import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import numpy as np

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Trend Master Pro", layout="wide")

try:
    API_KEY = st.secrets["X_RAPIDAPI_KEY"]
except:
    st.error("Inserisci X_RAPIDAPI_KEY nei Secrets.")
    st.stop()

# --- FUNZIONI MATEMATICHE (Sostituiscono pandas-ta) ---
def calculate_metrics(df):
    # EMA 20
    df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
    
    # ATR (Volatilità)
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    df['atr'] = true_range.rolling(14).mean()
    
    # ADX semplificato per forza trend
    upmove = df['high'] - df['high'].shift()
    downmove = df['low'].shift() - df['low']
    plus_dm = np.where((upmove > downmove) & (upmove > 0), upmove, 0)
    minus_dm = np.where((downmove > upmove) & (downmove > 0), downmove, 0)
    
    tr_smooth = true_range.rolling(14).mean()
    plus_di = 100 * (pd.Series(plus_dm).rolling(14).mean() / tr_smooth)
    minus_di = 100 * (pd.Series(minus_dm).rolling(14).mean() / tr_smooth)
    dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
    df['adx'] = dx.rolling(14).mean()
    
    return df

def get_data(symbol, interval):
    url = "https://twelve-data1.p.rapidapi.com/time_series"
    headers = {"x-rapidapi-key": API_KEY, "x-rapidapi-host": "twelve-data1.p.rapidapi.com"}
    params = {"symbol": symbol, "interval": interval, "outputsize": "80", "format": "json"}
    try:
        res = requests.get(url, headers=headers, params=params)
        data = res.json()
        if "values" in data:
            df = pd.DataFrame(data["values"])
            df['datetime'] = pd.to_datetime(df['datetime'])
            for col in ['open', 'high', 'low', 'close']:
                df[col] = pd.to_numeric(df[col])
            df = df.sort_values('datetime')
            return calculate_metrics(df)
        return None
    except:
        return None

# --- INTERFACCIA ---
st.sidebar.header("Trading Terminal")
assets = {
    "ORO (XAU/USD)": "XAU/USD", "EUR/USD": "EUR/USD", "GBP/USD": "GBP/USD",
    "USD/JPY": "USD/JPY", "BTC/USD": "BTC/USD", "ETH/USD": "ETH/USD"
}
selected_label = st.sidebar.selectbox("Asset", list(assets.keys()))
tf = st.sidebar.selectbox("Timeframe", ["15min", "1h", "4h", "1day"], index=1)
rr = st.sidebar.slider("Rapporto Rischio/Rendimento", 1.5, 4.0, 2.5)

df = get_data(assets[selected_label], tf)

if df is not None:
    last = df.iloc[-1]
    prev = df.iloc[-2]
    
    # Logica Segnale
    is_bullish = last['close'] > last['ema20']
    strength = "FORTE" if last['adx'] > 25 else "DEBOLE"
    direction = "BUY 🚀" if is_bullish else "SELL 📉"
    
    # Livelli
    entry = last['close']
    sl_dist = last['atr'] * 2
    sl = entry - sl_dist if is_bullish else entry + sl_dist
    tp = entry + (sl_dist * rr) if is_bullish else entry - (sl_dist * rr)

    # Display
    st.subheader(f"📊 {selected_label} - Trend: {strength}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Prezzo", f"{entry:.4f}")
    c2.metric("Forza ADX", f"{last['adx']:.1f}")
    c3.metric("Segnale", direction)

    st.markdown("---")
    st.write("### 🎯 Piano Operativo")
    o1, o2, o3 = st.columns(3)
    o1.info(f"**ENTRY:** {entry:.5f}")
    o2.error(f"**STOP LOSS:** {sl:.5f}")
    o3.success(f"**TAKE PROFIT:** {tp:.5f}")

    # Grafico
    fig = go.Figure(data=[go.Candlestick(x=df['datetime'], open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
    fig.add_trace(go.Scatter(x=df['datetime'], y=df['ema20'], line=dict(color='orange', width=1.5), name="EMA20"))
    fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=500)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Configurazione completata. In attesa di dati da Twelve Data...")
