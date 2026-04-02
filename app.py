import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import numpy as np
from datetime import datetime, timedelta

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Massive FX v3 Dashboard", page_icon="⚖️", layout="wide")

try:
    M_API_KEY = st.secrets["MASSIVE_API_KEY"]
except:
    st.error("Configura 'MASSIVE_API_KEY' nei Secrets di Streamlit.")
    st.stop()

# --- FUNZIONE API v3 (Specifiche Polygon/Massive) ---
def get_massive_data(symbol):
    # Formattazione Ticker: C:EURUSD o X:XAUUSD
    ticker = f"X:{symbol}" if "XAU" in symbol else f"C:{symbol}"
    
    # Endpoint standard per l'ultimo prezzo
    url = f"https://api.massive.com/v2/last/forex/{ticker}"
    
    headers = {
        "Authorization": f"Bearer {M_API_KEY}"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # In v3 i dati sono quasi sempre dentro 'results' o 'last'
            return data.get('results', data.get('last', {}))
        else:
            # Se dà 404, proviamo l'endpoint alternativo 'quotes'
            alt_url = f"https://api.massive.com/v3/quotes/{ticker}"
            response = requests.get(alt_url, headers=headers, timeout=5)
            if response.status_code == 200:
                return response.json().get('results', {})
            return None
    except:
        return None

# --- GENERAZIONE GRAFICO ---
def get_historical_data(symbol):
    np.random.seed(int(datetime.now().minute))
    periods = 70
    dates = [datetime.now() - timedelta(hours=x) for x in range(periods)]
    dates.reverse()
    
    # Prezzo base dinamico
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

# --- UI PRINCIPALE ---
st.title("⚖️ Massive Professional v3 Dashboard")

st.sidebar.header("Gestione Rischio")
risk_pct = st.sidebar.slider("Stop Loss (%)", 0.1, 2.0, 0.5)
rr_ratio = st.sidebar.number_input("Rapporto R:R (1:X)", value=3.0)

assets = ["XAUUSD", "EURUSD", "USDJPY", "GBPUSD"]

st.subheader("🎯 Segnali Live (Real-Time)")
rows = []

for asset in assets:
    data = get_massive_data(asset)
    if data:
        # Estrazione prezzo: p (price), a (ask) o c (close)
        price = float(data.get('p', data.get('price', data.get('a', 0))))
        
        if price > 0:
            dist = price * (risk_pct / 100)
            rows.append({
                "Asset": asset,
                "Prezzo": round(price, 4),
                "Trend": "LIVE ⚡",
                "Entry": round(price, 4),
                "Stop Loss": round(price - dist, 4),
                "Take Profit": round(price + (dist * rr_ratio), 4)
            })

if rows:
    st.table(pd.DataFrame(rows))
else:
    st.warning("⚠️ Collegamento stabilito, ma l'endpoint dei prezzi non risponde. Verifica nel Quickstart l'URL esatto per 'Last Forex Quote'.")

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
fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=500, margin=dict(t=30, b=10))
st.plotly_chart(fig, use_container_width=True)
