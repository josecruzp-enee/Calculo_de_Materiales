# -*- coding: utf-8 -*-
"""
analizador.py
Escáner del proyecto: enumera módulos/funciones/imports, claves de st.session_state,
genera un grafo simple de llamadas (call graph) e imports internos (DOT),
y produce salida TXT / JSON. Puede correrse por CLI o como app de Streamlit.

Uso (CLI):
    python analizador.py --base modulo --incluir app.py \
        --salida MAPA_FUNCIONES.txt --json MAPA_FUNCIONES.json \
        --dot-imports imports.dot --dot-llamadas llamadas.dot --depurar-imports

Uso (Streamlit):
    streamlit run analizador.py -- --base modulo --incluir app.py --ui
"""

import os, re, ast, json, argparse, traceback
from datetime import datetime
from typing import Dict, List, Set, Tuple, Optional

# ---------- Config predeterminada ----------
BASES_PREDETERMINADAS = ["modulo"]     # carpetas a analizar
INCLUIR_PREDETERMINADOS = ["app.py"]   # archivos sueltos a sumar
SALIDA_PREDETERMINADA = "MAPA_FUNCIONES.txt"

PATRONES_SESSION_STATE = [
    r'st\.session_state\["([^"]+)"\]',
    r"st\.session_state\['([^']+)'\]",
    r"st\.session_state\.get\(\s*['\"]([^'\"]+)['\"]",
]

# ---------- Utilidades de E/S ----------
def leer_texto(ruta: str) -> str:
    with open(ruta, "r", encoding="utf-8") as f:
        return f.read()

def nombre_modulo_relativo(ruta: str) -> str:
    # "modulo/estilos_app.py" -> "modulo.estilos_app"
    rel = os.path.relpath(ruta, start=".")
    rel = rel.replace("\\", "/")
    if rel.endswith(".py"):
        rel = rel[:-3]
    return rel.replace("/", ".")

def recorrer_archivos_python(bases: List[str], incluir_archivos: List[str]) -> List[str]:
    encontrados = []
    for base in bases:
        if os.path.isdir(base):
            for raiz, _, archivos in os.walk(base):
                for a in archivos:
                    if a.endswith(".py"):
                        encontrados.append(os.path.join(raiz, a))
    for a in incluir_archivos:
        if os.path.isfile(a):
            encontrados.append(a)
    # únicos y ordenados
    vistos, salida = set(), []
    for p in encontrados:
        ap = os.path.abspath(p)
        if ap not in vistos:
            vistos.add(ap)
            salida.append(ap)
    return sorted(salida)

# ---------- AST Parser ----------
class InfoArchivo(ast.NodeVisitor):
    def __init__(self, modulo: str, fuente: str):
        self.modulo = modulo
        self.fuente = fuente
        self.funciones: Set[str] = set()
        self.imports: Set[str] = set()
        self.llamadas_por_funcion: Dict[str, Set[str]] = {}
        self.llamadas_toplevel: Set[str] = set()
        self.llamadas_en_main: Set[str] = set()
        self.claves_session: Set[str] = set()
        self._funcion_actual: Optional[str] = None
        # capturar claves de session_state por regex (complemento al AST)
        for pat in PATRONES_SESSION_STATE:
            for m in re.findall(pat, fuente):
                self.claves_session.add(m)

    # imports
    def visit_Import(self, nodo: ast.Import):
        for alias in nodo.names:
            self.imports.add(alias.name)
        self.generic_visit(nodo)

    def visit_ImportFrom(self, nodo: ast.ImportFrom):
        if nodo.module:
            self.imports.add(nodo.module)
        self.generic_visit(nodo)

    # definiciones de función
    def visit_FunctionDef(self, nodo: ast.FunctionDef):
        nombre = nodo.name
        self.funciones.add(nombre)
        anterior = self._funcion_actual
        self._funcion_actual = nombre
        self.generic_visit(nodo)
        self._funcion_actual = anterior

    def visit_AsyncFunctionDef(self, nodo: ast.AsyncFunctionDef):
        nombre = nodo.name
        self.funciones.add(nombre)
        anterior = self._funcion_actual
        self._funcion_actual = nombre
        self.generic_visit(nodo)
        self._funcion_actual = anterior

    # llamadas
    def visit_Call(self, nodo: ast.Call):
        llamada = None
        if isinstance(nodo.func, ast.Name):
            llamada = nodo.func.id
        elif isinstance(nodo.func, ast.Attribute):
            llamada = nodo.func.attr
        if llamada:
            if self._funcion_actual:
                self.llamadas_por_funcion.setdefault(self._funcion_actual, set()).add(llamada)
            else:
                self.llamadas_toplevel.add(llamada)
        self.generic_visit(nodo)

def analizar_archivo(ruta: str) -> InfoArchivo:
    src = leer_texto(ruta)
    modulo = nombre_modulo_relativo(ruta)
    arbol = ast.parse(src, filename=ruta)
    info = InfoArchivo(modulo, src)
    info.visit(arbol)

    # detectar if __name__ == "__main__"
    try:
        for nodo in arbol.body:
            if isinstance(nodo, ast.If):
                cond = nodo.test
                if isinstance(cond, ast.Compare):
                    left = cond.left
                    comparadores = cond.comparators
                    if isinstance(left, ast.Name) and left.id == "__name__" and comparadores:
                        right = comparadores[0]
                        if isinstance(right, ast.Constant) and right.value == "__main__":
                            class VisitanteMain(ast.NodeVisitor):
                                def __init__(self, contenedor: InfoArchivo):
                                    self.c = contenedor
                                def visit_Call(self, llamada: ast.Call):
                                    if isinstance(llamada.func, ast.Name):
                                        self.c.llamadas_en_main.add(llamada.func.id)
                                    elif isinstance(llamada.func, ast.Attribute):
                                        self.c.llamadas_en_main.add(llamada.func.attr)
                                    self.generic_visit(llamada)
                            vm = VisitanteMain(info)
                            for stmt in nodo.body:
                                vm.visit(stmt)
    except Exception:
        pass
    return info

# ---------- Construcción del mapa ----------
def construir_mapa_proyecto(bases: List[str], incluir_archivos: List[str]) -> Dict[str, dict]:
    archivos = recorrer_archivos_python(bases, incluir_archivos)
    proyecto: Dict[str, dict] = {}
    for ruta in archivos:
        try:
            info = analizar_archivo(ruta)
            proyecto[info.modulo] = {
                "ruta": ruta,
                "funciones": sorted(info.funciones),
                "imports": sorted(info.imports),
                "llamadas_por_funcion": {k: sorted(v) for k, v in info.llamadas_por_funcion.items()},
                "llamadas_toplevel": sorted(info.llamadas_toplevel),
                "llamadas_en_main": sorted(info.llamadas_en_main),
                "claves_session": sorted(info.claves_session),
            }
        except Exception as e:
            proyecto[nombre_modulo_relativo(ruta)] = {
                "ruta": ruta,
                "error_parseo": f"{type(e).__name__}: {e}",
                "funciones": [],
                "imports": [],
                "llamadas_por_funcion": {},
                "llamadas_toplevel": [],
                "llamadas_en_main": [],
                "claves_session": [],
            }
    return proyecto

def inferir_aristas_llamadas(proyecto: Dict[str, dict]) -> List[Tuple[str, str]]:
    # Heurística: si el nombre de función es único en el proyecto, conectamos mod.func -> mod2.func
    nombre_a_duenios: Dict[str, List[Tuple[str, str]]] = {}
    for mod, datos in proyecto.items():
        for f in datos.get("funciones", []):
            nombre_a_duenios.setdefault(f, []).append((mod, f))

    aristas: Set[Tuple[str, str]] = set()
    for mod, datos in proyecto.items():
        for llamante, llamados in datos.get("llamadas_por_funcion", {}).items():
            for llamado in llamados:
                duenos = nombre_a_duenios.get(llamado, [])
                if len(duenos) == 1:
                    tmod, tfunc = duenos[0]
                    aristas.add((f"{mod}.{llamante}", f"{tmod}.{tfunc}"))
    return sorted(aristas)

def filtrar_imports_internos(proyecto: Dict[str, dict]) -> List[Tuple[str, str]]:
    # Pares (módulo → módulo) solo entre módulos locales
    modulos = set(proyecto.keys())
    aristas = set()
    for mod, datos in proyecto.items():
        for imp in datos.get("imports", []):
            if imp in modulos:
                aristas.add((mod, imp))
                continue
            for local in modulos:
                if local.startswith(imp + "."):
                    aristas.add((mod, local))
    return sorted(aristas)

# ---------- Salidas ----------
def escribir_txt(proyecto: Dict[str, dict], aristas_llamadas, aristas_imports, ruta_salida: str):
    lineas = []
    lineas.append("MAPA AUTOMÁTICO DEL PROYECTO")
    lineas.append(f"Generado: {datetime.now():%Y-%m-%d %H:%M:%S}")
    lineas.append("=" * 100); lineas.append("")
    for mod, datos in sorted(proyecto.items()):
        lineas.append(f"📄 {mod}  ({datos.get('ruta','?')})")
        lineas.append("-" * 100)
        if "error_parseo" in datos:
            lineas.append(f"❌ Error de parseo: {datos['error_parseo']}")
        if datos.get("imports"):
            lineas.append("🔗 Imports:")
            lineas.append("   " + ", ".join(sorted(datos["imports"])))
        else:
            lineas.append("🔗 Imports: (ninguno)")
        if datos.get("funciones"):
            lineas.append(f"⚙️  Funciones ({len(datos['funciones'])}): " + ", ".join(datos["funciones"]))
        else:
            lineas.append("⚙️  (sin funciones definidas)")
        if datos.get("claves_session"):
            lineas.append("🔑 st.session_state keys: " + ", ".join(datos["claves_session"]))
        if datos.get("llamadas_toplevel"):
            lineas.append("▶️ Llamadas toplevel: " + ", ".join(datos["llamadas_toplevel"]))
        if datos.get("llamadas_en_main"):
            lineas.append("🚀 En __main__ llama a: " + ", ".join(datos["llamadas_en_main"]))
        if datos.get("llamadas_por_funcion"):
            lineas.append("📞 Llamadas por función:")
            for f, callee in sorted(datos["llamadas_por_funcion"].items()):
                if callee:
                    lineas.append(f"   - {f} → {', '.join(callee)}")
        lineas.append("")
    lineas.append("=" * 100)
    lineas.append("📊 Grafo de imports internos:")
    for a, b in aristas_imports:
        lineas.append(f"  - {a} → {b}")
    lineas.append("")
    lineas.append("🕸️ Call graph inferido:")
    for a, b in aristas_llamadas:
        lineas.append(f"  - {a} → {b}")
    with open(ruta_salida, "w", encoding="utf-8") as f:
        f.write("\n".join(lineas))
    print(f"✅ TXT: {ruta_salida}")

def escribir_json(proyecto: Dict[str, dict], aristas_llamadas, aristas_imports, ruta_salida: str):
    datos = {
        "generado_en": datetime.now().isoformat(),
        "proyecto": proyecto,
        "aristas_llamadas": aristas_llamadas,
        "aristas_imports": aristas_imports,
    }
    with open(ruta_salida, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
    print(f"✅ JSON: {ruta_salida}")

def escribir_dot(aristas: List[Tuple[str, str]], ruta_salida: str, dirigido: bool = True, etiqueta: str = ""):
    nodos = set()
    for a, b in aristas:
        nodos.add(a); nodos.add(b)
    tipo = "digraph" if dirigido else "graph"
    flecha = "->" if dirigido else "--"
    lineas = [f'{tipo} G {{', '  rankdir=LR;', '  node [shape=box, fontsize=10];']
    if etiqueta:
        lineas.append(f'  labelloc="t"; label="{etiqueta}";')
    for n in sorted(nodos):
        lineas.append(f'  "{n}";')
    for a, b in aristas:
        lineas.append(f'  "{a}" {flecha} "{b}";')
    lineas.append("}")
    with open(ruta_salida, "w", encoding="utf-8") as f:
        f.write("\n".join(lineas))
    print(f"✅ DOT: {ruta_salida}")

def depurar_imports(proyecto: Dict[str, dict]):
    import importlib
    print("\n--- Depuración de imports (puede ignorarse en CI) ---")
    for mod in sorted(proyecto.keys()):
        try:
            importlib.import_module(mod)
        except Exception as e:
            print(f"❌ ImportError en {mod}: {e}")

# ---------- Modo Streamlit (opcional) ----------
def renderizar_streamlit(proyecto, aristas_llamadas, aristas_imports):
    import streamlit as st
    st.set_page_config(page_title="Analizador", layout="wide")
    st.title("🔎 Análisis de Proyecto (módulos, funciones, imports)")
    st.caption(f"Generado: {datetime.now():%Y-%m-%d %H:%M:%S}")

    st.subheader("Resumen")
    st.write({
        "Módulos": len(proyecto),
        "Aristas de imports internos": len(aristas_imports),
        "Aristas de llamadas inferidas": len(aristas_llamadas),
    })

    st.subheader("Módulos")
    import pandas as pd
    filas = []
    for mod, d in sorted(proyecto.items()):
        filas.append({
            "módulo": mod,
            "ruta": d.get("ruta","?"),
            "funciones": ", ".join(d.get("funciones", [])),
            "imports": ", ".join(d.get("imports", [])),
            "keys_session": ", ".join(d.get("claves_session", [])),
            "llamadas_en_main": ", ".join(d.get("llamadas_en_main", [])),
            "error_parseo": d.get("error_parseo",""),
        })
    st.dataframe(pd.DataFrame(filas), use_container_width=True, hide_index=True)

    with st.expander("🕸️ Call graph (pares mod.func → mod.func)"):
        st.code("\n".join([f"{a} -> {b}" for a,b in aristas_llamadas]) or "(vacío)")
    with st.expander("📊 Imports internos (pares módulo → módulo)"):
        st.code("\n".join([f"{a} -> {b}" for a,b in aristas_imports]) or "(vacío)")

# ---------- Main ----------
def principal():
    ap = argparse.ArgumentParser(description="Analizador de flujo/funciones/imports del proyecto")
    ap.add_argument("--base", nargs="*", default=BASES_PREDETERMINADAS, help="Carpetas base a analizar (default: modulo)")
    ap.add_argument("--incluir", nargs="*", default=INCLUIR_PREDETERMINADOS, help="Archivos .py extra a incluir (default: app.py)")
    ap.add_argument("--salida", default=SALIDA_PREDETERMINADA, help="Reporte TXT (default: MAPA_FUNCIONES.txt)")
    ap.add_argument("--json", default="", help="Ruta opcional para JSON")
    ap.add_argument("--dot-imports", default="", help="Ruta DOT para grafo de imports internos")
    ap.add_argument("--dot-llamadas", default="", help="Ruta DOT para call graph")
    ap.add_argument("--depurar-imports", action="store_true", help="Intentar importar módulos y listar ImportError")
    ap.add_argument("--ui", action="store_true", help="Render Streamlit (si ejecutas con streamlit run ... -- --ui)")
    args = ap.parse_args()

    proyecto = construir_mapa_proyecto(args.base, args.incluir)
    aristas_imports = filtrar_imports_internos(proyecto)
    aristas_llamadas = inferir_aristas_llamadas(proyecto)

    # salidas de archivo (CLI)
    escribir_txt(proyecto, aristas_llamadas, aristas_imports, args.salida)
    if args.json:
        escribir_json(proyecto, aristas_llamadas, aristas_imports, args.json)
    if args.dot_imports:
        escribir_dot(aristas_imports, args.dot_imports, dirigido=True, etiqueta="Imports internos")
    if args.dot_llamadas:
        escribir_dot(aristas_llamadas, args.dot_llamadas, dirigido=True, etiqueta="Call graph")

    if args.depurar_imports:
        depurar_imports(proyecto)

    # UI opcional
    if args.ui:
        try:
            renderizar_streamlit(proyecto, aristas_llamadas, aristas_imports)
        except Exception:
            print("⚠️ No se pudo cargar la UI de Streamlit:")
            print(traceback.format_exc())

if __name__ == "__main__":
    principal()
