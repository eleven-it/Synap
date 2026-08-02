# Especificación: Informe «Ventas marcas mensual»

Slug canónico: **`ventas-marcas-mensual`**. Nombre en catálogo/UI: **Ventas marcas mensual**.

**URL del dashboard:** `/reports/dashboard/ventas-marcas-mensual/` (nombre `reports:dashboard_detail`). Atajo: `/reports/ventas-marcas-mensual/` redirige a la URL canónica. Tras desplegar, ejecutar migraciones (`0033_add_ventas_marcas_mensual_report`). Si la fila aún no existe (p. ej. Staging sin migrate), `DashboardDetailView` llama a `ensure_ventas_marcas_mensual_report()` (`reports/services/ventas_marcas_mensual_seed.py`) para crearla en el primer acceso.

Documento para implementación y pruebas. Referencias: [PLAN_INFORME_VENTAS_MARCAS_MENSUAL.md](PLAN_INFORME_VENTAS_MARCAS_MENSUAL.md), [MAPEO_PUW_PUM_ADMINISTRANET.md](MAPEO_PUW_PUM_ADMINISTRANET.md).

**Estado:** Fase 1 + **Fase 2** (regalías, TC, proyección, deep-link Command Center) implementadas (29/07/2026).

---

## 1. Objetivo del producto

Informe **pivot mensual** de ventas por marca: filas **Vendedor → Cliente**, columnas **AñoMes** (`yyyyMM`), celdas con **unidades** (packs o docenas según toggle) y **facturación neta** de renglón (`PrecioNetoxR` con signo FA/NC).

Cubre la lógica de las hojas Excel PuW/PuM (plantilla BEST) leyendo **solo AdministraNET**. Sin históricos Excel.

---

## 2. Filtros

| Filtro | Control UI | Campo backend | Notas |
|--------|------------|---------------|-------|
| Período | Desde–hasta (dd/MM/yyyy) | `cc.Fecha` | `fecha_inicio_facturacion` / `fecha_fin_facturacion`; fallback `fecha_inicio` / `fecha_fin` |
| Marca | Multi-tags | `art.CodigoMarca` | `marcas_incluidos`; vacío = todas |
| SuperArt | Multi-tags `id_manual` | `art.id_manual IN (...)` | `superarts_incluidos` o `id_manuales`; vacío = todos |
| Unidades | Toggle packs / docenas | Solo presentación + SQL docenas | `modo_unidades`: `packs` (default) \| `docenas` |
| Sucursal / PV | Tags (familia VPV) | `cc.CodSucursal`, `cc.id_pv` | Opcional |
| Clientes incl/excl | Tags | `cc.Codigo` | Igual VO |
| Vendedores incl/excl | Tags | `cc.CodViajante` | Alcance comercial del usuario |
| **Tasa regalía (%)** | Input numérico | `tasa_regalia_pct` | Default **13** (= 13 %). Backend acepta también `tasa_regalia` = 0.13 |
| **TC** | Input numérico opcional | `tc` | Vacío → `SELECT ValorPesos FROM cotizacion WHERE id_cotizacion = 1`; fallback **14,5817** |
| **Incluir proyección** | Toggle Sí/No | `incluir_proyeccion` | `"1"` / `"0"`; default off |
| **Coef. proyección** | Input numérico | `coef_proyeccion` | Default **1,07**; solo si proyección ON |

Sección UI: **«Licencia y proyección»** en `filters_ventas_marcas_mensual.html`. Persistencia en `localStorage` como el resto de filtros.

**Fijos (sin UI):** `cc.Anulado='No'`, `cc.CodigoMovimiento<>0`, tipos FA/FB/FC/FE/FM + NC*, `st.Anulado='No'`, `st.TipoComp` ∈ Venta / Venta TPV / Devol - Cliente / ND Anul NC.

**Omitidos:** módulo/comprobante, tabla `mpr_costo_parametro` (fase posterior), depósitos.

---

## 3. KPIs de cabecera

Sobre el universo filtrado:

| KPI | Cálculo |
|-----|---------|
| Unidades / Docenas | `SUM(packs)` o `SUM(docenas)` según `modo_unidades` |
| Facturación | `SUM(signo × PrecioNetoxR)` |
| Precio medio | Facturación / Unidades (0 si unidades = 0) |
| **Regalías** | Facturación × tasa_regalia |
| **Regalías / TC** | Regalías / TC (0 si TC ≈ 0) |

En `meta.extra.kpis` también: `tasa_regalia`, `tc` (valores efectivos usados).

Grid UI: 5 tarjetas (Unidades, Facturación, Precio medio, Regalías, Regalías / TC).

---

## 4. Matriz

| Eje | Contenido |
|-----|-----------|
| Filas | Vendedor (`CodViajante` / nombre) → Cliente (`Codigo` / `nombre_cliente`) |
| Columnas | Mes `yyyyMM` ascendente + **Total** |
| Celdas (Fase 1) | Unidades + Facturación (`u`, `f`) |
| Celdas (proyección ON) | + **U proy** (`pu`) + **$ proy** (`pf`); estilo más suave |
| Expansión | Colapsar/expandir por vendedor; estado en `localStorage` |

**Proyección:** `pu = CEILING(u × coef)`; `pf = round(f × coef, 2)`. Helpers testables: `ceil_proy_unidades`, `aplicar_proyeccion_filas`.

**Cap blando:** si hay más de 24 meses distintos, truncar a los 24 más recientes y avisar en `meta.extra.aviso_meses`.

---

## 5. Exportación Excel

Hoja plana (no pivot Excel nativo):

| Columna | Origen |
|---------|--------|
| Vendedor código | `cod_viajante` |
| Vendedor | `nombre_vendedor` |
| Cliente código | `codigo_cliente` |
| Cliente | `nombre_cliente` |
| AñoMes | `anio_mes` |
| Unidades / Docenas | según `modo_unidades` |
| Facturación | `facturacion` |
| Unidades proy | `unidades_proy` (solo si proyección activa) |
| Facturación proy | `facturacion_proy` (solo si proyección activa) |

Nombre archivo: `Ventas_marcas_mensual_{desde}_{hasta}.xlsx` (sin cambio).

---

## 6. Contrato JSON (`meta.extra`)

```json
{
  "modo_unidades": "packs",
  "meses": ["202607", "202608"],
  "kpis": {
    "unidades": 0,
    "facturacion": 0,
    "precio_medio": 0,
    "regalias": 0,
    "regalias_tc": 0,
    "tasa_regalia": 0.13,
    "tc": 14.5817
  },
  "proyeccion": { "activa": true, "coef": 1.07 },
  "filas": [
    {
      "tipo": "vendedor",
      "cod": 1,
      "nombre": "…",
      "totales_mes": { "202607": { "u": 0, "f": 0, "pu": 0, "pf": 0 } },
      "total": { "u": 0, "f": 0, "pu": 0, "pf": 0 },
      "clientes": [
        {
          "cod": "C1",
          "nombre": "…",
          "valores_mes": { "202607": { "u": 0, "f": 0, "pu": 0, "pf": 0 } },
          "total": { "u": 0, "f": 0, "pu": 0, "pf": 0 }
        }
      ]
    }
  ]
}
```

`pu`/`pf` y `proyeccion` solo cuando `incluir_proyeccion` está activo. `data[]` en `QueryResult`: filas planas para export.

---

## 7. Command Center (Fase 2)

- Enlace **«Ventas marcas mensual»** en área Ventas del Command Center.
- Navegación full-page (no modal) con `fecha_inicio`, `fecha_fin` y `sucursal` en query string.
- Al abrir el informe, `dashboard.js` aplica esos parámetros al período de facturación y sucursal.

---

## 8. Escenarios (Given / When / Then)

- **G1:** Dado el slug `ventas-marcas-mensual`, cuando se abre el informe, entonces se muestran KPIs (unidades/docenas, facturación, precio medio, regalías, regalías/TC) y la matriz Ven→Cliente×Mes; no hay diálogos nativos del navegador.
- **G2:** Dado `modo_unidades=packs`, cuando se consulta con marca PUM en un período con ventas, entonces las unidades coinciden con `SUM(Cantidad)` con signo FA/NC en AdministraNET.
- **G3:** Dado `modo_unidades=docenas`, cuando hay renglones con U.M. P3, entonces docenas = cantidad / 4 (factor mapa P1→12, P2→6, P3→4, P6→2, CU→1).
- **G4:** Dado un vendedor con dos clientes, cuando se expande el vendedor en la matriz, entonces se ven filas cliente con valores por mes y total fila.
- **G5:** Dado tiempo real desactivado, cuando el usuario cambia un filtro, entonces los datos no se recargan hasta «Actualizar» (política `isInformeQuerySoloManualORealtime`).
- **G6:** Dado export con los mismos filtros que la consulta en pantalla, entonces el Excel plano tiene columnas Ven / Cliente / AñoMes / Unidades / Facturación coherentes con `data[]`.
- **G7:** Dado un período con más de 24 meses distintos, cuando se ejecuta la consulta, entonces `meta.extra.aviso_meses` informa el truncamiento y la matriz muestra como máximo 24 columnas de mes.
- **G8:** Dado `tasa_regalia_pct=13` y facturación 1000, entonces regalías = 130 y regalías_tc = 130 / TC efectivo.
- **G9:** Dado `incluir_proyeccion=1` y `coef_proyeccion=1.07`, entonces `ceil(12 × 1.07) = 13` en unidades proy y la matriz muestra 4 subcolumnas por mes.
- **G10:** Dado deep-link desde Command Center con `fecha_inicio`/`fecha_fin`, entonces el informe precarga el período de facturación y sucursal si viene en URL.

---

## 9. Rollback

Eliminar `ReportDefinition`, rama en `query_runner`, runner, plantilla, JS, tests y este archivo. No requiere migración de datos de negocio.

---

## 10. Relación con otros informes

- Reutiliza parsers de período, sucursal/PV, clientes/vendedores y whitelist FA/NC de VO/VPV.
- **No** reutiliza árbol VO (objetivo, REM, PEA, BO).
- TC desde maestro `cotizacion` (sin `mpr_costo_parametro`).
