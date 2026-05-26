# Punto 10 — Informe PDF Presupuesto y plantillas (`plantillas`)

Documento del cambio **presupuesto-ventas-synap**. Cierra el diseño respecto a **`permisos_sistema.plantillas`**, `reporte_plantilla` en VB6 y el módulo **`reports`** Synap.

---

## Contexto legacy

- **`plantillas`** en `permisos_sistema`: habilita uso de plantillas / rutas de informe alternativas.
- VB6: Crystal `comp_presupuesto.rpt` o **`reporte_plantilla`** según configuración.

En Synap **no** hay Crystal: el PDF es **`ReportDefinition`** + ejecución/export existente (`reports`).

---

## Decisión de arquitectura (cerrada)

| Tema | Decisión |
|------|----------|
| **Documento operativo** | Categoría **`operational`** en `ReportCategory` (no gerencial). |
| **Una definición lógica por “Presupuesto de ventas PDF”** | Un **`ReportDefinition`** con **`slug`** estable (nombre final al implementar, p. ej. `documento-presupuesto-ventas`). Evita proliferar slugs por cada variante cosmética. |
| **Varias plantillas / layouts** | Resolver con **`config` JSON** de la definición (plantillas admitidas, rutas de plantilla HTML/PDF, queries si difieren) + **payload de ejecución** que incluya `codigo_movimiento` y, si aplica, **`id_plantilla`** alineado a `comp_ped.id_plantilla` / tablas legacy de plantillas. El runner o servicio de export **rama** según `plantillas` del puesto y el payload. |
| **Varias filas `ReportDefinition`** | **Solo** si dos plantillas tienen **datasets o pipelines totalmente distintos** no parametrizables con `config`; cada fila suma mantenimiento — evitar salvo necesidad demostrada. |
| **v1 contenido** | Primera entrega: **una** salida PDF que cubra los mismos datos esenciales que el Crystal de referencia; personalización visual iterativa después (ya acordado en tabla de producto). |
| **Momento de generación** | Según **configuración** (empresa / preferencia): tras guardado, solo bajo demanda o ambos — la vista PRE y permisos disparan llamada al mismo contrato `export`/ejecución con `codigo_movimiento`. |

---

## Contrato API / Agent IA

- Invocación tipada: **`report_slug`** + **`codigo_movimiento`** (+ opcional **`id_plantilla`** / **`variant`** si negocio lo exige).
- Respuestas y errores alineados al **`ExportService`** / patrones existentes en `reports` (mensajes en español).

---

## Checklist implementación

- [x] Crear `ReportDefinition` operational + registrar en catálogo (`documento-presupuesto-ventas`, migración `0032`).
- [x] Implementar dataset desde `comp_ped` + `stockp` + cliente (runner `presupuesto_ventas_runner`; Excel v1).
- [ ] Respetar **`plantillas`** del puesto: si `No`, una sola variante o mensaje acorde al SPEC funcional (v1: una variante Excel para todos).
- [x] Documentar slug y payload en `docs/reports/DOCUMENTO_PRESUPUESTO_VENTAS_REPORT.md` y SPEC §9.5.

---

**Diseño global del cambio:** punto **13** (entitlement y desactivación remota) cerrado en **`DESIGN_PUNTO13_ENTITLEMENT_Y_DESACTIVACION_REMOTA.md`** y `design.md`.
