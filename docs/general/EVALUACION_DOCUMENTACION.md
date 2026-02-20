# Evaluación de la documentación – estado actual del proyecto

Documento de auditoría: **qué está obsoleto, qué ya no debe tenerse en cuenta y qué está duplicado** según el estado actual (instalación mínima: core, login, dashboard, reports, self_checkout; módulos sales, inventory, tiendanube, mercadopago, etc. no instalados).

---

## 1. Información obsoleta (debe actualizarse)

| Documento | Ubicación | Qué está obsoleto | Acción recomendada |
|-----------|-----------|-------------------|--------------------|
| **LIMPIEZA_MODULOS.md** | docs/general/ | Indica que **reports_ai** está "Mantenidos"; en `settings.py` está comentado y no se instala. Lista de comandos deshabilitados puede haber cambiado. | Actualizar: quitar reports_ai de "Mantenidos"; listar solo módulos realmente instalados (core, login, dashboard, reports, self_checkout). Revisar comandos deshabilitados. |
| **ADMINISTRANET_ANALYTICS.md** | docs/general/ | Dice "Módulos habilitados: Core, Dashboard, Reports, **Reports AI**"; Reports AI no está en INSTALLED_APPS. | Sustituir "Reports AI" por "SIA, Self Checkout"; alinear con settings.py actual. |
| **REPORTE_INSTALACION_MINIMA_REPORTES.md** | docs/reports/ | Menciona reports_ai como opcional y rutas/APPs que pueden haber cambiado. | Revisar contra settings/urls actuales; marcar reports_ai como "no instalado en instalación mínima actual". |
| **FIREBASE_DESHABILITADO.md** | docs/general/ | Lista archivos modificados (firebase_config, core/views, etc.). Si hubo refactors posteriores, rutas o nombres pueden haber cambiado. | Comprobar que los paths y nombres sigan existiendo; si algo se movió, actualizar. |
| **DOCKER_OPTIMIZATIONS.md** | docs/general/ | Referencias a Docker/build pueden estar desactualizadas. | Revisar contra docker-compose y Dockerfile actuales; actualizar si hay diferencias. |
| **CONTEXTO_TABLAS_VB6_INFORMES.md** | docs/general/ | Enlaces a otros docs (VALIDACION_*, BO_REPORT_PERFORMANCE) ya actualizados a docs/reports/; puede haber más referencias a rutas viejas. | Revisar enlaces internos; asegurar que todos apunten a docs/*. |
| **ANALISIS_VENTAS_NETAS.md** / **RESUMEN_ANALISIS_VENTAS_NETAS.md** / **TEST_VENTAS_NETAS_RESULTS.md** | docs/reports/ | Fechas 2026-01-23; estado del reporte (slug ventas_netas vs ventas-netas, configuración JSON). | Verificar slug y config actual en BD; si cambió, actualizar fechas y descripción. |

---

## 2. Información que ya no debe tenerse en cuenta (marcar como deprecada o de referencia)

| Documento | Ubicación | Motivo | Acción recomendada |
|-----------|-----------|--------|--------------------|
| **REFACTOR_SUMMARY.md** | docs/general/ | Trata **tiendanube_administranet** (refactor de templates). Ese módulo **no está en INSTALLED_APPS**. | Añadir al inicio: "**Referencia histórica.** Módulo tiendanube_administranet no instalado en la instalación mínima actual." No borrar; útil si se reinstala el módulo. |
| **ANALISIS_MODULE_MANAGEMENT.md** | docs/general/ | Analiza **tiendanube_administranet** y su integración con Module Management. Módulo no instalado. | Añadir aviso: "**Referencia.** Módulo tiendanube_administranet no instalado. Aplicable si se vuelve a habilitar." |
| **ANALISIS_MERCADOPAGO_SALES.md** | docs/self_checkout/ | Describe estado de **mercadopago** y **sales** (no instalados). Ya indica que no existen en el proyecto. | Mantener como referencia; añadir al inicio: "**Solo referencia.** Apps mercadopago y sales no instaladas. Relevante si se reinstalan." |
| **PROPUESTA_SALES_DEPRECADO_MERCADOPAGO_SELF_CHECKOUT.md** | docs/self_checkout/ | Propuesta de diseño sin Sales y con MercadoPago en Self Checkout. Módulos no instalados. | Añadir: "**Referencia de diseño.** Sales/mercadopago no instalados; este doc describe la arquitectura prevista si se integran." |
| **FODA_MERCADOPAGO_INTEGRACION_VS_MCP.md**, **INFORME_MENU_MERCADOPAGO.md**, **MERCADOPAGO_CONFIG_UX.md** | docs/self_checkout/ | Giran en torno a MercadoPago; app no instalada. | Añadir en cada uno: "**Solo referencia.** Módulo mercadopago no instalado." |
| **PROPUESTA_FACTURA_ELECTRONICA_PYAFIPWS.md** | docs/self_checkout/ | pyafipws está en .gitignore / no usado en instalación mínima. | Añadir: "**Referencia.** pyafipws no en uso en instalación mínima; aplicable si se habilita FE con esta lib." |

---

## 3. Información duplicada (consolidar o eliminar)

### 3.1 Archivos duplicados literales (eliminar copia " 2" / " 3")

| Tipo | Ubicación | Acción |
|------|-----------|--------|
| **Tablas** | docs/general/tablas/ | Hay **centenares** de archivos `* 2.md` y `* 3.md` (duplicados de cada tabla). Conservar solo el `.md` sin sufijo numérico; **eliminar** todos los `* 2.md` y `* 3.md`. |
| **Self-checkout** | docs/self_checkout/ | Eliminar **DISEÑO_TPV_EXTENDER_SELF_CHECKOUT 2.md** y **SELF_CHECKOUT_UI 2.md**; conservar DISEÑO_TPV_EXTENDER_SELF_CHECKOUT.md y SELF_CHECKOUT_UI.md. |

### 3.2 Contenido duplicado o solapado (consolidar)

| Documentos | Ubicación | Relación | Acción recomendada |
|------------|-----------|----------|--------------------|
| **ANALISIS_VENTAS_NETAS.md** y **RESUMEN_ANALISIS_VENTAS_NETAS.md** | docs/reports/ | Uno es análisis exhaustivo y el otro resumen ejecutivo del mismo reporte. | Opción A: mantener ambos con títulos claros ("Análisis exhaustivo" / "Resumen ejecutivo") y enlaces cruzados al inicio. Opción B: unificar en un solo doc con secciones "Resumen ejecutivo" y "Análisis detallado". |
| **CAE_CAEA_ARCA_SELF_CHECKOUT.md** y **CAE_CAEA_ARCA_SELF_CHECKOUT.txt** | docs/self_checkout/ | Mismo tema; .txt suele ser copia o export. | Revisar si el .txt aporta algo que no esté en .md; si no, eliminar el .txt o dejar solo el .md. |
| **CERTIFICADOS_AFIP_ARCA.md** y **CERTIFICADOS_AFIP_ARCA.txt** | docs/self_checkout/ | Idem. | Igual que arriba: conservar .md; eliminar .txt si es redundante. |
| **STOCK_VB6_PROCEDIMIENTOS_GUARDADO.md** y **STOCKP_VB6_PROCEDIMIENTOS_GUARDADO.md** | docs/self_checkout/ | Tratan tablas distintas: **stock** vs **stockp**. No son duplicados. | No consolidar; son complementarios. Opcional: en el índice o en cada uno, enlazar al otro ("Ver también STOCKP_..." / "Ver también STOCK_..."). |

### 3.3 Referencias cruzadas a documentación antigua

- Varios docs citan rutas como `reports/docs/...` o archivos ya movidos. Tras la reubicación a `docs/`, **ya se actualizaron** muchas referencias (p. ej. CONTEXTO_TABLAS_VB6_INFORMES, PLAN_PRINCIPAL_FODA).
- Revisión hecha: en `docs/` se actualizaron **STOCK_VB6_PROCEDIMIENTOS_GUARDADO.md** (texto "reports/docs y docs" → "docs (docs/reports, …)") y **README_DOCUMENTACION_TABLAS.md** (`--output-dir reports/docs` → `--output-dir docs/general`). Los archivos duplicados `* 2.md` en `reports/docs/` y `self_checkout/` siguen con rutas antiguas si se conservan.

---

## 4. Resumen de acciones prioritarias

1. **Eliminar duplicados literales:** Borrar todos los `* 2.md` y `* 3.md` en `docs/general/tablas/` y en `docs/self_checkout/` (DISEÑO_TPV_EXTENDER_SELF_CHECKOUT 2.md, SELF_CHECKOUT_UI 2.md).
2. **Actualizar obsoletos:** LIMPIEZA_MODULOS, ADMINISTRANET_ANALYTICS, REPORTE_INSTALACION_MINIMA_REPORTES (y si aplica FIREBASE_DESHABILITADO, DOCKER_OPTIMIZATIONS) para que reflejen el estado actual de INSTALLED_APPS y rutas.
3. **Marcar como referencia/deprecada:** REFACTOR_SUMMARY, ANALISIS_MODULE_MANAGEMENT, docs de MercadoPago/Sales/pyafipws/tiendanube con una nota al inicio.
4. **Consolidar o enlazar:** Ventas netas (ANALISIS vs RESUMEN) según se prefiera un solo doc o dos con enlaces; CAE_CAEA y CERTIFICADOS: conservar .md y eliminar .txt si son redundantes.
5. **Revisar enlaces:** Búsqueda de `reports/docs/` y rutas antiguas en todos los .md y actualizar a `docs/...`.

---

## 5. Estado del proyecto de referencia (para la evaluación)

- **INSTALLED_APPS (activos):** core, login, dashboard, reports, self_checkout (+ terceros).
- **No instalados (comentados en settings):** reports_ai, administraNET_integration, sales, inventory, tiendanube, tiendanube_administranet, accounting, purchases, mercadopago, clover, logistics, finance, support_ai, celery, django_celery_beat.
- **Autenticación:** MySQL administraNET (Firebase deshabilitado).
- **Documentación:** Centralizada en `docs/` (general, reports, self_checkout, login).

Este documento debe actualizarse cuando cambie el conjunto de módulos instalados o la estructura de `docs/`.
