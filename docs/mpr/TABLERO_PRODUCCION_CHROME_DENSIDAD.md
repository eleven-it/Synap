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

## 3. Decisiones de producto (cerradas 25/07/2026)

| Tema | Decisión |
|------|----------|
| Look | Toolbar **clara** (blanco/slate); sin caja hero `slate-800` full-bleed |
| Migas | **Eliminadas** en esta pantalla |
| KPI cabecera | Solo **resta urgente** (+ chip Solo urgentes en Par). Sin «resta total» |
| Atajos visibles | Actualizar, Parte, CC — **icono + tooltip** (`title` + `aria-label`) |
| Menú `⋯ Más` | Tablero KPIs, Armado, Anular envíos (si permiso) — con **texto** |
| Ayuda | Ícono `help_outline` → manual `#tablero-produccion` |
| CTA primario | **Enviar a producción** conserva label (no solo ícono) |
| Estado | Pack\|Par, Docenas\|Pares, búsqueda: conservan texto |

## 4. Arquitectura de información (dos filas)

```
Fila 1 — contexto y atajos
[Pack|Par]  [Urgente N · Solo urgentes]  [↻][Parte][CC][⋯][?]

Fila 2 — acción sobre la grilla
[ Buscar artículo… ]                         [Docenas|Pares]  [Enviar a producción]
```

- Sin H1 visible grande (título de pestaña / menú Synap bastan).
- Filtros **Desde / Hasta / Marcas / Filtrar** permanecen en el DOM con clase `hidden` (no eliminados) por si se reactivan.
- KPI urgente en **una sola línea** (etiqueta + valor en negrita).
- Orden de filas (Par): primero con máquina asignada (`tiene_maquina`), luego el resto; dentro de cada grupo por **marca** y descripción. Helper: `ordenar_filas_tablero_maquina_marca`.
- «Última actualización» en tooltip del botón Actualizar.
- Modales (confirmación envío, detalle Fabricando) permanecen en el mismo `x-data` de página, fuera del layout de filas.

## 5. Iconos y tooltips (atajos)

| Acción | Material icon | Tooltip / aria-label |
|--------|---------------|----------------------|
| Actualizar vista | `refresh` | Actualizar vista |
| Parte de producción | `assignment` | Parte de producción |
| Control de calidad | `verified` (canon MPR) o `fact_check` | Control de calidad |
| Más acciones | `more_horiz` | Más acciones |
| Ayuda | `help_outline` | Manual del tablero |

Botón icono: ~`h-8 w-8`, borde slate suave, foco visible. Sin `alert`/`confirm` nativos.

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
