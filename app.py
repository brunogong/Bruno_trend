import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Twelve Data FX Dashboard", layout="wide", page_icon="📈")

# --- RECUPERO API KEY ---
# Assicurati di aver inserito 'X_RAPIDAPI_KEY' nei Secrets di Streamlit Cloud
try:
    API_KEY = st.secrets["X_RAPIDAPI_KEY"]
except:
    st.error("ERRORE: Chiave 'X_RAPIDAPI_KEY' non trovata nei Secrets.")
    st.stop()

# --- FUNZIONE RECUPERO DATI ---
def get_twelve_data(symbol, interval="1h"):
    url = "https://twelve-data1.p.rapidapi.com/time_series"
    
    # Twelve Data preferisce il formato con lo slash per il Forex/Gold
    clean_symbol = f"{symbol[:3]}/{symbol[3:]}" if "/" not in symbol else symbol
    
    querystring = {
        "symbol": clean_symbol,
        "interval": interval,
        "outputsize": "78", # Circa una settimana di dati a 1h
        "format": "json"
    }

    headers = {
        "X-RapidAPI-Key": API_KEY,
        "X-RapidAPI-Host": "twelve-data1.p.rapidapi.com"
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
                st.sidebar.error(f"Nota: {data.get('message', 'Errore API')}")
        return None
    except Exception as e:
        st.sidebar.error(f"Errore connessione: {e}")
        return None

# --- INTERFACCIA UTENTE ---
st.title("⚖️ Pro Trend Dashboard")
st.markdown("Analisi tecnica basata su feed real-time **Twelve Data**.")

# Sidebar per parametri tecnici
st.sidebar.header("Parametri Analisi")
assets = ["XAU/USD", "EUR/USD", "USD/JPY", "GBP/USD", "BTC/USD"]
selected_asset = st.sidebar.selectbox("Seleziona Asset", assets)
timeframe = st.sidebar.selectbox("Timeframe", ["5min", "15min", "30min", "1h", "1day"], index=3)

risk_pct = st.sidebar.slider("Distanza SL (%)", 0.1, 2.0, 0.5)
rr_ratio = st.sidebar.number_input("Rapporto Rischio/Rendimento (1:X)", value=3.0)

# --- RECUPERO E VISUALIZZAZIONE ---
df = get_twelve_data(selected_asset, timeframe)

if df is not None and not df.empty:
    # Calcolo Segnali Rapidi
    current_p = df['close'].iloc[0]
    prev_p = df['close'].iloc[1]
    change = ((current_p - prev_p) / prev_p) * 100
    
    # Layout Metriche
    m1, m2, m3 = st.columns(3)
    m1.metric("Prezzo Attuale", f"{current_p:.4f}")
    m2.metric("Variazione Candela", f"{change:+.2f}%", delta_color="normal")
    
    # Calcolo Operatività
    dist = current_p * (risk_pct / 100)
    trend = "BUY 🚀" if current_p > prev_p else "SELL 📉"
    sl = current_p - dist if current_p > prev_p else current_p + dist
    tp = current_p + (dist * rr_ratio) if current_p > prev_p else current_p - (dist * rr_ratio)
    
    m3.info(f"Segnale: **{trend}**")

    # --- TABELLA LIVE ---
    st.subheader("🎯 Livelli Operativi")
    ops_df = pd.DataFrame({
        "Entry": [round(current_p, 5)],
        "Stop Loss": [round(sl, 5)],
        "Take Profit": [round(tp, 5)],
        "Target Pips/Points": [round(abs(tp - current_p), 5)]
    })
    st.table(ops_df)

    # --- GRAFICO A CANDELE ---
    st.subheader(f"📈 Grafico Intraday: {selected_asset}")
    
    fig = go.Figure(data=[go.Candlestick(
        x=df['datetime'],
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        increasing_line_color='#26a69a', # Verde TradingView
        decreasing_line_color='#ef5350', # Rosso TradingView
        name="Price Action"
    )])

    fig.update_layout(
        template="plotly_dark",
        xaxis_rangeslider_visible=False,
        height=600,
        margin=dict(l=10, r=10, t=30, b=10),
        yaxis_title="Prezzo"
    )

    st.plotly_chart(fig, use_container_width=True)
    
else:
    st.warning("⚠️ Impossibile recuperare i dati. Controlla la tua API Key su RapidAPI e assicurati di aver sottoscritto il piano gratuito di Twelve Data.")

st.caption("Dati forniti da Twelve Data API via RapidAPI. I segnali sono puramente indicativi.")
