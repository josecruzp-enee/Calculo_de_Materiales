def hoja_info_proyecto(
    datos_proyecto,
    df_estructuras=None,
    df_mat=None,
    *,
    styles=None,
    styleN=None,
    styleH=None,
    _calibres_por_tipo=None
):
    # ==========================================================
    # VALIDACIÓN / CONTEXTO
    # ==========================================================
    def _validar_dependencias():
        if styleH is None or styleN is None or _calibres_por_tipo is None:
            raise ValueError("Faltan styleH/styleN/_calibres_por_tipo. Debes pasarlos desde pdf_utils.")

    # ==========================================================
    # HELPERS BASE
    # ==========================================================
    def _float_safe(x, d=0.0):
        try:
            return float(x)
        except Exception:
            return d

    def _formato_tension(vll):
        """
        Ej: 13.8 -> '7.9 LN / 13.8 LL KV' (LN truncado a 1 decimal).
        """
        try:
            vll = float(vll)
            vln = vll / sqrt(3)
            vln = floor(vln * 10) / 10
            return f"{vln:.1f} LN / {vll:.1f} LL KV"
        except Exception:
            return str(vll)

    def _col_cantidad(df):
        if df is None:
            return None
        if "Cantidad" in df.columns:
            return "Cantidad"
        if "CANTIDAD" in df.columns:
            return "CANTIDAD"
        return None

    def _parse_n_fases(configuracion: str) -> int:
        s = (configuracion or "").strip().upper()
        m = re.search(r"(\d+)\s*F", s)
        return int(m.group(1)) if m else 1

    # ==========================================================
    # EXTRACTORES (RETORNAN DATOS, NO FLOWABLES)
    # ==========================================================
    def _extraer_postes(df_est):
        """
        Retorna: (resumen_dict, total) o (None, 0)
        resumen_dict: {"PC-30": 2, "PC-40": 1}
        """
        if df_est is None or df_est.empty or "codigodeestructura" not in df_est.columns:
            return None, 0

        postes = df_est[df_est["codigodeestructura"].astype(str).str.contains(r"\b(PC|PT)\b", case=False, na=False)]
        if postes.empty:
            return None, 0

        resumen = {}
        for _, r in postes.iterrows():
            cod = str(r.get("codigodeestructura", "")).strip()
            cant = int(_float_safe(r.get("Cantidad", 0), 0))
            if cod:
                resumen[cod] = resumen.get(cod, 0) + cant

        total = sum(resumen.values())
        return (resumen if resumen else None), total

    def _extraer_transformadores(df_est, df_m):
        """
        Retorna: (total_transformadores, capacidades_lista)
        total_transformadores = cantidad física (TS=1, TD=2, TT=3)
        capacidades_lista: ["TS-15 KVA", "TT-37.5 KVA", ...]
        """
        total_t = 0
        capacidades = []
        mult = {"TS": 1, "TD": 2, "TT": 3}

        def _desde_estructuras():
            nonlocal total_t, capacidades
            if df_est is None or df_est.empty or "codigodeestructura" not in df_est.columns:
                return
            s = df_est["codigodeestructura"].astype(str).str.upper().str.strip()
            ext = s.str.extract(r"^(TS|TD|TT)\s*-\s*(\d+(?:\.\d+)?)\s*KVA$", expand=True)
            mask = ext[0].notna()
            if not mask.any():
                return

            qty = pd.to_numeric(df_est.loc[mask, "Cantidad"], errors="coerce").fillna(0)
            pref = ext.loc[mask, 0]
            kva = pd.to_numeric(ext.loc[mask, 1], errors="coerce").fillna(0)

            total_t = int((qty * pref.map(mult)).sum())
            capacidades = sorted({f"{p}-{k:g} KVA" for p, k in zip(pref, kva)})

        def _desde_materiales_fallback():
            nonlocal total_t, capacidades
            if total_t != 0:
                return
            if df_m is None or df_m.empty or "Materiales" not in df_m.columns:
                return

            s = df_m["Materiales"].astype(str).str.upper().str.strip()
            ext = s.str.extract(r"\b(TS|TD|TT)\s*-\s*(\d+(?:\.\d+)?)\s*KVA\b", expand=True)
            mask = ext[0].notna()
            if not mask.any():
                return

            df_tx = df_m.loc[mask].copy()
            cc = _col_cantidad(df_tx) or "Cantidad"
            if cc not in df_tx.columns:
                df_tx[cc] = 0
            df_tx[cc] = pd.to_numeric(df_tx[cc], errors="coerce").fillna(0)

            df_tx["_key"] = ext.loc[mask, 0] + "-" + ext.loc[mask, 1] + " KVA"
            bancos = df_tx.groupby("_key", as_index=False)[cc].max()

            total_t_calc = 0
            for _, r in bancos.iterrows():
                pref = str(r["_key"]).split("-")[0].upper()
                total_t_calc += _float_safe(r[cc], 0) * mult.get(pref, 1)

            total_t = int(total_t_calc)
            capacidades = bancos["_key"].tolist()

        _desde_estructuras()
        _desde_materiales_fallback()
        return total_t, capacidades

    def _parse_ll(txt):
        """
        Devuelve (n_lamparas, etiqueta_potencia)
        - LL-1-50W -> (1, '50 W')
        - LL-1-28A50W -> (1, '50 W')
        - LL-1-28-50W -> (1, '28-50 W')
        """
        s = str(txt).upper().replace("–", "-")
        s = re.sub(r"\s+", "", s)

        m_n = re.search(r"LL-(\d+)-", s)
        n = int(m_n.group(1)) if m_n else 1

        m = re.search(r"LL-\d+-(\d+)A(\d+)W", s)
        if m:
            return n, f"{m.group(2)} W"

        m = re.search(r"LL-\d+-(\d+)-(\d+)W", s)
        if m:
            return n, f"{m.group(1)}-{m.group(2)} W"

        m = re.search(r"LL-\d+-(\d+)W", s)
        if m:
            return n, f"{m.group(1)} W"

        return n, "SIN POTENCIA"

    def _extraer_luminarias_por_ll(df_m):
        """
        Retorna: (total, dict_potencias)
        dict_potencias: {"50 W": 2, "100 W": 1}
        """
        if df_m is None or df_m.empty or "Materiales" not in df_m.columns:
            return 0, {}

        cc = _col_cantidad(df_m)
        if cc is None:
            return 0, {}

        s_mat = df_m["Materiales"].astype(str)
        pat_ll = r"\bLL\s*-\s*\d+\s*-\s*(?:\d+\s*A\s*)?\d+(?:\s*-\s*\d+)?\s*W\b"
        lums = df_m[s_mat.str.contains(pat_ll, case=False, na=False)].copy()
        if lums.empty:
            return 0, {}

        lums[cc] = pd.to_numeric(lums[cc], errors="coerce").fillna(0)

        parsed = lums["Materiales"].map(_parse_ll)
        lums["_n"] = parsed.map(lambda x: x[0])
        lums["_pot"] = parsed.map(lambda x: x[1])
        lums["_qty_real"] = lums[cc].astype(float) * lums["_n"].astype(float)

        resumen = (
            lums.groupby("_pot", as_index=True)["_qty_real"]
                .sum().round().astype(int).sort_index()
        )

        total = int(resumen.sum())
        return total, resumen.to_dict()

    # ==========================================================
    # BUILDERS (RETORNAN FLOWABLES)
    # ==========================================================
    def _build_header():
        return [Paragraph("<b>Hoja de Información del Proyecto</b>", styleH), Spacer(1, 12)]

    def _build_tabla_datos(nivel_tension_fmt: str, cables: list):
        calibre_primario_tab = _calibres_por_tipo(cables, "MT")
        calibre_secundario_tab = _calibres_por_tipo(cables, "BT")
        calibre_neutro_tab = _calibres_por_tipo(cables, "N")
        calibre_piloto_tab = _calibres_por_tipo(cables, "HP")
        calibre_retenidas_tab = _calibres_por_tipo(cables, "RETENIDA")

        calibre_primario = calibre_primario_tab or datos_proyecto.get("calibre_primario") or datos_proyecto.get("calibre_mt", "")
        calibre_secundario = calibre_secundario_tab or datos_proyecto.get("calibre_secundario", "")
        calibre_neutro = calibre_neutro_tab or datos_proyecto.get("calibre_neutro", "")
        calibre_piloto = calibre_piloto_tab or datos_proyecto.get("calibre_piloto", "")
        calibre_retenidas = calibre_retenidas_tab or datos_proyecto.get("calibre_retenidas", "")

        data = [
            ["Nombre del Proyecto:", datos_proyecto.get("nombre_proyecto", "")],
            ["Código / Expediente:", datos_proyecto.get("codigo_proyecto", "")],
            ["Nivel de Tensión (kV):", nivel_tension_fmt],
            ["Calibre Primario:", calibre_primario],
            ["Calibre Secundario:", calibre_secundario],
            ["Calibre Neutro:", calibre_neutro],
            ["Calibre Piloto:", calibre_piloto],
            ["Calibre Cable de Retenidas:", calibre_retenidas],
            ["Fecha de Informe:", datos_proyecto.get("fecha_informe", datetime.today().strftime("%Y-%m-%d"))],
            ["Responsable / Diseñador:", datos_proyecto.get("responsable", "N/A")],
            ["Empresa / Área:", datos_proyecto.get("empresa", "N/A")],
        ]

        t = Table(data, colWidths=[180, 300])
        t.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ]))
        return [t, Spacer(1, 18)]

    def _build_descripcion_general(nivel_tension_fmt: str, primarios: list, secundarios: list):
        def _linea_postes():
            resumen, total = _extraer_postes(df_estructuras)
            if not resumen:
                return None
            partes = [f"{v} {k}" for k, v in resumen.items()]
            return f"Hincado de {', '.join(partes)} (Total: {total} postes)."

        def _lineas_lp():
            out = []
            for c in primarios:
                long_total = _float_safe(c.get("Total Cable (m)", c.get("Longitud (m)", 0)))
                fase = str(c.get("Configuración", "")).strip().upper()
                calibre = str(c.get("Calibre", "")).strip()
                n_fases = _parse_n_fases(fase)
                long_desc = (long_total / n_fases) if n_fases > 1 else long_total
                if long_desc > 0 and calibre:
                    out.append(f"Construcción de {long_desc:.0f} m de LP, {nivel_tension_fmt}, {fase}, {calibre}.")
            return out

        def _lineas_ls():
            out = []
            for c in secundarios:
                long_total = _float_safe(c.get("Total Cable (m)", 0))
                fase = str(c.get("Configuración", "")).strip().upper()
                calibre = str(c.get("Calibre", "")).strip()
                n_fases = _parse_n_fases(fase)
                long_desc = (long_total / n_fases) if n_fases > 1 else long_total
                if long_desc > 0 and calibre:
                    out.append(f"Construcción de {long_desc:.0f} m de LS, 120/240 V, {fase}, {calibre}.")
            return out

        def _linea_transformadores():
            total_t, capacidades = _extraer_transformadores(df_estructuras, df_mat)
            if total_t <= 0:
                return None
            cap_txt = ", ".join(capacidades) if capacidades else ""
            return f"Instalación de {total_t} transformador(es) {f'({cap_txt})' if cap_txt else ''}."

        def _linea_luminarias():
            total_l, det_l = _extraer_luminarias_por_ll(df_mat)
            if total_l <= 0:
                return None
            det = " y ".join([f\"{v} de {k}\" for k, v in det_l.items()])
            return f"Instalación de {total_l} luminaria(s) de alumbrado público ({det})."

        def _armar_cuerpo():
            descripcion_manual = (datos_proyecto.get("descripcion_proyecto", "") or "").strip()
            lineas = []

            lp = _linea_postes()
            if lp:
                lineas.append(lp)

            lineas.extend(_lineas_lp())
            lineas.extend(_lineas_ls())

            lt = _linea_transformadores()
            if lt:
                lineas.append(lt)

            ll = _linea_luminarias()
            if ll:
                lineas.append(ll)

            descripcion_auto = "<br/>".join([f"{i + 1}. {l}" for i, l in enumerate(lineas)])
            return (descripcion_manual + "<br/><br/>" + descripcion_auto) if descripcion_manual else descripcion_auto

        cuerpo_desc = _armar_cuerpo()
        return [
            Paragraph("<b>Descripción general del Proyecto:</b>", styleN),
            Spacer(1, 6),
            Paragraph(cuerpo_desc, styleN),
            Spacer(1, 18),
        ]

    # ==========================================================
    # MAIN INTERNO (SOLO ORQUESTA BUILDERS)
    # ==========================================================
    def _main():
        _validar_dependencias()

        tension_valor = datos_proyecto.get("nivel_de_tension") or datos_proyecto.get("tension") or ""
        nivel_tension_fmt = _formato_tension(tension_valor)

        cables = datos_proyecto.get("cables_proyecto", []) or []
        primarios = [c for c in cables if str(c.get("Tipo", "")).upper() == "MT"]
        secundarios = [c for c in cables if str(c.get("Tipo", "")).upper() in ("BT", "HP", "N")]

        elems = []
        elems.extend(_build_header())
        elems.extend(_build_tabla_datos(nivel_tension_fmt, cables))
        elems.extend(_build_descripcion_general(nivel_tension_fmt, primarios, secundarios))
        return elems

    return _main()
