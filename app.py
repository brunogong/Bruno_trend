import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import pandas_ta as ta

# Configurazione Dashboard
st.set_page_config(page_title="Trading Signal Pro", layout="wide")

# API Key dai Secrets
try:
    API_KEY = st.secrets["X_RAPIDAPI_KEY"]
except:
    st.error("Configura X_RAPIDAPI_KEY nei Secrets di Streamlit.")
    st.stop()

def get_data(symbol, interval):
    url = "https://twelve-data1.p.rapidapi.com/time_series"
    headers = {"x-rapidapi-key": API_KEY, "x-rapidapi-host": "twelve-data1.p.rapidapi.com"}
    params = {"symbol": symbol, "interval": interval, "outputsize": "100", "format": "json"}
    try:
        res = requests.get(url, headers=headers, params=params)
        data = res.json()
        if "values" in data:
            df = pd.DataFrame(data["values"])
            df['datetime'] = pd.to_datetime(df['datetime'])
            for col in ['open', 'high', 'low', 'close']:
                df[col] = pd.to_numeric(df[col])
            return df.sort_values('datetime')
        return None
    except:
        return None

# --- UI SIDEBAR ---
st.sidebar.header("Selezione Mercato")
# Lista Valute Principali (Major) e Oro
assets = {
    "ORO (XAU/USD)": "XAU/USD",
    "EUR/USD": "EUR/USD",
    "GBP/USD": "GBP/USD",
    "USD/JPY": "USD/JPY",
    "USD/CHF": "USD/CHF",
    "AUD/USD": "AUD/USD",
    "USD/CAD": "USD/CAD",
    "NZD/USD": "NZD/USD"
}
selected_label = st.sidebar.selectbox("Asset", list(assets.keys()))
symbol = assets[selected_label]
tf = st.sidebar.selectbox("Timeframe", ["15min", "1h", "4h", "1day"], index=1)
rr = st.sidebar.slider("Rapporto Rischio/Rendimento", 1.5, 4.0, 2.5)

df = get_data(symbol, tf)

if df is not None:
    # Calcoli Tecnici
    df['EMA20'] = ta.ema(df['close'], length=20)
    adx = ta.adx(df['high'], df['low'], df['close'], length=14)
    current_adx = adx['ADX_14'].iloc[-1]
    atr = ta.atr(df['high'], df['low'], df['close'], length=14).iloc[-1]
    
    last_price = df['close'].iloc[-1]
    is_bullish = last_price > df['EMA20'].iloc[-1]
    
    # Valutazione Forza
    strength = "FORTE" if current_adx > 25 else "DEBOLE (Attendere)"
    
    # Livelli Operativi
    direction = "BUY" if is_bullish else "SELL"
    sl_distance = atr * 2  # Usiamo 2 volte l'ATR per uno Stop Loss sicuro
    sl = last_price - sl_distance if is_bullish else last_price + sl_distance
    tp_distance = sl_distance * rr
    tp = last_price + tp_distance if is_bullish else last_price - tp_distance

    # Display Metriche
    st.subheader(f"Analisi {selected_label} - Trend {strength}")
    m1, m2, m3 = st.columns(3)
    m1.metric("Prezzo", f"{last_price:.4f}")
    m2.metric("ADX (Forza)", f"{current_adx:.2f}", strength)
    m3.metric("Direzione", direction)

    st.markdown("---")
    st.write("### 📍 Piano d'Azione")
    o1, o2, o3 = st.columns(3)
    o1.info(f"**ENTRY:** {last_price:.5f}")
    o2.error(f"**STOP LOSS:** {sl:.5f}")
    o3.success(f"**TAKE PROFIT:** {tp:.5f}")

    # Grafico
    fig = go.Figure(data=[go.Candlestick(x=df['datetime'], open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
    fig.add_trace(go.Scatter(x=df['datetime'], y=df['EMA20'], line=dict(color='yellow', width=1), name="Trend Line (EMA20)"))
    fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=500)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("Caricamento dati in corso o limite API raggiunto...")
