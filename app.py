import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import numpy as np
from datetime import datetime, timedelta

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(
    page_title="Massive FX & Gold Dashboard", 
    page_icon="⚖️", 
    layout="wide"
)

# --- RECUPERO API KEY DAI SECRETS ---
try:
    M_API_KEY = st.secrets["MASSIVE_API_KEY"]
except Exception:
    st.error("ERRORE: Chiave 'MASSIVE_API_KEY' non trovata nei Secrets di Streamlit.")
    st.stop()

# --- IMPOSTAZIONI API MASSIVE ---
# Cambia questo URL se la documentazione di Massive indica un percorso diverso
BASE_URL = "https://api.massive.com/v1/quotes" 

def get_massive_data(symbol):
    """
    Recupera i dati real-time. 
    Nota: Alcune API richiedono il simbolo con lo slash (es. XAU/USD)
    """
    url = f"{BASE_URL}/{symbol}"
    headers = {
        "Authorization": f"Bearer {M_API_KEY}",
        "Content-Type": "application/json"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            # Debug visibile per capire l'errore 404
            st.sidebar.error(f"Errore {response.status_code} su {symbol}")
            return None
    except Exception as e:
        st.sidebar.error(f"Errore connessione: {e}")
        return None

def get_historical_data(symbol):
    """Genera dati storici simulati con candele rosse e verdi alternate"""
    np.random.seed(int(datetime.now().timestamp()) % 1000) # Seed variabile
    periods = 60
    dates = [datetime.now() - timedelta(hours=x) for x in range(periods)]
    dates.reverse()
    
    # Prezzo di partenza realistico
    start_price = 2350.0 if "XAU" in symbol else 1.0850
    if "JPY" in symbol: start_price = 151.0
    
    prices = [start_price]
    for _ in range(periods - 1):
        # Movimento casuale per creare trend e ritracciamenti
        move = np.random.normal(0, start_price * 0.0015)
        prices.append(prices[-1] + move)
    
    df = pd.DataFrame({'Date': dates, 'Close': prices})
    # Creazione Open/High/Low per generare candele di entrambi i colori
    df['Open'] = df['Close'].shift(1).fillna(df['Close'] * 0.998)
    df['High'] = df[['Open', 'Close']].max(axis=1) + (np.random.rand(periods) * (start_price * 0.001))
    df['Low'] = df[['Open', 'Close']].min(axis=1) - (np.random.rand(periods) * (start_price * 0.001))
    
    return df

# --- INTERFACCIA UI ---
st.title("⚖️ Massive Professional Forex Dashboard")

# Sidebar per Risk Management
st.sidebar.header("Parametri Risk Management")
risk_pct = st.sidebar.slider("Distanza Stop Loss (%)", 0.1, 2.0, 0.5)
rr_ratio = st.sidebar.number_input("Rapporto Rischio/Rendimento (1:X)", value=3.0)

# Lista Asset - Prova a cambiare formato in "XAU/USD" se ricevi ancora 404
assets = ["XAUUSD", "EURUSD", "USDJPY", "GBPUSD"]

# --- TABELLA SEGNALI ---
st.subheader("🎯 Analisi Trend e Segnali Live")
rows = []

for asset in assets:
    data = get_massive_data(asset)
    
    # Se Massive restituisce dati validi
    if data and 'price' in data:
        price = float(data['price'])
        change = float(data.get('change_24h', 0))
        
        # Logica di trading basata sul trend giornaliero
        trend_label = "BULLISH 🚀" if change >= 0 else "BEARISH 📉"
        
        # Calcolo livelli automatici
        dist = price * (risk_pct / 100)
        entry = price
        
        if change >= 0: # Long
            sl = price - dist
            tp = price + (dist * rr_ratio)
        else: # Short
            sl = price + dist
            tp = price - (dist * rr_ratio)
            
        rows.append({
            "Asset": asset,
            "Prezzo": round(price, 4),
            "Variazione 24h": f"{change:+.2f}%",
            "Trend": trend_label,
            "Entry Point": round(entry, 4),
            "Stop Loss": round(sl, 4),
            "Take Profit": round(tp, 4)
        })

if rows:
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
else:
    st.warning("⚠️ In attesa di dati validi. Se vedi errori 404 nella sidebar, verifica il formato dei simboli (es. XAUUSD vs XAU/USD).")

st.markdown("---")

# --- GRAFICO A CANDELE ---
st.subheader("📈 Visualizzazione Grafica Interna")
selected_asset = st.selectbox("Seleziona Asset da analizzare:", assets)

hist_df = get_historical_data(selected_asset)

fig = go.Figure(data=[go.Candlestick(
    x=hist_df['Date'],
    open=hist_df['Open'],
    high=hist_df['High'],
    low=hist_df['Low'],
    close=hist_df['Close'],
    increasing_line_color='#26a69a', # Verde TradingView
    decreasing_line_color='#ef5350', # Rosso TradingView
    increasing_fillcolor='#26a69a',
    decreasing_fillcolor='#ef5350'
)])

fig.update_layout(
    title=f"Analisi Price Action: {selected_asset}",
    template="plotly_dark",
    xaxis_rangeslider_visible=False,
    height=600,
    margin=dict(l=20, r=20, t=50, b=20)
)

st.plotly_chart(fig, use_container_width=True)

st.caption("I grafici mostrano dati simulati per l'analisi tecnica. I segnali in tabella sono basati su dati Massive.com.")
