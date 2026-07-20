"""Tests de resolución de políticas y config_hash."""
from decimal import Decimal

from django.test import TestCase

from contabilidad_audit.models import (
    HistorialPoliticaAuditoria,
    PREFIJOS_CUENTA_DEFAULT,
    PoliticaAuditoriaContable,
)
from contabilidad_audit.services.politicas import (
    calcular_config_hash,
    diff_snapshots_politica,
    listar_historial_politica,
    registrar_historial_politica,
    resolver_politica,
    snapshot_desde_politica,
)


class PoliticasTestCase(TestCase):
    def setUp(self):
        PoliticaAuditoriaContable.objects.get_or_create(
            base_empresa=PoliticaAuditoriaContable.BASE_DEFAULT,
            defaults={
                "tratamiento_anulados": "excluir",
                "politica_centavo": "diario_manda",
                "prefijos_cuenta": dict(PREFIJOS_CUENTA_DEFAULT),
                "ejercicios_cerrados": "no_tocar",
                "alcance_recompute": "ejercicio_seleccionado",
                "tolerancia_decimal": Decimal("0.005"),
                "actualizado_por": "test",
            },
        )

    def test_empresa_sin_override_usa_default(self):
        politica = resolver_politica("empresa_test")
        self.assertEqual(politica["tolerancia_decimal"], Decimal("0.005"))
        self.assertEqual(politica["tratamiento_anulados"], "excluir")

    def test_override_parcial(self):
        PoliticaAuditoriaContable.objects.create(
            base_empresa="empresa_a",
            tolerancia_decimal=Decimal("0.01"),
            prefijos_cuenta=dict(PREFIJOS_CUENTA_DEFAULT),
            actualizado_por="test",
        )
        politica = resolver_politica("empresa_a")
        self.assertEqual(politica["tolerancia_decimal"], Decimal("0.01"))
        self.assertEqual(politica["tratamiento_anulados"], "excluir")

    def test_config_hash_estable(self):
        p1 = resolver_politica("empresa_test")
        p2 = resolver_politica("empresa_test")
        self.assertEqual(calcular_config_hash(p1), calcular_config_hash(p2))

    def test_config_hash_cambia_con_politica(self):
        base = resolver_politica("empresa_test")
        h1 = calcular_config_hash(base)
        base["tratamiento_anulados"] = "incluir_neutralizado"
        h2 = calcular_config_hash(base)
        self.assertNotEqual(h1, h2)

    def test_validacion_prefijos_resultado_vacio(self):
        obj = PoliticaAuditoriaContable(
            base_empresa="mal",
            prefijos_cuenta={"resultado": [], "activo": ["1"], "pasivo": ["2"], "pn": ["3"]},
        )
        with self.assertRaises(Exception):
            obj.full_clean()

    def test_fallback_prefijos_vacio_en_lectura(self):
        PoliticaAuditoriaContable.objects.create(
            base_empresa="empresa_fallback",
            prefijos_cuenta={"resultado": [], "activo": ["1"], "pasivo": ["2"], "pn": ["3"]},
            actualizado_por="test",
        )
        politica = resolver_politica("empresa_fallback")
        self.assertTrue(politica["prefijos_cuenta"]["resultado"])

    def test_registrar_historial_alta(self):
        nueva = PoliticaAuditoriaContable(
            base_empresa="empresa_hist",
            prefijos_cuenta=dict(PREFIJOS_CUENTA_DEFAULT),
            tolerancia_decimal=Decimal("0.01"),
            actualizado_por="usuario_test",
        )
        nueva.full_clean()
        nueva.save()
        registro = registrar_historial_politica(
            base_empresa="empresa_hist",
            anterior=None,
            nuevo=nueva,
            usuario="usuario_test",
        )
        self.assertIsNone(registro.snapshot_anterior)
        self.assertIsNone(registro.config_hash_anterior)
        self.assertTrue(registro.config_hash_nuevo.startswith("v1:"))
        self.assertEqual(registro.cambiado_por, "usuario_test")

    def test_registrar_historial_modificacion(self):
        fila = PoliticaAuditoriaContable.objects.create(
            base_empresa="empresa_mod",
            prefijos_cuenta=dict(PREFIJOS_CUENTA_DEFAULT),
            tolerancia_decimal=Decimal("0.005"),
            actualizado_por="test",
        )
        anterior = snapshot_desde_politica(fila)
        fila.tolerancia_decimal = Decimal("0.02")
        fila.save()
        registro = registrar_historial_politica(
            base_empresa="empresa_mod",
            anterior=anterior,
            nuevo=fila,
            usuario="editor",
        )
        self.assertIsNotNone(registro.config_hash_anterior)
        self.assertNotEqual(registro.config_hash_anterior, registro.config_hash_nuevo)
        cambios = diff_snapshots_politica(registro.snapshot_anterior, registro.snapshot_nuevo)
        self.assertEqual(len(cambios), 1)
        self.assertEqual(cambios[0]["campo"], "tolerancia_decimal")

    def test_listar_historial_politica(self):
        nueva = PoliticaAuditoriaContable.objects.create(
            base_empresa="empresa_lista",
            prefijos_cuenta=dict(PREFIJOS_CUENTA_DEFAULT),
            actualizado_por="test",
        )
        registrar_historial_politica("empresa_lista", None, nueva, "test")
        historial = listar_historial_politica("empresa_lista")
        self.assertEqual(len(historial), 1)
        self.assertTrue(historial[0]["es_alta"])
        self.assertEqual(HistorialPoliticaAuditoria.objects.filter(base_empresa="empresa_lista").count(), 1)
