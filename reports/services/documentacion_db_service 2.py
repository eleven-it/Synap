"""
Servicio para documentación de tablas de la DB AdministraNET.

- Extrae relaciones entre tablas a partir de consultas SQL usadas en VB6 y Synap
  (la DB no está normalizada; las FKs del catálogo no bastan).
- Extrae uso de cada tabla en AdministraNET (qué formularios/procedimientos leen/escriben).

Uso: desde el comando documentar_tablas_db (management command).
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)

# Patrones para detectar tablas en SQL (VB6 y Python)
# Nombres de tabla: palabra con letras, números, guión bajo (y opcionalmente backticks)
TABLE_NAME_PATTERN = r"[\w]+"
# FROM / JOIN pueden tener espacio o newline
RE_FROM = re.compile(
    r"\bFROM\s+(?:`)?(" + TABLE_NAME_PATTERN + r")(?:`)?",
    re.IGNORECASE | re.MULTILINE,
)
RE_JOIN = re.compile(
    r"\b(?:LEFT|RIGHT|INNER|OUTER|CROSS)?\s*JOIN\s+(?:`)?(" + TABLE_NAME_PATTERN + r")(?:`)?",
    re.IGNORECASE | re.MULTILINE,
)
RE_INTO = re.compile(
    r"\bINTO\s+(?:`)?(" + TABLE_NAME_PATTERN + r")(?:`)?",
    re.IGNORECASE | re.MULTILINE,
)
RE_UPDATE = re.compile(
    r"\bUPDATE\s+(?:`)?(" + TABLE_NAME_PATTERN + r")(?:`)?",
    re.IGNORECASE | re.MULTILINE,
)
# DELETE FROM tabla
RE_DELETE = re.compile(
    r"\bDELETE\s+FROM\s+(?:`)?(" + TABLE_NAME_PATTERN + r")(?:`)?",
    re.IGNORECASE | re.MULTILINE,
)
# .Open "SELECT ... FROM tabla" o RecordSource = "SELECT ... FROM tabla"
RE_SELECT_FROM = re.compile(
    r"(?:SELECT|\.Open|RecordSource)\s+.*?\bFROM\s+(?:`)?(" + TABLE_NAME_PATTERN + r")(?:`)?",
    re.IGNORECASE | re.DOTALL,
)
# Para relaciones: en un mismo bloque de SQL, FROM tabla1 ... JOIN tabla2
RE_SQL_BLOCK = re.compile(
    r"(?:SELECT|\.Open|RecordSource)\s*=\s*[\"']([^\"']{50,2000})[\"']",
    re.IGNORECASE | re.DOTALL,
)
# Dentro de un bloque, FROM y JOINs
RE_FROM_JOIN_IN_BLOCK = re.compile(
    r"\bFROM\s+(?:`)?(" + TABLE_NAME_PATTERN + r")(?:`)?[\s\S]*?(?:JOIN\s+(?:`)?(" + TABLE_NAME_PATTERN + r")(?:`)?)",
    re.IGNORECASE,
)


@dataclass
class UsoTabla:
    """Referencia a una tabla en un archivo (lectura/escritura)."""
    archivo: str
    linea: int
    operacion: str  # SELECT, INSERT, UPDATE, DELETE, JOIN
    snippet: str
    contexto: Optional[str] = None  # nombre del formulario o procedimiento si se infiere


@dataclass
class RelacionDesdeSQL:
    """Relación entre dos tablas inferida por uso en una consulta SQL."""
    tabla_origen: str
    tabla_destino: str
    archivo: str
    linea: int
    snippet: str
    tipo_join: Optional[str] = None  # INNER, LEFT, etc.


def _normalize_table_name(name: str) -> str:
    """Normaliza nombre de tabla para comparación (lowercase, sin backticks)."""
    if not name:
        return ""
    return name.strip().lower()


def _extraer_tablas_en_texto(
    texto: str,
    patrones: List[Tuple[re.Pattern, str]],
) -> List[Tuple[str, str]]:
    """Extrae (nombre_tabla, operacion) de un texto usando los patrones dados."""
    encontradas: List[Tuple[str, str]] = []
    seen: Set[Tuple[str, str]] = set()
    for pat, op in patrones:
        for m in pat.finditer(texto):
            name = _normalize_table_name(m.group(1))
            if name and (name, op) not in seen:
                # Filtrar palabras que no son tablas
                if name in ("select", "where", "set", "values", "index", "dual"):
                    continue
                seen.add((name, op))
                encontradas.append((name, op))
    return encontradas


def extraer_uso_tablas_vb6(vb6_root: str) -> Dict[str, List[UsoTabla]]:
    """
    Escanea la carpeta VB6 (Formularios, Modulos) y devuelve por cada tabla
    la lista de archivos/líneas donde se usa (SELECT, INSERT, UPDATE, DELETE).

    vb6_root: ruta a administranet_vb6 (contiene Formularios/, Modulos/).
    """
    root = Path(vb6_root)
    if not root.is_dir():
        return {}

    tabla_a_usos: Dict[str, List[UsoTabla]] = {}
    patrones = [
        (RE_FROM, "SELECT"),
        (RE_JOIN, "JOIN"),
        (RE_INTO, "INSERT"),
        (RE_UPDATE, "UPDATE"),
        (RE_DELETE, "DELETE"),
    ]

    for subdir in ("Formularios", "Modulos"):
        dir_path = root / subdir
        if not dir_path.is_dir():
            continue
        for fpath in dir_path.rglob("*"):
            if fpath.suffix.lower() not in (".frm", ".bas", ".cls"):
                continue
            try:
                content = fpath.read_text(encoding="utf-8", errors="replace")
            except Exception as e:
                logger.debug("No se pudo leer %s: %s", fpath, e)
                continue
            nombre_archivo = fpath.name
            for num, line in enumerate(content.splitlines(), 1):
                tablas_op = _extraer_tablas_en_texto(line, patrones)
                for tabla, op in tablas_op:
                    if tabla not in tabla_a_usos:
                        tabla_a_usos[tabla] = []
                    tabla_a_usos[tabla].append(
                        UsoTabla(
                            archivo=nombre_archivo,
                            linea=num,
                            operacion=op,
                            snippet=line.strip()[:200],
                        )
                    )
    return tabla_a_usos


def extraer_relaciones_desde_sql_vb6(vb6_root: str) -> List[RelacionDesdeSQL]:
    """
    Extrae pares (tabla1, tabla2) cuando en una misma consulta SQL aparece
    FROM tabla1 ... JOIN tabla2 (o varias JOINs). Útil para documentar
    relaciones reales de uso aunque no existan FKs.
    """
    root = Path(vb6_root)
    if not root.is_dir():
        return []

    relaciones: List[RelacionDesdeSQL] = []
    seen: Set[Tuple[str, str, str, int]] = set()

    for subdir in ("Formularios", "Modulos"):
        dir_path = root / subdir
        if not dir_path.is_dir():
            continue
        for fpath in dir_path.rglob("*"):
            if fpath.suffix.lower() not in (".frm", ".bas"):
                continue
            try:
                content = fpath.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            nombre_archivo = fpath.name
            # Buscar bloques de SQL en strings (RecordSource, .Open "SELECT ...")
            for m in re.finditer(
                r'(?:RecordSource|\.Open)\s*=\s*["\']([^"\']+)["\']',
                content,
                re.IGNORECASE | re.DOTALL,
            ):
                sql = m.group(1)
                # FROM tabla
                from_m = RE_FROM.search(sql)
                if not from_m:
                    continue
                tabla_from = _normalize_table_name(from_m.group(1))
                if tabla_from in ("select", "where", "set", "dual"):
                    continue
                # Todas las JOIN en ese bloque
                for join_m in RE_JOIN.finditer(sql):
                    tabla_join = _normalize_table_name(join_m.group(1))
                    if tabla_join in ("select", "where", "set", "dual"):
                        continue
                    key = (tabla_from, tabla_join, nombre_archivo, 0)
                    if key in seen:
                        continue
                    seen.add(key)
                    relaciones.append(
                        RelacionDesdeSQL(
                            tabla_origen=tabla_from,
                            tabla_destino=tabla_join,
                            archivo=nombre_archivo,
                            linea=0,
                            snippet=sql[:300],
                            tipo_join="JOIN",
                        )
                    )
            # Por línea: FROM tabla1 JOIN tabla2
            for num, line in enumerate(content.splitlines(), 1):
                from_m = RE_FROM.search(line)
                if not from_m:
                    continue
                t1 = _normalize_table_name(from_m.group(1))
                if t1 in ("select", "where", "set", "dual"):
                    continue
                for join_m in RE_JOIN.finditer(line):
                    t2 = _normalize_table_name(join_m.group(1))
                    if t2 in ("select", "where", "set", "dual"):
                        continue
                    key = (t1, t2, nombre_archivo, num)
                    if key in seen:
                        continue
                    seen.add(key)
                    relaciones.append(
                        RelacionDesdeSQL(
                            tabla_origen=t1,
                            tabla_destino=t2,
                            archivo=nombre_archivo,
                            linea=num,
                            snippet=line.strip()[:300],
                            tipo_join="JOIN",
                        )
                    )
    return relaciones


def extraer_relaciones_desde_sql_synap(synap_reports_path: str) -> List[RelacionDesdeSQL]:
    """
    Escanea reports (query_runner, servicios) en busca de SQL con JOINs
    para inferir relaciones entre tablas.
    """
    root = Path(synap_reports_path)
    if not root.is_dir():
        return []

    relaciones: List[RelacionDesdeSQL] = []
    seen: Set[Tuple[str, str, str, int]] = set()

    for fpath in root.rglob("*.py"):
        try:
            content = fpath.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        rel_path = str(fpath.relative_to(root))
        for num, line in enumerate(content.splitlines(), 1):
            from_m = RE_FROM.search(line)
            if not from_m:
                continue
            t1 = _normalize_table_name(from_m.group(1))
            if t1 in ("select", "where", "information_schema", "dual"):
                continue
            for join_m in RE_JOIN.finditer(line):
                t2 = _normalize_table_name(join_m.group(1))
                if t2 in ("select", "where", "information_schema", "dual"):
                    continue
                key = (t1, t2, rel_path, num)
                if key in seen:
                    continue
                seen.add(key)
                relaciones.append(
                    RelacionDesdeSQL(
                        tabla_origen=t1,
                        tabla_destino=t2,
                        archivo=rel_path,
                        linea=num,
                        snippet=line.strip()[:300],
                        tipo_join="JOIN",
                    )
                )
    return relaciones


def extraer_uso_tablas_synap(synap_reports_path: str) -> Dict[str, List[UsoTabla]]:
    """Uso de tablas en código Python de reports (SELECT, FROM, etc.)."""
    root = Path(synap_reports_path)
    if not root.is_dir():
        return {}

    tabla_a_usos: Dict[str, List[UsoTabla]] = {}
    patrones = [(RE_FROM, "SELECT"), (RE_JOIN, "JOIN"), (RE_UPDATE, "UPDATE")]

    for fpath in root.rglob("*.py"):
        if "migrations" in str(fpath):
            continue
        try:
            content = fpath.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        rel_path = str(fpath.relative_to(root))
        for num, line in enumerate(content.splitlines(), 1):
            tablas_op = _extraer_tablas_en_texto(line, patrones)
            for tabla, op in tablas_op:
                if "information_schema" in tabla:
                    continue
                if tabla not in tabla_a_usos:
                    tabla_a_usos[tabla] = []
                tabla_a_usos[tabla].append(
                    UsoTabla(
                        archivo=rel_path,
                        linea=num,
                        operacion=op,
                        snippet=line.strip()[:200],
                    )
                )
    return tabla_a_usos


def agrupar_relaciones_por_tabla(
    relaciones: List[RelacionDesdeSQL],
) -> Dict[str, List[RelacionDesdeSQL]]:
    """Agrupa relaciones por tabla: para cada tabla T lista todos los RelacionDesdeSQL donde T es origen o destino."""
    resultado: Dict[str, List[RelacionDesdeSQL]] = {}
    for r in relaciones:
        o = r.tabla_origen.lower()
        d = r.tabla_destino.lower()
        for t in (o, d):
            resultado.setdefault(t, []).append(r)
    return resultado
