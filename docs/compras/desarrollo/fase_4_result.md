# Resultado Fase 4 — Posting legacy (estado entregado y pendientes)

**Normativa:** [docs/compras/posting_contract.md](compras/posting_contract.md), [posting_sql_spec.md](compras/posting_sql_spec.md), [posting_tests.md](compras/posting_tests.md), DoD Fase 4.

---

## 1. Módulos implementados en código (hoy)

| Componente | Ubicación | Notas |
|------------|-----------|--------|
| Comando + validación v1 | `factura_compra_posting/legacy_posting_command_v1.py` | Test gate UT-CMD parcial |
| Mapper expediente → comando | `factura_compra_posting/mapper_v1.py` | Sin ORM legacy |
| Conexión fake + adapter grabación P1–P9 | `fake_legacy_connection.py`, `recording_mysql_adapter.py` | Orden BEGIN → FOR UPDATE → fases → COMMIT; UT-ADP |
| Preflight servicio | `preflight_legacy.py` | UT-PRE |
| Flag SQL real | `FACTURA_COMPRA_LEGACY_SQL_ENABLED` (default **False** en `settings.py`) | Obligatorio mantener apagado hasta fixture + IT |

---

## 2. SQL real por módulo P*

**No implementado aún** contra MySQL: los módulos P1–P9 existen como **marcadores de fase** en el adapter de grabación. La implementación parametrizada sin ORM legacy, transacción única ADR-0002 y `FOR UPDATE` sobre `codmov` deben añadirse cuando el test gate completo y la fixture de [posting_tests.md §8](compras/posting_tests.md) estén operativos.

---

## 3. Tests

| Suite | Estado |
|-------|--------|
| UT-CMD (parcial) | `test_legacy_command_v1.py` |
| UT-ADP | `test_ut_adp.py` |
| UT-PRE | `test_ut_pre.py` |
| IT-LEG-01..04 | `test_it_leg_placeholder.py` — **omitidos** salvo `RUN_MYSQL_LEGACY_IT=1` |

**Criterio de equipo:** no ejecutar SQL real contra legacy hasta UT-CMD/ADP/PRE completos en verde + fixture acordada.

---

## 4. Diferencias vs auditoría VB6 (riesgo)

- El adapter real deberá respetar orden de ramas documentado en auditoría; el código actual solo fija **orden de transacción y fases nominales**.
- Tipos columnas AdministraNET: en escritura real usar `core.utils.administranet_types` (regla proyecto).
- Triggers y reglas no documentadas en SQL spec → riesgo de divergencia; registrar en issues por cliente.

---

## 5. Idempotencia y transacción

- Idempotencia Synap: `idempotency_key` por intento en comando v1; modelo expediente guarda `idempotency_key_last` y `posting_attempt`.
- **Doble posting:** la capa real deberá combinar clave + estado `posting_status` (diseño en contrato); tests UT-IDM pendientes de modelo dedicado si se exige.

**No avanzar a Fase 5 funcional sin IT-LEG en verde** según DoD; el placeholder documenta el gap.
