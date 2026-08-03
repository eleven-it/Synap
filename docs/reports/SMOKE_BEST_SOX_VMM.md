# Smoke Best Sox — Informe Ventas marcas mensual (A1)

**Change:** `vmm-pwa-cotizacion-bcra` (tarea A1)  
**Fecha documento:** 02/08/2026  
**Empresa:** Best Sox — `empresas.id_empresa=1`, `base_empresa=administranet`  
**Estado:** **plantilla pendiente de ejecución** — resultados numéricos se completan **solo** tras corrida en Staging/local con MySQL Best Sox alcanzable. **No inventar totales.**

**Referencias:** [MAPEO_PUW_PUM_ADMINISTRANET.md](MAPEO_PUW_PUM_ADMINISTRANET.md) §8, [PLAN_INFORME_VENTAS_MARCAS_MENSUAL.md](PLAN_INFORME_VENTAS_MARCAS_MENSUAL.md) §9 A1, [QA_VMM_PWA_P7.md](QA_VMM_PWA_P7.md) (extensión PWA).

---

## Precondiciones

- Entorno: **Staging** (o local con túnel/VPN a MySQL LAN Best Sox).
- Migraciones Django aplicadas (`ReportDefinition` slug `ventas-marcas-mensual`).
- DDL `cotizacion_historial` aplicado si se prueba TC BCRA (proveedor `cotizacion_historial` en herramienta global MySQL).
- Usuario Synap con alcance comercial que incluya ventas del período elegido.
- Período con ventas recientes documentadas en MAPEO §8 (ajustar fechas al cutover real al ejecutar).

---

## Parte 1 — SQL AdministraNET (referencia)

Ejecutar en MySQL sobre `administranet`. **Sustituir** `@fecha_desde`, `@fecha_hasta`, `@cod_marca` antes de correr.

### 1.1 Catálogo marcas PUM / PUW

```sql
SELECT CodMarca, NombreMarca
FROM marca
WHERE NombreMarca IN ('PUM', 'PUW');
-- Esperado (Best Sox): PUM=13, PUW=15 — anotar resultado real: ___________
```

### 1.2 Totales agregados (packs + facturación neta renglón)

Plantilla alineada a runner VMM (whitelist FA/NC, `PrecioNetoxR` con signo). Validar **una marca** por corrida.

```sql
SET @fecha_desde = '2026-07-24';
SET @fecha_hasta = '2026-07-29';
SET @cod_marca = 13;  -- PUM; usar 15 para PUW

SELECT
  COUNT(*) AS renglones,
  SUM(
    CASE WHEN cc.TipoComp IN ('NC','NC A','NC B','NC C','NC E','NC M') THEN -1 ELSE 1 END
    * st.Cantidad
  ) AS packs,
  SUM(
    CASE WHEN cc.TipoComp IN ('NC','NC A','NC B','NC C','NC E','NC M') THEN -1 ELSE 1 END
    * st.PrecioNetoxR
  ) AS facturacion_neta
FROM stock st
INNER JOIN cuentacliente cc ON st.NroComprobante = cc.NroComprobante AND st.TipoComp = cc.TipoComp
INNER JOIN articulo art ON st.CodArticulo = art.CodArticulo
WHERE cc.Anulado = 'No'
  AND cc.CodigoMovimiento <> 0
  AND cc.TipoComp IN ('FA','FB','FC','FE','FM','NC','NC A','NC B','NC C','NC E','NC M')
  AND st.Anulado = 'No'
  AND st.TipoComp IN ('Venta','Venta TPV','Devol - Cliente','ND Anul NC')
  AND cc.Fecha BETWEEN @fecha_desde AND @fecha_hasta
  AND art.CodigoMarca = @cod_marca;
```

| Métrica SQL | Valor anotado | Fecha corrida |
|-------------|---------------|---------------|
| renglones | _pendiente_ | |
| packs | _pendiente_ | |
| facturacion_neta | _pendiente_ | |

### 1.3 TC vigente (cotización id=1)

```sql
SELECT id_cotizacion, ValorPesos FROM cotizacion WHERE id_cotizacion = 1;
-- Valor anotado: ___________
```

### 1.4 (Opcional) Historial cotización

```sql
SELECT fecha, valor_pesos, origen
FROM cotizacion_historial
WHERE id_cotizacion = 1
ORDER BY fecha DESC
LIMIT 5;
-- Si tabla no existe: aplicar proveedor cotizacion_historial antes de smoke BCRA
```

---

## Parte 2 — UI desktop

URL: `/reports/dashboard/ventas-marcas-mensual/`

| # | Paso | Esperado | OK | Notas |
|---|------|----------|-----|-------|
| D1 | Login Best Sox; abrir informe | 200, filtros visibles | ☐ | |
| D2 | Período = mismo que SQL §1.2 | Consulta OK | ☐ | |
| D3 | Marca = PUM (o PUW); modo packs | KPI Unidades ≈ SQL packs (tolerancia redondeo) | ☐ | anotar: ___ |
| D4 | KPI Facturación ≈ SQL facturacion_neta | ☐ | anotar: ___ |
| D5 | Expandir vendedor → cliente | Filas anidadas | ☐ | |
| D6 | Toggle docenas | KPI cambia según factor U.M. | ☐ | |
| D7 | TC vacío + tasa 13% | Regalías = fact × 0,13; Regalías/TC = reg/TC | ☐ | |
| D8 | Export Excel | Hojas Matriz + Detalle descargadas | ☐ | |
| D9 | Modo comparar PUM vs PUW | KPIs delta; matriz a/b | ☐ | |

---

## Parte 3 — UI PWA (misma corrida numérica)

Usar mismos filtros que Parte 2. Detalle táctil en [QA_VMM_PWA_P7.md](QA_VMM_PWA_P7.md).

| # | Paso | Esperado | OK | Notas |
|---|------|----------|-----|-------|
| M1 | PWA: mismos KPIs que desktop (± redondeo UI) | ☐ | anotar: ___ |
| M2 | Sheet filtros + Actualizar | ☐ | |
| M3 | Matriz tarjetas portrait | ☐ | |
| M4 | Export / aviso descarga | ☐ | |

---

## Parte 4 — Cotización BCRA (opcional en mismo smoke)

| # | Paso | Esperado | OK | Notas |
|---|------|----------|-----|-------|
| B1 | `/contabilidad/cotizacion-dolar/` carga | ☐ | |
| B2 | Sugerencia BCRA o mensaje fail-soft | ☐ | |
| B3 | Aceptar sugerido (staging) → `cotizacion.ValorPesos` actualizado | ☐ | SQL §1.3 post-acción |
| B4 | VMM TC vacío usa nuevo vigente | ☐ | |

---

## Acta de resultados

| Campo | Valor |
|-------|-------|
| Fecha | _pendiente_ |
| Entorno (URL) | _pendiente_ |
| Ejecutor | _pendiente_ |
| Período probado | _pendiente_ |
| Marca(s) | _pendiente_ |
| Delta KPI vs SQL (%) | _pendiente_ |
| Incidencias / tickets | _pendiente_ |
| Aprobado smoke A1 | ☐ Sí / ☐ No — _pendiente_ |

**Criterio A1 done:** SQL §1.2 anotado + UI desktop D3–D4 dentro de tolerancia acordada + checklist PWA M1 sin divergencia numérica; acta completada.
