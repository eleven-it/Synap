# Spec — Recálculo y corrección controlada de imputación contable

**Capability:** `contabilidad-recalculo-correccion`  
**Change:** `contabilidad-auditoria-recalculo`  
**Estado:** Propuesto

---

## Purpose

Habilitar un motor de **corrección transaccional** sobre tablas derivadas `cont_*` del MySQL legacy, con dry-run obligatorio, backup previo, detección de concurrencia, log de auditoría y cumplimiento de políticas por empresa. La fuente de verdad DEBE ser `cont_asiento`; las tablas de saldo son reconstruibles. Regla de oro: ninguna escritura hasta validar auditoría en lectura; apply solo bajo salvaguardas de producción.

---

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

### Requirement: REC-02 — Escritura solo en producción con permiso reforzado

`apply` DEBE verificar `ENVIRONMENT=production` (o `produccion` según convención del proyecto) y permiso Synap dedicado de corrección contable reforzado. Fuera de producción, `apply` MUST NOT estar disponible aunque el usuario tenga permiso. `dry_run` DEBE estar disponible en todos los entornos con permiso de lectura/auditoría.

#### Scenario: Apply bloqueado en desarrollo

- **Dado** `ENVIRONMENT=development` y usuario con permiso de corrección
- **Cuando** intenta confirmar apply
- **Entonces** la operación es rechazada y no se escribe en legacy

#### Scenario: Apply permitido en producción

- **Dado** `ENVIRONMENT=production`, permiso reforzado y dry-run aprobado
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

1. `asiento_balanceado` — solo diagnóstico; NO auto-corrige montos de negocio sin regla explícita  
2. `concepto_anulacion_incoherente` — UPDATE puntual de `id_concepto_asiento`  
3. `cuentas_sin_fila_saldo` — INSERT de filas faltantes con saldo recalculado  
4. `saldo_ejercicio_vs_diario` / `saldo_periodo_vs_diario` — recompute maestro de tablas derivadas desde `cont_asiento`  
5. `rei_recalculo` — regeneración caso a caso; requiere aprobación explícita adicional  

NO DEBE ejecutar paso 4 antes de completar 2–3 cuando el plan los incluya.

#### Scenario: Recompute maestro post-inserts

- **Dado** un plan con filas faltantes y saldos desincronizados
- **Cuando** apply ejecuta el lote
- **Entonces** primero INSERT de filas saldo, luego recálculo de saldos derivados, respetando el orden

---

### Requirement: REC-08 — Estrategias de corrección por tipo

| Tipo detectado | Acción permitida | Auto-apply |
|----------------|------------------|------------|
| Saldos derivados desincronizados | Recalcular desde `cont_asiento` | Sí (paso 4) |
| Filas saldo faltantes | INSERT con saldo recalculado | Sí (paso 3) |
| Concepto anulación erróneo | UPDATE a `id_concepto_anul` del original | Sí (paso 2) |
| Asiento desbalanceado centavo | Según `politica_centavo`; re-derivar saldos | Condicional |
| REI mal calculado | Anular/regenerar REI | Solo manual/aprobación |
| Cierre PyG / cuentas resultado | Marcar revisión manual | NO auto-corrige |

#### Scenario: Corrección de concepto de anulación

- **Dado** contra-asiento con concepto incorrecto (H05) detectado por auditoría
- **Cuando** apply ejecuta paso 2
- **Entonces** actualiza `id_concepto_asiento` al `id_concepto_anul` esperado y registra log

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

El servicio DEBE poder recomputar **desde cero** (reconstrucción total, no incremento) las tablas derivadas `cont_ejercicio_saldo_cta` y `cont_periodo_saldo_cta` a partir de los renglones de `cont_asiento`, aplicando la regla de signo según `cont_pc.saldo_pc` (**Deudor:** `+debe − haber`; **Acreedor:** `+haber − debe`). Con `tratamiento_anulados=incluir_neutralizado` (default validado) DEBE **sumar TODAS las filas** —incluidas las marcadas `anulado='Si'`—, porque cada anulación tiene su **contra-asiento reversante** (`anulado='No'`) y ambos se netean; excluir solo las `anulado='Si'` dejaría el contra sin su original y desbalancearía (validado empíricamente: 31 vs 6 cuentas divergentes). **Modelo de arrastre validado en `administranet89`: NO hay arrastre de apertura** — `saldo_ejercicio_cta` = Σ firmada de los movimientos del propio ejercicio (con arrastre 1/2/3 las diferencias empeoraban de 25 a 109). El servicio DEBE reproducir el modelo sin-arrastre salvo que una empresa documente lo contrario (parámetro configurable). Ejecución de referencia: 83 cuentas/ejercicio recompuestas, idempotente en re-corrida. DEBE respetar `alcance_recompute`, `ejercicios_cerrados` y el flujo dry-run → backup → transacción única (REC-01, REC-03, REC-04). DEBE mapear H53, H10, H17, H33.

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

---

### Requirement: REC-18 — Regeneración idempotente de asientos faltantes de compras/pagos

El servicio DEBE poder regenerar el asiento contable de un comprobante detectado por `comprobante_compra_pago_sin_asiento` (AUD-LECT-21). DEBE **reconstruir los insumos desde las tablas persistidas** (`cuentaproveedor`, `stock`, `percep_prov`, `transferencia`, `otro_egreso`, `caja`, retenciones…), porque `generar_asiento_cont` (VB6) los tomaba de temporales de sesión inexistentes; la lógica de cuentas portada está validada contra los asientos existentes (facturas 100 %). DEBE usar `id_concepto_asiento=3` para `FA/FC` (y `FB/FM` si existieran) y `7` para `OP`. DEBE **reusar el `CodigoMovimiento` existente** del comprobante (preserva el enlace; NO asignar `codmov` nuevo) y asignar **`nro_asiento` nuevo** del contador `cont_ejercicio.nro_asiento_ejercicio` del ejercicio que contiene la **fecha original** del comprobante, con locking pesimista; la fecha del asiento DEBE ser la **original**. El alcance de esta capacidad son los **331 huérfanos linkables** (`CodigoMovimiento>0`); los **86 registros de anulación** (`CodigoMovimiento=0`) quedan **fuera** (requieren asignación de `codmov` nuevo, tratamiento separado). DEBE ser **idempotente**: si ya existen renglones en `cont_asiento` para el `codigo_movimiento`, NO DEBE duplicar. Un **desbalance residual** de reconstrucción menor o igual a un umbral configurable (referencia: $1,00) DEBE imputarse a la **cuenta de diferencias/redondeo** (`cont_pc` 'Redondeo'; en `administranet89` `id_pc=300`) — ajuste tipo `Balancea_asiento` extendido; por encima del umbral DEBE bloquearse el caso. El `apply` DEBE ejecutarse solo con `ENVIRONMENT=production` (o `produccion`) y permiso reforzado; el `dry-run` es siempre solo lectura. DEBE incluir backup previo (salvo entornos de testing), transacción (InnoDB) por asiento con rollback y log (REC-06), y marcar cada renglón regenerado de forma trazable (p. ej. `desc_renglon_asiento`) para permitir reversión. Tras regenerar asiento, DEBE encadenar reconstrucción de saldos afectados (REC-17). DEBE mapear H51, H52. Ejecución de referencia en testing: 331 regenerados (1.012 renglones), 1 con ajuste de redondeo, 0 bloqueados; verificación 0 huérfanos y validaciones 100%.

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

#### Scenario: Apply bloqueado fuera de producción

- **Dado** `ENVIRONMENT=development` y comprobante sin asiento detectado
- **Cuando** se intenta apply de regeneración
- **Entonces** la operación es rechazada sin escritura en legacy

#### Scenario: Regeneración encadena reconstrucción de saldos

- **Dado** apply exitoso de regeneración de orden de pago (`OP`)
- **Cuando** finaliza la transacción
- **Entonces** los saldos de cuentas afectadas quedan coherentes con el diario (recompute o paso encadenado REC-17) y el log registra ambas operaciones

---

## Referencias

- Arquitectura §5–§6: `docs/general/PROPUESTA_ARQUITECTURA_AUDITORIA_RECALCULO_CONTABILIDAD_SYNAP.md`
- Hallazgos: H01–H06, H10, H17, H33, H34, H41, H45, H50, H51–H53
- Compras/pagos: `docs/general/AUDITORIA_IMPUTACION_CONTABILIDAD_VB6.md` §6
- Capabilities relacionadas: `contabilidad-auditoria-lectura`, `contabilidad-politicas-configurables`
- Escritura legacy: app `legacy_db`; DDL log: `core/services/legacy_mysql_schema/catalog.py`
