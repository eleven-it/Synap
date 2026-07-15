# Exploración — Inventario tabla MPR en módulo Stock

**Change:** `stock-inventario-tabla-mpr`  
**Fecha:** 06/07/2026  
**Solicitante:** Producto / MPR e inventario

---

## 1. Pedido

Nueva consulta de inventario en formato **tabla pivote** en el módulo Stock:

| Aspecto | Valor |
|---------|--------|
| Ruta nueva | `/stock/inventario/` |
| Reemplaza menú | Subítem **Inventario** hoy en `stock:consulta_ficha_stock` (`/stock/consulta-ficha/`) |
| Columna artículo | `articulo.id_manual` + `" - "` + `articulo.CodArtProv` |
| Columnas stock | Producción · Semi elaborado · 2da Selección · Terminado · **Consolidado** |
| Filtros | Buscador predictivo por artículo · filtro por **marca** |
| Audiencia | Analista MPR e inventario |

---

## 2. Estado actual

### Menú y rutas

| Artefacto | Ubicación |
|-----------|-----------|
| Menú «Inventario» | `core/utils/utils.py` → `url: stock:consulta_ficha_stock`, permiso `stock.consultas` |
| Vista stub | `stock/views.py` → `consulta_ficha_stock_view` |
| Plantilla | `stock/templates/stock/consulta_ficha_stock.html` — texto «En construcción» |
| URL | `stock/urls.py` → `consulta-ficha/` |

### Consulta ficha legacy (VB6)

`Info_Stock.frm` / inventario físico es **otro flujo** (conteo, `inventario` / `inventario_temp`). La pantalla Synap «Consulta Ficha» nunca se implementó; el stub es placeholder.

### Código reutilizable

| Pieza | Archivo | Relevancia |
|-------|---------|------------|
| Stock por depósito MPR | `mpr/services.py` → `reporte_mpr_stock()` | Lee `stock_deposito` + `deposito.tipo_mpr`; **no** filtra `suma_stock` hoy |
| Pivote docenas/unidades | `mpr/reportes_presentacion.py` → `preparar_stock_por_deposito()` | Pivote por **id_deposito**, no por `tipo_mpr` |
| Tipos MPR canónicos | `mpr/pipeline.py` → `TIPOS_QUE_SUMAN_STOCK`, `ORDEN_ETAPAS_MPR` | Consolidado = suma de Producción + 2da + Semi + Terminado (sin Scrap) |
| Existencias + marca | `reports/services/stock_existencias_query.py` | Filtro `marcas_incluidos`, búsqueda server-side, JOIN `marca` |
| Búsqueda artículo stock | `stock/api_views.py` → `api_ingreso_articulos` | Permiso `stock.crear_movimiento` — **no** sirve para consultas |
| Buscador tabla client-side | `mpr/templates/mpr/reportes/_busqueda_tabla_articulos.html` | Patrón UX canon (Alpine, sugerencias) |
| Tabla stock MPR | `mpr/templates/mpr/reportes/partials/stock.html` | Sticky columna artículo, scroll horizontal, docenas/unidades |

### Esquema datos

| Campo | Tabla | Notas |
|-------|-------|-------|
| `id_manual` | `articulo` | Código manual usuario; Synap: `str_codigo_manual_articulo` |
| `CodArtProv` | `articulo` | Código proveedor |
| `CodigoMarca` | `articulo` | FK → `marca.CodMarca` |
| `tipo_mpr` | `deposito` | `Produccion`, `SemiElaborado`, `2daSeleccion`, `Terminado`, … |
| `suma_stock` | `deposito` | Solo depósitos con `'Si'` entran al consolidado operativo |
| `saldo` | `stock_deposito` | Por `id_articulo` × `id_deposito` |

**Regla negocio MPR:** un depósito por `tipo_mpr` (validado en `actualizar_deposito_tipo_mpr`). Si hubiera dos depósitos con el mismo tipo, las columnas deben **sumar** saldos del tipo.

---

## 3. Modelo de datos propuesto

```text
Por cada artículo (filtros marca + búsqueda):
  col[Produccion]      = SUM(saldo) WHERE deposito.tipo_mpr = 'Produccion' AND suma_stock = 'Si'
  col[SemiElaborado]   = idem Semi elaborado
  col[2daSeleccion]    = idem 2da Selección
  col[Terminado]       = idem Terminado
  col[Consolidado]     = suma de las 4 anteriores (alineado TIPOS_QUE_SUMAN_STOCK sin Scrap)
```

Etiquetas UI (español con tilde donde aplique):

| `tipo_mpr` DB | Encabezado columna |
|---------------|-------------------|
| `Produccion` | Producción |
| `SemiElaborado` | Semi elaborado |
| `2daSeleccion` | 2da Selección |
| `Terminado` | Terminado |
| — | Consolidado |

---

## 4. Opciones de implementación

| Opción | Pros | Contras |
|--------|------|---------|
| **A — Servicio en `stock/`** + vista Django GET | Cohesión módulo Stock; permiso `stock.consultas`; sin acoplar MPR UI | Duplica algo de SQL de `reporte_mpr_stock` |
| **B — Reutilizar `reporte_mpr_stock` + pivote tipo_mpr en MPR** | Menos SQL nuevo | Inventario en menú Stock pero lógica en `mpr/` |
| **C — Informe `reports/` slug nuevo** | Relay API, export gerencial | Fuera del módulo Stock pedido por producto |

**Recomendación:** **Opción A** — `stock/services/inventario_tabla.py` (o `stock/services.py`) con función `consultar_inventario_por_tipo_mpr()`. Opcional: extraer helper SQL compartido con `reporte_mpr_stock` en `core/services/administranet_stock.py` si crece.

---

## 5. UX — dirección de diseño (Product Designer)

### Persona

**Ana, analista MPR:** revisa saldos por etapa del pipeline varias veces al día; compara Semi elaborado vs Terminado; filtra por marca de línea; busca un pack por código manual.

### Principios

| Principio | Aplicación |
|-----------|------------|
| Escaneo horizontal | Columnas fijas en orden pipeline (Producción → … → Consolidado) |
| Código primero | Primera columna `id_manual - CodArtProv` tabular, sticky |
| Consolidado destacado | Última columna con fondo sutil / negrita — total operativo |
| Filtros sin sorpresa | Marca + búsqueda arriba; botón «Aplicar» o auto-submit GET |
| Canon Synap | Patrones de `mpr/reportes/` y `reports/dashboard/` (no pantallas ventas) |

### Wireframe (borrador)

```text
[ Breadcrumb: Inicio / Stock / Inventario ]
[ Título: Inventario por etapa MPR ]

[ Filtros — barra sticky ]
  [ Marca ▼ todas ]  [ Buscar artículo…………… 🔍 ]  [ Limpiar ]
  [ Toggle: Unidades | Docenas ]  (pendiente confirmación producto)

[ Tabla scroll horizontal ]
  | Artículo (id_manual - CodArtProv) | Producción | Semi elaborado | 2da Selección | Terminado | Consolidado |
  | PACK-001 - PRV-88                 | 120        | 48             | 0             | 200         | **368**     |

[ Pie: N artículos · última actualización sesión ]
```

### Buscador predictivo

| Enfoque | Cuándo |
|---------|--------|
| **Server-side** (`GET ?q=` + API JSON) | Tabla grande; filtra antes de renderizar — recomendado |
| Client-side (como MPR reportes) | Solo si universo acotado (<500 filas) |

Reutilizar criterios de `stock_existencias_query` (id_manual, nombre, barras) y endpoint nuevo `stock/api/inventario/articulos/` con permiso `stock.consultas`.

---

## 6. Impacto archivos (estimado)

| Archivo | Cambio |
|---------|--------|
| `stock/urls.py` | `path("inventario/", …)` + API opcional |
| `stock/views.py` | `inventario_view` |
| `stock/services/inventario_tabla.py` | SQL + pivote |
| `stock/templates/stock/inventario.html` | UI tabla + filtros |
| `stock/api_views.py` | búsqueda artículos consultas |
| `core/utils/utils.py` | menú → `stock:inventario` |
| `stock/tests/` | URL, servicio pivote, permisos |
| `docs/stock/INVENTARIO_TABLA_MPR.md` | Documentación |

`/stock/consulta-ficha/`: redirect 301 a `/stock/inventario/` o mantener stub — **pendiente producto**.

---

## 7. Riesgos

| Riesgo | Mitigación |
|--------|------------|
| `tipo_mpr` no configurado en depósitos | Columna en 0; nota en UI si falta config MPR |
| `CodArtProv` vacío | Mostrar `id_manual` sin sufijo o `id_manual -` — **pendiente** |
| Volumen de filas | Paginación server-side (patrón `stock_existencias_query`) |
| Duplicar lógica MPR reportes stock | Spec única de consolidado referenciando `TIPOS_QUE_SUMAN_STOCK` |

---

## 8. Preguntas abiertas (producto)

Ver formulario de decisión en conversación. Bloqueantes para **spec**:

1. ¿Solo artículos con saldo ≠ 0 o incluir ceros?
2. ¿Toggle unidades / docenas?
3. ¿Búsqueda server-side vs filtro client-side sobre tabla completa?
4. ¿Redirect de `/stock/consulta-ficha/`?
5. ¿Descripción del artículo bajo el código en columna 1?
6. ¿Marca: select único o multi?
7. ¿Paginación (cuántas filas) o export CSV en v1?
