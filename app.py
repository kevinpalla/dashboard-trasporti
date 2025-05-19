import streamlit as st
import app_mappa
import dashboard_trasporti
import rinfusaestero

st.set_page_config(page_title="Dashboard Trasporti", layout="wide")

st.sidebar.title("Navigazione")
pagina = st.sidebar.radio("Vai a:", ["Mappa dei clienti UNIGRA'", "Confronto Budget vs Consuntivo 2025", "Analisi Trasporti Rinfusa - Estero"])

if pagina == "Mappa dei clienti UNIGRA'":
    app_mappa.mostra()
elif pagina == "Confronto Budget vs Consuntivo 2025":
    dashboard_trasporti.mostra()
elif pagina == "Analisi Trasporti Rinfusa - Estero":
    rinfusaestero.mostra()
