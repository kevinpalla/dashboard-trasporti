import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO
import itertools

def mostra():
    st.title("🚚 Analisi Trasporti Rinfusa - Estero")

    uploaded_file = st.file_uploader("Carica il file Excel con i dati di Rinfusa Conselice", type=["xlsx"])

    if uploaded_file:
        df = pd.read_excel(uploaded_file, sheet_name="RINFUSA CONSELICE")
        df["L DATE"] = pd.to_datetime(df["L DATE"], errors='coerce')
        df["RATE"] = pd.to_numeric(df["RATE"], errors='coerce')
        df = df.dropna(subset=["L DATE"])

        all_carriers = df["CARRIER"].dropna().unique().tolist()
        all_colors = px.colors.qualitative.Alphabet + px.colors.qualitative.Set3 + px.colors.qualitative.Dark24
        if len(all_carriers) > len(all_colors):
            all_colors = list(itertools.islice(itertools.cycle(all_colors), len(all_carriers)))
        color_map = dict(zip(sorted(all_carriers), all_colors))

        st.sidebar.header("🔎 Filtri")
        min_date, max_date = df["L DATE"].min(), df["L DATE"].max()
        date_range = st.sidebar.date_input("Periodo di carico", [min_date, max_date])
        clienti = st.sidebar.multiselect("Cliente", sorted(df["CUSTOMER"].dropna().unique()))
        trasportatori = st.sidebar.multiselect("Trasportatore", sorted(df["CARRIER"].dropna().unique()))

        df_filtered = df[(df["L DATE"] >= pd.to_datetime(date_range[0])) & (df["L DATE"] <= pd.to_datetime(date_range[1]))]
        if clienti:
            df_filtered = df_filtered[df_filtered["CUSTOMER"].isin(clienti)]
        if trasportatori:
            df_filtered = df_filtered[df_filtered["CARRIER"].isin(trasportatori)]

        st.subheader("📈 Totale Viaggi per Mese")
        df_filtered["Mese"] = df_filtered["L DATE"].dt.to_period("M").astype(str)
        viaggi_mensili = df_filtered.groupby("Mese").size().reset_index(name="Totale Viaggi")
        st.plotly_chart(px.bar(viaggi_mensili, x="Mese", y="Totale Viaggi"), use_container_width=True)

        st.subheader("📊 Viaggi per Mese e Trasportatore")
        df_filtered["Anno"] = df_filtered["L DATE"].dt.year
        df_filtered["Mese Solo"] = df_filtered["L DATE"].dt.month
        df_filtered["Mese"] = df_filtered["L DATE"].dt.to_period("M").astype(str)  # ✅ Conversione corretta

        selected_anno = st.selectbox("Seleziona Anno", sorted(df_filtered["Anno"].unique()), index=0)
        selected_mese = st.selectbox("Seleziona Mese", ["Tutti"] + sorted(df_filtered["Mese Solo"].unique()))

        df_vpt = df_filtered[df_filtered["Anno"] == selected_anno]
        if selected_mese != "Tutti":
            df_vpt = df_vpt[df_vpt["Mese Solo"] == int(selected_mese)]

        df_vpt_grouped = df_vpt.groupby(["Mese", "CARRIER"]).size().reset_index(name="Totale Viaggi")
        st.plotly_chart(
            px.bar(
                df_vpt_grouped,
                x="Mese",
                y="Totale Viaggi",
                color="CARRIER",
                barmode="group",
                color_discrete_map=color_map
            ),
            use_container_width=True
        )

        st.subheader("💰 Costi per Cliente")
        costi_cliente = df_filtered.groupby("CUSTOMER")["RATE"].sum().reset_index()
        st.plotly_chart(px.bar(costi_cliente, x="RATE", y="CUSTOMER", orientation="h"), use_container_width=True)

        st.subheader("📊 Performance Trasportatori")
        performance = df_filtered.groupby("CARRIER").agg(
            Viaggi=("CARRIER", "count"),
            Costo_Totale=("RATE", "sum"),
            Costo_Medio=("RATE", "mean")
        ).reset_index()
        performance["Costo_Medio"] = performance["Costo_Medio"].fillna(0).round(0)
        st.dataframe(performance)

        st.subheader("👥 Viaggi per Cliente e Trasportatore")
        viaggi_cliente_carrier = df_filtered.groupby(["CUSTOMER", "CARRIER"]).size().reset_index(name="Numero Viaggi")
        st.dataframe(viaggi_cliente_carrier.sort_values(by=["CUSTOMER", "Numero Viaggi"], ascending=[True, False]))

        st.subheader("📤 Scarica dati filtrati")
        def convert_df(df):
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Filtrati')
            output.seek(0)
            return output

        excel_bytes = convert_df(df_filtered)
        st.download_button("Scarica Excel", data=excel_bytes, file_name="dati_filtrati.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


