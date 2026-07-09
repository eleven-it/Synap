# Best Sox → MPR — Iteración 1: validación Producción diaria y Por tejedor/operario

**Fecha:** 07/07/2026  
**Alcance:** `BS-Reportes Fabrica 22.xlsx` (hojas *Produccion Diario*, *Produccion x Tejedor*) vs reportes MPR *Resumen diario* y *Por operario*.  
**Restricción:** solo **lectura** en Azure SQL `BEST` (sin INSERT/UPDATE/DELETE).  
**Plan general:** ver análisis previo en conversación / fases A–D del relevamiento Best Sox.

---

## 1. Fuentes y conexión (solo lectura BEST)

| Parámetro | Valor |
|-----------|--------|
| Servidor | `m52q7iitok.database.windows.net:1433` |
| Base | `BEST` |
| Usuario (lectura) | `interfase$bestsox` o `fabrica$bestsox@m52q7iitok` |
| Planilla | `Best Sox/BS-Reportes Fabrica 22.xlsx` |
| Vista SQL pivot | `REP_MOVIMIENTOS_TOTAL` (filtro últimos ~480 días en conexión Excel) |

---

## 2. Definición canónica BEST — «Producción diaria»

La hoja **Produccion Diario** filtra pivot con **`Origen = Producción`** y suma **Docenas**.

En SQL, el movimiento que mejor representa el **ingreso físico a depósito de producción** es:

```sql
-- SOLO LECTURA — no modificar datos
SELECT CAST(Fecha AS DATE) AS dia,
       SUM(Cantidad) AS unidades,
       SUM(Docenas) AS docenas,
       COUNT(*) AS movimientos
FROM REP_MOVIMIENTOS_TOTAL
WHERE Fecha BETWEEN @desde AND @hasta
  AND Motivo = 'Ingreso por Distr s/ Orden'
  AND [Origen] = 'Producción'
  AND Deposito = 'Depósito Producción'
GROUP BY CAST(Fecha AS DATE)
ORDER BY dia;
```

**Notas:**

- `Motivo = 'Alta por Produccion'` (TTCODE 201) **no aparece** en movimientos recientes; el flujo operativo usa **distribución sin orden** entre centros virtuales y depósitos físicos.
- Filtro solo `Origen = 'Producción'` es casi equivalente (diferencia marginal por anulaciones).
- **Docenas** en BEST: `Cantidad / divisor` con `divisor = 6` (pack×2), `4` (pack×3), `12` (resto).

### 2.1 Resultado BEST — 30/06/2026 a 06/07/2026

| Día | Unidades | Docenas | Movimientos |
|-----|----------|---------|-------------|
| 30/06/2026 | 15.930 | 1.327,5 | — |
| 01/07/2026 | 16.981 | 1.415,1 | — |
| 02/07/2026 | 16.200 | 1.350,0 | — |
| 03/07/2026 | 12.588 | 1.049,0 | — |
| 04/07/2026 | 12.660 | 1.055,0 | — |
| 06/07/2026 | 5.430 | 452,5 | — |

*(Sin datos 05/07 — fin de semana / sin carga.)*

---

## 3. Definición MPR — equivalentes semánticos

| Concepto Best Sox | Reporte / tabla MPR | Campo agregado |
|-------------------|---------------------|----------------|
| Producción registrada (parte tejedor) | **Resumen diario → Parte** | `SUM(mpr_parte_linea.cantidad)` por `mpr_parte.fecha_produccion` |
| Envío a planta | Resumen diario → Enviado | `mpr_envio_produccion` |
| Clasificación (semi / 2da / scrap) | Resumen diario → Clasificado / Scrap | `mpr_transicion_lote` desde `Produccion` |
| Producción x Tejedor | **Por operario** | `mpr_parte_linea` + clasificación CC por `id_operario` fabricante |
| Cupo en planta (no es KPI diario) | Tablero / Parte — **Fabricando** | `max(0, envíos − acreditado)`; acreditado incluye stock, CC y partes previos |

**Diferencia de modelo:** BEST tiene un **único ledger** (`TT` → `REP_MOVIMIENTOS_TOTAL`). MPR separa **envío → parte → clasificación (CC)** en tablas distintas. Para paridad con Excel de fábrica, la serie comparable a *Produccion Diario* es **`parte`**, no `enviado`. Estado **Completo** en cadena pipeline no implica armado de pack.

---

## 4. Resultado MPR — mismas fechas

### 4.1 `administranet93` (base de tests Synap)

| Día | Enviado | Parte | Clasificado |
|-----|---------|-------|-------------|
| 30/06 – 04/07 | 0 | 0 | 0 |
| 05/07/2026 | 8 | 0 | 0 |

**Conclusión:** sin datos operativos reales; no sirve para validación numérica contra BEST.

### 4.2 `administranet96` (única base con parte MPR en el período)

| Día | Enviado | Parte | Clasificado |
|-----|---------|-------|-------------|
| 03/07/2026 | 0 | 64 | 0 |
| 04/07/2026 | 739 | 1.488 | 146 |
| 05/07/2026 | 1 | 1 | 7.379 |

| Operario (03–05/07) | Unidades parte |
|---------------------|----------------|
| Luis C (id 2) | 1.486 |
| Juan Perez (id 1) | 67 |

**Conclusión:** datos piloto / UAT, **no correlacionan** con BEST (ej. 04/07: BEST 12.660 u vs MPR 1.488 u). Los sistemas **no comparten ledger** en este momento.

---

## 5. BEST — Producción x Tejedor (30/06 – 06/07/2026)

Misma query de §2 + agrupación por **`Tejedor`** (`TT.TTNOTE`, código de una letra):

| Tejedor | Docenas | Unidades |
|---------|---------|----------|
| F | 769,0 | 9.228 |
| D | 535,0 | 6.420 |
| S | 521,0 | 6.252 |
| R | 449,5 | 5.394 |
| J | 445,0 | 5.340 |
| … | … | … |
| B | 59,0 | 708 |

**Hallazgos:**

- El tejedor en BEST es un **código de una letra** en `TTNOTE`, no el nombre completo.
- `Responsable` en el mismo movimiento suele ser el usuario de carga (ej. `soledad`), no el tejedor.
- Códigos frecuentes en `TTNOTE` (jun 2026): S, R, D, J, L, F, K, M, C, N, V, G, E, T, W, B, P.
- MPR guarda `id_operario` + `operario_nombre` en `mpr_parte_linea` / `mpr_transicion_lote` → requiere **tabla de equivalencia** letra BEST ↔ operario AdministraNET.

---

## 6. Tabla de paridad (iteración 1)

| Dimensión | BEST (Excel/SQL) | MPR | Estado iteración 1 |
|-----------|------------------|-----|-------------------|
| Producción diaria | `REP_MOVIMIENTOS_TOTAL`, Origen Producción | `reporte_mpr_resumen_diario` → `parte` | Query BEST definida; MPR sin datos productivos en misma base |
| Docenas | Vista SQL con divisor pack | `presentacion_operativa` / divisor 12 + bulto | Regla alineable; validar pack×2/×3 en MySQL |
| Por tejedor | Pivot Tejedor = `TTNOTE` | `reporte_mpr_operario_parte` | Semántica OK; falta diccionario códigos |
| Semi / 2da / scrap | Movimientos hacia dep. 4004 / motivos | `mpr_transicion_lote` por operario | Pendiente iteración 2 |
| 2da / Eficiencia | `Segunda x Tejedor` ÷ `Produccion x Tejedor` | Ratio en reporte operario | Pendiente iteración 2 |

---

## 7. Bloqueadores para validación numérica 1:1

1. **Bases distintas:** BEST (Azure SQL) vs AdministraNET MySQL — no hay réplica automática de movimientos.
2. **Empresa MySQL productiva Best Sox:** confirmar cuál `base_empresa` usar en cutover (93 = tests, 96 = piloto con pocos registros).
3. **Migración pendiente en 96:** `mpr_transicion_lote.id_operario` no aplicada → reporte *Por operario* falla al incluir clasificación (`apply_mpr_core_tables administranet96`).
4. **Volumen:** BEST ~13k–17k u/día; MPR piloto ~1,5k u en 3 días → comparación solo tendrá sentido tras **operación paralela** o **import histórico**.

---

## 8. Consultas de control reutilizables

### BEST — total período (solo lectura)

```sql
SELECT SUM(Docenas) AS docenas, SUM(Cantidad) AS unidades
FROM REP_MOVIMIENTOS_TOTAL
WHERE Fecha BETWEEN '2026-07-01' AND '2026-07-31'
  AND Motivo = 'Ingreso por Distr s/ Orden'
  AND [Origen] = 'Producción'
  AND Deposito = 'Depósito Producción';
```

### MPR — total parte período

```sql
SELECT p.fecha_produccion, SUM(pl.cantidad) AS unidades
FROM mpr_parte_linea pl
INNER JOIN mpr_parte p ON p.id_mpr_parte = pl.id_mpr_parte
WHERE p.fecha_produccion BETWEEN '2026-07-01' AND '2026-07-31'
GROUP BY p.fecha_produccion;
```

---

## 9. Próxima iteración recomendada (2)

1. **Confirmar `base_empresa` Best Sox** en producción y aplicar DDL MPR (`002_mpr_transicion_lote_operario`).
2. **Diccionario tejedor:** relevar en BEST/AdministraNET qué operario corresponde a cada letra (`F`, `D`, `S`, …).
3. **Período de operación paralela** (1 semana): cada parte MPR debe generar movimiento equivalente en depósito producción.
4. **Validar inventario:** hoja *Inventarios Terminado* (`REP_INVENTARIOS`) vs `reporte_mpr_stock` por `tipo_mpr`.
5. **Ratio 2da/Ef.:** replicar fórmula Excel `Segunda x Tejedor` / `Produccion x Tejedor` en reporte MPR.

---

## 10. Referencias

- **GAP procesos y cálculos (catálogo Excel → MPR):** `docs/mpr/BEST_SOX_GAP_PROCESOS_Y_CALCULOS.md`
- Planillas: `Best Sox/*.xlsx`
- Vistas BEST: `REP_MOVIMIENTOS_TOTAL`, `REP_INVENTARIOS`, `REP_PCP_ARMADO`
- MPR: `reporte_mpr_resumen_diario`, `reporte_mpr_operario_parte` en `mpr/services.py`
- Depósitos BEST: `CC` 2000 Producción, 4000 Depósito Producción, 4002 Semi, 4003 Terminado, 4004 2da/Sobrante
