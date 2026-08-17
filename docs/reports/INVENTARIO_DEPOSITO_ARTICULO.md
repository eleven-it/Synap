# Inventario por depósito (catálogo Reportes)

**Slug:** `inventario-deposito-articulo`  
**Ruta canónica:** `/reports/dashboard/inventario-deposito-articulo/`  
**Atajo:** `/reports/inventario-deposito-articulo/`  
**Change:** `reports-inventario-deposito-catalogo` (oleada 1)

Motor de negocio: [`docs/mpr/INVENTARIO_DEPOSITO_ARTICULO.md`](../mpr/INVENTARIO_DEPOSITO_ARTICULO.md)  
(`mpr.services_inventario_deposito`, docenas 12/6/4, corte `stock.Fecha`).

## Acceso

| Canal | Destino |
|-------|---------|
| Menú **Stock → Consultas → Inventario por depósito** | Dashboard del slug |
| Catálogo `/reports/` | Tarjeta del informe |
| Hub legacy `/mpr/reportes/?grupo=demanda&reporte=inventario_deposito` | **302** al dashboard |

No hay ítem en el menú MPR ni en Reports: el acceso de menú es solo Stock.

**Permisos:** `reports.view_operational` **o** `mpr.reportes` **o** `mpr.ver`.

## UI

Usa el chrome estándar de Synap Reports en `reports/dashboard_detail.html` (sin tabs del hub MPR ni Desde/Hasta compartidos):

- Hero con **Actualizar**, **Exportar Excel**, **Mostrar/Ocultar filtros**, **Tiempo real** y **Pantalla completa**.
- Panel de filtros colapsable: fecha de corte, depósitos y marcas con tags, artículo e Incluir 2da selección (default No).
- Resumen `#report-summary` con total docenas, depósitos y filas.
- Modal compartido durante la consulta y tabla jerárquica dedicada Depósito → Marca → Artículo/Talle/Stock/UM/Docenas.
- Exportación **Excel** vía `POST /api/reports/export/?type=xlsx` con los filtros vigentes (sin CSV).

## Distinto de `stock-existencias`

| | Inventario por depósito | Stock existencias |
|--|-------------------------|-------------------|
| Jerarquía | Depósito → Marca → Artículo | Artículo (+ detalle depósitos) |
| Docenas MPR 12/6/4 | Sí | No |
| Corte a fecha | Sí | No (saldo actual) |

## Playbook oleadas 2–4 (hub MPR restante)

1. **Oleada 2 — Demanda:** UI catálogo para `mpr-brecha-demanda` y `mpr-pedidos-estado`; alta `stock-por-deposito` y `bajo-minimo`; redirects hub.
2. **Oleada 3 — Trazabilidad:** UI `mpr-movimientos-produccion`; alta `kardex-articulo`, `mpr-timeline`, `mpr-conciliacion`.
3. **Oleada 4 — Producción:** resumen diario, operarios, cadena, pendiente (período y docenas/pares **en el informe**).
4. **Cierre:** `/mpr/reportes/` → catálogo filtrado tag `mpr`; apagar chrome hub.
