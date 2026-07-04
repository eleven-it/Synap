# Checklist de Implementación: Bloqueo de packs sin receta en ventana pack OPT

**Change:** `opt-bloqueo-pack-sin-receta`  
**Proyecto:** Synap (Django)  
**Fecha:** 2026-07-02  
**Estado:** Completado

---

## Fase 1: Backend (mpr/views.py)

### 1.1 Añadir helper `_tiene_receta`
- [x] Importar `json` (o reutilizar import existente) cerca del inicio del módulo `mpr/views.py`
- [x] Definir función privada `_tiene_receta(fila: dict) -> bool` por encima de la clase `VentanaPackAgruparView` (aprox. líneas ~4070)
  - Lógica: devolver `False` si `fila.get("receta_json")` es `None`/ausente
  - Intentar `json.loads(raw)` en bloque `try/except (ValueError, TypeError)`
  - Devolver `False` si el parsing falla
  - Devolver `True` solo si `receta` es `list` y `len(receta) > 0`
- **Mapeo requisito:** REQ-VPK-001 (criterio "sin receta" = JSON vacío/inválido)
- **Archivo:** `mpr/views.py`

### 1.2 Modificar `VentanaPackAgruparView.post` — validación de receta
- [x] Localizar el bloque en `VentanaPackAgruparView.post` que guarda `ventana_pack_seleccion` (líneas ~4106-4110)
- [x] **Insertar antes** de `request.session["ventana_pack_seleccion"] = ...`:
  - Construir lista `packs_sin_receta` con list comprehension que:
    - Itera `filas_sesion` (qty > 0)
    - Recupera fila completa con `lookup.get(fila["id_articulo"])`
    - Filtra con `not _tiene_receta(f)`
    - Extrae dict con claves `id_articulo`, `codigo_manual`, `descripcion_articulo`
  - Si `packs_sin_receta` no está vacía:
    - Guardar `request.session["ventana_pack_sin_receta"] = packs_sin_receta`
    - Devolver `redirect("mpr:ventana_pack")` **sin** guardar `ventana_pack_seleccion`
- [x] Verificar que la ruta "feliz" (todos con receta) sigue guardando `ventana_pack_seleccion` y redirigiendo a `ventana_pack_agrupar`
- **Mapeo requisito:** REQ-VPK-001 (validación servidor, bloqueo antes de avanzar)
- **Archivo:** `mpr/views.py`

### 1.3 Modificar `VentanaPackView.get_context_data` — leer y limpiar sesión temporal
- [x] Localizar método `get_context_data` en clase `VentanaPackView` (aprox. línea ~4010)
- [x] **Al inicio** del método (antes de poblar `context["filas"]`), añadir:
  - `packs_sin_receta = self.request.session.pop("ventana_pack_sin_receta", None)`
  - `context["packs_sin_receta"] = packs_sin_receta or []`
- [x] Verificar que `session.pop` limpia la clave (evita mostrar modal repetidamente en reloads)
- **Mapeo requisito:** REQ-VPK-002 (exponer datos del modal al template), REQ-VPK-003 (usuario vuelve a Pantalla 1)
- **Archivo:** `mpr/views.py`

---

## Fase 2: Frontend/Template (mpr/templates/mpr/ventana_pack.html)

### 2.1 Añadir modal de bloqueo con estructura Tailwind
- [x] Localizar el final de `ventana_pack.html`, antes de `{% endblock %}`
- [x] Insertar bloque condicional `{% if packs_sin_receta %}` con modal completo:
  - Overlay fijo `fixed inset-0 z-[100]` con `bg-black/50 backdrop-blur-sm`
  - Contenedor blanco `max-w-lg rounded-2xl border-amber-200/90` (dark mode compatible)
  - Icono `material-icons warning_amber` en círculo amber
  - Título "Pack(s) sin receta definida" (`text-lg font-bold`)
  - Descripción explicativa (texto ayuda para cargar receta en módulo correspondiente)
  - Tabla con columnas: Cód. Sistema | Cód. Manual | Descripción
    - Loop `{% for p in packs_sin_receta %}`
    - Mostrar `{{ p.id_articulo }}`, `{{ p.codigo_manual|default:"-" }}`, `{{ p.descripcion_articulo|default:"-" }}`
  - Botón "Cerrar" con `onclick="document.getElementById('modal-sin-receta').remove();"`
- [x] Verificar que el modal tiene `id="modal-sin-receta"` para JS de cierre
- [x] Verificar accesibilidad: `role="dialog"`, `aria-modal="true"`, `aria-labelledby="modal-sin-receta-titulo"`
- **Mapeo requisito:** REQ-VPK-002 (contenido del modal con código sistema, manual, descripción), REQ-VPK-003 (botón cerrar, vuelve a Pantalla 1)
- **Archivo:** `mpr/templates/mpr/ventana_pack.html`

### 2.2 Añadir data attributes a filas de tabla (soporte para JS cliente)
- [x] Localizar el loop `{% for f in filas %}` de la tabla de packs en `ventana_pack.html`
- [x] En el elemento `<tr>` de cada fila, añadir:
  - `data-codigo-manual="{{ f.codigo_manual|default:'-' }}"`
  - `data-descripcion="{{ f.descripcion_articulo|default:'-'|escape }}"`
- [x] Verificar que `data-receta="{{ f.receta_json|default:'[]'|escape }}"` ya existe en elemento `.receta-tooltip-trigger` (no modificar)
- **Mapeo requisito:** REQ-VPK-001 (validación cliente opcional, mejora UX)
- **Archivo:** `mpr/templates/mpr/ventana_pack.html`

### 2.3 Añadir interceptor JS cliente (validación temprana opcional)
- [x] Localizar el bloque de scripts al final de `ventana_pack.html` (o añadir nuevo IIFE)
- [x] Implementar listener `submit` en `form-crear-opt`:
  - Capturar todos los `input[name="sel"]:checked`
  - Para cada checkbox marcado, leer `data-receta` del trigger de tooltip en su fila
  - Intentar `JSON.parse(raw)`, capturar excepción
  - Si `receta` no es array o `length === 0`, agregar a `sinReceta[]` con `{ idArticulo, codigoManual, descripcion }`
  - Si `sinReceta.length > 0`, llamar `ev.preventDefault()` y mostrar modal cliente con JS vanilla
- [x] Implementar función `mostrarModalSinRecetaCliente(items)`:
  - Construir DOM del modal con misma estructura que el modal servidor
  - Insertar en `document.body`
  - Añadir handler de cierre con `remove()`
- [x] **Nota:** Esta validación NO reemplaza la validación servidor; es defensa temprana
- **Mapeo requisito:** REQ-VPK-001 (prevenir round-trip innecesario si se detecta sin receta antes de POST)
- **Archivo:** `mpr/templates/mpr/ventana_pack.html`

---

## Fase 3: Tests (mpr/tests/test_ventana_pack_bloqueo_sin_receta.py)

### 3.1 Crear archivo de test
- [x] Crear archivo nuevo `mpr/tests/test_ventana_pack_bloqueo_sin_receta.py`
- [x] Importar `unittest.mock.patch`, `django.test.SimpleTestCase`, `django.test.RequestFactory`
- [x] Crear helpers de fixture y sesión para las clases de test
- **Archivo:** `mpr/tests/test_ventana_pack_bloqueo_sin_receta.py`

### 3.2 Test: Todos los packs con receta → continúa normal
- [x] Implementar `test_todos_con_receta_continua` ✅

### 3.3 Test: Un pack sin receta → bloquea y redirige a Pantalla 1
- [x] Implementar `test_uno_sin_receta_bloquea` ✅

### 3.4 Test: Selección mixta → bloquea y lista solo sin receta
- [x] Implementar `test_mixto_bloquea_y_lista_solo_sin_receta` ✅

### 3.5 Test: receta_json=None → tratado como sin receta
- [x] Implementar `test_receta_json_none_se_trata_como_sin_receta` ✅

### 3.6 Test: receta_json JSON inválido → tratado como sin receta
- [x] Implementar `test_receta_json_invalido_se_trata_como_sin_receta` ✅

### 3.7 Test: POST directo sin receta → bloqueado (no bypass)
- [x] Implementar `test_post_directo_sin_receta_bloqueado` ✅

### 3.8 Test: GET limpia sesión temporal
- [x] Implementar `test_get_limpia_sesion_sin_receta` ✅

### 3.9 Test: Modal se renderiza cuando hay packs sin receta
- [x] Implementar `test_modal_renderizado_cuando_hay_sin_receta` (vía contexto) ✅

### 3.10 Ejecutar tests en contenedor
- [x] Correr `docker exec Synap_app python manage.py test mpr.tests.test_ventana_pack_bloqueo_sin_receta`
- [x] Todos los tests pasan (16/16, exit code 0)
- **Resultado:** `Ran 16 tests in 0.016s — OK`

---

## Fase 4: Documentación

### 4.1 Actualizar documentación del flujo OPT/ventana-pack
- [x] Localizar `docs/mpr/MPR_FLUJO_CREAR_OPT.md` (doc existente del flujo)
- [x] Añadir sección `## 0. Validación de receta (BOM) antes de avanzar` con:
  - Criterio "sin receta" (`receta_json` vacío/inválido)
  - Flujo de bloqueo (modal en Pantalla 1 con listado de artículos sin BOM)
  - Restricciones: validación obligatoria en servidor, sesión temporal se consume en primer GET
- **Archivo:** `docs/mpr/MPR_FLUJO_CREAR_OPT.md`

---

## Resumen de mapeo de requisitos a tareas

| Requisito | Tareas que lo cubren |
|---|---|
| **REQ-VPK-001** — Validación de receta antes de continuar | 1.1, 1.2, 2.2, 2.3, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7 |
| **REQ-VPK-002** — Contenido del modal de bloqueo | 1.2 (estructura de datos), 2.1, 3.8, 3.9 |
| **REQ-VPK-003** — Acción correctiva del usuario | 1.3, 2.1 (botón cerrar), 3.8 |

---

## Archivos modificados/creados

| Archivo | Tipo de cambio | Tareas |
|---|---|---|
| `mpr/views.py` | Modificar | 1.1, 1.2, 1.3 |
| `mpr/templates/mpr/ventana_pack.html` | Modificar | 2.1, 2.2, 2.3 |
| `mpr/tests/test_ventana_pack_bloqueo_sin_receta.py` | Crear | 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9 |
| `docs/mpr/FLUJO_VENTANA_PACK_OPT.md` (o similar) | Crear/Modificar | 4.1 |

---

## Notas de implementación

- **Orden recomendado:** Backend (Fase 1) → Tests (Fase 3, parcial para Backend) → Frontend (Fase 2) → Tests completos (Fase 3) → Documentación (Fase 4)
- **Sesión de desarrollo:** Cada tarea de las fases 1 y 2 es completable en una sesión corta (~15-30 min). Los tests pueden agruparse en 2-3 sesiones.
- **Herramientas:** Ejecutar tests en contenedor con `docker exec Synap_app`; no correr tests fuera del contenedor (dependencias MySQL).
- **Edge cases cubiertos:** `receta_json` None/vacío/inválido, selección mixta, POST directo (bypass), sesión expirada (aceptable sin modal), preselección desde tablero (deuda técnica documentada).

---

## Metadata

- **Generado:** 2026-07-02
- **Generado por:** sdd-tasks subagent
- **Spec base:** `openspec/changes/opt-bloqueo-pack-sin-receta/specs/mpr-opt-creacion-ventana-pack/spec.md`
- **Diseño base:** `openspec/changes/opt-bloqueo-pack-sin-receta/design.md`
- **Próxima fase:** sdd-apply
