def leer_dxf(archivo_dxf) -> pd.DataFrame:
    """
    Ahora devuelve directamente:
        Punto | codigodeestructura | cantidad
    """

    try:
        import ezdxf
    except ImportError:
        raise ImportError("Debes instalar ezdxf: pip install ezdxf")

    # -------------------------
    # CARGAR DXF
    # -------------------------
    try:
        if hasattr(archivo_dxf, "read"):
            import tempfile

            with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
                tmp.write(archivo_dxf.read())
                ruta = tmp.name

            doc = ezdxf.readfile(ruta)
        else:
            doc = ezdxf.readfile(archivo_dxf)

    except Exception as e:
        raise ValueError(f"No se pudo leer el DXF: {e}")

    msp = doc.modelspace()

    # -------------------------
    # EXTRAER TEXTOS
    # -------------------------
    filas = []

    for e in msp:

        if e.dxftype() not in ["TEXT", "MTEXT"]:
            continue

        try:
            if e.dxftype() == "TEXT":
                contenido = e.dxf.text
                punto = e.dxf.insert
            else:
                contenido = e.text
                punto = e.dxf.insert

            texto = _limpiar_texto_basico(contenido)

            if not _es_texto_util(texto):
                continue

            x = float(punto[0]) if punto else None
            y = float(punto[1]) if punto else None

            filas.append({
                "Texto": texto,
                "X": x,
                "Y": y
            })

        except Exception:
            continue

    if not filas:
        return pd.DataFrame(columns=["Punto", "codigodeestructura", "cantidad"])

    df = pd.DataFrame(filas)

    # =====================================================
    # 🔥 EXTRAER CÓDIGOS DE ESTRUCTURA
    # =====================================================
    regex = re.compile(
        r"(A-[IVX0-9\-]+|B-[IVX0-9\-]+|CT-[A-Z0-9\-]+|TS-\d+(\.\d+)?KVA|R-\d+|PC-\d+[A-Z]?)"
    )

    def extraer(texto):
        encontrados = regex.findall(str(texto).upper())
        salida = []
        for e in encontrados:
            if isinstance(e, tuple):
                salida.append(e[0])
            else:
                salida.append(e)
        return salida

    df["codigos"] = df["Texto"].apply(extraer)
    df = df.explode("codigos")
    df = df[df["codigos"].notna()]
    df = df[df["codigos"] != ""]

    if df.empty:
        return pd.DataFrame(columns=["Punto", "codigodeestructura", "cantidad"])

    # =====================================================
    # 🔥 AGRUPAR POR PUNTO (por cercanía)
    # =====================================================
    puntos = []
    clusters = []

    for _, row in df.iterrows():

        x, y = row["X"], row["Y"]
        asignado = False

        for i, (cx, cy) in enumerate(clusters):
            if abs(x - cx) <= 5 and abs(y - cy) <= 5:
                puntos.append(f"Punto {i+1}")
                asignado = True
                break

        if not asignado:
            clusters.append((x, y))
            puntos.append(f"Punto {len(clusters)}")

    df["Punto"] = puntos

    # =====================================================
    # 🔥 CONTEO FINAL
    # =====================================================
    df_out = (
        df.groupby(["Punto", "codigos"])
        .size()
        .reset_index(name="cantidad")
    )

    df_out.rename(columns={"codigos": "codigodeestructura"}, inplace=True)

    return df_out
