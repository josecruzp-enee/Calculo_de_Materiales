# -*- coding: utf-8 -*-
"""
analizador.py  (versión +potente)

Qué agrega vs tu versión:
✅ 1) Imports detallados (import/from import + alias + símbolos)
✅ 2) Mapa de símbolos por módulo: funciones, clases, constantes (UPPERCASE)
✅ 3) Detección de ciclos de import (SCC) + reporte legible
✅ 4) Call graph mejorado (resuelve llamadas a funciones importadas y alias tipo mx.foo())
✅ 5) Diagnóstico de imports rotos:
      - "from X import Y" pero Y no existe en X
      - "import X as a" y luego "a.foo()" pero foo no existe en X (si X es local)
✅ 6) Reporte extra: DIAGNOSTICO_IMPORTS.txt

Uso (CLI):
    python analizador.py --base modulo core servicios interfaz exportadores --incluir app.py \
        --salida MAPA_FUNCIONES.txt --diag DIAGNOSTICO_IMPORTS.txt \
        --json MAPA_FUNCIONES.json \
        --dot-imports imports.dot --dot-llamadas llamadas.dot

Uso (Streamlit):
    streamlit run analizador.py -- --base modulo core servicios interfaz exportadores --incluir app.py --ui
"""

import os
import re
import ast
import json
import argparse
import traceback
from datetime import datetime
from typing import Dict, List, Set, Tuple, Optional, Any


# ---------- Config predeterminada ----------
BASES_PREDETERMINADAS = ["modulo"]
INCLUIR_PREDETERMINADOS = ["app.py"]
SALIDA_PREDETERMINADA = "MAPA_FUNCIONES.txt"
DIAG_PREDETERMINADO = "DIAGNOSTICO_IMPORTS.txt"

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


def _is_upper_name(name: str) -> bool:
    s = str(name).strip()
    return bool(s) and s.upper() == s and any(c.isalpha() for c in s)


# ---------- AST Parser ----------
class InfoArchivo(ast.NodeVisitor):
    """
    Extrae:
      - imports simples + imports detallados
      - funciones/clases/constantes (UPPERCASE)
      - session_state keys (regex)
      - llamadas por función (captura nombres y atributos)
      - llamadas en __main__
      - además: "usos de alias" a nivel de atributos (a.foo)
    """

    def __init__(self, modulo: str, fuente: str):
        self.modulo = modulo
        self.fuente = fuente

        # símbolos definidos en el archivo
        self.funciones: Set[str] = set()
        self.clases: Set[str] = set()
        self.constantes: Set[str] = set()

        # imports: lista simple (como antes) + detallado
        self.imports: Set[str] = set()
        # Ejemplo: {"kind":"from","module":"modulo.x","names":[("foo",None),("bar","b")]}
        #          {"kind":"import","module":"pandas","as":"pd"}
        self.imports_detallados: List[dict] = []

        # calls
        self.llamadas_por_funcion: Dict[str, Set[Tuple[str, Optional[str]]]] = {}
        # cada llamada la guardamos como:
        #   ("foo", None) para foo()
        #   ("mx", "bar") para mx.bar()
        self.llamadas_toplevel: Set[Tuple[str, Optional[str]]] = set()
        self.llamadas_en_main: Set[Tuple[str, Optional[str]]] = set()

        # session_state
        self.claves_session: Set[str] = set()

        self._funcion_actual: Optional[str] = None

        # claves de session_state por regex (complemento al AST)
        for pat in PATRONES_SESSION_STATE:
            for m in re.findall(pat, fuente):
                self.claves_session.add(m)

    # ---------------- imports ----------------
    def visit_Import(self, nodo: ast.Import):
        for alias in nodo.names:
            name = alias.name
            asname = alias.asname
            self.imports.add(name)
            self.imports_detallados.append(
                {"kind": "import", "module": name, "as": asname or ""}
            )
        self.generic_visit(nodo)

    def visit_ImportFrom(self, nodo: ast.ImportFrom):
        mod = nodo.module or ""
        if mod:
            self.imports.add(mod)
        names: List[Tuple[str, str]] = []
        for alias in nodo.names:
            # alias.name puede ser "*"
            names.append((alias.name, alias.asname or ""))
        self.imports_detallados.append(
            {"kind": "from", "module": mod, "level": int(nodo.level or 0), "names": names}
        )
        self.generic_visit(nodo)

    # --------------- defs --------------------
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

    def visit_ClassDef(self, nodo: ast.ClassDef):
        self.clases.add(nodo.name)
        self.generic_visit(nodo)

    def visit_Assign(self, nodo: ast.Assign):
        # constantes top-level: UPPERCASE = ...
        if self._funcion_actual is None:
            for t in nodo.targets:
                if isinstance(t, ast.Name) and _is_upper_name(t.id):
                    self.constantes.add(t.id)
        self.generic_visit(nodo)

    # --------------- calls -------------------
    def visit_Call(self, nodo: ast.Call):
        llamada: Optional[Tuple[str, Optional[str]]] = None

        # foo()
        if isinstance(nodo.func, ast.Name):
            llamada = (nodo.func.id, None)

        # mx.foo()
        elif isinstance(nodo.func, ast.Attribute):
            # nodo.func.value puede ser Name (mx) u otro (obj.attr.attr)
            if isinstance(nodo.func.value, ast.Name):
                llamada = (nodo.func.value.id, nodo.func.attr)
            else:
                # capturamos al menos el attr final
                llamada = (nodo.func.attr, None)

        if llamada:
            if self._funcion_actual:
                self.llamadas_por_funcion.setdefault(self._funcion_actual, set()).add(llamada)
            else:
                self.llamadas_toplevel.add(llamada)

        self.generic_visit(nodo)


def _resolver_importfrom_absoluto(modulo_actual: str, imp: dict) -> str:
    """
    Convierte imports relativos 'from .x import y' a módulo absoluto aproximado:
      - modulo_actual: "modulo.sub.archivo"
      - level=1: sube 1 paquete -> "modulo.sub"
      - + module: "x" -> "modulo.sub.x"
    Nota: es heurístico y suficiente para proyectos python-package típicos.
    """
    kind = imp.get("kind")
    if kind != "from":
        return ""

    mod = imp.get("module", "") or ""
    level = int(imp.get("level") or 0)
    if level <= 0:
        return mod

    partes = modulo_actual.split(".")
    # quitar el último segmento (archivo)
    if partes:
        partes = partes[:-1]
    # subir 'level' paquetes
    subir = max(level, 0)
    if subir > 0:
        partes = partes[:-subir] if subir <= len(partes) else []
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
                                    tup = None
                                    if isinstance(llamada.func, ast.Name):
                                        tup = (llamada.func.id, None)
                                    elif isinstance(llamada.func, ast.Attribute):
                                        if isinstance(llamada.func.value, ast.Name):
                                            tup = (llamada.func.value.id, llamada.func.attr)
                                        else:
                                            tup = (llamada.func.attr, None)
                                    if tup:
                                        self.c.llamadas_en_main.add(tup)
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
            proyecto[nombre_modulo_relativo(ruta)] = {
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


def _indice_simbolos(proyecto: Dict[str, dict]) -> Dict[str, Set[str]]:
    """
    Devuelve dict: modulo -> set(symbols definidos)
    """
    out: Dict[str, Set[str]] = {}
    for mod, d in proyecto.items():
        syms = set(d.get("funciones", [])) | set(d.get("clases", [])) | set(d.get("constantes", []))
        out[mod] = syms
    return out


def filtrar_imports_internos(proyecto: Dict[str, dict]) -> List[Tuple[str, str]]:
    """
    Imports internos (módulo → módulo) solo entre módulos locales.
    Ahora usa imports_detallados y resuelve from-import relativo.
    """
    modulos = set(proyecto.keys())
    aristas = set()

    for mod, datos in proyecto.items():
        # usar detallados (mejor)
        for imp in datos.get("imports_detallados", []):
            if imp.get("kind") == "import":
                m = imp.get("module", "")
                # match directo o prefijo
                if m in modulos:
                    aristas.add((mod, m))
                else:
                    for local in modulos:
                        if local.startswith(m + "."):
                            aristas.add((mod, local))
            elif imp.get("kind") == "from":
                abs_mod = _resolver_importfrom_absoluto(mod, imp)
                if abs_mod in modulos:
                    aristas.add((mod, abs_mod))
                else:
                    for local in modulos:
                        if local.startswith(abs_mod + "."):
                            aristas.add((mod, local))

    return sorted(aristas)


def _build_import_context(mod: str, datos: dict) -> dict:
    """
    Construye contexto de import para resolver llamadas:
      - imported_funcs: nombre -> modulo_origen (solo from-import)
      - alias_modules: alias -> modulo (import X as a) / (from X import Y as a, si Y es módulo local)
      - direct_modules: set(modulos importados sin alias) (import X)
    """
    imported_funcs: Dict[str, str] = {}
    alias_modules: Dict[str, str] = {}
    direct_modules: Set[str] = set()

    for imp in datos.get("imports_detallados", []):
        kind = imp.get("kind")
        if kind == "import":
            m = imp.get("module", "") or ""
            a = imp.get("as", "") or ""
            if a:
                alias_modules[a] = m
            else:
                direct_modules.add(m)
        elif kind == "from":
            abs_mod = _resolver_importfrom_absoluto(mod, imp)
            for name, asname in imp.get("names", []):
                if name == "*":
                    continue
                local_name = asname or name
                imported_funcs[local_name] = abs_mod

    return {
        "imported_funcs": imported_funcs,
        "alias_modules": alias_modules,
        "direct_modules": direct_modules,
    }


def inferir_aristas_llamadas(proyecto: Dict[str, dict]) -> List[Tuple[str, str]]:
    """
    Call graph mejorado:
    - Si llamó foo() y foo vino por "from X import foo", conectamos mod.f -> X.foo
    - Si llamó alias.foo() y alias vino de "import X as alias", conectamos mod.f -> X.foo
    - Si no se puede resolver: fallback a tu heurística de "nombre único"
    """
    # dueños por nombre (fallback)
    nombre_a_duenios: Dict[str, List[Tuple[str, str]]] = {}
    for mod, datos in proyecto.items():
        for f in datos.get("funciones", []):
            nombre_a_duenios.setdefault(f, []).append((mod, f))

    aristas: Set[Tuple[str, str]] = set()

    for mod, datos in proyecto.items():
        ctx = _build_import_context(mod, datos)

        imported_funcs = ctx["imported_funcs"]
        alias_modules = ctx["alias_modules"]

        for llamante, llamados in datos.get("llamadas_por_funcion", {}).items():
            for base, attr in llamados:
                # caso foo()
                if attr is None:
                    # resolver si viene de from-import
                    if base in imported_funcs:
                        origen = imported_funcs[base]
                        aristas.add((f"{mod}.{llamante}", f"{origen}.{base}"))
                        continue

                    # fallback si es único
                    duenos = nombre_a_duenios.get(base, [])
                    if len(duenos) == 1:
                        tmod, tfunc = duenos[0]
                        aristas.add((f"{mod}.{llamante}", f"{tmod}.{tfunc}"))
                    continue

                # caso alias.foo()
                if base in alias_modules:
                    origen_mod = alias_modules[base]
                    aristas.add((f"{mod}.{llamante}", f"{origen_mod}.{attr}"))
                    continue

                # si hacen "X.foo()" sin alias (import X)
                # es más raro porque base sería "X" (Name) y attr sería foo
                # pero sin map de "X" a módulo real no podemos asegurar; lo dejamos sin resolver

    return sorted(aristas)


# ---------- Ciclos de import (SCC Tarjan) ----------
def _tarjan_scc(nodes: List[str], edges: List[Tuple[str, str]]) -> List[List[str]]:
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

    # solo ciclos reales: tamaño>1 o self-loop
    out: List[List[str]] = []
    edge_set = set(edges)
    for comp in sccs:
        if len(comp) > 1:
            out.append(comp)
        elif len(comp) == 1:
            v = comp[0]
            if (v, v) in edge_set:
                out.append(comp)
    return out


# ---------- Diagnóstico de imports rotos ----------
def diagnosticar_imports(proyecto: Dict[str, dict]) -> Dict[str, Any]:
    """
    Retorna dict con:
      - rotos_from_import: lista de (mod_archivo, from_mod, symbol, sugerencias)
      - rotos_alias_attr: lista de (mod_archivo, alias, target_mod, attr, sugerencias)
      - ciclos_import: lista de SCCs
    """
    modulos = set(proyecto.keys())
    symbols_by_mod = _indice_simbolos(proyecto)

    rotos_from: List[dict] = []
    rotos_alias_attr: List[dict] = []

    # índice inverso: símbolo -> módulos que lo definen
    owners: Dict[str, List[str]] = {}
    for m, syms in symbols_by_mod.items():
        for s in syms:
            owners.setdefault(s, []).append(m)

    # analizar archivo por archivo
    for mod, d in proyecto.items():
        if "error_parseo" in d:
            continue

        ctx = _build_import_context(mod, d)

        # 1) from X import Y
        for imp in d.get("imports_detallados", []):
            if imp.get("kind") != "from":
                continue
            abs_from = _resolver_importfrom_absoluto(mod, imp)
            if not abs_from:
                continue
            # solo chequeamos si el módulo from es local (existe en el proyecto)
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

        # 2) alias.foo() cuando alias viene de "import X as alias"
        alias_modules = ctx["alias_modules"]
        for llamante, llamados in d.get("llamadas_por_funcion", {}).items():
            for base, attr in llamados:
                if attr is None:
                    continue
                if base not in alias_modules:
                    continue
                target_mod = alias_modules[base]
                # si target_mod es local, podemos verificar attr existe
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

    # ciclos de import
    aristas_imports = filtrar_imports_internos(proyecto)
    sccs = _tarjan_scc(sorted(list(modulos)), aristas_imports)

    return {
        "rotos_from_import": rotos_from,
        "rotos_alias_attr": rotos_alias_attr,
        "ciclos_import": sccs,
        "aristas_imports": aristas_imports,
    }


# ---------- Salidas ----------
def escribir_txt(
    proyecto: Dict[str, dict],
    aristas_llamadas: List[Tuple[str, str]],
    aristas_imports: List[Tuple[str, str]],
    ruta_salida: str
):
    lineas: List[str] = []
    lineas.append("MAPA AUTOMÁTICO DEL PROYECTO")
    lineas.append(f"Generado: {datetime.now():%Y-%m-%d %H:%M:%S}")
    lineas.append("=" * 100)
    lineas.append("")

    for mod, datos in sorted(proyecto.items()):
        lineas.append(f"📄 {mod}  ({datos.get('ruta','?')})")
        lineas.append("-" * 100)

        if "error_parseo" in datos:
            lineas.append(f"❌ Error de parseo: {datos['error_parseo']}")
            lineas.append("")
            continue

        # imports
        if datos.get("imports"):
            lineas.append("🔗 Imports:")
            lineas.append("   " + ", ".join(sorted(datos["imports"])))
        else:
            lineas.append("🔗 Imports: (ninguno)")

        # símbolos
        funcs = datos.get("funciones", [])
        clases = datos.get("clases", [])
        consts = datos.get("constantes", [])

        if funcs:
            lineas.append(f"⚙️  Funciones ({len(funcs)}): " + ", ".join(funcs))
        else:
            lineas.append("⚙️  Funciones: (ninguna)")

        if clases:
            lineas.append(f"🏷️  Clases ({len(clases)}): " + ", ".join(clases))

        if consts:
            lineas.append(f"🔒 Constantes ({len(consts)}): " + ", ".join(consts))

        # session_state
        if datos.get("claves_session"):
            lineas.append("🔑 st.session_state keys: " + ", ".join(datos["claves_session"]))

        # llamadas
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
    lineas: List[str] = []
    lineas.append("DIAGNÓSTICO DE IMPORTS / ACOPLAMIENTO")
    lineas.append(f"Generado: {datetime.now():%Y-%m-%d %H:%M:%S}")
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
        lineas.append("♻️  Ciclos de import: (no se detectaron)")
        lineas.append("")

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
        lineas.append("❌ from-import rotos: (no encontrados)")
        lineas.append("")

    rotos_alias = diag.get("rotos_alias_attr", [])
    if rotos_alias:
        lineas.append("❌ alias.attr() rotos (attr no existe en módulo importado con alias):")
        for x in rotos_alias:
            sug = x.get("sugerencias", [])
            sug_txt = (" | sugerencias: " + ", ".join(sug)) if sug else ""
            lineas.append(
                f"  - {x['archivo']}::{x['funcion']}: {x['alias']}.{x['attr']}  "
                f"(alias -> {x['target_mod']}){sug_txt}"
            )
        lineas.append("")
    else:
        lineas.append("❌ alias.attr() rotos: (no encontrados)")
        lineas.append("")

    with open(ruta_salida, "w", encoding="utf-8") as f:
        f.write("\n".join(lineas))
    print(f"✅ DIAG: {ruta_salida}")


def escribir_json(proyecto: Dict[str, dict], aristas_llamadas, aristas_imports, diag: Dict[str, Any], ruta_salida: str):
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
        # escapar comillas básicas
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
    print("\n--- Depuración de imports (puede ignorarse en CI) ---")
    for mod in sorted(proyecto.keys()):
        try:
            importlib.import_module(mod)
        except Exception as e:
            print(f"❌ ImportError en {mod}: {e}")


# ---------- Modo Streamlit (opcional) ----------
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

    st.subheader("Diagnóstico")
    with st.expander("♻️ Ciclos de import"):
        ciclos = diag.get("ciclos_import", [])
        if not ciclos:
            st.info("No se detectaron ciclos.")
        else:
            st.code("\n".join(
                [(" → ".join(c) + " → " + c[0]) if len(c) > 1 else (c[0] + " ↺")
                 for c in ciclos]
            ))

    with st.expander("❌ from-import rotos"):
        rotos = diag.get("rotos_from_import", [])
        if not rotos:
            st.info("No se encontraron.")
        else:
            st.code("\n".join([
                f"{r['archivo']}: from {r['from_mod']} import {r['symbol']}"
                + (f" as {r['as']}" if r.get("as") else "")
                + (f" | sugerencias: {', '.join(r.get('sugerencias', []))}" if r.get("sugerencias") else "")
                for r in rotos
            ]))

    with st.expander("❌ alias.attr rotos"):
        rotos = diag.get("rotos_alias_attr", [])
        if not rotos:
            st.info("No se encontraron.")
        else:
            st.code("\n".join([
                f"{r['archivo']}::{r['funcion']}: {r['alias']}.{r['attr']} (alias -> {r['target_mod']})"
                + (f" | sugerencias: {', '.join(r.get('sugerencias', []))}" if r.get("sugerencias") else "")
                for r in rotos
            ]))

    st.subheader("Módulos (tabla)")
    import pandas as pd
    filas = []
    for mod, d in sorted(proyecto.items()):
        filas.append({
            "módulo": mod,
            "ruta": d.get("ruta", "?"),
            "funciones": len(d.get("funciones", [])),
            "clases": len(d.get("clases", [])),
            "constantes": len(d.get("constantes", [])),
            "imports": len(d.get("imports", [])),
            "keys_session": len(d.get("claves_session", [])),
            "error_parseo": d.get("error_parseo", ""),
        })
    st.dataframe(pd.DataFrame(filas), use_container_width=True, hide_index=True)

    with st.expander("📊 Imports internos (pares módulo → módulo)"):
        st.code("\n".join([f"{a} -> {b}" for a, b in aristas_imports]) or "(vacío)")

    with st.expander("🕸️ Call graph (pares mod.func → mod.func)"):
        st.code("\n".join([f"{a} -> {b}" for a, b in aristas_llamadas]) or "(vacío)")


# ---------- Main ----------
def principal():
    ap = argparse.ArgumentParser(description="Analizador de proyecto (imports/símbolos/calls + diagnóstico)")
    ap.add_argument("--base", nargs="*", default=BASES_PREDETERMINADAS,
                    help="Carpetas base a analizar (ej: modulo core servicios interfaz exportadores)")
    ap.add_argument("--incluir", nargs="*", default=INCLUIR_PREDETERMINADOS,
                    help="Archivos .py extra a incluir (default: app.py)")
    ap.add_argument("--salida", default=SALIDA_PREDETERMINADA,
                    help="Reporte TXT principal (default: MAPA_FUNCIONES.txt)")
    ap.add_argument("--diag", default=DIAG_PREDETERMINADO,
                    help="Reporte TXT diagnóstico (default: DIAGNOSTICO_IMPORTS.txt)")
    ap.add_argument("--json", default="", help="Ruta opcional para JSON")
    ap.add_argument("--dot-imports", default="", help="Ruta DOT para grafo de imports internos")
    ap.add_argument("--dot-llamadas", default="", help="Ruta DOT para call graph")
    ap.add_argument("--depurar-imports", action="store_true", help="Intentar importar módulos y listar ImportError")
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
