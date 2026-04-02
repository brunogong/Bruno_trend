import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import pandas_ta as ta  # Libreria per analisi tecnica veloce

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Trend Master Pro", layout="wide")

try:
    API_KEY = st.secrets["X_RAPIDAPI_KEY"]
except:
    st.error("Errore: Inserisci 'X_RAPIDAPI_KEY' nei Secrets.")
    st.stop()

# --- FUNZIONE RECUPERO DATI ---
def get_market_data(symbol, interval="1h"):
    url = "https://twelve-data1.p.rapidapi.com/time_series"
    headers = {"x-rapidapi-key": API_KEY, "x-rapidapi-host": "twelve-data1.p.rapidapi.com"}
    params = {"symbol": symbol, "interval": interval, "outputsize": "100", "format": "json"}
    
    try:
        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        if "values" in data:
            df = pd.DataFrame(data["values"])
            df['datetime'] = pd.to_datetime(df['datetime'])
            for col in ['open', 'high', 'low', 'close']:
                df[col] = pd.to_numeric(df[col])
            # Ordiniamo dal più vecchio al più recente per i calcoli tecnici
            df = df.sort_values('datetime')
            return df
        return None
    except:
        return None

# --- UI ---
st.title("⚖️ Trend Master: Analisi Forza e Livelli")

# Sidebar con lista valute principali
st.sidebar.header("Selezione Mercato")
assets = {
    "ORO (XAU/USD)": "XAU/USD",
    "EUR/USD": "EUR/USD",
    "GBP/USD": "GBP/USD",
    "USD/JPY": "USD/JPY",
    "AUD/USD": "AUD/USD",
    "USD/CAD": "USD/CAD",
    "BTC/USD": "BTC/USD",
    "ETH/USD": "ETH/USD"
}
choice = st.sidebar.selectbox("Asset", list(assets.keys()))
tf = st.sidebar.selectbox("Timeframe", ["15min", "1h", "4h", "1day"], index=1)
rr_ratio = st.sidebar.slider("Rapporto Rischio/Rendimento (TP:SL)", 1.5, 5.0, 3.0)

df = get_market_data(assets[choice], tf)

if df is not None:
    # --- CALCOLO INDICATORI ---
    # Forza del Trend (ADX)
    adx_df = ta.adx(df['high'], df['low'], df['close'], length=14)
    current_adx = adx_df['ADX_14'].iloc[-1]
    
    # Volatilità per SL/TP (ATR)
    atr = ta.atr(df['high'], df['low'], df['close'], length=14).iloc[-1]
    
    # Direzione (Media Mobile 20)
    df['ema20'] = ta.ema(df['close'], length=20)
    last_price = df['close'].iloc[-1]
    is_bullish = last_price > df['ema20'].iloc[-1]

    # --- VALUTAZIONE TREND ---
    if current_adx > 25:
        trend_status = "FORTE 💪"
        trend_color = "inverse" # Verde/Rosso
    elif current_adx < 20:
        trend_status = "DEBOLE/LATERALE 😴"
        trend_color = "off"
    else:
        trend_status = "MODERATO 📈"
        trend_color = "normal"

    # --- CALCOLO LIVELLI OPERATIVI ---
    entry_point = last_price
    # Lo Stop Loss è calcolato come 1.5 volte l'ATR (volatilità media)
    sl_dist = atr * 1.5
    
    if is_bullish:
        direction = "BUY"
        sl = entry_point - sl_dist
        tp = entry_point + (sl_dist * rr_ratio)
    else:
        direction = "SELL"
        sl = entry_point + sl_dist
        tp = entry_point - (sl_dist * rr_ratio)

    # --- VISUALIZZAZIONE DASHBOARD ---
    col1, col2, col3 = st.columns(3)
    col1.metric("Forza Trend (ADX)", f"{current_adx:.2f}", trend_status)
    col2.metric("Direzione", direction, delta_color="normal")
    col3.metric("Prezzo Attuale", f"{last_price:.4f}")

    # Pannello Operativo
    st.markdown(f"### 🎯 Strategia Consigliata: {direction}")
    if current_adx > 25:
        st.success(f"**TREND CONFERMATO:** Il trend è sufficientemente forte per un'operazione.")
    else:
        st.warning("**ATTENZIONE:** Trend debole. Rischio di falsi segnali elevato.")

    o1, o2, o3 = st.columns(3)
    o1.info(f"**ENTRY:** {entry_point:.5f}")
    o2.error(f"**STOP LOSS:** {sl:.5f}")
    o3.success(f"**TAKE PROFIT:** {tp:.5f}")

    # --- GRAFICO ---
    fig = go.Figure(data=[go.Candlestick(
        x=df['datetime'], open=df['open'], high=df['high'],
        low=df['low'], close=df['close'], name="Prezzo"
    )])
    
    # Aggiungiamo la EMA20 al grafico
    fig.add_trace(go.Scatter(x=df['datetime'], y=df['ema20'], line=dict(color='orange', width=1), name="Trend Line"))

    fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=600)
    st.plotly_chart(fig, use_container_width=True)

else:
    st.error("Impossibile caricare i dati. Verifica la chiave API.")
