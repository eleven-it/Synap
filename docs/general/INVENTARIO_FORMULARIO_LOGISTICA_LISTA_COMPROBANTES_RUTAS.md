# Inventario — `logistica_lista_comprobantes_rutas.php` (lista comprobantes en rutas)

**Metodología:** `docs/general/INVENTARIO_MIGRACION_FORMULARIOS.md`.  
**Origen:** `mayoristapp/logistica_lista_comprobantes_rutas.php` + `mayoristapp/relay-logistica-comprobantes.php` (lógica y AJAX).  
**Fecha:** 2026-04-09.

**Nota de migración:** este inventario describe el **origen VB/PHP** para no perder capacidades. La solución Synap **adapta** UI y APIs al módulo Reports; solo debe mantener la **lógica de negocio** equivalente (ver `docs/ecom/PLAN_LOGISTICA_LISTA_COMPROBANTES_RUTAS.md` §0). **Synap (2026-04-12):** estado de entrega en pantalla con **dos** valores (**Entregado** / **No entregado**); sin modo «Buscar por número», solo período de fechas.

---

## 1. Componentes en pantalla principal (PHP)

| # | Tipo origen | Etiqueta / texto | Id / nombre | Comportamiento |
|---|-------------|------------------|-------------|----------------|
| 1 | Panel colapsable | «Parámetros» + icono ángulo | `#parametrosInformes` | Alterna visibilidad de `.panelesBloqueInforme`. |
| 2 | Text + hidden | Cliente | `#inputClientes`, `#inputClientesId` | jQuery UI autocomplete → `relay-logistica-comprobantes.php?action=obtenerClientes&q=…` (mín. 2 caracteres, hasta 7 sugerencias). |
| 3 | Text + hidden | Ruta (hoja de ruta) | `#inputRutas`, `#inputRutasId` | Autocomplete → `action=obtenerHojasRuta`. |
| 4 | Select | Estado (entrega) | `#entregadoRemito` | Opciones: Todos, Sin datos, Entregado, No Entregado. |
| 5 | Select | Buscar por | `#campoBusca` | Fecha (por defecto) o Número; muestra/oculta bloques `#buscaFecha` / `#buscaNumero`. |
| 6 | Date | Desde / Hasta | `#fechaDesde`, `#fechaHasta` | Valores iniciales PHP: primer y último día del mes actual (`Y-m-d`). Al focus se vacían (comportamiento legacy discutible). |
| 7 | Text | Nº comprobante | `#numeroComp` | Visible solo si «Buscar por» = Número. |
| 8 | Button | Buscar | `#botonBuscar` | GET AJAX `listarComprobantes=1` con filtros; deshabilita y spinner texto. |
| 9 | Título + tabla | «Comprobantes en ruta» | `#myTable` | DataTables: paginación, botones Excel/PDF, orden por columna 0 desc (tras recarga). |
| 10 | Modal | Actualizar comprobante | `#modal-actualiza` | Formulario entrega: `selectEntregado`, motivos, detalle, chofer (carga vía `obtenerChoferesTodos`; en validación JS se mencionaba chofer obligatorio pero el código de guardado PHP comentó el uso del chofer). |
| 11 | Modal | Ver más (detalle) | `#modal-ver-mas` | `obtenerInfo=1&codMovRemito=…` → secciones estado, trazabilidad, ruta/chofer, preparación. |

### 1.1 Código PHP cargado y no enlazado a la UI actual

- **Lista de viajadores** (`$arrVendedores`, SQL `viajantes` filtrado por puesto ≠ 1): se arma en PHP pero **no** hay `<select id="filtraVendedor">` en el HTML analizado.
- **JavaScript** aún referencia `$('#tipoPedido')`, `$('#estadoPedido')`, `$('#filtraVendedor')` solo para **títulos de exportación** PDF/Excel; al no existir esos nodos, jQuery devuelve selección vacía (título con segmentos en blanco). **No** se envían al relay como filtros SQL.

### 1.2 Autocomplete chofer

- Código comentado en la página para `#inputChoferes`; el relay expone `obtenerChoferes` y `obtenerChoferesTodos` (este último usado en el modal).

### 1.3 Motivos «no entrega» (hardcoded en PHP)

Array en la página: «No se encuentra en domicilio», «Error de facturación», «Error de mercadería», «Mercadería defectuosa». En Synap deben conservarse como **mismas opciones de negocio** (lista equivalente o fuente única configurable); la presentación (select, chips, etc.) es libre.

---

## 2. Tabla de resultados (HTML generado por relay)

**Función usada en JSON:** `armoTablaComprobantes` (versión «móvil» en nombre; es la que devuelve el listado). Existe `armoTablaComprobantesDesktop` pero **no** se invoca en `listarComprobantes`.

Columnas efectivas (PHP): Fecha remito, bloque comprobante (nº remito, total, factura si hay, cliente), Estado (tres valores en relay), acciones (editar si aplica, «ver más»). En Synap la columna estado se unifica a **Entregado** / **No entregado**.

---

## 3. Comparación objetivo Synap (post-implementación)

| Legado | Synap (objetivo) |
|--------|------------------|
| Panel parámetros + DataTables + jQuery UI | Informe **legacy del módulo Reports:** `/reports/dashboard/comprobantes-rutas/`, cabecera y patrones de `dashboard_detail.html` + filtros colapsables. |
| Autocomplete jQuery UI | Endpoints GET bajo **`/api/reports/…`** (misma sesión y permisos `reports.view_operational` que el resto de informes), debounce y teclado. |
| Tabla HTML + DataTables | Tabla responsive con **agrupación** configurable y búsqueda predictiva; datos vía **`POST /api/reports/query/`** (`slug` del informe), no relay ecom. |
| Modales inline | Diálogos accesibles (modal Synap) con mismos campos y validaciones alineadas al PHP vigente. |
| Export Excel/PDF | Mismo patrón que otros legacy en Reports (export Excel desde dashboard si está habilitado para el slug); CSV/PDF según implementación del módulo. |
| Conexión MySQL | **`get_mysql_pool()`** (`reports.services.connection_pool` → `core.mysql_pool`) con `base_empresa` de `session['user']`, igual que `pedidos-pendientes`, BO, ventas netas, etc. |

---

## 4. Referencias

- Especificación funcional y API: `docs/ecom/SPEC_LOGISTICA_LISTA_COMPROBANTES_RUTAS.md`.  
- Plan de migración: `docs/ecom/PLAN_LOGISTICA_LISTA_COMPROBANTES_RUTAS.md`.  
- Casos de prueba: `docs/ecom/TEST_LOGISTICA_LISTA_COMPROBANTES_RUTAS.md`.
