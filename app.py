import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Professional Trend Dashboard", layout="wide")

# Recupero chiave dai Secrets
try:
    API_KEY = st.secrets["X_RAPIDAPI_KEY"]
except:
    st.error("Errore: Inserisci 'X_RAPIDAPI_KEY' nei Secrets di Streamlit.")
    st.stop()

# --- FUNZIONE RECUPERO DATI (Basata sul tuo curl) ---
def get_ohlc_data(symbol, interval="1day", outputsize="70"):
    url = "https://twelve-data1.p.rapidapi.com/time_series"
    
    headers = {
        "x-rapidapi-key": API_KEY,
        "x-rapidapi-host": "twelve-data1.p.rapidapi.com"
    }
    
    querystring = {
        "symbol": symbol,
        "interval": interval,
        "outputsize": outputsize,
        "format": "json"
    }

    try:
        response = requests.get(url, headers=headers, params=querystring, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if "values" in data:
                df = pd.DataFrame(data["values"])
                # Conversione tipi dati
                df['datetime'] = pd.to_datetime(df['datetime'])
                for col in ['open', 'high', 'low', 'close']:
                    df[col] = pd.to_numeric(df[col])
                return df
            else:
                st.sidebar.warning(f"Messaggio API: {data.get('message', 'Nessun dato')}")
        return None
    except Exception as e:
        st.error(f"Errore connessione: {e}")
        return None

# --- INTERFACCIA UTENTE ---
st.title("⚖️ Pro Trend Analyzer")

# Sidebar
st.sidebar.header("Parametri")
assets = {
    "Oro (XAU/USD)": "XAU/USD",
    "Euro/Dollaro": "EUR/USD",
    "Amazon (AMZN)": "AMZN",
    "Bitcoin (BTC/USD)": "BTC/USD"
}
choice = st.sidebar.selectbox("Asset", list(assets.keys()))
tf = st.sidebar.selectbox("Timeframe", ["1min", "15min", "1h", "1day"], index=3)

# Calcolo segnali
risk_pct = st.sidebar.slider("Distanza SL (%)", 0.1, 2.0, 0.5)

# Recupero Dati
df = get_ohlc_data(assets[choice], tf)

if df is not None and not df.empty:
    # Metriche Live
    last_price = df['close'].iloc[0]
    prev_price = df['close'].iloc[1]
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Prezzo Attuale", f"{last_price:.4f}")
    
    # Logica Segnale
    trend = "BUY 🚀" if last_price > prev_price else "SELL 📉"
    dist = last_price * (risk_pct / 100)
    sl = last_price - dist if trend == "BUY 🚀" else last_price + dist
    
    col2.metric("Trend", trend)
    col3.metric("Suggerimento SL", f"{sl:.4f}")

    # --- GRAFICO CANDLESTICK ---
    st.subheader(f"Analisi Grafica: {choice}")
    fig = go.Figure(data=[go.Candlestick(
        x=df['datetime'],
        open=df['open'], high=df['high'],
        low=df['low'], close=df['close'],
        increasing_line_color='#26a69a',
        decreasing_line_color='#ef5350'
    )])

    fig.update_layout(
        template="plotly_dark",
        xaxis_rangeslider_visible=False,
        height=600,
        margin=dict(t=30, b=10)
    )
    st.plotly_chart(fig, use_container_width=True)
    
else:
    st.info("🔄 In attesa di dati... Assicurati di aver fatto 'Subscribe' al piano Free su RapidAPI.")
