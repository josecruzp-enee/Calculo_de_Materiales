def _convertir_a_largo(df: pd.DataFrame) -> pd.DataFrame:

    df = df.copy()
    df.columns = df.columns.str.strip()

    registros = []

    for idx, row in df.iterrows():

        punto = row.get("Punto") or row.get("punto") or f"P-{idx+1}"

        estructura_raw = None

        for col in df.columns:
            if col.lower() in ["estructura", "estructuras", "codigodeestructura"]:
                estructura_raw = row.get(col)
                break

        if estructura_raw is None:
            continue

        lista_codigos = expandir_lista_codigos(estructura_raw)

        debug_guardar("RAW_ESTRUCTURA", estructura_raw)
        debug_guardar("LISTA_CODIGOS", lista_codigos)

        poste_detectado = None  # 🔥 CLAVE

        for raw in lista_codigos:

            if not raw:
                continue

            # =========================================
            # 🔥 DETECTAR POSTE (ANTES DE LIMPIAR)
            # =========================================
            if _es_poste(raw):
                poste_detectado = limpiar_codigo(raw)
                continue

            cod = limpiar_codigo(raw)

            if not cod:
                continue

            # ❌ eliminar multiplicadores basura
            if re.match(r"^\d+X$", cod):
                continue

            # ❌ eliminar luminaria incompleta
            if cod == "LL-1":
                continue

            registros.append({
                "punto": str(punto).strip(),
                "poste": poste_detectado,   # 🔥 NUEVO
                "codigodeestructura": cod,
                "cantidad": 1
            })

    return pd.DataFrame(registros)
