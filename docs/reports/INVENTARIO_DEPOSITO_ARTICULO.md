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
| Menú **Reports → Producción / stock → Inventario por depósito** | Dashboard del slug |
| Menú **MPR → Reportes → Inventario por depósito** | Mismo deep-link |
| Catálogo `/reports/` | Tarjeta del informe |
| Hub legacy `/mpr/reportes/?grupo=demanda&reporte=inventario_deposito` | **302** al dashboard |

**Permisos:** `reports.view_operational` **o** `mpr.reportes` **o** `mpr.ver`.

## UI

Pantalla dedicada (sin tabs del hub MPR ni Desde/Hasta compartidos):

- Hero + KPIs (total docenas, depósitos, filas)
- Filtros: fecha de corte, depósitos, marcas, artículo, Incluir 2da (default No)
- Tabla jerárquica Depósito → Marca → Artículo/Talle/Stock/UM/Docenas
- Export **Excel** vía `POST /api/reports/export/?type=xlsx` (sin CSV)

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
