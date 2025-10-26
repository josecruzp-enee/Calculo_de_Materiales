# interfaz/puntos.py (o pégalo en tu app donde cargas puntos)
from __future__ import annotations
import io
import pandas as pd
import streamlit as st

try:
    from streamlit_folium import st_folium
    import folium
    from folium.plugins import Draw, MousePosition
    _HAVE_MAPS = True
except Exception:
    _HAVE_MAPS = False


def _ensure_state():
    if "puntos_lista" not in st.session_state:
        # almacenamos como lista de dicts: {"Punto": "Punto 1", "lat": 14.08, "lon": -87.21}
        st.session_state["puntos_lista"] = []
    if "punto_auto_n" not in st.session_state:
        st.session_state["punto_auto_n"] = 1


def _df_puntos_from_state() -> pd.DataFrame:
    if "puntos_lista" not in st.session_state or not st.session_state["puntos_lista"]:
        return pd.DataFrame(columns=["Punto", "lat", "lon"])
    return pd.DataFrame(st.session_state["puntos_lista"], columns=["Punto", "lat", "lon"])


def ui_puntos_desde_csv_o_mapa() -> pd.DataFrame:
    """
    Devuelve SIEMPRE un DataFrame con columnas: ['Punto','lat','lon'].
    Permite cargar por CSV o seleccionar en mapa.
    """
    _ensure_state()

    st.markdown("### 1) Cargar coordenadas de puntos")
    tabs = st.tabs(["📄 CSV", "🗺️ Mapa"])

    # ---------------------------
    # Pestaña CSV
    # ---------------------------
    with tabs[0]:
        st.caption("Formato esperado: columnas **Punto, lat, lon** (separador coma).")
        upl = st.file_uploader("Sube puntos.csv", type=["csv"], key="uploader_puntos")
        if upl is not None:
            try:
                df = pd.read_csv(upl)
                # Normalizamos nombre de columnas
                cols_map = {c.lower().strip(): c for c in df.columns}
                # Asignar canónicos si hay variantes
                col_p = cols_map.get("punto") or cols_map.get("id") or "Punto"
                col_lat = cols_map.get("lat") or cols_map.get("latitude") or "lat"
                col_lon = cols_map.get("lon") or cols_map.get("lng") or cols_map.get("longitude") or "lon"

                # Renombrar si fuese necesario
                rename = {}
                if col_p != "Punto": rename[col_p] = "Punto"
                if col_lat != "lat": rename[col_lat] = "lat"
                if col_lon != "lon": rename[col_lon] = "lon"
                df = df.rename(columns=rename)

                # Limpiar y tipar
                for c in ["Punto", "lat", "lon"]:
                    if c not in df.columns:
                        df[c] = "" if c == "Punto" else 0.0
                df["Punto"] = df["Punto"].astype(str).str.strip()
                df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
                df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
                df = df.dropna(subset=["lat", "lon"]).reset_index(drop=True)

                st.session_state["puntos_lista"] = df.to_dict(orient="records")
                # reinicia contador para nuevos puntos por mapa
                st.session_state["punto_auto_n"] = len(df) + 1

                st.success(f"✅ Cargados {len(df)} puntos desde CSV.")
            except Exception as e:
                st.error(f"Error leyendo CSV: {e}")

    # ---------------------------
    # Pestaña Mapa
    # ---------------------------
    with tabs[1]:
        if not _HAVE_MAPS:
            st.error("Falta instalar dependencias de mapa. Ejecuta: `pip install streamlit-folium folium`")
        else:
            st.caption("Haz **clic** en el mapa para tomar coordenadas. Luego pulsa **Agregar punto del click**.")
            # Centro por defecto (Honduras aprox. – puedes cambiarlo)
            default_center = [14.7, -86.8]
            # Construimos el mapa
            m = folium.Map(location=default_center, zoom_start=7, control_scale=True, prefer_canvas=True)

            # Muestra lat/lon en el mouse
            MousePosition().add_to(m)

            # Draw sólo marcador (evitamos polígonos innecesarios)
            draw = Draw(
                draw_options={
                    "polyline": False, "polygon": False, "rectangle": False,
                    "circle": False, "circlemarker": False, "marker": True
                },
                edit_options={"edit": True, "remove": True},
            )
            draw.add_to(m)

            # Marcadores ya creados (estado)
            for i, r in enumerate(st.session_state["puntos_lista"], start=1):
                folium.Marker(
                    location=[r["lat"], r["lon"]],
                    tooltip=r["Punto"],
                    icon=folium.Icon(color="blue", icon="map-marker")
                ).add_to(m)

            # Render del mapa
            ret = st_folium(m, width="100%", height=520, key="folium_puntos", returned_objects=[])

            # Captura del último click (ret['last_clicked'] = {'lat':..., 'lng':...})
            lc = ret.get("last_clicked") if isinstance(ret, dict) else None
            with st.expander("➕ Agregar punto manual (desde último click)"):
                c1, c2, c3 = st.columns([2, 1, 1])
                with c1:
                    nombre = st.text_input(
                        "Nombre del punto",
                        value=f"Punto {st.session_state['punto_auto_n']}",
                        key="nombre_punto_mapa",
                    )
                with c2:
                    lat_val = (lc.get("lat") if lc else None)
                    lat = st.number_input("lat", value=float(lat_val) if lat_val is not None else 0.0,
                                          format="%.8f", key="lat_mapa")
                with c3:
                    lon_val = (lc.get("lng") if lc else None)
                    lon = st.number_input("lon", value=float(lon_val) if lon_val is not None else 0.0,
                                          format="%.8f", key="lon_mapa")

                add_col1, add_col2 = st.columns([1,1])
                with add_col1:
                    if st.button("➕ Agregar punto del click", use_container_width=True):
                        if lat and lon:
                            st.session_state["puntos_lista"].append({
                                "Punto": nombre.strip() or f"Punto {st.session_state['punto_auto_n']}",
                                "lat": float(lat),
                                "lon": float(lon),
                            })
                            st.session_state["punto_auto_n"] += 1
                            st.success("Punto agregado.")
                        else:
                            st.warning("Primero haz click en el mapa o escribe lat/lon.")

                with add_col2:
                    if st.button("🗑️ Limpiar todos los puntos del mapa", use_container_width=True):
                        st.session_state["puntos_lista"].clear()
                        st.session_state["punto_auto_n"] = 1
                        st.info("Puntos limpiados.")

    # ---------------------------
    # Vista y descarga
    # ---------------------------
    st.markdown("#### 📍 Puntos seleccionados")
    df_out = _df_puntos_from_state()
    st.dataframe(df_out, use_container_width=True, hide_index=True)

    if not df_out.empty:
        st.download_button(
            "⬇️ Descargar CSV de puntos",
            df_out.to_csv(index=False).encode("utf-8"),
            file_name="puntos.csv",
            mime="text/csv",
            use_container_width=True,
        )

    return df_out
