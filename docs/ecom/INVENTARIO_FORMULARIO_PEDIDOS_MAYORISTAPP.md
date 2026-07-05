# Inventario — Pedidos del vendedor (mayoristapp)

**Origen PHP:** `lista-pedidos-vendedor.php` (+ datos vía `relay-pedidos.php`)  
**Destino Synap:** `GET /ecom/mayoristapp/pedidos-vendedor/`  
**Patrón UI:** `presupuestos_vendedor.html` (fuente verdad reports/MPR)  
**API:** `POST /ecom/api/v1/mayoristapp/comprobantes/pedidos/` (REST v1, sin `ajax=1`)

---

## Componentes origen vs Synap

| # | Componente PHP | Tipo | Synap | Estado |
|---|----------------|------|-------|--------|
| 1 | Título "Pedidos del vendedor" | Label / H1 | Hero slate/sky `pedidos_vendedor.html` | ✅ |
| 2 | Filtro vendedor/viajante | Combo | `<select id="filtraVendedor">` | ✅ |
| 3 | Filtro clientes (todos/seleccionado) | Combo | `<select id="listaTodos">` | ✅ |
| 4 | Filtro estado pedido | Combo | `<select id="estadoPedido">` | ✅ |
| 5 | Buscar por (fecha/número/tipo) | Combo | `<select id="campoBusca">` | ✅ |
| 6 | Fecha desde / hasta | Date | `<input type="date">` ×2 | ✅ |
| 7 | N.º comprobante | TextBox | `<input id="numeroComp">` | ✅ |
| 8 | Tipo pedido (Sistema/Web) | Combo | `<select id="tipoPedido">` | ✅ |
| 9 | Botón Buscar | Acción | `#botonBuscar` | ✅ |
| 10 | Botón Actualizar | Acción | `data-refresh-pedidos` | ✅ |
| 11 | Export Excel | Acción | CSV client-side `data-export-excel-pedidos` | ✅ (F1 mínimo) |
| 12 | Tiempo real + intervalo | Toggle + combo | Patrón `filters_interval.html` | ✅ |
| 13 | Pantalla completa | Botón | `data-fullscreen-toggle` | ✅ |
| 14 | Tabla listado | DataTable → tabla Synap | `#tabla-pedidos` | ✅ |
| 15 | Columnas: fecha, nº, cliente, cond., subtotal, IVA, total, tipo, estado, autorizado, entrega, viajante, anulado | Grid | Mismas columnas | ✅ |
| 16 | Fila anulada en rojo | Estilo | Clase `text-red-600` si Anulado=Si | ✅ |
| 17 | Totales pie tabla | Footer | `#tabla-pedidos-foot` | ✅ |
| 18 | Ver PDF comprobante (ícono fila) | Link | — | ⏳ F1-api-gaps (mail/PDF) |
| 19 | Anular pedido | Botón | — | ⏳ F1-api-gaps (API existe) |
| 20 | Autocomplete nº (sugerencias) | AJAX | API v1 sugerencias | ⏳ UI opcional F1.1 |
| 21 | `campoAnulado` Si/No | Combo | — | ⏳ Solo `lista-pedidos-total` (gerencial) |
| 22 | `tipoInforme` detallado | Combo | — | ⏳ F1-api-gaps |
| 23 | Export PDF servidor | Acción | — | ⏳ F1-api-gaps |

---

## Gaps aceptados en piloto F1

- PDF individual y anulación desde grilla: API legacy disponible; UI en change siguiente.
- Listado gerencial (`lista-pedidos-total.php`): misma base con filtros extra en F1.1.
- Presupuestos sigue en legacy `ajax=1`; pedidos usa **v1** como piloto REST.

---

## Comparación API

| Campo request | PHP (camelCase) | v1 (snake_case) |
|---------------|-----------------|-----------------|
| vendedor | `true` | `vendedor: true` |
| campoBusca | Fecha / NroComprobante / TipoPedido | `campo_busca` |
| fechaDesde/Hasta | dd/mm o ISO | `fecha_desde` / `fecha_hasta` |
| filtraVendedor | código o todos | `filtra_vendedor` |
| listaPed | cliente / todos | `lista_ped` |

Response v1: `{ ok, page, page_size, total, results: [...] }` (legacy: `{ total, filas }`).
