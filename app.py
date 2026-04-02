import streamlit as st
import pandas as pd

# 1. Configurazione della pagina
st.set_page_config(
    page_title="Trading Dashboard",
    page_icon="📈",
    layout="wide"
)

# 2. Intestazione e Disclaimer
st.title("📊 Dashboard Operativa Forex & Commodities")
st.warning("""
**Disclaimer:** I dati presentati in questa dashboard hanno scopo puramente illustrativo e didattico. 
Non costituiscono in alcun modo consigli di investimento o sollecitazioni al trading. 
Il trading comporta un alto livello di rischio.
""")

# 3. Creazione del DataFrame con i segnali
st.subheader("Setup Suggeriti (Dati Demo)")

data = {
    "Asset": ["XAUUSD (Oro)", "USDJPY", "EURUSD", "GBPUSD"],
    "Trend Attuale": ["📉 Correzione Ribassista", "📈 Forte Rialzo", "📉 Forte Ribasso", "📉 Ribassista"],
    "Setup": ["Short (Sell Stop)", "Long (Buy)", "Short (Sell)", "Short (Sell)"],
    "Entry Point": ["< 4.605,00", "~ 159,40", "~ 1.1528", "< 1.3210"],
    "Take Profit (TP)": ["4.275,00", "161,00", "1.1450", "1.3100"],
    "Stop Loss (SL)": ["4.740,00", "158,50", "1.1605", "1.3320"]
}

df = pd.DataFrame(data)

# Mostra la tabella a tutto schermo
st.dataframe(df, use_container_width=True, hide_index=True)

# 4. Sezione Analisi e Contesto
st.markdown("---")
st.subheader("📝 Contesto Macro e Analisi Tecnica")

col1, col2 = st.columns(2)

with col1:
    st.info("**XAUUSD:** Dopo una corsa sfrenata, l'oro subisce prese di beneficio. Una rottura del supporto a 4.605 apre al ribasso. *Piano B:* Se consolida sopra 4.855,00, si invalida lo short e si valuta un long verso 4.995,00.")
    st.info("**EURUSD & GBPUSD:** Il dollaro domina su tutti i principali incroci. Le valute europee faticano a tenere i supporti chiave in attesa dei dati USA sull'occupazione.")

with col2:
    st.success("**USDJPY:** Trazione schiacciante del biglietto verde contro lo yen. I differenziali di rendimento confermano il trend rialzista di fondo.")
    st.error("**Risk Management:** Ricorda di calcolare la size della posizione in base ai pips di Stop Loss. Rischia al massimo l'1-2% del tuo capitale per trade.")
    
# Footer
st.markdown("---")
st.caption("Aggiornato al: 2 Aprile 2026 | Sviluppato con Streamlit 🎈")
