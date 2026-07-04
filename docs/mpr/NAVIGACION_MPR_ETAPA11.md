# Navegación MPR — Etapa 11 (hub tablero consolidado)

**Fecha:** 04/07/2026  
**Estado:** Implementado

## Objetivo

Priorizar el **tablero de producción consolidado** como entrada y flujo operativo diario; relegar **ventana pack** y **asistente wizard** a trazabilidad OPT avanzada / legacy.

## Flujo canónico (operación diaria)

| Operación | Pantalla | URL |
|-----------|----------|-----|
| Demanda / stock por componente | Tablero de producción | `/mpr/tablero-produccion/` |
| Enviar a fabricar | Columna Enviar (tablero) | POST `/mpr/tablero-produccion/enviar/` |
| Registrar producido | Parte de producción | `/mpr/parte-produccion/` |
| Clasificar salida | Clasificación de producción | `/mpr/clasificacion-produccion/` |
| Armado | Armado | `/mpr/armado/` |
| KPIs / urgencias | Tablero de control | `/mpr/tablero/` |

## Flujo legacy (trazabilidad OPT)

| Operación | Pantalla | URL |
|-----------|----------|-----|
| Crear OPT desde demanda pack | Ventana pack | `/mpr/demanda/ventana-pack/` |
| Listado / detalle OPT | OPT list / detail | `/mpr/opt/` |
| Asistente pack-centrico | Wizard | `/mpr/wizard/` |

Tras crear y liberar OPT desde el asistente legacy, la redirección va al **detalle OPT** con mensaje para usar **Parte de producción** (ya no al paso 3 del wizard).

## Cambios de menú (`core/utils/utils.py` → `APPS_MENU`)

- **URL del módulo:** `mpr:tablero_produccion` (antes `mpr:tablero`).
- **Sección «Producción diaria»:** tablero, parte, clasificación, planificación, KPIs.
- **Sección «Trazabilidad OPT (avanzado)»:** listado OPT, ventana pack, asistente legacy.
- **Sección «Armado y stock»:** armado, imputación, reclasificación.

## Enlaces actualizados

- `crear_opp_url` en vistas/servicios → `mpr:parte_produccion` (listado OPT, tablero KPIs, detalle OPT).
- Tablero consolidado: botón **Trazabilidad OPT** → `opt_list` (antes ventana pack).
- Tablero KPIs: CTA principal **Tablero de producción**; ventana pack como enlace secundario.
- Ventana pack: banner ámbar fuera del wizard; pasos del asistente corregidos a **4** (`WIZARD_PASO_MAX`).

## Barra rápida MPR (`base_mpr.html`)

Tablero consolidado · Parte · Clasificación · Trazabilidad OPT · Planificación · KPIs.

## Tests

`mpr/tests/test_etapa11_navegacion.py` — menú, plantillas y URLs canónicas.
