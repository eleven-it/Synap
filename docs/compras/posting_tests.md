# Tests del posting legacy: especificación TDD (antes de lógica real)

**Referencias:** [posting_contract.md](posting_contract.md), [posting_sql_spec.md](posting_sql_spec.md), [test_strategy.md](test_strategy.md), [test_cases.md](test_cases.md).

**Orden obligatorio:** implementar y hacer pasar estos tests **antes** del cuerpo SQL real del adapter (mocks/stubs primero).

### Regla de equipo — test gate antes de MySQL legacy real

**No está permitido** ejecutar **SQL real** del `LegacyPostingAdapter` contra **MySQL AdministraNET legacy** (entornos con datos reales o sin fixture aislada acordada) mientras **no estén en verde** la totalidad de:

1. Suite **UT-CMD-*** (§2).
2. Suite **UT-ADP-*** (§4).
3. Tests **preflight** **UT-PRE-*** (§5).

Norma replicada en [master_execution_plan.md](master_execution_plan.md) §6 y en DoD Fase 4 de [definition_of_done_by_phase.md](definition_of_done_by_phase.md).

---

## 1. Principios

1. **Contrato primero:** `LegacyPostingCommand` + validaciones `V-*` con tests de propiedades/frozen y `validate_command(cmd)`.
2. **Adapter con doble de conexión:** en unit tests, un `FakeLegacyConnection` que registra orden de operaciones y soporta `commit`/`rollback` simulado.
3. **Integración MySQL:** solo después con fixtures de [§8](#8-fixtures-mínimos-mysql).
4. Cada test cita **ID** de validación o **paso P*** de `posting_sql_spec.md` cuando aplique.

---

## 2. Tests unitarios — `LegacyPostingCommand` y validaciones

| Test ID | Nombre sugerido (`pytest`) | Qué asserta | Evidencia |
|---------|---------------------------|-------------|-----------|
| UT-CMD-01 | `test_command_frozen_immutable` | `dataclasses.replace` o mutación falla | Contrato |
| UT-CMD-02 | `test_validate_fails_empty_lines` | `V-01` raise | Auditoría |
| UT-CMD-03 | `test_validate_fails_zero_total` | `V-02` | Auditoría |
| UT-CMD-04 | `test_validate_origen_remito_sin_codmov_remito` | `V-04` | sql.md |
| UT-CMD-05 | `test_validate_origen_oc_sin_codmov_oc` | `V-05` | sql.md |
| UT-CMD-06 | `test_validate_origen_vale_sin_vales` | `V-06` | sql.md |
| UT-CMD-07 | `test_validate_lote_sin_codigo` | `V-09` | Anexo A |
| UT-CMD-08 | `test_validate_percep_ib_sin_detalle` | `V-12` | Guardar |
| UT-CMD-09 | `test_validate_contado_dias_cero` | coherencia `cond_compra_dias` + flags caja | reglas_negocio |
| UT-HDR-01 | `test_nro_comprobante_formateado_requerido` | header sin string formateado → error mapper, no adapter | Contrato |

**Implementación sugerida:** función pura `validate_posting_command(cmd: LegacyPostingCommand) -> None` que lanza `PostingValidationError(code=...)`.

---

## 3. Tests unitarios — numeración y mappers

| Test ID | Nombre | Comportamiento | Notas |
|---------|--------|----------------|-------|
| UT-NUM-01 | `test_formato_nro_comprobante_ceros` | Entrada PV + nro → string igual a regla VB6 | Parámetros desde config mock |
| UT-MAP-01 | `test_mapper_expediente_minimo_a_command` | Expediente fake → command con `lines` 1 elemento | Sin DB |
| UT-MAP-02 | `test_mapper_entrada_fisica_deposito_matriz` | Tabla de casos (origen × remite_factura_art × permiso) | Debe coincidir con VB6 documentado |

---

## 4. Tests unitarios — `LegacyPostingAdapter` con fake connection

**Objetivo:** verificar **orden de llamadas** a métodos del fake sin MySQL.

### 4.1 Fake mínimo

```python
class FakeLegacyConnection:
    def __init__(self):
        self.log: list[str] = []
        self.in_tx = False

    def begin(self): self.in_tx = True; self.log.append("BEGIN")
    def commit(self): self.log.append("COMMIT"); self.in_tx = False
    def rollback(self): self.log.append("ROLLBACK"); self.in_tx = False
    def execute(self, sql: str, params: tuple): self.log.append(f"EXEC:{sql[:50]}...")
```

### 4.2 Tests

| Test ID | Nombre | Assert |
|---------|--------|--------|
| UT-ADP-01 | `test_adapter_starts_transaction` | Primer log `BEGIN` |
| UT-ADP-02 | `test_adapter_codmov_lock_before_inserts` | Orden: `BEGIN` → ejecución que contiene `codmov` / `FOR UPDATE` → resto |
| UT-ADP-03 | `test_adapter_commit_on_success` | Último `COMMIT` |
| UT-ADP-04 | `test_adapter_rollback_on_error` | Tras excepción simulada en P3, `ROLLBACK` y sin `COMMIT` |
| UT-ADP-05 | `test_adapter_skips_caja_when_credito` | No log de `caja_saldo` si días ≠ 0 |
| UT-ADP-06 | `test_adapter_skips_op_factura_when_contado` | No log `op_factura` si días = 0 |

**Nota:** hasta que exista SQL real, el adapter stub puede registrar **marcadores** `PHASE=P1`, `PHASE=P2`, … para assert de orden.

---

## 5. Tests unitarios — `PreflightLegacyPostingService`

Mock de cursor que devuelve:

- 0 filas → `FISCAL_PERIOD_CLOSED`
- 1 fila duplicado → `DUPLICATE_INVOICE`

| Test ID | Nombre |
|---------|--------|
| UT-PRE-01 | `test_preflight_period_ok` |
| UT-PRE-02 | `test_preflight_period_closed` |
| UT-PRE-03 | `test_preflight_duplicate` |
| UT-PRE-04 | `test_preflight_duplicate_fm_excluded_when_flag_false` |

---

## 6. Tests unitarios — idempotencia (Synap DB)

Usar `pytest-django` o transacciones de test en modelo **stub** `ExpedientePostingState`:

| Test ID | Nombre |
|---------|--------|
| UT-IDM-01 | `test_second_approve_same_key_returns_cached_result` |
| UT-IDM-02 | `test_concurrent_second_fails_with_conflict` |
| UT-IDM-03 | `test_after_failed_retry_increments_attempt` |

---

## 7. Tests de integración MySQL (después de unitarios)

Ejecutar contra fixture [§8](#8-fixtures-mínimos-mysql). Marcar `@pytest.mark.mysql_legacy`.

| Test ID | Nombre | Caso TC de test_cases.md |
|---------|--------|---------------------------|
| IT-LEG-01 | `test_posting_contado_minimo` | TC-POST-01 |
| IT-LEG-02 | `test_posting_credito_op_factura` | TC-POST-02 |
| IT-LEG-03 | `test_posting_rollback_no_huella` | TC-ERR-10 |
| IT-LEG-04 | `test_codmov_serializado_dos_threads` | TC-POST-05 |

---

## 8. Fixtures mínimos MySQL

**Objetivo:** schema reducido o base de datos de test con solo lo necesario para **un** comprobante contado mínimo y **uno** crédito.

### 8.1 Tablas mínimas (filas semilla)

| Tabla | Filas | Campos críticos |
|-------|-------|-----------------|
| `codmov` | 1 (`codigo=1`, `CodigoMovimiento` conocido) | PK `codigo` |
| `proveedor` | 1 | `codigo`, `saldo` inicial |
| `cond_venta` | 2 | `Codigo`, `Dias` = `'0'` y `'30'` |
| `years` | 1 | año actual |
| `periodos` | 1+ | abierto, `vencimiento_fiscal_periodo` futuro |
| `articulo` | 1 | `IDArt`, alícuota, tipo |
| `stock_deposito` | 1 | `id_articulo`, `id_deposito`, `Saldo`, `saldo_pedido_proveedor` opcional |
| `caja_saldo` | 1 | `id_caja`, `moneda='Pesos'`, `Saldo` |
| `caja_abm` | 1 | id usado por command |
| `iva` | 1 | alícuota del artículo |

**Para crédito:** no requiere `caja_saldo` si el posting no entra en rama contado.

**Para OC (test opcional):** `cuentaproveedor` OC + `stockp` mínimo.

**Para contabilidad (test opcional):** `configuracion`, `cont_ejercicio`, `cont_periodo`, `cont_paramatriz` stub, `cont_pc` con `saldo_pc` definido.

### 8.2 Datos de command mínimo contado

- `cond_compra_dias = '0'`
- 1 línea con `id_art` existente, `cod_deposito` existente, `entrada_fisica_deposito = True`
- `importe_total` > 0, totales coherentes
- `nro_comprobante_formateado` único en DB de test

### 8.3 Limpieza

Cada test en transacción **rollback** al final o TRUNCATE ordenado respetando FKs (o schema efímero por caso).

---

## 9. Orden de implementación TDD recomendado

1. `validate_posting_command` + tests UT-CMD-*  
2. `format_nro_comprobante` + UT-NUM-01  
3. `FakeLegacyConnection` + `LegacyPostingAdapter` stub con fases P1–P5 + UT-ADP-*  
4. `PreflightLegacyPostingService` + UT-PRE-*  
5. Modelo idempotencia Synap + UT-IDM-*  
6. SQL real módulo por módulo según `posting_sql_spec.md`, sustituyendo stubs  
7. IT-LEG-*

---

## 10. Regresión contra auditoría

Mantener tabla en código o CSV:

```text
audit_ref,test_id
auditoria_facturas_compras_sql.md#Validacion_Comp,UT-PRE-03
posting_sql_spec.md#P1,UT-ADP-02
```

CI: fallar si se elimina test enlazado a `CA-*` del PRD sin ADR.

---

## 11. Marcadores pytest

```ini
markers =
    mysql_legacy: requiere MySQL legacy fixture
    posting_unit: unitarios posting sin DB
```

---

## 12. Qué no testear en esta fase

- OCR, PWA, UI.  
- `modificacion_comp` VB6 (fuera de alcance primera entrega posting).
