# Informe de verificación — ecom-venta-pedido-unificada

**Change:** `ecom-venta-pedido-unificada`  
**Fecha:** 13/07/2026  
**Modo:** Standard (strict_tdd no configurado)  
**Verificador:** sdd-verify (hybrid)

---

## Veredicto

**PASS WITH WARNINGS**

Implementación completa y coherente con proposal/design/tasks; tests obligatorios del change en verde (44/44). Cinco escenarios delta carecen de prueba automatizada de comportamiento (modos shell y acciones JS); cobertura estructural en código es sólida.

**Listo para `sdd-archive`** con advertencias documentadas (no bloqueantes).

---

## Completitud de tareas

| Métrica | Valor |
|--------|-------|
| Tareas totales | 17 |
| Completadas `[x]` | 17 |
| Incompletas | 0 |

Todas las fases (1–5) marcadas completas en `tasks.md`.

---

## Build y ejecución de tests

**Build / check:** ✅ `python manage.py check` — sin errores (solo warnings de despliegue en entorno dev).

**Tests obligatorios (usuario):** ✅ 44 passed, 0 failed, 0 skipped

```bash
docker exec Synap_app python manage.py test \
  ecom.tests.test_compra_mayorista_view \
  ecom.tests.test_pedido_gestion \
  ecom.tests.test_pedido_pendientes \
  ecom.tests.test_mayorista_cart_service \
  --keepdb
```

**Tests adicionales relacionados:**

| Módulo | Resultado | Notas |
|--------|-----------|-------|
| `ecom.tests.test_compra_mayorista_cliente` | ✅ 2/2 | GET `/venta/` limpia cliente vendedor |
| `ecom.tests.test_pedidos_hub_pipeline` | ✅ 3/3 | Pipeline hub; no assert de URL en cards |
| `ecom.tests.test_cliente_relay` | ⚠️ ERROR import | `ModuleNotFoundError: pytest` — preexistente, no fallo de lógica del change |

**Cobertura:** No disponible / no ejecutada.

---

## Matriz de cumplimiento de specs (delta propio)

Alcance verificado: **REQ-VTA-01..04** + **REQ-NAV-01..03** (delta en `openspec/changes/.../specs/`).  
REQ-VTA-05..09 viven en `openspec/specs/ecom-pedido-venta-shell/spec.md` (change `ecom-pedidos-usabilidad-supervisor`); **fuera del alcance de este verify**.

| Requisito | Escenario | Test | Resultado |
|-----------|-----------|------|-----------|
| REQ-VTA-01 | Alta sin cod_mov | `test_compra_mayorista_view > test_render_ok_con_sesion` | ✅ COMPLIANT |
| REQ-VTA-01 | Abrir PED existente | (ninguno) | ❌ UNTESTED |
| REQ-VTA-02 | Pendiente editable | (ninguno) | ❌ UNTESTED |
| REQ-VTA-02 | En preparación solo lectura | (ninguno) | ❌ UNTESTED |
| REQ-VTA-03 | Anular visible solo si permitido | (ninguno) | ❌ UNTESTED |
| REQ-VTA-04 | Modal de confirmación | (ninguno) | ❌ UNTESTED |
| REQ-NAV-01 | Bookmark compra | `test_compra_mayorista_view > test_redirect_compra_alias_a_venta` | ✅ COMPLIANT |
| REQ-NAV-02 | Legacy detalle | `test_compra_mayorista_view > test_redirect_detalle_a_venta_cod_mov` | ✅ COMPLIANT |
| REQ-NAV-03 | Card PED del hub | (ninguno directo) | ⚠️ PARTIAL |

**Resumen cumplimiento comportamental:** 3/9 COMPLIANT · 1/9 PARTIAL · 5/9 UNTESTED

---

## Correctitud (evidencia estática)

| Requisito | Estado | Evidencia |
|-----------|--------|-----------|
| REQ-VTA-01 | ✅ Implementado | `CompraMayoristaView` en `/mayoristapp/venta/`; bootstrap `?cod_mov=` en `mayoristapp_web_views.py` |
| REQ-VTA-02 | ✅ Implementado | Resolución `modo` (`nuevo` / `editar_pendiente` / `consulta`) en vista + `compra_mayorista_pedido.mjs`; UI bloquea catálogo/checkout con `esConsulta` / `pedidoEditable` en `compra_mayorista.html` |
| REQ-VTA-03 | ✅ Implementado | Hero Anular/Repetir/PDF/mail; `puedeAnular` desde cabecera; APIs reutilizadas |
| REQ-VTA-04 | ✅ Implementado | `abrirResumen()` → diálogo `confirmar_cambios`; `_confirmarCambiosPendiente()` anula + checkout + redirect |
| REQ-NAV-01 | ✅ Implementado | `urls.py` RedirectView `mayoristapp/compra/` → `mayoristapp_venta` con `query_string=True` |
| REQ-NAV-02 | ✅ Implementado | `PedidoDetalleView` → redirect `venta/?cod_mov=` |
| REQ-NAV-03 | ✅ Implementado | `pedidos_hub_pipeline.py`, `menu_config.py`, `core/utils/utils.py`, listados → `mayoristapp_venta` + `?cod_mov=` |

---

## Coherencia con design

| Decisión | ¿Seguida? | Notas |
|----------|-----------|-------|
| Ruta canónica `/venta/` + alias `/compra/` | ✅ | Coincide con design §1 |
| Modos `nuevo \| editar_pendiente \| consulta` | ✅ | Vista + mixin JS |
| Confirmar Pendiente = modal + anular + checkout | ✅ | `compra_mayorista_pedido.mjs` |
| Acciones portadas del detalle | ✅ | URLs bootstrap en contexto venta |
| Textos «Pedido de venta» | ✅ | `page_title`, template, test render |
| Tests redirects + hub/frm=0 + vista venta | ⚠️ Parcial | Redirects y vista OK; frm=0 no ejecutado (pytest); modos sin test E2E |

---

## Issues encontrados

### CRITICAL (bloquean archive)

Ninguno.

### WARNING (recomendado corregir)

1. **5 escenarios delta sin test automatizado** — modos editable/consulta, modal confirmar cambios, hero Anular y carga `?cod_mov=` dependen de JS; solo hay evidencia estática.
2. **REQ-NAV-03 parcial** — `pedidos_hub_pipeline` genera URLs `/venta/?cod_mov=` pero no hay assert en tests del hub.
3. **`test_cliente_relay` no ejecutable** en contenedor (`pytest` ausente); el relay `frm=0` → `/venta/` está implementado en `cliente_relay.py` y documentado, pero no verificado en esta corrida.

### SUGGESTION

1. Añadir tests de integración mínimos: bootstrap `pedido_bootstrap` con `modo=consulta`/`editar_pendiente` en `CompraMayoristaView` (mock relays).
2. Test unitario en `TestConstruirHub` que valide `url` de ítems PED contiene `/mayoristapp/venta/` y `cod_mov=`.
3. Instalar `pytest` en imagen dev o migrar tests de `test_cliente_relay.py` a `unittest` puro.

---

## Documentación

- ✅ `docs/ecom/SPEC_GESTION_PEDIDOS_SYNAP.md` — §6.2 y rutas `/venta/`
- ✅ `docs/ecom/UI_COMPRA_MAYORISTA_P3.md` — ruta canónica
- ✅ Inventarios/specs cliente actualizados con `frm=0` → venta

---

## Próximo paso recomendado

`sdd-archive` — veredicto PASS WITH WARNINGS; gaps de test no bloquean el merge del change.
