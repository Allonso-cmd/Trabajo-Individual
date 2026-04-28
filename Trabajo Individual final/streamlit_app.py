"""
Streamlit App - Tutorial de Visualizaciones Geoespaciales con Folium
=====================================================================
App de ejemplo basada en el notebook "Unidad 3 - Lab Geoespacial".
Muestra cómo integrar mapas de Folium en Streamlit usando streamlit-folium.

Cómo ejecutar:
    pip install -r requirements.txt
    streamlit run streamlit_app.py

Archivos requeridos en el MISMO directorio que este script:
    - comunas_metropolitana.geojson
    - dataset_lab_3.csv
"""

from pathlib import Path

import folium
import geopandas as gpd
import pandas as pd
import streamlit as st
from folium.plugins import HeatMap
from streamlit_folium import st_folium

# =============================================================================
# Configuración de la página
# =============================================================================
st.set_page_config(
    page_title="Mapas Folium en Streamlit",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded",
)

SANTIAGO_COORDS = [-33.45694, -70.64827]
DATA_DIR = Path(__file__).parent


# =============================================================================
# Carga de datos (cacheada para no releer los archivos en cada rerun)
# =============================================================================
@st.cache_data
def cargar_datos():
    """Lee el GeoJSON de comunas y el CSV de publicaciones inmobiliarias."""
    geojson_path = DATA_DIR / "comunas_metropolitana.geojson"
    csv_path = DATA_DIR / "dataset_lab_3.csv"

    if not geojson_path.exists() or not csv_path.exists():
        return None, None

    comunas = gpd.read_file(geojson_path)
    df = pd.read_csv(csv_path).dropna(subset=["lat", "lng"])
    return comunas, df


comunas_gdf, df = cargar_datos()

if comunas_gdf is None or df is None:
    st.error(
        "⚠️ No encontré los archivos de datos.\n\n"
        "Asegúrate de tener `comunas_metropolitana.geojson` y "
        "`dataset_lab_3.csv` en la misma carpeta que este script."
    )
    st.stop()


# =============================================================================
# Sidebar - Navegación
# =============================================================================
st.sidebar.title("🗺️ Tutorial de Folium")
st.sidebar.markdown(
    "Ejemplos de mapas geoespaciales en **Streamlit** usando `st_folium`."
)

seccion = st.sidebar.radio(
    "Selecciona una sección:",
    [
        "🏠 Introducción",
        "1. Mapa Básico + Tiles",
        "2. Marcadores Simples",
        "3. Marcadores Personalizados",
        "4. Rutas (PolyLine)",
        "5. Polígonos (GeoJSON)",
        "6. Mapa de Calor (HeatMap)",
        "7. Coropletas (Choropleth)",
    ],
)

st.sidebar.markdown("---")
st.sidebar.info(
    "💡 **Tip:** `st_folium` devuelve un diccionario con la interacción del "
    "usuario (click, zoom, bounds). Puedes usarlo para reaccionar desde "
    "Streamlit."
)


# =============================================================================
# 🏠 Introducción
# =============================================================================
if seccion.startswith("🏠"):
    st.title("Tutorial: Mapas de Folium en Streamlit")
    st.markdown(
        """
Este dashboard muestra cómo integrar mapas de **Folium** dentro de una
aplicación **Streamlit** usando el componente `streamlit-folium`.

Está basado en el notebook **Unidad 3 – Lab Geoespacial** y usa los
mismos datos:

- `comunas_metropolitana.geojson` → límites de las comunas de la Región Metropolitana.
- `dataset_lab_3.csv` → publicaciones inmobiliarias con coordenadas, precios (UF),
  comuna, agencia y distancia al metro.

### ¿Cómo se usa `st_folium`?

```python
from streamlit_folium import st_folium
import folium

mapa = folium.Map(location=[-33.45, -70.66], zoom_start=11)
st_folium(mapa, width=700, height=500)
```

Toma un objeto `folium.Map` y lo renderiza de forma **interactiva**.
Además devuelve un diccionario con el estado actual del mapa (última
coordenada clickeada, bounding box visible, zoom, etc.) que puedes usar
para actualizar otras partes de tu app.

### Datos cargados
        """
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("Publicaciones", f"{len(df):,}")
    c2.metric("Comunas (GeoJSON)", len(comunas_gdf))
    c3.metric("Columnas del CSV", df.shape[1])

    st.subheader("Vista previa del dataset")
    st.dataframe(df.head(10), use_container_width=True)


# =============================================================================
# 1. Mapa Básico + Tiles
# =============================================================================
elif seccion.startswith("1."):
    st.title("1. Mapa Básico con Diferentes Tiles")
    st.markdown(
        "El objeto `folium.Map` necesita una ubicación (`location`), un zoom "
        "inicial (`zoom_start`) y un mapa base (`tiles`). Podemos alternar "
        "entre varios tiles agregando `TileLayer` y un `LayerControl`."
    )

    col1, col2 = st.columns(2)
    tile = col1.selectbox(
        "Tile base:",
        ["OpenStreetMap", "CartoDB positron", "CartoDB dark_matter"],
    )
    zoom = col2.slider("Zoom inicial", min_value=8, max_value=15, value=11)

    mapa = folium.Map(location=SANTIAGO_COORDS, zoom_start=zoom, tiles=tile)

    # Agregar las otras capas para poder alternar con el control
    for t in ["OpenStreetMap", "CartoDB positron", "CartoDB dark_matter"]:
        if t != tile:
            folium.TileLayer(t).add_to(mapa)
    folium.LayerControl().add_to(mapa)

    st_folium(mapa, width=None, height=500, returned_objects=[])


# =============================================================================
# 2. Marcadores Simples + captura de click
# =============================================================================
elif seccion.startswith("2."):
    st.title("2. Marcadores Simples")
    st.markdown(
        "Los marcadores (`folium.Marker`) señalan ubicaciones específicas. "
        "Aceptan `popup` (se muestra al hacer clic) y `tooltip` (al pasar el "
        "cursor). \n\n👉 **Haz click en un marcador** para ver lo que devuelve "
        "`st_folium` más abajo — esto es algo que **no puedes hacer** con un "
        "Folium renderizado estáticamente."
    )

    n = st.slider("Cantidad de marcadores", min_value=3, max_value=50, value=10)

    mapa = folium.Map(location=SANTIAGO_COORDS, zoom_start=11)
    for _, row in df.head(n).iterrows():
        folium.Marker(
            location=[row["lat"], row["lng"]],
            popup=(
                f"<strong>{row.get('agencia', 'Propiedad')}</strong><br>"
                f"Comuna: {row.get('comuna', '-')}<br>"
                f"Precio UF: {row.get('precio_uf', '-')}"
            ),
            tooltip=row.get("comuna", "Propiedad"),
        ).add_to(mapa)

    datos_mapa = st_folium(mapa, width=None, height=500)

    # Capturar interacciones (feature clave de st_folium)
    clicked = datos_mapa.get("last_object_clicked") if datos_mapa else None
    if clicked:
        st.success(
            f"📍 Última coordenada clickeada: **{clicked['lat']:.4f}, "
            f"{clicked['lng']:.4f}**"
        )
    else:
        st.caption("Aún no hay click. Haz click en cualquier marcador.")


# =============================================================================
# 3. Marcadores Personalizados
# =============================================================================
elif seccion.startswith("3."):
    st.title("3. Marcadores Personalizados")
    st.markdown(
        "Con `folium.Icon` podemos cambiar color e ícono para diferenciar "
        "categorías (por ejemplo: casa, edificio, info). Los íconos vienen "
        "de **Font Awesome** (`prefix='fa'`) o **Bootstrap Glyphicons** "
        "(`prefix='glyphicon'`)."
    )

    configuraciones = [
        {"idx": 0, "nombre": "Casa", "color": "blue",
         "icon": "home", "prefix": "fa"},
        {"idx": 1, "nombre": "Edificio", "color": "green",
         "icon": "building", "prefix": "fa"},
        {"idx": 2, "nombre": "Info", "color": "purple",
         "icon": "info-sign", "prefix": "glyphicon"},
    ]

    mapa = folium.Map(location=SANTIAGO_COORDS, zoom_start=12)
    for cfg in configuraciones:
        row = df.iloc[cfg["idx"]]
        folium.Marker(
            location=[row["lat"], row["lng"]],
            popup=f"<i>{cfg['nombre']}</i>: {row.get('agencia', '')}",
            tooltip=f"Click para ver {cfg['nombre']}",
            icon=folium.Icon(
                color=cfg["color"],
                icon=cfg["icon"],
                prefix=cfg["prefix"],
            ),
        ).add_to(mapa)

    st_folium(mapa, width=None, height=500, returned_objects=[])


# =============================================================================
# 4. Rutas (PolyLine)
# =============================================================================
elif seccion.startswith("4."):
    st.title("4. Rutas con PolyLine")
    st.markdown(
        "`folium.PolyLine` recibe una lista de coordenadas `(lat, lng)` y "
        "dibuja una línea. Útil para representar trayectos, conexiones o "
        "recorridos logísticos."
    )

    n_puntos = st.slider("Puntos de la ruta", min_value=3, max_value=15, value=5)
    puntos = [
        (df["lat"].iloc[i], df["lng"].iloc[i]) for i in range(n_puntos)
    ]
    puntos.append(puntos[0])  # cerrar el circuito

    mapa = folium.Map(location=SANTIAGO_COORDS, zoom_start=11)
    folium.PolyLine(
        locations=puntos,
        color="red",
        weight=3,
        opacity=0.8,
        tooltip="Ruta de visita",
    ).add_to(mapa)

    for i, p in enumerate(puntos[:-1]):
        folium.Marker(location=p, popup=f"Parada {i + 1}").add_to(mapa)

    st_folium(mapa, width=None, height=500, returned_objects=[])


# =============================================================================
# 5. Polígonos (GeoJSON de comunas)
# =============================================================================
elif seccion.startswith("5."):
    st.title("5. Polígonos desde GeoJSON")
    st.markdown(
        "Con `folium.GeoJson` podemos dibujar directamente los límites de "
        "las comunas de la Región Metropolitana. Activa el toggle para "
        "superponer una muestra de los puntos del dataset."
    )

    mostrar_puntos = st.checkbox("Superponer puntos del dataset", value=False)

    mapa = folium.Map(
        location=SANTIAGO_COORDS, zoom_start=9, tiles="CartoDB positron"
    )

    folium.GeoJson(
        comunas_gdf,
        name="Comunas RM",
        style_function=lambda _: {
            "fillColor": "orange",
            "color": "black",
            "weight": 1,
            "fillOpacity": 0.3,
        },
        tooltip=folium.GeoJsonTooltip(fields=["name"], aliases=["Comuna:"]),
    ).add_to(mapa)

    if mostrar_puntos:
        # Muestreamos para no saturar el navegador
        sample = df.sample(min(500, len(df)), random_state=42)
        for _, row in sample.iterrows():
            folium.CircleMarker(
                location=[row["lat"], row["lng"]],
                radius=2,
                color="blue",
                fill=True,
                fill_color="blue",
                fill_opacity=0.6,
                popup=row.get("comuna", ""),
            ).add_to(mapa)

    st_folium(mapa, width=None, height=550, returned_objects=[])


# =============================================================================
# 6. Mapa de Calor (HeatMap)
# =============================================================================
elif seccion.startswith("6."):
    st.title("6. Mapa de Calor (HeatMap)")
    st.markdown(
        "Los heatmaps (`folium.plugins.HeatMap`) visualizan **densidad**. "
        "Si se agrega un tercer valor por punto, ese valor se interpreta "
        "como **peso** (aquí usamos `precio_uf`)."
    )

    col1, col2 = st.columns(2)
    modo = col1.radio(
        "Modo de visualización:",
        ["Densidad (cantidad)", "Ponderado por precio UF"],
    )
    radius = col2.slider("Radius", min_value=5, max_value=30, value=15)

    mapa = folium.Map(
        location=SANTIAGO_COORDS, zoom_start=10, tiles="CartoDB dark_matter"
    )

    if modo.startswith("Densidad"):
        datos = df[["lat", "lng"]].values.tolist()
    else:
        datos = df[["lat", "lng", "precio_uf"]].dropna().values.tolist()

    HeatMap(datos, radius=radius).add_to(mapa)

    st_folium(mapa, width=None, height=550, returned_objects=[])


# =============================================================================
# 7. Coropletas (Choropleth)
# =============================================================================
elif seccion.startswith("7."):
    st.title("7. Mapa de Coropletas (Choropleth)")
    st.markdown(
        "`folium.Choropleth` colorea cada comuna según una variable "
        "estadística. Cambia la variable abajo para ver cómo se comportan "
        "distintas métricas a nivel de comuna."
    )

    VARIABLES = {
        "distancia_metro_km": "Distancia promedio al metro (km)",
        "precio_uf": "Precio promedio (UF)",
    }
    variable = st.selectbox(
        "Variable por comuna:",
        options=list(VARIABLES.keys()),
        format_func=lambda v: VARIABLES[v],
    )

    # Agregación por comuna
    agrupado = df.groupby("comuna")[variable].mean().reset_index()
    valores_dict = agrupado.set_index("comuna")[variable].to_dict()

    mapa = folium.Map(
        location=SANTIAGO_COORDS, zoom_start=9, tiles="CartoDB positron"
    )

    cp = folium.Choropleth(
        geo_data=comunas_gdf,
        name=variable,
        data=agrupado,
        columns=["comuna", variable],
        key_on="feature.properties.name",
        fill_color="YlOrRd",
        nan_fill_color="white",
        legend_name=VARIABLES[variable],
        highlight=True,
    ).add_to(mapa)

    # Enriquecer el GeoJSON para mostrar el valor en el tooltip
    for feature in cp.geojson.data["features"]:
        comuna = feature["properties"]["name"]
        feature["properties"]["valor"] = round(valores_dict.get(comuna, 0), 2)

    folium.GeoJsonTooltip(
        fields=["name", "valor"],
        aliases=["Comuna:", f"{VARIABLES[variable]}:"],
    ).add_to(cp.geojson)

    st_folium(mapa, width=None, height=600, returned_objects=[])

    with st.expander("📊 Ver tabla de valores por comuna"):
        st.dataframe(
            agrupado.sort_values(variable, ascending=False).reset_index(drop=True),
            use_container_width=True,
        )
