"""Proxies duck-typing para servicios/vistas cuando el ledger está en MySQL."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any, List, Optional

from core.utils.administranet_types import str_or_default


def _coerce_time(value: Any) -> time:
    if isinstance(value, time):
        return value
    if isinstance(value, timedelta):
        total = int(value.total_seconds())
        h, rem = divmod(total, 3600)
        m, s = divmod(rem, 60)
        return time(h % 24, m, s)
    if isinstance(value, str) and value:
        parts = value.split(":")
        return time(int(parts[0]), int(parts[1]), int(parts[2]) if len(parts) > 2 else 0)
    return time(0, 0)


class TurnoRecord:
    """Sustituto de MprTurno cuando MPR_LEDGER_BACKEND lee MySQL."""

    def __init__(
        self,
        *,
        id_mpr_turno: int,
        nombre: str,
        hora_inicio: Any,
        hora_fin: Any,
        activo: bool,
        base_empresa: str,
    ):
        self.id = int(id_mpr_turno)
        self.pk = self.id
        self.id_mpr_turno = self.id
        self.nombre = nombre
        self.hora_inicio = _coerce_time(hora_inicio)
        self.hora_fin = _coerce_time(hora_fin)
        self.activo = bool(activo)
        self.base_empresa = base_empresa

    def save(self, update_fields=None) -> None:
        from mpr.repositories.turno_roster import guardar_turno_record

        guardar_turno_record(self.base_empresa, self, update_fields)


class _ParteRelatedList:
    """Compatibilidad tipo RelatedManager: ``.all()`` y también iterable."""

    def __init__(self, items: List[Any]):
        self._items = list(items or [])

    def all(self) -> List[Any]:
        return list(self._items)

    def __iter__(self):
        return iter(self._items)

    def __len__(self) -> int:
        return len(self._items)

    def __bool__(self) -> bool:
        return bool(self._items)


class ParteLineaRecord:
    def __init__(
        self,
        *,
        id_articulo: int,
        id_operario: int,
        cantidad: Decimal,
        operario_nombre: str = "-",
    ):
        self.id_articulo = id_articulo
        self.id_operario = id_operario
        self.cantidad = cantidad
        self.operario_nombre = operario_nombre


class ParteAjusteRecord:
    def __init__(
        self,
        *,
        id_mpr_parte_ajuste: int,
        uuid_ajuste: Optional[str],
        id_mpr_parte: int,
        id_articulo: int,
        id_operario: int,
        delta: Decimal,
        motivo: str,
        id_usuario: int,
        registrado_en: datetime,
        ajuste_fisico_ok: bool,
        base_empresa: str,
    ):
        self.id = uuid_ajuste or str(id_mpr_parte_ajuste)
        self.pk = self.id
        self.id_mpr_parte_ajuste = id_mpr_parte_ajuste
        self.uuid_ajuste = uuid_ajuste
        self.parte_id = id_mpr_parte
        self.id_articulo = id_articulo
        self.id_operario = id_operario
        self.delta = delta
        self.motivo = motivo
        self.id_usuario = id_usuario
        self.registrado_en = registrado_en
        self.creado_en = registrado_en
        self.ajuste_fisico_ok = ajuste_fisico_ok
        self.base_empresa = base_empresa
        self.parte = None

    def save(self, update_fields=None) -> None:
        from mpr.repositories.parte import actualizar_ajuste_fisico_ok

        if update_fields and "ajuste_fisico_ok" in update_fields:
            actualizar_ajuste_fisico_ok(
                self.base_empresa,
                self.id_mpr_parte_ajuste,
                self.ajuste_fisico_ok,
            )

    def delete(self) -> None:
        from mpr.repositories.parte import eliminar_ajuste

        eliminar_ajuste(self.base_empresa, self.id_mpr_parte_ajuste)


class ParteRecord:
    """Sustituto de MprParte cuando MPR_LEDGER_BACKEND lee MySQL."""

    def __init__(
        self,
        *,
        id_mpr_parte: int,
        uuid_parte: Optional[str],
        fecha_produccion: date,
        id_mpr_turno: int,
        turno: Optional[TurnoRecord],
        id_usuario: int,
        registrado_en: datetime,
        notas: str,
        movimiento_fisico_ok: bool,
        id_lista_produccion: Optional[int],
        base_empresa: str,
        lineas: Optional[List[ParteLineaRecord]] = None,
        ajustes: Optional[List[ParteAjusteRecord]] = None,
    ):
        self.id_mpr_parte = id_mpr_parte
        self.uuid_parte = uuid_parte
        self.pk = uuid_parte or str(id_mpr_parte)
        self.id = self.pk
        self.fecha_produccion = fecha_produccion
        self.turno_id = id_mpr_turno
        self.turno = turno
        self.id_usuario = id_usuario
        self.registrado_en = registrado_en
        self.notas = notas
        self.movimiento_fisico_ok = movimiento_fisico_ok
        self.id_lista_produccion = id_lista_produccion
        self.base_empresa = base_empresa
        self.lineas = _ParteRelatedList(lineas or [])
        self.ajustes = _ParteRelatedList(ajustes or [])

    def save(self, update_fields=None) -> None:
        from mpr.repositories.parte import actualizar_parte_record

        actualizar_parte_record(self.base_empresa, self, update_fields)


class ArmadoMovimientoRecord:
    """Sustituto mínimo de MprArmadoSurtidoMovimiento en MySQL."""

    def __init__(
        self,
        *,
        id_mpr_armado_surtido_movimiento: int,
        codigo_movimiento: int,
        id_articulo_pack: int,
        cantidad_packs: int,
        modo: str,
        estado_imputacion: str,
        id_operario: Optional[int],
        id_usuario: int,
        creado_en: datetime,
        id_mpr_armado_lote: Optional[int] = None,
        base_empresa: str = "",
    ):
        self.id = id_mpr_armado_surtido_movimiento
        self.pk = self.id
        self.codigo_movimiento = codigo_movimiento
        self.id_articulo_pack = id_articulo_pack
        self.cantidad_packs = cantidad_packs
        self.modo = modo
        self.estado_imputacion = estado_imputacion
        self.id_operario = id_operario
        self.id_usuario = id_usuario
        self.creado_en = creado_en
        self.id_lote_armado_id = id_mpr_armado_lote
        self.base_empresa = base_empresa

    @property
    def id_mpr_armado_surtido_movimiento(self) -> int:
        return int(self.id)

    @property
    def id_mpr_armado_lote(self) -> Optional[int]:
        return self.id_lote_armado_id

    def save(self, update_fields=None) -> None:
        from mpr.repositories.armado_surtido import actualizar_estado_imputacion_mov

        if update_fields and "estado_imputacion" in update_fields:
            actualizar_estado_imputacion_mov(
                self.base_empresa,
                self.id,
                self.estado_imputacion,
            )


class ArmadoLoteRecord:
    def __init__(
        self,
        *,
        id_mpr_armado_lote: int,
        uuid_lote: Optional[str],
        modo: str,
        id_operario: Optional[int],
        id_usuario: int,
        deposito_origen: int,
        deposito_destino: int,
        cantidad_items: int,
        cantidad_exitosos: int = 0,
        cantidad_fallidos: int = 0,
        ejecutado_en: Optional[datetime] = None,
        fecha_realizado: Optional[date] = None,
        estado: str = "aprobado",
        movimiento_fisico_ok: bool = True,
        detalle: str = "",
        base_empresa: str = "",
    ):
        self.id = uuid_lote or id_mpr_armado_lote
        self.pk = self.id
        self.id_mpr_armado_lote = id_mpr_armado_lote
        self.uuid_lote = uuid_lote
        self.modo = modo
        self.id_operario = id_operario
        self.id_usuario = id_usuario
        self.deposito_origen = deposito_origen
        self.deposito_destino = deposito_destino
        self.cantidad_items = cantidad_items
        self.cantidad_exitosos = cantidad_exitosos
        self.cantidad_fallidos = cantidad_fallidos
        self.ejecutado_en = ejecutado_en or datetime.now()
        self.fecha_realizado = fecha_realizado
        self.estado = str_or_default(estado, "aprobado")
        self.movimiento_fisico_ok = bool(movimiento_fisico_ok)
        self.detalle = str_or_default(detalle, "")
        self.base_empresa = base_empresa

    def save(self, update_fields=None) -> None:
        from mpr.repositories.armado_surtido import actualizar_lote_armado

        if update_fields:
            actualizar_lote_armado(
                self.base_empresa,
                self.id_mpr_armado_lote,
                cantidad_exitosos=self.cantidad_exitosos,
                cantidad_fallidos=self.cantidad_fallidos,
                estado=self.estado if "estado" in update_fields else None,
                movimiento_fisico_ok=self.movimiento_fisico_ok
                if "movimiento_fisico_ok" in update_fields
                else None,
                fecha_realizado=self.fecha_realizado
                if "fecha_realizado" in update_fields
                else None,
                detalle=self.detalle if "detalle" in update_fields else None,
                cantidad_items=self.cantidad_items if "cantidad_items" in update_fields else None,
            )
