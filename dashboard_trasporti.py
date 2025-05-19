import streamlit as st
import pandas as pd

def mostra():
    st.title("📊 Confronto Budget vs Consuntivo 2025")
    st.markdown("Carica i file Excel di budget e consuntivi trasporti (confezionato e rinfusa)")

    # Upload
    budget_file = st.file_uploader("📁 File BUDGET 2025", type=["xlsx"])
    confezionato_file = st.file_uploader("📁 File CONSUNTIVO CONFEZIONATO", type=["xlsx"])
    rinfusa_file = st.file_uploader("📁 File CONSUNTIVO RINFUSA", type=["xlsx"])


    def normalizza_blocchi(df, tipo_trasporto):
        base_labels = [
            'Peso Netto x Consegna (Tons)',
            'Somma di Numero Trasporti',
            'Costo CDG',
            'Somma di Costo CDG Medio per viaggio',
            'Costo €/ton'
        ]
        anni = [2022, 2023, 2024, 2025]
        records = []

        for i, anno in enumerate(anni):
            suffisso = "" if i == 0 else f".{i}"
            cols = [f"{label}{suffisso}" for label in base_labels]

            for _, row in df.iterrows():
                try:
                    records.append({
                        "Anno": anno,
                        "Cliente": row["Desc Cliente"],
                        "Nazione": row["Desc Nazione"],
                        "Italia/Estero": row["ITALIA/ESTERO"],
                        "Peso Netto (tons)": row.get(cols[0], None),
                        "Numero Trasporti": row.get(cols[1], None),
                        "Costo Totale": row.get(cols[2], None),
                        "Costo Medio Viaggio": row.get(cols[3], None),
                        "Costo €/ton": row.get(cols[4], None),
                        "Tipo Trasporto": tipo_trasporto
                    })
                except KeyError:
                    continue
        return pd.DataFrame(records)

    def media_ponderata(df):
        grouped = df.groupby("Nazione").agg({
            "Costo Totale": "sum",
            "Peso Netto (tons)": "sum",
            "Numero Trasporti": "sum"
        }).reset_index()
        grouped["Costo €/ton"] = grouped.apply(
            lambda row: row["Costo Totale"] / row["Peso Netto (tons)"] if row["Peso Netto (tons)"] else None,
            axis=1
        )
        grouped["Numero Trasporti"] = grouped["Numero Trasporti"].fillna(0)
        return grouped[["Nazione", "Numero Trasporti", "Costo €/ton"]]

    def delta_label(val):
        if pd.isna(val):
            return ""
        elif val > 4:
            return "🔴 Alto"
        elif val >= 0:
            return "🟠 Medio"
        else:
            return "🟢 Basso"

    def riordina_colonne(df):
        cols = df.columns.tolist()
        if "Numero Trasporti 2024" in cols:
            cols.remove("Numero Trasporti 2024")
            idx = cols.index("Nazione") + 1
            cols = cols[:idx] + ["Numero Trasporti 2024"] + cols[idx:]
        return df[cols]

    if budget_file and confezionato_file and rinfusa_file:
        try:
            budget_xls = pd.ExcelFile(budget_file)
            budget_rinfusa = pd.read_excel(budget_xls, sheet_name="BUDGET RINFUSA")
            budget_confezionato = pd.read_excel(budget_xls, sheet_name="BUDGET CONFEZIONATO")
            for df, tipo in [(budget_rinfusa, "Rinfusa"), (budget_confezionato, "Confezionato")]:
                df["Tipo Trasporto"] = tipo
                df["Anno"] = 2025
                df["Cliente"] = "BUDGET"
                df["Italia/Estero"] = None
                df["Numero Trasporti"] = None
                df["Costo Totale"] = df["€/Ton 2025"] * df["Tons Budget 2025"]
                df["Costo Medio Viaggio"] = None
                df.rename(columns={
                    "Nazione": "Nazione",
                    "€/Ton 2025": "Costo €/ton",
                    "Tons Budget 2025": "Peso Netto (tons)"
                }, inplace=True)

            budget_df = pd.concat([
                budget_rinfusa, budget_confezionato
            ])[[
                "Anno", "Cliente", "Nazione", "Italia/Estero",
                "Peso Netto (tons)", "Numero Trasporti", "Costo Totale",
                "Costo Medio Viaggio", "Costo €/ton", "Tipo Trasporto"
            ]]

            cons_rinfusa_raw = pd.read_excel(rinfusa_file, sheet_name="RINFUSA", header=4)
            cons_conf_raw = pd.read_excel(confezionato_file, sheet_name="CONFEZIONATO", header=4)
            cons_rinfusa = normalizza_blocchi(cons_rinfusa_raw, "Rinfusa")
            cons_conf = normalizza_blocchi(cons_conf_raw, "Confezionato")
            cons_df = pd.concat([cons_rinfusa, cons_conf], ignore_index=True)

            budget_2025 = budget_df[budget_df["Anno"] == 2025]
            cons_2025 = cons_df[cons_df["Anno"] == 2025]
            cons_2024 = cons_df[cons_df["Anno"] == 2024]

            for tipo, df_budget, df_cons in [("Rinfusa", budget_2025, cons_2025), ("Confezionato", budget_2025, cons_2025)]:
                df_budget_tipo = df_budget[df_budget["Tipo Trasporto"] == tipo]
                df_cons_tipo = df_cons[df_cons["Tipo Trasporto"] == tipo]
                df_merge = pd.merge(
                    media_ponderata(df_cons_tipo).rename(columns={"Costo €/ton": "Costo €/ton _Consuntivo", "Numero Trasporti": "Numero Trasporti Consuntivo"}),
                    media_ponderata(df_budget_tipo).rename(columns={"Costo €/ton": "Costo €/ton _Budget2025"}),
                    on="Nazione", how="right"
                ).dropna(subset=["Costo €/ton _Budget2025"])

                df_merge = df_merge[["Nazione", "Numero Trasporti Consuntivo", "Costo €/ton _Consuntivo", "Costo €/ton _Budget2025"]]
                df_merge["Numero Trasporti Consuntivo"] = df_merge["Numero Trasporti Consuntivo"].fillna(0)
                df_merge = df_merge[~df_merge["Costo €/ton _Budget2025"].isin([float("inf")])]
                df_merge = df_merge[df_merge["Nazione"].str.lower() != "totale"]
                df_merge["Delta"] = df_merge["Costo €/ton _Consuntivo"] - df_merge["Costo €/ton _Budget2025"]
                df_merge["NOTE"] = ""
                df_merge["🟢 Criticità"] = df_merge["Delta"].apply(delta_label)

                nt_2024 = media_ponderata(cons_2024[cons_2024["Tipo Trasporto"] == tipo])[["Nazione", "Numero Trasporti"]]
                nt_2024.rename(columns={"Numero Trasporti": "Numero Trasporti 2024"}, inplace=True)
                df_merge = pd.merge(df_merge, nt_2024, on="Nazione", how="left")
                df_merge = riordina_colonne(df_merge)
                df_merge.fillna(0, inplace=True)

                st.subheader(f"{'🟠' if tipo == 'Rinfusa' else '🔵'} Confronto {tipo.upper()} 2025 per Nazione")
                nazioni = sorted(df_merge["Nazione"].dropna().unique())
                if not st.checkbox(f"✅ Mostra tutte le nazioni {tipo.upper()}", value=True):
                    selezionate = st.multiselect(f"🔍 Seleziona nazioni {tipo.upper()}", options=nazioni, default=nazioni)
                    df_merge = df_merge[df_merge["Nazione"].isin(selezionate)]

                st.data_editor(
                    df_merge[[
                        "Nazione", "Numero Trasporti 2024", "Numero Trasporti Consuntivo",
                        "Costo €/ton _Consuntivo", "Costo €/ton _Budget2025",
                        "Delta", "🟢 Criticità", "NOTE"
                    ]],
                    num_rows="dynamic",
                    use_container_width=True
                )

                st.download_button(f"⬇️ Scarica {tipo.upper()} con NOTE", data=df_merge.to_csv(index=False), file_name=f"{tipo.lower()}_con_note.csv", mime="text/csv")

        except Exception as e:
            st.error("Errore durante l'elaborazione dei file.")
            st.exception(e)
