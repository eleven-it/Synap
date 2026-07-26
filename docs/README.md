# Documentación Synap

Toda la documentación del proyecto está en **`docs/`** en la raíz del repositorio, clasificada por ámbito. Sirve de **contexto para distintas sesiones y equipos multidisciplinarios**.

## Regla: todo desarrollo debe actualizar la documentación

**Cada cambio de desarrollo (features, refactors, correcciones, nuevos módulos) debe incluir la actualización de la documentación** en `docs/`. Detalle en [general/POLITICA_DOCUMENTACION.md](general/POLITICA_DOCUMENTACION.md).

## Estructura

| Directorio | Contenido |
| ---------- | --------- |
| **general/** | Plan del proyecto, flujo de ramas, **implementación servidor Staging** ([GUIA_IMPLEMENTACION_SERVIDOR_STAGING.md](general/GUIA_IMPLEMENTACION_SERVIDOR_STAGING.md)), política de documentación, **tipos de datos y normalización con AdministraNET** ([TIPOS_DATOS_ADMINISTRANET.md](general/TIPOS_DATOS_ADMINISTRANET.md)), **una empresa por base** ([EMPRESA_UNA_POR_BASE_ADMINISTRANET.md](general/EMPRESA_UNA_POR_BASE_ADMINISTRANET.md)), documentación de tablas/BD (`general/tablas/`), Principal (shell VB6), **mapeo menú Archivo VB6** ([ADMINISTRANET_VB6_MENU_ARCHIVO.md](general/ADMINISTRANET_VB6_MENU_ARCHIVO.md)), **análisis para migración** ([MIGRACION_ADMINISTRANET_VB6_ANALISIS.md](general/MIGRACION_ADMINISTRANET_VB6_ANALISIS.md)), **avances de migración Archivo** ([AVANCES_MIGRACION_ARCHIVO.md](general/AVANCES_MIGRACION_ARCHIVO.md)) y **alineación Synap vs AdministraNET + GAPs** ([SYNAP_ALINEACION_ADMINISTRANET_Y_GAPS.md](general/SYNAP_ALINEACION_ADMINISTRANET_Y_GAPS.md)), MySQL local, depósitos, Firebase/refactor/instalación mínima, Docker, limpieza de módulos. **Inventario de cambios de seguridad (CSRF, JWT RAG, rate limit, XSS, media):** [SEGURIDAD_CAMBIOS_SYNAP.md](general/SEGURIDAD_CAMBIOS_SYNAP.md); contrato RAG Support: [SEGURIDAD_API_SUPPORT_RAG.md](general/SEGURIDAD_API_SUPPORT_RAG.md). |
| **administranet_vb6/** | Documentación **exclusiva de AdministraNET (VB6)**. Los `.md` aquí se etiquetan como sistema **administranet** cuando Synap sirve conocimiento al RAG del módulo Support; el resto de `docs/` se etiqueta como **synap**. Colocar aquí procedimientos VB6, tablas, menú Archivo, etc. Actualización: cada "Cargar desde Synap" en Support lee `docs/` al vuelo (sin caché). Ver [administranet_vb6/README.md](administranet_vb6/README.md) y [support/docs/RAG_Y_SYNAP.md](../support/docs/RAG_Y_SYNAP.md). |
| **reports/** | Módulo Reportes: análisis ventas netas, validaciones (BO, pedidos, ventas), total consolidado, KPI, builder técnico, rendimiento BO, reconocimiento de relaciones, comando inspect_articulos, widgets. |
| **self_checkout/** | Self-checkout, TPV, caja, AFIP/CAE/CAEA, certificados, auditorías TPV, procedimientos stock VB6, scripts SQL (`self_checkout/sql/`). |
| **support/** | Módulo Support: RAG con LangChain/PGVector, implementación del refactor ([RAG_LANGCHAIN_IMPLEMENTACION.md](support/RAG_LANGCHAIN_IMPLEMENTACION.md)), uso y configuración (ver también [support/docs/RAG_Y_SYNAP.md](../support/docs/RAG_Y_SYNAP.md)). |
| **login/** | Reservado para documentación de login, sesión y autenticación. |
| **compras/** | **Factura de compra:** auditoría VB6 (`Guardar` PFactura), origen Manual/Remito/OC/Vale, especificación PWA captura + workflow, posting legacy MySQL, contrato `LegacyPostingCommand`, SQL y tests. Índice: [compras/README.md](compras/README.md). |
| **mpr/** | Producción (MPR): manual ([mpr/MANUAL_USUARIO_MPR.md](mpr/MANUAL_USUARIO_MPR.md)), CE talle/color ([mpr/ARTICULO_CE_TALLES_COLOR.md](mpr/ARTICULO_CE_TALLES_COLOR.md)), índice [mpr/README.md](mpr/README.md). |
| **ecom/** | E-commerce y Ventas (pedidos mayorista, portal): manual ([ecom/MANUAL_USUARIO_VENTAS.md](ecom/MANUAL_USUARIO_VENTAS.md), HTML en **`/ecom/manual/`**), índice [ecom/README.md](ecom/README.md). |
| **stock/** | Stock e inventario por etapa: manual ([stock/MANUAL_USUARIO_STOCK.md](stock/MANUAL_USUARIO_STOCK.md)), inventario MPR ([stock/INVENTARIO_TABLA_MPR.md](stock/INVENTARIO_TABLA_MPR.md)), índice [stock/README.md](stock/README.md). |
| **contabilidad/** | Auditoría contable: manual ([contabilidad/MANUAL_USUARIO_CONTABILIDAD.md](contabilidad/MANUAL_USUARIO_CONTABILIDAD.md), HTML en **`/contabilidad/manual/`**), índice [contabilidad/README.md](contabilidad/README.md). Técnico: [general/AUDITORIA_IMPUTACION_CONTABILIDAD_SYNAP.md](general/AUDITORIA_IMPUTACION_CONTABILIDAD_SYNAP.md). |

Los README de proyecto (`README_REPORTS.md`, `README_INSTALLATION.md`) permanecen en la raíz del repo como punto de entrada.

**Auditoría de documentación:** [general/EVALUACION_DOCUMENTACION.md](general/EVALUACION_DOCUMENTACION.md) evalúa, según el estado actual del proyecto, qué información está obsoleta (actualizar), qué debe considerarse solo referencia (módulos no instalados) y qué está duplicada (consolidar o eliminar).

## Uso de esta carpeta por ramas

- **Desarrollo:** La carpeta `docs/` se versiona y se sube a la rama **Desarrollo**.
- **Staging y Produccion:** Al promover código de Desarrollo a Staging (o de Staging a Produccion), la carpeta `docs/` **no** debe formar parte del release. Al hacer merge a Staging, ejecutar en esa rama: `git rm -r docs` y commit, de modo que Staging y Produccion no incluyan documentación. Ver [general/FLUJO_RAMAS_Y_PLAN.md](general/FLUJO_RAMAS_Y_PLAN.md).

## OpenSpec (especificaciones)

- Especificaciones vigentes en el repo: carpeta **`openspec/specs/`** (p. ej. normativa de fuente de verdad UI en [openspec/specs/ui-fuente-verdad-reportes-mpr/spec.md](../openspec/specs/ui-fuente-verdad-reportes-mpr/spec.md)).
- Cambios cerrados y auditoría SDD: **`openspec/changes/archive/`**.
- Documento legible asociado (UX/UI canónica Reportes + MPR): [general/FUENTE_VERDAD_UI_REPORTES_MPR.md](general/FUENTE_VERDAD_UI_REPORTES_MPR.md).

## Referencia del plan

El desarrollo debe ajustarse al plan en ** [general/PLAN_PRINCIPAL_FODA_BRECHAS_SYNAP.md](general/PLAN_PRINCIPAL_FODA_BRECHAS_SYNAP.md)**.
