"""
Servicio de lectura/escritura de stock (AdministraNET).
Paridad con CargaMovStock/Visualiza: mismas tablas y formato.
Sin modelos Django; usa core.mysql_pool y base_empresa de sesión.
"""
import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from core.mysql_pool import get_mysql_pool, mysql_cursor
from core.services.administranet_permisos_sistema import AdministraNETPermisosSistemaService
from core.utils.administranet_types import str_or_default, to_date_or_none, to_decimal_or_none, to_int_or_none

logger = logging.getLogger(__name__)

# Motivos de movimiento (VB6 CargaMovStock). Códigos numéricos según análisis.
# En VB6 el combo Motivo usa ListIndex 0..9 (y 10/11 si pedidos_parte_produccion);
# Synap usa códigos 1..12. Cada motivo se persiste en movimiento_stock.motivo_movimiento (texto)
# y en cada renglón de stock como stock.TipoComp ("movimiento en artículo").
MOTIVOS_MOVIMIENTO = [
    (1, "Stock Inicial"),
    (2, "Ajuste"),
    (3, "Faltante"),
    (4, "Sobrante"),
    (5, "Rotura"),
    (6, "Transferencia"),
    (7, "Mov. Interno Salida"),
    (8, "Mov. Interno Entrada"),
    (9, "Armado"),
    (10, "Desarmado"),
    (11, "Pedido producción"),
    (12, "Parte producción"),
]

# Mapa código -> nombre para escribir motivo_movimiento y TipoComp como en VB6 (Motivo.Text).
MOTIVO_CODIGO_A_NOMBRE = {c: n for c, n in MOTIVOS_MOVIMIENTO}


def _get_permisos_puesto(base_empresa: str, id_puesto: Optional[int]) -> Dict[str, Any]:
    """Obtiene permisos del puesto desde permisos_sistema (tabla wide por puesto)."""
    if not base_empresa or not id_puesto:
        return {}
    try:
        svc = AdministraNETPermisosSistemaService()
        return svc.obtener_permisos_puesto(base_empresa, id_puesto) or {}
    except Exception as e:
        logger.warning("Error al obtener permisos puesto %s: %s", id_puesto, e)
        return {}


def get_depositos(
    base_empresa: str,
    id_puesto: Optional[int],
) -> List[Dict[str, Any]]:
    """
    Lista depósitos permitidos para el puesto.
    Si cambia_deposito != 'Si', filtrar por deposito_usr (o tabla deposito_usr si existe).
    """
    try:
        permisos = _get_permisos_puesto(base_empresa, id_puesto)
        cambia_deposito = (permisos.get("cambia_deposito") or "").strip() == "Si"

        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            if cambia_deposito:
                cursor.execute(
                    """
                    SELECT CodDeposito, COALESCE(NombreDeposito, '') AS NombreDeposito
                    FROM deposito
                    WHERE COALESCE(anulado, 'No') = 'No'
                    ORDER BY NombreDeposito
                    """
                )
            else:
                # Restricción por depósito del usuario: columna deposito_usr en permisos_sistema
                # o tabla deposito_usr (id_puesto, CodDeposito). Aquí asumimos permisos_sistema.
                deposito_usr = permisos.get("deposito_usr") or permisos.get("CodDeposito")
                if deposito_usr is not None and str(deposito_usr).strip() != "":
                    try:
                        cod = int(deposito_usr)
                        cursor.execute(
                            """
                            SELECT CodDeposito, COALESCE(NombreDeposito, '') AS NombreDeposito
                            FROM deposito
                            WHERE CodDeposito = %s AND COALESCE(anulado, 'No') = 'No'
                            ORDER BY NombreDeposito
                            """,
                            [cod],
                        )
                    except (ValueError, TypeError):
                        cursor.execute(
                            """
                            SELECT CodDeposito, COALESCE(NombreDeposito, '') AS NombreDeposito
                            FROM deposito
                            WHERE COALESCE(anulado, 'No') = 'No'
                            ORDER BY NombreDeposito
                            """
                        )
                else:
                    cursor.execute(
                        """
                        SELECT CodDeposito, COALESCE(NombreDeposito, '') AS NombreDeposito
                        FROM deposito
                        WHERE COALESCE(anulado, 'No') = 'No'
                        ORDER BY NombreDeposito
                        """
                    )
            rows = cursor.fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.warning("Error al listar depósitos en %s: %s", base_empresa, e)
        return []


def get_nombre_deposito(base_empresa: str, cod_deposito: Optional[int]) -> str:
    """
    Devuelve el nombre del depósito por CodDeposito (tabla deposito.NombreDeposito).
    Si no existe o hay error, devuelve '-' o el código como texto.
    """
    if cod_deposito is None:
        return "-"
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            cursor.execute(
                "SELECT COALESCE(NombreDeposito, '') AS NombreDeposito FROM deposito WHERE CodDeposito = %s",
                [to_int_or_none(cod_deposito)],
            )
            row = cursor.fetchone()
        return str_or_default((row or {}).get("NombreDeposito"), "-") or "-"
    except Exception as e:
        logger.warning("Error al obtener nombre depósito %s en %s: %s", cod_deposito, base_empresa, e)
        return str(cod_deposito)


def get_nombres_depositos(
    base_empresa: str, codigos: List[int]
) -> Dict[int, str]:
    """
    Devuelve un diccionario CodDeposito -> NombreDeposito para la lista de códigos.
    Útil para enriquecer listados sin N consultas.
    """
    if not codigos:
        return {}
    codigos = [to_int_or_none(c) for c in codigos if to_int_or_none(c) is not None]
    if not codigos:
        return {}
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            placeholders = ",".join(["%s"] * len(codigos))
            cursor.execute(
                f"SELECT CodDeposito, COALESCE(NombreDeposito, '') AS NombreDeposito FROM deposito WHERE CodDeposito IN ({placeholders})",
                codigos,
            )
            rows = cursor.fetchall()
        return {
            to_int_or_none(r.get("CodDeposito")): str_or_default(r.get("NombreDeposito"), "-") or "-"
            for r in (rows or [])
            if to_int_or_none(r.get("CodDeposito")) is not None
        }
    except Exception as e:
        logger.warning("Error al obtener nombres depósitos en %s: %s", base_empresa, e)
        return {}


def get_ref_movstock(base_empresa: str, id_puesto: Optional[int]) -> List[Dict[str, Any]]:
    """
    Lista referencias de movimiento permitidas.
    Si acceso_ref_movstock != 'Todos', filtrar por id_refmovstock del puesto.
    """
    try:
        permisos = _get_permisos_puesto(base_empresa, id_puesto)
        acceso = (permisos.get("acceso_ref_movstock") or "").strip()
        id_ref = permisos.get("id_refmovstock")

        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            if acceso == "Todos" or not id_ref:
                cursor.execute(
                    """
                    SELECT id_ref_movstock, COALESCE(nombre_ref_movstock, '') AS nombre_ref_movstock
                    FROM ref_movstock
                    WHERE COALESCE(anulado, 'No') = 'No'
                    ORDER BY nombre_ref_movstock
                    """
                )
            else:
                try:
                    id_ref = int(id_ref)
                    cursor.execute(
                        """
                        SELECT id_ref_movstock, COALESCE(nombre_ref_movstock, '') AS nombre_ref_movstock
                        FROM ref_movstock
                        WHERE id_ref_movstock = %s AND COALESCE(anulado, 'No') = 'No'
                        ORDER BY nombre_ref_movstock
                        """,
                        [id_ref],
                    )
                except (ValueError, TypeError):
                    cursor.execute(
                        """
                        SELECT id_ref_movstock, COALESCE(nombre_ref_movstock, '') AS nombre_ref_movstock
                        FROM ref_movstock
                        WHERE COALESCE(anulado, 'No') = 'No'
                        ORDER BY nombre_ref_movstock
                        """
                    )
            rows = cursor.fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.warning("Error al listar ref_movstock en %s: %s", base_empresa, e)
        return []


def get_viajantes(base_empresa: str) -> List[Dict[str, Any]]:
    """
    Lista viajantes (operarios/vendedores) no anulados para desplegable Operario.
    Paridad con VB6: SELECT * FROM viajantes WHERE anulado = 'No' ORDER BY Nombre.
    """
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            cursor.execute(
                """
                SELECT CodViajante, COALESCE(Nombre, '') AS Nombre
                FROM viajantes
                WHERE COALESCE(anulado, 'No') = 'No'
                ORDER BY Nombre
                """
            )
            rows = cursor.fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.warning("Error al listar viajantes en %s: %s", base_empresa, e)
        return []


def get_clientes(
    base_empresa: str,
    q: Optional[str] = None,
    limit: int = 300,
) -> List[Dict[str, Any]]:
    """
    Lista clientes (tabla cliente) para Mov. Interno Salida/Entrada (campo Cliente).
    Si se pasa q, filtra por nombre_cliente o Codigo (LIKE).
    """
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            if q and q.strip():
                busqueda = f"%{q.strip()}%"
                cursor.execute(
                    """
                    SELECT Codigo, COALESCE(nombre_cliente, '') AS nombre_cliente
                    FROM cliente
                    WHERE (nombre_cliente LIKE %s OR CAST(Codigo AS CHAR) LIKE %s)
                    ORDER BY nombre_cliente
                    LIMIT %s
                    """,
                    [busqueda, busqueda, limit],
                )
            else:
                cursor.execute(
                    """
                    SELECT Codigo, COALESCE(nombre_cliente, '') AS nombre_cliente
                    FROM cliente
                    ORDER BY nombre_cliente
                    LIMIT %s
                    """,
                    [limit],
                )
            rows = cursor.fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.warning("Error al listar clientes en %s: %s", base_empresa, e)
        return []


def listar_pedidos_pendientes(
    base_empresa: str,
    motivo: int,
    deposito_destino: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Lista pedidos pendientes para Busca_PEDI (modal lista).
    - motivo 6 (Transferencia): PEDI + movimiento_stock, tipo_pedido_interno = 'A deposito',
      movimiento_stock.deposito_origen = deposito_destino. Requiere deposito_destino.
    - motivo 11 (Pedido producción) / 12 (Parte producción): comp_ped PED, estado_pedido_opt = 'Pendiente' (pedidos pendientes de producción).
    Devuelve lista de dict con CodigoMovimiento, NroComprobante y opcionalmente nombre_cliente, Estado.
    """
    motivo = int(motivo)
    if motivo == 6:
        if deposito_destino is None:
            return []
        try:
            with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
                cursor.execute(
                    """
                    SELECT cp.CodigoMovimiento, cp.NroComprobante, cp.Estado,
                           ms.deposito_origen, ms.deposito_destino
                    FROM comp_ped cp
                    INNER JOIN movimiento_stock ms ON ms.codigo_movimiento = cp.CodigoMovimiento
                    WHERE cp.Anulado = 'No'
                      AND cp.TipoComprobante IN ('PEDI')
                      AND COALESCE(cp.tipo_pedido_interno, '') = 'A deposito'
                      AND cp.Estado = 'Pendiente'
                      AND ms.deposito_origen = %s
                    ORDER BY cp.CodigoMovimiento DESC
                    LIMIT 200
                    """,
                    [deposito_destino],
                )
                rows = cursor.fetchall()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.warning("Error listar PEDI pendientes en %s: %s", base_empresa, e)
            return []
    if motivo in (11, 12):
        try:
            with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
                cursor.execute(
                    """
                    SELECT cp.CodigoMovimiento, cp.NroComprobante, cp.Estado,
                           COALESCE(cli.nombre_cliente, '') AS nombre_cliente
                    FROM comp_ped cp
                    LEFT JOIN cliente cli ON cli.codigo = cp.codigo
                    WHERE cp.Anulado = 'No'
                      AND cp.TipoComprobante IN ('PED')
                      AND COALESCE(cp.estado_pedido_opt, '') = 'Pendiente'
                    ORDER BY cp.CodigoMovimiento DESC
                    LIMIT 200
                    """,
                )
                rows = cursor.fetchall()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.warning("Error listar PED pendientes (OPT/OPP) en %s: %s", base_empresa, e)
            return []
    return []


def listar_proyectos(base_empresa: str) -> List[Dict[str, Any]]:
    """
    Lista proyectos para Lista_Proyecto_Click (modal lista).
    Solo proyectos erp_proyecto con estado_proyecto = 'En curso' (id_proyecto <> 1).
    Si no hay ninguno, devuelve lista vacía y el modal mostrará "No hay proyectos en curso."
    Si hay proyectos, se antepone "Ninguno" (id_proyecto=1) para poder dejar sin proyecto.
    """
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            cursor.execute(
                """
                SELECT ep.id_proyecto, COALESCE(ep.nombre_proyecto, '') AS nombre_proyecto,
                       COALESCE(ep.estado_proyecto, '') AS estado_proyecto,
                       COALESCE(ez.nombre_zona, '') AS nombre_zona,
                       COALESCE(cli.nombre_cliente, '') AS nombre_cliente
                FROM erp_proyecto ep
                LEFT JOIN erp_zona ez ON ez.id_zona = ep.id_zona
                LEFT JOIN cliente cli ON cli.codigo = ep.id_cliente
                WHERE ep.id_proyecto <> 1 AND COALESCE(ep.estado_proyecto, '') = 'En curso'
                ORDER BY ep.nombre_proyecto
                LIMIT 200
                """,
            )
            rows = cursor.fetchall()
        lista = [dict(r) for r in rows]
        if not lista:
            return []
        # Si hay proyectos, primera opción: Ninguno (id_proyecto = 1)
        lista.insert(0, {
            "id_proyecto": 1,
            "nombre_proyecto": "Ninguno",
            "estado_proyecto": "",
            "nombre_zona": "",
            "nombre_cliente": "",
        })
        return lista
    except Exception as e:
        logger.warning("Error al listar proyectos en %s: %s", base_empresa, e)
        return []


def get_activ_proyecto(base_empresa: str) -> str:
    """
    Indica si el módulo de proyectos está activo (tabla configuracion.activ_proyecto).
    En VB6: Principal.activ_proyecto; controla visibilidad de frame_proyecto en CargaMovStock.
    """
    try:
        with mysql_cursor(base_empresa, dict_cursor=False) as cursor:
            cursor.execute("SELECT COALESCE(activ_proyecto, 'No') FROM configuracion LIMIT 1")
            row = cursor.fetchone()
        return (row[0] or "No").strip() if row else "No"
    except Exception as e:
        logger.warning("Error al leer activ_proyecto en %s: %s", base_empresa, e)
        return "No"


def get_calculo_stock_saldo(base_empresa: str) -> str:
    """
    Indica si está activo el cálculo de saldo directo (ajuste por saldo deseado).
    En VB6: Principal.calculo_stock_saldo (permiso 129); en algunas bases puede estar en configuracion.
    Si la columna no existe en configuracion, devuelve 'No'.
    """
    try:
        with mysql_cursor(base_empresa, dict_cursor=False) as cursor:
            cursor.execute("SELECT COALESCE(calculo_stock_saldo, 'No') FROM configuracion LIMIT 1")
            row = cursor.fetchone()
        return (row[0] or "No").strip() if row else "No"
    except Exception as e:
        if "Unknown column" in str(e) or "calculo_stock_saldo" in str(e):
            return "No"
        logger.warning("Error al leer calculo_stock_saldo en %s: %s", base_empresa, e)
        return "No"


def get_config_unidad_bulto_display(base_empresa: str) -> Dict[str, Any]:
    """
    Lee de configuracion: utiliza_bulto_cerrado, utiliza_display, tipo_unidad_defecto.
    Para tipo_unidad_defecto: si la columna no existe, devuelve 'Unidad'.
    Usado en ingreso mov. stock para mostrar select Unidad/Display/Bulto por renglón.
    """
    out = {
        "utiliza_bulto_cerrado": "No",
        "utiliza_display": "No",
        "tipo_unidad_defecto": "Unidad",
    }
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            cursor.execute(
                """
                SELECT COALESCE(utiliza_bulto_cerrado, 'No') AS utiliza_bulto_cerrado,
                       COALESCE(utiliza_display, 'No') AS utiliza_display
                FROM configuracion LIMIT 1
                """
            )
            row = cursor.fetchone()
            if row:
                out["utiliza_bulto_cerrado"] = str_or_default(row.get("utiliza_bulto_cerrado"), "No").strip()
                out["utiliza_display"] = str_or_default(row.get("utiliza_display"), "No").strip()
            try:
                cursor.execute("SELECT COALESCE(tipo_unidad_defecto, 'Unidad') AS tipo_unidad_defecto FROM configuracion LIMIT 1")
                row2 = cursor.fetchone()
                if row2 and row2.get("tipo_unidad_defecto"):
                    out["tipo_unidad_defecto"] = str_or_default(row2.get("tipo_unidad_defecto"), "Unidad").strip()
            except Exception:
                pass
    except Exception as e:
        logger.warning("Error al leer config unidad/bulto/display en %s: %s", base_empresa, e)
    return out


def get_config_peso_balanza(base_empresa: str) -> Dict[str, Any]:
    """
    Lee de configuracion: usa_multiplica_bulto_promedio, tipo_balanza.
    Usado en ingreso mov. stock para mostrar unidad_art_peso y botón lista_unidad_art_peso
    (paridad VB6: visible cuando usa_multiplica_bulto_promedio = Si y tipo_balanza = Bascula).
    """
    out = {"usa_multiplica_bulto_promedio": "No", "tipo_balanza": ""}
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            cursor.execute(
                """
                SELECT COALESCE(usa_multiplica_bulto_promedio, 'No') AS usa_multiplica_bulto_promedio,
                       COALESCE(tipo_balanza, '') AS tipo_balanza
                FROM configuracion LIMIT 1
                """
            )
            row = cursor.fetchone()
            if row:
                out["usa_multiplica_bulto_promedio"] = str_or_default(row.get("usa_multiplica_bulto_promedio"), "No").strip()
                out["tipo_balanza"] = str_or_default(row.get("tipo_balanza"), "").strip()
    except Exception as e:
        logger.warning("Error al leer config peso/balanza en %s: %s", base_empresa, e)
    return out


def get_pedidos_parte_produccion(base_empresa: str) -> str:
    """
    Lee de configuracion: pedidos_parte_produccion ('Si' / 'No').
    Si la columna no existe, devuelve 'No'.
    Usado para mostrar cantidad_armado (Unidad/Armado) en motivos OPT/OPP (Parte producción).
    """
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            cursor.execute(
                "SELECT COALESCE(pedidos_parte_produccion, 'No') AS pedidos_parte_produccion FROM configuracion LIMIT 1"
            )
            row = cursor.fetchone()
            if row and row.get("pedidos_parte_produccion"):
                return str_or_default(row.get("pedidos_parte_produccion"), "No").strip()
    except Exception as e:
        if "Unknown column" in str(e) or "pedidos_parte_produccion" in str(e):
            return "No"
        logger.warning("Error al leer pedidos_parte_produccion en %s: %s", base_empresa, e)
    return "No"


def get_motivos_permitidos(
    base_empresa: str,
    id_puesto: Optional[int],
    incluir_pedidos_produccion: bool = False,
) -> List[Tuple[int, str]]:
    """
    Lista motivos de movimiento permitidos para el puesto.
    Si acceso_motivo_movstock != 'Todos', filtrar por valor del permiso (paridad VB6 CargaMovStock).
    Valores: "Todos" → todos; "Movimiento interno E/S" → solo 7 y 8; "Ajuste" → 2,3,4,5; "Transferencia" → 6.
    Si no incluir_pedidos_produccion, excluir códigos 11 y 12.
    """
    permisos = _get_permisos_puesto(base_empresa, id_puesto)
    acceso = (permisos.get("acceso_motivo_movstock") or "").strip()
    if acceso == "Todos":
        motivos = list(MOTIVOS_MOVIMIENTO)
    elif acceso == "Movimiento interno E/S":
        motivos = [(c, n) for c, n in MOTIVOS_MOVIMIENTO if c in (7, 8)]
    elif acceso == "Ajuste":
        motivos = [(c, n) for c, n in MOTIVOS_MOVIMIENTO if c in (2, 3, 4, 5)]
    elif acceso == "Transferencia":
        motivos = [(c, n) for c, n in MOTIVOS_MOVIMIENTO if c == 6]
    else:
        motivos = list(MOTIVOS_MOVIMIENTO)
    # Motivos 9 (Armado), 11 (Pedido producción), 12 (Parte producción) solo desde módulo MPR
    if not incluir_pedidos_produccion:
        motivos = [(c, n) for c, n in motivos if c not in (9, 11, 12)]
    return motivos


def get_datos_iniciales_ingreso_stock(
    base_empresa: str,
    id_puesto: Optional[int],
    incluir_pedidos_produccion: bool = False,
) -> Dict[str, Any]:
    """
    Carga todos los datos iniciales para el formulario de ingreso mov. stock en 1 conexión.
    Consolida: depósitos, ref_movstock, motivos, viajantes, clientes, y toda la configuración.
    """
    resultado = {
        "depositos": [],
        "ref_movstock": [],
        "motivos": [],
        "viajantes": [],
        "clientes": [],
        "activ_proyecto": "No",
        "calculo_stock_saldo": "No",
        "utiliza_bulto_cerrado": "No",
        "utiliza_display": "No",
        "tipo_unidad_defecto": "Unidad",
        "usa_multiplica_bulto_promedio": "No",
        "tipo_balanza": "",
        "pedidos_parte_produccion": "No",
    }
    try:
        permisos = _get_permisos_puesto(base_empresa, id_puesto)
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            # Configuración (1 query)
            config_cols = ["activ_proyecto"]
            opt_config = [
                "calculo_stock_saldo", "utiliza_bulto_cerrado", "utiliza_display",
                "tipo_unidad_defecto", "usa_multiplica_bulto_promedio", "tipo_balanza",
                "pedidos_parte_produccion",
            ]
            cursor.execute("SHOW COLUMNS FROM configuracion")
            existing = {r["Field"] for r in cursor.fetchall()}
            select_parts = []
            for col in config_cols + opt_config:
                if col in existing:
                    select_parts.append(f"COALESCE({col}, '') AS {col}")
            if select_parts:
                cursor.execute(f"SELECT {', '.join(select_parts)} FROM configuracion LIMIT 1")
                cfg = cursor.fetchone()
                if cfg:
                    resultado["activ_proyecto"] = (cfg.get("activ_proyecto") or "No").strip() or "No"
                    resultado["calculo_stock_saldo"] = (cfg.get("calculo_stock_saldo") or "No").strip() or "No"
                    resultado["utiliza_bulto_cerrado"] = (cfg.get("utiliza_bulto_cerrado") or "No").strip() or "No"
                    resultado["utiliza_display"] = (cfg.get("utiliza_display") or "No").strip() or "No"
                    resultado["tipo_unidad_defecto"] = (cfg.get("tipo_unidad_defecto") or "Unidad").strip() or "Unidad"
                    resultado["usa_multiplica_bulto_promedio"] = (cfg.get("usa_multiplica_bulto_promedio") or "No").strip() or "No"
                    resultado["tipo_balanza"] = (cfg.get("tipo_balanza") or "").strip()
                    resultado["pedidos_parte_produccion"] = (cfg.get("pedidos_parte_produccion") or "No").strip() or "No"

            # Depósitos
            acceso_dep = (permisos.get("acceso_deposito") or "").strip()
            id_dep = permisos.get("id_deposito")
            if acceso_dep == "Todos" or not id_dep:
                cursor.execute("SELECT CodDeposito, COALESCE(NombreDeposito, '') AS NombreDeposito FROM deposito WHERE COALESCE(anulado, 'No') = 'No' ORDER BY NombreDeposito")
            else:
                cursor.execute("SELECT CodDeposito, COALESCE(NombreDeposito, '') AS NombreDeposito FROM deposito WHERE CodDeposito = %s AND COALESCE(anulado, 'No') = 'No'", [id_dep])
            resultado["depositos"] = [dict(r) for r in cursor.fetchall()]

            # Ref movstock
            acceso_ref = (permisos.get("acceso_ref_movstock") or "").strip()
            id_ref = permisos.get("id_refmovstock")
            if acceso_ref == "Todos" or not id_ref:
                cursor.execute("SELECT id_ref_movstock, COALESCE(nombre_ref_movstock, '') AS nombre_ref_movstock FROM ref_movstock WHERE COALESCE(anulado, 'No') = 'No' ORDER BY nombre_ref_movstock")
            else:
                cursor.execute("SELECT id_ref_movstock, COALESCE(nombre_ref_movstock, '') AS nombre_ref_movstock FROM ref_movstock WHERE id_ref_movstock = %s AND COALESCE(anulado, 'No') = 'No'", [int(id_ref)])
            resultado["ref_movstock"] = [dict(r) for r in cursor.fetchall()]

            # Viajantes
            cursor.execute("SELECT CodViajante, COALESCE(Nombre, '') AS Nombre FROM viajantes WHERE COALESCE(anulado, 'No') = 'No' ORDER BY Nombre")
            resultado["viajantes"] = [dict(r) for r in cursor.fetchall()]

            # Clientes
            try:
                cursor.execute("SELECT Codigo, COALESCE(nombre_cliente, '') AS nombre_cliente FROM cliente WHERE COALESCE(anulado, 'No') = 'No' ORDER BY nombre_cliente LIMIT 300")
            except Exception:
                cursor.execute("SELECT Codigo, COALESCE(nombre_cliente, '') AS nombre_cliente FROM cliente ORDER BY nombre_cliente LIMIT 300")
            resultado["clientes"] = [dict(r) for r in cursor.fetchall()]

        # Motivos (lógica en Python, sin query)
        resultado["motivos"] = [
            {"codigo": c, "nombre": n}
            for c, n in get_motivos_permitidos(base_empresa, id_puesto, incluir_pedidos_produccion)
        ]
    except Exception as e:
        logger.warning("Error en get_datos_iniciales_ingreso_stock (%s): %s", base_empresa, e)
    return resultado


def buscar_articulos(
    base_empresa: str,
    q: str,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """
    Búsqueda de artículos por código, nombre o código de barras.
    Devuelve IDArt, CodigoArticulo (texto), Descripcion (NombreArticulo) para el formulario.
    """
    if not (q or "").strip():
        return []
    try:
        term = f"%{(q or '').strip()}%"
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            cursor.execute(
                """
                SELECT a.IDArt,
                       COALESCE(a.CodigoArticuloT, CAST(a.CodigoArticulo AS CHAR), '') AS CodigoArticulo,
                       COALESCE(a.NombreArticulo, '') AS Descripcion
                FROM articulo a
                WHERE (
                    a.NombreArticulo LIKE %s
                    OR a.CodigoArticuloT LIKE %s
                    OR a.NroCodBarra LIKE %s
                    OR CAST(a.CodigoArticulo AS CHAR) LIKE %s
                  )
                ORDER BY a.NombreArticulo
                LIMIT %s
                """,
                [term, term, term, term, limit],
            )
            rows = cursor.fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.warning("Error al buscar artículos en %s: %s", base_empresa, e)
        return []


def _buscar_articulos_con_precios(
    base_empresa: str,
    q: str,
    limit: int = 15,
) -> List[Dict[str, Any]]:
    """
    Búsqueda de artículos con campos de precios (paridad con ABMArticulo_seleccion grid).
    Devuelve IDArt, CodigoArticulo, Descripcion, id_manual, PrecioCosto, Precio1V, PNOficial, Alicuota (porcentaje desde iva), Moneda.
    articulo.Alicuota es FK a iva.id; el porcentaje para mostrar está en iva.Alicuota (igual que reportes y TPV).
    """
    if not (q or "").strip():
        return []
    try:
        term = f"%{(q or '').strip()}%"
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            cursor.execute(
                """
                SELECT a.IDArt,
                       COALESCE(a.CodigoArticuloT, CAST(a.CodigoArticulo AS CHAR), '') AS CodigoArticulo,
                       COALESCE(a.NombreArticulo, '') AS Descripcion,
                       a.id_manual,
                       a.PrecioCosto,
                       a.Precio1V,
                       a.PNOficial,
                       COALESCE(iva.Alicuota, a.Alicuota, 0) AS Alicuota,
                       a.Moneda
                FROM articulo a
                LEFT JOIN iva ON iva.id = a.Alicuota
                WHERE (
                    a.NombreArticulo LIKE %s
                    OR a.CodigoArticuloT LIKE %s
                    OR a.NroCodBarra LIKE %s
                    OR CAST(a.CodigoArticulo AS CHAR) LIKE %s
                  )
                ORDER BY a.NombreArticulo
                LIMIT %s
                """,
                [term, term, term, term, limit],
            )
            rows = cursor.fetchall()
        result = []
        for r in rows:
            result.append({
                "IDArt": to_int_or_none(r.get("IDArt")),
                "CodigoArticulo": str_or_default(r.get("CodigoArticulo"), "-"),
                "Descripcion": str_or_default(r.get("Descripcion"), "-"),
                "id_manual": str_or_default(r.get("id_manual"), "-"),
                "PrecioCosto": to_decimal_or_none(r.get("PrecioCosto")),
                "Precio1V": to_decimal_or_none(r.get("Precio1V")),
                "PNOficial": to_decimal_or_none(r.get("PNOficial")),
                "Alicuota": to_decimal_or_none(r.get("Alicuota")),
                "Moneda": str_or_default(r.get("Moneda"), "-"),
            })
        return result
    except Exception as e:
        logger.warning("Error al buscar artículos con precios en %s: %s", base_empresa, e)
        return []


def buscar_articulo_por_codigo_exacto(
    base_empresa: str,
    codigo: str,
    id_deposito: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    """
    Búsqueda exacta por código de barras / id_manual / IDArt (misma lógica que TPV).
    Campos: id_manual, IDArt, NroCodBarra, NroCodBarraF, CodigoArticuloT, CodArtProv.
    Devuelve un único artículo en el mismo formato que buscar_articulos_para_movimiento (con stock_depositos, stock_lotes),
    o None si no hay coincidencia.
    """
    cod = (codigo or "").strip()
    if not cod:
        return None
    try:
        import MySQLdb
        sql_ext = """
            SELECT a.IDArt,
                   COALESCE(a.CodigoArticuloT, CAST(a.CodigoArticulo AS CHAR), '') AS CodigoArticulo,
                   COALESCE(a.NombreArticulo, '') AS Descripcion,
                   a.id_manual,
                   a.PrecioCosto,
                   a.Precio1V,
                   a.PNOficial,
                   COALESCE(iva.Alicuota, a.Alicuota, 0) AS Alicuota,
                   a.Moneda
            FROM articulo a
            LEFT JOIN iva ON iva.id = a.Alicuota
            WHERE (a.id_manual = %s OR CAST(a.IDArt AS CHAR) = %s
                   OR a.NroCodBarra = %s OR a.NroCodBarraF = %s
                   OR a.CodigoArticuloT = %s OR a.CodArtProv = %s)
            LIMIT 1
        """
        sql_basic = """
            SELECT a.IDArt,
                   COALESCE(a.CodigoArticuloT, CAST(a.CodigoArticulo AS CHAR), '') AS CodigoArticulo,
                   COALESCE(a.NombreArticulo, '') AS Descripcion,
                   a.id_manual,
                   a.PrecioCosto,
                   a.Precio1V,
                   a.PNOficial,
                   COALESCE(iva.Alicuota, a.Alicuota, 0) AS Alicuota,
                   a.Moneda
            FROM articulo a
            LEFT JOIN iva ON iva.id = a.Alicuota
            WHERE (a.id_manual = %s OR CAST(a.IDArt AS CHAR) = %s
                   OR a.NroCodBarra = %s OR a.CodigoArticuloT = %s)
            LIMIT 1
        """
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            try:
                cursor.execute(sql_ext, [cod] * 6)
            except MySQLdb.ProgrammingError as e:
                if (e.args and e.args[0] == 1054) or "Unknown column" in str(e):
                    cursor.execute(sql_basic, [cod, cod, cod, cod])
                else:
                    raise
            row = cursor.fetchone()
        if not row:
            return None
        a = {
            "IDArt": to_int_or_none(row.get("IDArt")),
            "CodigoArticulo": str_or_default(row.get("CodigoArticulo"), "-"),
            "Descripcion": str_or_default(row.get("Descripcion"), "-"),
            "id_manual": str_or_default(row.get("id_manual"), "-"),
            "PrecioCosto": to_decimal_or_none(row.get("PrecioCosto")),
            "Precio1V": to_decimal_or_none(row.get("Precio1V")),
            "PNOficial": to_decimal_or_none(row.get("PNOficial")),
            "Alicuota": to_decimal_or_none(row.get("Alicuota")),
            "Moneda": str_or_default(row.get("Moneda"), "-"),
        }
        id_art = a.get("IDArt")
        if not id_art:
            return None
        a["stock_depositos"] = get_stock_por_deposito(base_empresa, id_art)
        a["stock_lotes"] = get_stock_por_lote(base_empresa, id_art, id_deposito=id_deposito)
        return a
    except Exception as e:
        logger.warning("Error al buscar artículo por código exacto en %s: %s", base_empresa, e)
        return None


def _buscar_articulos_ensamblados_con_precios(
    base_empresa: str,
    q: str,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """
    Búsqueda de artículos ensamblados (articulo.id_en_abm IS NOT NULL, en_abm.anulado = 'No').
    Si q.strip() == '*', devuelve todos hasta limit; si no, filtra por nombre/código (LIKE).
    Mismo formato que _buscar_articulos_con_precios (IDArt, CodigoArticulo, Descripcion, id_manual, precios, etc.).
    """
    q_clean = (q or "").strip()
    busqueda_completa = q_clean == "*"
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            if busqueda_completa:
                cursor.execute(
                    """
                    SELECT a.IDArt,
                           COALESCE(a.CodigoArticuloT, CAST(a.CodigoArticulo AS CHAR), '') AS CodigoArticulo,
                           COALESCE(a.NombreArticulo, '') AS Descripcion,
                           a.id_manual,
                           a.PrecioCosto,
                           a.Precio1V,
                           a.PNOficial,
                           COALESCE(iva.Alicuota, a.Alicuota, 0) AS Alicuota,
                           a.Moneda
                    FROM articulo a
                    INNER JOIN en_abm e ON e.id_en_abm = a.id_en_abm AND COALESCE(e.anulado, 'No') = 'No'
                    LEFT JOIN iva ON iva.id = a.Alicuota
                    WHERE a.id_en_abm IS NOT NULL
                    ORDER BY a.NombreArticulo
                    LIMIT %s
                    """,
                    [limit],
                )
            else:
                if not q_clean:
                    return []
                term = f"%{q_clean}%"
                cursor.execute(
                    """
                    SELECT a.IDArt,
                           COALESCE(a.CodigoArticuloT, CAST(a.CodigoArticulo AS CHAR), '') AS CodigoArticulo,
                           COALESCE(a.NombreArticulo, '') AS Descripcion,
                           a.id_manual,
                           a.PrecioCosto,
                           a.Precio1V,
                           a.PNOficial,
                           COALESCE(iva.Alicuota, a.Alicuota, 0) AS Alicuota,
                           a.Moneda
                    FROM articulo a
                    INNER JOIN en_abm e ON e.id_en_abm = a.id_en_abm AND COALESCE(e.anulado, 'No') = 'No'
                    LEFT JOIN iva ON iva.id = a.Alicuota
                    WHERE a.id_en_abm IS NOT NULL
                      AND (
                          a.NombreArticulo LIKE %s
                          OR a.CodigoArticuloT LIKE %s
                          OR a.NroCodBarra LIKE %s
                          OR CAST(a.CodigoArticulo AS CHAR) LIKE %s
                          OR a.id_manual LIKE %s
                      )
                    ORDER BY a.NombreArticulo
                    LIMIT %s
                    """,
                    [term, term, term, term, term, limit],
                )
            rows = cursor.fetchall()
        result = []
        for r in rows:
            result.append({
                "IDArt": to_int_or_none(r.get("IDArt")),
                "CodigoArticulo": str_or_default(r.get("CodigoArticulo"), "-"),
                "Descripcion": str_or_default(r.get("Descripcion"), "-"),
                "id_manual": str_or_default(r.get("id_manual"), "-"),
                "PrecioCosto": to_decimal_or_none(r.get("PrecioCosto")),
                "Precio1V": to_decimal_or_none(r.get("Precio1V")),
                "PNOficial": to_decimal_or_none(r.get("PNOficial")),
                "Alicuota": to_decimal_or_none(r.get("Alicuota")),
                "Moneda": str_or_default(r.get("Moneda"), "-"),
                "tiene_formula": True,
            })
        return result
    except Exception as e:
        logger.warning("Error al buscar artículos ensamblados en %s: %s", base_empresa, e)
        return []


def _bulk_stock_y_lotes(
    base_empresa: str,
    ids: List[int],
    id_deposito: Optional[int] = None,
) -> Tuple[Dict[int, list], Dict[int, list]]:
    """Obtiene stock por depósito y lotes para una lista de IDArt en 1 conexión (2 queries)."""
    stock_map: Dict[int, list] = {}
    lote_map: Dict[int, list] = {}
    if not ids:
        return stock_map, lote_map
    try:
        placeholders = ",".join(["%s"] * len(ids))
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            cursor.execute(
                f"""
                SELECT sd.id_articulo, sd.id_deposito, sd.saldo,
                       COALESCE(d.NombreDeposito, '') AS nombre_deposito
                FROM stock_deposito sd
                INNER JOIN deposito d ON d.CodDeposito = sd.id_deposito
                WHERE sd.id_articulo IN ({placeholders})
                  AND COALESCE(d.anulado, 'No') = 'No'
                ORDER BY d.NombreDeposito
                """,
                ids,
            )
            for sr in cursor.fetchall():
                aid = sr.get("id_articulo")
                stock_map.setdefault(aid, []).append({
                    "id_deposito": to_int_or_none(sr.get("id_deposito")),
                    "nombre_deposito": str_or_default(sr.get("nombre_deposito"), "-"),
                    "saldo": to_decimal_or_none(sr.get("saldo")) or Decimal(0),
                })

            if id_deposito is not None:
                cursor.execute(
                    f"""
                    SELECT l.id_articulo, l.id_lote, l.cod_lote, l.fecha_vto_lote, ls.stock_lote
                    FROM lote l INNER JOIN lote_stock ls ON ls.id_lote = l.id_lote
                    WHERE l.id_articulo IN ({placeholders}) AND ls.id_deposito = %s
                      AND COALESCE(l.anulado, 'No') = 'No' AND COALESCE(ls.stock_lote, 0) <> 0
                    ORDER BY l.fecha_vto_lote ASC
                    """,
                    ids + [id_deposito],
                )
            else:
                cursor.execute(
                    f"""
                    SELECT l.id_articulo, l.id_lote, l.cod_lote, l.fecha_vto_lote,
                           COALESCE(SUM(ls.stock_lote), 0) AS stock_lote
                    FROM lote l INNER JOIN lote_stock ls ON ls.id_lote = l.id_lote
                    WHERE l.id_articulo IN ({placeholders})
                      AND COALESCE(l.anulado, 'No') = 'No'
                    GROUP BY l.id_articulo, l.id_lote, l.cod_lote, l.fecha_vto_lote
                    HAVING COALESCE(SUM(ls.stock_lote), 0) <> 0
                    ORDER BY l.fecha_vto_lote ASC
                    """,
                    ids,
                )
            for lr in cursor.fetchall():
                aid = lr.get("id_articulo")
                vto_raw = lr.get("fecha_vto_lote")
                lote_map.setdefault(aid, []).append({
                    "id_lote": to_int_or_none(lr.get("id_lote")),
                    "cod_lote": str_or_default(lr.get("cod_lote"), ""),
                    "fecha_vto_lote": str(vto_raw) if vto_raw else None,
                    "vto_lote": str(vto_raw) if vto_raw else None,
                    "stock_lote": to_decimal_or_none(lr.get("stock_lote")) or Decimal(0),
                })
    except Exception as e:
        logger.warning("Error en _bulk_stock_y_lotes (%s): %s", base_empresa, e)
    return stock_map, lote_map


def buscar_articulos_ensamblados_para_movimiento(
    base_empresa: str,
    q: str,
    limit: int = 50,
    id_deposito: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Artículos ensamblados con stock bulk (misma optimización que buscar_articulos_para_movimiento).
    """
    articulos = _buscar_articulos_ensamblados_con_precios(base_empresa, q, limit=limit)
    if not articulos:
        return []
    ids = [a["IDArt"] for a in articulos if a.get("IDArt")]
    if not ids:
        return []
    stock_map, lote_map = _bulk_stock_y_lotes(base_empresa, ids, id_deposito)
    result = []
    for a in articulos:
        aid = a.get("IDArt")
        if not aid:
            continue
        item = dict(a)
        item["stock_depositos"] = stock_map.get(aid, [])
        item["stock_lotes"] = lote_map.get(aid, [])
        result.append(item)
    return result


def buscar_articulos_para_movimiento(
    base_empresa: str,
    q: str,
    limit: int = 10,
    id_deposito: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Búsqueda para ingreso de renglón de movimiento de stock: artículo + precios + stock por depósito + stock por lote.
    Usa 1 conexión con 3 queries bulk (artículos + stock + lotes) en vez de N+1.
    """
    if not (q or "").strip():
        return []
    try:
        term = f"%{(q or '').strip()}%"
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            cursor.execute("SHOW COLUMNS FROM articulo")
            art_cols = {r["Field"] for r in cursor.fetchall()}

            opt_cols = []
            for col in ("cantidad_uni", "unidad_art_peso", "lote_articulo",
                        "serie_articulo", "marca", "multiplicador_vta"):
                if col in art_cols:
                    opt_cols.append(f"a.{col}")
                else:
                    opt_cols.append(f"NULL AS {col}")
            opt_select = ", ".join(opt_cols)

            cursor.execute(
                f"""
                SELECT a.IDArt,
                       COALESCE(a.CodigoArticuloT, CAST(a.CodigoArticulo AS CHAR), '') AS CodigoArticulo,
                       COALESCE(a.NombreArticulo, '') AS Descripcion,
                       a.id_manual, a.PrecioCosto, a.Precio1V, a.PNOficial,
                       COALESCE(iva.Alicuota, a.Alicuota, 0) AS Alicuota,
                       a.Moneda,
                       {opt_select}
                FROM articulo a
                LEFT JOIN iva ON iva.id = a.Alicuota
                WHERE (a.NombreArticulo LIKE %s OR a.CodigoArticuloT LIKE %s
                       OR a.NroCodBarra LIKE %s OR CAST(a.CodigoArticulo AS CHAR) LIKE %s)
                ORDER BY a.NombreArticulo
                LIMIT %s
                """,
                [term, term, term, term, limit],
            )
            art_rows = cursor.fetchall()

            if not art_rows:
                return []

            ids = [r["IDArt"] for r in art_rows if r.get("IDArt")]
            if not ids:
                return []

        stock_map, lote_map = _bulk_stock_y_lotes(base_empresa, ids, id_deposito)

        result = []
        for r in art_rows:
            aid = r.get("IDArt")
            result.append({
                "IDArt": to_int_or_none(aid),
                "CodigoArticulo": str_or_default(r.get("CodigoArticulo"), "-"),
                "Descripcion": str_or_default(r.get("Descripcion"), "-"),
                "id_manual": str_or_default(r.get("id_manual"), "-"),
                "PrecioCosto": to_decimal_or_none(r.get("PrecioCosto")),
                "Precio1V": to_decimal_or_none(r.get("Precio1V")),
                "PNOficial": to_decimal_or_none(r.get("PNOficial")),
                "Alicuota": to_decimal_or_none(r.get("Alicuota")),
                "Moneda": str_or_default(r.get("Moneda"), "-"),
                "multiplicador_vta": r.get("multiplicador_vta"),
                "cantidad_uni": r.get("cantidad_uni"),
                "unidad_art_peso": r.get("unidad_art_peso"),
                "lote_articulo": r.get("lote_articulo"),
                "serie_articulo": r.get("serie_articulo"),
                "marca": r.get("marca"),
                "stock_depositos": stock_map.get(aid, []),
                "stock_lotes": lote_map.get(aid, []),
            })
        return result
    except Exception as e:
        logger.warning("Error en buscar_articulos_para_movimiento (%s): %s", base_empresa, e)
        return []


def get_saldo_articulo_deposito(
    base_empresa: str,
    id_articulo: int,
    id_deposito: int,
) -> Decimal:
    """Saldo disponible del artículo en el depósito (stock_deposito.saldo)."""
    try:
        with mysql_cursor(base_empresa, dict_cursor=False) as cursor:
            cursor.execute(
                "SELECT COALESCE(saldo, 0) FROM stock_deposito WHERE id_articulo = %s AND id_deposito = %s",
                [id_articulo, id_deposito],
            )
            row = cursor.fetchone()
        return Decimal(str(row[0] or 0)) if row else Decimal(0)
    except Exception as e:
        logger.warning("Error al obtener saldo: %s", e)
        return Decimal(0)


def get_stock_por_deposito(
    base_empresa: str,
    id_articulo: int,
) -> List[Dict[str, Any]]:
    """
    Stock disponible del artículo por depósito (paridad con ABMArticulo_seleccion Data_Stock).
    Devuelve lista con id_deposito, nombre_deposito, saldo (solo depósitos no anulados).
    """
    if not id_articulo:
        return []
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            cursor.execute(
                """
                SELECT sd.id_deposito, sd.saldo, COALESCE(d.NombreDeposito, '') AS nombre_deposito
                FROM stock_deposito sd
                INNER JOIN deposito d ON d.CodDeposito = sd.id_deposito
                WHERE sd.id_articulo = %s
                  AND COALESCE(d.anulado, 'No') = 'No'
                ORDER BY d.NombreDeposito
                """,
                [id_articulo],
            )
            rows = cursor.fetchall()
        return [
            {
                "id_deposito": to_int_or_none(r.get("id_deposito")),
                "nombre_deposito": str_or_default(r.get("nombre_deposito"), "-"),
                "saldo": to_decimal_or_none(r.get("saldo")) or Decimal(0),
            }
            for r in rows
        ]
    except Exception as e:
        logger.warning("Error al obtener stock por depósito (id_articulo=%s): %s", id_articulo, e)
        return []


def get_stock_por_lote(
    base_empresa: str,
    id_articulo: int,
    id_deposito: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Stock por lote del artículo (paridad con ABMArticulo_seleccion data_lote).
    Devuelve lista con id_lote, cod_lote, fecha_vto_lote, vto_lote (texto), stock_lote.
    Si id_deposito se indica, filtra por ese depósito; si no, suma stock_lote por lote.
    """
    if not id_articulo:
        return []
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            if id_deposito is not None:
                cursor.execute(
                    """
                    SELECT l.id_lote, l.cod_lote, l.fecha_vto_lote, ls.stock_lote
                    FROM lote l
                    INNER JOIN lote_stock ls ON ls.id_lote = l.id_lote
                    WHERE l.id_articulo = %s AND ls.id_deposito = %s
                      AND COALESCE(l.anulado, 'No') = 'No' AND COALESCE(ls.stock_lote, 0) <> 0
                    ORDER BY l.fecha_vto_lote ASC
                    """,
                    [id_articulo, id_deposito],
                )
            else:
                cursor.execute(
                    """
                    SELECT l.id_lote, l.cod_lote, l.fecha_vto_lote, COALESCE(SUM(ls.stock_lote), 0) AS stock_lote
                    FROM lote l
                    INNER JOIN lote_stock ls ON ls.id_lote = l.id_lote
                    WHERE l.id_articulo = %s
                      AND COALESCE(l.anulado, 'No') = 'No'
                    GROUP BY l.id_lote, l.cod_lote, l.fecha_vto_lote
                    HAVING COALESCE(SUM(ls.stock_lote), 0) <> 0
                    ORDER BY l.fecha_vto_lote ASC
                    """,
                    [id_articulo],
                )
            rows = cursor.fetchall()
        result = []
        for r in rows:
            fv = to_date_or_none(r.get("fecha_vto_lote"))
            vto_str = str(fv) if fv else "-"
            result.append({
                "id_lote": to_int_or_none(r.get("id_lote")),
                "cod_lote": str_or_default(r.get("cod_lote"), "-"),
                "fecha_vto_lote": fv,
                "vto_lote": vto_str,
                "stock_lote": to_decimal_or_none(r.get("stock_lote")) or Decimal(0),
            })
        return result
    except Exception as e:
        logger.warning("Error al obtener stock por lote (id_articulo=%s): %s", id_articulo, e)
        return []


def listar_renglones_temporales(
    base_empresa: str,
    id_usuario: int,
) -> List[Dict[str, Any]]:
    """Renglones en cuerpostock_mstock para el usuario (visualiza='No', CodigoMovimiento=1). Incluye id_manual, nro_pedi, serie_articulo, lote_articulo (Si/No) y campos para tooltip."""
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            cursor.execute(
                """
                SELECT c.Orden, c.IDArt, c.CodigoArticulo, c.Descripcion, c.Cantidad, c.entrada, c.salida, c.ES,
                       c.CodDeposito, c.cod_deposito_destino, c.id_lote, c.cod_lote, c.vto_lote,
                       c.id_manual, c.nro_pedi, c.codmov_nro_pedi,
                       c.marca, c.multiplicador_vta, c.cantidad_uni,
                       COALESCE(NULLIF(TRIM(c.tipo_unidad), ''), 'Unidad') AS tipo_unidad,
                       c.unidad_art_peso,
                       COALESCE(NULLIF(TRIM(a.serie), ''), 'No') AS serie_articulo,
                       COALESCE(NULLIF(TRIM(a.lote), ''), 'No') AS lote_articulo
                FROM cuerpostock_mstock c
                LEFT JOIN articulo a ON a.IDArt = c.IDArt
                WHERE c.CodUsuario = %s AND COALESCE(c.visualiza, 'No') = 'No'
                  AND COALESCE(c.CodigoMovimiento, 1) = 1
                ORDER BY c.Orden
                """,
                [id_usuario],
            )
            rows = cursor.fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.warning("Error al listar temporales en %s: %s", base_empresa, e)
        return []


def listar_series_renglon(
    base_empresa: str,
    id_usuario: int,
    orden: int,
    id_articulo: int,
    es_entrada: bool,
) -> List[Dict[str, Any]]:
    """Lista números de serie en temp para un renglón (serie_entrada_temp si entrada, serie_salida_temp si salida)."""
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            if es_entrada:
                cursor.execute(
                    """
                    SELECT id_serie_entrada_temp AS id_temp, nro_serie, vto_serie
                    FROM serie_entrada_temp
                    WHERE id_usuario = %s AND COALESCE(tipo_comprobante, '') = 'Mstock'
                      AND orden = %s AND id_articulo = %s
                    ORDER BY id_serie_entrada_temp
                    """,
                    [id_usuario, orden, id_articulo],
                )
            else:
                cursor.execute(
                    """
                    SELECT id_serie_salida_temp AS id_temp, nro_serie, vto_serie, id_serie_entrada
                    FROM serie_salida_temp
                    WHERE id_usuario = %s AND COALESCE(tipo_comprobante, '') = 'Mstock'
                      AND orden = %s AND id_articulo = %s
                    ORDER BY id_serie_salida_temp
                    """,
                    [id_usuario, orden, id_articulo],
                )
            rows = cursor.fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.warning("Error al listar series renglón %s: %s", orden, e)
        return []


def listar_series_disponibles_deposito(
    base_empresa: str,
    id_articulo: int,
    id_deposito: int,
) -> List[Dict[str, Any]]:
    """Lista series disponibles (serie_entrada.disponible='Si') para un artículo en un depósito (para salida)."""
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            cursor.execute(
                """
                SELECT id_serie_entrada, nro_serie, vto_serie
                FROM serie_entrada
                WHERE id_articulo = %s AND id_deposito = %s
                  AND COALESCE(anulado, 'No') = 'No' AND COALESCE(disponible, 'Si') = 'Si'
                ORDER BY nro_serie
                """,
                [id_articulo, id_deposito],
            )
            rows = cursor.fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.warning("Error al listar series disponibles: %s", e)
        return []


def agregar_serie_entrada_temp(
    base_empresa: str,
    id_usuario: int,
    orden: int,
    id_articulo: int,
    id_deposito: int,
    nro_serie: str,
    vto_serie: Optional[str] = None,
) -> Optional[Dict[str, str]]:
    """Inserta un número de serie en serie_entrada_temp para movimiento de entrada."""
    try:
        with mysql_cursor(base_empresa, dict_cursor=False) as cursor:
            cursor.execute(
                """
                INSERT INTO serie_entrada_temp
                (id_articulo, nro_serie, vto_serie, tipo_comprobante, fecha, id_usuario, visualiza, orden, id_deposito)
                VALUES (%s, %s, %s, 'Mstock', CURDATE(), %s, 'No', %s, %s)
                """,
                [
                    id_articulo,
                    (nro_serie or "").strip() or None,
                    to_date_or_none(vto_serie) if vto_serie else None,
                    id_usuario,
                    orden,
                    id_deposito,
                ],
            )
        return None
    except Exception as e:
        logger.warning("Error al agregar serie entrada temp: %s", e)
        return {"error": str(e)}


def agregar_serie_salida_temp(
    base_empresa: str,
    id_usuario: int,
    orden: int,
    id_articulo: int,
    id_deposito: int,
    id_serie_entrada: int,
) -> Optional[Dict[str, str]]:
    """Inserta en serie_salida_temp una serie seleccionada (por id_serie_entrada) para salida."""
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            cursor.execute(
                "SELECT nro_serie, vto_serie, desc_serie FROM serie_entrada WHERE id_serie_entrada = %s",
                [id_serie_entrada],
            )
            row = cursor.fetchone()
            if not row:
                return {"error": "Serie no encontrada."}
            nro_serie = str_or_default(row.get("nro_serie"), "")
            vto_serie = row.get("vto_serie")
            desc_serie = str_or_default(row.get("desc_serie"), "")
        with mysql_cursor(base_empresa, dict_cursor=False) as cursor:
            cursor.execute(
                """
                INSERT INTO serie_salida_temp
                (id_serie_entrada, id_articulo, nro_serie, vto_serie, desc_serie, tipo_comprobante, fecha, id_usuario, visualiza, orden, id_deposito)
                VALUES (%s, %s, %s, %s, %s, 'Mstock', CURDATE(), %s, 'No', %s, %s)
                """,
                [
                    id_serie_entrada,
                    id_articulo,
                    nro_serie,
                    vto_serie,
                    desc_serie,
                    id_usuario,
                    orden,
                    id_deposito,
                ],
            )
        return None
    except Exception as e:
        logger.warning("Error al agregar serie salida temp: %s", e)
        return {"error": str(e)}


def quitar_serie_entrada_temp(
    base_empresa: str,
    id_usuario: int,
    id_serie_entrada_temp: int,
) -> Optional[Dict[str, str]]:
    """Elimina un registro de serie_entrada_temp (solo si pertenece al usuario y tipo Mstock)."""
    try:
        with mysql_cursor(base_empresa, dict_cursor=False) as cursor:
            cursor.execute(
                """
                DELETE FROM serie_entrada_temp
                WHERE id_serie_entrada_temp = %s AND id_usuario = %s AND COALESCE(tipo_comprobante, '') = 'Mstock'
                """,
                [id_serie_entrada_temp, id_usuario],
            )
        return None
    except Exception as e:
        logger.warning("Error al quitar serie entrada temp: %s", e)
        return {"error": str(e)}


def quitar_serie_salida_temp(
    base_empresa: str,
    id_usuario: int,
    id_serie_salida_temp: int,
) -> Optional[Dict[str, str]]:
    """Elimina un registro de serie_salida_temp (solo si pertenece al usuario y tipo Mstock)."""
    try:
        with mysql_cursor(base_empresa, dict_cursor=False) as cursor:
            cursor.execute(
                """
                DELETE FROM serie_salida_temp
                WHERE id_serie_salida_temp = %s AND id_usuario = %s AND COALESCE(tipo_comprobante, '') = 'Mstock'
                """,
                [id_serie_salida_temp, id_usuario],
            )
        return None
    except Exception as e:
        logger.warning("Error al quitar serie salida temp: %s", e)
        return {"error": str(e)}


def agregar_renglon_temporal(
    base_empresa: str,
    id_usuario: int,
    datos: Dict[str, Any],
) -> Optional[Dict[str, str]]:
    """
    Inserta un renglón en cuerpostock_mstock.
    datos: IDArt, CodigoArticulo, Descripcion, Cantidad, entrada, salida, ES, CodDeposito,
           cod_deposito_destino (opcional), id_lote, cod_lote, vto_lote (opcionales),
           id_manual, nro_pedi (opcionales), marca, multiplicador_vta, cantidad_uni, tipo_unidad, unidad_art_peso (opc. para tooltip).
    Devuelve None si ok, o dict con clave 'error'.
    """
    try:
        with mysql_cursor(base_empresa, dict_cursor=False) as cursor:
            cursor.execute(
                "SELECT COALESCE(MAX(Orden), 0) + 1 FROM cuerpostock_mstock WHERE CodUsuario = %s AND COALESCE(visualiza, 'No') = 'No'",
                [id_usuario],
            )
            row = cursor.fetchone()
            orden = int(row[0]) if row else 1

            codmov_nro_pedi = datos.get("codmov_nro_pedi")
            if codmov_nro_pedi is None and datos.get("nro_pedi") is not None:
                try:
                    nro = str(datos.get("nro_pedi")).strip()
                    if nro and nro.replace(".", "").replace("-", "").isdigit():
                        codmov_nro_pedi = int(float(nro))
                except (ValueError, TypeError):
                    codmov_nro_pedi = None

            cursor.execute(
                """
                INSERT INTO cuerpostock_mstock
                (Orden, CodUsuario, visualiza, CodigoMovimiento, IDArt, CodigoArticulo, Descripcion,
                 Cantidad, entrada, salida, ES, CodDeposito, cod_deposito_destino, id_lote, cod_lote, vto_lote,
                 id_manual, nro_pedi, codmov_nro_pedi, marca, multiplicador_vta, cantidad_uni, tipo_unidad, unidad_art_peso)
                VALUES (%s, %s, 'No', 1, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                [
                    orden,
                    id_usuario,
                    datos.get("IDArt"),
                    datos.get("CodigoArticulo") or "",
                    datos.get("Descripcion") or "",
                    datos.get("Cantidad") or 0,
                    datos.get("entrada") or 0,
                    datos.get("salida") or 0,
                    datos.get("ES") or "E",
                    datos.get("CodDeposito"),
                    datos.get("cod_deposito_destino"),
                    datos.get("id_lote"),
                    datos.get("cod_lote"),
                    datos.get("vto_lote"),
                    datos.get("id_manual"),
                    datos.get("nro_pedi"),
                    codmov_nro_pedi,
                    datos.get("marca"),
                    datos.get("multiplicador_vta"),
                    datos.get("cantidad_uni"),
                    datos.get("tipo_unidad"),
                    datos.get("unidad_art_peso"),
                ],
            )
        return None
    except Exception as e:
        logger.exception("Error al agregar renglón temporal")
        return {"error": str(e)}


def quitar_renglon_temporal(
    base_empresa: str,
    id_usuario: int,
    orden: int,
) -> Optional[Dict[str, str]]:
    """Elimina el renglón con Orden dado de cuerpostock_mstock para el usuario."""
    try:
        with mysql_cursor(base_empresa, dict_cursor=False) as cursor:
            cursor.execute(
                "DELETE FROM cuerpostock_mstock WHERE CodUsuario = %s AND COALESCE(visualiza, 'No') = 'No' AND Orden = %s",
                [id_usuario, orden],
            )
        return None
    except Exception as e:
        logger.exception("Error al quitar renglón temporal")
        return {"error": str(e)}


def actualizar_renglon_temporal(
    base_empresa: str,
    id_usuario: int,
    orden: int,
    datos: Dict[str, Any],
) -> Optional[Dict[str, str]]:
    """
    Actualiza el renglón con Orden dado en cuerpostock_mstock.
    datos: IDArt, CodigoArticulo, Descripcion, Cantidad, entrada, salida, ES, CodDeposito, cod_deposito_destino (opc),
           id_manual, nro_pedi, codmov_nro_pedi (opc), id_lote, cod_lote, vto_lote (opc), marca, multiplicador_vta, cantidad_uni, tipo_unidad, unidad_art_peso (opc).
    Devuelve None si ok, o dict con clave 'error'.
    """
    try:
        codmov_nro_pedi = datos.get("codmov_nro_pedi")
        if codmov_nro_pedi is None and datos.get("nro_pedi") is not None:
            try:
                nro = str(datos.get("nro_pedi")).strip()
                if nro and nro.replace(".", "").replace("-", "").isdigit():
                    codmov_nro_pedi = int(float(nro))
            except (ValueError, TypeError):
                codmov_nro_pedi = None

        with mysql_cursor(base_empresa, dict_cursor=False) as cursor:
            cursor.execute(
                """
                UPDATE cuerpostock_mstock SET
                    IDArt = %s, CodigoArticulo = %s, Descripcion = %s,
                    Cantidad = %s, entrada = %s, salida = %s, ES = %s,
                    CodDeposito = %s, cod_deposito_destino = %s,
                    id_manual = COALESCE(%s, id_manual),
                    nro_pedi = COALESCE(%s, nro_pedi),
                    codmov_nro_pedi = COALESCE(%s, codmov_nro_pedi),
                    id_lote = %s, cod_lote = %s, vto_lote = %s,
                    marca = COALESCE(%s, marca),
                    multiplicador_vta = COALESCE(%s, multiplicador_vta),
                    cantidad_uni = COALESCE(%s, cantidad_uni),
                    tipo_unidad = COALESCE(%s, tipo_unidad),
                    unidad_art_peso = COALESCE(%s, unidad_art_peso)
                WHERE CodUsuario = %s AND COALESCE(visualiza, 'No') = 'No'
                  AND COALESCE(CodigoMovimiento, 1) = 1 AND Orden = %s
                """,
                [
                    datos.get("IDArt"),
                    datos.get("CodigoArticulo") or "",
                    datos.get("Descripcion") or "",
                    datos.get("Cantidad") or 0,
                    datos.get("entrada") or 0,
                    datos.get("salida") or 0,
                    (datos.get("ES") or "E").strip().upper(),
                    datos.get("CodDeposito"),
                    datos.get("cod_deposito_destino"),
                    datos.get("id_manual"),
                    datos.get("nro_pedi"),
                    codmov_nro_pedi,
                    datos.get("id_lote"),
                    datos.get("cod_lote"),
                    datos.get("vto_lote"),
                    datos.get("marca"),
                    datos.get("multiplicador_vta"),
                    datos.get("cantidad_uni"),
                    datos.get("tipo_unidad"),
                    datos.get("unidad_art_peso"),
                    id_usuario,
                    orden,
                ],
            )
        return None
    except Exception as e:
        logger.exception("Error al actualizar renglón temporal")
        return {"error": str(e)}


def limpiar_temporales_usuario(base_empresa: str, id_usuario: int) -> None:
    """Elimina todos los renglones temporales del usuario (y series temp si existen)."""
    try:
        with mysql_cursor(base_empresa, dict_cursor=False) as cursor:
            cursor.execute(
                "DELETE FROM cuerpostock_mstock WHERE CodUsuario = %s AND COALESCE(visualiza, 'No') = 'No'",
                [id_usuario],
            )
            try:
                cursor.execute(
                    "DELETE FROM serie_entrada_temp WHERE id_usuario = %s AND COALESCE(tipo_comprobante, '') = 'Mstock'",
                    [id_usuario],
                )
            except Exception:
                pass
            try:
                cursor.execute(
                    "DELETE FROM serie_salida_temp WHERE id_usuario = %s AND COALESCE(tipo_comprobante, '') = 'Mstock'",
                    [id_usuario],
                )
            except Exception:
                pass
    except Exception as e:
        logger.warning("Error al limpiar temporales usuario %s: %s", id_usuario, e)


def _validar_series_renglones(
    cursor: Any,
    id_usuario: int,
    renglones: List[Dict[str, Any]],
) -> Optional[str]:
    """
    Valida que cada renglón con artículo seriado tenga cantidad de series en temp igual a Cantidad.
    Devuelve mensaje de error o None.
    """
    for idx, reng in enumerate(renglones):
        if (str(reng.get("serie_articulo") or "").strip()) != "Si":
            continue
        orden = reng.get("Orden")
        id_art = reng.get("IDArt")
        try:
            orden = int(orden) if orden is not None else None
            id_art = int(id_art) if id_art is not None else None
        except (TypeError, ValueError):
            return f"Renglón {idx + 1}: datos de serie inválidos."
        if orden is None or id_art is None:
            continue
        cant = Decimal(str(reng.get("Cantidad") or 0))
        es_entrada = (str(reng.get("ES") or "E").strip().upper()) == "E"
        if es_entrada:
            cursor.execute(
                """
                SELECT COUNT(*) FROM serie_entrada_temp
                WHERE id_usuario = %s AND COALESCE(tipo_comprobante, '') = 'Mstock'
                  AND orden = %s AND id_articulo = %s
                """,
                [id_usuario, orden, id_art],
            )
        else:
            cursor.execute(
                """
                SELECT COUNT(*) FROM serie_salida_temp
                WHERE id_usuario = %s AND COALESCE(tipo_comprobante, '') = 'Mstock'
                  AND orden = %s AND id_articulo = %s
                """,
                [id_usuario, orden, id_art],
            )
        row = cursor.fetchone()
        count_series = int(row[0] or 0) if row else 0
        if count_series != int(cant):
            return (
                f"Renglón {idx + 1} (artículo seriado): "
                f"debe haber {int(cant)} número(s) de serie, hay {count_series}."
            )
    return None


def _guardar_series_movimiento(
    cursor: Any,
    id_usuario: int,
    codigo_mov: Decimal,
    nro_comprobante: str,
    fecha: str,
    es_entrada: bool,
    deposito_origen: Any,
) -> Optional[str]:
    """
    Copia series desde temp a serie_entrada/serie_movimiento (paridad VB6 GuardarSerie).
    Usar dentro de la misma transacción que el alta. Devuelve None si ok, mensaje si error.
    """
    try:
        if es_entrada:
            cursor.execute(
                """
                INSERT INTO serie_entrada
                (anulado, codigo_mov_entrada, desc_serie, disponible, fecha, id_articulo, nro_serie, tipo_comprobante, vto_serie, id_deposito)
                SELECT 'No', %s, COALESCE(t.desc_serie, ''), 'Si', %s, t.id_articulo, t.nro_serie, COALESCE(t.tipo_comprobante, 'Mstock'), t.vto_serie, t.id_deposito
                FROM serie_entrada_temp t
                WHERE COALESCE(t.visualiza, 'No') = 'No' AND t.id_usuario = %s AND COALESCE(t.tipo_comprobante, '') = 'Mstock'
                ORDER BY t.id_serie_entrada_temp
                """,
                [codigo_mov, fecha, id_usuario],
            )
            cursor.execute(
                """
                INSERT INTO serie_movimiento
                (anulado, codigo_mov_mstock, desc_serie, fecha, nro_serie, tipo_comprobante, vto_serie, id_serie_entrada, id_articulo, tipo_comp_desc, comprobante, modificado, id_stock, id_deposito, nro_comprobante)
                SELECT 'No', %s, se.desc_serie, %s, se.nro_serie, se.tipo_comprobante, se.vto_serie, se.id_serie_entrada, se.id_articulo, 'MSTOCK Entrada', 'MSTOCK', 'No', s.id_stock, s.CodDeposito, %s
                FROM serie_entrada se
                INNER JOIN stock s ON s.codigoMovimiento = se.codigo_mov_entrada AND s.IDArt = se.id_articulo AND COALESCE(s.anulado, 'No') = 'No'
                WHERE se.codigo_mov_entrada = %s AND COALESCE(se.tipo_comprobante, '') = 'Mstock'
                """,
                [codigo_mov, fecha, nro_comprobante, codigo_mov],
            )
        else:
            cursor.execute(
                """
                INSERT INTO serie_movimiento
                (anulado, codigo_mov_mstock, desc_serie, fecha, id_articulo, nro_serie, tipo_comprobante, vto_serie, id_serie_entrada, tipo_comp_desc, comprobante, modificado, id_stock, id_deposito, nro_comprobante)
                SELECT 'No', %s, st.desc_serie, %s, st.id_articulo, st.nro_serie, st.tipo_comprobante, st.vto_serie, st.id_serie_entrada, 'MSTOCK Salida', 'MSTOCK', 'No', s.id_stock, %s, %s
                FROM serie_salida_temp st
                INNER JOIN stock s ON s.codigoMovimiento = %s AND s.IDArt = st.id_articulo AND COALESCE(s.anulado, 'No') = 'No' AND s.Salida > 0 AND s.Orden = st.orden
                WHERE COALESCE(st.visualiza, 'No') = 'No' AND st.id_usuario = %s AND COALESCE(st.tipo_comprobante, '') = 'Mstock'
                ORDER BY st.id_serie_salida_temp
                """,
                [codigo_mov, fecha, deposito_origen, nro_comprobante, codigo_mov, id_usuario],
            )
            cursor.execute(
                """
                UPDATE serie_entrada se
                INNER JOIN serie_salida_temp st ON st.id_serie_entrada = se.id_serie_entrada
                  AND COALESCE(st.visualiza, 'No') = 'No' AND st.id_usuario = %s AND COALESCE(st.tipo_comprobante, '') = 'Mstock'
                SET se.disponible = 'No'
                """,
                [id_usuario],
            )
        return None
    except Exception as e:
        logger.exception("Error en GuardarSerie")
        return str(e)


def _validar_permisos_alta(
    base_empresa: str,
    id_puesto: Optional[int],
    cabecera: Dict[str, Any],
) -> Optional[str]:
    """Revalida permisos de puesto para el alta. Devuelve mensaje de error o None."""
    permisos = _get_permisos_puesto(base_empresa, id_puesto)
    motivo = cabecera.get("motivo_movimiento")
    id_ref = cabecera.get("id_ref_movstock")
    deposito_origen = cabecera.get("deposito_origen")
    deposito_destino = cabecera.get("deposito_destino")

    if (permisos.get("cambia_deposito") or "").strip() != "Si":
        deposito_usr = permisos.get("deposito_usr") or permisos.get("CodDeposito")
        if deposito_usr is not None:
            try:
                cod = int(deposito_usr)
                if deposito_origen is not None and int(deposito_origen) != cod:
                    return "No tiene permiso para usar este depósito origen."
                if deposito_destino is not None and int(deposito_destino) != cod:
                    return "No tiene permiso para usar este depósito destino."
            except (ValueError, TypeError):
                pass

    acceso_ref = (permisos.get("acceso_ref_movstock") or "").strip()
    if acceso_ref != "Todos" and id_ref is not None:
        id_ref_perm = permisos.get("id_refmovstock")
        if id_ref_perm is not None:
            try:
                if int(id_ref) != int(id_ref_perm):
                    return "No tiene permiso para esta referencia de movimiento."
            except (ValueError, TypeError):
                pass

    motivos_permitidos = get_motivos_permitidos(base_empresa, id_puesto, incluir_pedidos_produccion=True)
    codigos_permitidos = {c for c, _ in motivos_permitidos}
    try:
        motivo_num = int(motivo) if motivo is not None and str(motivo).strip() != "" else None
    except (ValueError, TypeError):
        motivo_num = None
    if motivo_num is not None and codigos_permitidos and motivo_num not in codigos_permitidos:
        return "No tiene permiso para este motivo de movimiento."

    return None


def alta_movimiento(
    base_empresa: str,
    id_usuario: int,
    id_puesto: Optional[int],
    cabecera: Dict[str, Any],
    renglones: List[Dict[str, Any]],
) -> Tuple[bool, Optional[Decimal], Optional[str], Optional[str]]:
    """
    Alta de movimiento en una sola transacción.
    (1) UPDATE codmov, (2) talonarios FOR UPDATE + Nro, (3) INSERT movimiento_stock,
    (4) por cada renglón: INSERT stock, UPDATE/INSERT stock_deposito,
    (5) limpieza temporales.
    Devuelve (ok, codigo_movimiento, nro_comprobante, mensaje_error).
    """
    if not renglones:
        return False, None, None, "Debe haber al menos un renglón."

    err = _validar_permisos_alta(base_empresa, id_puesto, cabecera)
    if err:
        return False, None, None, err

    pool = get_mysql_pool()
    try:
        with pool.get_connection(base_empresa) as conn:
            conn.autocommit(False)
            cursor = conn.cursor()

            try:
                # (1) codmov: obtener y actualizar CodigoMovimiento
                cursor.execute("SELECT CodigoMovimiento FROM codmov WHERE codigo = 1 FOR UPDATE")
                row = cursor.fetchone()
                if not row:
                    conn.rollback()
                    return False, None, None, "No se pudo obtener código de movimiento."
                codigo_mov = Decimal(str(row[0] or 0)) + 1
                cursor.execute("UPDATE codmov SET CodigoMovimiento = %s WHERE codigo = 1", [codigo_mov])

                # (2) talonarios: MSTOCK para id_punto_venta (usar 1 si no se envía)
                id_pv = to_int_or_none(cabecera.get("id_pv") or cabecera.get("id_punto_venta")) or 1
                cursor.execute(
                    "SELECT Orden, Nro FROM talonarios WHERE TipoComprobante = 'MSTOCK' AND id_punto_venta = %s FOR UPDATE",
                    [id_pv],
                )
                talon_row = cursor.fetchone()
                if not talon_row:
                    conn.rollback()
                    return False, None, None, "No existe talonario MSTOCK para el punto de venta."
                orden_talon, nro_actual = talon_row[0], (talon_row[1] or 0)
                nro_nuevo = nro_actual + 1
                cursor.execute("UPDATE talonarios SET Nro = %s WHERE Orden = %s", [nro_nuevo, orden_talon])
                # Formato como AdministraNET: PV de 4 dígitos + guión + Nro de 8 dígitos (ej. 0001-00000288)
                nro_comprobante = f"{id_pv:04d}-{nro_nuevo:08d}"

                # Validar series: artículos seriados deben tener cantidad de series = Cantidad
                err_series = _validar_series_renglones(cursor, id_usuario, renglones)
                if err_series:
                    conn.rollback()
                    return False, None, None, err_series

                # Texto del motivo para movimiento_stock.motivo_movimiento y stock.TipoComp (paridad VB6: Motivo.Text).
                motivo_num = to_int_or_none(cabecera.get("motivo_movimiento")) or 0
                motivo_texto = MOTIVO_CODIGO_A_NOMBRE.get(motivo_num) or str(motivo_num)

                # Normalización de cabecera (tipos AdministraNET: INT, DATE, VARCHAR, DECIMAL).
                deposito_origen = to_int_or_none(cabecera.get("deposito_origen"))
                deposito_destino = to_int_or_none(cabecera.get("deposito_destino")) if motivo_num == 6 else deposito_origen
                if deposito_destino is None:
                    deposito_destino = deposito_origen
                fecha_mov = to_date_or_none(cabecera.get("fecha"))
                if not fecha_mov:
                    from datetime import date
                    fecha_mov = date.today().isoformat()
                id_ref_movstock = to_int_or_none(cabecera.get("id_ref_movstock"))
                id_proyecto = to_int_or_none(cabecera.get("id_proyecto")) or 1
                id_cliente = to_int_or_none(cabecera.get("id_cliente"))
                id_vendedor = to_int_or_none(cabecera.get("id_vendedor"))
                _cant_desarme = to_decimal_or_none(
                    cabecera.get("valor_variable") or cabecera.get("cant_desarme"), "0.000001"
                )
                detalle_mov = (str_or_default(cabecera.get("detalle"), "") or "").strip()
                # Transferencia sin detalle: completar como AdministraNET ("Transferencia de X a Y")
                if motivo_num == 6 and not detalle_mov:
                    detalle_mov = "Transferencia de {} a {}".format(
                        get_nombre_deposito(base_empresa, deposito_origen),
                        get_nombre_deposito(base_empresa, deposito_destino),
                    )

                # tipo_mov (cabecera): motivo 11 = OPT (Pedido producción), 12 = OPP (Parte producción); resto NULL.
                tipo_mov = None
                if motivo_num == 11:
                    tipo_mov = "OPT"
                elif motivo_num == 12:
                    tipo_mov = "OPP"

                # (3) INSERT movimiento_stock (valores normalizados). id_pv e tipo_mov/cant_desarme pueden no existir en todas las bases.
                params_mov = [
                    codigo_mov,
                    nro_comprobante,
                    motivo_texto,
                    fecha_mov,
                    deposito_origen,
                    deposito_destino,
                    detalle_mov,
                    id_usuario,
                    id_ref_movstock,
                    id_proyecto,
                    id_cliente,
                    id_vendedor,
                    _cant_desarme,
                    tipo_mov,
                    id_pv,
                ]
                try:
                    cursor.execute(
                        """
                        INSERT INTO movimiento_stock
                        (codigo_movimiento, nro_comprobante, motivo_movimiento, fecha, deposito_origen, deposito_destino,
                         detalle, id_usuario, tipo_comprobante, anulado, id_ref_movstock, id_proyecto, id_cliente, id_vendedor, cant_desarme, tipo_mov, id_pv)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'MSTOCK', 'No', %s, %s, %s, %s, %s, %s, %s)
                        """,
                        params_mov,
                    )
                except Exception as insert_err:  # noqa: B902
                    err_msg = str(insert_err)
                    if "1054" in err_msg and ("tipo_mov" in err_msg or "id_pv" in err_msg):
                        # Base sin columna tipo_mov, cant_desarme y/o id_pv: INSERT solo con columnas básicas
                        cursor.execute(
                            """
                            INSERT INTO movimiento_stock
                            (codigo_movimiento, nro_comprobante, motivo_movimiento, fecha, deposito_origen, deposito_destino,
                             detalle, id_usuario, tipo_comprobante, anulado, id_ref_movstock, id_proyecto, id_cliente, id_vendedor)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'MSTOCK', 'No', %s, %s, %s, %s)
                            """,
                            params_mov[:12],
                        )
                    else:
                        raise insert_err

                # Factor valor variable (Desarmado): solo aplica a renglones de entrada (insumos)
                if motivo_num == 10 and _cant_desarme is not None and _cant_desarme > 0:
                    factor_desarme = Decimal(str(_cant_desarme)) / Decimal("100")
                else:
                    factor_desarme = None

                def _actualizar_stock_deposito(cursor, id_art, cod_dep, delta: Decimal):
                    """UPDATE o INSERT stock_deposito sumando delta al saldo."""
                    cursor.execute(
                        "SELECT id_stock_deposito, saldo FROM stock_deposito WHERE id_articulo = %s AND id_deposito = %s FOR UPDATE",
                        [id_art, cod_dep],
                    )
                    sd_row = cursor.fetchone()
                    if sd_row:
                        nuevo_saldo = Decimal(str(sd_row[1] or 0)) + delta
                        cursor.execute("UPDATE stock_deposito SET saldo = %s WHERE id_stock_deposito = %s", [nuevo_saldo, sd_row[0]])
                    else:
                        cursor.execute(
                            "INSERT INTO stock_deposito (id_articulo, id_deposito, saldo) VALUES (%s, %s, %s)",
                            [id_art, cod_dep, delta],
                        )

                # (4) Por cada renglón: INSERT stock y actualizar stock_deposito (transfer = dos filas por renglón)
                for idx, reng in enumerate(renglones):
                    id_art = to_int_or_none(reng.get("IDArt"))
                    cantidad = to_decimal_or_none(reng.get("Cantidad"), "0.000001") or Decimal(0)
                    entrada = to_decimal_or_none(reng.get("entrada"), "0.000001") or Decimal(0)
                    salida = to_decimal_or_none(reng.get("salida"), "0.000001") or Decimal(0)
                    cod_dep = to_int_or_none(reng.get("CodDeposito")) or deposito_origen
                    es = (str(reng.get("ES") or "E")).strip().upper()
                    codigo_art = str_or_default(reng.get("CodigoArticulo"), "")
                    descripcion_art = str_or_default(reng.get("Descripcion"), "")

                    cod_viajante = (
                        to_int_or_none(reng.get("CodViajante") or cabecera.get("id_vendedor"))
                        if motivo_num in (6, 7, 8)
                        else None
                    )

                    # Desarmado (motivo 10): aplicar porcentaje solo a entradas (insumos)
                    if factor_desarme is not None and es == "E":
                        entrada = (entrada * factor_desarme).quantize(Decimal("0.000001"))
                        cantidad = (cantidad * factor_desarme).quantize(Decimal("0.000001"))

                    if not id_art and not codigo_art:
                        conn.rollback()
                        return False, None, None, f"Renglón {idx + 1}: artículo obligatorio."

                    if motivo_num == 6:
                        # Transferencia: dos filas por renglón (salida origen + entrada destino), paridad VB6.
                        cantidad_transfer = salida if es == "S" else entrada
                        if cantidad_transfer <= 0:
                            conn.rollback()
                            return False, None, None, f"Renglón {idx + 1}: cantidad de transferencia debe ser mayor a cero."
                        # Validar saldo en origen
                        cursor.execute(
                            "SELECT id_stock_deposito, saldo FROM stock_deposito WHERE id_articulo = %s AND id_deposito = %s FOR UPDATE",
                            [id_art, deposito_origen],
                        )
                        sd_row = cursor.fetchone()
                        saldo_actual = Decimal(str(sd_row[1] or 0)) if sd_row else Decimal(0)
                        if saldo_actual < cantidad_transfer:
                            conn.rollback()
                            return False, None, None, f"Renglón {idx + 1}: saldo insuficiente en origen (disponible: {saldo_actual})."
                        saldo_origen_despues = saldo_actual - cantidad_transfer
                        # 1) Salida en origen
                        cursor.execute(
                            """
                            INSERT INTO stock
                            (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                             id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante)
                            VALUES (%s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s)
                            """,
                            [
                                codigo_mov, id_art, codigo_art, descripcion_art, fecha_mov,
                                cantidad_transfer, saldo_origen_despues, deposito_origen, id_ref_movstock,
                                idx * 2 + 1, id_usuario, motivo_texto, nro_comprobante, cod_viajante,
                            ],
                        )
                        _actualizar_stock_deposito(cursor, id_art, deposito_origen, -cantidad_transfer)
                        # Lote salida en origen
                        id_lote_reng = to_int_or_none(reng.get("id_lote"))
                        if id_lote_reng:
                            cursor.execute(
                                "SELECT id_lote_stock, stock_lote FROM lote_stock WHERE id_lote = %s AND id_deposito = %s FOR UPDATE",
                                [id_lote_reng, deposito_origen],
                            )
                            ls_row = cursor.fetchone()
                            if not ls_row:
                                conn.rollback()
                                return False, None, None, f"Renglón {idx + 1}: lote sin stock en el depósito origen."
                            stock_actual = Decimal(str(ls_row[1] or 0))
                            if stock_actual < cantidad_transfer:
                                conn.rollback()
                                return False, None, None, f"Renglón {idx + 1}: stock del lote insuficiente en origen (disponible: {stock_actual})."
                            cursor.execute("UPDATE lote_stock SET stock_lote = %s WHERE id_lote_stock = %s", [stock_actual - cantidad_transfer, ls_row[0]])
                            cursor.execute("UPDATE lote SET stock_total_lote = COALESCE(stock_total_lote, 0) - %s WHERE id_lote = %s", [cantidad_transfer, id_lote_reng])
                        # Saldo en destino después de la entrada (para el informe)
                        cursor.execute(
                            "SELECT saldo FROM stock_deposito WHERE id_articulo = %s AND id_deposito = %s",
                            [id_art, deposito_destino],
                        )
                        sd_dest = cursor.fetchone()
                        saldo_dest_actual = Decimal(str(sd_dest[0] or 0)) if sd_dest else Decimal(0)
                        saldo_destino_despues = saldo_dest_actual + cantidad_transfer
                        # 2) Entrada en destino
                        cursor.execute(
                            """
                            INSERT INTO stock
                            (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                             id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante)
                            VALUES (%s, %s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s)
                            """,
                            [
                                codigo_mov, id_art, codigo_art, descripcion_art, fecha_mov,
                                cantidad_transfer, saldo_destino_despues, deposito_destino, id_ref_movstock,
                                idx * 2 + 2, id_usuario, motivo_texto, nro_comprobante, cod_viajante,
                            ],
                        )
                        _actualizar_stock_deposito(cursor, id_art, deposito_destino, cantidad_transfer)
                        # Lote entrada en destino (opcional: crear/actualizar si viene cod_lote o id_lote)
                        id_lote_reng = to_int_or_none(reng.get("id_lote"))
                        cod_lote_reng = (str_or_default(reng.get("cod_lote"), "").strip()) or None
                        vto_lote_reng = reng.get("vto_lote")
                        if id_lote_reng or cod_lote_reng:
                            if id_lote_reng:
                                cursor.execute("SELECT id_lote FROM lote WHERE id_lote = %s FOR UPDATE", [id_lote_reng])
                                lote_row = cursor.fetchone()
                            else:
                                lote_row = None
                            if not lote_row and cod_lote_reng:
                                cursor.execute(
                                    "SELECT id_lote FROM lote WHERE cod_lote = %s AND id_articulo = %s FOR UPDATE",
                                    [cod_lote_reng, id_art],
                                )
                                lote_row = cursor.fetchone()
                            if lote_row:
                                id_lote_use = lote_row[0]
                                cursor.execute(
                                    "UPDATE lote SET stock_total_lote = COALESCE(stock_total_lote, 0) + %s WHERE id_lote = %s",
                                    [cantidad_transfer, id_lote_use],
                                )
                                cursor.execute(
                                    "SELECT id_lote_stock, stock_lote FROM lote_stock WHERE id_lote = %s AND id_deposito = %s FOR UPDATE",
                                    [id_lote_use, deposito_destino],
                                )
                                ls_row = cursor.fetchone()
                                if ls_row:
                                    nuevo_stock = Decimal(str(ls_row[1] or 0)) + cantidad_transfer
                                    cursor.execute("UPDATE lote_stock SET stock_lote = %s WHERE id_lote_stock = %s", [nuevo_stock, ls_row[0]])
                                else:
                                    cursor.execute(
                                        "INSERT INTO lote_stock (id_lote, id_deposito, stock_lote) VALUES (%s, %s, %s)",
                                        [id_lote_use, deposito_destino, cantidad_transfer],
                                    )
                            elif cod_lote_reng:
                                fecha_vto = to_date_or_none(vto_lote_reng)
                                cursor.execute(
                                    """
                                    INSERT INTO lote (cod_lote, fecha_vto_lote, id_articulo, anulado, stock_total_lote)
                                    VALUES (%s, %s, %s, 'No', %s)
                                    """,
                                    [cod_lote_reng, fecha_vto, id_art, cantidad_transfer],
                                )
                                id_lote_nuevo = cursor.lastrowid
                                cursor.execute(
                                    "INSERT INTO lote_stock (id_lote, id_deposito, stock_lote) VALUES (%s, %s, %s)",
                                    [id_lote_nuevo, deposito_destino, cantidad_transfer],
                                )
                            elif id_lote_reng:
                                conn.rollback()
                                return False, None, None, f"Renglón {idx + 1}: lote no encontrado."
                        continue

                    # No transferencia: una fila por renglón (leer saldo actual para INSERT y validación)
                    cursor.execute(
                        "SELECT id_stock_deposito, saldo FROM stock_deposito WHERE id_articulo = %s AND id_deposito = %s FOR UPDATE",
                        [id_art, cod_dep],
                    )
                    sd_row = cursor.fetchone()
                    saldo_actual = Decimal(str(sd_row[1] or 0)) if sd_row else Decimal(0)
                    if es == "S" or salida > 0:
                        if saldo_actual < salida:
                            conn.rollback()
                            return False, None, None, f"Renglón {idx + 1}: saldo insuficiente (disponible: {saldo_actual})."
                    saldo_despues = saldo_actual + (entrada - salida)

                    cursor.execute(
                        """
                        INSERT INTO stock
                        (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                         id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s)
                        """,
                        [
                            codigo_mov, id_art, codigo_art, descripcion_art, fecha_mov,
                            entrada, salida, saldo_despues, cod_dep, id_ref_movstock,
                            idx + 1, id_usuario, motivo_texto, nro_comprobante, cod_viajante,
                        ],
                    )
                    _actualizar_stock_deposito(cursor, id_art, cod_dep, entrada - salida)

                    id_lote_reng = to_int_or_none(reng.get("id_lote"))
                    cod_lote_reng = (str_or_default(reng.get("cod_lote"), "").strip()) or None
                    vto_lote_reng = reng.get("vto_lote")
                    if es == "S" and id_lote_reng:
                        cursor.execute(
                            "SELECT id_lote_stock, stock_lote FROM lote_stock WHERE id_lote = %s AND id_deposito = %s FOR UPDATE",
                            [id_lote_reng, cod_dep],
                        )
                        ls_row = cursor.fetchone()
                        if not ls_row:
                            conn.rollback()
                            return False, None, None, f"Renglón {idx + 1}: lote sin stock en el depósito."
                        stock_actual = Decimal(str(ls_row[1] or 0))
                        if stock_actual < salida:
                            conn.rollback()
                            return False, None, None, f"Renglón {idx + 1}: stock del lote insuficiente (disponible: {stock_actual})."
                        nuevo_stock_lote = stock_actual - salida
                        cursor.execute("UPDATE lote_stock SET stock_lote = %s WHERE id_lote_stock = %s", [nuevo_stock_lote, ls_row[0]])
                        cursor.execute(
                            "UPDATE lote SET stock_total_lote = COALESCE(stock_total_lote, 0) - %s WHERE id_lote = %s",
                            [salida, id_lote_reng],
                        )
                    elif es == "E" and (id_lote_reng or cod_lote_reng):
                        if id_lote_reng:
                            cursor.execute("SELECT id_lote FROM lote WHERE id_lote = %s FOR UPDATE", [id_lote_reng])
                            lote_row = cursor.fetchone()
                        else:
                            lote_row = None
                        if not lote_row and cod_lote_reng:
                            cursor.execute(
                                "SELECT id_lote FROM lote WHERE cod_lote = %s AND id_articulo = %s FOR UPDATE",
                                [cod_lote_reng, id_art],
                            )
                            lote_row = cursor.fetchone()
                        if lote_row:
                            id_lote_use = lote_row[0]
                            cursor.execute(
                                "UPDATE lote SET stock_total_lote = COALESCE(stock_total_lote, 0) + %s WHERE id_lote = %s",
                                [entrada, id_lote_use],
                            )
                            cursor.execute(
                                "SELECT id_lote_stock, stock_lote FROM lote_stock WHERE id_lote = %s AND id_deposito = %s FOR UPDATE",
                                [id_lote_use, cod_dep],
                            )
                            ls_row = cursor.fetchone()
                            if ls_row:
                                nuevo_stock = Decimal(str(ls_row[1] or 0)) + entrada
                                cursor.execute("UPDATE lote_stock SET stock_lote = %s WHERE id_lote_stock = %s", [nuevo_stock, ls_row[0]])
                            else:
                                cursor.execute(
                                    "INSERT INTO lote_stock (id_lote, id_deposito, stock_lote) VALUES (%s, %s, %s)",
                                    [id_lote_use, cod_dep, entrada],
                                )
                        elif cod_lote_reng:
                            fecha_vto = to_date_or_none(vto_lote_reng)
                            cursor.execute(
                                """
                                INSERT INTO lote (cod_lote, fecha_vto_lote, id_articulo, anulado, stock_total_lote)
                                VALUES (%s, %s, %s, 'No', %s)
                                """,
                                [cod_lote_reng, fecha_vto, id_art, entrada],
                            )
                            id_lote_nuevo = cursor.lastrowid
                            cursor.execute(
                                "INSERT INTO lote_stock (id_lote, id_deposito, stock_lote) VALUES (%s, %s, %s)",
                                [id_lote_nuevo, cod_dep, entrada],
                            )
                        elif id_lote_reng:
                            conn.rollback()
                            return False, None, None, f"Renglón {idx + 1}: lote no encontrado."

                # (4a) movstock_pedi: una fila por renglón que tenga pedido (codmov_nro_pedi), paridad VB6
                codigo_mov_int = to_int_or_none(codigo_mov) or int(codigo_mov)
                for reng in renglones:
                    codmov_pedi = to_int_or_none(reng.get("codmov_nro_pedi"))
                    if codmov_pedi is None and reng.get("nro_pedi") is not None:
                        nro = str(reng.get("nro_pedi")).strip()
                        if nro and nro.replace(".", "").replace("-", "").isdigit():
                            codmov_pedi = to_int_or_none(float(nro))
                    if codmov_pedi is not None:
                        cursor.execute(
                            """
                            INSERT INTO movstock_pedi (codmov_movstock, codmov_pedi, anulado)
                            VALUES (%s, %s, 'No')
                            """,
                            [codigo_mov_int, codmov_pedi],
                        )

                # (4b) Guardar series (temp → serie_entrada / serie_movimiento) si hay artículos seriados
                hay_seriados = any(
                    (str(r.get("serie_articulo") or "").strip() == "Si" for r in renglones)
                )
                if hay_seriados:
                    es_entrada = (str(renglones[0].get("ES") or "E").strip().upper()) == "E"
                    err_guardar = _guardar_series_movimiento(
                        cursor,
                        id_usuario,
                        codigo_mov,
                        nro_comprobante,
                        fecha_mov,
                        es_entrada,
                        deposito_origen,
                    )
                    if err_guardar:
                        conn.rollback()
                        return False, None, None, f"Error al grabar series: {err_guardar}"

                # (5) Limpiar temporales del usuario (cuerpo y series)
                cursor.execute(
                    "DELETE FROM cuerpostock_mstock WHERE CodUsuario = %s AND COALESCE(visualiza, 'No') = 'No'",
                    [id_usuario],
                )
                cursor.execute(
                    "DELETE FROM serie_entrada_temp WHERE id_usuario = %s AND COALESCE(tipo_comprobante, '') = 'Mstock'",
                    [id_usuario],
                )
                cursor.execute(
                    "DELETE FROM serie_salida_temp WHERE id_usuario = %s AND COALESCE(tipo_comprobante, '') = 'Mstock'",
                    [id_usuario],
                )

                conn.commit()
                return True, codigo_mov, nro_comprobante, None

            except Exception as e:
                conn.rollback()
                logger.exception("Error en alta_movimiento")
                return False, None, None, str(e)

    except Exception as e:
        logger.exception("Error de conexión en alta_movimiento")
        return False, None, None, str(e)


def listar_movimientos(
    base_empresa: str,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    id_deposito: Optional[int] = None,
    motivo: Optional[str] = None,
    nro_comprobante: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """Listado de movimientos de stock (solo lectura) con filtros."""
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            sql = """
                SELECT m.codigo_movimiento, m.nro_comprobante, m.motivo_movimiento, m.fecha,
                       m.deposito_origen, m.deposito_destino, m.detalle, m.id_usuario, m.id_ref_movstock,
                       TRIM(CONCAT(COALESCE(u.nombre_usuario, ''), ' ', COALESCE(u.apellido_usuario, ''))) AS nombre_usuario
                FROM movimiento_stock m
                LEFT JOIN usuarios u ON u.id_usuario = m.id_usuario
                WHERE COALESCE(m.anulado, 'No') = 'No'
            """
            params = []
            if fecha_desde:
                sql += " AND m.fecha >= %s"
                params.append(fecha_desde)
            if fecha_hasta:
                sql += " AND m.fecha <= %s"
                params.append(fecha_hasta)
            if id_deposito is not None:
                sql += " AND (m.deposito_origen = %s OR m.deposito_destino = %s)"
                params.extend([id_deposito, id_deposito])
            if motivo:
                sql += " AND m.motivo_movimiento = %s"
                params.append(motivo)
            if nro_comprobante:
                sql += " AND m.nro_comprobante LIKE %s"
                params.append(f"%{nro_comprobante}%")
            sql += " ORDER BY m.fecha DESC, m.codigo_movimiento DESC LIMIT %s"
            params.append(limit)
            cursor.execute(sql, params)
            rows = cursor.fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.warning("Error al listar movimientos: %s", e)
        return []


def obtener_movimiento(base_empresa: str, codigo_movimiento: int) -> Optional[Dict[str, Any]]:
    """Cabecera de un movimiento por codigo_movimiento."""
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            cursor.execute(
                "SELECT * FROM movimiento_stock WHERE codigo_movimiento = %s",
                [codigo_movimiento],
            )
            row = cursor.fetchone()
        return dict(row) if row else None
    except Exception as e:
        logger.warning("Error al obtener movimiento: %s", e)
        return None


def obtener_renglones_movimiento(base_empresa: str, codigo_movimiento: int) -> List[Dict[str, Any]]:
    """Renglones (tabla stock) de un movimiento. Incluye CodDeposito, saldo y nombre_deposito para la vista detalle."""
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            cursor.execute(
                "SELECT IDArt, CodigoArticulo, Descripcion, Entrada, Salida, COALESCE(saldo, 0) AS saldo, CodDeposito FROM stock WHERE CodigoMovimiento = %s ORDER BY Orden",
                [codigo_movimiento],
            )
            rows = cursor.fetchall()
        renglones = [dict(r) for r in rows]
        if not renglones:
            return renglones
        codigos_dep = list({to_int_or_none(r.get("CodDeposito")) for r in renglones if to_int_or_none(r.get("CodDeposito")) is not None})
        nombres = get_nombres_depositos(base_empresa, codigos_dep)
        for r in renglones:
            r["nombre_deposito"] = nombres.get(to_int_or_none(r.get("CodDeposito")), "—")
        return renglones
    except Exception as e:
        logger.warning("Error al obtener renglones: %s", e)
        return []
