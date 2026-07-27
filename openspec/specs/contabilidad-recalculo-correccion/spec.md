# contabilidad-recalculo-correccion Specification

## Purpose

Habilitar un motor de **corrección transaccional** sobre tablas derivadas `cont_*` del MySQL legacy, con dry-run obligatorio, backup previo, detección de concurrencia, log de auditoría y cumplimiento de políticas por empresa. La fuente de verdad DEBE ser `cont_asiento`; las tablas de saldo son reconstruibles. Regla de oro: ninguna escritura hasta validar auditoría en lectura; apply solo con permiso reforzado y confirmación explícita (disponible también en development para pruebas).

*Archivado desde el cambio OpenSpec `contabilidad-auditoria-recalculo` (19/07/2026).*


## Requirements

### Requirement: REC-01 — Separación dry-run vs apply

El servicio `legacy_db/services/cont_recalculo_service.py` DEBE exponer dos modos: `dry_run` (plan de cambios, 100% solo lectura en legacy) y `apply` (escritura transaccional). `dry_run` NO DEBE emitir DML alguno. `apply` NO DEBE ejecutarse sin un `dry_run` previo compatible (mismo alcance, política y hash de plan) dentro de la ventana de validez definida en design.

#### Scenario: Dry-run sin escrituras

- **Dado** diferencias detectadas en `saldo_ejercicio_vs_diario`
- **Cuando** se ejecuta `dry_run` para un ejercicio
- **Entonces** se genera plan `(tabla, clave, valor_anterior, valor_nuevo, delta)` sin modificar MySQL legacy

#### Scenario: Apply sin dry-run previo

- **Dado** un operador con permiso de corrección
- **Cuando** intenta `apply` directamente sin plan dry-run válido
- **Entonces** el sistema rechaza la operación con mensaje en español

---

### Requirement: REC-02 — Escritura con permiso reforzado (cualquier entorno)

`apply` y `rollback_lote` DEBEN verificar permiso Synap dedicado de corrección contable (`contabilidad.auditoria.corregir`). NO DEBEN exigir `ENVIRONMENT=production`: deben poder ejecutarse también en `development` (y otros entornos) para pruebas, siempre con el mismo permiso, backup previo y confirmación UI (checkbox; sin token escrito). `dry_run` DEBE estar disponible en todos los entornos con permiso de lectura/auditoría.

#### Scenario: Apply rechazado sin permiso

- **Dado** cualquier `ENVIRONMENT` y usuario sin permiso de corrección
- **Cuando** intenta confirmar apply
- **Entonces** la operación es rechazada y no se escribe en legacy

#### Scenario: Apply permitido en development con permiso

- **Dado** `ENVIRONMENT=development`, permiso reforzado y dry-run aprobado
- **Cuando** confirma apply explícitamente
- **Entonces** inicia flujo transaccional con backup previo

---

### Requirement: REC-03 — Backup previo obligatorio

Antes de cualquier `apply`, el sistema DEBE crear backup de todas las tablas afectadas en tablas `*_bkp_<timestamp>` o mecanismo equivalente documentado en design, registrando metadatos (`lote_id`, tablas, timestamp dd/MM/yyyy HH:mm, usuario). Sin backup exitoso NO DEBE iniciarse la transacción de corrección.

#### Scenario: Backup exitoso antes de recálculo

- **Dado** un plan que afecta `cont_ejercicio_saldo_cta` y `cont_periodo_saldo_cta`
- **Cuando** se confirma apply
- **Entonces** existen tablas backup con sufijo timestamp y el log referencia esas tablas antes del primer UPDATE

#### Scenario: Fallo en backup aborta apply

- **Dado** un error de espacio o permisos al crear backup
- **Cuando** se intenta apply
- **Entonces** la operación se aborta sin DML en tablas productivas

---

### Requirement: REC-04 — Transacción única con rollback

Todo `apply` DEBE ejecutarse en una única transacción MySQL por `lote_id`. Ante cualquier error, validación fallida o detección de concurrencia, DEBE hacer `ROLLBACK` completo sin dejar estados intermedios (corrige raíz H01, H03, H41, H45).

#### Scenario: Error a mitad de lote

- **Dado** un apply con múltiples UPDATE de saldos
- **Cuando** falla el tercer UPDATE por constraint
- **Entonces** ningún cambio del lote permanece aplicado

---

### Requirement: REC-05 — Detección de concurrencia y re-validación

Dentro de la transacción, antes de cada escritura o grupo coherente, el servicio DEBE re-ejecutar la validación del check correspondiente (segunda lectura) y comparar con el plan dry-run. Si los valores actuales difieren (otro proceso VB6/Synap modificó datos), DEBE abortar con error de concurrencia. Donde aplique contadores (`nro_asiento_ejercicio`, `codmov`), DEBE usar locking pesimista según design (mitiga H06).

#### Scenario: Concurrencia detectada en saldo

- **Dado** un plan dry-run con `saldo_ejercicio_cta=1000` para una cuenta
- **Cuando** otro usuario modifica ese saldo a `1100` antes del apply
- **Entonces** la re-validación falla, se hace rollback y se informa conflicto de concurrencia

#### Scenario: Re-validación exitosa

- **Dado** datos sin cambios desde el dry-run
- **Cuando** apply ejecuta re-validación intra-transacción
- **Entonces** procede la escritura en el orden seguro definido

---

### Requirement: REC-06 — Log de auditoría cont_audit_correccion

Cada mutación aplicada DEBE registrarse en log `cont_audit_correccion` (DDL vía `core/services/legacy_mysql_schema/catalog.py` cuando se apruebe), con campos mínimos: `lote_id`, `base_empresa`, `check_id`, `tabla`, `clave` (p. ej. `id_pc`, `id_ejercicio`), `valor_anterior`, `valor_nuevo`, `usuario`, `fecha`, `config_hash`, `dry_run_id`. Fechas en UI DEBEN mostrarse dd/MM/yyyy.

#### Scenario: Trazabilidad por lote

- **Dado** un apply completado con `lote_id=L20260718-001`
- **Cuando** un auditor consulta el log
- **Entonces** ve todas las filas modificadas con valores antes/después y usuario responsable

---

### Requirement: REC-07 — Orden seguro de ejecución

El motor DEBE aplicar correcciones en este orden fijo salvo bloqueo explícito documentado:

1. `comprobante_compra_pago_sin_asiento` / `comprobante_venta_cobranza_sin_asiento` — regeneración de asientos huérfanos (REC-18 / REC-20)  
2. `integridad_anulacion_compra_pago` — reparación de anulaciones incompletas (REC-19)  
3. `concepto_anulacion_incoherente` — UPDATE puntual de `id_concepto_asiento`  
4. `cuentas_sin_fila_saldo` — INSERT de filas faltantes con saldo recalculado  
5. `saldo_ejercicio_vs_diario` / `saldo_periodo_vs_diario` — recompute maestro de tablas derivadas desde `cont_asiento`  
6. `rei_recalculo` — regeneración caso a caso; requiere aprobación explícita adicional  

NO DEBE ejecutar paso 5 antes de completar 2–4 cuando el plan los incluya. NO DEBE ejecutar paso 2 antes de completar paso 1 cuando el plan incluya regeneración de huérfanos para el mismo comprobante.

#### Scenario: Recompute maestro post-inserts

- **Dado** un plan con filas faltantes y saldos desincronizados
- **Cuando** apply ejecuta el lote
- **Entonces** primero INSERT de filas saldo, luego recálculo de saldos derivados, respetando el orden

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

#### Scenario: Corrección de concepto de anulación

- **Dado** contra-asiento con concepto incorrecto (H05) detectado por auditoría
- **Cuando** apply ejecuta paso 3
- **Entonces** actualiza `id_concepto_asiento` al `id_concepto_anul` esperado y registra log

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

#### Scenario: Cierre resultado no auto-corregido

- **Dado** diferencias en `cierre_resultado_no_cero`
- **Cuando** se solicita apply genérico
- **Entonces** esas cuentas quedan excluidas del apply automático y permanecen para revisión manual

---

### Requirement: REC-09 — Respeto a ejercicios cerrados

Si la política resuelta tiene `ejercicios_cerrados=no_tocar` (default), `apply` NO DEBE modificar datos de ejercicios/periodos marcados cerrados. Con `permitir_con_reapertura`, apply DEBE exigir permiso reforzado adicional y confirmación explícita registrada en log.

#### Scenario: Ejercicio cerrado bloqueado

- **Dado** `ejercicios_cerrados=no_tocar` y ejercicio 2023 cerrado
- **Cuando** el plan incluye cambios en 2023
- **Entonces** apply rechaza el lote o excluye ese ejercicio con error claro

#### Scenario: Reapertura controlada

- **Dado** `ejercicios_cerrados=permitir_con_reapertura` y confirmación explícita del operador
- **Cuando** apply procede sobre ejercicio cerrado en producción
- **Entonces** el log registra flag de reapertura y usuario autorizador

---

### Requirement: REC-10 — Alcance según alcance_recompute

El dry-run y apply DEBEN respetar `alcance_recompute` de la política: `ejercicio_activo`, `ejercicio_seleccionado` o `historico` (por lotes). NO DEBE procesar ejercicios fuera del alcance seleccionado.

#### Scenario: Alcance ejercicio activo

- **Dado** `alcance_recompute=ejercicio_activo` y ejercicio activo id=7
- **Cuando** se genera dry-run
- **Entonces** el plan solo incluye filas de ejercicio 7 aunque existan diferencias en otros ejercicios

---

### Requirement: REC-11 — Idempotencia

Re-ejecutar `apply` sobre datos ya corregidos DEBE resultar en plan vacío o no-op: segunda corrida NO DEBE alterar valores ni duplicar filas. Tras apply exitoso, los checks `saldo_*_vs_diario` DEBEN quedar en verde dentro de tolerancia.

#### Scenario: Segundo apply sin cambios

- **Dado** un lote ya aplicado que dejó saldos coherentes
- **Cuando** se repite dry-run y apply con misma política
- **Entonces** dry-run reporta cero cambios y apply no modifica filas

#### Scenario: Piloto post-recálculo

- **Dado** apply exitoso del recompute maestro
- **Cuando** se ejecuta auditoría `saldo_ejercicio_vs_diario`
- **Entonces** `ok=true` para todas las cuentas dentro de `tolerancia_decimal`

---

### Requirement: REC-12 — Normalización de tipos en escritura

Toda escritura legacy DEBE pasar por capa `legacy_db` normalizando con `administranet_types` (`to_int_or_none`, `to_date_or_none`, `to_decimal_or_none`, `str_or_default`). NO DEBE enviar strings vacíos en DATE ni números sin convertir (mitiga H50).

#### Scenario: INSERT fila saldo con tipos correctos

- **Dado** un INSERT de `cont_ejercicio_saldo_cta` generado por recálculo
- **Cuando** apply persiste la fila
- **Entonces** los campos numéricos y fechas cumplen tipos AdministraNET documentados

---

### Requirement: REC-13 — Dry-run reporte de impacto

`dry_run` DEBE producir reporte exportable con: número de filas afectadas por tabla, cuentas (`id_pc`) impactadas, monto total de ajuste por signo, `config_hash`, checks incluidos y SQL/operación abstracta que apply ejecutaría. DEBE ser aprobable por área contable antes de apply.

#### Scenario: Reporte previo a aprobación

- **Dado** desincronización masiva de saldos en ejercicio 2024
- **Cuando** contabilidad ejecuta dry-run
- **Entonces** recibe reporte con totales y detalle por cuenta sin cambios en DB

---

### Requirement: REC-14 — Rollback por lote_id

El sistema DEBE permitir reversión de un `lote_id` aplicado restaurando filas desde tablas backup asociadas, en transacción única, registrando evento de rollback en log. Rollback DEBE exigir las mismas salvaguardas de permiso que apply.

#### Scenario: Reversión exitosa

- **Dado** lote `L20260718-001` con backup consistente
- **Cuando** un operador autorizado ejecuta rollback del lote
- **Entonces** los valores productivos vuelven al estado pre-apply y el log registra la reversión

#### Scenario: Rollback con backup incompleto

- **Dado** un lote cuyo backup fue purgado manualmente
- **Cuando** se intenta rollback
- **Entonces** la operación falla con error explícito y sin cambios parciales

---

### Requirement: REC-15 — Integración con política y config_hash

Dry-run y apply DEBEN invocar `resolver_politica(base_empresa)` y persistir el mismo `config_hash` en plan, log y respuesta API. Cambios de política entre dry-run y apply DEBEN invalidar el plan.

#### Scenario: Política modificada invalida plan

- **Dado** dry-run con `config_hash=H1`
- **Cuando** se cambia `tolerancia_decimal` antes del apply
- **Entonces** apply rechaza el plan obsoleto y exige nuevo dry-run

---

### Requirement: REC-16 — Casos borde y errores

El servicio DEBE manear sin crash: cuentas con `saldo_pc` NULL (abortar corrección de esa cuenta con log), planes vacíos, timeouts, locks de VB6 concurrentes, empresas sin política (usar default), y locale en formateo decimal independiente del servidor.

#### Scenario: Cuenta con saldo_pc NULL

- **Dado** una diferencia en cuenta cuyo `cont_pc.saldo_pc` es NULL
- **Cuando** apply intenta recalcular saldo
- **Entonces** excluye esa cuenta del apply automático, registra error en log y continúa con el resto si la política lo permite

#### Scenario: Empresa sin override de política

- **Dado** empresa sin fila en `PoliticaAuditoriaContable`
- **Cuando** se ejecuta dry-run
- **Entonces** usa defaults globales y genera `config_hash` coherente con POL-02

#### Scenario: Plan vacío

- **Dado** auditoría en verde para el alcance seleccionado
- **Cuando** se solicita dry-run
- **Entonces** reporta cero cambios y apply no tiene efecto

---

### Requirement: REC-17 — Reconstrucción total de saldos por cuenta

El servicio DEBE poder recomputar **desde cero** (reconstrucción total, no incremento) las tablas derivadas `cont_ejercicio_saldo_cta` y `cont_periodo_saldo_cta` a partir de los renglones de `cont_asiento`, aplicando la regla de signo según `cont_pc.saldo_pc` (**Deudor:** `+debe − haber`; **Acreedor:** `+haber − debe`). Con `tratamiento_anulados=incluir_neutralizado` (default) DEBE **sumar TODAS las filas** —incluidas las marcadas `anulado='Si'`—, porque cada anulación tiene su **contra-asiento reversante** (`anulado='No'`) y ambos se netean; excluir solo las `anulado='Si'` dejaría el contra sin su original y desbalancearía (validado empíricamente: 31 vs 6 cuentas divergentes). **Modelo de arrastre validado en `administranet89`: NO hay arrastre de apertura** — `saldo_ejercicio_cta` = Σ firmada de los movimientos del propio ejercicio (con arrastre 1/2/3 las diferencias empeoraban de 25 a 109). El servicio DEBE reproducir el modelo sin-arrastre salvo que una empresa documente lo contrario (parámetro configurable). Al reescribir `cont_asiento.saldo_asiento` (columna del informe VB6 `conta_libro_mayor.rpt` / `Conta_Info` 130) el servicio DEBE acumular todas las filas del ejercicio de la cuenta con la misma regla canónica (`incluir_neutralizado` por defecto). Pie (`cont_*_saldo_cta`), corrido y checks DEBEN quedar alineados con la política activa. Ejecución de referencia: 83 cuentas/ejercicio recompuestas, idempotente en re-corrida. DEBE respetar `alcance_recompute`, `ejercicios_cerrados` y el flujo dry-run → backup → transacción única (REC-01, REC-03, REC-04). DEBE mapear H53, H10, H17, H33.

#### Scenario: Dry-run de reconstrucción de saldos

- **Dado** saldos derivados desincronizados del diario por updates parciales (H53)
- **Cuando** se ejecuta dry-run de reconstrucción para un ejercicio
- **Entonces** el plan lista `(tabla, id_pc, id_ejercicio, id_periodo opcional, valor_anterior, valor_nuevo)` sin DML en legacy

#### Scenario: Apply con backup y transacción

- **Dado** dry-run aprobado de reconstrucción en `ENVIRONMENT=production` con permiso reforzado
- **Cuando** se confirma apply
- **Entonces** se crean tablas backup, se recomputan saldos en transacción única y se registran mutaciones en `cont_audit_correccion`

#### Scenario: Reconstrucción idempotente

- **Dado** un apply de reconstrucción ya exitoso
- **Cuando** se repite dry-run sobre el mismo alcance
- **Entonces** el plan reporta cero cambios

#### Scenario: Cuenta con saldo_pc NULL excluida

- **Dado** una cuenta imputable con `saldo_pc` NULL usada en movimientos
- **Cuando** apply intenta reconstruir saldos
- **Entonces** excluye esa cuenta del apply automático, registra error en log y continúa con el resto según política

#### Scenario: Corrido Libro Mayor incluye anulados

- **Dado** una cuenta con renglones `anulado='Si'` y política global `tratamiento_anulados=incluir_neutralizado` (default)
- **Cuando** se ejecuta `recalcular_saldo_asiento_cuenta` / `recalcular_libro_mayor`
- **Entonces** el saldo corrido suma también las filas anuladas (paridad Conta_Info) y el rebuild de `cont_ejercicio_saldo_cta` usa la misma regla; pie == último corrido

#### Scenario: Política explícita excluir omite anulados en pie y checks

- **Dado** una cuenta con renglones `anulado='Si'` y política global `tratamiento_anulados=excluir`
- **Cuando** se ejecuta dry-run de reconstrucción de saldos o `saldo_ejercicio_vs_diario`
- **Entonces** los renglones anulados no participan del saldo teórico del pie; el corrido del Libro Mayor sigue incluyendo anulados (regla fija Conta_Info)

---

### Requirement: REC-18 — Regeneración idempotente de asientos faltantes de compras/pagos

El servicio DEBE poder regenerar el asiento contable de un comprobante detectado por `comprobante_compra_pago_sin_asiento` (AUD-LECT-21). DEBE **reconstruir los insumos desde las tablas persistidas** (`cuentaproveedor`, `stock`, `percep_prov`, `transferencia`, `otro_egreso`, `caja`, retenciones…), porque `generar_asiento_cont` (VB6) los tomaba de temporales de sesión inexistentes; la lógica de cuentas portada está validada contra los asientos existentes (facturas 100 %). DEBE usar `id_concepto_asiento=3` para `FA/FC` (y `FB/FM` si existieran) y `7` para `OP`. DEBE **reusar el `CodigoMovimiento` existente** del comprobante (preserva el enlace; NO asignar `codmov` nuevo) y asignar **`nro_asiento` nuevo** del contador `cont_ejercicio.nro_asiento_ejercicio` del ejercicio que contiene la **fecha original** del comprobante, con locking pesimista; la fecha del asiento DEBE ser la **original**. El alcance de esta capacidad son los **331 huérfanos linkables** (`CodigoMovimiento>0`); los **86 registros de anulación** (`CodigoMovimiento=0`) quedan **fuera** (requieren asignación de `codmov` nuevo, tratamiento separado). DEBE ser **idempotente**: si ya existen renglones en `cont_asiento` para el `codigo_movimiento`, NO DEBE duplicar. Un **desbalance residual** de reconstrucción menor o igual a un umbral configurable (referencia: $1,00) DEBE imputarse a la **cuenta de diferencias/redondeo** (`cont_pc` 'Redondeo'; en `administranet89` `id_pc=300`) — ajuste tipo `Balancea_asiento` extendido; por encima del umbral DEBE bloquearse el caso. El `apply` DEBE ejecutarse con permiso reforzado (cualquier entorno, incluido development para pruebas); el `dry-run` es siempre solo lectura. DEBE incluir backup previo (salvo entornos de testing), transacción (InnoDB) por asiento con rollback y log (REC-06), y marcar cada renglón regenerado de forma trazable (p. ej. `desc_renglon_asiento`) para permitir reversión. Tras regenerar asiento, DEBE encadenar reconstrucción de saldos afectados (REC-17). DEBE mapear H51, H52. Ejecución de referencia en testing: 331 regenerados (1.012 renglones), 1 con ajuste de redondeo, 0 bloqueados; verificación 0 huérfanos y validaciones 100%.

#### Scenario: Regeneración de factura de compra sin asiento

- **Dado** una factura `TipoComprobante='FA'` con `CodigoMovimiento` huérfano detectada por auditoría (H51)
- **Cuando** se ejecuta dry-run de regeneración
- **Entonces** el plan detalla renglones propuestos en `cont_asiento`, `id_concepto_asiento=3`, `nro_asiento` estimado del ejercicio de la **fecha original**, `fecha` = fecha original del comprobante y **reuso del `codigo_movimiento` existente** (sin `codmov` nuevo)

#### Scenario: Registros de anulación (CodigoMovimiento=0) fuera de alcance

- **Dado** los 86 registros de anulación con `CodigoMovimiento=0`
- **Cuando** se ejecuta regeneración de asientos faltantes
- **Entonces** NO se regeneran en esta capacidad (quedan para tratamiento separado con asignación de `codmov` nuevo)

#### Scenario: Apply idempotente sin duplicar

- **Dado** un comprobante cuyo asiento fue regenerado exitosamente
- **Cuando** se reintenta apply de regeneración para el mismo `CodigoMovimiento`
- **Entonces** el plan está vacío o apply no inserta filas duplicadas

#### Scenario: Apply de regeneración exige permiso reforzado

- **Dado** un comprobante sin asiento detectado y usuario sin permiso de corrección
- **Cuando** se intenta apply de regeneración
- **Entonces** la operación es rechazada sin escritura en legacy

#### Scenario: Regeneración encadena reconstrucción de saldos

- **Dado** apply exitoso de regeneración de orden de pago (`OP`)
- **Cuando** finaliza la transacción
- **Entonces** los saldos de cuentas afectadas quedan coherentes con el diario (recompute o paso encadenado REC-17) y el log registra ambas operaciones

---

### Requirement: REC-20 — Regeneración idempotente de asientos faltantes de ventas/cobranzas

El servicio DEBE poder regenerar el asiento contable de un comprobante detectado por `comprobante_venta_cobranza_sin_asiento` (AUD-LECT-24). DEBE reconstruir insumos desde tablas persistidas (`cuentacliente`, `stock`, `percep_cli`, `caja`, `chequetercero`, `transferencia`, `retenciones`, `tc_comprobante`, `articulo.id_pc_vta`, matriz de cuentas). DEBE usar `id_concepto_asiento=1` (Venta) para `FA`/`FB`/`FC`/`FE`/`FM` y `5` (Cobranza) para `REC`. DEBE aplicar gating **`punto_venta.cont='Si'`** (no `sucursales.cont`). DEBE **reusar el `CodigoMovimiento` existente**, asignar **`nro_asiento` nuevo** del ejercicio de la fecha original, y marcar renglones con `"REGEN auditoria (bug factura/REC sin asiento)"`. DEBE ser idempotente (no duplicar si ya hay filas en `cont_asiento`). Desbalance ≤ umbral de redondeo → cuenta Redondeo (`id_pc=300` en referencia); por encima → omitir el caso del plan. DEBE incluir `comprobante_venta_cobranza_sin_asiento` en `CHECKS_INCLUIDOS` y ejecutar regeneración venta en el **mismo paso de orden** que REC-18 (antes de REC-19/saldos). Apply con permiso reforzado (cualquier entorno, incluido development). DEBE mapear H54/H55. Fuera de alcance: integridad de anulación venta/REC y NC/ND.

#### Scenario: Dry-run propone asiento de factura de venta

- **Dado** un `FA` en `cuentacliente` con `CodigoMovimiento` huérfano, PV con `cont='Si'`, reconstrucción balanceada
- **Cuando** se ejecuta dry-run de corrección
- **Entonces** el plan incluye INSERT en `cont_asiento` con `check_id=comprobante_venta_cobranza_sin_asiento`, `id_concepto_asiento=1` y reuso del `codigo_movimiento`

#### Scenario: Dry-run propone asiento de REC

- **Dado** un `REC` huérfano con medios de cobro persistidos y total coherente
- **Cuando** se ejecuta dry-run
- **Entonces** el plan incluye INSERT con `id_concepto_asiento=5` y referencia H55

#### Scenario: Apply idempotente venta sin duplicar

- **Dado** un plan REC-20 ya aplicado para un `CodigoMovimiento`
- **Cuando** se reintenta apply
- **Entonces** no se insertan filas duplicadas en `cont_asiento`

---

### Requirement: REC-19 — Reparación auto-apply de anulaciones incompletas compra/pago

El servicio `legacy_db/services/cont_recalculo_service.py` DEBE extender dry-run y apply para reparar hallazgos del check `integridad_anulacion_compra_pago` (AUD-LECT-23) en comprobantes `FA`/`FC`/`OP` con `Anulado='Si'` y `CodigoMovimiento>0`. DEBE incluir `integridad_anulacion_compra_pago` en `CHECKS_INCLUIDOS`. DEBE ampliar `TABLAS_BACKUP_PERMITIDAS` con `cuentaproveedor`. DEBE marcar renglones insertados en `cont_asiento` con `"REGEN auditoria (anulacion incompleta)"` en `desc_renglon_asiento` (o campo trazable equivalente ya usado por REC-18).

El mapeo problema → remedio DEBE ser:

| Problema | Remedio auto-apply |
|----------|-------------------|
| `falta_marcador_cuentaproveedor_cm0` | INSERT marcador en `cuentaproveedor` con `CodigoMovimiento=0`, `codigo_movimiento_anul` = cm original, `Detalle="Anulacion - <Tipo> - <Nro>"`, `Anulado='No'` |
| `asiento_original_no_anulado` | UPDATE `cont_asiento` SET `anulado='Si'` en renglones con `codigo_movimiento` = cm original |
| `falta_contra_asiento` | INSERT contra-asiento con `id_concepto_asiento` 4 (FA/FC) u 8 (OP), debe/haber invertidos respecto al original, **`codigo_movimiento` nuevo** del contador global, `codigo_movimiento_anul` = cm original, `anulado='No'`, `nro_asiento` nuevo |
| `contra_no_invierte_original` | **EXCLUIDO** del auto-apply (item `excluido=True`; revisión manual) |

El orden de apply DEBE ser: (1) regeneración huérfanos REC-18/REC-20 → (2) reparación anulaciones REC-19 → (3) concepto anulación REC-07 paso 3 → (4) INSERT filas saldo → (5) recompute saldos. DEBE respetar REC-01, REC-03, REC-04, REC-05, REC-06, REC-09, REC-11 y REC-12. DEBE mapear §6.8 de `AUDITORIA_IMPUTACION_CONTABILIDAD_VB6.md` y H53.

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
- **Y** el check `integridad_anulacion_compra_pago` no reporta problemas reparables para ese cm en el alcance

#### Scenario: Apply de anulación exige permiso reforzado

- **Dado** hallazgos de anulación incompleta y usuario sin permiso de corrección
- **Cuando** se intenta apply
- **Entonces** la operación es rechazada sin escritura en legacy (REC-02)

#### Scenario: Ejercicio cerrado excluido

- **Dado** política con `ejercicios_cerrados=no_tocar` y comprobante anulado en ejercicio cerrado
- **Cuando** se genera dry-run
- **Entonces** los items REC-19 de ese ejercicio quedan `excluido=True` según REC-09

---

## Referencias

- Arquitectura §5–§6: `docs/general/PROPUESTA_ARQUITECTURA_AUDITORIA_RECALCULO_CONTABILIDAD_SYNAP.md`
- Hallazgos: H01–H06, H10, H17, H33, H34, H41, H45, H50, H51–H53
- Compras/pagos: `docs/general/AUDITORIA_IMPUTACION_CONTABILIDAD_VB6.md` §6
- Capabilities relacionadas: `contabilidad-auditoria-lectura`, `contabilidad-politicas-configurables`
- Escritura legacy: app `legacy_db`; DDL log: `core/services/legacy_mysql_schema/catalog.py`
- Change REC-19: `openspec/changes/archive/2026-07-25-contabilidad-auditoria-anulaciones-apply/`
