# Delta — contabilidad-recalculo-correccion

**Change:** `contabilidad-auditoria-anulaciones-apply`  
**Capability:** `contabilidad-recalculo-correccion`  
**Estado:** Propuesto

---

## ADDED Requirements

### Requirement: REC-19 — Reparación auto-apply de anulaciones incompletas compra/pago

El servicio `legacy_db/services/cont_recalculo_service.py` DEBE extender dry-run y apply para reparar hallazgos del check `integridad_anulacion_compra_pago` (AUD-LECT-23) en comprobantes `FA`/`FC`/`OP` con `Anulado='Si'` y `CodigoMovimiento>0`. DEBE incluir `integridad_anulacion_compra_pago` en `CHECKS_INCLUIDOS`. DEBE ampliar `TABLAS_BACKUP_PERMITIDAS` con `cuentaproveedor`. DEBE marcar renglones insertados en `cont_asiento` con `"REGEN auditoria (anulacion incompleta)"` en `desc_renglon_asiento` (o campo trazable equivalente ya usado por REC-18).

El mapeo problema → remedio DEBE ser:

| Problema | Remedio auto-apply |
|----------|-------------------|
| `falta_marcador_cuentaproveedor_cm0` | INSERT marcador en `cuentaproveedor` con `CodigoMovimiento=0`, `codigo_movimiento_anul` = cm original, `Detalle="Anulacion - <Tipo> - <Nro>"`, `Anulado='No'` |
| `asiento_original_no_anulado` | UPDATE `cont_asiento` SET `anulado='Si'` en renglones con `codigo_movimiento` = cm original |
| `falta_contra_asiento` | INSERT contra-asiento con `id_concepto_asiento` 4 (FA/FC) u 8 (OP), debe/haber invertidos respecto al original, **`codigo_movimiento` nuevo** del contador global, `codigo_movimiento_anul` = cm original, `anulado='No'`, `nro_asiento` nuevo |
| `contra_no_invierte_original` | **EXCLUIDO** del auto-apply (item `excluido=True`; revisión manual) |

El orden de apply DEBE ser: (1) regeneración huérfanos REC-18 → (2) reparación anulaciones REC-19 → (3) concepto anulación REC-07 paso 2 → (4) INSERT filas saldo → (5) recompute saldos. DEBE respetar REC-01, REC-03, REC-04, REC-05, REC-06, REC-09, REC-11 y REC-12. DEBE mapear §6.8 de `AUDITORIA_IMPUTACION_CONTABILIDAD_VB6.md` y H53.

#### Scenario: Dry-run propone INSERT marcador cm=0

- **Dado** un comprobante `OP` con `Anulado='Si'`, cm=12345, sin fila marcador en `cuentaproveedor`
- **Cuando** se ejecuta dry-run de corrección con alcance que incluye el ejercicio del comprobante
- **Entonces** el plan incluye un item INSERT sobre `cuentaproveedor` con `CodigoMovimiento=0`, `codigo_movimiento_anul=12345` y `check_id=integridad_anulacion_compra_pago`
- **Y** no se ejecuta DML en legacy

#### Scenario: Dry-run propone UPDATE asiento original

- **Dado** un comprobante anulado cuyo asiento (cm=12345) tiene renglones con `anulado='No'`
- **Cuando** se ejecuta dry-run
- **Entonces** el plan incluye items UPDATE sobre `cont_asiento` marcando `anulado='Si'` para esos renglones

#### Scenario: Dry-run propone INSERT contra-asiento invertido

- **Dado** un comprobante `FA` anulado con asiento original balanceado y sin contra-asiento (concepto 4)
- **Cuando** se ejecuta dry-run
- **Entonces** el plan propone INSERT de renglones en `cont_asiento` con `id_concepto_asiento=4`, debe/haber invertidos respecto al original, `codigo_movimiento` nuevo estimado, `codigo_movimiento_anul=12345` y marca `"REGEN auditoria (anulacion incompleta)"`

#### Scenario: Contra mal invertido queda excluido

- **Dado** un comprobante anulado con contra-asiento existente cuyos totales no espejan al original (`contra_no_invierte_original`)
- **Cuando** se ejecuta dry-run
- **Entonces** el plan marca el caso como `excluido=True` con motivo en español
- **Y** no propone INSERT ni UPDATE que modifiquen el contra existente

#### Scenario: Apply respeta orden regen → repair → concepto → saldos

- **Dado** un plan con items de REC-18, REC-19, concepto anulación y recompute de saldos
- **Cuando** se confirma apply en producción con permiso reforzado
- **Entonces** las escrituras se ejecutan en el orden: regeneración huérfanos, reparación anulaciones, concepto anulación, INSERT filas saldo, recompute saldos
- **Y** todas las mutaciones quedan en una transacción única con log `cont_audit_correccion`

#### Scenario: Backup incluye cuentaproveedor

- **Dado** un plan REC-19 que INSERTA marcador en `cuentaproveedor`
- **Cuando** se confirma apply
- **Entonces** existe tabla backup `cuentaproveedor_bkp_<timestamp>` antes del primer DML
- **Y** el log referencia esa tabla

#### Scenario: Idempotencia post-reparación

- **Dado** un apply exitoso que reparó una anulación incompleta para cm=12345
- **Cuando** se repite dry-run sobre el mismo alcance
- **Entonces** no se proponen items aplicables para ese cm
- **Y** el check `integridad_anulacion_compra_pago` reporta `ok=true`

#### Scenario: Apply bloqueado fuera de producción

- **Dado** `ENVIRONMENT=development` y hallazgos de anulación incompleta
- **Cuando** se intenta apply
- **Entonces** la operación es rechazada sin escritura en legacy (REC-02)

#### Scenario: Ejercicio cerrado excluido

- **Dado** política con `ejercicios_cerrados=no_tocar` y comprobante anulado en ejercicio cerrado
- **Cuando** se genera dry-run
- **Entonces** los items REC-19 de ese ejercicio quedan `excluido=True` según REC-09

---

## MODIFIED Requirements

### Requirement: REC-07 — Orden seguro de ejecución

El motor DEBE aplicar correcciones en este orden fijo salvo bloqueo explícito documentado:

1. `comprobante_compra_pago_sin_asiento` — regeneración de asientos huérfanos (REC-18)  
2. `integridad_anulacion_compra_pago` — reparación de anulaciones incompletas (REC-19)  
3. `concepto_anulacion_incoherente` — UPDATE puntual de `id_concepto_asiento`  
4. `cuentas_sin_fila_saldo` — INSERT de filas faltantes con saldo recalculado  
5. `saldo_ejercicio_vs_diario` / `saldo_periodo_vs_diario` — recompute maestro de tablas derivadas desde `cont_asiento`  
6. `rei_recalculo` — regeneración caso a caso; requiere aprobación explícita adicional  

NO DEBE ejecutar paso 5 antes de completar 2–4 cuando el plan los incluya. NO DEBE ejecutar paso 2 antes de completar paso 1 cuando el plan incluya regeneración de huérfanos para el mismo comprobante.

(Previously: orden sin paso de reparación de anulaciones; regeneración REC-18 implícita al inicio del apply sin numeración explícita en REC-07.)

#### Scenario: Reparación anulación tras regen huérfano

- **Dado** un comprobante sin asiento (huérfano) y anulación incompleta simultánea
- **Cuando** apply ejecuta el lote
- **Entonces** primero regenera el asiento original (REC-18)
- **Y** después aplica reparación de anulación (REC-19) sobre el cm existente

---

### Requirement: REC-08 — Estrategias de corrección por tipo

| Tipo detectado | Acción permitida | Auto-apply |
|----------------|------------------|------------|
| Saldos derivados desincronizados | Recalcular desde `cont_asiento` | Sí (paso 5) |
| Filas saldo faltantes | INSERT con saldo recalculado | Sí (paso 4) |
| Anulación compra/pago incompleta | Reparar marcador / marcar original / insertar contra | Sí (paso 2, REC-19) |
| Contra-asiento que no invierte original | Marcar revisión manual | NO auto-corrige |
| Concepto anulación erróneo | UPDATE a `id_concepto_anul` del original | Sí (paso 3) |
| Asiento desbalanceado centavo | Según `politica_centavo`; re-derivar saldos | Condicional |
| REI mal calculado | Anular/regenerar REI | Solo manual/aprobación |
| Cierre PyG / cuentas resultado | Marcar revisión manual | NO auto-corrige |

(Previously: tabla sin fila para anulaciones incompletas compra/pago.)

#### Scenario: Anulación incompleta auto-reparable

- **Dado** hallazgo `falta_contra_asiento` sin `contra_no_invierte_original`
- **Cuando** apply ejecuta paso 2 (REC-19)
- **Entonces** inserta contra-asiento con concepto 4 u 8 e invierte importes
- **Y** registra log con `check_id=integridad_anulacion_compra_pago`

#### Scenario: Contra desbalanceado no auto-corrige

- **Dado** hallazgo `contra_no_invierte_original`
- **Cuando** se solicita apply genérico
- **Entonces** ese comprobante queda excluido del apply automático
- **Y** permanece visible en auditoría para revisión manual

---

## Referencias

- Check lectura: AUD-LECT-23 en `contabilidad-auditoria-lectura`
- VB6 §6.8: `docs/general/AUDITORIA_IMPUTACION_CONTABILIDAD_VB6.md`
- Motor: `legacy_db/services/cont_recalculo_service.py`
- Change relacionado: `contabilidad-auditoria-recalculo` (REC-18)
