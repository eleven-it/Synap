# contabilidad-politicas-configurables Specification

## Purpose

Modelar en la DB propia de Synap (no legacy) las decisiones de negocio que afectan cómo se arman los checks de auditoría y el alcance del recálculo posterior. Las políticas DEBEN resolverse por empresa, ser auditables en sus cambios y snapshottearse en cada corrida mediante `config_hash` para garantizar reproducibilidad explicativa.

*Archivado desde el cambio OpenSpec `contabilidad-auditoria-recalculo` (19/07/2026).*


## Requirements

### Requirement: POL-01 — Modelo PoliticaAuditoriaContable en DB Synap

El sistema DEBE persistir políticas en el modelo Django `PoliticaAuditoriaContable` dentro de `contabilidad_audit/models.py`, almacenado en PostgreSQL/Synap. NO DEBE escribir políticas en tablas MySQL legacy (`cont_*`). El modelo DEBE incluir los campos: `base_empresa`, `tratamiento_anulados`, `politica_centavo`, `prefijos_cuenta`, `ejercicios_cerrados`, `alcance_recompute`, `tolerancia_decimal`, `actualizado_por`, `actualizado_en`.

#### Scenario: Creación de override por empresa

- **Dado** una política global default existente
- **Cuando** un administrador crea override para `base_empresa=EMPRESA_A`
- **Entonces** la fila se persiste en PostgreSQL con `base_empresa='EMPRESA_A'` y timestamps de auditoría

#### Scenario: Política no escrita en legacy

- **Dado** cualquier operación CRUD sobre `PoliticaAuditoriaContable`
- **Cuando** se confirma la transacción
- **Entonces** ninguna tabla `cont_*` del MySQL legacy es modificada

---

### Requirement: POL-02 — Resolución default → override por base_empresa

La función `resolver_politica(base_empresa)` DEBE cargar primero la fila global (`base_empresa='__default__'` o convención equivalente documentada en design) y aplicar override campo a campo si existe fila específica para la empresa solicitada. DEBE devolver un `dict` completo con todos los parámetros efectivos, sin valores NULL en parámetros obligatorios.

#### Scenario: Empresa sin override usa default

- **Dado** solo existe política global con `tolerancia_decimal=0.005`
- **Cuando** se resuelve política para `base_empresa=EMPRESA_B` sin fila propia
- **Entonces** el dict efectivo coincide con el default global

#### Scenario: Override parcial

- **Dado** default global y override de `EMPRESA_A` que solo cambia `tolerancia_decimal=0.01`
- **Cuando** se resuelve política para `EMPRESA_A`
- **Entonces** `tolerancia_decimal=0.01` y el resto de campos provienen del default

#### Scenario: Empresa inexistente

- **Dado** un `base_empresa` válido en sesión pero sin datos contables
- **Cuando** se resuelve política
- **Entonces** se aplican defaults globales sin error, indicando en metadatos que no hay override

---

### Requirement: POL-03 — Parámetro tratamiento_anulados

El parámetro `tratamiento_anulados` DEBE ser enum con valores `excluir` | `incluir_neutralizado`. DEBE afectar la consulta canónica de saldo teórico desde `cont_asiento` y los checks `saldo_*_vs_diario`. Default DEBE ser `excluir`.

#### Scenario: Excluir anulados en saldo teórico

- **Dado** `tratamiento_anulados=excluir` y asientos marcados `anulado='Si'`
- **Cuando** se ejecuta `saldo_ejercicio_vs_diario`
- **Entonces** los renglones anulados no participan del saldo teórico

#### Scenario: Incluir anulados neutralizados

- **Dado** `tratamiento_anulados=incluir_neutralizado` y contra-asientos que neutralizan el original
- **Cuando** se ejecuta un check de saldo
- **Entonces** el criterio de inclusión sigue la regla documentada en design (pares original/contra) y queda reflejado en el snapshot de política

---

### Requirement: POL-04 — Parámetro politica_centavo

El parámetro `politica_centavo` DEBE ser enum con valores `diario_manda` | `conservar_compensacion`. DEBE afectar `asiento_balanceado` y el plan de recálculo posterior (Fase 3). Default DEBE ser `diario_manda`. Mapea el comportamiento de `Balancea_asiento` VB6 (H10).

#### Scenario: Diario manda ante desbalance de centavo

- **Dado** `politica_centavo=diario_manda` y asiento con desbalance 0,01 en diario pero compensado en saldos
- **Cuando** se audita `asiento_balanceado`
- **Entonces** se reporta el desbalance del diario como diferencia

#### Scenario: Conservar compensación VB6

- **Dado** `politica_centavo=conservar_compensacion` y desbalance ≤0,01 aplicado por VB6
- **Cuando** se audita saldo vs diario
- **Entonces** el check DEBE aplicar la regla de tolerancia/centavo definida en design sin contradecir la política elegida

---

### Requirement: POL-05 — Parámetro prefijos_cuenta

El parámetro `prefijos_cuenta` DEBE ser un mapping JSON `{resultado:[...], pasivo:[...], activo:[...], pn:[...]}` usado por `cierre_resultado_no_cero` y clasificaciones similares. DEBE tener defaults sugeridos alineados a VB6 (`41`, `42`, `2%`, etc., H14) pero editables por empresa.

#### Scenario: Prefijos personalizados por plan de cuentas

- **Dado** una empresa cuyo plan usa prefijo `5` para resultados
- **Cuando** se configura `prefijos_cuenta.resultado=['5%']` en el override
- **Entonces** `cierre_resultado_no_cero` clasifica cuentas con ese prefijo

#### Scenario: Prefijos vacíos o inválidos

- **Dado** un override con lista vacía en `resultado`
- **Cuando** se resuelve política
- **Entonces** el sistema DEBE rechazar el guardado con validación en español o aplicar fallback al default global (decisión fijada en design; hasta entonces NO DEBE persistir JSON inválido)

---

### Requirement: POL-06 — Parámetro ejercicios_cerrados

El parámetro `ejercicios_cerrados` DEBE ser enum `no_tocar` | `permitir_con_reapertura`. DEBE gobernar si el motor de corrección (capability hermana) puede modificar ejercicios marcados cerrados. Default DEBE ser `no_tocar` por implicancia fiscal (H29).

#### Scenario: Ejercicio cerrado no modificable por defecto

- **Dado** `ejercicios_cerrados=no_tocar` y un ejercicio con flag cerrado
- **Cuando** se intenta plan de corrección sobre ese ejercicio
- **Entonces** el recálculo DEBE rechazar escritura y la auditoría MAY seguir en lectura

#### Scenario: Reapertura explícita con permiso reforzado

- **Dado** `ejercicios_cerrados=permitir_con_reapertura` y permiso de corrección reforzado
- **Cuando** se solicita apply en ejercicio cerrado con `ENVIRONMENT=production`
- **Entonces** el sistema permite corrección solo tras confirmación explícita registrada en log (detalle en capability recálculo)

---

### Requirement: POL-07 — Parámetro alcance_recompute

El parámetro `alcance_recompute` DEBE ser enum `ejercicio_activo` | `ejercicio_seleccionado` | `historico`. DEBE limitar el alcance del dry-run/apply del recálculo de saldos. Default DEBE ser `ejercicio_seleccionado`.

#### Scenario: Alcance ejercicio seleccionado

- **Dado** `alcance_recompute=ejercicio_seleccionado` y filtro `id_ejercicio=2024`
- **Cuando** se genera plan de recálculo
- **Entonces** solo se incluyen cuentas/movimientos de ese ejercicio

#### Scenario: Alcance histórico con advertencia de performance

- **Dado** `alcance_recompute=historico`
- **Cuando** se inicia dry-run
- **Entonces** la UI DEBE advertir impacto de performance y el procesamiento DEBE ejecutarse por lotes (detalle en design)

---

### Requirement: POL-08 — Parámetro tolerancia_decimal

El parámetro `tolerancia_decimal` DEBE ser un `Decimal` positivo (default `0.005`) aplicado a todos los checks que comparan importes (`saldo_*_vs_diario`, `asiento_balanceado`, `reparto_cc_incompleto`, etc.). DEBE persistirse con precisión acorde a `DecimalField(max_digits=8, decimal_places=4)`.

#### Scenario: Tolerancia estricta

- **Dado** `tolerancia_decimal=0.001` y delta de saldo 0,002
- **Cuando** se ejecuta `saldo_periodo_vs_diario`
- **Entonces** se reporta diferencia

#### Scenario: Tolerancia relajada

- **Dado** `tolerancia_decimal=0.05` y delta 0,03
- **Cuando** se ejecuta el mismo check
- **Entonces** no se reporta diferencia (`ok=true` para esa cuenta)

---

### Requirement: POL-09 — Snapshot config_hash por corrida

Cada corrida de auditoría o corrección DEBE serializar el dict de política efectiva (orden de claves estable), calcular `config_hash` (algoritmo fijado en design, p. ej. SHA-256 del JSON canónico) y persistirlo en el registro de corrida y en logs (`cont_audit_correccion` / tabla de corridas de auditoría). El hash DEBE permitir reproducir qué reglas aplicaron en una fecha pasada aunque la política haya cambiado después.

#### Scenario: Hash estable para misma política

- **Dado** dos resoluciones consecutivas sin cambios de parámetros
- **Cuando** se calcula `config_hash` en ambas
- **Entonces** el valor es idéntico

#### Scenario: Hash cambia al editar política

- **Dado** una corrida con hash `abc123`
- **Cuando** se modifica `tratamiento_anulados` y se ejecuta nueva corrida
- **Entonces** el nuevo `config_hash` difiere de `abc123` y la corrida anterior conserva su hash histórico

---

### Requirement: POL-10 — Auditoría de cambios de política

Todo alta/modificación de `PoliticaAuditoriaContable` DEBE registrar `actualizado_por` (usuario Synap) y `actualizado_en` (timestamp servidor). DEBERÍA exponer historial consultable en UI admin o pantalla dedicada. Los cambios DEBEN validarse antes de persistir (enums, JSON schema de prefijos, rango de tolerancia).

#### Scenario: Guardado con usuario identificado

- **Dado** un usuario con permiso de configuración contable
- **Cuando** guarda override de política
- **Entonces** `actualizado_por` contiene su identificador y `actualizado_en` refleja la fecha/hora actual

#### Scenario: Validación de enum inválido

- **Dado** un formulario con `tratamiento_anulados='invalido'`
- **Cuando** se intenta guardar
- **Entonces** el sistema rechaza con mensaje en español y no persiste cambios

---

### Requirement: POL-11 — Integración con checks y recálculo

Los servicios de auditoría (`contabilidad_audit/services/*`) y corrección (`legacy_db/services/cont_recalculo_service.py`) DEBEN recibir la política resuelta como argumento explícito; NO DEBEN leer constantes hardcodeadas de negocio. Cambiar política y re-ejecutar DEBE alterar solo comportamiento de comparación/filtrado, nunca escribir legacy en Fase 1.

#### Scenario: Re-ejecución tras cambio de tolerancia

- **Dado** una corrida previa con diferencias bajo tolerancia antigua
- **Cuando** se reduce `tolerancia_decimal` y se re-ejecuta auditoría
- **Entonces** pueden aparecer nuevas diferencias sin ninguna escritura MySQL

---

### Requirement: POL-12 — Permisos de configuración

La pantalla de configuración de políticas DEBE exigir permiso Synap dedicado distinto del permiso de lectura de auditoría y del permiso de corrección. Usuarios sin permiso NO DEBEN ver formularios de edición.

#### Scenario: Usuario solo lectura de auditoría

- **Dado** un usuario con permiso de ejecutar checks pero sin permiso de configuración
- **Cuando** accede a `/contabilidad/auditoria/configuracion/`
- **Entonces** recibe denegación o vista solo lectura sin campos editables

---

### Requirement: POL-13 — UI de configuración (canon reports)

La configuración DEBE exponerse en UI alineada al canon de reportes (`reports/dashboard_detail.html` o formulario equivalente bajo `/contabilidad/auditoria/configuracion/`), con etiquetas en español, fechas dd/MM/yyyy en metadatos y ayuda contextual por parámetro.

#### Scenario: Visualización de política efectiva

- **Dado** default global y override parcial de empresa
- **Cuando** el usuario consulta configuración de `EMPRESA_A`
- **Entonces** ve valores efectivos resueltos, indicando qué campos heredan del default

---

## Referencias

- Arquitectura §8: `docs/general/PROPUESTA_ARQUITECTURA_AUDITORIA_RECALCULO_CONTABILIDAD_SYNAP.md`
- Hallazgos relacionados: H05, H10, H11, H14, H29, H37 (criterios de filtro/clasificación)
