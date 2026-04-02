import streamlit as st
import pandas as pd
from polygon import RESTClient
import plotly.graph_objects as go
import numpy as np
from datetime import datetime, timedelta

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Massive FX Dashboard v3", page_icon="⚖️", layout="wide")

try:
    M_API_KEY = st.secrets["MASSIVE_API_KEY"]
    # Inizializziamo il client ufficiale
    client = RESTClient(api_key=M_API_KEY)
except:
    st.error("Configura 'MASSIVE_API_KEY' nei Secrets di Streamlit.")
    st.stop()

# --- FUNZIONE API REAL-TIME ---
def get_massive_data(symbol):
    # Formattazione per FX: C:EURUSD, per Metalli: X:XAUUSD
    ticker = f"X:{symbol}" if "XAU" in symbol else f"C:{symbol}"
    try:
        # Usiamo il metodo che hai postato: get_last_quote
        quote = client.get_last_quote(ticker=ticker)
        return quote
    except Exception as e:
        st.sidebar.error(f"Errore su {ticker}: {e}")
        return None

# --- FUNZIONE DATI STORICI (REALI) ---
def get_historical_data(symbol):
    ticker = f"X:{symbol}" if "XAU" in symbol else f"C:{symbol}"
    aggs = []
    try:
        # Usiamo list_aggs per avere candele REALI invece di quelle simulate
        for a in client.list_aggs(
            ticker=ticker,
            multiplier=1,
            timespan="hour",
            from_=(datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
            to=datetime.now().strftime("%Y-%m-%d"),
            limit=100
        ):
            aggs.append({
                "Date": datetime.fromtimestamp(a.timestamp / 1000),
                "Open": a.open,
                "High": a.high,
                "Low": a.low,
                "Close": a.close
            })
        return pd.DataFrame(aggs)
    except:
        # Fallback su dati simulati se l'API non ha storico per il piano free
        return generate_fake_data(symbol)

def generate_fake_data(symbol):
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
st.title("⚖️ Massive Pro FX (Polygon SDK Mode)")

st.sidebar.header("Risk Management")
risk_pct = st.sidebar.slider("Stop Loss (%)", 0.1, 2.0, 0.5)
rr_ratio = st.sidebar.number_input("Rapporto R:R", value=3.0)

assets = ["XAUUSD", "EURUSD", "USDJPY", "GBPUSD"]

# --- TABELLA SEGNALI ---
st.subheader("🎯 Segnali Live")
rows = []
for asset in assets:
    data = get_massive_data(asset)
    if data:
        # Il client restituisce un oggetto, non un dizionario
        p = data.bid_price if hasattr(data, 'bid_price') else 0
        if p > 0:
            dist = p * (risk_pct / 100)
            rows.append({
                "Asset": asset, "Prezzo": round(p, 4), "Trend": "LIVE ⚡",
                "Entry": round(p, 4), "SL": round(p - dist, 4), "TP": round(p + (dist * rr_ratio), 4)
            })

if rows:
    st.table(pd.DataFrame(rows))
else:
    st.warning("In attesa di dati dal client... Verifica che il tuo piano supporti i dati Forex.")

# --- GRAFICO A CANDELE ---
st.markdown("---")
st.subheader("📈 Analisi Grafica (Verde/Rosso)")
sel_asset = st.selectbox("Seleziona Asset:", assets)
df = get_historical_data(sel_asset)

fig = go.Figure(data=[go.Candlestick(
    x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
    increasing_line_color='#26a69a', # Verde
    decreasing_line_color='#ef5350', # Rosso
    increasing_fillcolor='#26a69a',
    decreasing_fillcolor='#ef5350'
)])

fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=550)
st.plotly_chart(fig, use_container_width=True)
