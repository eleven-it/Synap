# Tablero de producción — chrome denso (toolbar)

**Fecha:** 25/07/2026  
**Estado:** Especificado · implementado en `mpr/templates/mpr/tablero_produccion.html`  
**Plantilla:** `/mpr/tablero-produccion/`  
**Canon UI:** `docs/general/FUENTE_VERDAD_UI_REPORTES_MPR.md`  
**Relacionado:** [TABLERO_PRODUCCION_MODO_PACK_PAR.md](TABLERO_PRODUCCION_MODO_PACK_PAR.md), [NAVIGACION_MPR_ETAPA11.md](NAVIGACION_MPR_ETAPA11.md), [TABLERO_MPR_LAYOUT_DENSIDAD.md](TABLERO_MPR_LAYOUT_DENSIDAD.md)

## 1. Objetivo

Maximizar altura útil de la **tabla**: el chrome encima no debe ser un hero MPR de varias filas. La tabla es el producto; el encabezado es un *toolbar* operativo.

## 2. Flujo canónico de planta (UI viva)

| Orden | Pantalla | Rol |
|------:|----------|-----|
| 1 | **Tablero de producción** | Demanda, cupo Fabricando, envío |
| 2 | **Parte de producción** | Registrar producido |
| 3 | **Control de calidad** | Clasificar salida |

Cualquier UI de **OPT / ventana_pack** (y pantallas hermanas de demanda→OPT) que **no** aporte a ese flujo queda **deprecada** como referencia visual y como atajo del tablero, salvo que cubra un proceso MPR **no** resuelto por Tablero / Parte / CC (p. ej. armado de packs, configuración, reportes).

Ver §6.

## 3. Decisiones de producto (cerradas 25/07/2026 · chrome compartido 26/07/2026)

| Tema | Decisión |
|------|----------|
| Look | Barra **slate-800** alineada al hub Pedidos (`pedidos_hub.html`): título blanco, búsqueda oscura, toggles púrpura/sky, CTAs `slate-700` / primario púrpura |
| Migas | **Eliminadas** en Tablero, **Parte** y **Control de calidad** |
| KPI cabecera | Solo **resta urgente** (+ chip Solo urgentes en Par). Sin «resta total» — solo Tablero |
| Atajos visibles | Orden canónico: Tablero prod (emerald) → Parte (púrpura) → CC (teal) → Tablero KPI (ámbar) → `help_outline` (slate). Include: `chrome_nav_flujo.html` |
| Menú `⋯ Más` | Armado, Anular envíos (si permiso) — **solo Tablero**; KPI ya no está en el menú (ícono ámbar) |
| Ayuda | Ícono `help_outline` → ancla del manual de cada pantalla |
| CTA cargar filtros | **Cargar grilla** / **Actualizar** = secundario `slate-700` |
| CTA primario acción | Tablero **Enviar** púrpura; Parte **Guardar** púrpura; CC **Guardar** teal |
| Estado | Pack\|Par, Docenas\|Pares, búsqueda: en la misma barra (**Pack\|Par solo Tablero**) |
| Toggles | **Pack\|Par** activo púrpura; **Docenas\|Pares** activo sky (`variant=dark`) |
| Marcas (Parte/CC) | **Ocultas** en chrome (`hidden`, DOM conservado): el tags-filter `min-h-9` rompía la alineación |
| Alineación atajos | En Parte/CC el `header` usa **`items-end`** (formulario con labels encima de inputs) para que los íconos compartan línea base con los campos y «Cargar grilla»; el `h1` lleva `self-center`. Tablero (sin labels visibles) sigue con `items-center`. |
| Altura controles | **`h-9`** (36px) canónica = búsqueda «Código o descripción…» / Tablero. Inputs, selects, atajos `h-9 w-9`, CTAs y toggles Pack\|Par / Docenas\|Pares comparten esa altura (`text-sm` en campos). |

## 3.1 Alcance chrome compartido (flujo planta)

Misma barra densa en:

1. `tablero_produccion.html`
2. `parte_produccion.html`
3. `clasificacion_encabezado.html` (+ sin migas en `clasificacion_produccion.html`)

Navegación: `mpr/includes/chrome_nav_flujo.html` (omite la pantalla actual).

| Destino | Color | Ícono |
|---------|-------|-------|
| Tablero de producción | emerald | `table_chart` |
| Parte | púrpura | `assignment` |
| Control de calidad | teal | `verified` |
| Tablero KPI (`/mpr/`) | ámbar | `analytics` |

Sin Pack\|Par ni KPI urgente fuera del Tablero. Fecha / línea / máquina / turno siguen visibles y operativos en Parte y CC.

## 4. Arquitectura de información (una barra)

```
[ Tablero de producción ] [ Buscar artículo… ]  [Pack|Par] [Docenas|Pares] [Urgente · Solo urgentes]
                                                    [Actualizar] [Parte][CC][⋯][?] [Enviar]
```

- Título `h1` blanco `text-lg/xl font-bold` (mismo peso que «Pedidos»).
- Contenedor: `rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 shadow-md`.
- Filtros **Desde / Hasta / Marcas / Filtrar** permanecen en el DOM con clase `hidden`.
- KPI urgente en **una sola línea** sobre fondo rose tenue en la barra oscura.
- Orden de filas (Par): máquina asignada → número de máquina 1…N → marca → descripción.
- Modal Fabricando: artículo como título; tabla por fila
  (`Fila | Mañana/Tarde/Noche + operarios` + una fila de datos por máquina).
- Ícono máquina en columna Fabricando: tooltip al hover («Máquina N»); clic abre el modal.
- Modales (envío / Fabricando) en el mismo `x-data` de página.
- **Thead tabla (Par):** columna Artículo en una sola celda `rowspan="2"` (sin etiqueta duplicada). Fondos del `thead` (Pack y Par) **opacos** (sin alpha) para que el sticky no deje ver las filas al scrollear.

## 5. Iconos y tooltips (atajos)

Los atajos de solo ícono usan tooltip Synap inmediato al hover/foco (`mpr/includes/chrome_icon_tooltip.html`: burbuja `slate-900`, sin `title` nativo duplicado). Fuente de atajos de flujo: `chrome_nav_flujo.html`.

| Acción | Material icon | Tooltip / aria-label |
|--------|---------------|----------------------|
| Tablero de producción | `table_chart` | Tablero de producción (emerald) |
| Parte de producción | `assignment` | Parte de producción (púrpura) |
| Control de calidad | `verified` | Control de calidad (teal) |
| Tablero KPI | `analytics` | Tablero KPI (ámbar) |
| Actualizar vista | `refresh` | Actualizar vista (botón con label; `title` con última hora) |
| Más acciones | `more_horiz` | Más acciones |
| Ayuda | `help_outline` | Manual del tablero / parte / CC |

Botón icono: **`h-9 w-9`**, borde slate suave, foco visible. Sin `alert`/`confirm` nativos.

## 6. Deprecación OPT / ventana_pack (UI)

### 6.1 Deprecado como flujo diario / referencia visual del tablero

No enlazar desde el chrome del tablero ni usar como patrón de densidad/look para Tablero / Parte / CC:

- `/mpr/demanda/ventana-pack/` y agrupar / crear OPT
- `/mpr/opt/` (listado, detalle, alta) como camino principal de planta
- Pedidos fábrica / opts-por-pedido como entrada operativa
- Wizard OPT legacy

Las URLs pueden existir en código por compatibilidad; **no** son el hub ni el look de referencia. Alineado con [NAVIGACION_MPR_ETAPA11.md](NAVIGACION_MPR_ETAPA11.md) (ya fuera del menú).

### 6.2 Excepciones (mantener hasta validar retiro)

| Área | Motivo |
|------|--------|
| **Armado** `/mpr/armado/` | Proceso no cubierto por Tablero/Parte/CC; atajo en `⋯ Más` |
| Config (máquinas, roster, turnos, depósitos, BOM) | Setup, no demanda→OPT |
| Reportes / Tablero KPIs | Analítica |
| Trazabilidad OPT / PDF | Solo si auditoría u operación histórica lo exige |

### 6.3 Regla para agentes y diseño

> Al diseñar o refinar Tablero, Parte o Control de calidad: **MUST NOT** tomar como fuente de verdad visual `ventana_pack.html`, `opt_list.html` u otras pantallas OPT deprecadas. Preferir patrones densos del propio tablero y MPR operativo vivo.

## 7. Criterios de aceptación UX

1. En laptop típica, el chrome (filas 1–2) ocupa **claramente menos** altura que el hero oscuro previo (objetivo ~80–120 px menos).
2. Primera fila de datos de la tabla visible sin scroll en viewport 900–1080 px de alto (con navbar Synap).
3. Atajos Parte/CC/Actualizar usables solo con ícono + tooltip; menú Más con labels.
4. Ningún enlace del chrome apunta a ventana_pack / opt_list como flujo primario.
5. Pack\|Par, filtros, envío y búsqueda siguen funcionando igual (solo reubicación).

## 8. Implementación

- Plantilla: `mpr/templates/mpr/tablero_produccion.html` (bloque `flex-shrink-0` + fusión con barra Pack/Par).
- Alpine: `masMenuOpen` (+ cierre Escape / click outside opcional).
- Include CC: variant `icon` en `mpr/includes/btn_control_calidad.html` si se reutiliza.
- Docs índice: entrada en [README.md](README.md).
