# -*- coding: utf-8 -*-
"""
analizador.py (compacto + útil)

Objetivo:
- Describir cómo está relacionada tu app (imports internos + call graph).
- Detectar ciclos de imports (SCC) y from-import rotos / alias.attr rotos.
- Exportar TXT + DIAG + opcional JSON/DOT + UI streamlit (opcional).

Uso:
  python analizador.py --base modulo interfaz core servicios exportadores --incluir app.py
  python analizador.py --base modulo interfaz core --incluir app.py --ui
"""

import os
import re
import ast
import json
import argparse
import traceback
from datetime import datetime
from typing import Dict, List, Set, Tuple, Optional, Any


# ==========================
# Config predeterminada
# ==========================
BASES_PREDETERMINADAS = ["modulo"]
INCLUIR_PREDETERMINADOS = ["app.py"]
SALIDA_PREDETERMINADA = "MAPA_FUNCIONES.txt"
DIAG_PREDETERMINADO = "DIAGNOSTICO_IMPORTS.txt"

PATRONES_SESSION_STATE = [
    r'st\.session_state\["([^"]+)"\]',
    r"st\.session_state\['([^']+)'\]",
    r"st\.session_state\.get\(\s*['\"]([^'\"]+)['\"]",
]


# ==========================
# Utilidades E/S
# ==========================
def leer_texto(ruta: str) -> str:
    with open(ruta, "r", encoding="utf-8") as f:
        return f.read()


def nombre_modulo_relativo(ruta: str) -> str:
    rel = os.path.relpath(ruta, start=".")
    rel = rel.replace("\\", "/")
    if rel.endswith(".py"):
        rel = rel[:-3]
    return rel.replace("/", ".")


def recorrer_archivos_python(bases: List[str], incluir_archivos: List[str]) -> List[str]:
    encontrados: List[str] = []
    for base in bases:
        if os.path.isdir(base):
            for raiz, _, archivos in os.walk(base):
                for a in archivos:
                    if a.endswith(".py"):
                        encontrados.append(os.path.join(raiz, a))
    for a in incluir_archivos:
        if os.path.isfile(a):
            encontrados.append(a)

    vistos, salida = set(), []
    for p in encontrados:
        ap = os.path.abspath(p)
        if ap not in vistos:
            vistos.add(ap)
            salida.append(ap)
    return sorted(salida)


def es_mayuscula_constante(name: str) -> bool:
    s = str(name).strip()
    return bool(s) and s.upper() == s and any(c.isalpha() for c in s)


# ==========================
# AST Parser
# ==========================
class InfoArchivo(ast.NodeVisitor):
    """
    Extrae:
      - símbolos definidos: funciones, clases, constantes (UPPERCASE)
      - imports detallados
      - session_state keys (regex)
      - llamadas por función y toplevel
      - llamadas dentro de if __name__ == "__main__"
    Llamadas capturadas como:
      - foo()          -> ("foo", None)
      - mx.foo()       -> ("mx", "foo")
      - a.b.c()        -> ("a.b", "c")
    """

    def __init__(self, modulo: str, fuente: str):
        self.modulo = modulo
        self.fuente = fuente

        self.funciones: Set[str] = set()
        self.clases: Set[str] = set()
        self.constantes: Set[str] = set()

        self.imports: Set[str] = set()
        self.imports_detallados: List[dict] = []

        self.llamadas_por_funcion: Dict[str, Set[Tuple[str, Optional[str]]]] = {}
        self.llamadas_toplevel: Set[Tuple[str, Optional[str]]] = set()
        self.llamadas_en_main: Set[Tuple[str, Optional[str]]] = set()

        self.claves_session: Set[str] = set()
        self._funcion_actual: Optional[str] = None

        for pat in PATRONES_SESSION_STATE:
            for m in re.findall(pat, fuente):
                self.claves_session.add(m)

    # --------- helpers ---------
    def _cadena_atributos(self, nodo) -> Optional[List[str]]:
        if isinstance(nodo, ast.Name):
            return [nodo.id]
        if isinstance(nodo, ast.Attribute):
            base = self._cadena_atributos(nodo.value)
            if not base:
                return [nodo.attr]
            return base + [nodo.attr]
        return None

    # --------- imports ---------
    def visit_Import(self, nodo: ast.Import):
        for alias in nodo.names:
            name = alias.name
            asname = alias.asname or ""
            self.imports.add(name)
            self.imports_detallados.append({"kind": "import", "module": name, "as": asname})
        self.generic_visit(nodo)

    def visit_ImportFrom(self, nodo: ast.ImportFrom):
        mod = nodo.module or ""
        if mod:
            self.imports.add(mod)
        names: List[Tuple[str, str]] = [(a.name, a.asname or "") for a in nodo.names]
        self.imports_detallados.append(
            {"kind": "from", "module": mod, "level": int(nodo.level or 0), "names": names}
        )
        self.generic_visit(nodo)

    # --------- defs ----------
    def visit_FunctionDef(self, nodo: ast.FunctionDef):
        self.funciones.add(nodo.name)
        prev = self._funcion_actual
        self._funcion_actual = nodo.name
        self.generic_visit(nodo)
        self._funcion_actual = prev

    def visit_AsyncFunctionDef(self, nodo: ast.AsyncFunctionDef):
        self.funciones.add(nodo.name)
        prev = self._funcion_actual
        self._funcion_actual = nodo.name
        self.generic_visit(nodo)
        self._funcion_actual = prev

    def visit_ClassDef(self, nodo: ast.ClassDef):
        self.clases.add(nodo.name)
        self.generic_visit(nodo)

    def visit_Assign(self, nodo: ast.Assign):
        if self._funcion_actual is None:
            for t in nodo.targets:
                if isinstance(t, ast.Name) and es_mayuscula_constante(t.id):
                    self.constantes.add(t.id)
        self.generic_visit(nodo)

    # --------- calls ----------
    def visit_Call(self, nodo: ast.Call):
        llamada: Optional[Tuple[str, Optional[str]]] = None
        chain = self._cadena_atributos(nodo.func)

        if chain and len(chain) == 1:
            llamada = (chain[0], None)
        elif chain and len(chain) >= 2:
            llamada = (".".join(chain[:-1]), chain[-1])

        if llamada:
            if self._funcion_actual:
                self.llamadas_por_funcion.setdefault(self._funcion_actual, set()).add(llamada)
            else:
                self.llamadas_toplevel.add(llamada)

        self.generic_visit(nodo)


def resolver_from_absoluto(modulo_actual: str, imp: dict) -> str:
    """
    from .x import y -> resuelve aproximado a módulo absoluto.
    """
    if imp.get("kind") != "from":
        return ""

    mod = (imp.get("module") or "").strip()
    level = int(imp.get("level") or 0)
    if level <= 0:
        return mod

    partes = modulo_actual.split(".")
    if partes:
        partes = partes[:-1]  # quitar archivo
    subir = min(level, len(partes))
    if subir > 0:
        partes = partes[:-subir]
    base = ".".join([p for p in partes if p])

    if not base:
        return mod
    if not mod:
        return base
    return base + "." + mod


def analizar_archivo(ruta: str) -> InfoArchivo:
    src = leer_texto(ruta)
    modulo = nombre_modulo_relativo(ruta)
    arbol = ast.parse(src, filename=ruta)

    info = InfoArchivo(modulo, src)
    info.visit(arbol)

    # detectar if __name__ == "__main__" y extraer calls dentro
    for nodo in arbol.body:
        if isinstance(nodo, ast.If) and isinstance(nodo.test, ast.Compare):
            left = nodo.test.left
            comps = nodo.test.comparators
            if (
                isinstance(left, ast.Name)
                and left.id == "__name__"
                and comps
                and isinstance(comps[0], ast.Constant)
                and comps[0].value == "__main__"
            ):

                class VisitanteMain(ast.NodeVisitor):
                    def __init__(self, cont: InfoArchivo):
                        self.c = cont

                    def _cadena_atributos(self, n):
                        if isinstance(n, ast.Name):
                            return [n.id]
                        if isinstance(n, ast.Attribute):
                            base = self._cadena_atributos(n.value)
                            if not base:
                                return [n.attr]
                            return base + [n.attr]
                        return None

                    def visit_Call(self, call: ast.Call):
                        chain = self._cadena_atributos(call.func)
                        if chain and len(chain) == 1:
                            self.c.llamadas_en_main.add((chain[0], None))
                        elif chain and len(chain) >= 2:
                            self.c.llamadas_en_main.add((".".join(chain[:-1]), chain[-1]))
                        self.generic_visit(call)

                vm = VisitanteMain(info)
                for stmt in nodo.body:
                    vm.visit(stmt)

    return info


# ==========================
# Construcción del mapa
# ==========================
def construir_mapa_proyecto(bases: List[str], incluir_archivos: List[str]) -> Dict[str, dict]:
    archivos = recorrer_archivos_python(bases, incluir_archivos)
    proyecto: Dict[str, dict] = {}

    for ruta in archivos:
        mod = nombre_modulo_relativo(ruta)
        try:
            info = analizar_archivo(ruta)
            proyecto[info.modulo] = {
                "ruta": ruta,
                "funciones": sorted(info.funciones),
                "clases": sorted(info.clases),
                "constantes": sorted(info.constantes),
                "imports": sorted(info.imports),
                "imports_detallados": info.imports_detallados,
                "llamadas_por_funcion": {k: sorted(list(v)) for k, v in info.llamadas_por_funcion.items()},
                "llamadas_toplevel": sorted(list(info.llamadas_toplevel)),
                "llamadas_en_main": sorted(list(info.llamadas_en_main)),
                "claves_session": sorted(info.claves_session),
            }
        except Exception as e:
            proyecto[mod] = {
                "ruta": ruta,
                "error_parseo": f"{type(e).__name__}: {e}",
                "funciones": [],
                "clases": [],
                "constantes": [],
                "imports": [],
                "imports_detallados": [],
                "llamadas_por_funcion": {},
                "llamadas_toplevel": [],
                "llamadas_en_main": [],
                "claves_session": [],
            }

    return proyecto


def indice_simbolos(proyecto: Dict[str, dict]) -> Dict[str, Set[str]]:
    out: Dict[str, Set[str]] = {}
    for mod, d in proyecto.items():
        out[mod] = set(d.get("funciones", [])) | set(d.get("clases", [])) | set(d.get("constantes", []))
    return out


def filtrar_imports_internos(proyecto: Dict[str, dict]) -> List[Tuple[str, str]]:
    modulos = set(proyecto.keys())
    aristas: Set[Tuple[str, str]] = set()

    for mod, datos in proyecto.items():
        for imp in datos.get("imports_detallados", []):
            if imp.get("kind") == "import":
                m = (imp.get("module") or "").strip()
                if m in modulos:
                    aristas.add((mod, m))
                else:
                    for local in modulos:
                        if local.startswith(m + "."):
                            aristas.add((mod, local))

            elif imp.get("kind") == "from":
                abs_mod = resolver_from_absoluto(mod, imp)
                if abs_mod in modulos:
                    aristas.add((mod, abs_mod))
                else:
                    for local in modulos:
                        if local.startswith(abs_mod + "."):
                            aristas.add((mod, local))

    return sorted(aristas)


def build_contexto_import(mod: str, datos: dict) -> dict:
    imported: Dict[str, str] = {}   # foo -> modulo_origen (from-import)
    alias_mod: Dict[str, str] = {}  # alias -> modulo (import X as alias)
    direct: Set[str] = set()        # import X (sin alias)

    for imp in datos.get("imports_detallados", []):
        kind = imp.get("kind")
        if kind == "import":
            m = (imp.get("module") or "").strip()
            a = (imp.get("as") or "").strip()
            if a:
                alias_mod[a] = m
            else:
                direct.add(m)

        elif kind == "from":
            abs_mod = resolver_from_absoluto(mod, imp)
            for name, asname in imp.get("names", []):
                if name == "*" or not name:
                    continue
                imported[(asname or name)] = abs_mod

    return {"imported": imported, "alias_mod": alias_mod, "direct": direct}


def inferir_aristas_llamadas(proyecto: Dict[str, dict]) -> List[Tuple[str, str]]:
    modulos = set(proyecto.keys())

    # fallback: dueño único por nombre (solo para foo())
    owners: Dict[str, List[Tuple[str, str]]] = {}
    for m, d in proyecto.items():
        for f in d.get("funciones", []):
            owners.setdefault(f, []).append((m, f))

    def resolver_base_a_modulo_local(base: str) -> Optional[str]:
        b = (base or "").strip()
        if not b:
            return None
        if b in modulos:
            return b
        # si base es prefijo de un módulo local (base.*)
        candidatos = [m for m in modulos if m.startswith(b + ".")]
        if candidatos:
            return sorted(candidatos, key=len)[0]
        return None

    aristas: Set[Tuple[str, str]] = set()

    for mod, datos in proyecto.items():
        if "error_parseo" in datos:
            continue

        ctx = build_contexto_import(mod, datos)
        imported = ctx["imported"]
        alias_mod = ctx["alias_mod"]

        for llamante, llamados in datos.get("llamadas_por_funcion", {}).items():
            origen = f"{mod}.{llamante}"
            for base, attr in llamados:
                # foo()
                if attr is None:
                    if base in imported:
                        aristas.add((origen, f"{imported[base]}.{base}"))
                        continue
                    duenos = owners.get(base, [])
                    if len(duenos) == 1:
                        tmod, tfunc = duenos[0]
                        aristas.add((origen, f"{tmod}.{tfunc}"))
                    continue

                # base.attr()
                if base in alias_mod:
                    aristas.add((origen, f"{alias_mod[base]}.{attr}"))
                    continue

                mod_local = resolver_base_a_modulo_local(base)
                if mod_local:
                    aristas.add((origen, f"{mod_local}.{attr}"))
                    continue

    return sorted(aristas)


# ==========================
# SCC (Tarjan)
# ==========================
def tarjan_scc(nodes: List[str], edges: List[Tuple[str, str]]) -> List[List[str]]:
    g: Dict[str, List[str]] = {n: [] for n in nodes}
    for a, b in edges:
        if a in g:
            g[a].append(b)

    index = 0
    stack: List[str] = []
    onstack: Set[str] = set()
    idx: Dict[str, int] = {}
    low: Dict[str, int] = {}
    sccs: List[List[str]] = []

    def strongconnect(v: str):
        nonlocal index
        idx[v] = index
        low[v] = index
        index += 1
        stack.append(v)
        onstack.add(v)

        for w in g.get(v, []):
            if w not in idx:
                strongconnect(w)
                low[v] = min(low[v], low[w])
            elif w in onstack:
                low[v] = min(low[v], idx[w])

        if low[v] == idx[v]:
            comp: List[str] = []
            while True:
                w = stack.pop()
                onstack.remove(w)
                comp.append(w)
                if w == v:
                    break
            sccs.append(list(reversed(comp)))

    for n in nodes:
        if n not in idx:
            strongconnect(n)

    # filtrar ciclos reales
    edge_set = set(edges)
    out: List[List[str]] = []
    for comp in sccs:
        if len(comp) > 1:
            out.append(comp)
        elif len(comp) == 1 and (comp[0], comp[0]) in edge_set:
            out.append(comp)
    return out


# ==========================
# Diagnóstico imports rotos
# ==========================
def diagnosticar_imports(proyecto: Dict[str, dict]) -> Dict[str, Any]:
    modulos = set(proyecto.keys())
    symbols_by_mod = indice_simbolos(proyecto)

    owners: Dict[str, List[str]] = {}
    for m, syms in symbols_by_mod.items():
        for s in syms:
            owners.setdefault(s, []).append(m)

    rotos_from: List[dict] = []
    rotos_alias_attr: List[dict] = []

    for mod, d in proyecto.items():
        if "error_parseo" in d:
            continue

        ctx = build_contexto_import(mod, d)
        alias_modules = ctx["alias_mod"]

        # 1) from X import Y (X local)
        for imp in d.get("imports_detallados", []):
            if imp.get("kind") != "from":
                continue
            abs_from = resolver_from_absoluto(mod, imp)
            if abs_from not in modulos:
                continue

            defined = symbols_by_mod.get(abs_from, set())
            for name, asname in imp.get("names", []):
                if name == "*" or not name:
                    continue
                if name not in defined:
                    rotos_from.append({
                        "archivo": mod,
                        "from_mod": abs_from,
                        "symbol": name,
                        "as": asname or "",
                        "sugerencias": owners.get(name, [])[:10],
                    })

        # 2) alias.attr() (alias -> módulo local), verificar attr existe
        for llamante, llamados in d.get("llamadas_por_funcion", {}).items():
            for base, attr in llamados:
                if attr is None:
                    continue
                if base not in alias_modules:
                    continue
                target_mod = alias_modules[base]
                if target_mod in modulos:
                    defined = symbols_by_mod.get(target_mod, set())
                    if attr not in defined:
                        rotos_alias_attr.append({
                            "archivo": mod,
                            "funcion": llamante,
                            "alias": base,
                            "target_mod": target_mod,
                            "attr": attr,
                            "sugerencias": owners.get(attr, [])[:10],
                        })

    aristas_imports = filtrar_imports_internos(proyecto)
    ciclos = tarjan_scc(sorted(list(modulos)), aristas_imports)

    return {
        "rotos_from_import": rotos_from,
        "rotos_alias_attr": rotos_alias_attr,
        "ciclos_import": ciclos,
        "aristas_imports": aristas_imports,
    }


# ==========================
# Salidas
# ==========================
def escribir_txt(proyecto: Dict[str, dict],
                aristas_llamadas: List[Tuple[str, str]],
                aristas_imports: List[Tuple[str, str]],
                ruta_salida: str):

    now = datetime.now()
    lineas: List[str] = []
    lineas.append("MAPA AUTOMÁTICO DEL PROYECTO")
    lineas.append(f"Generado: {now:%Y-%m-%d %H:%M:%S}")
    lineas.append("=" * 100)
    lineas.append("")

    for mod, datos in sorted(proyecto.items()):
        lineas.append(f"📄 {mod}  ({datos.get('ruta','?')})")
        lineas.append("-" * 100)

        if "error_parseo" in datos:
            lineas.append(f"❌ Error de parseo: {datos['error_parseo']}")
            lineas.append("")
            continue

        imps = datos.get("imports", [])
        lineas.append("🔗 Imports: " + (", ".join(imps) if imps else "(ninguno)"))

        funcs = datos.get("funciones", [])
        clases = datos.get("clases", [])
        consts = datos.get("constantes", [])

        lineas.append(f"⚙️  Funciones ({len(funcs)}): " + (", ".join(funcs) if funcs else "(ninguna)"))
        if clases:
            lineas.append(f"🏷️  Clases ({len(clases)}): " + ", ".join(clases))
        if consts:
            lineas.append(f"🔒 Constantes ({len(consts)}): " + ", ".join(consts))

        if datos.get("claves_session"):
            lineas.append("🔑 st.session_state keys: " + ", ".join(datos["claves_session"]))

        if datos.get("llamadas_toplevel"):
            lineas.append("▶️ Llamadas toplevel: " + ", ".join([f"{a}.{b}" if b else a for a, b in datos["llamadas_toplevel"]]))
        if datos.get("llamadas_en_main"):
            lineas.append("🚀 En __main__ llama a: " + ", ".join([f"{a}.{b}" if b else a for a, b in datos["llamadas_en_main"]]))

        if datos.get("llamadas_por_funcion"):
            lineas.append("📞 Llamadas por función:")
            for f, callees in sorted(datos["llamadas_por_funcion"].items()):
                if callees:
                    ctxt = ", ".join([f"{a}.{b}" if b else a for a, b in callees])
                    lineas.append(f"   - {f} → {ctxt}")

        lineas.append("")

    lineas.append("=" * 100)
    lineas.append("📊 Grafo de imports internos (módulo → módulo):")
    for a, b in aristas_imports:
        lineas.append(f"  - {a} → {b}")

    lineas.append("")
    lineas.append("🕸️ Call graph inferido (mod.func → mod.func):")
    for a, b in aristas_llamadas:
        lineas.append(f"  - {a} → {b}")

    with open(ruta_salida, "w", encoding="utf-8") as f:
        f.write("\n".join(lineas))
    print(f"✅ TXT: {ruta_salida}")


def escribir_diag(diag: Dict[str, Any], ruta_salida: str):
    now = datetime.now()
    lineas: List[str] = []
    lineas.append("DIAGNÓSTICO DE IMPORTS / ACOPLAMIENTO")
    lineas.append(f"Generado: {now:%Y-%m-%d %H:%M:%S}")
    lineas.append("=" * 100)
    lineas.append("")

    ciclos = diag.get("ciclos_import", [])
    if ciclos:
        lineas.append("♻️  Ciclos de import detectados (SCC):")
        for i, comp in enumerate(ciclos, 1):
            if len(comp) == 1:
                lineas.append(f"  {i:02d}) {comp[0]} ↺")
            else:
                lineas.append(f"  {i:02d}) " + " → ".join(comp) + " → " + comp[0])
        lineas.append("")
    else:
        lineas.append("♻️  Ciclos de import: (no se detectaron)\n")

    rotos_from = diag.get("rotos_from_import", [])
    if rotos_from:
        lineas.append("❌ from-import rotos (símbolo no existe en módulo):")
        for x in rotos_from:
            sug = x.get("sugerencias", [])
            sug_txt = (" | sugerencias: " + ", ".join(sug)) if sug else ""
            alias = f" as {x['as']}" if x.get("as") else ""
            lineas.append(f"  - {x['archivo']}: from {x['from_mod']} import {x['symbol']}{alias}{sug_txt}")
        lineas.append("")
    else:
        lineas.append("❌ from-import rotos: (no encontrados)\n")

    rotos_alias = diag.get("rotos_alias_attr", [])
    if rotos_alias:
        lineas.append("❌ alias.attr() rotos (attr no existe en módulo importado con alias):")
        for x in rotos_alias:
            sug = x.get("sugerencias", [])
            sug_txt = (" | sugerencias: " + ", ".join(sug)) if sug else ""
            lineas.append(
                f"  - {x['archivo']}::{x['funcion']}: {x['alias']}.{x['attr']} "
                f"(alias -> {x['target_mod']}){sug_txt}"
            )
        lineas.append("")
    else:
        lineas.append("❌ alias.attr() rotos: (no encontrados)\n")

    with open(ruta_salida, "w", encoding="utf-8") as f:
        f.write("\n".join(lineas))
    print(f"✅ DIAG: {ruta_salida}")


def escribir_json(proyecto: Dict[str, dict],
                 aristas_llamadas,
                 aristas_imports,
                 diag: Dict[str, Any],
                 ruta_salida: str):
    datos = {
        "generado_en": datetime.now().isoformat(),
        "proyecto": proyecto,
        "aristas_llamadas": aristas_llamadas,
        "aristas_imports": aristas_imports,
        "diagnostico": diag,
    }
    with open(ruta_salida, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
    print(f"✅ JSON: {ruta_salida}")


def escribir_dot(aristas: List[Tuple[str, str]], ruta_salida: str, dirigido: bool = True, etiqueta: str = ""):
    nodos = set()
    for a, b in aristas:
        nodos.add(a)
        nodos.add(b)
    tipo = "digraph" if dirigido else "graph"
    flecha = "->" if dirigido else "--"

    lineas = [f"{tipo} G {{", "  rankdir=LR;", "  node [shape=box, fontsize=10];"]
    if etiqueta:
        et = etiqueta.replace('"', '\\"')
        lineas.append(f'  labelloc="t"; label="{et}";')

    for n in sorted(nodos):
        nn = n.replace('"', '\\"')
        lineas.append(f'  "{nn}";')
    for a, b in aristas:
        aa = a.replace('"', '\\"')
        bb = b.replace('"', '\\"')
        lineas.append(f'  "{aa}" {flecha} "{bb}";')
    lineas.append("}")

    with open(ruta_salida, "w", encoding="utf-8") as f:
        f.write("\n".join(lineas))
    print(f"✅ DOT: {ruta_salida}")


def depurar_imports(proyecto: Dict[str, dict]):
    import importlib
    print("\n--- Depuración de imports ---")
    for mod in sorted(proyecto.keys()):
        try:
            importlib.import_module(mod)
        except Exception as e:
            print(f"❌ ImportError en {mod}: {e}")


# ==========================
# UI Streamlit (opcional)
# ==========================
def renderizar_streamlit(proyecto, aristas_llamadas, aristas_imports, diag):
    import streamlit as st

    st.set_page_config(page_title="Analizador", layout="wide")
    st.title("🔎 Analizador (imports, símbolos, llamadas, diagnóstico)")
    st.caption(f"Generado: {datetime.now():%Y-%m-%d %H:%M:%S}")

    st.subheader("Resumen")
    st.write({
        "Módulos": len(proyecto),
        "Aristas imports internos": len(aristas_imports),
        "Aristas llamadas (inferidas)": len(aristas_llamadas),
        "Ciclos import": len(diag.get("ciclos_import", [])),
        "from-import rotos": len(diag.get("rotos_from_import", [])),
        "alias.attr rotos": len(diag.get("rotos_alias_attr", [])),
    })

    with st.expander("♻️ Ciclos de import"):
        ciclos = diag.get("ciclos_import", [])
        st.code("\n".join(
            [(" → ".join(c) + " → " + c[0]) if len(c) > 1 else (c[0] + " ↺") for c in ciclos]
        ) or "(ninguno)")

    with st.expander("❌ from-import rotos"):
        rotos = diag.get("rotos_from_import", [])
        st.code("\n".join([
            f"{r['archivo']}: from {r['from_mod']} import {r['symbol']}"
            + (f" as {r['as']}" if r.get("as") else "")
            + (f" | sugerencias: {', '.join(r.get('sugerencias', []))}" if r.get("sugerencias") else "")
            for r in rotos
        ]) or "(ninguno)")

    with st.expander("❌ alias.attr rotos"):
        rotos = diag.get("rotos_alias_attr", [])
        st.code("\n".join([
            f"{r['archivo']}::{r['funcion']}: {r['alias']}.{r['attr']} (alias -> {r['target_mod']})"
            + (f" | sugerencias: {', '.join(r.get('sugerencias', []))}" if r.get("sugerencias") else "")
            for r in rotos
        ]) or "(ninguno)")

    with st.expander("📊 Imports internos"):
        st.code("\n".join([f"{a} -> {b}" for a, b in aristas_imports]) or "(vacío)")

    with st.expander("🕸️ Call graph (mod.func -> mod.func)"):
        st.code("\n".join([f"{a} -> {b}" for a, b in aristas_llamadas]) or "(vacío)")


# ==========================
# Main
# ==========================
def principal():
    ap = argparse.ArgumentParser(description="Analizador de proyecto (imports/símbolos/calls + diagnóstico)")
    ap.add_argument("--base", nargs="*", default=BASES_PREDETERMINADAS,
                    help="Carpetas base (ej: modulo interfaz core servicios exportadores)")
    ap.add_argument("--incluir", nargs="*", default=INCLUIR_PREDETERMINADOS,
                    help="Archivos .py extra (default: app.py)")
    ap.add_argument("--salida", default=SALIDA_PREDETERMINADA,
                    help="Reporte TXT principal")
    ap.add_argument("--diag", default=DIAG_PREDETERMINADO,
                    help="Reporte TXT diagnóstico")
    ap.add_argument("--json", default="", help="Ruta opcional JSON")
    ap.add_argument("--dot-imports", default="", help="Ruta DOT imports internos")
    ap.add_argument("--dot-llamadas", default="", help="Ruta DOT call graph")
    ap.add_argument("--depurar-imports", action="store_true", help="Intentar importar módulos (diagnóstico runtime)")
    ap.add_argument("--ui", action="store_true", help="Render Streamlit (streamlit run ... -- --ui)")
    args = ap.parse_args()

    proyecto = construir_mapa_proyecto(args.base, args.incluir)
    aristas_imports = filtrar_imports_internos(proyecto)
    aristas_llamadas = inferir_aristas_llamadas(proyecto)
    diag = diagnosticar_imports(proyecto)

    escribir_txt(proyecto, aristas_llamadas, aristas_imports, args.salida)
    escribir_diag(diag, args.diag)

    if args.json:
        escribir_json(proyecto, aristas_llamadas, aristas_imports, diag, args.json)
    if args.dot_imports:
        escribir_dot(aristas_imports, args.dot_imports, dirigido=True, etiqueta="Imports internos")
    if args.dot_llamadas:
        escribir_dot(aristas_llamadas, args.dot_llamadas, dirigido=True, etiqueta="Call graph")

    if args.depurar_imports:
        depurar_imports(proyecto)

    if args.ui:
        try:
            renderizar_streamlit(proyecto, aristas_llamadas, aristas_imports, diag)
        except Exception:
            print("⚠️ No se pudo cargar la UI de Streamlit:")
            print(traceback.format_exc())


if __name__ == "__main__":
    principal()
