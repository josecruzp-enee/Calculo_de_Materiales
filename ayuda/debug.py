# -*- coding: utf-8 -*-
# ayuda/debug.py

from __future__ import annotations
import streamlit as st
import pandas as pd


# =========================================================
# 🔷 GUARDAR DEBUG GLOBAL
# =========================================================
def debug_guardar(clave: str, valor):

    if "debug_pipeline" not in st.session_state:
        st.session_state["debug_pipeline"] = {}

    st.session_state["debug_pipeline"][clave] = valor


# =========================================================
# 🔷 DEBUG ESTRUCTURADO (PRO)
# =========================================================
def debug_step(nombre: str, data):

    debug_guardar(nombre, {
        "tipo": type(data).__name__,
        "shape": getattr(data, "shape", None),
        "preview": str(data)[:500]
    })


# =========================================================
# 🔷 ESTADO VISUAL
# =========================================================
def _estado(ok):
    return "🟢" if ok else "🔴"


# =========================================================
# 🔷 PIPELINE REAL
# =========================================================
def _pipeline_runtime():

    df = st.session_state.get("df_estructuras")
    resultado = st.session_state.get("resultado_calculo")

    pasos = []

    pasos.append(("UI", True))

    pasos.append((
        "Entradas",
        isinstance(df, pd.DataFrame) and not df.empty
    ))

    pasos.append((
        "Normalización",
        isinstance(df, pd.DataFrame)
        and "Estructura" in df.columns
        and df["Estructura"].notna().any()
    ))

    pasos.append((
        "Materiales",
        resultado is not None
        and hasattr(resultado, "df_materiales")
    ))

    pasos.append(("Exportación", resultado is not None))
    pasos.append(("PDF", resultado is not None))

    return pasos


# =========================================================
# 🔷 RENDER PIPELINE
# =========================================================
def _render_pipeline_runtime():

    st.markdown("### 🧠 Pipeline en tiempo real")

    pasos = _pipeline_runtime()

    for nombre, ok in pasos:

        icono = _estado(ok)
        st.write(f"{icono} {nombre}")

        if not ok:
            st.error(f"⚠️ Falla en: {nombre}")
            break


# =========================================================
# 🔷 GRAFO PIPELINE
# =========================================================
def _grafo_pipeline():

    pasos = _pipeline_runtime()

    st.markdown("### 🔄 Flujo del sistema")

    try:
        import graphviz

        dot = graphviz.Digraph()

        prev = None

        for nombre, ok in pasos:

            label = f"{nombre}\n{_estado(ok)}"
            dot.node(nombre, label)

            if prev:
                dot.edge(prev, nombre)

            prev = nombre

        st.graphviz_chart(dot)

    except Exception:
        for nombre, ok in pasos:
            st.write(f"{_estado(ok)} {nombre}")


# =========================================================
# 🔷 RENDER DEBUG
# =========================================================
def _render_valor_debug(valor):

    if isinstance(valor, pd.DataFrame):
        st.caption(f"Filas: {len(valor)} | Columnas: {list(valor.columns)}")
        st.dataframe(valor.head(10), use_container_width=True)

    elif isinstance(valor, dict):
        st.json(valor)

    elif hasattr(valor, "__dict__"):
        st.json(valor.__dict__)

    else:
        st.write(valor)


# =========================================================
# 🔷 AUDITORÍA DE ESTRUCTURAS
# =========================================================
def _auditar_estructuras():

    st.markdown("### 🔍 Auditoría de estructuras")

    df = st.session_state.get("df_estructuras")

    if df is None:
        st.error("df_estructuras = None")
        return

    st.write("Shape:", df.shape)
    st.write("Columnas:", list(df.columns))
    st.dataframe(df.head(10))

    if "Estructura" in df.columns:
        st.write("Valores únicos:")
        st.write(sorted(df["Estructura"].dropna().unique())[:50])


# =========================================================
# 🔥 DEBUG PROFUNDO DE MATERIALES
# =========================================================
def _debug_materiales_profundo():

    st.markdown("### 🔬 Trazabilidad de materiales")

    hojas = st.session_state.get("hojas_base")
    df = st.session_state.get("df_estructuras")
    tension = st.session_state.get("tension")

    if hojas is None:
        st.error("❌ No hay hojas_base cargadas")
        return

    if df is None or df.empty:
        st.error("❌ No hay estructuras")
        return

    estructuras = sorted(df["Estructura"].dropna().unique())

    st.write("Total estructuras:", len(estructuras))

    for est in estructuras:

        with st.expander(f"🔎 {est}"):

            df_est = hojas.get(est)

            if df_est is None:
                st.error("❌ NO EXISTE EN BASE")
                continue

            st.success("✔ Hoja encontrada")

            st.write("Columnas:", list(df_est.columns))

            # Buscar columna tensión
            col_tension = None

            for c in df_est.columns:
                try:
                    val = float(str(c).replace(",", "."))
                    if abs(val - float(tension)) < 0.1:
                        col_tension = c
                        break
                except:
                    continue

            if col_tension is None:
                st.error(f"❌ No tiene columna {tension}")
                continue

            st.success(f"✔ Columna tensión: {col_tension}")

            df_est[col_tension] = pd.to_numeric(df_est[col_tension], errors="coerce").fillna(0)

            df_filtrado = df_est[
                (df_est[col_tension] > 0)
                & df_est["MATERIALES"].notna()
            ]

            if df_filtrado.empty:
                st.error("❌ SIN MATERIALES")
            else:
                st.success(f"✔ {len(df_filtrado)} materiales encontrados")
                st.dataframe(df_filtrado.head(10))


# =========================================================
# 🔷 DEBUG PRINCIPAL
# =========================================================
def seccion_debug():

    st.title("🧠 Debug del sistema")

    debug = st.session_state.get("debug_pipeline")

    if debug:
        st.markdown("### 📊 Variables capturadas")

        for k, v in debug.items():
            st.markdown(f"#### 🔹 {k}")
            _render_valor_debug(v)

    else:
        st.info("No hay debug aún")

    # ======================================================
    # Auditoría base
    # ======================================================
    _auditar_estructuras()

    # ======================================================
    # 📊 VER TODAS LAS ESTRUCTURAS (PROCESADAS)
    # ======================================================
    df = st.session_state.get("df_estructuras")

    if df is not None and hasattr(df, "empty") and not df.empty:

        st.markdown("### 📊 Estructuras completas (procesadas)")

        st.write(f"Total filas: {len(df)}")

        filtro = st.text_input("Buscar estructura")

        if filtro:
            df_filtrado = df[df["Estructura"].str.contains(filtro, case=False, na=False)]
            st.dataframe(df_filtrado, use_container_width=True)
        else:
            st.dataframe(df, use_container_width=True)

        st.markdown("### 🔍 Conteo por estructura")
        st.dataframe(
            df.groupby("Estructura")["Cantidad"]
            .sum()
            .sort_values(ascending=False)
        )

    else:
        st.warning("No hay df_estructuras disponible")

    # ======================================================
    # 🧾 DXF RAW (ANTES DE NORMALIZAR)
    # ======================================================
    debug_extra = st.session_state.get("debug_extra", {})

    raw = debug_extra.get("DXF_TODAS")

    if raw:

        st.markdown("### 🧾 Estructuras detectadas en DXF (RAW)")

        st.write(f"Total detectadas: {len(raw)}")

        st.dataframe(
            pd.DataFrame({"estructura": raw}),
            use_container_width=True
        )

        # 🔎 ÚNICAS
        st.markdown("### 🔎 Estructuras únicas en DXF")

        unicas = sorted(set(raw))

        st.write(f"Total únicas: {len(unicas)}")

        st.dataframe(
            pd.DataFrame({"estructura": unicas}),
            use_container_width=True
        )

        # 🔥 SOLO CS (para detectar bug)
        st.markdown("### 🔎 Solo estructuras CS")

        cs = [r for r in raw if "CS" in str(r)]

        st.dataframe(
            pd.DataFrame({"estructura": sorted(set(cs))}),
            use_container_width=True
        )

    else:
        st.info("No hay datos RAW del DXF")

    # ======================================================
    # DEBUG PROFUNDO
    # ======================================================
    _debug_materiales_profundo()

    # ======================================================
    # Pipeline
    # ======================================================
    _render_pipeline_runtime()

    # ======================================================
    # Grafo
    # ======================================================
    _grafo_pipeline()

    # ======================================================
    # Session completa
    # ======================================================
    with st.expander("🔍 session_state completo"):
        st.json({k: str(v)[:200] for k, v in st.session_state.items()})
