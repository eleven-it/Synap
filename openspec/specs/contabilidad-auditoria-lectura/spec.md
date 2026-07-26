# contabilidad-auditoria-lectura Specification

## Purpose

Exponer un motor de auditoría **determinista y solo lectura** sobre las tablas `cont_*` del MySQL legacy AdministraNET, mapeando los hallazgos de `AUDITORIA_IMPUTACION_CONTABILIDAD_VB6.md`. El motor DEBE detectar inconsistencias entre el diario (`cont_asiento`) y las tablas derivadas de saldo, sin escribir nunca en el legacy. La UX MAY divergir del VB6 siguiendo el canon de reportes Synap.

*Archivado desde el cambio OpenSpec `contabilidad-auditoria-recalculo` (19/07/2026).*


## Requirements

### Requirement: AUD-LECT-01 — Motor estrictamente solo lectura

El motor de auditoría DEBE ejecutar únicamente consultas `SELECT` (y operaciones de lectura equivalentes) contra el MySQL legacy. NO DEBE emitir `INSERT`, `UPDATE`, `DELETE`, `ALTER` ni invocar servicios de escritura de `legacy_db`. Toda conexión DEBE usar `get_mysql_pool().get_connection(base_empresa)` siguiendo el patrón de `reports/services/reconciliation_*`.

#### Scenario: Ejecución de corrida completa sin escritura

- **Dado** un `base_empresa` con datos contables en MySQL legacy
- **Cuando** se ejecuta una corrida con todos los checks registrados
- **Entonces** el motor solo emite `SELECT` y no modifica ninguna fila en tablas `cont_*`

#### Scenario: Entorno no producción

- **Dado** `ENVIRONMENT` distinto de `production`
- **Cuando** un usuario autorizado ejecuta auditoría
- **Entonces** la corrida se completa en solo lectura igual que en producción

---

### Requirement: AUD-LECT-02 — Registry de checks deterministas

El sistema DEBE mantener un registry `CHECKS` en `contabilidad_audit/services/` donde cada `check_id` apunta a una función pura `(base_empresa, filtros, politica_resuelta) -> AuditResult`. Cada check DEBE ser determinista: mismos filtros, misma política efectiva y mismos datos legacy producen el mismo resultado. El registry DEBE incluir como mínimo los 16 checks núcleo definidos en el proposal (14 originales + 2 de compras/pagos).

#### Scenario: Ejecución de un check individual

- **Dado** el registry con `check_id = saldo_ejercicio_vs_diario`
- **Cuando** se invoca solo ese check para un ejercicio dado
- **Entonces** se devuelve un `AuditResult` con `check_id`, conteos y lista de diferencias sin ejecutar otros checks

#### Scenario: Ejecución de todos los checks

- **Dado** filtros `base_empresa`, `id_ejercicio` e `id_periodo` opcional
- **Cuando** se solicita corrida completa
- **Entonces** el sistema ejecuta los ≥16 checks registrados y agrega un resumen por check

---

### Requirement: AUD-LECT-03 — Contrato estándar AuditResult

Cada check DEBE devolver un `AuditResult` con al menos: `check_id`, `titulo`, `severidad` (`critico`|`alto`|`medio`), `ok`, `total_evaluado`, `total_diferencias`, `diferencias[]`, `resumen`, `error` (nullable), `config_hash` de la política usada y metadatos de corrida (`corrida_id`, `fecha_corrida` en formato dd/MM/yyyy HH:mm para UI). Cada elemento de `diferencias` DEBE incluir referencias de drill-down: `id_pc`, `cod_pc` (si aplica), `id_ejercicio`, `id_periodo` (si aplica), `codigo_movimiento`, `nro_asiento`, `valor_esperado`, `valor_actual`, `delta`, `referencia_hallazgo` (p. ej. `H04`).

#### Scenario: Check sin diferencias

- **Dado** un ejercicio donde el saldo derivado coincide con el diario dentro de tolerancia
- **Cuando** se ejecuta `saldo_ejercicio_vs_diario`
- **Entonces** `ok=true`, `total_diferencias=0` y `diferencias` está vacía

#### Scenario: Check con diferencias y drill-down

- **Dado** una cuenta imputable con `|saldo_derivado − saldo_diario| > tolerancia_decimal`
- **Cuando** se ejecuta `saldo_ejercicio_vs_diario`
- **Entonces** cada diferencia incluye `id_pc`, `id_ejercicio`, `delta` y al menos un `codigo_movimiento` o `nro_asiento` para navegar al comprobante

---

### Requirement: AUD-LECT-04 — Check asiento_balanceado

El check `asiento_balanceado` DEBE agrupar por `codigo_movimiento` y detectar asientos donde `|SUM(debe_asiento) − SUM(haber_asiento)| > tolerancia_decimal`, aplicando `politica_centavo` de la política resuelta. DEBE mapear hallazgos H09, H10, H16, H42.

#### Scenario: Asiento desbalanceado por truncado locale

- **Dado** un `codigo_movimiento` con Σdebe − Σhaber = 0,02 por truncado asimétrico (H09)
- **Cuando** se ejecuta `asiento_balanceado` con `tolerancia_decimal=0.005`
- **Entonces** el check reporta la diferencia con referencia `H09` y datos del comprobante

#### Scenario: Asiento balanceado dentro de tolerancia

- **Dado** un asiento con desbalance de 0,01 y `politica_centavo=conservar_compensacion`
- **Cuando** se ejecuta `asiento_balanceado`
- **Entonces** el comportamiento DEBE seguir la regla de centavo configurada (documentada en design) y no reportar falso positivo si la política lo excluye

---

### Requirement: AUD-LECT-05 — Checks saldo derivado vs diario

Los checks `saldo_ejercicio_vs_diario` y `saldo_periodo_vs_diario` DEBEN recalcular el saldo teórico desde `cont_asiento` aplicando la regla de signo según `cont_pc.saldo_pc` (`Deudor`: debe−haber; `Acreedor`: haber−debe), respetando `tratamiento_anulados`. DEBEN comparar contra `cont_ejercicio_saldo_cta` y `cont_periodo_saldo_cta` usando `tolerancia_decimal`. DEBEN mapear H01, H03, H04, H10, H17, H33.

#### Scenario: Desincronización por saldo_pc NULL en re-alta

- **Dado** una cuenta cuyo movimiento fue modificado con `saldo_pc_temp` NULL en VB6 (H04)
- **Cuando** se ejecuta `saldo_ejercicio_vs_diario`
- **Entonces** se reporta delta entre saldo teórico y `saldo_ejercicio_cta` con referencia `H04`

#### Scenario: Cuenta con saldo_pc NULL en plan

- **Dado** una fila de `cont_pc` con `saldo_pc` NULL usada en movimientos
- **Cuando** se ejecuta cualquier check de saldo vs diario
- **Entonces** el check DEBE reportar la fila como diferencia crítica indicando imposibilidad de calcular signo, sin lanzar excepción no controlada

---

### Requirement: AUD-LECT-06 — Check cuentas_sin_fila_saldo

El check `cuentas_sin_fila_saldo` DEBE listar cuentas con `imp_cont_pc='Imputable'` que tienen movimientos en `cont_asiento` pero carecen de fila correspondiente en `cont_ejercicio_saldo_cta` y/o `cont_periodo_saldo_cta`. DEBE mapear H17, H20, H34.

#### Scenario: Cuenta imputable creada después del alta de ejercicio

- **Dado** una cuenta imputable con movimientos y sin fila en `cont_ejercicio_saldo_cta` (H34)
- **Cuando** se ejecuta `cuentas_sin_fila_saldo`
- **Entonces** la diferencia incluye `id_pc`, `id_ejercicio` y referencia `H34`

---

### Requirement: AUD-LECT-07 — Check imputacion_a_no_imputable

El check `imputacion_a_no_imputable` DEBE detectar renglones de `cont_asiento` cuyo `id_pc` apunta a `cont_pc.imp_cont_pc <> 'Imputable'`. DEBE mapear H15.

#### Scenario: Imputación a cuenta contenedora

- **Dado** un renglón de asiento sobre cuenta contenedora
- **Cuando** se ejecuta `imputacion_a_no_imputable`
- **Entonces** se reporta el `codigo_movimiento`, `id_pc` y referencia `H15`

---

### Requirement: AUD-LECT-08 — Check concepto_anulacion_incoherente

El check `concepto_anulacion_incoherente` DEBE detectar contra-asientos de anulación cuyo `id_concepto_asiento` no coincide con `cont_concepto_asiento.id_concepto_anul` del asiento original (no DEBE asumir `id_concepto_asiento + 1`). DEBE mapear H05.

#### Scenario: Contra-asiento con concepto incorrecto

- **Dado** un contra-asiento generado con `id_concepto_asiento + 1` en lugar de `id_concepto_anul` (H05)
- **Cuando** se ejecuta `concepto_anulacion_incoherente`
- **Entonces** se reportan ambos conceptos (esperado vs actual) y el `codigo_movimiento` del contra-asiento

---

### Requirement: AUD-LECT-09 — Check nro_asiento_duplicado

El check `nro_asiento_duplicado` DEBE detectar `nro_asiento` repetidos dentro del mismo `id_ejercicio`, incluyendo casos de numeración tomada del ejercicio activo pero estampada en otro ejercicio (H07). DEBE mapear H06, H07.

#### Scenario: Colisión de numeración concurrente

- **Dado** dos comprobantes distintos con el mismo `nro_asiento` en un ejercicio
- **Cuando** se ejecuta `nro_asiento_duplicado`
- **Entonces** se listan ambos `codigo_movimiento` con referencia `H06`

---

### Requirement: AUD-LECT-10 — Check codigo_movimiento_huerfano

El check `codigo_movimiento_huerfano` DEBE detectar registros en tablas satélite (p. ej. `cont_cc_asiento`) sin renglones correspondientes en `cont_asiento` del **mismo ejercicio**, limitando el alcance a códigos de movimiento cuyo comprobante (`cuentaproveedor` o `cuentacliente`) tenga `Fecha` dentro del rango del ejercicio filtrado (`cont_ejercicio`). Si se indica `id_periodo`, DEBE acotar además la fecha del comprobante al intervalo del período. DEBE mapear H01, H08.

#### Scenario: CC sin asiento padre

- **Dado** filas en `cont_cc_asiento` cuyo `codigo_movimiento` no existe en `cont_asiento`
- **Cuando** se ejecuta `codigo_movimiento_huerfano`
- **Entonces** se reporta el `codigo_movimiento` huérfano con referencia `H08`

---

### Requirement: AUD-LECT-11 — Checks fecha y periodo

Los checks `fecha_fuera_de_periodo` y `periodos_solapados` DEBEN validar que `cont_asiento.fecha_asiento` cae dentro del intervalo `[fecdesde, fechasta]` del periodo asignado, y que no existen solapamientos reales de intervalos entre periodos o ejercicios (`start1 <= end2 AND start2 <= end1`). DEBEN normalizar fechas con `to_date_or_none` y reportar fechas en UI como dd/MM/yyyy. DEBEN mapear H12, H13, H28, H30, H31, H32.

#### Scenario: Asiento con fecha fuera del periodo

- **Dado** un renglón cuya `fecha_asiento` excede `fechasta` del periodo (H13)
- **Cuando** se ejecuta `fecha_fuera_de_periodo`
- **Entonces** se reporta la fecha en dd/MM/yyyy, el periodo esperado y referencia `H13`

#### Scenario: Periodos solapados por rango envolvente

- **Dado** dos periodos cuyos intervalos se intersectan aunque no coincidan en extremos (H28)
- **Cuando** se ejecuta `periodos_solapados`
- **Entonces** se reportan los pares `id_periodo` conflictivos

#### Scenario: Fecha legacy inválida o NULL

- **Dado** un renglón con `fecha_asiento` NULL o no parseable
- **Cuando** se ejecuta `fecha_fuera_de_periodo`
- **Entonces** el check DEBE reportar la fila como diferencia sin abortar la corrida completa

---

### Requirement: AUD-LECT-12 — Check cierre_resultado_no_cero

El check `cierre_resultado_no_cero` DEBE identificar cuentas de resultado según `prefijos_cuenta` de la política resuelta con saldo ≠ 0 tras procesos de cierre PyG. NO DEBE auto-corregir; solo marca para revisión manual. DEBE mapear H11 y prefijos hardcodeados H14.

#### Scenario: Cuenta 4x con saldo residual post-cierre

- **Dado** una cuenta cuyo `cod_pc` coincide con prefijo de resultado configurado y saldo ≠ 0
- **Cuando** se ejecuta `cierre_resultado_no_cero` tras fecha de cierre del ejercicio
- **Entonces** se reporta la cuenta con referencia `H11` y severidad `medio`

---

### Requirement: AUD-LECT-13 — Check reparto_cc_incompleto

El check `reparto_cc_incompleto` DEBE comparar `SUM(cont_cc_asiento.importe_cc)` contra debe/haber del renglón en `cont_asiento` usando `tolerancia_decimal`. DEBE mapear H39, H40, H43.

#### Scenario: Reparto CC no cuadra

- **Dado** un renglón donde la suma de CC difiere del importe del renglón en más de la tolerancia
- **Cuando** se ejecuta `reparto_cc_incompleto`
- **Entonces** se reporta `codigo_movimiento`, delta de CC y referencia `H43`

---

### Requirement: AUD-LECT-14 — Check rei_recalculo

El check `rei_recalculo` DEBE recalcular el ajuste por inflación (REI) con la fórmula VB6 corregida (acumulación de **todos** los renglones base, fix H02), usando índices `cont_indiceinfla_periodo` (`ind_cierre` por `fechasta_ejercicio`, `ind_origen` por mes de `fecha_asiento`). DEBE comparar `REI_teorico` contra la suma firmada de renglones **concepto 13** por cuenta/ejercicio. DEBE reportar estado **no computable** (sin delta espurio) cuando falten índices. DEBE detectar desalineación de config (cuentas con concepto 13 sin `ajuste_infla_pc='Si'`, contrapartida ≠ paramatriz 63). DEBE mapear H02, H44. NO DEBE modificar asientos REI ni fabricar ajustes sin índices.

#### Scenario: REI subvaluado por acumulación rota

- **Dado** un ejercicio con asientos REI generados por VB6 con acumulación incorrecta (H02)
- **Cuando** se ejecuta `rei_recalculo`
- **Entonces** se reporta delta entre REI teórico (acumulación completa) y REI registrado por cuenta afectada

#### Scenario: Índices de inflación faltantes

- **Dado** un ejercicio sin `ind_cierre` o sin `ind_origen` para algún mes de movimiento
- **Cuando** se ejecuta `rei_recalculo`
- **Entonces** se reporta hallazgo `estado=no_computable` con motivo y referencia H02, sin `delta=0` espurio

#### Scenario: Config REI histórica distinta a la vigente

- **Dado** asientos concepto 13 sobre cuentas sin `ajuste_infla_pc='Si'` o con contrapartida distinta a paramatriz 63
- **Cuando** se ejecuta `rei_recalculo`
- **Entonces** se reporta desalineación de config con referencia H44

---

### Requirement: AUD-LECT-15 — Check concepto_no_normal

El check `concepto_no_normal` DEBE detectar conceptos con `tipo_concepto_asiento <> 'Normal'` usados en imputaciones o creados sin ese tipo, incluyendo inconsistencias entre `tipo_concepto` y `tipo_concepto_asiento`. DEBE mapear H37, H38.

#### Scenario: Concepto manual invisible para imputar

- **Dado** un concepto nuevo con `tipo_concepto='Manual'` y sin `tipo_concepto_asiento='Normal'` (H37)
- **Cuando** se ejecuta `concepto_no_normal`
- **Entonces** se reporta el `id_concepto_asiento` y la inconsistencia de tipos

---

### Requirement: AUD-LECT-16 — Filtros de ejecución

La orquestación DEBE aceptar filtros obligatorios `base_empresa` e `id_ejercicio`, y opcionales `id_periodo`, `check_ids[]`, `fecha_desde`, `fecha_hasta`. Los filtros DEBEN aplicarse de forma consistente en todos los checks que los soporten.

#### Scenario: Auditoría acotada a un periodo

- **Dado** `id_ejercicio=5` e `id_periodo=3`
- **Cuando** se ejecuta corrida con esos filtros
- **Entonces** los checks de periodo evalúan solo movimientos de ese periodo y el resumen indica el alcance aplicado

---

### Requirement: AUD-LECT-17 — Normalización de tipos legacy

Toda lectura de campos legacy DEBE normalizar valores con `core.utils.administranet_types` (`to_int_or_none`, `to_date_or_none`, `to_decimal_or_none`, `str_or_default`) antes de comparar o serializar resultados. NO DEBE enviar strings numéricos sin convertir ni strings vacíos en campos DATE.

#### Scenario: Comparación decimal con tolerancia

- **Dado** saldos leídos como string desde MySQL
- **Cuando** se calcula `delta` para un check de saldo
- **Entonces** la comparación usa `Decimal` normalizado y respeta `tolerancia_decimal` de la política

---

### Requirement: AUD-LECT-18 — Reproducibilidad y config_hash

Cada corrida DEBE resolver la política efectiva (`default global → override base_empresa`), calcular un `config_hash` determinista del snapshot JSON de parámetros, persistir ese hash en el registro de corrida y adjuntarlo a cada `AuditResult`. Re-ejecutar con la misma política y datos DEBE producir resultados equivalentes.

#### Scenario: Corrida reproducible

- **Dado** una corrida previa con `config_hash` registrado
- **Cuando** se repite la corrida sin cambios en política ni datos legacy
- **Entonces** los conteos y diferencias por check coinciden con la corrida anterior

#### Scenario: Cambio de política altera resultados

- **Dado** una corrida con `tratamiento_anulados=excluir`
- **Cuando** se cambia la política a `incluir_neutralizado` y se re-ejecuta
- **Entonces** el nuevo `config_hash` difiere y los resultados pueden cambiar de forma trazable

---

### Requirement: AUD-LECT-19 — UI tablero y export (canon reports)

La UI en `/contabilidad/auditoria/` DEBE presentar un tablero verde/rojo por check, filtros por empresa/ejercicio/periodo, drill-down al comprobante y export CSV/Excel reutilizando `reports/services/export_service.py` y plantillas `reports/dashboard_detail.html` + includes. NO DEBE usar como referencia visual `ventas/objetivos-venta/` ni `ventas/presupuestos/`.

#### Scenario: Tablero con diferencias de saldo

- **Dado** una corrida con diferencias en `saldo_ejercicio_vs_diario`
- **Cuando** el usuario abre el tablero
- **Entonces** ve tarjeta roja con conteo, lista de cuentas con `|delta| > tolerancia` y enlace de drill-down

#### Scenario: Export de corrida

- **Dado** una corrida completada
- **Cuando** el usuario exporta resultados
- **Entonces** el archivo incluye `config_hash`, fecha dd/MM/yyyy y detalle de diferencias por check

---

### Requirement: AUD-LECT-20 — Permisos y errores controlados

La ejecución de auditoría DEBE exigir permiso Synap de lectura contable dedicado. Si falla la conexión MySQL o un check individual, el sistema DEBE registrar el error en `AuditResult.error` del check afectado, continuar con los demás checks cuando sea posible, y NO DEBE enmascarar fallos como `ok=true`.

#### Scenario: Empresa sin pool MySQL

- **Dado** un `base_empresa` sin conexión configurada
- **Cuando** se intenta ejecutar auditoría
- **Entonces** la corrida falla con mensaje claro en español y sin escrituras parciales

#### Scenario: Fallo aislado de un check

- **Dado** un check cuya consulta SQL excede timeout
- **Cuando** se ejecuta corrida completa
- **Entonces** ese check reporta `ok=false` y `error` descriptivo; los demás checks completan si sus consultas son válidas

---

### Requirement: AUD-LECT-21 — Check comprobante_compra_pago_sin_asiento

El check `comprobante_compra_pago_sin_asiento` DEBE detectar comprobantes de `cuentaproveedor` con contabilidad activa en sucursal (`sucursales.cont='Si'`) que carecen de filas en `cont_asiento` enlazadas por `cuentaproveedor.CodigoMovimiento = cont_asiento.codigo_movimiento`. DEBE evaluar tipos `FA`, `FC` (facturas de compra, `id_concepto_asiento=3`) y `OP` (orden de pago, `id_concepto_asiento=7`); `FB`/`FM` se contemplan si existieran (en `administranet89` no hay). DEBE excluir comprobantes anulados (`Anulado='Si'`), comprobantes de sucursales con `sucursales.cont<>'Si'` y, **críticamente, los registros con `CodigoMovimiento=0`** (marcadores de anulación, `Detalle="Anulacion - …"`, `codigo_movimiento_anul` seteado — ver AUD-LECT-23), que NO son asientos faltantes. El subquery de `cont_asiento` DEBE excluir `codigo_movimiento=0` (asientos espurios). DEBE mapear H51, H52. Referencia empírica: 331 huérfanos linkables (FA 147, FC 27, OP 157). NO DEBE escribir en legacy.

#### Scenario: Comprobante sin asiento detectado

- **Dado** una factura de compra `TipoComprobante='FA'` no anulada con `CodigoMovimiento` asignado, sucursal con `cont='Si'` y sin filas en `cont_asiento` para ese `codigo_movimiento` (H51/H52)
- **Cuando** se ejecuta `comprobante_compra_pago_sin_asiento`
- **Entonces** el check reporta `ok=false`, incluye `CodigoMovimiento`, `TipoComprobante`, `NroComprobante`, `CodSucursal`, `ImporteCompra` y referencia `H51` o `H52`

#### Scenario: Comprobante con asiento OK

- **Dado** una orden de pago `TipoComprobante='OP'` con al menos un renglón en `cont_asiento` para su `CodigoMovimiento`
- **Cuando** se ejecuta `comprobante_compra_pago_sin_asiento`
- **Entonces** el comprobante no aparece en `diferencias` y el check contribuye a `ok=true`

#### Scenario: Sucursal no contable excluida

- **Dado** un comprobante de compra guardado en sucursal cuyo `sucursales.cont<>'Si'`
- **Cuando** se ejecuta `comprobante_compra_pago_sin_asiento`
- **Entonces** el comprobante queda fuera del alcance del check aunque no tenga asiento

#### Scenario: Comprobante anulado excluido

- **Dado** un comprobante con `Anulado='Si'` y sin asiento contable
- **Cuando** se ejecuta `comprobante_compra_pago_sin_asiento`
- **Entonces** no se reporta como diferencia

#### Scenario: Registro de anulación (CodigoMovimiento=0) excluido

- **Dado** un registro de `cuentaproveedor` con `CodigoMovimiento=0`, `Detalle="Anulacion - OP - …"` y `codigo_movimiento_anul` seteado (marcador de anulación de un comprobante original)
- **Cuando** se ejecuta `comprobante_compra_pago_sin_asiento`
- **Entonces** NO se reporta como comprobante sin asiento (no es un huérfano linkable)

---

### Requirement: AUD-LECT-24 — Check comprobante_venta_cobranza_sin_asiento

El check `comprobante_venta_cobranza_sin_asiento` DEBE detectar comprobantes de **`cuentacliente`** (ventas y cobranzas) con `CodigoMovimiento>0` que carecen de filas en `cont_asiento` enlazadas por `cuentacliente.CodigoMovimiento = cont_asiento.codigo_movimiento`. DEBE evaluar tipos de factura de venta `FA`, `FB`, `FC`, `FE`, `FM` (concepto típico **1** Venta) y `REC` (concepto **5** Cobranza). DEBE excluir anulados (`Anulado='Si'`) y marcadores `CodigoMovimiento=0`. DEBE aplicar gating de contabilidad **solo** `punto_venta.cont='Si'` (clientes); NO DEBE usar `sucursales.cont` como criterio para `cuentacliente` (ese gating aplica a proveedores/`cuentaproveedor`). NO DEBE mezclar filas de `cuentaproveedor` (compra). DEBE mapear H54 (venta) y H55 (REC). NO DEBE escribir en legacy (la regeneración es REC-20 en el motor de corrección). Fuera de alcance de este check: integridad de anulación venta/cobranza, NC/ND.

#### Scenario: Factura de venta sin asiento

- **Dado** un `FB` en `cuentacliente` no anulado, `CodigoMovimiento>0`, PV o sucursal con contabilidad activa, sin filas en `cont_asiento`
- **Cuando** se ejecuta `comprobante_venta_cobranza_sin_asiento`
- **Entonces** se reporta el `CodigoMovimiento` con referencia `H54`

#### Scenario: REC sin asiento

- **Dado** un `REC` en `cuentacliente` no anulado, `CodigoMovimiento>0`, con gating contable activo, sin filas en `cont_asiento`
- **Cuando** se ejecuta `comprobante_venta_cobranza_sin_asiento`
- **Entonces** se reporta con referencia `H55`

#### Scenario: Marcador CodigoMovimiento=0 excluido

- **Dado** un registro de `cuentacliente` con `CodigoMovimiento=0` (marcador de anulación)
- **Cuando** se ejecuta `comprobante_venta_cobranza_sin_asiento`
- **Entonces** NO se reporta como huérfano

---

### Requirement: AUD-LECT-23 — Check integridad_anulacion_compra_pago

El check `integridad_anulacion_compra_pago` DEBE validar que toda anulación de compra/pago esté correctamente registrada en partida doble, **solo para comprobantes cuya `Fecha` cae en el ejercicio (y período opcional) del tablero**. Para cada comprobante original con `Anulado='Si'`, DEBE verificar: (a) que exista un registro marcador en `cuentaproveedor` con `CodigoMovimiento=0` y `codigo_movimiento_anul = CodigoMovimiento` del original; (b) que las filas del asiento original (`cont_asiento.codigo_movimiento = CodigoMovimiento`) estén marcadas `anulado='Si'`; (c) que exista un **contra-asiento** (`cont_asiento.codigo_movimiento_anul = CodigoMovimiento` del original, `id_concepto_asiento IN (4,8)`, `anulado='No'`) cuyos importes **inviertan** exactamente el asiento original (Σdebe/Σhaber espejados). DEBE reportar como diferencia toda anulación incompleta (falta contra-asiento, o contra no balancea con el original). DEBE mapear la sección §6.8 del informe. NO DEBE escribir en legacy.

#### Scenario: Anulación correcta (partida doble completa)

- **Dado** un comprobante original `Anulado='Si'` con asiento original marcado `anulado='Si'` y un contra-asiento (concepto 4 u 8) con `codigo_movimiento_anul` al original e importes invertidos
- **Cuando** se ejecuta `integridad_anulacion_compra_pago`
- **Entonces** la anulación no aparece en `diferencias`

#### Scenario: Anulación sin contra-asiento

- **Dado** un comprobante original `Anulado='Si'` cuyo asiento original está marcado `anulado='Si'` pero NO existe contra-asiento con `codigo_movimiento_anul` al original
- **Cuando** se ejecuta `integridad_anulacion_compra_pago`
- **Entonces** se reporta la anulación incompleta con el `CodigoMovimiento` original

---

### Requirement: AUD-LECT-22 — Check asiento_compra_pago_desbalanceado_saldo_null

El check `asiento_compra_pago_desbalanceado_saldo_null` DEBE evaluar asientos vinculados a comprobantes de compra/pago (`cuentaproveedor.TipoComprobante IN ('FA','FC','OP')`, comprobante no anulado, `codigo_movimiento<>0`) cuya **`Fecha` cae en el ejercicio (y período opcional) del tablero**, enlazando `cont_asiento.id_ejercicio` con `cont_ejercicio` y agrupando por `codigo_movimiento`. DEBE marcar asientos donde `|SUM(debe_asiento) − SUM(haber_asiento)| > tolerancia_decimal` o donde exista al menos un renglón con `saldo_asiento IS NULL`. DEBE respetar `tratamiento_anulados` de la política. DEBE mapear H53, H10, H17. NO DEBE escribir en legacy.

#### Scenario: Asiento desbalanceado detectado

- **Dado** un `codigo_movimiento` de factura de compra con Σdebe − Σhaber fuera de `tolerancia_decimal`
- **Cuando** se ejecuta `asiento_compra_pago_desbalanceado_saldo_null`
- **Entonces** se reporta el `codigo_movimiento`, `sum_debe`, `sum_haber`, `delta` y referencia `H53`

#### Scenario: Asiento con saldo_asiento NULL

- **Dado** un asiento de orden de pago con renglones donde `saldo_asiento IS NULL` por update parcial sin fila de saldo (H53/H17)
- **Cuando** se ejecuta `asiento_compra_pago_desbalanceado_saldo_null`
- **Entonces** se reporta el `codigo_movimiento`, cantidad de renglones con saldo NULL y referencia `H53`

#### Scenario: Asiento balanceado y saldos completos

- **Dado** un asiento de compra/pago con Σdebe ≈ Σhaber dentro de tolerancia y sin `saldo_asiento` NULL
- **Cuando** se ejecuta `asiento_compra_pago_desbalanceado_saldo_null`
- **Entonces** no se incluye en `diferencias`

#### Scenario: Comprobante anulado con contra-asiento (neutralizado)

- **Dado** un comprobante anulado cuyo asiento original (`anulado='Si'`) tiene su contra-asiento reversante (`anulado='No'`)
- **Cuando** se ejecuta `asiento_compra_pago_desbalanceado_saldo_null` con `tratamiento_anulados=incluir_neutralizado` (default)
- **Entonces** original y contra se consideran juntos (se netean) y no se reporta un falso desbalance

---

## Referencias

- Hallazgos: `docs/general/AUDITORIA_IMPUTACION_CONTABILIDAD_VB6.md` (H01–H53, §6.6–6.9)
- Arquitectura: `docs/general/PROPUESTA_ARQUITECTURA_AUDITORIA_RECALCULO_CONTABILIDAD_SYNAP.md` §4
- Patrón reconciliación: `reports/services/reconciliation_saldo_pedido_proveedor.py`
