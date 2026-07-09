# Propuesta — Trazabilidad MPR por Máquina / Línea / Operario

**Change:** `mpr-trazabilidad-maquina-linea-operario`
**Fecha:** 08/07/2026
**Exploración:** [exploration.md](./exploration.md)

---

## 1. Intención

Incorporar al MPR la dimensión física de planta que hoy no existe: **máquinas** agrupadas por **líneas**, con **operarios** que cargan su producción por máquina desde el **móvil** al fin de turno, y un **supervisor** que revisa, corrige desvíos (**gap**) y **aprueba**. La aprobación es el evento que envía el stock al depósito **"Producción"**. Habilita trazabilidad e histórico de qué artículo estuvo seteado en cada máquina y cuánto produjo cada operario/máquina/turno.

## 2. Problema

| Hoy | Dolor |
|-----|-------|
| No existe máquina ni línea (ni Synap ni legacy) | Imposible atribuir producción a un recurso físico |
| El parte mueve stock al guardar | No hay control/aprobación previa; desvíos entran directo a stock |
| Operarios sin login | No pueden cargar su parte desde el móvil |
| Sin histórico de seteo máquina→artículo | No hay trazabilidad de configuración en el tiempo |

## 3. Alcance

### Incluido (P0)
| # | Entrega |
|---|---------|
| P0-1 | Catálogos `mpr_linea` y `mpr_maquina` (CRUD supervisor) |
| P0-2 | Pertenencia `mpr_maquina_linea` **versionada** (vigencia_desde/hasta) |
| P0-3 | Habilitación `mpr_maquina_articulo` **versionada** (varios artículos activos por máquina) |
| P0-4 | Asignación operario→línea: `mpr_operario_linea` (habitual) + override en `mpr_roster_dia` |
| P0-5 | Mapeo operario↔usuario login (`usuarios` AdministraNET ↔ `sue_abm_empleado`) |
| P0-6 | Permisos MPR nuevos: `mpr.parte_operario`, `mpr.maquinas_lineas`, `mpr.aprobar_parte` + rol **Supervisor MPR** + rol **Operario** (solo `mpr.parte_operario`, sin `mpr.ver`) |
| P0-6b | **Landing por rol**: operario puro redirige por defecto a la carga móvil (login, `/`, dashboard); acceso al resto denegado por permiso |
| P0-6c | Entradas de menú nuevas en `APPS_MENU` (partes pendientes, líneas, máquinas, artículos por máquina, mapeo operario↔usuario), filtradas por permiso |
| P0-7 | UI móvil mobile-first: contexto automático, lista de máquinas con estado/total, captura docenas/pares (carga libre), autosave, confirmación y estado "pendiente" |
| P0-8 | Estado del parte (`borrador`/`pendiente`/`aprobado`) + origen (`movil_operario`/`directo_supervisor`); el móvil deja en `pendiente` sin mover stock |
| P0-9 | Bandeja supervisor: revisión, corrección y **aprobación del parte completo**; guarda por línea `cantidad_declarada`/`cantidad_aprobada`/`gap`/`motivo` |
| P0-10 | La aprobación ejecuta el asiento físico a depósito "Producción" + validación de cupo |
| P0-11 | Extensión ledger `mpr_parte`/`mpr_parte_linea` con `id_maquina` (+ snapshot) y campos de gap |
| P0-12 | Migración de esquema vía `core/services/legacy_mysql_schema/catalog.py` + `mpr/sql/` |
| P0-13 | Tests (servicios, POST móvil, aprobación/asiento, esquema) + docs `docs/mpr/` |

### Incluido (P1)
| # | Entrega |
|---|---------|
| P1-1 | Reporte de conciliación envíos↔producción (desvío no respaldado por `mpr_envio_produccion`) |
| P1-2 | Reporte "Por operario/máquina/línea" (producción, %2da, gap) — extiende plan tejedor |

### Fuera de alcance
- Consumo de insumos/hilos por BOM al aprobar (solo ingresa producción terminada).
- Habilitación máquina→artículo dependiente del turno (es a nivel máquina).
- Programación/scheduling de máquinas y mantenimiento.
- Alta masiva automática de usuarios de operario (se define proceso, no ETL masivo).

## 4. Capabilities

> Contrato con sdd-spec. Nombres kebab-case; deltas de capabilities existentes van en la carpeta del change.

### New Capabilities
| Capability | Spec | Descripción |
|------------|------|-------------|
| `mpr-catalogo-maquina-linea` | `specs/mpr-catalogo-maquina-linea/spec.md` | Catálogos máquina/línea + pertenencia versionada |
| `mpr-asignacion-maquina-articulo` | `specs/mpr-asignacion-maquina-articulo/spec.md` | Habilitación máquina→artículo versionada |
| `mpr-operario-login` | `specs/mpr-operario-login/spec.md` | Mapeo operario↔usuario, rol operario/supervisor MPR |
| `mpr-parte-movil-operario` | `specs/mpr-parte-movil-operario/spec.md` | Carga móvil por máquina, estado borrador/pendiente, carga libre |
| `mpr-aprobacion-parte-supervisor` | `specs/mpr-aprobacion-parte-supervisor/spec.md` | Revisión, gap por línea, aprobación → asiento físico a "Producción" |

### Modified Capabilities
| Capability | Cambio |
|------------|--------|
| `mpr-opp-parte-produccion` (delta) | Estado/origen en `MprParte`; `id_maquina` + gap en `MprParteLinea`; asiento diferido a la aprobación |
| `mpr-turnos-roster` (delta) | `id_linea` override por día en `MprRosterDia` |

## 5. Enfoque técnico (resumen)

- **Persistencia:** tablas nuevas snake_case (`mpr_linea`, `mpr_maquina`, `mpr_maquina_linea`, `mpr_maquina_articulo`, `mpr_operario_linea`, mapeo operario↔usuario) creadas vía catálogo central `core/services/legacy_mysql_schema/catalog.py` (proveedor nuevo) + DDL runtime en `mpr/sql/`. Extensión de `mpr_parte`/`mpr_parte_linea` por la misma vía.
- **Versionado:** patrón `vigencia_desde`/`vigencia_hasta` (NULL = vigente); cierre de vigencia al reasignar.
- **Flujo dos etapas:** refactor de `registrar_parte_produccion` para separar *declaración* (no mueve stock, `estado=pendiente`) de *aprobación* (`aprobar_parte_produccion`, mueve stock reutilizando `_registrar_asiento_fisico_opp_parte` y valida cupo Fabricando). El parte directo del supervisor sigue disponible.
- **Roster:** reutilizar `MprRosterDia` (operario↔turno↔fecha) + `id_linea` override; línea habitual desde `mpr_operario_linea`.
- **Login operario:** reutilizar `login/administranet_auth.py`; resolver `id_operario` desde el mapeo; permisos vía `_usuario_tiene_permiso_mpr` + rol Supervisor MPR.
- **UI móvil:** `get_template_for_device` + templates `mpr/templates/mpr/mobile/` (canon UI del repo).

## 6. Affected Areas

| Área | Impacto | Descripción |
|------|---------|-------------|
| `core/services/legacy_mysql_schema/catalog.py` | Modificado | Proveedor nuevo (tablas máquina/línea + columnas ledger) |
| `mpr/sql/` | Nuevo | DDL runtime de tablas/columnas nuevas |
| `mpr/models.py` | Modificado | Estado/origen/gap/id_maquina en modelos parte; `id_linea` en roster |
| `mpr/services.py` | Modificado | CRUD catálogos, asignaciones, split declaración/aprobación, gap |
| `mpr/repositories/` | Modificado/Nuevo | Repos de máquina/línea/asignación; ledger extendido |
| `mpr/views.py`, `mpr/urls.py` | Modificado | Vistas catálogos, móvil operario, bandeja aprobación |
| `mpr/templates/mpr/` (+ `mobile/`) | Nuevo | Pantallas catálogos, captura móvil, aprobación |
| `login/views.py` | Modificado | Landing por rol (redirect operario a carga móvil); resolver operario desde el mapeo |
| `core/constantes_permisos.py` | Modificado | Permisos nuevos `mpr.parte_operario`, `mpr.maquinas_lineas`, `mpr.aprobar_parte` |
| `core/utils/utils.py` (`APPS_MENU`) | Modificado | Items de menú nuevos (config catálogos, partes pendientes) filtrados por permiso |
| `core/views/views_general.py`, `django_project/urls.py` | Modificado | Redirección de operario puro desde `/` y dashboard |
| `core/pwa_nivel_a.py` | Modificado | Servir la carga como app móvil enfocada (sin exponer otros items al operario) |
| `docs/mpr/` | Nuevo | Documentación del circuito |

## 7. Riesgos

| Riesgo | Prob. | Mitigación |
|--------|-------|------------|
| Stock en "Producción" no respaldado por envíos (carga libre) | Media | Validación en aprobación + reporte de conciliación (P1) |
| Alta/gestión de usuarios de operario en `usuarios` (AES, puesto, sucursal) | Media | Definir proceso y mapeo; scope por `base_empresa` |
| Cambio de comportamiento del parte (stock diferido a aprobación) | Media | Coexistencia: parte directo intacto; flag de estado; tests de regresión |
| Integridad del versionado (solapamiento de vigencias) | Baja | Constraint/servicio que cierra vigencia previa al reasignar |
| DDL en MySQL compartido con VB6 | Baja | Solo tablas/columnas nuevas aditivas; idempotencia catálogo |

## 8. Rollback Plan

- Esquema: columnas/tablas nuevas son **aditivas**; rollback = no usarlas (feature-flag de UI) y, si necesario, `DROP` de tablas nuevas (sin tocar tablas VB6 existentes).
- Código: el parte directo actual queda intacto; desactivar rutas móvil/aprobación revierte al flujo previo.
- Migraciones Django (Postgres) reversibles con `migrate mpr <anterior>`.

## 9. Dependencias

- Depósito con `tipo_mpr='Produccion'` configurado (`/mpr/config-depositos/`).
- Roster/turnos operativos (`mpr-turnos-roster`).
- Existencia de operarios en `sue_abm_empleado`.

## 10. Criterios de éxito

- [ ] Supervisor crea líneas/máquinas y habilita artículos por máquina con histórico consultable de vigencias.
- [ ] Operario inicia sesión en el móvil y ve solo las máquinas de su línea/turno con sus artículos habilitados.
- [ ] La carga del operario queda en `pendiente` **sin** mover stock.
- [ ] El supervisor aprueba el parte completo; se guarda `gap` por línea y **recién ahí** sube el stock del depósito "Producción".
- [ ] El parte directo del supervisor sigue funcionando como hoy.
- [ ] Todas las tablas nuevas usan separador `_` y se crean vía el catálogo central.
