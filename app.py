import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import numpy as np

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="FX Trend Scanner Pro", layout="wide")

try:
    API_KEY = st.secrets["X_RAPIDAPI_KEY"]
except:
    st.error("Configura X_RAPIDAPI_KEY nei Secrets.")
    st.stop()

# --- FUNZIONI TECNICHE ---
def calculate_indicators(df):
    # EMA per il Trend
    df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
    
    # RSI per ipercomprato/venduto
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # ATR per Volatilità e SL
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['atr'] = tr.rolling(14).mean()
    
    # ADX per Forza Trend
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
    params = {"symbol": symbol, "interval": interval, "outputsize": "100", "format": "json"}
    try:
        res = requests.get(url, headers=headers, params=params)
        data = res.json()
        if "values" in data:
            df = pd.DataFrame(data["values"])
            for col in ['open', 'high', 'low', 'close']: df[col] = pd.to_numeric(df[col])
            df['datetime'] = pd.to_datetime(df['datetime'])
            return calculate_indicators(df.sort_values('datetime'))
    except: return None

# --- LOGICA DI SCANNER ---
assets = {
    "XAU/USD": "Oro", "EUR/USD": "Euro", "GBP/USD": "Sterlina", 
    "USD/JPY": "Yen", "AUD/USD": "Aussie", "BTC/USD": "Bitcoin"
}

st.title("🚀 FX Trend Scanner & Signal Terminal")

# 1. SCANNER IN ALTO
st.subheader("🔍 Market Scanner (Forza Trend)")
cols = st.columns(len(assets))
scanner_results = {}

for i, (sym, name) in enumerate(assets.items()):
    df_mini = fetch_data(sym, "1h")
    if df_mini is not None:
        last = df_mini.iloc[-1]
        adx_val = last['adx']
        # Evidenzia se il trend è forte (>25)
        status = "🔥 FORTE" if adx_val > 25 else "😴 Debole"
        cols[i].metric(sym, f"{last['close']:.2f}", status, delta_color="normal" if adx_val > 25 else "off")
        scanner_results[sym] = df_mini

st.divider()

# 2. DETTAGLIO ASSET SELEZIONATO
sel_asset = st.selectbox("Seleziona Asset per analisi dettagliata", list(assets.keys()))
df = scanner_results.get(sel_asset)

if df is not None:
    last = df.iloc[-1]
    
    # Griglia Indicatori
    st.markdown("### 📊 Indicatori Tecnici")
    ind1, ind2, ind3, ind4 = st.columns(4)
    
    # Segnale EMA
    ema_signal = "BUY" if last['close'] > last['ema20'] else "SELL"
    ind1.info(f"**EMA Trend:** {ema_signal}")
    
    # Segnale RSI
    rsi_val = last['rsi']
    rsi_sig = "IPERCOMPRATO (Vendi)" if rsi_val > 70 else "IPERVENDUTO (Compra)" if rsi_val < 30 else "Neutro"
    ind2.warning(f"**RSI (14):** {rsi_val:.1f}\n\n{rsi_sig}")
    
    # ADX Forza
    ind3.success(f"**ADX Forza:** {last['adx']:.1f}\n\n{'OPERATIVO' if last['adx'] > 25 else 'ATTENDERE'}")
    
    # ATR Volatilità
    ind4.help(f"**ATR (Volatilità):** {last['atr']:.5f}")

    # 3. LIVELLI OPERATIVI (BOX EVIDENZIATO)
    st.subheader("🎯 Piano d'Azione")
    entry = last['close']
    sl_dist = last['atr'] * 1.5
    is_up = last['close'] > last['ema20']
    
    sl = entry - sl_dist if is_up else entry + sl_dist
    tp = entry + (sl_dist * 3) if is_up else entry - (sl_dist * 3)

    st.success(f"**SUGGERIMENTO:** {'APRI LONG (BUY)' if is_up and last['adx'] > 25 else 'APRI SHORT (SELL)' if not is_up and last['adx'] > 25 else 'NON ENTRARE (Trend Debole)'}")
    
    o1, o2, o3 = st.columns(3)
    o1.code(f"ENTRY: {entry:.5f}")
    o2.code(f"STOP LOSS: {sl:.5f}")
    o3.code(f"TAKE PROFIT: {tp:.5f}")

    # 4. GRAFICO PROFESSIONALE
    fig = go.Figure(data=[go.Candlestick(x=df['datetime'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], name="Prezzo")])
    fig.add_trace(go.Scatter(x=df['datetime'], y=df['ema20'], line=dict(color='orange', width=1), name="EMA 20"))
    fig.add_trace(go.Scatter(x=df['datetime'], y=df['ema50'], line=dict(color='cyan', width=1), name="EMA 50"))
    fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=600)
    st.plotly_chart(fig, use_container_width=True)
