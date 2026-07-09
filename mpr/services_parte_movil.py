"""Servicios de la carga móvil del operario (parte de producción por máquina).

Dominio Best Sox: 1 docena = 12 pares. Captura en docenas + pares sueltos,
persistencia en pares (`cantidad_declarada`). El parte nace `pendiente` sin
mover stock; la aprobación del supervisor (Fase 7) ejecuta el asiento.
"""
from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

PARES_POR_DOCENA = 12


def _docenas_pares(cantidad_pares: Decimal) -> Tuple[int, int]:
    total = int(cantidad_pares or 0)
    return total // PARES_POR_DOCENA, total % PARES_POR_DOCENA


def construir_grilla_carga_movil(
    base_empresa: str,
    id_operario: int,
    id_usuario: int,
    fecha: Optional[date] = None,
    id_turno: Optional[int] = None,
) -> Dict[str, Any]:
    """Arma el contexto de carga: línea, turno, máquinas y artículos vigentes.

    Devuelve dict con `estado_borde` in {ok, sin_operario, sin_turno, sin_linea, sin_maquinas}.
    """
    from mpr.repositories import maquina_articulo as repo_art
    from mpr.repositories import maquina_linea as repo_ml
    from mpr.repositories import parte_movil as repo_pm
    from mpr.repositories import turno_roster as repo_r
    from mpr.services_operario import resolver_linea_operario

    base = (base_empresa or "").strip()
    hoy = fecha or date.today()
    ctx: Dict[str, Any] = {"fecha": hoy, "maquinas": [], "estado_borde": "ok"}

    if not base or not id_operario:
        ctx["estado_borde"] = "sin_operario"
        return ctx

    tid = id_turno or repo_r.turno_del_operario_dia(base, id_operario, hoy)
    if not tid:
        ctx["estado_borde"] = "sin_turno"
        return ctx
    turno = repo_r.obtener_turno_record(base, tid)
    ctx["id_turno"] = tid
    ctx["turno_nombre"] = getattr(turno, "nombre", "") if turno else ""

    id_linea = resolver_linea_operario(base, id_operario, hoy, tid)
    if not id_linea:
        ctx["estado_borde"] = "sin_linea"
        return ctx
    linea = repo_ml.obtener_linea(base, id_linea)
    ctx["id_linea"] = id_linea
    ctx["linea_nombre"] = linea["nombre"] if linea else ""

    maquinas = repo_ml.maquinas_de_linea(base, id_linea, hoy)
    if not maquinas:
        ctx["estado_borde"] = "sin_maquinas"
        return ctx

    existente = repo_pm.obtener_parte_movil_editable(base, hoy, tid, id_usuario)
    prefill = existente["lineas"] if existente else {}
    ctx["estado_parte"] = existente["estado"] if existente else None

    grilla: List[Dict[str, Any]] = []
    total_pares = 0
    maquinas_cargadas = 0
    for maq in maquinas:
        articulos_vig = repo_art.listar_articulos_vigentes(base, maq["id"], hoy)
        items: List[Dict[str, Any]] = []
        maq_pares = 0
        for art in articulos_vig:
            pares = int(prefill.get((art["id_articulo"], maq["id"]), 0) or 0)
            doc, par = _docenas_pares(Decimal(pares))
            maq_pares += pares
            items.append({
                "id_articulo": art["id_articulo"],
                "codigo": art.get("codigo_manual") or art.get("codigo_articulo"),
                "descripcion": art.get("descripcion_articulo"),
                "docenas": doc,
                "pares": par,
            })
        total_pares += maq_pares
        if maq_pares > 0:
            maquinas_cargadas += 1
        grilla.append({
            "id_maquina": maq["id"],
            "codigo": maq["codigo"],
            "nombre": maq.get("nombre"),
            "articulos": items,
            "sin_articulos": not items,
            "cargada": maq_pares > 0,
        })

    ctx["maquinas"] = grilla
    ctx["total_pares"] = total_pares
    ctx["total_docenas"] = round(total_pares / PARES_POR_DOCENA, 2)
    ctx["maquinas_cargadas"] = maquinas_cargadas
    ctx["maquinas_total"] = len(grilla)
    return ctx


def registrar_parte_movil(
    base_empresa: str,
    id_operario: int,
    operario_nombre: str,
    id_usuario: int,
    celdas: List[Dict[str, Any]],
    fecha: Optional[date] = None,
    id_turno: Optional[int] = None,
    estado: str = "pendiente",
    notas: str = "",
) -> Tuple[bool, Optional[str], Optional[int]]:
    """Persiste el parte móvil (pendiente/borrador) sin mover stock.

    celdas: [{id_maquina, maquina_nombre, id_articulo, docenas, pares}]
    Devuelve (ok, error, id_parte).
    """
    from mpr.repositories import parte_movil as repo_pm
    from mpr.repositories import turno_roster as repo_r

    base = (base_empresa or "").strip()
    if not base:
        return False, "Empresa inválida.", None
    if not id_operario:
        return False, "No tenés un operario asociado. Contactá al supervisor.", None
    hoy = fecha or date.today()
    tid = id_turno or repo_r.turno_del_operario_dia(base, id_operario, hoy)
    if not tid:
        return False, "No tenés un turno asignado para hoy. Contactá al supervisor.", None

    lineas: List[Dict[str, Any]] = []
    for cel in celdas or []:
        try:
            id_art = int(cel.get("id_articulo"))
        except (TypeError, ValueError):
            continue
        id_maq = cel.get("id_maquina")
        try:
            docenas = int(cel.get("docenas") or 0)
            pares = int(cel.get("pares") or 0)
        except (TypeError, ValueError):
            return False, "Cantidades inválidas: usá números enteros.", None
        if docenas < 0 or pares < 0:
            return False, "Las cantidades no pueden ser negativas.", None
        declarada = docenas * PARES_POR_DOCENA + pares
        if declarada <= 0:
            continue
        lineas.append({
            "id_articulo": id_art,
            "id_mpr_maquina": id_maq,
            "maquina_nombre": cel.get("maquina_nombre"),
            "cantidad_declarada": declarada,
        })

    if not lineas and estado == "pendiente":
        return False, "No cargaste producción en ninguna máquina.", None

    try:
        id_parte, _uuid = repo_pm.crear_o_actualizar_parte_movil(
            base_empresa=base,
            fecha_produccion=hoy,
            id_mpr_turno=tid,
            id_usuario=id_usuario,
            id_operario=id_operario,
            operario_nombre=operario_nombre,
            lineas=lineas,
            estado=estado,
            notas=notas,
        )
        return True, None, id_parte
    except Exception as e:
        logger.error("Error al registrar parte móvil (%s): %s", base, e, exc_info=True)
        return False, "Error al guardar el parte.", None


def listar_partes_pendientes(
    base_empresa: str,
    fecha: Optional[date] = None,
    id_turno: Optional[int] = None,
    incluir_borrador: bool = False,
) -> List[Dict[str, Any]]:
    """Bandeja de partes pendientes (para el supervisor)."""
    from mpr.repositories import parte_movil as repo_pm

    partes = repo_pm.listar_partes_pendientes(
        base_empresa, fecha=fecha, id_mpr_turno=id_turno, incluir_borrador=incluir_borrador
    )
    for p in partes:
        total = p.get("total_declarado") or Decimal("0")
        p["total_docenas"] = round(float(total) / PARES_POR_DOCENA, 2)
    return partes


def detalle_parte_para_aprobacion(
    base_empresa: str,
    id_parte: int,
) -> Optional[Dict[str, Any]]:
    """Cabecera + líneas (con descripción y cupo Fabricando de referencia) del parte."""
    from mpr.repositories import maquina_articulo as repo_art
    from mpr.repositories import parte_movil as repo_pm
    from mpr.repositories import turno_roster as repo_r
    from mpr.services import cupo_fabricando_por_articulo

    base = (base_empresa or "").strip()
    cab = repo_pm.obtener_cabecera_parte(base, id_parte)
    if not cab:
        return None
    lineas = repo_pm.listar_lineas_aprobacion(base, id_parte)
    ids_art = [ln["id_articulo"] for ln in lineas if ln.get("id_articulo") is not None]
    descripciones = repo_art.articulos_por_ids(base, ids_art) if ids_art else {}
    cupos = cupo_fabricando_por_articulo(base, ids_art)

    turno = repo_r.obtener_turno_record(base, cab["id_mpr_turno"]) if cab.get("id_mpr_turno") else None
    total_declarado = Decimal("0")
    for ln in lineas:
        art = descripciones.get(ln["id_articulo"], {})
        ln["codigo"] = art.get("codigo_manual") or art.get("codigo_articulo") or str(ln["id_articulo"])
        ln["descripcion"] = art.get("descripcion_articulo") or ""
        ln["cupo_fabricando"] = cupos.get(ln["id_articulo"])
        decl = ln.get("cantidad_declarada") or Decimal("0")
        ln["cantidad_aprobada_defecto"] = (
            ln["cantidad_aprobada"] if ln.get("cantidad_aprobada") is not None else decl
        )
        total_declarado += decl
    return {
        "cabecera": cab,
        "turno_nombre": getattr(turno, "nombre", "") if turno else "",
        "lineas": lineas,
        "total_declarado": total_declarado,
        "total_docenas": round(float(total_declarado) / PARES_POR_DOCENA, 2),
    }
