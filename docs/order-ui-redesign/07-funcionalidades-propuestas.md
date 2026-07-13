# 07 · Funcionalidades propuestas — Clasificación

- **Fecha:** 10/07/2026
- **Pantalla:** `/ecom/mayoristapp/compra/`
- **Objetivo:** clasificar cada propuesta según su **viabilidad respecto al backend actual**, respetando que el rediseño es de **presentación** y que precios/totales siempre vienen del backend (`serializar_carrito`).

## Categorías

- **🟢 Solo Frontend** — presentación/estado en cliente (localStorage, UI, a11y). Cero backend.
- **🔵 Compatible backend actual** — la API/estado ya existe; falta exponerlo/usarlo en UI.
- **🟡 Requiere extensión backend** — necesita nuevo endpoint/campo/lógica de servidor.
- **🟠 Requiere validación de negocio** — antes de diseñar, producto/negocio debe definir reglas.
- **⚪ Recomendación futura** — deseable, fuera del alcance inmediato.

> Regla transversal: ninguna funcionalidad puede calcular precios/totales en el frontend. Cuando una función "muestra" importes, lo hace con datos del backend vía `money()`.

---

## 1. Tabla maestra

| # | Funcionalidad | Categoría | Base real / nota |
|---|---|---|---|
| 1 | Clientes recientes (en pantalla) | 🟢 Solo Frontend | `localStorage`, últimos clientes usados por este operador |
| 2 | Productos frecuentes / más vendidos | 🔵 Compatible | El listado ya acepta filtros/orden; existe API de catálogo (`urls.listado`) |
| 3 | Repetir pedido | 🔵 Compatible (ya existe) | `repetir_pedido_modal.js`, `cargar_desde_pedido` |
| 4 | Plantillas de pedido | 🟡 Extensión backend | Requiere persistir plantillas (modelo/endpoint) |
| 5 | Favoritos (productos) | 🟢 Solo Frontend (v1) / 🟡 (multi-dispositivo) | v1: `localStorage`; sincronizado: backend |
| 6 | Barcode / escaneo | 🟢 Solo Frontend | Input ya lo insinúa; falta foco + match exacto por código |
| 7 | Atajos de teclado | 🟢 Solo Frontend | ↑↓Enter ya existe; ampliar (foco búsqueda, confirmar) |
| 8 | Autoguardado (borrador) | 🔵 Compatible (ya existe) | Carrito es borrador EcomCart; falta indicador visual |
| 9 | Diálogo "cambios sin guardar" | 🟢 Solo Frontend | `beforeunload` + modal del canon |
| 10 | Stock (mostrar/alertar) | 🔵 Compatible | Stock ya viene en resultados y por línea |
| 11 | Fecha de entrega | 🟠 Validación de negocio | Backend a veces la soporta; definir si es editable y su semántica |
| 12 | Cross-sell / sugeridos | 🟡 Extensión backend | Requiere endpoint de recomendación |
| 13 | Historial de precios (preview repetir) | 🔵 Compatible (parcial) | Al repetir ya se recalcula; mostrar diferencia origen vs actual |
| 14 | Deuda / saldo cliente | 🔵 Compatible (ya existe) | `creditoWidget` (saldo, límite, autorización) |
| 15 | Límites de descuento | 🟠 Validación de negocio | Definir topes por perfil/cliente; hoy desc. pie libre |
| 16 | Margen (visibilidad) | 🟡 Extensión backend + 🟠 negocio | Requiere costo por artículo y política de quién lo ve |
| 17 | Carga masiva | 🟡 Extensión backend | Endpoint para alta múltiple de líneas |
| 18 | Pegado desde planilla | 🟢 Solo Frontend (parseo) + 🔵 alta línea | Parsear en cliente; agregar con API actual ítem a ítem |
| 19 | Selector UOM / embalaje | 🔵 Compatible (API ready) | API acepta `tipo_unidad`+`multiplicador`; UI hoy fuerza "Unidad" |
| 20 | Alta rápida de cliente | 🔵 Compatible (API existe) | Falta exponer en compra; hoy no está en UI |
| 21 | Domicilio / dirección de entrega | 🔵 Compatible (API existe) | Hoy solo "forma de entrega" texto libre |
| 22 | Condición de venta | 🟠 Validación de negocio | Definir catálogo y default por cliente |
| 23 | Selector de lista de precios | 🟠 Validación de negocio | Backend a veces sí; hoy la lista deriva del cliente |
| 24 | Sucursal / depósito | 🟠 Validación de negocio | Impacta stock/comprobante; definir reglas |
| 25 | Moneda | 🟠 Validación de negocio | Multi-moneda no en UI; requiere definición |
| 26 | Variantes de artículo | 🟡 Extensión backend | Requiere modelo/endpoint de variantes en catálogo |
| 27 | Descuento por renglón (UI) | 🟠 Validación de negocio | Hoy solo desc. al pie; definir si se permite por línea |
| 28 | Notas internas | 🟡 Extensión backend | Distinto de "observaciones"; requiere campo dedicado |
| 29 | Stock comprometido | 🟡 Extensión backend | Requiere dato de reservas/pendientes |
| 30 | Modales del canon (no nativos) | 🟢 Solo Frontend | Reemplazar `confirm()`/`prompt()` |
| 31 | `aria-live` + a11y de modal | 🟢 Solo Frontend | focus trap, `role="dialog"` |
| 32 | Summary sticky / bottom bar mobile | 🟢 Solo Frontend | CSS `sticky` + estructura |

---

## 2. 🟢 Solo Frontend (prioridad para el rediseño)

Estas se pueden ejecutar sin tocar backend y son el núcleo del rediseño de presentación.

### 2.1 Clientes recientes (localStorage)
Guardar en `localStorage` los últimos N clientes seleccionados por el operador (código + label). Mostrar como accesos rápidos en el CustomerSelector. **No** sustituye la búsqueda; la acelera. No expone datos sensibles más allá de nombre/código ya visibles.

### 2.2 Barcode / escaneo
- Foco automático al buscador al cargar la pantalla (operador puede escanear de inmediato).
- Detectar entrada tipo lector (ráfaga + Enter) y, si el término coincide **exactamente** con un código, agregar directo; si no, mostrar resultados. Todo con la API de búsqueda actual (`urls.listado`).
- Feedback claro "código no encontrado".

### 2.3 Atajos de teclado (ampliar)
Conservar ↑↓Enter/Esc. Añadir: `/` o `F2` enfocar búsqueda; `Alt+C` confirmar; `Alt+N` nuevo comprobante. Documentar en un hint discreto.

### 2.4 Indicador de borrador + autoguardado
El carrito ya persiste (EcomCart). Añadir badge "Borrador guardado" en el summary y microcopy. Sin nueva lógica de servidor.

### 2.5 Diálogo "cambios sin guardar"
Al navegar fuera con **cliente activo** (que se perderá por diseño), mostrar modal del canon. El carrito borrador se conserva; se comunica explícitamente.

### 2.6 Pegado desde planilla (parseo cliente)
Permitir pegar filas "código<TAB>cantidad"; parsear en el cliente y agregar ítem a ítem con la API actual de carrito. La parte de **parseo** es solo frontend; el **alta** usa el endpoint existente (por eso también figura como 🔵 en la tabla).

### 2.7 Favoritos (v1 local)
Marcar productos favoritos en `localStorage` para acceso rápido. La versión multi-dispositivo sería 🟡 (persistencia backend).

### 2.8 Modales del canon + a11y
Reemplazar `confirm()`/`prompt()` por `ConfirmModal`; agregar `aria-live`, focus trap, `role="dialog"`. Summary sticky y bottom bar mobile (CSS).

---

## 3. 🔵 Compatible con backend actual (exponer/usar lo que ya hay)

### 3.1 Selector UOM / embalaje
**El API ya acepta `tipo_unidad` y `multiplicador`** (método `agregar`, `compra_mayorista.html` 655–666) y expone `presentacion.opciones`. Hoy la UI **siempre** envía "Unidad" (`agregarDesdeBusqueda`, 629–641) y hay estado huérfano (`embalaje`, `mostrarEmbalaje`). Añadir `UomSelector` (ver `06`) activa la capacidad **sin backend nuevo**.

### 3.2 Alta rápida de cliente
El backend cuenta con alta de cliente (usada en otros flujos). Exponer en compra un modal "Nuevo cliente" que use el endpoint existente y seleccione al cliente creado. Requiere confirmar el endpoint exacto, pero **no** lógica nueva de negocio.

### 3.3 Domicilio / dirección de entrega
El backend soporta direcciones de cliente. Reemplazar/complementar el campo "forma de entrega" (texto libre) por un selector de domicilio del cliente + texto. Consumo de API existente.

### 3.4 Productos frecuentes / más vendidos
Usar el catálogo existente con orden/filtro por ventas para poblar un carrusel/lista de "frecuentes del cliente" cuando hay cliente activo. Consumo de `urls.listado` con filtros.

### 3.5 Repetir pedido (ya existe)
Mantener. Mejora de presentación: integrar en el header y mostrar preview con precios actualizados.

### 3.6 Historial de precios / diferencia al repetir
Al repetir, el backend ya recalcula. Mostrar (solo presentación) un indicador por línea "precio actualizado" comparando el precio del origen (que el preview ya trae) con el actual. Si el preview no incluye el precio origen, degrada a solo "precios actualizados" (comportamiento actual).

### 3.7 Deuda / crédito
`creditoWidget` ya provee saldo, límite y autorización. Ubicarlo mejor (header/summary) y mantener la regla: pedido se registra igual aunque no esté autorizado.

### 3.8 Stock
Ya visible en resultados y carrito. Añadir badge "Sin stock/Bajo" informativo (sin bloquear salvo que el backend lo indique).

---

## 4. 🟡 Requiere extensión backend

| Funcionalidad | Qué falta | Nota de diseño |
|---|---|---|
| Plantillas de pedido | Modelo + endpoints CRUD de plantillas | UI puede diseñarse en paralelo, gated por feature flag |
| Cross-sell / sugeridos | Endpoint de recomendación por producto/cliente | Zona reservada en la ficha de producto |
| Carga masiva | Endpoint de alta múltiple de líneas | Complementa el pegado desde planilla (evita N requests) |
| Margen | Costo por artículo + política de visibilidad | Solo perfiles autorizados |
| Variantes | Modelo/endpoint de variantes | Selector en resultado y línea |
| Notas internas | Campo dedicado (≠ observaciones) | Visible solo a interno |
| Stock comprometido | Dato de reservas/pendientes | Mostrar disponible real |
| Favoritos multi-dispositivo | Persistencia de favoritos por usuario | Evolución de la v1 local |

Estas propuestas se documentan aquí para hoja de ruta, pero **no** forman parte del rediseño de presentación inmediato.

---

## 5. 🟠 Requiere validación de negocio

Antes de diseñar UI, producto/negocio debe definir reglas:

- **Fecha de entrega:** ¿editable? ¿validaciones (no pasada, hábiles)? ¿afecta stock/logística?
- **Límites de descuento:** topes por perfil/cliente/artículo; hoy el desc. al pie es libre.
- **Condición de venta:** catálogo, default por cliente, impacto en comprobante.
- **Selector de lista de precios:** hoy la lista deriva del cliente; ¿se permite override manual? ¿quién?
- **Sucursal / depósito:** impacto en stock y numeración; reglas por usuario.
- **Moneda:** ¿multi-moneda? conversión, redondeo, quién define.
- **Descuento por renglón (UI):** ¿se habilita además del desc. al pie? interacción entre ambos.

Para todas: mientras no haya definición, **no** se agregan a la UI (coherente con "NO en UI aunque el backend a veces lo soporte").

---

## 6. ⚪ Recomendaciones futuras

- Guardar pedido como plantilla y compartir plantillas por equipo.
- Sugeridos inteligentes basados en histórico del cliente (requiere backend + datos).
- Modo "kiosco/mostrador" de alta velocidad con foco permanente en escaneo.
- Sincronización offline del borrador para conectividad intermitente.
- Vista de comparación de precios entre listas (si negocio habilita override).

---

## 7. Priorización sugerida (solo presentación / compatible)

| Prioridad | Funcionalidades |
|---|---|
| **P0** | Summary sticky/bottom bar (32), Modales del canon + a11y (30, 31), Selector UOM (19), Autoguardado visible (8) |
| **P1** | Barcode + foco (6), Atajos (7), Alta rápida cliente (20), Domicilio (21), Clientes recientes (1), Deuda ubicación (14) |
| **P2** | Productos frecuentes (2), Diferencia de precio al repetir (13), Diálogo cambios sin guardar (9), Stock badges (10), Favoritos local (5) |
| **P3** | Pegado desde planilla (18, parte FE) |

Todo lo P0–P2 es **🟢 Solo Frontend** o **🔵 Compatible** — ejecutable sin tocar backend, modelos, APIs, cálculos ni permisos.
