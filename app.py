import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(
    page_title="Massive FX & Gold Dashboard",
    page_icon="⚖️",
    layout="wide"
)

# --- RECUPERO API KEY DAI SECRETS ---
# Assicurati di aver aggiunto MASSIVE_API_KEY nei Secrets di Streamlit Cloud
try:
    M_API_KEY = st.secrets["MASSIVE_API_KEY"]
except Exception:
    st.error("ERRORE: API Key non trovata. Configura 'MASSIVE_API_KEY' nei Secrets di Streamlit.")
    st.stop()

# --- FUNZIONI DI SUPPORTO ---
def get_massive_data(symbol):
    """Recupera il prezzo attuale e la variazione da Massive.com"""
    url = f"https://api.massive.com/v1/quotes/{symbol}"
    headers = {"Authorization": f"Bearer {M_API_KEY}"}
    try:
        response = requests.get(url, headers=headers)
        return response.json()
    except:
        return None

def get_historical_data(symbol):
    """Recupera i dati storici per il grafico (Simulazione per il layout)"""
    # Nota: Qui andrebbe la chiamata all'endpoint 'history' di Massive
    # Per ora generiamo dati dummy per mostrare il funzionamento del grafico
    import numpy as np
    dates = pd.date_range(end=datetime.now(), periods=50)
    close_prices = np.random.uniform(low=1.0, high=1.1, size=50) if "USD" in symbol else np.random.uniform(2300, 2400, 50)
    df = pd.DataFrame({
        'Date': dates,
        'Open': close_prices * 0.99,
        'High': close_prices * 1.01,
        'Low': close_prices * 0.98,
        'Close': close_prices
    })
    return df

# --- INTERFACCIA UTENTE (UI) ---
st.title("⚖️ Massive Professional Forex Dashboard")
st.markdown(f"Aggiornato al: `{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}`")

# Sidebar per il Risk Management
st.sidebar.header("Parametri di Rischio")
risk_pct = st.sidebar.slider("Distanza Stop Loss (%)", 0.1, 2.0, 0.5, help="Percentuale dal prezzo di entry per lo SL")
rr_ratio = st.sidebar.number_input("Rapporto Rischio/Rendimento (1:X)", value=3.0)

# Lista Asset
assets = ["XAUUSD", "EURUSD", "USDJPY", "GBPUSD", "AUDUSD"]

# --- TABELLA PRINCIPALE ---
st.subheader("🎯 Segnali e Livelli Operativi")
rows = []

for asset in assets:
    data = get_massive_data(asset)
    if data:
        price = float(data.get('price', 0))
        change = float(data.get('change_24h', 0))
        
        # Logica Trend
        trend = "BULLISH 🚀" if change > 0 else "BEARISH 📉"
        
        # Calcolo Livelli
        sl_dist = price * (risk_pct / 100)
        tp_dist = sl_dist * rr_ratio
        
        sl = price - sl_dist if change > 0 else price + sl_dist
        tp = price + tp_dist if change > 0 else price - tp_dist
        
        rows.append({
            "Asset": asset,
            "Prezzo": round(price, 4),
            "Variazione 24h": f"{change:.2f}%",
            "Trend": trend,
            "Entry Point": round(price, 4),
            "Stop Loss": round(sl, 4),
            "Take Profit": round(tp, 4)
        })

if rows:
    df_display = pd.DataFrame(rows)
    st.table(df_display)
else:
    st.warning("In attesa di dati dall'API...")

st.markdown("---")

# --- SEZIONE GRAFICI ---
st.subheader("📈 Analisi Grafica")
selected_asset = st.selectbox("Seleziona un asset per visualizzare il grafico:", assets)

hist_df = get_historical_data(selected_asset)

fig = go.Figure(data=[go.Candlestick(
    x=hist_df['Date'],
    open=hist_df['Open'],
    high=hist_df['High'],
    low=hist_df['Low'],
    close=hist_df['Close'],
    increasing_line_color='#26a69a', decreasing_line_color='#ef5350'
)])

fig.update_layout(
    title=f"Andamento Temporale {selected_asset}",
    yaxis_title="Prezzo",
    template="plotly_dark",
    xaxis_rangeslider_visible=False,
    height=500
)

st.plotly_chart(fig, use_container_width=True)

st.caption("Nota: I grafici mostrano dati simulati. Collega l'endpoint 'history' di Massive per dati reali.")
