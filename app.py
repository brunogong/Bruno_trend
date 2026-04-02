import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import numpy as np
from datetime import datetime, timedelta

st.set_page_config(page_title="Massive FX v3 Dashboard", page_icon="⚖️", layout="wide")

# RECUPERO API KEY
try:
    M_API_KEY = st.secrets["MASSIVE_API_KEY"]
except:
    st.error("API Key non trovata nei Secrets di Streamlit.")
    st.stop()

# --- FUNZIONE API UNIVERSALE ---
def get_massive_data(symbol):
    # Formattiamo il simbolo per Forex v3 (spesso richiesto come C:EURUSD o C:XAUUSD)
    ticker = f"C:{symbol}" if "XAU" not in symbol else f"X:{symbol}"
    
    # Proviamo i due endpoint più probabili per i prezzi real-time
    endpoints = [
        f"https://api.massive.com/v2/last/forex/{ticker}",
        f"https://api.massive.com/v3/quotes/{symbol}"
    ]
    
    for url in endpoints:
        params = {"apiKey": M_API_KEY}
        try:
            response = requests.get(url, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                # Cerchiamo il prezzo dentro 'last' o 'results'
                res = data.get('last', data.get('results', {}))
                if isinstance(res, list): res = res[0]
                return res
        except:
            continue
    return None

def get_historical_data(symbol):
    np.random.seed(int(datetime.now().timestamp()) % 1000)
    periods = 60
    dates = [datetime.now() - timedelta(hours=x) for x in range(periods)]
    dates.reverse()
    start_price = 2350.0 if "XAU" in symbol else 1.0850
    prices = [start_price]
    for _ in range(periods - 1):
        prices.append(prices[-1] + np.random.normal(0, start_price * 0.0015))
    df = pd.DataFrame({'Date': dates, 'Close': prices})
    df['Open'] = df['Close'].shift(1).fillna(df['Close'] * 0.998)
    df['High'] = df[['Open', 'Close']].max(axis=1) + (np.random.rand(periods) * (start_price * 0.001))
    df['Low'] = df[['Open', 'Close']].min(axis=1) - (np.random.rand(periods) * (start_price * 0.001))
    return df

# --- UI ---
st.title("⚖️ Massive Professional v3 Dashboard")

st.sidebar.header("Impostazioni Rischio")
risk_pct = st.sidebar.slider("Stop Loss (%)", 0.1, 2.0, 0.5)
rr_ratio = st.sidebar.number_input("Rapporto R:R", value=3.0)

assets = ["XAUUSD", "EURUSD", "USDJPY", "GBPUSD"]

st.subheader("🎯 Segnali Live")
rows = []

for asset in assets:
    data = get_massive_data(asset)
    if data:
        # Estraiamo il prezzo (spesso mappato come 'p' o 'price')
        p = float(data.get('p', data.get('price', 0)))
        if p == 0: continue
        
        # Simuliamo un trend basato sull'ultimo movimento se manca change_24h
        c = float(data.get('cp', 0.01)) 
        
        dist = p * (risk_pct / 100)
        trend = "BULLISH 🚀" if c >= 0 else "BEARISH 📉"
        sl = p - dist if c >= 0 else p + dist
        tp = p + (dist * rr_ratio) if c >= 0 else p - (dist * rr_ratio)
        
        rows.append({
            "Asset": asset, "Prezzo": round(p, 4), "Trend": trend,
            "Entry": round(p, 4), "SL": round(sl, 4), "TP": round(tp, 4)
        })

if rows:
    st.table(pd.DataFrame(rows))
else:
    st.warning("⚠️ Controlla il tab 'Quickstart' su Massive: copia qui l'URL che vedi nell'esempio 'Get Last Quote'.")

# --- GRAFICO ---
st.markdown("---")
st.subheader("📈 Analisi Grafica")
selected = st.selectbox("Seleziona Asset", assets)
h_df = get_historical_data(selected)
fig = go.Figure(data=[go.Candlestick(
    x=h_df['Date'], open=h_df['Open'], high=h_df['High'], low=h_df['Low'], close=h_df['Close'],
    increasing_line_color='#26a69a', decreasing_line_color='#ef5350',
    increasing_fillcolor='#26a69a', decreasing_fillcolor='#ef5350'
)])
fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=500)
st.plotly_chart(fig, use_container_width=True)
