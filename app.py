import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import numpy as np
from datetime import datetime, timedelta

st.set_page_config(page_title="Massive FX Dashboard", page_icon="⚖️", layout="wide")

# RECUPERO API KEY
try:
    M_API_KEY = st.secrets["MASSIVE_API_KEY"]
except:
    st.error("API Key non trovata nei Secrets.")
    st.stop()

# FUNZIONE DI TEST ENDPOINT
def get_massive_data(symbol):
    # Proviamo i 3 formati più comuni se il primo fallisce
    formats = [symbol, symbol.replace("USD", "/USD"), symbol.replace("USD", "_USD")]
    
    headers = {"Authorization": f"Bearer {M_API_KEY}"}
    
    for fmt in formats:
        # Tenta con l'endpoint standard. Se Massive usa un percorso diverso, 
        # prova a cambiare 'quotes' con 'price' o 'market' qui sotto
        url = f"https://api.massive.com/v1/quotes/{fmt}"
        try:
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                return response.json()
        except:
            continue
    
    # Se arriva qui, ha fallito tutti i formati
    return None

def get_historical_data(symbol):
    np.random.seed(int(datetime.now().minute))
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

# UI
st.title("⚖️ Massive Professional Forex Dashboard")

st.sidebar.header("Parametri Risk")
risk_pct = st.sidebar.slider("Stop Loss (%)", 0.1, 2.0, 0.5)
rr_ratio = st.sidebar.number_input("Rapporto R:R (1:X)", value=3.0)

# LISTA ASSET
assets = ["XAUUSD", "EURUSD", "USDJPY", "GBPUSD"]

st.subheader("🎯 Segnali Live")
rows = []
for asset in assets:
    data = get_massive_data(asset)
    if data and 'price' in data:
        p = float(data['price'])
        c = float(data.get('change_24h', 0))
        dist = p * (risk_pct / 100)
        trend = "BULLISH 🚀" if c >= 0 else "BEARISH 📉"
        sl = p - dist if c >= 0 else p + dist
        tp = p + (dist * rr_ratio) if c >= 0 else p - (dist * rr_ratio)
        
        rows.append({
            "Asset": asset, "Prezzo": round(p, 4), "Trend": trend,
            "Entry": round(p, 4), "SL": round(sl, 4), "TP": round(tp, 4), "Var %": f"{c:+.2f}%"
        })

if rows:
    st.table(pd.DataFrame(rows))
else:
    st.error("Ancora errore 404. Controlla la scheda 'Keys | Massive' e cerca l'URL corretto dell'API.")

st.markdown("---")
st.subheader("📈 Grafico Analisi")
selected = st.selectbox("Asset", assets)
h_df = get_historical_data(selected)
fig = go.Figure(data=[go.Candlestick(
    x=h_df['Date'], open=h_df['Open'], high=h_df['High'], low=h_df['Low'], close=h_df['Close'],
    increasing_line_color='#26a69a', decreasing_line_color='#ef5350',
    increasing_fillcolor='#26a69a', decreasing_fillcolor='#ef5350'
)])
fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=500)
st.plotly_chart(fig, use_container_width=True)
