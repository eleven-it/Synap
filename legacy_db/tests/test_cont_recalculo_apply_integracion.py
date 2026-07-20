"""Test de integración piloto: apply + re-check saldo (solo entorno piloto)."""
from __future__ import annotations

import os
import unittest
from decimal import Decimal

from django.conf import settings
from django.test import TestCase

from contabilidad_audit.models import PREFIJOS_CUENTA_DEFAULT, PoliticaAuditoriaContable
from contabilidad_audit.services.checks.saldos import saldo_ejercicio_vs_diario
from contabilidad_audit.services.politicas import resolver_politica
from contabilidad_audit.services.resultados import CorridaContexto
from legacy_db.services.cont_recalculo_service import apply, dry_run


def _es_piloto_cont() -> bool:
    env = (getattr(settings, "ENVIRONMENT", "") or "").strip().lower()
    flag = os.environ.get("SYNAP_PILOTO_CONT", "").strip()
    return env in ("production", "produccion") and flag == "1"


@unittest.skipUnless(
    _es_piloto_cont(),
    "Integración piloto: requiere ENVIRONMENT=production y SYNAP_PILOTO_CONT=1",
)
class ContRecalculoApplyIntegracionPilotoTestCase(TestCase):
    """
    Apply real sobre ejercicio de prueba en base piloto.

    Ejecución documentada (NO correr contra administranet89 en dev):

    ```bash
    docker exec -e SYNAP_PILOTO_CONT=1 -e ENVIRONMENT=production Synap_app \\
      python manage.py test legacy_db.tests.test_cont_recalculo_apply_integracion --keepdb
    ```

    Variables adicionales recomendadas en el piloto:
    - ``SYNAP_PILOTO_BASE_EMPRESA`` (default: valor de settings.DEFAULT_BASE_EMPRESA)
    - ``SYNAP_PILOTO_ID_EJERCICIO`` (default: 1)
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.base_empresa = os.environ.get(
            "SYNAP_PILOTO_BASE_EMPRESA",
            getattr(settings, "DEFAULT_BASE_EMPRESA", "administranet89"),
        )
        cls.id_ejercicio = int(os.environ.get("SYNAP_PILOTO_ID_EJERCICIO", "1"))
        PoliticaAuditoriaContable.objects.get_or_create(
            base_empresa=PoliticaAuditoriaContable.BASE_DEFAULT,
            defaults={
                "prefijos_cuenta": dict(PREFIJOS_CUENTA_DEFAULT),
                "tolerancia_decimal": Decimal("0.005"),
                "actualizado_por": "piloto",
            },
        )

    def test_apply_y_saldo_ejercicio_vs_diario_verde(self):
        politica = resolver_politica(self.base_empresa)
        payload = dry_run(
            base_empresa=self.base_empresa,
            alcance={"id_ejercicio": self.id_ejercicio},
            politica=politica,
            usuario="piloto_integracion",
        )
        dry_run_id = payload["dry_run_id"]
        if payload.get("impacto", {}).get("total_aplicables", 0) == 0:
            self.skipTest("Dry-run sin items aplicables en el ejercicio piloto.")

        resultado = apply(
            self.base_empresa,
            dry_run_id,
            "piloto_integracion",
            tiene_permiso_corregir=True,
            modo="general",
        )
        self.assertTrue(resultado.get("ok"))

        from core.mysql_pool import get_mysql_pool

        pool = get_mysql_pool()
        with pool.get_connection(self.base_empresa) as conn:
            cur = conn.cursor()
            ctx = CorridaContexto(
                corrida_id="piloto",
                config_hash=payload["config_hash"],
                cursor=cur,
            )
            audit = saldo_ejercicio_vs_diario(
                self.base_empresa,
                {"id_ejercicio": self.id_ejercicio},
                politica,
                ctx,
            )
        self.assertTrue(
            audit.ok,
            msg=f"Diferencias post-apply: {audit.total_diferencias}",
        )
