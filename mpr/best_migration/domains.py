"""Dominios de paridad requeridos antes del cutover de pedidos BEST → MPR."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MigrationDomain:
    codigo: str
    nombre: str
    obligatorio_para_pedidos: bool
    descripcion: str
    fuente_best: str
    destino_admin: str
    estado_modulo: str  # implementado | pendiente


DOMAINS: tuple[MigrationDomain, ...] = (
    MigrationDomain(
        codigo="articulos",
        nombre="Artículos",
        obligatorio_para_pedidos=True,
        descripcion=(
            "Correspondencia 1:1 best_id_articulo (MMID) → articulo.IDArt. "
            "El gate solo exige SKUs en pedidos abiertos BEST (origen PEDIDO_ABIERTO). "
            "Los SKUs con saldo en depósito (STOCK_DEPOSITO) se mapean aparte y no bloquean la migración de pedidos."
        ),
        fuente_best="MM / MYL / REP_ORDENES_* (Id Articulo, Codigo, Articulo)",
        destino_admin="articulo (IDArt, id_manual, NombreArticulo)",
        estado_modulo="implementado",
    ),
    MigrationDomain(
        codigo="clientes",
        nombre="Clientes",
        obligatorio_para_pedidos=True,
        descripcion=(
            "Cliente de la nota de pedido BEST → cliente.Codigo AdministraNET. "
            "El gate solo exige clientes en pedidos abiertos (requerido_migracion=True). "
            "Match por CUIT, nombre, id_manual y base de campaña (ej. ATOMIK-FEBRERO→ATOMIK)."
        ),
        fuente_best="REP_ORDENES_COMBINADO.Cliente/CUIT y/o tabla CL",
        destino_admin="cliente (Codigo, nombre_cliente, CUIT, id_manual_cli)",
        estado_modulo="implementado",
    ),
    MigrationDomain(
        codigo="depositos",
        nombre="Depósitos / etapas",
        obligatorio_para_pedidos=False,
        descripcion=(
            "Depósito origen BEST (ej. Depósito Terminado / CC) ↔ deposito con tipo_mpr. "
            "Necesario para stock coherente post-corte, no para sembrar la cabecera PED."
        ),
        fuente_best="REP_INVENTARIOS / Deposito Origen en REP_ORDENES_*",
        destino_admin="deposito (CodDeposito, tipo_mpr)",
        estado_modulo="implementado",
    ),
    MigrationDomain(
        codigo="unidades",
        nombre="Unidades (par / docena)",
        obligatorio_para_pedidos=True,
        descripcion=(
            "BEST opera en pares (1 unidad = 1 par). Validar que cantidades migradas "
            "a stockp.cantidad queden en pares y no en docenas."
        ),
        fuente_best="UM / OOMMUM en OOL",
        destino_admin="stockp.cantidad (pares)",
        estado_modulo="pendiente",
    ),
    MigrationDomain(
        codigo="stock_inicial",
        nombre="Stock inicial por etapa",
        obligatorio_para_pedidos=False,
        descripcion=(
            "Opening balance desde REP_INVENTARIOS → stock_deposito. "
            "Sin esto el tablero sobreestima «resta a producir»."
        ),
        fuente_best="REP_INVENTARIOS (Stock en pares)",
        destino_admin="stock_deposito",
        estado_modulo="implementado",
    ),
    MigrationDomain(
        codigo="stock_reserva",
        nombre="Stock de seguridad (reserva)",
        obligatorio_para_pedidos=False,
        descripcion=(
            "MCSS (pares) del centro de costo Terminado (MCCCID=4003) → articulo.stock_reserva. "
            "Alimenta demanda por reserva (código 0) en ventana OPT y tablero armado."
        ),
        fuente_best="MC.MCSS (MCCCID=4003, pares)",
        destino_admin="articulo.stock_reserva",
        estado_modulo="implementado",
    ),
    MigrationDomain(
        codigo="operarios",
        nombre="Operarios / tejedores",
        obligatorio_para_pedidos=False,
        descripcion="Diccionario letra/código BEST ↔ sue_abm_empleado (reportes, no demanda).",
        fuente_best="Responsable / catálogos operario BEST",
        destino_admin="sue_abm_empleado / mpr operarios",
        estado_modulo="pendiente",
    ),
)


def domain_by_codigo(codigo: str) -> MigrationDomain | None:
    for d in DOMAINS:
        if d.codigo == codigo:
            return d
    return None


def domains_required_for_orders() -> list[MigrationDomain]:
    return [d for d in DOMAINS if d.obligatorio_para_pedidos]
