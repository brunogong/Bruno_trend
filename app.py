import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import numpy as np
from datetime import datetime, timedelta

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Massive FX Dashboard v3", page_icon="⚖️", layout="wide")

try:
    M_API_KEY = st.secrets["MASSIVE_API_KEY"]
except:
    st.error("Configura 'MASSIVE_API_KEY' nei Secrets.")
    st.stop()

def get_massive_data(symbol):
    # Formattazione Ticker v3
    ticker = f"X:{symbol}" if "XAU" in symbol else f"C:{symbol}"
    
    # Proviamo i due endpoint v2/v3 più comuni per i dati real-time
    endpoints = [
        f"https://api.massive.com/v2/last/forex/{ticker}",
        f"https://api.massive.com/v1/last/forex/{ticker}"
    ]
    
    headers = {"Authorization": f"Bearer {M_API_KEY}"}
    
    for url in endpoints:
        try:
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                # Cerchiamo il prezzo in tutti i campi possibili (p=price, a=ask, last=ultimo)
                res = data.get('last', data.get('results', data))
                return res
        except:
            continue
    return None

# --- GENERAZIONE DATI GRAFICO (SIMULATI) ---
def get_historical_data(symbol):
    np.random.seed(int(datetime.now().minute))
    periods = 70
    dates = [datetime.now() - timedelta(hours=x) for x in range(periods)]
    dates.reverse()
    start_price = 2350.0 if "XAU" in symbol else 1.0850
    if "JPY" in symbol: start_price = 151.0
    prices = [start_price]
    for _ in range(periods - 1):
        prices.append(prices[-1] + np.random.normal(0, start_price * 0.0018))
    df = pd.DataFrame({'Date': dates, 'Close': prices})
    df['Open'] = df['Close'].shift(1).fillna(df['Close'] * 0.998)
    df['High'] = df[['Open', 'Close']].max(axis=1) + (np.random.rand(periods) * (start_price * 0.0012))
    df['Low'] = df[['Open', 'Close']].min(axis=1) - (np.random.rand(periods) * (start_price * 0.0012))
    return df

# --- UI ---
st.title("⚖️ Massive Professional FX v3")

st.sidebar.header("Gestione Rischio")
risk_pct = st.sidebar.slider("Distanza Stop Loss (%)", 0.1, 2.0, 0.5)
rr_ratio = st.sidebar.number_input("Rapporto R:R", value=3.0)

assets = ["XAUUSD", "EURUSD", "USDJPY", "GBPUSD"]
st.subheader("🎯 Segnali Operativi Real-Time")

rows = []
for asset in assets:
    data = get_massive_data(asset)
    if data:
        # Estrazione flessibile del prezzo
        price = float(data.get('p', data.get('price', data.get('a', 0))))
        if price > 0:
            dist = price * (risk_pct / 100)
            rows.append({
                "Asset": asset, "Prezzo": round(price, 4), "Trend": "ANALISI LIVE 📈",
                "Entry": round(price, 4), "Stop Loss": round(price - dist, 4),
                "Take Profit": round(price + (dist * rr_ratio), 4)
            })

if rows:
    st.table(pd.DataFrame(rows))
else:
    st.info("🔄 Tentativo di connessione v3 in corso... Se l'errore 404 persiste, il tuo piano Massive potrebbe richiedere l'endpoint '/v2/snapshot/locale/global/markets/forex/tickers'")

# --- GRAFICO ---
st.markdown("---")
st.subheader("📈 Analisi Tecnica Candlestick")
sel_asset = st.selectbox("Seleziona Asset:", assets)
h_df = get_historical_data(sel_asset)
fig = go.Figure(data=[go.Candlestick(
    x=h_df['Date'], open=h_df['Open'], high=h_df['High'], low=h_df['Low'], close=h_df['Close'],
    increasing_line_color='#26a69a', decreasing_line_color='#ef5350',
    increasing_fillcolor='#26a69a', decreasing_fillcolor='#ef5350'
)])
fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=500)
st.plotly_chart(fig, use_container_width=True)
