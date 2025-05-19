import streamlit as st
import app_mappa
import budget_consuntivo
import rinfusa_estero

st.set_page_config(page_title="Dashboard Trasporti", layout="wide")

st.sidebar.title("Navigazione")
pagina = st.sidebar.radio("Vai a:", ["Mappa dei clienti UNIGRA'", "Confronto Budget vs Consuntivo 2025", "Analisi Trasporti Rinfusa - Estero"])

if pagina == "Mappa dei clienti UNIGRA'":
    app_mappa.mostra()
elif pagina == "Confronto Budget vs Consuntivo 2025":
    budget_consuntivo.mostra()
elif pagina == "Analisi Trasporti Rinfusa - Estero":
    rinfusa_estero.mostra()
