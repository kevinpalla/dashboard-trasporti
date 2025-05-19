import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO
import itertools
import urllib.parse

# Deve essere prima di tutto il resto di Streamlit
st.set_page_config(page_title="Analisi Trasporti Rinfusa", layout="wide")

def mostra():
    st.title("🚛 Analisi Trasporti Rinfusa - Estero")

    sheet_id = "1kv_VPHDtE1DDmGfLKtRmyNACfcIulr6p"
    sheet_name = "RINFUSA CONSELICE"
    encoded_name = urllib.parse.quote(sheet_name)
    sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={encoded_name}"

    try:
        df = pd.read_csv(sheet_url)
        df.columns = df.columns.str.strip()
        df["L DATE"] = pd.to_datetime(df["L DATE"], errors='coerce')
        df["RATE"] = pd.to_numeric(df["RATE"], errors='coerce')
        df = df.dropna(subset=["L DATE"])
    except Exception as e:
        st.error("Errore nel caricamento dei dati dal Google Sheet.")
        st.exception(e)
        st.stop()

    all_carriers = df["CARRIER"].dropna().unique().tolist()
    all_colors = px.colors.qualitative.Alphabet + px.colors.qualitative.Set3 + px.colors.qualitative.Dark24
    if len(all_carriers) > len(all_colors):
        all_colors = list(itertools.islice(itertools.cycle(all_colors), len(all_carriers)))
    color_map = dict(zip(sorted(all_carriers), all_colors))

    st.sidebar.header("🔍 Filtri")
    min_date, max_date = df["L DATE"].min(), df["L DATE"].max()
    date_range = st.sidebar.date_input("Periodo di carico", [min_date, max_date])
    clienti = st.sidebar.multiselect("Cliente", options=sorted(df["CUSTOMER"].dropna().unique()), default=None)
    trasportatori = st.sidebar.multiselect("Trasportatore", options=sorted(df["CARRIER"].dropna().unique()), default=None)

    df_filtered = df[(df["L DATE"] >= pd.to_datetime(date_range[0])) & (df["L DATE"] <= pd.to_datetime(date_range[1]))]
    if clienti:
        df_filtered = df_filtered[df_filtered["CUSTOMER"].isin(clienti)]
    if trasportatori:
        df_filtered = df_filtered[df_filtered["CARRIER"].isin(trasportatori)]

    st.subheader("📅 Totale Viaggi per Mese")
    df_filtered["Mese"] = df_filtered["L DATE"].dt.to_period("M").astype(str)
    viaggi_mensili = df_filtered.groupby("Mese").size().reset_index(name="Totale Viaggi")
    fig1 = px.bar(viaggi_mensili, x="Mese", y="Totale Viaggi")
    st.plotly_chart(fig1, use_container_width=True)

    st.subheader("📦 Totale Viaggi per Mese per Trasportatore")
    df_filtered["Anno"] = df_filtered["L DATE"].dt.year
    df_filtered["Mese Solo"] = df_filtered["L DATE"].dt.month
    selected_anno = st.selectbox("Seleziona Anno", sorted(df_filtered["Anno"].unique()), index=0)
    selected_mese = st.selectbox("Seleziona Mese", options=["Tutti"] + sorted(df_filtered["Mese Solo"].unique()))
    df_vpt = df_filtered[df_filtered["Anno"] == selected_anno]
    if selected_mese != "Tutti":
        df_vpt = df_vpt[df_vpt["Mese Solo"] == int(selected_mese)]
    df_vpt_grouped = df_vpt.groupby(["Mese", "CARRIER"]).size().reset_index(name="Totale Viaggi")
    fig_vpt = px.bar(df_vpt_grouped, x="Mese", y="Totale Viaggi", color="CARRIER", barmode="group", color_discrete_map=color_map)
    st.plotly_chart(fig_vpt, use_container_width=True)

    st.subheader("💰 Costi di Trasporto per Cliente")
    costi_cliente = df_filtered.groupby("CUSTOMER")["RATE"].sum().reset_index()
    fig2 = px.bar(costi_cliente, x="RATE", y="CUSTOMER", orientation="h")
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("📈 Performance Trasportatori")
    performance = df_filtered.groupby("CARRIER").agg(
        Viaggi=("CARRIER", "count"),
        Costo_Totale=("RATE", "sum"),
        Costo_Medio=("RATE", "mean")
    ).reset_index()
    performance["Costo_Medio"] = performance["Costo_Medio"].fillna(0).round(0)
    st.dataframe(performance)

    st.subheader("👥 Viaggi per Cliente e Trasportatore")
    viaggi_cliente_carrier = df_filtered.groupby(["CUSTOMER", "CARRIER"]).size().reset_index(name="Numero Viaggi")
    viaggi_cliente_carrier = viaggi_cliente_carrier.sort_values(by=["CUSTOMER", "Numero Viaggi"], ascending=[True, False])
    st.dataframe(viaggi_cliente_carrier)

    st.subheader("📤 Scarica Dati Filtrati")
    def convert_df(df):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Filtrati')
        output.seek(0)
        return output

    excel_bytes = convert_df(df_filtered)
    st.download_button(
        label="Scarica Excel",
        data=excel_bytes,
        file_name="dati_filtrati.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
