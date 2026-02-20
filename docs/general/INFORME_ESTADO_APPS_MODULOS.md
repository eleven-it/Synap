# Informe: estado de aplicaciones y módulos Synap

**Fecha:** 2025-02-16  
**Alcance:** INSTALLED_APPS, MODULE_CONFIGS (core/module_registry.py), URLs, APPS_MENU (navbar), y existencia de código (directorios/apps).

---

## 1. Resumen ejecutivo

| Categoría | Cantidad | Detalle |
|-----------|----------|---------|
| Apps Django instaladas (propias) | 6 | core, login, dashboard, reports, self_checkout, stock |
| Módulos en registro (MODULE_CONFIGS) | 16 | Ver tabla 2 |
| Módulos con entrada en menú (APPS_MENU) | 14 | archivo, inventory, stock, tiendanube, purchases, settings, self_checkout, module_management, reports, mercadopago, clover, finance, logistics, reports_ai (+ archivo/settings/module_management) |
| Apps con directorio en el repo | 8 | core, login, dashboard, reports, self_checkout, stock, theme, **fe_afip** |
| Incoherencias relevantes | Varias | Registry sin app (solo definición), app sin registry (stock), app con código no instalada (fe_afip) |

---

## 2. Aplicaciones instaladas (INSTALLED_APPS)

**Activas (apps propias):**

| App | ¿En registry? | ¿URLs en urls.py? | ¿En APPS_MENU? |
|-----|----------------|-------------------|----------------|
| core | Sí (core) | Sí (core/, core/api/) | Sí (como "archivo" / settings) |
| login | Sí (login) | Sí (login/) | No (no es ítem de navbar) |
| dashboard | Sí (dashboard) | No explícito (redirige a core/dashboard/) | Implícito vía core |
| reports | Sí (reports) | Sí (reports/, api/reports/) | Sí |
| self_checkout | Sí (self_checkout) | Sí (api/self-checkout/) | Sí |
| stock | **No** | Sí (stock/) | Sí (y en core_modules) |

**Comentadas (no instaladas):**

- reports_ai  
- administraNET_integration  
- sales  
- inventory  
- tiendanube  
- tiendanube_administranet  
- django_celery_beat, celery  
- accounting  
- purchases  
- mercadopago  
- clover  
- logistics  
- finance  
- support_ai  

---

## 3. Módulos en registro (MODULE_CONFIGS)

Todos los que define `core/module_registry.py`:

| Módulo | is_core / is_required | ¿App Django instalada? | ¿Existe directorio app? |
|--------|------------------------|------------------------|--------------------------|
| core | Sí / Sí | Sí | Sí (core/) |
| login | Sí / Sí | Sí | Sí (login/) |
| dashboard | Sí / Sí | Sí | Sí (dashboard/) |
| purchases | No / No | No (comentada) | No |
| inventory | No / No | No (comentada) | No |
| accounting | No / No | No (comentada) | No |
| tiendanube | No / No | No (comentada) | No |
| mercadopago | No / No | No (comentada) | No |
| clover | No / No | No (comentada) | No |
| administraNET_integration | No / No | No (comentada) | No |
| logistics | No / No | No (comentada) | No |
| finance | No / No | No (comentada) | No |
| reports | No / No | Sí | Sí (reports/) |
| tiendanube_administranet | No / No | No (comentada) | No |
| reports_ai | No / No | No (comentada) | No |
| self_checkout | No / No | Sí | Sí (self_checkout/) |

**No está en MODULE_CONFIGS:** `stock`. Stock es app instalada, con URLs y menú, pero no tiene entrada en el registro de módulos.

---

## 4. Menú (APPS_MENU y visibilidad)

- **core_modules** en `apps_visibles_para_usuario`: `{'core', 'login', 'dashboard', 'reports', 'stock'}`. Esos se consideran siempre activos para el menú además de lo que venga de `ModuleConfig` (BD).
- **APPS_MENU** en `core/utils/utils.py` define ítems con `id`: archivo, inventory, stock, tiendanube, purchases, settings, self_checkout, module_management, reports, mercadopago, clover, finance, logistics, reports_ai (y bloques comentados: tiendanube_administranet, crm, ventas, etc.).
- Un ítem se muestra si: está en módulos activos (BD + core_modules), el usuario tiene permiso y (si aplica) hay submenús resolubles. Por tanto, aunque inventory, tiendanube, purchases, etc. estén en APPS_MENU, al no estar instaladas sus apps las URLs no resuelven y pueden quedar ocultos o rotos según la lógica de submenús.

---

## 5. URLs (django_project/urls.py)

**Incluidas de forma explícita (activas):**

- `/` → redirección a `/core/dashboard/`
- `admin/`, `login/`, `core/`, `core/api/`, `media/`
- `reports/`, `stock/`
- `api/reports/`, `api/self-checkout/`

**Comentadas:** mercadopago, tiendanube_administranet, tiendanube, accounting, sales, administraNET_integration, inventory, purchases, finance, support_ai, logistics, reports_ai.

**Dinámicas:** `core.url_registry` construye patrones solo para **módulos activos en BD** (ModuleConfig.is_active). Como la mayoría de módulos no están instalados como apps, en la práctica solo podrían aportar URLs los que tengan app instalada y estén activos en BD (p. ej. core, login, dashboard, reports, self_checkout, stock). Stock y reports están montados por urls.py fijo, no solo por el registry.

---

## 6. App con código pero no instalada: fe_afip

- **Directorio:** `fe_afip/` existe con `apps.py`, `urls.py`, `models.py`, `admin.py`, `views.py`, etc.
- **INSTALLED_APPS:** no figura `fe_afip`.
- **MODULE_CONFIGS:** no hay entrada `fe_afip`.
- **urls.py:** no se incluye `fe_afip`.

Conclusión: **fe_afip** es una app presente en el repo sin integración en el proyecto (no instalada, no en registro, no en URLs). Queda como código “huérfano” o pendiente de decisión (activar o eliminar).

---

## 7. Tabla de coherencia por módulo/app

| Nombre | En INSTALLED_APPS | En MODULE_CONFIGS | En urls.py | En APPS_MENU | Directorio app |
|--------|-------------------|-------------------|------------|--------------|----------------|
| core | Sí | Sí | Sí | Sí (archivo/settings) | Sí |
| login | Sí | Sí | Sí | No | Sí |
| dashboard | Sí | Sí | (redir.) | Implícito | Sí |
| reports | Sí | Sí | Sí | Sí | Sí |
| self_checkout | Sí | Sí | Sí | Sí | Sí |
| stock | Sí | **No** | Sí | Sí | Sí |
| theme | Sí | No (UI) | No | No | Sí |
| fe_afip | **No** | No | No | No | Sí |
| purchases | No | Sí | No | Sí | No |
| inventory | No | Sí | No | Sí | No |
| accounting | No | Sí | No | Sí | No |
| tiendanube | No | Sí | No | Sí | No |
| tiendanube_administranet | No | Sí | No | Comentado | No |
| mercadopago | No | Sí | No | Sí | No |
| clover | No | Sí | No | Sí | No |
| administraNET_integration | No | Sí | No | No | No |
| logistics | No | Sí | No | Sí | No |
| finance | No | Sí | No | Sí | No |
| reports_ai | No | Sí | No | Sí | No |
| sales | No | No (eliminado) | No | No | No |

---

## 8. Conclusiones

1. **Instalación actual** es una “instalación mínima para Reportes”: core, login, dashboard, reports, self_checkout, stock. El resto de módulos de negocio están comentados en INSTALLED_APPS y en urls.py.
2. **Registry (MODULE_CONFIGS)** sigue definiendo 16 módulos; solo 6 tienen app instalada (core, login, dashboard, reports, self_checkout); **stock** no está en el registry pero sí instalado y en menú.
3. **Menú (APPS_MENU)** sigue incluyendo ítems para módulos sin app instalada (inventory, tiendanube, purchases, accounting, mercadopago, clover, finance, logistics, reports_ai). Su visibilidad depende de ModuleConfig en BD y de permisos; las URLs de esas apps no existen, por lo que pueden dar errores si se activan en BD sin instalar la app.
4. **fe_afip** es la única app con código en el repo que no está instalada ni referenciada en registro ni en URLs.
5. **stock** es la única app instalada y con URLs que no está en MODULE_CONFIGS; se trata como “siempre activa” vía `core_modules` en el menú.

---

## 9. Recomendaciones (solo informe, sin cambios aplicados)

- Decidir si **stock** debe añadirse a MODULE_CONFIGS para alinear registro con apps instaladas y menú.
- Decidir si **fe_afip** se activa (añadir a INSTALLED_APPS, urls y opcionalmente al registro) o se elimina/mueve del repo.
- Si se mantiene la instalación mínima, valorar quitar del menú (APPS_MENU) los ítems cuyas apps no están instaladas, o documentar que son “futuros” y no deben activarse en BD hasta instalar la app.
- Revisar ModuleConfig en BD: si hay módulos activos (is_active=True) que no tengan app instalada, la app no cargará y el registry/URLs dinámicos pueden comportarse mal; conviene alinear BD con la lista de apps realmente instaladas.
