# Informe de verificación — opt-bloqueo-pack-sin-receta

**Change:** opt-bloqueo-pack-sin-receta  
**Versión de contrato:** delta spec mpr-opt-creacion-ventana-pack  
**Modo:** Standard (strict_tdd no activo)  
**Almacén:** hybrid (openspec + Engram)  
**Fecha verificación:** 14/07/2026

---

## Veredicto

**PASS WITH WARNINGS** — Implementación completa (todas las tareas marcadas); 16/16 tests OK en contenedor; `manage.py check` sin issues. Los escenarios MUST de validación/bloqueo están cubiertos con evidencia runtime. Quedan huecos menores: render HTML del modal con múltiples packs sin receta y cierre del modal sin test automatizado (REQ-VPK-003 SHOULD).

---

## Completitud de tareas

| Métrica | Valor |
|--------|-------|
| Tareas totales (bloques principales) | 14 |
| Tareas completadas | 14 |
| Tareas incompletas | 0 |

Todas las tareas en `tasks.md` están marcadas `[x]` (Fases 1–4: backend, template, tests, documentación).

---

## Ejecución de build y tests

**Build / system check:** ✅ OK

```text
docker exec Synap_app python manage.py check
→ System check identified no issues (0 silenced).
```

**Tests del change:** ✅ 16 passed

```text
docker exec Synap_app python manage.py test mpr.tests.test_ventana_pack_bloqueo_sin_receta -v 2
→ Ran 16 tests in 0.024s — OK
```

**Desglose:**

| Clase | Tests | Resultado |
|-------|-------|-----------|
| `TieneRecetaHelperTest` | 7 | ✅ OK |
| `VentanaPackAgruparPostRecetaTest` | 6 | ✅ OK |
| `VentanaPackGetContextTest` | 3 | ✅ OK |

**Cobertura:** ➖ No configurada en `openspec/config.yaml` para este change.

---

## Matriz de cumplimiento de escenarios (spec)

| Requisito / escenario | Test | Resultado |
|----------------------|------|-----------|
| REQ-VPK-001 — Todos los packs con receta → continúa | `VentanaPackAgruparPostRecetaTest > test_todos_con_receta_continua` | ✅ COMPLIANT |
| REQ-VPK-001 — Un pack sin receta → bloquea | `VentanaPackAgruparPostRecetaTest > test_uno_sin_receta_bloquea` | ✅ COMPLIANT |
| REQ-VPK-001 — Selección mixta → bloquea, lista solo sin receta | `VentanaPackAgruparPostRecetaTest > test_mixto_bloquea_y_lista_solo_sin_receta` | ✅ COMPLIANT |
| REQ-VPK-002 — Modal muestra código sistema, manual y descripción | `VentanaPackGetContextTest > test_modal_renderizado_cuando_hay_sin_receta` | ⚠️ PARTIAL (contexto; sin assert HTML renderizado) |
| REQ-VPK-002 — Modal lista múltiples packs sin receta | (ninguno con ≥2 ítems en modal) | ❌ UNTESTED |
| REQ-VPK-003 — Usuario cierra modal y permanece en Pantalla 1 | (ninguno) | ❌ UNTESTED (SHOULD; evidencia estática en template) |

**Escenarios adicionales cubiertos por tests (no en spec Gherkin):**

| Caso | Test | Resultado |
|------|------|-----------|
| `receta_json=None` | `test_receta_json_none_se_trata_como_sin_receta` | ✅ COMPLIANT |
| JSON inválido | `test_receta_json_invalido_se_trata_como_sin_receta` | ✅ COMPLIANT |
| POST directo (anti-bypass) | `test_post_directo_sin_receta_bloqueado` | ✅ COMPLIANT |
| GET limpia sesión temporal | `test_get_limpia_sesion_sin_receta` | ✅ COMPLIANT |
| GET sin sesión → lista vacía | `test_get_sin_sesion_temporal_devuelve_lista_vacia` | ✅ COMPLIANT |

**Resumen escenarios spec:** 3/6 compliant en runtime; 1 partial; 2 untested (1 MUST parcial, 1 MUST untested, 1 SHOULD untested).

---

## Correctitud (evidencia estática)

| Requisito / restricción | Estado | Notas |
|-------------------------|--------|-------|
| REQ-VPK-001 — Validación antes de continuar | ✅ | `_tiene_receta` + bloqueo en `VentanaPackAgruparView.post` (`mpr/views.py` ~4581–4597) |
| REQ-VPK-002 — Modal con datos del artículo | ✅ | Modal `{% if packs_sin_receta %}` en `ventana_pack.html` (~599–654) |
| REQ-VPK-003 — Cierre y corrección | ✅ | Botón «Cerrar» con `.remove()`; usuario permanece en Pantalla 1 |
| Validación en servidor (constraint) | ✅ | Antes de `ventana_pack_seleccion` |
| Modal accesible Tailwind/Alpine | ✅ | `role="dialog"`, `aria-modal`, dark mode |
| Fuente `receta_json` | ✅ | Mismo lookup de `listar_ventana_pack` |
| Anti-bypass POST directo | ✅ | Validación en `VentanaPackAgruparView.post` |
| Helper `_tiene_receta` | ✅ | Cubre None, vacío, JSON inválido, lista vacía |
| Sesión temporal `ventana_pack_sin_receta` | ✅ | `session.pop` en `VentanaPackView.get_context_data` (~4693–4695) |
| Validación JS cliente (UX) | ✅ | Interceptor en `form-crear-opt` + `mostrarModalSinRecetaCliente` |
| Documentación | ✅ | `docs/mpr/MPR_FLUJO_CREAR_OPT.md` §0 |

---

## Coherencia con diseño

| Decisión | ¿Seguida? | Notas |
|----------|-----------|-------|
| Validación autoritativa en `VentanaPackAgruparView.post` | ✅ | Insertada tras `filas_sesion`, antes de sesión |
| Helper `_tiene_receta` en `mpr/views.py` | ✅ | Implementado ~4414–4423 |
| Comunicación vía `ventana_pack_sin_receta` + PRG | ✅ | Redirect a `mpr:ventana_pack` |
| Modal en `ventana_pack.html` (no base) | ✅ | Patrón overlay Tailwind |
| Validación JS opcional | ✅ | `data-codigo-manual`, `data-descripcion`, interceptor submit |
| Sin cambios en `services.py` / `urls.py` | ✅ | Según diseño |
| Archivo de tests dedicado | ✅ | `test_ventana_pack_bloqueo_sin_receta.py` |
| Preselección `?articulo=` sin validar receta | ⚠️ | Deuda técnica documentada en design §6 |

---

## Issues encontrados

### CRITICAL (bloquean archive)

Ninguno.

### WARNING (convendría corregir)

1. **REQ-VPK-002 escenario múltiples packs:** No hay test con ≥2 artículos sin receta verificando listado en sesión/modal.
2. **REQ-VPK-002 modal HTML:** `test_modal_renderizado_cuando_hay_sin_receta` valida contexto, no render (`Client.get` + assert `id="modal-sin-receta"` en HTML).
3. **REQ-VPK-003 sin test:** Cierre del modal y permanencia en Pantalla 1 solo verificados estáticamente en template.
4. **Preselección tablero:** Flujo `?articulo=` salta validación (riesgo bajo, documentado).

### SUGGESTION

1. Añadir test POST con 2 packs sin receta y assert `len(packs_sin_receta)==2`.
2. Añadir test de integración con `Client` que renderice `ventana_pack.html` y verifique filas del modal en HTML.
3. Renombrar referencia en `tasks.md` (tabla menciona `FLUJO_VENTANA_PACK_OPT.md`; doc real es `MPR_FLUJO_CREAR_OPT.md`).

---

## Artefactos revisados

- `openspec/changes/opt-bloqueo-pack-sin-receta/specs/mpr-opt-creacion-ventana-pack/spec.md`
- `openspec/changes/opt-bloqueo-pack-sin-receta/design.md`
- `openspec/changes/opt-bloqueo-pack-sin-receta/tasks.md`
- `mpr/views.py`, `mpr/templates/mpr/ventana_pack.html`
- `mpr/tests/test_ventana_pack_bloqueo_sin_receta.py`
- `docs/mpr/MPR_FLUJO_CREAR_OPT.md`

---

## Próxima fase recomendada

`sdd-archive` — veredicto PASS WITH WARNINGS; sin blockers CRITICAL.
