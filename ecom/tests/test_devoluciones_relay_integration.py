"""
Integración de devoluciones/filtros con MySQL legacy.
Solo lectura, sin escrituras.
"""

import pytest

from ecom.services.devoluciones_relay import (
    listar_devoluciones_relay,
    sugerencias_nro_devoluciones_relay,
)
from ecom.services.filtros_estadisticas_relay import listado_filtros_estadisticas


def _base_empresa(conn) -> str:
    # Alias mysql del proyecto (base legacy activa en tests de integración).
    return str(conn.settings_dict.get("NAME") or "").strip()


def _existe_tabla(conn, tabla: str) -> bool:
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_schema = DATABASE() AND table_name = %s",
            [tabla],
        )
        return bool(cursor.fetchone()[0])


def _skip_si_faltan_tablas(conn, tablas):
    faltantes = [t for t in tablas if not _existe_tabla(conn, t)]
    if faltantes:
        pytest.skip(f"Base sin tablas requeridas: {', '.join(faltantes)}")


def _assert_estructura_y_formato_basico(rows):
    assert isinstance(rows, list)
    if not rows:
        return
    primero = rows[0]
    assert "label" in primero
    assert "value" in primero
    assert isinstance(primero["label"], str)
    assert isinstance(primero["value"], str)
    # Formato esperado por relay PHP: "<valor>|<texto>"
    assert "|" in primero["value"]
    # Convención histórica de texto en filtros: "(cod:...)"
    assert "(cod:" in primero["label"] or "(ru:" in primero["label"]


def _assert_orden_asc_por_label(rows):
    labels = [r.get("label", "") for r in rows if isinstance(r, dict)]
    if len(labels) < 2:
        return
    assert labels == sorted(labels)


@pytest.mark.integration
class TestDevolucionesRelayIntegration:
    def test_filtros_cliente_no_explota(self, legacy_db_connection):
        base = _base_empresa(legacy_db_connection)
        if not base:
            pytest.skip("Sin nombre de base en conexión mysql.")
        _skip_si_faltan_tablas(legacy_db_connection, ["cliente"])

        rows = listado_filtros_estadisticas(
            base_empresa=base,
            tabla="cliente",
            usa_id_manual=False,
            arr_vend_cargo=[],
        )
        assert isinstance(rows, list)

    def test_listado_devoluciones_no_explota(self, legacy_db_connection):
        base = _base_empresa(legacy_db_connection)
        if not base:
            pytest.skip("Sin nombre de base en conexión mysql.")
        _skip_si_faltan_tablas(legacy_db_connection, ["comp_ped"])

        filas = listar_devoluciones_relay(
            base_empresa=base,
            body={"campoBusca": "1", "estadoPedido": "1"},
            usa_id_manual=False,
            limit=20,
        )
        assert isinstance(filas, list)

    def test_listado_con_fechas_y_estado(self, legacy_db_connection):
        base = _base_empresa(legacy_db_connection)
        if not base:
            pytest.skip("Sin nombre de base en conexión mysql.")
        _skip_si_faltan_tablas(legacy_db_connection, ["comp_ped"])

        with legacy_db_connection.cursor() as cursor:
            cursor.execute(
                "SELECT MIN(Fecha), MAX(Fecha) FROM comp_ped WHERE TipoComprobante = 'DEV'"
            )
            row = cursor.fetchone()
        if not row or not row[0] or not row[1]:
            pytest.skip("Sin devoluciones DEV para validar filtro por fecha.")
        fecha_desde, fecha_hasta = row[0], row[1]

        filas = listar_devoluciones_relay(
            base_empresa=base,
            body={
                "campoBusca": "Fecha",
                "fechaDesde": str(fecha_desde),
                "fechaHasta": str(fecha_hasta),
                "estadoPedido": "1",
            },
            usa_id_manual=False,
            limit=30,
        )
        assert isinstance(filas, list)

    def test_listado_con_filtrar_por_cliente(self, legacy_db_connection):
        base = _base_empresa(legacy_db_connection)
        if not base:
            pytest.skip("Sin nombre de base en conexión mysql.")
        _skip_si_faltan_tablas(legacy_db_connection, ["comp_ped"])

        with legacy_db_connection.cursor() as cursor:
            cursor.execute(
                "SELECT Codigo FROM comp_ped "
                "WHERE TipoComprobante = 'DEV' AND Codigo IS NOT NULL LIMIT 1"
            )
            row = cursor.fetchone()
        if not row:
            pytest.skip("Sin devoluciones DEV con cliente para validar filtrarPor.")
        codigo_cliente = int(row[0])

        filas = listar_devoluciones_relay(
            base_empresa=base,
            body={
                "campoBusca": "1",
                "estadoPedido": "1",
                "filtrarPor": f"cliente|{codigo_cliente}",
            },
            usa_id_manual=False,
            limit=30,
        )
        assert isinstance(filas, list)
        for item in filas:
            if "Codigo" in item and item["Codigo"] is not None:
                assert int(item["Codigo"]) == codigo_cliente

    def test_sugerencias_numero_devolucion(self, legacy_db_connection):
        base = _base_empresa(legacy_db_connection)
        if not base:
            pytest.skip("Sin nombre de base en conexión mysql.")
        _skip_si_faltan_tablas(legacy_db_connection, ["comp_ped"])

        with legacy_db_connection.cursor() as cursor:
            cursor.execute(
                "SELECT NroCompBusq FROM comp_ped "
                "WHERE TipoComprobante = 'DEV' "
                "AND NroCompBusq IS NOT NULL AND NroCompBusq <> '' LIMIT 1"
            )
            row = cursor.fetchone()
        if not row:
            pytest.skip("Sin NroCompBusq de DEV para validar sugerencias.")

        nro = str(row[0]).strip()
        prefijo = nro[:3] if len(nro) >= 3 else nro
        if not prefijo:
            pytest.skip("NroCompBusq sin prefijo usable.")

        sugerencias = sugerencias_nro_devoluciones_relay(
            base_empresa=base,
            query_string=prefijo,
            tipousuario="cliente",
            idcliente=None,
            limit=10,
        )
        assert isinstance(sugerencias, list)


@pytest.mark.integration
class TestFiltrosEstadisticasIntegration:
    def test_filtro_vendedor_estructura(self, legacy_db_connection):
        base = _base_empresa(legacy_db_connection)
        if not base:
            pytest.skip("Sin nombre de base en conexión mysql.")
        _skip_si_faltan_tablas(legacy_db_connection, ["viajantes"])

        rows = listado_filtros_estadisticas(
            base_empresa=base,
            tabla="vendedor",
            usa_id_manual=False,
            arr_vend_cargo=[],
        )
        _assert_estructura_y_formato_basico(rows)
        _assert_orden_asc_por_label(rows)

    def test_filtro_proveedor_estructura(self, legacy_db_connection):
        base = _base_empresa(legacy_db_connection)
        if not base:
            pytest.skip("Sin nombre de base en conexión mysql.")
        _skip_si_faltan_tablas(legacy_db_connection, ["proveedor"])

        rows = listado_filtros_estadisticas(
            base_empresa=base,
            tabla="proveedor",
            usa_id_manual=False,
            arr_vend_cargo=[],
        )
        _assert_estructura_y_formato_basico(rows)
        _assert_orden_asc_por_label(rows)

    def test_filtro_rubro_estructura(self, legacy_db_connection):
        base = _base_empresa(legacy_db_connection)
        if not base:
            pytest.skip("Sin nombre de base en conexión mysql.")
        _skip_si_faltan_tablas(legacy_db_connection, ["rubro"])

        rows = listado_filtros_estadisticas(
            base_empresa=base,
            tabla="rubro",
            usa_id_manual=False,
            arr_vend_cargo=[],
        )
        _assert_estructura_y_formato_basico(rows)
        _assert_orden_asc_por_label(rows)

    def test_filtro_subrubro_estructura(self, legacy_db_connection):
        base = _base_empresa(legacy_db_connection)
        if not base:
            pytest.skip("Sin nombre de base en conexión mysql.")
        _skip_si_faltan_tablas(legacy_db_connection, ["subrubro", "rubro"])

        rows = listado_filtros_estadisticas(
            base_empresa=base,
            tabla="subrubro",
            usa_id_manual=False,
            arr_vend_cargo=[],
        )
        _assert_estructura_y_formato_basico(rows)
        _assert_orden_asc_por_label(rows)

    def test_filtro_usuario_estructura(self, legacy_db_connection):
        base = _base_empresa(legacy_db_connection)
        if not base:
            pytest.skip("Sin nombre de base en conexión mysql.")
        _skip_si_faltan_tablas(legacy_db_connection, ["usuarios"])

        rows = listado_filtros_estadisticas(
            base_empresa=base,
            tabla="usuario",
            usa_id_manual=False,
            arr_vend_cargo=[],
        )
        _assert_estructura_y_formato_basico(rows)
        _assert_orden_asc_por_label(rows)

