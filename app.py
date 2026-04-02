import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import numpy as np
from datetime import datetime, timedelta

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Massive FX Dashboard", page_icon="⚖️", layout="wide")

# --- RECUPERO API KEY ---
try:
    M_API_KEY = st.secrets["MASSIVE_API_KEY"]
except Exception:
    st.error("Chiave 'MASSIVE_API_KEY' non trovata nei Secrets di Streamlit.")
    st.stop()

# --- FUNZIONI API ---
def get_massive_data(symbol):
    # Prova a cambiare l'URL se la documentazione di Massive indica un endpoint diverso
    url = f"https://api.massive.com/v1/quotes/{symbol}"
    headers = {"Authorization": f"Bearer {M_API_KEY}"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            # Mostra l'errore specifico se la chiamata fallisce
            st.error(f"Errore API {symbol}: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Errore di connessione: {e}")
        return None

def get_historical_data(symbol):
    """Genera dati storici realistici (con candele rosse e verdi)"""
    np.random.seed(42)
    periods = 60
    dates = [datetime.now() - timedelta(hours=x) for x in range(periods)]
    dates.reverse()
    
    # Simulazione movimento prezzi (Random Walk)
    start_price = 2350.0 if "XAU" in symbol else 1.0850
    prices = [start_price]
    for _ in range(periods - 1):
        prices.append(prices[-1] + np.random.normal(0, start_price * 0.002))
    
    df = pd.DataFrame({'Date': dates, 'Close': prices})
    # Creiamo Open, High, Low basandoci sulla chiusura per avere variazioni reali
    df['Open'] = df['Close'].shift(1).fillna(df['Close'] * 0.999)
    df['High'] = df[['Open', 'Close']].max(axis=1) + (np.random.rand(periods) * (start_price * 0.001))
    df['Low'] = df[['Open', 'Close']].min(axis=1) - (np.random.rand(periods) * (start_price * 0.001))
    
    return df

# --- UI PRINCIPALE ---
st.title("⚖️ Massive Professional Forex Dashboard")
st.sidebar.header("Parametri Risk Management")
risk_pct = st.sidebar.slider("Stop Loss (%)", 0.1, 2.0, 0.5)
rr_ratio = st.sidebar.number_input("Rapporto Rischio/Rendimento (1:X)", value=3.0)

assets = ["XAUUSD", "EURUSD", "USDJPY", "GBPUSD"]

# --- TABELLA SEGNALI ---
st.subheader("🎯 Analisi Trend e Segnali")
rows = []
for asset in assets:
    data = get_massive_data(asset)
    if data and 'price' in data:
        price = float(data['price'])
        change = float(data.get('change_24h', 0))
        
        trend = "BULLISH 🚀" if change >= 0 else "BEARISH 📉"
        sl_dist = price * (risk_pct / 100)
        tp_dist = sl_dist * rr_ratio
        
        sl = price - sl_dist if change >= 0 else price + sl_dist
        tp = price + tp_dist if change >= 0 else price - tp_dist
        
        rows.append({
            "Asset": asset,
            "Prezzo": round(price, 4),
            "Trend": trend,
            "Entry": round(price, 4),
            "Stop Loss": round(sl, 4),
            "Take Profit": round(tp, 4),
            "Var %": f"{change:+.2f}%"
        })

if rows:
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
else:
    st.info("In attesa di risposta valida dall'API Massive... Verifica i simboli o la chiave.")

# --- GRAFICO A CANDELE ---
st.subheader("📈 Visualizzazione Grafica")
target = st.selectbox("Seleziona Asset", assets)
hist_df = get_historical_data(target)

fig = go.Figure(data=[go.Candlestick(
    x=hist_df['Date'],
    open=hist_df['Open'],
    high=hist_df['High'],
    low=hist_df['Low'],
    close=hist_df['Close'],
    increasing_line_color='#26a69a', # Verde
    decreasing_line_color='#ef5350', # Rosso
    increasing_fillcolor='#26a69a',
    decreasing_fillcolor='#ef5350'
)])

fig.update_layout(
    template="plotly_dark",
    xaxis_rangeslider_visible=False,
    height=600,
    margin=dict(l=10, r=10, t=30, b=10)
)

st.plotly_chart(fig, use_container_width=True)
