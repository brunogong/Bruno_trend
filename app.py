import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import numpy as np
from datetime import datetime, timedelta

st.set_page_config(page_title="Massive FX v3 Dashboard", page_icon="⚖️", layout="wide")

# RECUPERO API KEY DAI SECRETS
try:
    M_API_KEY = st.secrets["MASSIVE_API_KEY"]
except:
    st.error("API Key non trovata nei Secrets di Streamlit.")
    st.stop()

# --- FUNZIONE API v3 ---
def get_massive_data(symbol):
    # Basandoci sul tuo link v3, proviamo l'endpoint 'quotes' o 'price'
    # Se 'quotes' non va, prova a cambiare la parola dopo /market/
    url = f"https://api.massive.com/v3/market/quotes"
    
    params = {
        "ticker": symbol,
        "apiKey": M_API_KEY
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # Adattiamo la lettura dei dati in base alla risposta tipica di Massive v3
            # Solitamente restituiscono una lista o un oggetto 'results'
            return data.get('results', data) 
        else:
            st.sidebar.error(f"Errore {response.status_code} su {symbol}")
            return None
    except Exception as e:
        return None

# --- GENERAZIONE GRAFICO (SIMULATO) ---
def get_historical_data(symbol):
    np.random.seed(42)
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

st.subheader("🎯 Segnali Live (Massive v3)")
rows = []

for asset in assets:
    data = get_massive_data(asset)
    # Verifichiamo se 'data' è una lista o un dizionario e prendiamo il prezzo
    if data:
        try:
            # Logica di estrazione basata su standard v3 (può variare leggermente)
            price = float(data[0]['price']) if isinstance(data, list) else float(data.get('price', 0))
            change = float(data[0]['changep']) if isinstance(data, list) else float(data.get('change_24h', 0))
            
            dist = price * (risk_pct / 100)
            trend = "BULLISH 🚀" if change >= 0 else "BEARISH 📉"
            sl = price - dist if change >= 0 else price + dist
            tp = price + (dist * rr_ratio) if change >= 0 else price - (dist * rr_ratio)
            
            rows.append({
                "Asset": asset, "Prezzo": round(price, 4), "Trend": trend,
                "Entry": round(price, 4), "SL": round(sl, 4), "TP": round(tp, 4), "Var %": f"{change:+.2f}%"
            })
        except:
            continue

if rows:
    st.table(pd.DataFrame(rows))
else:
    st.info("Connessione v3 stabilita, ma nessun dato ricevuto per questi ticker. Verifica se Massive usa simboli diversi (es. C:EURUSD).")

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
