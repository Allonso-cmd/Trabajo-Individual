"""
dashboard.py
Dashboard Interactivo - Analisis Geoespacial de Ventas (RM Chile)
Ejecutar con: streamlit run dashboard.py
"""

import warnings
warnings.filterwarnings("ignore")

from pathlib import Path
import json

import streamlit as st
import pandas as pd
import numpy as np
import geopandas as gpd
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns

# ════════════════════════════════════════════════════════
# CONFIGURACION DE PAGINA
# ════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Dashboard Ventas RM",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ════════════════════════════════════════════════════════
# RUTAS DE ARCHIVOS
# ════════════════════════════════════════════════════════
BASE_DIR     = Path(__file__).parent
RUTA_EXCEL   = BASE_DIR / "dataset_tarea_ind.xlsx"
RUTA_GEOJSON = BASE_DIR / "comunas_metropolitana-1.geojson"

# ════════════════════════════════════════════════════════
# CARGA DE DATOS
# ════════════════════════════════════════════════════════
@st.cache_data
def cargar_datos():
    df = pd.read_excel(RUTA_EXCEL)

    def pf(s):
        return s.astype(str).str.strip().str.replace(",", ".", regex=False).astype(float)

    for col in ["venta_neta", "lat", "lng", "kms_dist", "lat_cd", "lng_cd"]:
        df[col] = pf(df[col])

    df["fecha_compra"] = pd.to_datetime(df["fecha_compra"], dayfirst=True)
    df["mes"]          = df["fecha_compra"].dt.month
    df["state"]        = df["state"].str.title()
    return df


@st.cache_data
def cargar_geojson():
    with open(RUTA_GEOJSON, encoding="utf-8") as f:
        return json.load(f)


df_full = cargar_datos()
geojson = cargar_geojson()
CENTRO_RM = [-33.47, -70.65]

# ════════════════════════════════════════════════════════
# SIDEBAR - FILTROS
# ════════════════════════════════════════════════════════
st.sidebar.title("🛒 Filtros")

canales = st.sidebar.multiselect(
    "Canal de venta",
    options=df_full["canal"].unique().tolist(),
    default=df_full["canal"].unique().tolist()
)

comunas_opciones = sorted(df_full["comuna"].unique().tolist())
comunas_sel = st.sidebar.multiselect(
    "Comunas",
    options=comunas_opciones,
    default=comunas_opciones
)

fecha_min = df_full["fecha_compra"].min().date()
fecha_max = df_full["fecha_compra"].max().date()
rango_fecha = st.sidebar.date_input(
    "Periodo",
    value=(fecha_min, fecha_max),
    min_value=fecha_min,
    max_value=fecha_max
)

vr = st.sidebar.slider(
    "Rango Venta Neta (CLP)",
    min_value=int(df_full["venta_neta"].min()),
    max_value=int(df_full["venta_neta"].max()),
    value=(int(df_full["venta_neta"].min()), int(df_full["venta_neta"].max()))
)

# ── Aplicar filtros ──
f_ini = pd.Timestamp(rango_fecha[0]) if len(rango_fecha) == 2 else pd.Timestamp(fecha_min)
f_fin = pd.Timestamp(rango_fecha[1]) if len(rango_fecha) == 2 else pd.Timestamp(fecha_max)

df = df_full[
    df_full["canal"].isin(canales) &
    df_full["comuna"].isin(comunas_sel) &
    df_full["fecha_compra"].between(f_ini, f_fin) &
    df_full["venta_neta"].between(vr[0], vr[1])
]

# ════════════════════════════════════════════════════════
# ENCABEZADO
# ════════════════════════════════════════════════════════
st.title("🗺️ Dashboard de Ventas Geoespaciales – Región Metropolitana")
st.markdown(
    f"**{df.shape[0]:,} órdenes** filtradas &nbsp;|&nbsp; "
    f"Período **{f_ini.date()}** → **{f_fin.date()}**"
)
st.divider()

# ════════════════════════════════════════════════════════
# KPIs
# ════════════════════════════════════════════════════════
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("💰 Venta Total",      f"${df['venta_neta'].sum() / 1e6:.1f} M")
c2.metric("🛒 Órdenes",          f"{df.shape[0]:,}")
c3.metric("🎫 Ticket Promedio",  f"${df['venta_neta'].mean():,.0f}")
c4.metric("📍 Comunas activas",  df["comuna"].nunique())
c5.metric("📦 Unidades totales", f"{df['unidades'].sum():,}")
st.divider()

# ════════════════════════════════════════════════════════
# PESTAÑAS
# ════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Análisis General",
    "🔥 Mapa de Calor",
    "🗺️ Mapa Coroplético",
    "📈 Tendencias"
])

# ─────────────────────────────────────────────────────────
# TAB 1 – ANÁLISIS GENERAL
# ─────────────────────────────────────────────────────────
with tab1:

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Top 10 comunas por venta neta")
        top10 = (
            df.groupby("comuna")["venta_neta"]
              .sum()
              .sort_values(ascending=False)
              .head(10)
        )
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.barh(top10.index[::-1], top10.values[::-1] / 1e6,
                color=sns.color_palette("YlOrRd", 10)[::-1])
        ax.set_xlabel("Venta Neta (MM CLP)")
        ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:.0f}M"))
        plt.tight_layout()
        st.pyplot(fig)
        plt.close()

    with col2:
        st.subheader("Participación por canal")
        cv = df.groupby("canal")["venta_neta"].sum()
        fig2, ax2 = plt.subplots(figsize=(5, 4))
        ax2.pie(
            cv.values,
            labels=cv.index,
            autopct="%1.1f%%",
            colors=["#2196F3", "#FF9800"],
            wedgeprops=dict(edgecolor="white", linewidth=1.5),
            startangle=90
        )
        ax2.set_title("Participación de venta por canal")
        plt.tight_layout()
        st.pyplot(fig2)
        plt.close()

    st.subheader("Distribución de distancia cliente → Centro de Distribución")
    fig3, ax3 = plt.subplots(figsize=(10, 3.5))
    for canal, grp in df.groupby("canal"):
        ax3.hist(grp["kms_dist"], bins=40, alpha=0.55, label=canal, edgecolor="white")
    ax3.set_xlabel("Distancia al CD (km)")
    ax3.set_ylabel("Frecuencia")
    ax3.legend()
    plt.tight_layout()
    st.pyplot(fig3)
    plt.close()

    st.subheader("Tabla resumen por comuna")
    tabla = (
        df.groupby("comuna")
          .agg(
              Venta_Total=("venta_neta", "sum"),
              Ordenes=("orden", "count"),
              Ticket_Prom=("venta_neta", "mean"),
              Unidades=("unidades", "sum"),
              Pct_App=("canal", lambda x: round((x == "App").mean() * 100, 1))
          )
          .sort_values("Venta_Total", ascending=False)
          .reset_index()
    )
    tabla["Venta_Total"] = tabla["Venta_Total"].apply(lambda x: f"${x:,.0f}")
    tabla["Ticket_Prom"] = tabla["Ticket_Prom"].apply(lambda x: f"${x:,.0f}")
    tabla["Pct_App"]     = tabla["Pct_App"].apply(lambda x: f"{x}%")
    st.dataframe(tabla, use_container_width=True)

# ─────────────────────────────────────────────────────────
# TAB 2 – MAPA DE CALOR
# ─────────────────────────────────────────────────────────
with tab2:
    st.subheader("🔥 Mapa de Calor – Intensidad de Ventas")
    st.markdown(
        "Densidad espacial de ventas ponderadas por monto. "
        "Las zonas **rojas** son los hotspots de mayor actividad. "
        "Los marcadores indican los centros de distribución."
    )

    tiles_op = st.radio(
        "Estilo de mapa base",
        ["CartoDB positron", "CartoDB dark_matter", "OpenStreetMap"],
        horizontal=True
    )

    m_heat = folium.Map(location=CENTRO_RM, zoom_start=11, tiles=tiles_op)

    heat_data = (
        df[["lat", "lng", "venta_neta"]]
        .dropna()
        .assign(peso=lambda d: d["venta_neta"] / df_full["venta_neta"].max())
        [["lat", "lng", "peso"]]
        .values.tolist()
    )
    HeatMap(
        heat_data,
        radius=12,
        blur=15,
        max_zoom=13,
        min_opacity=0.3,
        gradient={
            "0.2": "#1a237e",
            "0.4": "#1976D2",
            "0.6": "#43A047",
            "0.8": "#FDD835",
            "1.0": "#D32F2F"
        }
    ).add_to(m_heat)

    cd_coords = df_full.groupby("centro_dist")[["lat_cd", "lng_cd"]].first().reset_index()
    for _, row in cd_coords.iterrows():
        v = df[df["centro_dist"] == row["centro_dist"]]["venta_neta"].sum()
        folium.Marker(
            location=[row["lat_cd"], row["lng_cd"]],
            popup=folium.Popup(
                f"<b>{row['centro_dist']}</b><br>Venta filtrada: ${v:,.0f}",
                max_width=220
            ),
            icon=folium.Icon(color="red", icon="home"),
            tooltip=row["centro_dist"].replace("Centro Distribucion ", "CD ")
        ).add_to(m_heat)

    st_folium(m_heat, width="100%", height=520)

# ─────────────────────────────────────────────────────────
# TAB 3 – MAPA COROPLÉTICO
# ─────────────────────────────────────────────────────────
with tab3:
    st.subheader("🗺️ Mapa Coroplético – Ventas por Zona")

    metrica = st.selectbox(
        "Métrica a visualizar",
        ["Venta Total", "Número de Órdenes", "Ticket Promedio", "% Canal App"]
    )
    col_map = {
        "Venta Total":       "venta_total",
        "Número de Órdenes": "ordenes",
        "Ticket Promedio":   "ticket_prom",
        "% Canal App":       "pct_app"
    }
    col_sel = col_map[metrica]

    stats = (
        df.groupby("comuna")
          .agg(
              venta_total=("venta_neta", "sum"),
              ordenes=("orden", "count"),
              ticket_prom=("venta_neta", "mean"),
              pct_app=("canal", lambda x: (x == "App").mean() * 100)
          )
          .reset_index()
    )

    mc = folium.Map(location=CENTRO_RM, zoom_start=11, tiles="CartoDB positron")

    folium.Choropleth(
        geo_data=geojson,
        data=stats,
        columns=["comuna", col_sel],
        key_on="feature.properties.name",
        fill_color="YlOrRd",
        fill_opacity=0.75,
        line_opacity=0.4,
        legend_name=metrica,
        nan_fill_color="#e0e0e0",
        highlight=True
    ).add_to(mc)

    lookup = stats.set_index("comuna").to_dict("index")
    gj2 = json.loads(json.dumps(geojson))
    for feat in gj2["features"]:
        n = feat["properties"]["name"]
        d = lookup.get(n, {})
        feat["properties"]["venta_total"] = f"${d.get('venta_total', 0):,.0f}"
        feat["properties"]["ordenes"]     = f"{d.get('ordenes', 0):,}"
        feat["properties"]["ticket_prom"] = f"${d.get('ticket_prom', 0):,.0f}"
        feat["properties"]["pct_app"]     = f"{d.get('pct_app', 0):.1f}%"

    folium.GeoJson(
        gj2,
        style_function=lambda x: {
            "fillColor": "transparent",
            "color": "transparent",
            "weight": 0
        },
        tooltip=folium.GeoJsonTooltip(
            fields=["name", "venta_total", "ordenes", "ticket_prom", "pct_app"],
            aliases=["🏘️ Comuna", "💰 Venta", "🛒 Órdenes", "🎫 Ticket", "📱 % App"],
            sticky=True,
            style="font-size:12px;"
        )
    ).add_to(mc)

    for _, row in cd_coords.iterrows():
        folium.CircleMarker(
            location=[row["lat_cd"], row["lng_cd"]],
            radius=7,
            color="#0D47A1",
            fill=True,
            fill_color="#1976D2",
            fill_opacity=0.9,
            tooltip=row["centro_dist"].replace("Centro Distribucion ", "CD ")
        ).add_to(mc)

    folium.LayerControl().add_to(mc)
    st_folium(mc, width="100%", height=520)

    st.subheader(f"Ranking por {metrica}")
    ranking = (
        stats[["comuna", col_sel]]
        .sort_values(col_sel, ascending=False)
        .reset_index(drop=True)
    )
    ranking.index += 1
    st.dataframe(ranking, use_container_width=True)

# ─────────────────────────────────────────────────────────
# TAB 4 – TENDENCIAS
# ─────────────────────────────────────────────────────────
with tab4:
    st.subheader("📈 Evolución Temporal de Ventas")

    agg_sel = st.radio("Granularidad", ["Diario", "Semanal"], horizontal=True)

    if agg_sel == "Diario":
        tmp = (
            df.groupby(["fecha_compra", "canal"])
              .agg(venta=("venta_neta", "sum"), ordenes=("orden", "count"))
              .reset_index()
        )
        xcol = "fecha_compra"
    else:
        df2 = df.copy()
        df2["sem"] = df2["fecha_compra"] - pd.to_timedelta(
            df2["fecha_compra"].dt.dayofweek, unit="D"
        )
        tmp = (
            df2.groupby(["sem", "canal"])
               .agg(venta=("venta_neta", "sum"), ordenes=("orden", "count"))
               .reset_index()
        )
        xcol = "sem"

    fig_t, axes = plt.subplots(2, 1, figsize=(11, 6), sharex=True)
    for canal, grp in tmp.groupby("canal"):
        axes[0].plot(grp[xcol], grp["venta"] / 1e6,
                     marker=".", markersize=3, linewidth=1.2, label=canal)
        axes[1].plot(grp[xcol], grp["ordenes"],
                     marker=".", markersize=3, linewidth=1.2, label=canal)
    axes[0].set_ylabel("Venta Neta (MM CLP)")
    axes[0].set_title("Venta Neta")
    axes[0].legend()
    axes[1].set_ylabel("Órdenes")
    axes[1].set_title("Número de Órdenes")
    axes[1].legend()
    fig_t.autofmt_xdate(rotation=30)
    plt.tight_layout()
    st.pyplot(fig_t)
    plt.close()

    st.subheader("Venta Neta por Comuna y Mes")
    pivot = df.pivot_table(
        index="comuna",
        columns="mes",
        values="venta_neta",
        aggfunc="sum",
        fill_value=0
    )
    pivot.columns = [f"Mes {c}" for c in pivot.columns]
    pivot["Total"] = pivot.sum(axis=1)
    pivot = pivot.sort_values("Total", ascending=False)
    st.dataframe(
        pivot.style.background_gradient(
            cmap="YlOrRd",
            subset=[c for c in pivot.columns if c != "Total"]
        ),
        use_container_width=True
    )

# ════════════════════════════════════════════════════════
# FOOTER
# ════════════════════════════════════════════════════════
st.divider()
st.caption(
    "Dashboard desarrollado con Streamlit · "
    "Datos: Cadena de Comestibles RM (ene–mar 2025) · "
    "Librerías: pandas, geopandas, folium, streamlit-folium, matplotlib, seaborn"
)
