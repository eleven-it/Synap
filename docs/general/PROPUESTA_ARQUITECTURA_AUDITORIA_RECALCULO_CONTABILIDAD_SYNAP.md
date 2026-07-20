# Propuesta de arquitectura — Auditoría y recálculo de imputación contable en Synap

> **Rol:** documento de arquitectura de solución (iterable).
> **Objetivo:** construir en Synap un motor que **audite** las imputaciones contables de AdministraNET (detectar los defectos catalogados en `AUDITORIA_IMPUTACION_CONTABILIDAD_VB6.md`) primero **solo en lectura**, y luego habilite un **recálculo/corrección controlada** de los datos en la base MySQL legacy.
> **Regla de oro:** *lectura primero, corrección después*. Ninguna escritura hasta que la auditoría en lectura esté validada por el usuario contable.
> **Estado:** **F1 (auditoría lectura) implementada en app** `contabilidad_audit` — backend (17 checks, políticas, corrida) **y** UI canon reportes (tablero verde/rojo con drill-down, export CSV/Excel, configuración de políticas, entrada de menú). Fase 2 (dry-run) y Fase 3 (apply) permanecen como stubs.

---

## 1. Principios de diseño

1. **Read-only por defecto.** Toda la Fase 1 es idempotente y sin efectos: solo `SELECT`. La corrección (Fase 3) es un módulo separado, detrás de permiso y de un *dry-run* obligatorio.
2. **Separación de capas (regla del proyecto).**
   - **Aplicación:** UI, orquestación, presentación de diferencias.
   - **Legacy:** persistencia MySQL compartida con VB6. Toda escritura pasa por `legacy_db/` (nunca SQL suelto en apps).
3. **No romper contratos VB6.** El recálculo replica exactamente la semántica contable esperada (partida doble, `saldo_pc`, ejercicios/periodos). No se modifica el esquema salvo lo imprescindible, y siempre vía `core/services/legacy_mysql_schema/catalog.py`.
4. **Determinismo y trazabilidad.** `cont_asiento` es la **fuente de verdad**; las tablas de saldo son *derivadas* y por tanto **reconstruibles**. Toda corrección deja evidencia (backup + log + metadata).
5. **Atomicidad.** Cada corrección se ejecuta en una única transacción con rollback; nunca deja estados intermedios (corrige de raíz H01/H03/H41).
6. **Tipos AdministraNET.** Toda lectura/escritura normaliza con `core.utils.administranet_types`.
7. **Multi-empresa.** Todo recibe `base_empresa` y usa el pool `reports/services/connection_pool.get_mysql_pool()`.

---

## 2. Componentes reutilizables ya existentes en Synap

| Necesidad | Reutilizar |
|-----------|-----------|
| Conexión MySQL legacy multi-empresa | `reports/services/connection_pool.get_mysql_pool()` → `pool.get_connection(base_empresa)` |
| Patrón de reconciliación read-only (modelo a seguir) | `reports/services/reconciliation_saldo_pedido_proveedor.py`, `reports/services/reconciliation_saldo_stock.py` |
| Capa de escritura VB6-compatible | app `legacy_db/` (`services/`, `repositories.py`, `mappers.py`, `validators.py`, `db_router.py`) |
| Normalización de tipos | `core/utils/administranet_types.py` |
| DDL legacy centralizado | `core/services/legacy_mysql_schema/catalog.py` |
| UI canónica (dashboards) | `reports/dashboard/<slug>/`, `reports/dashboard_detail.html`, includes en `reports/includes/` |
| Tests en contenedor | `docker exec Synap_app python manage.py test <app>` |

---

## 3. Arquitectura por capas

```
┌─────────────────────────────────────────────────────────────┐
│  UI (canon reports)   /contabilidad/auditoria/<slug>/         │
│  - Tablero de checks (verde/rojo)  - Detalle de diferencias   │
│  - Botón "Recalcular (dry-run)"    - Confirmación corrección  │
└───────────────▲───────────────────────────────┬──────────────┘
                │ read (JSON)                    │ write (permiso + confirm)
┌───────────────┴───────────────┐   ┌────────────┴──────────────┐
│  AUDIT ENGINE (read-only)      │   │  CORRECTION ENGINE         │
│  contabilidad_audit/services/  │   │  legacy_db/services/       │
│  - registry de checks          │   │    cont_recalculo_service  │
│  - cada check = SQL SELECT      │   │  - dry-run (diff)          │
│  - devuelve diferencias         │   │  - apply (transaccional)   │
└───────────────▲────────────────┘   └────────────▲──────────────┘
                │                                   │
        get_mysql_pool()                    get_mysql_pool()/legacy_db
                │                                   │
        ┌───────┴───────────────────────────────────┴───────┐
        │           MySQL AdministraNET (legacy)             │
        │  cont_asiento · cont_*_saldo_cta · cont_pc · ...   │
        └────────────────────────────────────────────────────┘
```

Se propone una **app nueva `contabilidad_audit`** (solo lectura + orquestación UI) y ubicar la corrección en `legacy_db/services/cont_recalculo_service.py` (respeta la separación app/legacy).

---

## 4. Fase 1 — Motor de auditoría (solo lectura)

### 4.1 Contrato de un "check"

Cada verificación es una función pura que recibe `(base_empresa, filtros)` y devuelve un resultado estándar:

```python
@dataclass
class AuditResult:
    check_id: str            # p.ej. "saldos_vs_diario_ejercicio"
    titulo: str
    severidad: str           # critico | alto | medio
    ok: bool
    total_evaluado: int
    total_diferencias: int
    diferencias: list[dict]  # filas con id_pc, esperado, actual, delta, drill-down
    resumen: dict
    error: str | None
```

Un **registry** (`CHECKS = {check_id: fn}`) permite ejecutar uno, varios o todos, y exponerlos en la UI. Modelo directo: `run_reconciliation()` en `reconciliation_saldo_pedido_proveedor.py`.

### 4.2 Catálogo inicial de checks (mapea los hallazgos)

| check_id | Verifica (SQL SELECT) | Detecta |
|----------|----------------------|---------|
| `asiento_balanceado` | Por `codigo_movimiento`: `SUM(debe) = SUM(haber)` | H09, H10, H16, H42 |
| `saldo_ejercicio_vs_diario` | `cont_ejercicio_saldo_cta.saldo` vs recálculo desde `cont_asiento` según `cont_pc.saldo_pc` | H01, H03, H04, H10, H17, H33 |
| `saldo_periodo_vs_diario` | Igual a nivel periodo (`cont_periodo_saldo_cta`) | idem |
| `cuentas_sin_fila_saldo` | Cuentas imputables con movimientos sin fila en `cont_*_saldo_cta` | H17, H20, H34 |
| `imputacion_a_no_imputable` | `cont_asiento` sobre `id_pc` con `imp_cont_pc <> 'Imputable'` | H15 |
| `concepto_anulacion_incoherente` | Contra-asientos cuyo `id_concepto_asiento` no coincide con `id_concepto_anul` del original | H05 |
| `nro_asiento_duplicado` | `nro_asiento` repetido dentro de un mismo ejercicio | H06, H07 |
| `codigo_movimiento_huerfano` | `cont_cc_asiento` / anulaciones sin `cont_asiento` correspondiente | H01, H08 |
| `fecha_fuera_de_periodo` | `cont_asiento.fecha_asiento` fuera de `[fecdesde_periodo, fechasta_periodo]` | H12, H13, H28 |
| `periodos_solapados` | Intersección real de intervalos (`start1<=end2 AND start2<=end1`) | H28, H30, H31, H32 |
| `cierre_resultado_no_cero` | Cuentas `4x` con saldo ≠ 0 tras cierre PyG | H11 |
| `reparto_cc_incompleto` | `SUM(cont_cc_asiento.importe_cc) <> debe/haber` del renglón | H39, H40, H43 |
| `rei_recalculo` | Recalcula REI con `ind_cierre/ind_origen` y compara con asientos REI existentes | H02, H44 |
| `concepto_no_normal` | Conceptos con `tipo_concepto_asiento <> 'Normal'` usados/creados | H37, H38 |

> Cada check devuelve **diferencias con drill-down** (equivalente a `get_movimiento_detalle`) para que el contador vea el comprobante exacto.

### 4.3 Consulta canónica de reconciliación de saldos (núcleo)

```sql
-- saldo teórico por cuenta/ejercicio derivado del diario (fuente de verdad)
SELECT a.id_pc, a.id_ejercicio,
       CASE pc.saldo_pc
            WHEN 'Deudor'   THEN SUM(a.debe_asiento - a.haber_asiento)
            WHEN 'Acreedor' THEN SUM(a.haber_asiento - a.debe_asiento)
       END AS saldo_teorico
FROM cont_asiento a
JOIN cont_pc pc ON pc.id_pc = a.id_pc
WHERE (a.anulado IS NULL OR a.anulado <> 'Si')   -- criterio a confirmar con negocio
GROUP BY a.id_pc, a.id_ejercicio;
```

Se compara `saldo_teorico` contra `cont_ejercicio_saldo_cta.saldo_ejercicio_cta` con tolerancia decimal (`abs(delta) > 0.005`). *(El tratamiento de asientos anulados y del centavo de `Balancea_asiento` debe consensuarse con el área contable antes de fijar el criterio.)*

### 4.4 UI (canon reports)

- Nueva ruta `/contabilidad/auditoria/` con tablero de checks (tarjetas verde/rojo con conteo de diferencias), filtros por empresa/ejercicio/periodo, y detalle expandible por cuenta con drill-down al comprobante.
- Reutiliza `reports/dashboard_detail.html` + includes; **no** usa como referencia las pantallas de Objetivos/Presupuestos (excluidas por la regla UI).
- Export a Excel/CSV vía `reports/services/export_service.py`.

---

## 5. Fase 2 — Dry-run del recálculo (lectura, sin escritura)

Antes de tocar la DB, el motor de corrección produce un **plan de cambios** sin ejecutarlo:

- Para cada tabla derivada (`cont_*_saldo_cta`) calcula el valor correcto y muestra `(actual → propuesto, delta)`.
- Para inconsistencias de referencia (concepto de anulación, filas de saldo faltantes) lista el `UPDATE`/`INSERT` exacto que aplicaría.
- Genera un **reporte de impacto** (nº de filas, cuentas afectadas, monto total de ajuste) exportable y aprobable.

El dry-run es la salida de la Fase 1 promovida a "propuesta de corrección"; sigue siendo 100% lectura.

---

## 6. Fase 3 — Corrección en DB (escritura controlada)

> Solo tras aprobación explícita. Vive en `legacy_db/services/cont_recalculo_service.py`.

### 6.1 Estrategia de corrección por tipo

| Problema | Corrección | Reversible |
|----------|-----------|------------|
| Saldos derivados desincronizados | **Recalcular** `cont_*_saldo_cta` desde `cont_asiento` (la derivada se reconstruye) | Sí (backup) |
| Filas de saldo faltantes | `INSERT` de la fila con saldo recalculado | Sí |
| Concepto de anulación erróneo | `UPDATE cont_asiento.id_concepto_asiento` = `id_concepto_anul` del original | Sí |
| Asiento desbalanceado por centavo | Regla de compensación consensuada + re-derivar saldos | Sí |
| REI mal calculado | Anular asiento REI y regenerar con acumulación correcta | Sí (contra-asiento) |

**Cuentas de resultado / cierres ya cerrados:** no se auto-corrigen; se marcan para revisión manual (implicancia contable/fiscal).

### 6.2 Salvaguardas obligatorias

1. **Backup previo** de las tablas afectadas (snapshot a tabla `*_bkp_<timestamp>` o export) — orquestado, registrado.
2. **Transacción única** por lote con rollback ante cualquier error (elimina H01/H03).
3. **Idempotencia:** re-ejecutar no cambia nada si ya está correcto.
4. **Detección de concurrencia:** re-validar la diferencia dentro de la transacción antes de escribir (segunda validación); locking pesimista donde aplique (corrige H06).
5. **Auditoría (`metadata`):** tabla de log `cont_audit_correccion` (`base_empresa`, `check_id`, `id_pc`, `valor_anterior`, `valor_nuevo`, `usuario`, `fecha`, `lote_id`). Se crea vía `catalog.py` si se aprueba.
6. **Permiso + `ENVIRONMENT=production`:** la corrección exige permiso Synap dedicado y refuerzos de seguridad activos en producción (regla del proyecto).
7. **Rollback de lote:** cada `lote_id` es revertible desde el backup/log.

### 6.3 Orden de ejecución seguro

```
1) asiento_balanceado           (diagnóstico; no auto-corrige montos de negocio)
2) concepto_anulacion_incoherente (UPDATE puntual)
3) cuentas_sin_fila_saldo        (INSERT)
4) saldo_ejercicio/periodo_vs_diario (recálculo derivado)  ← el gran recompute
5) rei_recalculo                 (regenerar, requiere aprobación caso a caso)
```

El paso 4 es el **recompute maestro**: como `cont_asiento` es la fuente de verdad, reconstruir las tablas de saldo desde cero (por empresa/ejercicio) resuelve de una vez H04/H10/H17/H33/H34.

---

## 7. Plan incremental (SDD sugerido)

| Iteración | Entregable | Escritura |
|-----------|-----------|-----------|
| **I0** | App `contabilidad_audit` + registry + 3 checks núcleo (`saldo_*_vs_diario`, `asiento_balanceado`) + tests | ❌ |
| **I1** | Catálogo completo de checks + drill-down | ❌ |
| **I2** | UI tablero (canon reports) + export | ❌ |
| **I3** | Dry-run del recompute (plan de cambios + reporte de impacto) | ❌ |
| **I4** | `cont_recalculo_service` con backup + transacción + log, tras permiso | ✅ (controlada) |
| **I5** | Reversión de lote + hardening de concurrencia | ✅ |

Formalizar cada iteración como un change en `openspec/` (propose → spec → design → tasks → apply → verify). Delegar exploración/implementación mecánica a workers generales; el diseño de UI a worker de diseño; los fixes/debug a worker de debug (según regla de orquestación).

---

## 8. Políticas contables como configuración (parámetros de la app)

Las decisiones de negocio **no se codifican como constantes**: son **parámetros configurables por empresa**. La Fase 1 es solo lectura, por lo que cambiar un parámetro solo altera cómo se arma el `SELECT` o el umbral de comparación → re-ejecutar el check, sin riesgo.

### 8.1 Ubicación y resolución

- **Capa aplicación** (es política de negocio, no dato legacy): se persiste en la **DB propia de Synap** (modelo Django en `contabilidad_audit/models.py`), **no** en el MySQL de AdministraNET.
- **Resolución:** `default global → override por base_empresa`.
- **Reproducibilidad (obligatoria):** cada corrida de auditoría/corrección **snapshotea** la configuración efectiva y guarda un `config_hash` en el log (`cont_audit_correccion` / registro de corrida). Una auditoría pasada sigue siendo explicable aunque la política cambie después.

### 8.2 Parámetros

| Parámetro | Tipo | Valores | Afecta |
|-----------|------|---------|--------|
| `tratamiento_anulados` | enum | `incluir_neutralizado` (default validado) · `excluir` | consulta canónica §4.3 / recompute de saldos |
| `politica_centavo` | enum | `diario_manda` · `conservar_compensacion` | `asiento_balanceado`, recompute |
| `prefijos_cuenta` | mapping | `{resultado:[...], pasivo:[...], activo:[...], pn:[...]}` | `cierre_resultado_no_cero`, clasificación |
| `ejercicios_cerrados` | enum | `no_tocar` · `permitir_con_reapertura` | Fase 3 (corrección) |
| `alcance_recompute` | enum | `ejercicio_activo` · `ejercicio_seleccionado` · `historico` | Fase 3 (performance) |
| `tolerancia_decimal` | decimal | p. ej. `0.005` | todos los checks de saldo |

### 8.3 Modelo (borrador)

```python
# contabilidad_audit/models.py  (DB Synap, no legacy)
class PoliticaAuditoriaContable(models.Model):
    base_empresa = models.CharField(max_length=64, unique=True)  # null/"__default__" = global
    tratamiento_anulados = models.CharField(default="incluir_neutralizado")  # ver §10: original marcado + contra reversante se netean
    politica_centavo = models.CharField(default="diario_manda")
    prefijos_cuenta = models.JSONField(default=dict)
    ejercicios_cerrados = models.CharField(default="no_tocar")
    alcance_recompute = models.CharField(default="ejercicio_seleccionado")
    tolerancia_decimal = models.DecimalField(max_digits=8, decimal_places=4, default=Decimal("0.005"))
    actualizado_por = models.CharField(max_length=64)
    actualizado_en = models.DateTimeField(auto_now=True)

def resolver_politica(base_empresa) -> dict:
    """override por empresa sobre el default global; devuelve dict + config_hash."""
```

Los checks reciben la política resuelta y construyen su SQL/umbrales a partir de ella (p. ej. filtro `anulado`, prefijos `LIKE`, tolerancia). La UI expone una pantalla de configuración (canon reports/forms), con permiso dedicado; los cambios quedan auditados (`actualizado_por/en`).

### 8.4 Riesgos remanentes

- **Prefijos de cuenta:** aunque configurables, hay que validar contra el plan real de cada empresa antes de auto-clasificar resultado/pasivo (default sugerido: `41/42/2%`, ajustable).
- **`historico` en `alcance_recompute`:** impacto de performance; ejecutar por lotes.
- **`permitir_con_reapertura`:** implicancia fiscal; requiere permiso reforzado y `ENVIRONMENT=production`.

---

## 9. Criterios de éxito

- Fase 1: para un ejercicio dado, el tablero lista el 100% de cuentas con `|saldo_derivado − saldo_diario| > 0.005` con drill-down al comprobante.
- Fase 3: tras el recompute, `saldo_*_vs_diario` queda en verde y es idempotente; existe backup y log reversibles de cada lote.

---

## 10. Validación empírica (entorno de testing) y motor de reconstrucción

Prueba de concepto ejecutada en **solo lectura** sobre la copia de testing (`administranet89`), que valida la viabilidad del recompute antes de construir la app.

### 10.1 Detección del bug "factura/OP sin asiento"
- **331 huérfanos linkables** (FA 147, FC 27, OP 157) con `CodigoMovimiento>0` y sin filas en `cont_asiento` → regenerables.
- **86 registros de anulación** (`CodigoMovimiento=0`) correctamente excluidos (ver §10.3).
- Dispersión mensual jul-2025→jul-2026 confirma bug **intermitente** (H51/H52), no falta de activación.

### 10.2 Motor de reconstrucción (`legacy_db/scripts/cont_reconstruccion_compras_pagos.py`)
- `generar_asiento_cont` (VB6) arma el asiento desde **temporales de sesión** ya inexistentes → regenerar exige **reconstruir insumos desde tablas persistidas** (`cuentaproveedor`, `stock`, `percep_prov`, `transferencia`, `otro_egreso`, `caja`, retenciones…).
- **Facturas (FA/FC): 634/634 = 100 %** y **OP: 1.672/1.672 = 100 %** de fidelidad (validado recomputando y comparando contra los asientos reales; OP contempla la exclusión de `caja` con `id_chequetercero` para no duplicar el HABER de cheque de tercero).
- Este script es el germen de `cont_recalculo_service` (Fase 3 / I4). Se ejecuta con `docker exec Synap_app python …` (driver `MySQLdb`).

### 10.3 Anulaciones: partida doble correcta → `tratamiento_anulados = incluir_neutralizado`
- Anular una compra/pago marca el asiento original `anulado='Si'` **y** crea un **contra-asiento** reversante (concepto 4/8, `codigo_movimiento_anul`=original, cm nuevo, `anulado='No'`). Ver `AUDITORIA_IMPUTACION_CONTABILIDAD_VB6.md` §6.8.
- **Corrección de criterio:** original + contra **se netean a cero**. El recompute de saldos debe **sumar TODAS las filas** (no excluir `anulado='Si'`). Verificación: excluyendo anulados el saldo difiere en 31/111 cuentas; **incluyendo todas, solo 6/111**. Desfase material real: 7 ctas (ej.1) + 3 (ej.2), no 90/29.
- Contemplar **arrastre de apertura** (el ejercicio 2 no tiene asiento de apertura; el saldo inicial se arrastra directo a `cont_ejercicio_saldo_cta`).

---

*Referencia de hallazgos: `docs/general/AUDITORIA_IMPUTACION_CONTABILIDAD_VB6.md`. Este documento es iterable; ajustar el catálogo de checks y las políticas de corrección con feedback del área contable.*
