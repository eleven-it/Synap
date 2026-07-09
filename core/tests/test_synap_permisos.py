# -*- coding: utf-8 -*-
"""
Tests de la fachada de permisos Synap (get_permisos_totales_administranet) y del
catálogo de seed. Los lectores contra MySQL se mockean para probar el enrutado por
``SYNAP_PERMISOS_SOURCE``, el fallback, el modo dual y las invariantes de supervisor.
"""
from unittest import mock

from django.test import SimpleTestCase, override_settings

from core.services import administranet_permisos_usuario as facade
from core.services.administranet_permisos_usuario import (
    REPORTS_PERMISSIONS_FOR_SUPERVISOR,
    get_permisos_totales_administranet,
)
from core.services.administranet_puestos import (
    AdministraNETPuestosService,
    CreacionPuestoBloqueadaError,
)
from core.services.synap_permisos_seed import _filas_catalogo


def _patch_lectores(synap=None, legacy=None, complementarios=None, tiene_mapeo=False):
    """Devuelve un contexto que mockea los 4 lectores usados por la fachada."""
    return mock.patch.multiple(
        facade,
        get_permisos_desde_synap_store=mock.DEFAULT,
        get_permisos_legacy_synap=mock.DEFAULT,
        get_permisos_complementarios_legacy=mock.DEFAULT,
        puesto_tiene_mapeo_synap=mock.DEFAULT,
    )


class FachadaPermisosTests(SimpleTestCase):
    def test_supervisor_cod_usuario_acceso_total(self):
        # No debe consultar ninguna fuente: retorno temprano {"*"}.
        with _patch_lectores() as m:
            result = get_permisos_totales_administranet(
                "empresa", 3, cod_usuario="supervisor", nombre_puesto="Cajero"
            )
        self.assertEqual(result, {"*"})
        m["get_permisos_desde_synap_store"].assert_not_called()
        m["get_permisos_legacy_synap"].assert_not_called()

    @override_settings(SYNAP_PERMISOS_SOURCE="legacy")
    def test_source_legacy(self):
        with _patch_lectores() as m:
            m["get_permisos_legacy_synap"].return_value = {"stock.ver", "ventas.ver"}
            m["get_permisos_complementarios_legacy"].return_value = {"stock.crear_movimiento"}
            m["get_permisos_desde_synap_store"].return_value = {"NO_DEBE_USARSE"}
            result = get_permisos_totales_administranet("empresa", 5)
        self.assertEqual(result, {"stock.ver", "ventas.ver", "stock.crear_movimiento"})
        m["get_permisos_desde_synap_store"].assert_not_called()

    @override_settings(SYNAP_PERMISOS_SOURCE="synap")
    def test_source_synap_con_mapeo(self):
        with _patch_lectores() as m:
            m["get_permisos_desde_synap_store"].return_value = {"reports.ver"}
            m["puesto_tiene_mapeo_synap"].return_value = True
            m["get_permisos_complementarios_legacy"].return_value = set()
            m["get_permisos_legacy_synap"].return_value = {"NO_DEBE_USARSE"}
            result = get_permisos_totales_administranet("empresa", 5)
        self.assertEqual(result, {"reports.ver"})
        m["get_permisos_legacy_synap"].assert_not_called()

    @override_settings(SYNAP_PERMISOS_SOURCE="synap")
    def test_source_synap_fallback_a_legacy_sin_mapeo(self):
        with _patch_lectores() as m:
            m["get_permisos_desde_synap_store"].return_value = set()
            m["puesto_tiene_mapeo_synap"].return_value = False
            m["get_permisos_legacy_synap"].return_value = {"ventas.ver"}
            m["get_permisos_complementarios_legacy"].return_value = set()
            result = get_permisos_totales_administranet("empresa", 5)
        self.assertEqual(result, {"ventas.ver"})
        m["get_permisos_legacy_synap"].assert_called_once()

    @override_settings(SYNAP_PERMISOS_SOURCE="synap")
    def test_source_synap_mapeo_sin_permisos_no_fallback(self):
        # Puesto mapeado pero sin permisos: set vacío, NO fallback a legacy.
        with _patch_lectores() as m:
            m["get_permisos_desde_synap_store"].return_value = set()
            m["puesto_tiene_mapeo_synap"].return_value = True
            m["get_permisos_legacy_synap"].return_value = {"NO_DEBE_USARSE"}
            m["get_permisos_complementarios_legacy"].return_value = set()
            result = get_permisos_totales_administranet("empresa", 5)
        self.assertEqual(result, set())
        m["get_permisos_legacy_synap"].assert_not_called()

    @override_settings(SYNAP_PERMISOS_SOURCE="dual")
    def test_source_dual_union(self):
        with _patch_lectores() as m:
            m["get_permisos_desde_synap_store"].return_value = {"a", "b"}
            m["get_permisos_legacy_synap"].return_value = {"b", "c"}
            m["get_permisos_complementarios_legacy"].return_value = set()
            result = get_permisos_totales_administranet("empresa", 5)
        self.assertEqual(result, {"a", "b", "c"})

    @override_settings(SYNAP_PERMISOS_SOURCE="legacy")
    def test_complementarios_clavemenu_siempre_sumados(self):
        with _patch_lectores() as m:
            m["get_permisos_legacy_synap"].return_value = set()
            m["get_permisos_complementarios_legacy"].return_value = {"stock.crear_movimiento"}
            result = get_permisos_totales_administranet("empresa", 5)
        self.assertIn("stock.crear_movimiento", result)

    @override_settings(SYNAP_PERMISOS_SOURCE="legacy")
    def test_nombre_puesto_supervisor_agrega_reports(self):
        with _patch_lectores() as m:
            m["get_permisos_legacy_synap"].return_value = set()
            m["get_permisos_complementarios_legacy"].return_value = set()
            result = get_permisos_totales_administranet(
                "empresa", 5, nombre_puesto="Supervisor"
            )
        self.assertTrue(REPORTS_PERMISSIONS_FOR_SUPERVISOR.issubset(result))


class CrearPuestoGuardTests(SimpleTestCase):
    @override_settings(SYNAP_BLOQUEAR_CREAR_PUESTOS=True)
    def test_crear_puesto_bloqueado_lanza_excepcion(self):
        svc = AdministraNETPuestosService()
        with self.assertRaises(CreacionPuestoBloqueadaError):
            svc.crear_puesto("empresa", "Nuevo Puesto")

    @override_settings(SYNAP_BLOQUEAR_CREAR_PUESTOS=False)
    def test_crear_puesto_permitido_no_lanza_por_flag(self):
        # Con el flag desactivado no debe cortar por guard; fallará al conectar (no hay DB),
        # devolviendo None, pero NO CreacionPuestoBloqueadaError.
        svc = AdministraNETPuestosService()
        try:
            resultado = svc.crear_puesto("empresa_inexistente", "Nuevo Puesto")
        except CreacionPuestoBloqueadaError:
            self.fail("No debe bloquear con SYNAP_BLOQUEAR_CREAR_PUESTOS=False")
        self.assertIsNone(resultado)


class CatalogoSeedTests(SimpleTestCase):
    def test_catalogo_keys_unicas_y_comodines(self):
        filas = _filas_catalogo()
        keys = [f[0] for f in filas]
        self.assertEqual(len(keys), len(set(keys)), "Hay key_permiso duplicados en el catálogo")
        for comodin in ("reports.*", "stock.*", "self_checkout.*", "logistica.*"):
            self.assertIn(comodin, keys)
        # Tuplas (key, modulo, nombre) bien formadas
        for key, modulo, nombre in filas:
            self.assertTrue(key and isinstance(key, str))
            self.assertTrue(modulo and isinstance(modulo, str))
            self.assertTrue(nombre and isinstance(nombre, str))
