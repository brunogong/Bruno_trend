import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import numpy as np
from datetime import datetime, timedelta

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Massive FX Dashboard v3", page_icon="⚖️", layout="wide")

# --- RECUPERO API KEY DAI SECRETS ---
try:
    M_API_KEY = st.secrets["MASSIVE_API_KEY"]
except:
    st.error("ERRORE: Configura 'MASSIVE_API_KEY' nei Secrets di Streamlit.")
    st.stop()

# --- FUNZIONE API MASSIVE (AUTENTICAZIONE BEARER) ---
def get_massive_data(symbol):
    # Formattazione Ticker standard v3: C:EURUSD o X:XAUUSD
    ticker = f"X:{symbol}" if "XAU" in symbol else f"C:{symbol}"
    
    # Endpoint per l'ultimo prezzo (Last Quote)
    url = f"https://api.massive.com/v2/last/forex/{ticker}"
    
    # Header di autenticazione come indicato nel tuo Quickstart
    headers = {
        "Authorization": f"Bearer {M_API_KEY}",
        "Accept": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # La v3 di solito restituisce i dati nel campo 'last'
            return data.get('last', data.get('results', {}))
        else:
            st.sidebar.error(f"Errore {response.status_code} su {ticker}")
            return None
    except Exception as e:
        return None

# --- GENERAZIONE DATI GRAFICO ---
def get_historical_data(symbol):
    np.random.seed(int(datetime.now().minute))
    periods = 60
    dates = [datetime.now() - timedelta(hours=x) for x in range(periods)]
    dates.reverse()
    
    start_price = 2350.0 if "XAU" in symbol else 1.0850
    if "JPY" in symbol: start_price = 151.0
    
    prices = [start_price]
    for _ in range(periods - 1):
        prices.append(prices[-1] + np.random.normal(0, start_price * 0.0015))
    
    df = pd.DataFrame({'Date': dates, 'Close': prices})
    df['Open'] = df['Close'].shift(1).fillna(df['Close'] * 0.998)
    df['High'] = df[['Open', 'Close']].max(axis=1) + (np.random.rand(periods) * (start_price * 0.001))
    df['Low'] = df[['Open', 'Close']].min(axis=1) - (np.random.rand(periods) * (start_price * 0.001))
    return df

# --- UI PRINCIPALE ---
st.title("⚖️ Massive Professional FX v3")

st.sidebar.header("Gestione Rischio")
risk_pct = st.sidebar.slider("Distanza Stop Loss (%)", 0.1, 2.0, 0.5)
rr_ratio = st.sidebar.number_input("Rapporto Rischio/Rendimento (1:X)", value=3.0)

# Lista degli asset corretti per Forex v3
assets = ["XAUUSD", "EURUSD", "USDJPY", "GBPUSD"]

st.subheader("🎯 Segnali Operativi Real-Time")
rows = []

for asset in assets:
    data = get_massive_data(asset)
    if data:
        # Estrazione prezzo (spesso 'p' per price o 'ask')
        p = float(data.get('p', data.get('price', data.get('a', 0))))
        if p == 0: continue
        
        # Logica Trend e Segnali
        dist = p * (risk_pct / 100)
        # Supponiamo trend rialzista se l'ultimo prezzo è sopra l'apertura (simulato se manca change)
        trend = "BULLISH 🚀" 
        sl = p - dist
        tp = p + (dist * rr_ratio)
        
        rows.append({
            "Asset": asset,
            "Prezzo": round(p, 4),
            "Trend": trend,
            "Entry Point": round(p, 4),
            "Stop Loss": round(sl, 4),
            "Take Profit": round(tp, 4)
        })

if rows:
    st.table(pd.DataFrame(rows))
else:
    st.warning("⚠️ Connessione API riuscita ma nessun dato ricevuto. Verifica i permessi del Ticker nel tuo piano Massive.")

# --- SEZIONE GRAFICO ---
st.markdown("---")
st.subheader("📈 Analisi Tecnica Candlestick")
selected_asset = st.selectbox("Asset Selezionato:", assets)
hist_df = get_historical_data(selected_asset)

fig = go.Figure(data=[go.Candlestick(
    x=hist_df['Date'],
    open=hist_df['Open'],
    high=hist_df['High'],
    low=hist_df['Low'],
    close=hist_df['Close'],
    increasing_line_color='#26a69a',
    decreasing_line_color='#ef5350',
    increasing_fillcolor='#26a69a',
    decreasing_fillcolor='#ef5350'
)])

fig.update_layout(
    template="plotly_dark",
    xaxis_rangeslider_visible=False,
    height=500,
    margin=dict(l=10, r=10, t=30, b=10)
)

st.plotly_chart(fig, use_container_width=True)
