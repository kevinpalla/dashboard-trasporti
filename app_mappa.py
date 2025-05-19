import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import Draw
from shapely.geometry import Point, Polygon
from io import BytesIO
import zipfile
from PIL import ImageGrab
import plotly.express as px

def mostra():
    st.title("🗺️ Mappa dei clienti UNIGRA'")

    uploaded_file = st.file_uploader("📁 Carica il file Excel", type=["xlsx"])

    if uploaded_file:
        xls = pd.ExcelFile(uploaded_file)
        sheet = st.selectbox("Scegli il foglio", xls.sheet_names)
        df = pd.read_excel(xls, sheet_name=sheet, dtype={"CAP": str})

        df.columns = df.columns.str.strip().str.upper()
        required = {"CLIENTE", "CAP", "SOMMA TRASPORTI", "LAT", "LON"}
        if not required.issubset(df.columns):
            st.error("⚠️ Il file deve contenere le colonne: CLIENTE, CAP, SOMMA TRASPORTI, LAT, LON")
            st.stop()

        df["SOMMA TRASPORTI"] = pd.to_numeric(df["SOMMA TRASPORTI"], errors="coerce")
        df = df.dropna(subset=["LAT", "LON", "SOMMA TRASPORTI"])

        center_lat, center_lon = df["LAT"].mean(), df["LON"].mean()

        colors = ["red", "blue", "green", "purple", "orange", "darkred", "lightblue", "darkgreen"]
        zone_assignments = {}
        polygons = []

        m = folium.Map(location=[center_lat, center_lon], zoom_start=6, tiles="CartoDB positron")
        draw = Draw(
            export=False,
            edit_options={"edit": True, "remove": True},
            draw_options={
                "rectangle": True,
                "polygon": True,
                "circle": False,
                "marker": False,
                "polyline": False
            })
        draw.add_to(m)

        for _, row in df.iterrows():
            folium.CircleMarker(
                location=[row["LAT"], row["LON"]],
                radius=5,
                color="gray",
                fill=True,
                fill_color="gray",
                fill_opacity=0.6,
                tooltip=f"{row['CLIENTE']} - {row['CAP']} - {int(row['SOMMA TRASPORTI'])}"
            ).add_to(m)

        col1, col2 = st.columns([6, 1])
        with col1:
            map_data = st_folium(m, width=1300, height=700, returned_objects=["all_drawings"])

        if map_data and map_data.get("all_drawings"):
            polygons_raw = map_data["all_drawings"]
            for shape in polygons_raw:
                geom = shape.get("geometry")
                if geom and geom["type"] == "Polygon":
                    coords = geom["coordinates"][0]
                    polygon_points = [(lat, lon) for lon, lat in coords]
                    polygons.append(Polygon(polygon_points))

        if polygons:
            st.markdown("### 📋 Clienti suddivisi per zona")

            zip_buffer = BytesIO()
            pie_data = []
            color_map = {}

            with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED) as zip_file:
                for i, poly in enumerate(polygons):
                    df_zone = df[df.apply(lambda row: poly.contains(Point(row["LAT"], row["LON"])), axis=1)]
                    st.markdown(f"#### ZONA {i+1} - {len(df_zone)} clienti")
                    if df_zone.empty:
                        st.write("Nessun cliente in questa zona.")
                    else:
                        total = df_zone["SOMMA TRASPORTI"].sum()
                        st.write(f"**Totale trasporti:** {int(total):,}")
                        st.dataframe(df_zone[["CLIENTE", "CAP", "SOMMA TRASPORTI"]].sort_values(by="SOMMA TRASPORTI", ascending=False))

                        csv_bytes = df_zone.to_csv(index=False).encode("utf-8")
                        zip_file.writestr(f"zona_{i+1}.csv", csv_bytes)

                        zona_label = f"Zona {i+1}"
                        pie_data.append((zona_label, total))
                        color_map[zona_label] = colors[i % len(colors)]

                        for _, row in df_zone.iterrows():
                            zone_assignments[(row["LAT"], row["LON"])] = colors[i % len(colors)]

            m = folium.Map(location=[center_lat, center_lon], zoom_start=6, tiles="CartoDB positron")
            for _, row in df.iterrows():
                coord = (row["LAT"], row["LON"])
                color = zone_assignments.get(coord, "gray")
                folium.CircleMarker(
                    location=[row["LAT"], row["LON"]],
                    radius=6,
                    color=color,
                    fill=True,
                    fill_color=color,
                    fill_opacity=0.9,
                    tooltip=f"{row['CLIENTE']} - {row['CAP']} - {int(row['SOMMA TRASPORTI'])}"
                ).add_to(m)

            for i, shape in enumerate(polygons_raw):
                coords = shape["geometry"]["coordinates"]
                if isinstance(coords[0], list):
                    polygon_coords = [(lat, lon) for lon, lat in coords[0]]
                else:
                    polygon_coords = [(coords[1], coords[0])]
                folium.Polygon(
                    locations=polygon_coords,
                    color=colors[i % len(colors)],
                    weight=2,
                    fill=False
                ).add_to(m)

            st.markdown("### 🧭 Legenda colori zone")
            for i, color in enumerate(colors[:len(polygons)]):
                st.markdown(f"<span style='color:{color};font-weight:bold;'>■ Zona {i+1}</span>", unsafe_allow_html=True)

            st.markdown("### 🗺️ Mappa aggiornata con zone")
            st_folium(m, width=1400, height=800)

            st.markdown("### 📊 Distribuzione dei trasporti per zona")
            if pie_data:
                pie_df = pd.DataFrame(pie_data, columns=["Zona", "Totale Trasporti"])
                fig = px.pie(
                    pie_df,
                    values="Totale Trasporti",
                    names="Zona",
                    title="Distribuzione per Zona",
                    color="Zona",
                    color_discrete_map=color_map
                )
                st.plotly_chart(fig)

                try:
                    img_pie = fig.to_image(format="png")
                    st.download_button("📥 Scarica grafico a torta (PNG)", data=img_pie, file_name="grafico_torta.png", mime="image/png")
                except Exception as e:
                    st.warning(f"⚠️ Errore durante l'esportazione dell'immagine: {e}")

            st.download_button("📥 Scarica CSV per zone (ZIP)", data=zip_buffer.getvalue(), file_name="zone_clienti.zip", mime="application/zip")

            st.markdown("### 📷 Esporta mappa in JPEG")
            st.warning("⚠️ Funziona solo in locale con PIL.ImageGrab")
            if st.button("📸 Esporta mappa visibile in JPEG"):
                try:
                    img = ImageGrab.grab()
                    buf = BytesIO()
                    img.save(buf, format="JPEG")
                    st.download_button("📥 Scarica JPEG", data=buf.getvalue(), file_name="mappa.jpeg", mime="image/jpeg")
                except Exception as e:
                    st.error(f"Errore durante l'acquisizione dello screenshot: {e}")
        else:
            st.markdown("### 📋 Clienti suddivisi per zona")
            st.info("Disegna una o più aree sulla mappa per visualizzare i clienti associati.")
