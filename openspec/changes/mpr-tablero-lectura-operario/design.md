# Design: Tablero de producción — lectura para operarios

**Change:** `mpr-tablero-lectura-operario` · **Fecha:** 27/07/2026

## Technical Approach

Permiso opt-in `mpr.tablero_ver` (siembra vía `core/constantes_permisos.py` + `apply_synap_permisos_tables`). Helpers y mixins en `mpr/views.py` reutilizan `_usuario_tiene_permiso_mpr`. GET tablero + Actualizar aceptan `mpr.ver` OR `mpr.tablero_ver`; mutaciones (Enviar, anular, CC, escritorio) exigen `mpr.ver`. UI del tablero recibe `puede_enviar` / `solo_lectura_tablero` para ocultar acciones sin depender solo del backend. Menú: extender chequeo de `permission`/`permiso` a lista OR. Landing sin cambio semántico (`es_operario_puro` = parte ∧ ¬ver).

## Architecture Decisions

### ADR-1: Permiso `mpr.tablero_ver` opt-in

| Opción | Tradeoff | Decisión |
|--------|----------|----------|
| Reutilizar `mpr.parte_operario` | Rompe separación operario puro | **Rechazado** |
| Nuevo `mpr.tablero_ver` | Requiere siembra + asignación puesto | **Elegido** |
| Quitar necesidad de `mpr.ver` globalmente | Fuera de scope | **Rechazado** |

**Rationale:** Lectura acotada sin abrir escritorio MPR. Etiqueta: «Ver tablero de producción (solo lectura)».

### ADR-2: Helpers centralizados en `mpr/views.py`

```python
PERMISO_TABLERO_VER = "mpr.tablero_ver"

def _usuario_puede_ver_tablero_produccion(user) -> bool:
    return (
        _usuario_tiene_permiso_mpr(user, "mpr.ver")
        or _usuario_tiene_permiso_mpr(user, PERMISO_TABLERO_VER)
    )

def _usuario_puede_enviar_desde_tablero(user) -> bool:
    return _usuario_tiene_permiso_mpr(user, "mpr.ver")

def _context_flags_tablero(user) -> dict:
    puede_enviar = _usuario_puede_enviar_desde_tablero(user)
    return {
        "puede_enviar": puede_enviar,
        "solo_lectura_tablero": _usuario_puede_ver_tablero_produccion(user) and not puede_enviar,
        "puede_anular_envios": _usuario_puede_anular_envios(user) and puede_enviar,
    }
```

**Alternativa:** módulo `mpr/permissions.py` — rechazada para no fragmentar helpers MPR ya en `views.py`.

### ADR-3: Mixins de guardia

| Mixin | Uso | Guard |
|-------|-----|-------|
| `MprTableroVerMixin` | `TableroProduccionView`, `TableroProduccionActualizarView` | `_usuario_puede_ver_tablero_produccion` |
| `MprEscritorioVerMixin(MprPermisoMixin)` | Todas las vistas MPR escritorio sin permiso específico | `permiso_requerido = "mpr.ver"` |
| `MprPermisoMixin` (existente) | Operario, máquinas, aprobar parte, imputación | Sin cambio |

`MprTableroVerMixin.dispatch` → `PermissionDenied` si falla; encadenar **después** de `MprLoginRequiredMixin`.

**Enviar/anular/CC:** añadir `MprEscritorioVerMixin`; corregir `EnviosProduccionListView` / `AnularEnviosProduccionView` (`permiso_requerido=""` → `"mpr.ver"`).

### ADR-4: Flags de contexto en tablero

Inyectar `**_context_flags_tablero(request.user)` en `TableroProduccionView`. Template `tablero_produccion.html`:

- `{% if puede_enviar %}`: botón Enviar, modales envío, columna inputs, `#form-enviar-lote`, menú Armado/Anular.
- `{% if not solo_lectura_tablero %}`: enlaces CC/Parte en modal Fabricando; pasar flag a `chrome_nav_flujo.html` para ocultar Parte/CC/KPI.
- Manual (`manual_usuario`): visible; vista con `MprTableroVerMixin` (documentación de lectura).

### ADR-5: Menú OR en `core/utils/utils.py`

Extender `_permiso_menu_ok(perm, permisos_usuario)` → acepta `str | list[str]` (cualquiera basta). Aplicar en `_resolver_url_item` y REGLA 4 de `apps_visibles_sin_filtro_pwa`.

| Nodo | `permiso` / `permission` |
|------|--------------------------|
| App `mpr` | `["mpr.ver", "mpr.tablero_ver"]` |
| Item Tablero | `["mpr.ver", "mpr.tablero_ver"]` |
| Resto ítems MPR | sin cambio (`mpr.ver` u otros) |

Operario+tablero ve módulo MPR con solo «Tablero de producción».

### ADR-6: Landing (`mpr/landing.py`)

Sin cambio de firma. `es_operario_puro` = `parte_operario` ∧ ¬`mpr.ver`. Operario+tablero sigue aterrizando en `/mpr/mi-parte/` (decisión cerrada).

## Data Flow

```
Login → landing_url_para_usuario
         ├─ operario puro / operario+tablero → /mpr/mi-parte/
         └─ resto → dashboard normal

Menú → apps_visibles (mpr.ver OR tablero_ver) → submenú Tablero

GET tablero → MprTableroVerMixin → filas + flags UI
POST actualizar → MprTableroVerMixin → sesión timestamp → redirect GET

POST enviar/anular/CC → MprEscritorioVerMixin → 403 si solo tablero_ver
```

## Endpoints tablero y escritorio MPR

### GET / lectura tablero (`mpr.ver` OR `mpr.tablero_ver`)

| URL | Vista | Notas |
|-----|-------|-------|
| `GET /mpr/tablero-produccion/` | `TableroProduccionView` | Filtros Pack\|Par, modales Fabricando (datos embebidos) |
| `POST /mpr/tablero-produccion/actualizar/` | `TableroProduccionActualizarView` | Solo timestamp sesión; no muta ledger |
| `GET /mpr/manual/` | `ManualUsuarioMprView` | Documentación |

**Sin AJAX adicional:** el tablero no usa `fetch`/API; modales Alpine consumen JSON embebido en filas del GET.

### POST / mutaciones — solo `mpr.ver`

| URL | Vista |
|-----|-------|
| `POST /mpr/tablero-produccion/enviar/` | `EnviarProduccionLoteView` |
| `GET /mpr/tablero-produccion/envios/` | `EnviosProduccionListView` |
| `POST /mpr/tablero-produccion/envios/anular/` | `AnularEnviosProduccionView` |
| `POST /mpr/tablero-produccion/transicion/` | `TransicionLoteView` (legacy) |
| `GET /mpr/tablero-produccion/clasificacion-produccion/` | `ClasificacionProduccionView` |
| `POST …/clasificacion-produccion/registrar/` | `RegistrarClasificacionProduccionView` |

### Vistas escritorio a endurecer (`+ MprEscritorioVerMixin`, `mpr.ver`)

Todas las clases en `mpr/views.py` con solo `MprLoginRequiredMixin` **excepto** tablero GET/actualizar y `ParteMovilOperarioView` (`mpr.parte_operario`):

`TableroView`, `WizardProduccionView`, `OpListView`, `OptListView`, `OptDetailView`, `RegistrarOppView`, `ArmadoOptView`, `CerrarOptView`, `NuevaOptView`, `BomListView`, `BomDetailView`, `BomCreateView`, `BomEditView`, `PedidosFabricaListView`, `OptsPorPedidoView`, `ConfigDepositosView`, `OperariosListView`, `OperarioCreateView`, `OperarioUpdateView`, `OperarioAnularView`, `OperarioReactivarView`, `ArmadoLegacyView`, `ReclasificacionView`, APIs armado (`ArmadoPacksCatalogAPIView`, `ArmadoBomPackAPIView`, `ArmadoSurtidoStockOrigenAPIView`, `ArmadoSurtidoValidarItemLoteAPIView`), `ArmadoSurtidoView`, `ArmadoSurtidoRedirectView`, `ReportesMPRView`, `VentanaPack*`, `EmpleadosOperariosAPIView`, turnos (`TurnosListView`, `TurnoCreateView`, `TurnoUpdateView`), planificación roster, `ParteProduccionView`, `RegistrarParteProduccionView`, `AjusteParteView`, `TrazabilidadOptView`, `opt_comprobante_pdf_view`.

**`mpr/best_migration/views.py`:** todas las clases con solo `MprLoginRequiredMixin` (+ mixin escritorio).

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `core/constantes_permisos.py` | Modify | Añadir `mpr.tablero_ver` |
| `mpr/views.py` | Modify | Helpers, mixins, guards, context flags, endurecer vistas |
| `mpr/best_migration/views.py` | Modify | `MprEscritorioVerMixin` en hub/APIs |
| `mpr/landing.py` | — | Sin cambio (ver ADR-6) |
| `core/utils/utils.py` | Modify | OR menú + helper `_permiso_menu_ok` |
| `mpr/templates/mpr/tablero_produccion.html` | Modify | Condicionales `puede_enviar` / `solo_lectura_tablero` |
| `mpr/templates/mpr/includes/chrome_nav_flujo.html` | Modify | Ocultar Parte/CC/KPI si solo lectura |
| `docs/mpr/*.md` | Modify | Perfil operario+tablero, matriz permisos |
| `mpr/tests/test_tablero_lectura_operario.py` | Create | GET 200, POST enviar 403, CC URL 403, menú |

## Testing Strategy

| Layer | Qué | Cómo |
|-------|-----|------|
| Unit | Helpers OR permiso | Mock `tiene_permiso` |
| Integration | Vistas tablero vs enviar/CC | `Client` + usuario `parte_operario`+`tablero_ver` |
| Integration | Menú parcial MPR | `apps_visibles_sin_filtro_pwa` |
| Integration | Landing operario+tablero | `landing_url_para_usuario` → mi-parte |
| Regression | `mpr.ver` full | Tablero envía OK |

## Migration / Rollout

Siembra catálogo (`apply_synap_permisos_tables` / sync). Asignación manual en puesto operario. Sin migración de datos. Rollback: quitar permiso de puestos + revert guards.

## Open Questions

- [ ] ¿Mostrar ítem «Mi parte» en menú MPR para operario+tablero? (propuesta: no; acceso vía landing.)
