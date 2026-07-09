"""
Capa de lectura de permisos Synap (tablas ``synap_*``) y lecturas legacy asociadas.

Este módulo aísla las consultas de permisos por puesto para que
``core.services.administranet_permisos_usuario.get_permisos_totales_administranet``
actúe como fachada que elige la fuente según ``settings.SYNAP_PERMISOS_SOURCE``.

Funciones:
- ``get_permisos_desde_synap_store``: fuente propia Synap (synap_puesto_rol → synap_rol_permiso → synap_permiso).
- ``puesto_tiene_mapeo_synap``: indica si el puesto tiene alguna fila en synap_puesto_rol (para fallback).
- ``get_permisos_legacy_synap``: fuente legacy actual (permiso_sistema + permiso_sistema_puesto).
- ``get_permisos_complementarios_legacy``: tabla ``permisos`` (Clavemenu VB6) mapeada a key_permiso.

Ninguna de estas funciones escribe en tablas VB6.
"""
import logging
from typing import Dict, List, Optional, Set

from core.constantes_permisos import MAPEO_MENU_A_PERMISO
from core.mysql_pool import get_connection, mysql_cursor

logger = logging.getLogger(__name__)


def get_permisos_desde_synap_store(
    base_empresa: str,
    id_puesto: Optional[int],
) -> Set[str]:
    """
    Devuelve el set de ``key_permiso`` del puesto según las tablas ``synap_*``.

    Recorre synap_puesto_rol → synap_rol (activo) → synap_rol_permiso → synap_permiso (activo).
    Devuelve set vacío si no hay datos o si las tablas aún no existen.
    """
    permisos: Set[str] = set()
    if not (base_empresa and id_puesto):
        return permisos
    try:
        with mysql_cursor(base_empresa, dict_cursor=False) as cursor:
            cursor.execute(
                """
                SELECT DISTINCT p.key_permiso
                FROM synap_puesto_rol pr
                INNER JOIN synap_rol r
                    ON r.id_rol = pr.id_rol AND r.activo = 1
                INNER JOIN synap_rol_permiso rp
                    ON rp.id_rol = r.id_rol
                INNER JOIN synap_permiso p
                    ON p.id_permiso = rp.id_permiso AND p.activo = 1
                WHERE pr.idpuesto = %s
                """,
                [id_puesto],
            )
            for row in cursor.fetchall():
                key_permiso = row[0] if row else None
                if key_permiso:
                    permisos.add(key_permiso)
    except Exception as e:
        logger.warning(
            "Error al leer permisos Synap (synap_*) para puesto %s en %s: %s",
            id_puesto, base_empresa, e,
        )
    return permisos


def puesto_tiene_mapeo_synap(base_empresa: str, id_puesto: Optional[int]) -> bool:
    """Indica si el puesto tiene al menos una fila en ``synap_puesto_rol``."""
    if not (base_empresa and id_puesto):
        return False
    try:
        with mysql_cursor(base_empresa, dict_cursor=False) as cursor:
            cursor.execute(
                "SELECT 1 FROM synap_puesto_rol WHERE idpuesto = %s LIMIT 1",
                [id_puesto],
            )
            return cursor.fetchone() is not None
    except Exception as e:
        logger.debug(
            "No se pudo verificar mapeo Synap para puesto %s en %s (tabla puede no existir): %s",
            id_puesto, base_empresa, e,
        )
        return False


def get_permisos_legacy_synap(
    base_empresa: str,
    id_puesto: Optional[int],
) -> Set[str]:
    """
    Fuente legacy actual: ``permiso_sistema`` + ``permiso_sistema_puesto``.

    Toma el valor más reciente por ``id_permiso_sistema`` (MAX id) con ``valor_permiso='Si'``.
    """
    permisos: Set[str] = set()
    if not (base_empresa and id_puesto):
        return permisos
    try:
        with mysql_cursor(base_empresa, dict_cursor=False) as cursor:
            cursor.execute(
                """
                SELECT ps.key_permiso, psp.valor_permiso
                FROM permiso_sistema ps
                INNER JOIN (
                    SELECT psp1.id_permiso_sistema, psp1.valor_permiso
                    FROM permiso_sistema_puesto psp1
                    INNER JOIN (
                        SELECT id_permiso_sistema, MAX(id_permiso_sistema_puesto) AS max_id
                        FROM permiso_sistema_puesto
                        WHERE id_puesto = %s
                        GROUP BY id_permiso_sistema
                    ) psp2 ON psp1.id_permiso_sistema = psp2.id_permiso_sistema
                           AND psp1.id_permiso_sistema_puesto = psp2.max_id
                    WHERE psp1.id_puesto = %s
                ) psp ON ps.id_permiso_sistema = psp.id_permiso_sistema
                WHERE psp.valor_permiso = 'Si'
                """,
                [id_puesto, id_puesto],
            )
            for row in cursor.fetchall():
                key_permiso = row[0] if row else None
                if key_permiso:
                    permisos.add(key_permiso)
    except Exception as e:
        logger.warning(
            "Error al obtener permisos legacy (permiso_sistema) para puesto %s: %s",
            id_puesto, e,
        )
    return permisos


def get_permisos_complementarios_legacy(
    base_empresa: str,
    id_puesto: Optional[int],
) -> Set[str]:
    """
    Permisos derivados de la tabla ``permisos`` (Clavemenu VB6) vía ``MAPEO_MENU_A_PERMISO``.

    Se suman SIEMPRE (independiente de la fuente): es lectura genuinamente legacy.
    """
    permisos: Set[str] = set()
    if not (base_empresa and id_puesto):
        return permisos
    try:
        with mysql_cursor(base_empresa, dict_cursor=False) as cursor:
            cursor.execute(
                """
                SELECT Clavemenu FROM permisos
                WHERE IDpuesto = %s AND (Permiso = '1' OR Permiso = 'Si')
                """,
                [str(id_puesto)],
            )
            for row in cursor.fetchall():
                clavemenu = row[0] if row else None
                if clavemenu and clavemenu in MAPEO_MENU_A_PERMISO:
                    permisos.add(MAPEO_MENU_A_PERMISO[clavemenu])
    except Exception as e:
        logger.debug(
            "No se pudo leer tabla permisos (Clavemenu) para puesto %s (puede no existir): %s",
            id_puesto, e,
        )
    return permisos


class SynapPermisosService:
    """
    Servicio de escritura/lectura de permisos Synap por puesto para la UI
    ``/core/permisos-puesto/`` (pestaña Synap).

    Modelo de rol dedicado: cada puesto tiene un rol propio (``es_sistema=1``) al que
    se le asignan/quitan permisos. NUNCA escribe en tablas VB6.
    """

    def obtener_o_crear_rol_puesto(
        self, cursor, id_puesto: int, nombre_puesto: str
    ) -> int:
        """Devuelve el id_rol dedicado del puesto; lo crea y mapea si no existe."""
        cursor.execute(
            """
            SELECT r.id_rol FROM synap_puesto_rol pr
            INNER JOIN synap_rol r ON r.id_rol = pr.id_rol AND r.es_sistema = 1
            WHERE pr.idpuesto = %s LIMIT 1
            """,
            [id_puesto],
        )
        fila = cursor.fetchone()
        if fila:
            return fila[0]

        nombre_rol = f"Synap · {nombre_puesto or 'Sin nombre'} (#{id_puesto})"[:128]
        cursor.execute(
            """
            INSERT INTO synap_rol (nombre, descripcion, es_sistema, activo)
            VALUES (%s, %s, 1, 1)
            ON DUPLICATE KEY UPDATE id_rol = LAST_INSERT_ID(id_rol)
            """,
            [nombre_rol, f"Rol dedicado del puesto {id_puesto}"],
        )
        id_rol = cursor.lastrowid
        cursor.execute(
            "INSERT IGNORE INTO synap_puesto_rol (idpuesto, id_rol) VALUES (%s, %s)",
            [id_puesto, id_rol],
        )
        return id_rol

    def obtener_resumen_rol_puesto(self, base_empresa: str, id_puesto: Optional[int]) -> Dict:
        """
        Devuelve ``{existe, nombre, total_activos}`` del rol dedicado del puesto.

        ``total_activos`` cuenta los permisos distintos efectivamente asignados al puesto
        (a través de sus roles activos), consistente con la lectura de runtime.
        """
        resumen: Dict = {"existe": False, "nombre": None, "total_activos": 0}
        if not (base_empresa and id_puesto):
            return resumen
        try:
            with mysql_cursor(base_empresa, dict_cursor=False) as cursor:
                cursor.execute(
                    """
                    SELECT r.nombre FROM synap_puesto_rol pr
                    INNER JOIN synap_rol r ON r.id_rol = pr.id_rol AND r.es_sistema = 1
                    WHERE pr.idpuesto = %s LIMIT 1
                    """,
                    [id_puesto],
                )
                row = cursor.fetchone()
                if row:
                    resumen["existe"] = True
                    resumen["nombre"] = row[0]

                cursor.execute(
                    """
                    SELECT COUNT(DISTINCT p.id_permiso)
                    FROM synap_puesto_rol pr
                    INNER JOIN synap_rol r ON r.id_rol = pr.id_rol AND r.activo = 1
                    INNER JOIN synap_rol_permiso rp ON rp.id_rol = r.id_rol
                    INNER JOIN synap_permiso p ON p.id_permiso = rp.id_permiso AND p.activo = 1
                    WHERE pr.idpuesto = %s
                    """,
                    [id_puesto],
                )
                resumen["total_activos"] = cursor.fetchone()[0] or 0
        except Exception as e:
            logger.debug(
                "No se pudo obtener resumen de rol Synap para puesto %s en %s: %s",
                id_puesto, base_empresa, e,
            )
        return resumen

    def listar_permisos(
        self,
        base_empresa: str,
        busqueda: Optional[str] = None,
        grupo: Optional[str] = None,
        id_puesto: Optional[int] = None,
    ) -> List[Dict]:
        """
        Lista el catálogo ``synap_permiso`` (activos) con el estado ('Si'/'No') para el puesto.

        Devuelve dicts compatibles con la plantilla: ``id_permiso``, ``key_permiso``,
        ``nombre_permiso``, ``detalle_permiso``, ``grupo_permiso``, ``default_permiso``,
        ``valor_guardado``.
        """
        permisos: List[Dict] = []
        try:
            with mysql_cursor(base_empresa, dict_cursor=False) as cursor:
                query = """
                    SELECT p.id_permiso, p.key_permiso, p.nombre, p.descripcion, p.modulo,
                        CASE WHEN EXISTS (
                            SELECT 1 FROM synap_puesto_rol pr
                            INNER JOIN synap_rol r ON r.id_rol = pr.id_rol AND r.activo = 1
                            INNER JOIN synap_rol_permiso rp ON rp.id_rol = r.id_rol
                            WHERE pr.idpuesto = %s AND rp.id_permiso = p.id_permiso
                        ) THEN 'Si' ELSE 'No' END AS valor_guardado
                    FROM synap_permiso p
                    WHERE p.activo = 1
                """
                params: list = [id_puesto]
                if busqueda:
                    query += " AND (p.nombre LIKE %s OR p.key_permiso LIKE %s OR p.descripcion LIKE %s)"
                    like = f"%{busqueda}%"
                    params.extend([like, like, like])
                if grupo:
                    query += " AND p.modulo = %s"
                    params.append(grupo)
                query += " ORDER BY p.modulo, p.nombre"
                cursor.execute(query, params)
                for row in cursor.fetchall():
                    permisos.append(
                        {
                            "id_permiso": row[0],
                            "key_permiso": row[1],
                            "nombre_permiso": row[2],
                            "detalle_permiso": row[3],
                            "grupo_permiso": row[4] or "Sin módulo",
                            "default_permiso": "No",
                            "valor_guardado": row[5],
                        }
                    )
        except Exception as e:
            logger.warning("Error al listar permisos Synap para puesto %s: %s", id_puesto, e)
        return permisos

    def obtener_grupos(self, base_empresa: str) -> List[str]:
        """Módulos distintos del catálogo Synap (para el filtro de la UI)."""
        try:
            with mysql_cursor(base_empresa, dict_cursor=False) as cursor:
                cursor.execute(
                    "SELECT DISTINCT modulo FROM synap_permiso WHERE modulo IS NOT NULL ORDER BY modulo"
                )
                return [row[0] for row in cursor.fetchall() if row[0]]
        except Exception as e:
            logger.warning("Error al obtener módulos Synap en %s: %s", base_empresa, e)
            return []

    def actualizar_valor_permiso(
        self,
        base_empresa: str,
        id_permiso: int,
        valor: str,
        id_puesto: int,
        nombre_puesto: str = "",
    ) -> bool:
        """Asigna ('Si') o quita ('No') un permiso del rol dedicado del puesto."""
        try:
            with get_connection(base_empresa) as conn:
                cursor = conn.cursor()
                id_rol = self.obtener_o_crear_rol_puesto(cursor, id_puesto, nombre_puesto)
                if valor == "Si":
                    cursor.execute(
                        "INSERT IGNORE INTO synap_rol_permiso (id_rol, id_permiso) VALUES (%s, %s)",
                        [id_rol, id_permiso],
                    )
                else:
                    cursor.execute(
                        "DELETE FROM synap_rol_permiso WHERE id_rol = %s AND id_permiso = %s",
                        [id_rol, id_permiso],
                    )
                conn.commit()
                cursor.close()
                return True
        except Exception as e:
            logger.error(
                "Error al actualizar permiso Synap %s (puesto %s) en %s: %s",
                id_permiso, id_puesto, base_empresa, e,
            )
            return False

    def establecer_modulo_para_puesto(
        self,
        base_empresa: str,
        id_puesto: int,
        prefijo_modulo: str,
        activar: bool,
        nombre_puesto: str = "",
    ) -> int:
        """
        Activa/desactiva todos los permisos cuyo ``key_permiso`` coincide con el prefijo
        (``prefijo.*``, ``prefijo.x`` y, para logística, ``prefijo_x``). Devuelve nº afectados.
        """
        prefijo = (prefijo_modulo or "").strip().lower()
        if not prefijo or not id_puesto:
            return 0
        afectados = 0
        try:
            with get_connection(base_empresa) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id_permiso, key_permiso FROM synap_permiso WHERE activo = 1")
                objetivo = []
                for id_permiso, key_permiso in cursor.fetchall():
                    key = (key_permiso or "").strip().lower()
                    if not key:
                        continue
                    if key == f"{prefijo}.*" or key.startswith(f"{prefijo}."):
                        objetivo.append(id_permiso)
                    elif prefijo == "logistica" and key.startswith("logistica_"):
                        objetivo.append(id_permiso)
                if not objetivo:
                    cursor.close()
                    return 0
                id_rol = self.obtener_o_crear_rol_puesto(cursor, id_puesto, nombre_puesto)
                for id_permiso in objetivo:
                    if activar:
                        cursor.execute(
                            "INSERT IGNORE INTO synap_rol_permiso (id_rol, id_permiso) VALUES (%s, %s)",
                            [id_rol, id_permiso],
                        )
                    else:
                        cursor.execute(
                            "DELETE FROM synap_rol_permiso WHERE id_rol = %s AND id_permiso = %s",
                            [id_rol, id_permiso],
                        )
                    afectados += cursor.rowcount
                conn.commit()
                cursor.close()
        except Exception as e:
            logger.error(
                "Error al establecer módulo Synap '%s' (puesto %s) en %s: %s",
                prefijo, id_puesto, base_empresa, e,
            )
        return afectados


def backfill_synap_permisos_desde_legacy(
    base_empresa: str,
    dry_run: bool = False,
    force: bool = False,
) -> Dict:
    """
    Migra las asignaciones de permisos Synap desde las tablas legacy
    (``permiso_sistema_puesto``) hacia ``synap_*`` (rol dedicado por puesto). Idempotente.

    Reutilizable desde el comando ``backfill_synap_permisos_from_legacy`` y desde la UI
    (``/core/permisos-puesto/`` para la empresa logueada).

    Args:
        base_empresa: base MySQL de la empresa.
        dry_run: si True, solo calcula (no escribe).
        force: si True, re-sincroniza (reemplaza los permisos del rol de cada puesto).

    Returns:
        dict con ``success``, ``dry_run``, ``force``, ``total_puestos``, ``total_roles``,
        ``total_asignaciones``, ``detalles`` (list[str]) y ``message``.
    """
    base_empresa = (base_empresa or "").strip()
    resultado: Dict = {
        "success": False,
        "dry_run": dry_run,
        "force": force,
        "total_revisados": 0,
        "total_puestos": 0,
        "total_roles": 0,
        "total_asignaciones": 0,
        "detalles": [],
        "message": "",
    }
    if not base_empresa:
        resultado["message"] = "No se indicó la empresa."
        return resultado

    try:
        # Imports diferidos para evitar ciclos con catalog.py.
        from core.services.legacy_mysql_schema.catalog import run_synap_permisos_tables_mysql

        svc = SynapPermisosService()
        with get_connection(base_empresa) as conn:
            # Asegurar esquema + catálogo (idempotente) antes del backfill.
            run_synap_permisos_tables_mysql(conn)

            cur = conn.cursor()
            cur.execute("SELECT id_permiso, key_permiso FROM synap_permiso")
            catalogo = {row[1]: row[0] for row in cur.fetchall()}

            cur.execute(
                """
                SELECT DISTINCT psp.id_puesto, COALESCE(p.puesto, '')
                FROM permiso_sistema_puesto psp
                LEFT JOIN puestos p ON p.idpuesto = psp.id_puesto
                WHERE psp.id_puesto IS NOT NULL
                """
            )
            puestos = [(row[0], row[1] or "") for row in cur.fetchall()]

            for id_puesto, nombre_puesto in puestos:
                resultado["total_revisados"] += 1
                nombre_disp = nombre_puesto or "Sin nombre"
                legacy_keys = get_permisos_legacy_synap(base_empresa, id_puesto)
                relevantes = {k: catalogo[k] for k in legacy_keys if k in catalogo}
                if not relevantes:
                    resultado["detalles"].append(
                        f"Puesto {id_puesto} «{nombre_disp}»: sin permisos Synap para migrar"
                    )
                    continue

                resultado["total_puestos"] += 1
                resultado["detalles"].append(
                    f"Puesto {id_puesto} «{nombre_disp}»: {len(relevantes)} permiso(s)"
                )

                if dry_run:
                    resultado["total_asignaciones"] += len(relevantes)
                    continue

                # ¿Ya existe rol dedicado? (para contar roles nuevos)
                cur.execute(
                    """
                    SELECT r.id_rol FROM synap_puesto_rol pr
                    INNER JOIN synap_rol r ON r.id_rol = pr.id_rol AND r.es_sistema = 1
                    WHERE pr.idpuesto = %s LIMIT 1
                    """,
                    [id_puesto],
                )
                existia = cur.fetchone() is not None
                id_rol = svc.obtener_o_crear_rol_puesto(cur, id_puesto, nombre_puesto)
                if not existia:
                    resultado["total_roles"] += 1

                if force:
                    cur.execute("DELETE FROM synap_rol_permiso WHERE id_rol = %s", [id_rol])

                for id_permiso in relevantes.values():
                    cur.execute(
                        "INSERT IGNORE INTO synap_rol_permiso (id_rol, id_permiso) VALUES (%s, %s)",
                        [id_rol, id_permiso],
                    )
                    resultado["total_asignaciones"] += cur.rowcount

            if not dry_run:
                conn.commit()
            cur.close()

        resultado["success"] = True
        resultado["message"] = (
            f"Backfill {'(simulación) ' if dry_run else ''}en {base_empresa}: "
            f"{resultado['total_revisados']} puesto(s) revisado(s), "
            f"{resultado['total_puestos']} con permisos Synap, "
            f"{resultado['total_roles']} rol(es) creado(s), "
            f"{resultado['total_asignaciones']} asignación(es)."
        )
    except Exception as e:
        logger.exception("Error en backfill Synap en %s: %s", base_empresa, e)
        resultado["message"] = f"Error en backfill Synap en {base_empresa}: {e}"
    return resultado
