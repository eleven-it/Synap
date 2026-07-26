# Navegación MPR — Etapa 11 (hub tablero consolidado)

**Fecha:** 04/07/2026  
**Estado:** Implementado

## Objetivo

Priorizar el **tablero de producción consolidado** como entrada y flujo operativo diario. Las pantallas OPT legacy (`lista_produccion_*`) fueron retiradas del menú tras el DROP de tablas y la migración a ledgers `mpr_*`.

## Flujo canónico (operación diaria)

| Operación | Pantalla | URL |
|-----------|----------|-----|
| Demanda / stock por componente | Tablero de producción | `/mpr/tablero-produccion/` |
| Enviar a fabricar | Columna Enviar (tablero) | POST `/mpr/tablero-produccion/enviar/` |
| Registrar producido | Parte de producción | `/mpr/parte-produccion/` |
| Clasificar salida (control de calidad) | Control de calidad | `/mpr/clasificacion-produccion/` |
| Armado | Armado | `/mpr/armado/` |
| KPIs / urgencias | Tablero de control | `/mpr/tablero/` |
| Reportes analítica | Reportes MPR (hub visual) | `/mpr/reportes/` |

Ver catálogo: [REPORTES_MPR.md](./REPORTES_MPR.md).

## Rutas legacy (sin menú)

Las URLs `/mpr/opt/`, `/mpr/wizard/` y `/mpr/demanda/ventana-pack/` pueden seguir existiendo en código pero **no** aparecen en el menú. Requieren tablas `lista_produccion_*` eliminadas en bases migradas.

**Canon UX (25/07/2026 · chrome compartido 26/07/2026):** el flujo diario de planta es **Tablero → Parte → Control de calidad**, con la misma barra densa `slate-800` (sin migas; atajos coloreados: prod emerald · parte púrpura · CC teal · KPI ámbar). Detalle: [TABLERO_PRODUCCION_CHROME_DENSIDAD.md](TABLERO_PRODUCCION_CHROME_DENSIDAD.md). La UI OPT/ventana_pack está **deprecada** como referencia visual y como atajo del tablero, salvo procesos MPR no cubiertos por esas tres pantallas (p. ej. armado).

## Cambios de menú (`core/utils/utils.py` → `APPS_MENU`)

- **URL del módulo:** `mpr:tablero_produccion` (antes `mpr:tablero`).
- **Sección «Producción diaria»:** tablero, asignar artículo a máquina (grilla), parte, clasificación, planificación, KPIs.
- **Sección «Armado y stock»:** armado, imputación, reclasificación.
- **Sección «Reportes»:** hub Reportes MPR.
- **Sección «Configuración»:** turnos de producción, depósitos, operarios.
- **Retirado:** sección «Trazabilidad OPT (avanzado)» (listado OPT, ventana pack, asistente legacy).

## Enlaces actualizados

- `crear_opp_url` en vistas legacy OPT → `mpr:parte_produccion` (detalle OPT legacy).
- Tablero KPI: CTA **Tablero de producción**, parte, clasificación; sin OPT en encabezado.
- Ventana pack: banner ámbar fuera del wizard; pasos del asistente corregidos a **4** (`WIZARD_PASO_MAX`).

## Tablero KPI (`/mpr/`)

**Actualizado 04/07/2026:** KPIs y paneles alimentados por el **flujo diario** (demanda PED en vivo + tablero consolidado por componente). Sin OPT atrasadas ni panel «OPTs en proceso».

| KPI / panel | Fuente |
|-------------|--------|
| Pedidos pendientes | `contar_pedidos_fabrica` |
| Componentes pendientes | `listar_tablero_por_articulo(solo_pendiente=True)` |
| Pares resta urgente | Suma `resta_urgente` por componente (mismo dato que tablero de producción) |
| Packs con brecha | `listar_demanda_pack_desde_pedidos` |
| Panel izquierdo | Top componentes con **resta urgente** (sin botones; fila enlaza al tablero consolidado) |
| Top pack pendientes | Demanda pack desde pedidos: stock terminado, resta urgente, a fabricar |

Enlaces rápidos: tablero consolidado, parte, clasificación, armado, planificación. **Sin** Trazabilidad OPT ni ventana pack en el encabezado.

## Barra rápida MPR (`base_mpr.html`)

Tablero consolidado · Parte · Control de calidad (teal) · Planificación · KPIs · Armado · Reportes.

## Filtro de marcas (operación diaria)

**Actualizado 07/07/2026:** tablero de producción, parte y control de calidad incluyen selector **Marcas** (tags + búsqueda predictiva local, patrón `tags_filter.mjs` / inventario MPR). Query param repetido `marcas_incluidos` (CodMarca). Filtra filas por `articulo.CodigoMarca` en `listar_tablero_por_articulo`, `construir_grilla_parte` y `construir_grilla_clasificacion_produccion`. Include: `mpr/includes/filtro_marcas_tags.html` → `templates/includes/filtro_marcas_tags.html` (variant `dark`). Toggle canónico **Docenas | Pares**: `templates/includes/toggle_docenas_pares.html`.

## Tests

`mpr/tests/test_etapa11_navegacion.py` — menú, plantillas y URLs canónicas.
