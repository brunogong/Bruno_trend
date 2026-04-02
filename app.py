import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import numpy as np
from datetime import datetime, timedelta

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Massive FX v3 Dashboard", page_icon="⚖️", layout="wide")

# Recupero della chiave dai Secrets di Streamlit
try:
    M_API_KEY = st.secrets["MASSIVE_API_KEY"]
except:
    st.error("Errore: Chiave 'MASSIVE_API_KEY' non configurata nei Secrets.")
    st.stop()

# --- LOGICA API ---
def get_massive_data(symbol):
    # Formattazione Ticker per v3/Polygon
    # Per Forex si usa C: (es. C:EURUSD), per Metalli a volte basta il ticker o X:
    tickers_to_try = [f"C:{symbol}", symbol, f"X:{symbol}"] if "XAU" in symbol else [f"C:{symbol}", symbol]
    
    headers = {"Authorization": f"Bearer {M_API_KEY}"}
    
    for ticker in tickers_to_try:
        # Endpoint Last Quote (standard v2/v3)
        url = f"https://api.massive.com/v2/last/forex/{ticker}"
        try:
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data.get('last', data.get('results', data))
        except:
            continue
    return None

# --- GENERAZIONE DATI STORICI (Per il grafico a candele) ---
def get_historical_data(symbol):
    np.random.seed(int(datetime.now().minute))
    periods = 80
    dates = [datetime.now() - timedelta(hours=x) for x in range(periods)]
    dates.reverse()
    
    # Prezzo base dinamico per asset
    start_price = 2350.0 if "XAU" in symbol else 1.0850
    if "JPY" in symbol: start_price = 151.0
    
    prices = [start_price]
    for _ in range(periods - 1):
        # Genera variazioni per creare candele rosse e verdi
        prices.append(prices[-1] + np.random.normal(0, start_price * 0.0015))
    
    df = pd.DataFrame({'Date': dates, 'Close': prices})
    df['Open'] = df['Close'].shift(1).fillna(df['Close'] * 0.998)
    df['High'] = df[['Open', 'Close']].max(axis=1) + (np.random.rand(periods) * (start_price * 0.0008))
    df['Low'] = df[['Open', 'Close']].min(axis=1) - (np.random.rand(periods) * (start_price * 0.0008))
    return df

# --- INTERFACCIA UTENTE ---
st.title("⚖️ Massive Professional FX v3")

# Sidebar per il Risk Management
st.sidebar.header("Parametri Risk")
risk_pct = st.sidebar.slider("Distanza Stop Loss (%)", 0.1, 2.0, 0.5)
rr_ratio = st.sidebar.number_input("Rapporto Rischio/Rendimento (1:X)", value=3.0)

assets = ["XAUUSD", "EURUSD", "USDJPY", "GBPUSD"]

# Sezione Segnali Live
st.subheader("🎯 Segnali Operativi Real-Time")
rows = []

for asset in assets:
    data = get_massive_data(asset)
    if data:
        # Estrazione prezzo (mappa 'p' o 'price' o 'a' per Ask)
        p = float(data.get('p', data.get('price', data.get('a', 0))))
        if p > 0:
            dist = p * (risk_pct / 100)
            rows.append({
                "Asset": asset,
                "Prezzo": round(p, 4),
                "Trend": "LIVE ⚡",
                "Entry": round(p, 4),
                "Stop Loss": round(p - dist, 4),
                "Take Profit": round(p + (dist * rr_ratio), 4)
            })

if rows:
    st.table(pd.DataFrame(rows))
else:
    st.info("🔄 In attesa di dati live... Se vedi ancora errori 404, verifica l'abilitazione del Ticker nel tuo piano API.")

# Sezione Grafico
st.markdown("---")
st.subheader("📈 Analisi Tecnica Candlestick")
sel_asset = st.selectbox("Seleziona Asset da visualizzare:", assets)
h_df = get_historical_data(sel_asset)

fig = go.Figure(data=[go.Candlestick(
    x=h_df['Date'],
    open=h_df['Open'],
    high=h_df['High'],
    low=h_df['Low'],
    close=h_df['Close'],
    increasing_line_color='#26a69a', # Verde
    decreasing_line_color='#ef5350', # Rosso
    increasing_fillcolor='#26a69a',
    decreasing_fillcolor='#ef5350'
)])

fig.update_layout(
    template="plotly_dark",
    xaxis_rangeslider_visible=False,
    height=550,
    margin=dict(t=30, b=10)
)

st.plotly_chart(fig, use_container_width=True)
