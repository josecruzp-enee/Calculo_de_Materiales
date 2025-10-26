# -*- coding: utf-8 -*-
from __future__ import annotations
import os, io, time, tempfile
import pandas as pd
import streamlit as st

# ========= Helpers =========
def _resumen_por_punto(df_largo: pd.DataFrame) -> pd.DataFrame:
    grp = (df_largo.groupby(["Punto", "codigodeestructura"], as_index=False)["cantidad"]
           .sum().sort_values(["Punto","codigodeestructura"]))
    # normalizar tipos
    grp["Punto"] = grp["Punto"].astype(str).str.strip()
    grp["codigodeestructura"] = grp["codigodeestructura"].astype(str).str.strip()
    grp["cantidad"] = pd.to_numeric(grp["cantidad"], errors="coerce").fillna(1).astype(int)
    return grp

def _html_descripcion(sub: pd.DataFrame) -> str:
    rows = "".join(
        f"<tr><td>{r['codigodeestructura']}</td><td style='text-align:right'>{int(r['cantidad'])}</td></tr>"
        for _, r in sub.iterrows()
    )
    return f"""
    <![CDATA[
      <h4>Estructuras del Punto</h4>
      <table border="1" cellspacing="0" cellpadding="3">
        <tr><th>Estructura</th><th>Cantidad</th></tr>
        {rows}
      </table>
    ]]>"""

def _ordenar_puntos_series(s: pd.Series) -> pd.Series:
    # intenta ordenar por número si el valor parece "12" o "12.0"
    def _key(x):
        sx = str(x).strip()
        try:
            return int(float(sx))
        except Exception:
            return sx
    return s.map(_key)

def _crear_kmz(df_puntos: pd.DataFrame, df_largo: pd.DataFrame, dibujar_linea: bool = True) -> str:
    """
    Genera un .kmz en /tmp y devuelve la ruta.
    Requiere: simplekml
    """
    import simplekml, zipfile

    # Normalizar entradas
    df_pts = df_puntos.copy()
    df_pts["Punto"] = df_pts["Punto"].astype(str).str.strip()
    df_pts["lat"] = pd.to_numeric(df_pts["lat"], errors="coerce")
    df_pts["lon"] = pd.to_numeric(df_pts["lon"], errors="coerce")
    df_pts = df_pts.dropna(subset=["lat","lon"])

    df_res = _resumen_por_punto(df_largo)

    kml = simplekml.Kml()

    # Iconos (puedes cambiarlos por los tuyos)
    ICON_PUNTO = "http://maps.google.com/mapfiles/kml/paddle/red-circle.png"
    ICON_TRAFO = "http://maps.google.com/mapfiles/kml/shapes/parks.png"

    folder_proj = kml.newfolder(name="Proyecto - Puntos")

    # Para la línea entre puntos
    coords_linea = []

    # Orden estable por 'Punto'
    for _, row in df_pts.sort_values("Punto", key=_ordenar_puntos_series).iterrows():
        p = str(row["Punto"]).strip()
        lat, lon = float(row["lat"]), float(row["lon"])
        coords_linea.append((lon, lat))

        sub = df_res[df_res["Punto"] == p]
        f = folder_proj.newfolder(name=f"Punto {p}")

        pm = f.newpoint(name=f"Punto {p}", coords=[(lon, lat)])
        pm.style.iconstyle.icon.href = ICON_PUNTO
        pm.description = _html_descripcion(sub)

        # Poner un icono adicional si hay transformador
        if any(sub["codigodeestructura"].str.contains(r"\bTS|TD|TR\b", case=False, regex=True)):
            pt = f.newpoint(name=f"Transformador (Punto {p})", coords=[(lon, lat)])
            pt.style.iconstyle.icon.href = ICON_TRAFO

    if dibujar_linea and len(coords_linea) >= 2:
        ls = kml.newlinestring(name="Tendido (orden por Punto)")
        ls.coords = coords_linea
        ls.style.linestyle.width = 3

    # Guardar como .kml primero
    tmp_dir = tempfile.gettempdir()
    kml_path = os.path.join(tmp_dir, f"proyecto_{int(time.time())}.kml")
    kml.save(kml_path)

    # Empaquetar .kmz (zip del kml)
    kmz_path = os.path.join(tmp_dir, f"proyecto_{int(time.time())}.kmz")
    with zipfile.ZipFile(kmz_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.write(kml_path, arcname="doc.kml")

    # Limpieza opcional del kml intermedio (no estricta)
    try:
        os.remove(kml_path)
    except Exception:
        pass

    return kmz_path

# ========= UI principal =========
def seccion_mapa_kmz():
    st.header("🌍 KMZ para Google Earth")

    # 1) Tomar estructuras desde session_state (formato LARGO)
    df_largo = st.session_state.get("df_estructuras_compacto")
    if not isinstance(df_largo, pd.DataFrame) or df_largo.empty:
        st.info("Primero arma tus estructuras. Necesito un DF con columnas: Punto, codigodeestructura, cantidad.")
        return

    # Normalizar columnas esperadas
    need_cols = {"Punto","codigodeestructura","cantidad"}
    if not need_cols.issubset({c.strip() for c in df_largo.columns}):
        st.error(f"Faltan columnas en estructuras: {need_cols}. Revisa la sección de estructuras.")
        return

    st.caption(f"Detecté {df_largo['Punto'].nunique()} punto(s).")
    with st.expander("Ver primeras filas de estructuras (largo)"):
        st.dataframe(df_largo.head(15), use_container_width=True, hide_index=True)

    # 2) Cargar CSV de coordenadas
    st.subheader("1) Cargar coordenadas de puntos (CSV: Punto,lat,lon)")
    upl = st.file_uploader("Sube puntos.csv", type=["csv"])
    ejemplo = st.toggle("Ver ejemplo CSV", value=False)
    if ejemplo:
        demo = pd.DataFrame({"Punto":[1,2,3],"lat":[14.08712,14.08655,14.08597],"lon":[-87.20153,-87.19990,-87.19822]})
        st.dataframe(demo, hide_index=True, use_container_width=True)
        st.download_button("Descargar ejemplo CSV", demo.to_csv(index=False).encode("utf-8"), "puntos_ejemplo.csv", "text/csv")

    if not upl:
        st.stop()

    try:
        df_pts = pd.read_csv(upl)
    except Exception as e:
        st.error(f"No pude leer el CSV: {e}")
        st.stop()

    need_pts = {"Punto","lat","lon"}
    if not need_pts.issubset({c.strip() for c in df_pts.columns}):
        st.error("El CSV debe tener columnas exactas: Punto, lat, lon (WGS84).")
        st.stop()

    # Normaliza tipos
    df_pts["Punto"] = df_pts["Punto"].astype(str).str.strip()
    df_largo["Punto"] = df_largo["Punto"].astype(str).str.strip()

    # Chequeos
    faltan = sorted(set(df_largo["Punto"]) - set(df_pts["Punto"]))
    if faltan:
        st.warning(f"Puntos sin coordenadas: {faltan} (no aparecerán en el KMZ).")

    # (Opcional) Vista rápida en mapa con folium
    if st.toggle("Previsualizar en mapa (opcional)", value=False):
        try:
            import folium
            from streamlit_folium import st_folium
            center = [df_pts["lat"].astype(float).mean(), df_pts["lon"].astype(float).mean()]
            m = folium.Map(location=center, zoom_start=14)
            for _, r in df_pts.iterrows():
                folium.Marker(
                    location=[float(r["lat"]), float(r["lon"])],
                    tooltip=f"Punto {r['Punto']}"
                ).add_to(m)
            st_folium(m, width=None)
        except Exception as e:
            st.info(f"Para la vista previa instala: folium y streamlit-folium. Detalle: {e}")

    # 3) Opciones
    st.subheader("2) Opciones")
    dibujar_linea = st.checkbox("Conectar puntos con línea (en orden numérico)", value=True)

    # 4) Generar KMZ
    st.subheader("3) Generar KMZ")
    if st.button("🏁 Crear KMZ para Google Earth", type="primary", use_container_width=True):
        ruta = _crear_kmz(df_pts, df_largo, dibujar_linea=dibujar_linea)
        st.success("KMZ generado.")
        with open(ruta, "rb") as f:
            st.download_button(
                "⬇️ Descargar KMZ",
                f, file_name="proyecto.kmz",
                mime="application/vnd.google-earth.kmz",
                use_container_width=True
            )
