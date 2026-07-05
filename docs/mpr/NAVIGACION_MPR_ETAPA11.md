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
| Clasificar salida | Clasificación de producción | `/mpr/clasificacion-produccion/` |
| Armado | Armado | `/mpr/armado/` |
| KPIs / urgencias | Tablero de control | `/mpr/tablero/` |
| Reportes analítica | Reportes MPR (hub visual) | `/mpr/reportes/` |

Ver catálogo: [REPORTES_MPR.md](./REPORTES_MPR.md).

## Rutas legacy (sin menú)

Las URLs `/mpr/opt/`, `/mpr/wizard/` y `/mpr/demanda/ventana-pack/` pueden seguir existiendo en código pero **no** aparecen en el menú. Requieren tablas `lista_produccion_*` eliminadas en bases migradas.

## Cambios de menú (`core/utils/utils.py` → `APPS_MENU`)

- **URL del módulo:** `mpr:tablero_produccion` (antes `mpr:tablero`).
- **Sección «Producción diaria»:** tablero, parte, clasificación, planificación, KPIs.
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
| Unidades pendientes | Suma `pendiente` por componente |
| Packs con brecha | `listar_demanda_pack_desde_pedidos` |
| Panel izquierdo | Top componentes con pendiente |
| Top pendientes | Misma fuente, enlace al tablero consolidado |

Enlaces rápidos: tablero consolidado, parte, clasificación, armado, planificación. **Sin** Trazabilidad OPT ni ventana pack en el encabezado.

## Barra rápida MPR (`base_mpr.html`)

Tablero consolidado · Parte · Clasificación · Planificación · KPIs · Armado · Reportes.

## Tests

`mpr/tests/test_etapa11_navegacion.py` — menú, plantillas y URLs canónicas.
