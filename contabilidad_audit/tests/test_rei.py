"""Tests del cálculo y check REI (ajuste por inflación)."""
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import uuid4

from django.test import SimpleTestCase
from django.utils import timezone

from contabilidad_audit.services.checks.rei import rei_recalculo
from contabilidad_audit.services.rei_calculo import (
    PeriodoIndice,
    ResultadoReiCuenta,
    DesalineacionConfigRei,
    calcular_rei_teorico_cuenta,
    evaluar_rei_ejercicio,
    indice_cierre,
    indice_origen,
    movimiento_firmado,
)
from contabilidad_audit.services.resultados import CorridaContexto


def _contexto(cursor):
    return CorridaContexto(
        cursor=cursor,
        corrida_id=str(uuid4()),
        config_hash="v1:test",
        fecha_corrida=timezone.now(),
    )


def _politica(**kwargs):
    base = {
        "tratamiento_anulados": "excluir",
        "politica_centavo": "diario_manda",
        "tolerancia_decimal": Decimal("0.005"),
    }
    base.update(kwargs)
    return base


class ReiCalculoTestCase(SimpleTestCase):
    def test_movimiento_firmado_deudor_y_acreedor(self):
        self.assertEqual(movimiento_firmado("100", "20", "Deudor"), Decimal("80"))
        self.assertEqual(movimiento_firmado("100", "20", "Acreedor"), Decimal("-80"))

    def test_indice_cierre_por_fechasta_ejercicio(self):
        periodos = [
            PeriodoIndice(date(2025, 4, 1), date(2026, 3, 31), Decimal("150")),
            PeriodoIndice(date(2012, 1, 1), date(2012, 12, 31), Decimal("20")),
        ]
        self.assertEqual(indice_cierre(periodos, date(2026, 3, 31)), Decimal("150"))
        self.assertIsNone(indice_cierre(periodos, date(2025, 1, 1)))

    def test_indice_origen_faltante_o_cero(self):
        periodos = [PeriodoIndice(date(2025, 1, 1), date(2025, 1, 31), Decimal("0"))]
        importe, motivo = indice_origen(periodos, date(2025, 1, 15))
        self.assertIsNone(importe)
        self.assertIn("importe cero", motivo or "")

    def test_calcular_rei_acumula_todos_los_renglones_fix_h02(self):
        """Fix H02: no omitir el último renglón al cambiar de cuenta."""
        cur = MagicMock()
        cur.fetchall.side_effect = [
            [
                (date(2025, 5, 10), Decimal("1000"), Decimal("0")),
                (date(2025, 6, 10), Decimal("500"), Decimal("0")),
            ],
            [(Decimal("0"),)],
        ]
        periodos = [PeriodoIndice(date(2025, 4, 1), date(2026, 3, 31), Decimal("100"))]
        resultado = calcular_rei_teorico_cuenta(
            cur,
            id_pc=115,
            cod_pc="210000",
            saldo_pc="Deudor",
            id_ejercicio=1,
            ind_cierre=Decimal("200"),
            periodos=periodos,
        )
        self.assertTrue(resultado.computable)
        # mov 1000 -> subt 1000; mov 500 -> subt 500
        self.assertEqual(resultado.rei_teorico, Decimal("1500"))
        self.assertEqual(resultado.detalle["renglones_acumulados"], 2)

    def test_calcular_rei_indice_origen_faltante_no_computable(self):
        cur = MagicMock()
        cur.fetchall.side_effect = [
            [(date(2025, 5, 10), Decimal("1000"), Decimal("0"))],
            [(Decimal("50"),)],
        ]
        periodos = [PeriodoIndice(date(2025, 6, 1), date(2025, 6, 30), Decimal("100"))]
        resultado = calcular_rei_teorico_cuenta(
            cur,
            id_pc=115,
            cod_pc="210000",
            saldo_pc="Deudor",
            id_ejercicio=1,
            ind_cierre=Decimal("200"),
            periodos=periodos,
        )
        self.assertFalse(resultado.computable)
        self.assertIsNone(resultado.rei_teorico)
        self.assertIn("falta índice de origen", resultado.motivo_no_computable or "")

    def test_evaluar_rei_sin_indice_cierre(self):
        cur = MagicMock()

        def _execute(sql, params=None):
            sql_norm = " ".join(sql.split())
            if "cont_indiceinfla_periodo" in sql_norm and "anulado" in sql_norm:
                cur.fetchall.return_value = [
                    {
                        "fecdesde_indiceinfla_periodo": date(2012, 1, 1),
                        "fechasta_indiceinfla_periodo": date(2012, 12, 31),
                        "importe_indiceinfla_periodo": Decimal("20"),
                    }
                ]
            elif "fechasta_ejercicio FROM cont_ejercicio" in sql_norm:
                cur.fetchone.return_value = {"fechasta_ejercicio": date(2026, 3, 31)}
            elif "id_paramatriz" in sql_norm:
                cur.fetchone.return_value = {"id_pc": 109}
            elif "ajuste_infla_pc" in sql_norm and "cont_pc" in sql_norm:
                cur.fetchall.return_value = [
                    {"id_pc": 115, "cod_pc": "210000", "saldo_pc": "Deudor"}
                ]
            elif "id_concepto_asiento = %s" in sql_norm and params and params[-1] == 13:
                if "ajuste_infla_pc" in sql_norm:
                    cur.fetchall.return_value = [
                        {"id_pc": 17, "cod_pc": "170000"},
                    ]
                elif "GROUP BY a.codigo_movimiento" in sql_norm:
                    cur.fetchall.return_value = [
                        {
                            "codigo_movimiento": "9001",
                            "cuentas": "17,140",
                        }
                    ]
                else:
                    cur.fetchall.return_value = [{"total": Decimal("0")}]
            else:
                cur.fetchall.return_value = []

        cur.execute.side_effect = _execute
        evaluacion = evaluar_rei_ejercicio(cur, 1)
        self.assertIsNone(evaluacion["ind_cierre"])
        self.assertIn("falta índice de cierre", evaluacion["motivo_ind_cierre"] or "")
        self.assertFalse(evaluacion["cuentas"][0].computable)
        self.assertGreaterEqual(len(evaluacion["desalineaciones"]), 1)


class ReiCheckTestCase(SimpleTestCase):
    @patch("contabilidad_audit.services.checks.rei.evaluar_rei_ejercicio")
    def test_rei_recalculo_delta_computable(self, mock_eval):
        mock_eval.return_value = {
            "id_ejercicio": 1,
            "fechasta_ejercicio": "31/03/2026",
            "ind_cierre": "200",
            "motivo_ind_cierre": None,
            "id_pc_contrapartida": 109,
            "periodos_indice_cargados": 1,
            "cuentas": [
                ResultadoReiCuenta(
                    id_pc=115,
                    cod_pc="210000",
                    saldo_pc="Deudor",
                    rei_teorico=Decimal("1500"),
                    rei_registrado=Decimal("1200"),
                    computable=True,
                )
            ],
            "desalineaciones": [],
        }
        ctx = _contexto(MagicMock())
        result = rei_recalculo("empresa", {"id_ejercicio": 1}, _politica(), ctx)
        self.assertFalse(result.ok)
        self.assertEqual(len(result.diferencias), 1)
        self.assertEqual(result.diferencias[0].delta, Decimal("300"))
        self.assertEqual(result.diferencias[0].referencia_hallazgo, "H02")

    @patch("contabilidad_audit.services.checks.rei.evaluar_rei_ejercicio")
    def test_rei_recalculo_no_computable_sin_delta_espurio(self, mock_eval):
        mock_eval.return_value = {
            "id_ejercicio": 1,
            "fechasta_ejercicio": "31/03/2026",
            "ind_cierre": None,
            "motivo_ind_cierre": "falta índice de cierre para 31/03/2026",
            "id_pc_contrapartida": 109,
            "periodos_indice_cargados": 1,
            "cuentas": [
                ResultadoReiCuenta(
                    id_pc=115,
                    cod_pc="210000",
                    saldo_pc="Deudor",
                    rei_teorico=None,
                    rei_registrado=Decimal("0"),
                    computable=False,
                    motivo_no_computable="falta índice de cierre para 31/03/2026",
                )
            ],
            "desalineaciones": [],
        }
        ctx = _contexto(MagicMock())
        result = rei_recalculo("empresa", {"id_ejercicio": 1}, _politica(), ctx)
        self.assertFalse(result.ok)
        dif = result.diferencias[0]
        self.assertIsNone(dif.delta)
        self.assertEqual(dif.detalle.get("estado"), "no_computable")

    @patch("contabilidad_audit.services.checks.rei.evaluar_rei_ejercicio")
    def test_rei_recalculo_desalineacion_config_h44(self, mock_eval):
        mock_eval.return_value = {
            "id_ejercicio": 1,
            "fechasta_ejercicio": "31/03/2026",
            "ind_cierre": None,
            "motivo_ind_cierre": "falta índice de cierre para 31/03/2026",
            "id_pc_contrapartida": 109,
            "periodos_indice_cargados": 1,
            "cuentas": [],
            "desalineaciones": [
                DesalineacionConfigRei(
                    id_pc=17,
                    cod_pc="170000",
                    tipo="cuenta_sin_ajuste_inflacion",
                    detalle={"mensaje": "REI registrado sobre cuenta sin ajuste_infla_pc='Si'"},
                )
            ],
        }
        ctx = _contexto(MagicMock())
        result = rei_recalculo("empresa", {"id_ejercicio": 1}, _politica(), ctx)
        self.assertFalse(result.ok)
        self.assertEqual(result.diferencias[0].referencia_hallazgo, "H44")
        self.assertEqual(result.diferencias[0].detalle.get("estado"), "desalineacion_config")
