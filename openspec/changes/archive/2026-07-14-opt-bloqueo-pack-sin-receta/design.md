# Diseño Técnico: Bloqueo de packs sin receta en ventana pack OPT

**Change:** `opt-bloqueo-pack-sin-receta`  
**Artifact Type:** design  
**Estado:** draft  
**Autor:** sdd-design subagent  
**Fecha:** 2026-07-02

---

## 1. Contexto y alcance

El flujo de creación de OPT (Orden de Producción de Trabajo) tiene dos pantallas:

| Pantalla | Vista Django | URL |
|---|---|---|
| Pantalla 1 — Selección de packs | `VentanaPackView` | `/mpr/demanda/ventana-pack/` |
| Pantalla 2 — Agrupar / Generar OPT | `VentanaPackAgruparView` | `/mpr/demanda/ventana-pack/agrupar/` |

El campo `receta_json` en cada fila de `listar_ventana_pack()` es un JSON string:
- **Con receta**: lista con al menos un objeto componente, ej. `[{"articulo": "...", "cantidad": 2}]`
- **Sin receta**: lista vacía `[]` o ausente/`None`

El objetivo es bloquear el avance a Pantalla 2 si alguno de los packs seleccionados por el usuario tiene `receta_json == []` (o no presente/inválido).

---

## 2. Decisiones de arquitectura

### 2.1 Dónde vive la validación: servidor (autoritativa)

**Decisión:** La validación se inserta en `VentanaPackAgruparView.post`, en la rama que procesa la selección proveniente de Pantalla 1 (después de construir el `lookup` de filas con `receta_json`), antes de guardar `ventana_pack_seleccion` en sesión.

**Rationale:**  
- El `lookup` ya tiene la `receta_json` fresca de la BD, sin depender de nada que el cliente haya enviado.  
- Un POST directo (bypass de JS) a `/mpr/demanda/ventana-pack/agrupar/` también pasa por esta rama, por lo que la validación no puede evitarse desde el cliente.  
- Evita duplicar la llamada a `listar_ventana_pack` (ya se hace en esa rama).

**Alternativa descartada — validar en `VentanaPackView.post` (no existe):** `VentanaPackView` solo tiene `get`; el POST va directamente a `VentanaPackAgruparView`.

**Alternativa descartada — validar solo en cliente (JS):** Insuficiente; no protege contra bypass por POST directo.

---

### 2.2 Helper `tiene_receta(fila)`

Se define un helper privado en `mpr/views.py` (no en `services.py`, ya que es lógica de vista/negocio de guardia, no de consulta de datos):

```python
import json as _json

def _tiene_receta(fila: dict) -> bool:
    """Devuelve True si la fila de pack tiene BOM (receta_json es lista no vacía)."""
    raw = fila.get("receta_json")
    if not raw:
        return False
    try:
        receta = _json.loads(raw)
    except (ValueError, TypeError):
        return False
    return isinstance(receta, list) and len(receta) > 0
```

---

### 2.3 Comunicación del resultado de validación a Pantalla 1

**Decisión:** Sesión temporal con clave `"ventana_pack_sin_receta"`.

El flujo es:
1. En `VentanaPackAgruparView.post`, si hay packs sin receta, guardar en sesión:
   ```python
   request.session["ventana_pack_sin_receta"] = [
       {
           "id_articulo": f["id_articulo"],
           "codigo_manual": f.get("codigo_manual", "-"),
           "descripcion_articulo": f.get("descripcion_articulo", "-"),
       }
       for f in filas_sin_receta
   ]
   ```
2. Redirigir a `mpr:ventana_pack` (GET), **sin** guardar `ventana_pack_seleccion`.
3. En `VentanaPackView.get_context_data`, leer y limpiar:
   ```python
   packs_sin_receta = self.request.session.pop("ventana_pack_sin_receta", None)
   context["packs_sin_receta"] = packs_sin_receta or []
   ```
4. El template renderiza el modal si `packs_sin_receta` no está vacío.

**Alternativa descartada — Django messages con datos estructurados:** `messages` no admite fácilmente listas de dicts estructurados; hay que serializar/deserializar manualmente. Más frágil que un key de sesión dedicado.

**Alternativa descartada — querystring con IDs:** Expone IDs en la URL, no lleva descripción ni código manual, y requiere una nueva query en `get_context_data` para reconstruir los datos de cada artículo. Más complejo y menos seguro.

**Alternativa descartada — renderizar Pantalla 1 directamente desde el POST de Pantalla 2 (sin redirect):** Rompe el patrón PRG (Post-Redirect-Get) que ya usa toda la vista; el navegador mostraría diálogo de "reenviar formulario" al refrescar.

---

### 2.4 Formato del ítem sin receta (estructura de datos)

Cada elemento de `packs_sin_receta` en sesión y en contexto:

```python
{
    "id_articulo":        int,   # clave primaria del artículo
    "codigo_manual":      str,   # código legible del pack (ej. "PKG-001")
    "descripcion_articulo": str, # nombre del pack (ej. "Pack Promocional Verano")
}
```

No se incluye `codigo_articulo` (código de sistema de AdministraNET): el campo se llama `codigo_articulo` en el lookup, pero puede ser el mismo que `id_articulo` o diferir. Para el modal se muestra `id_articulo` como "Cód. Sistema" y `codigo_manual` como "Cód. Manual".

> **Revisión de naming:** si el equipo prefiere mostrar `codigo_articulo` (varchar del ABM) en lugar de `id_articulo` (int PK), bastará agregar `"codigo_articulo": f.get("codigo_articulo", "-")` al dict. El diseño lo admite sin cambio estructural.

---

### 2.5 Modal de bloqueo en el template

**Patrón UI elegido:** mismo patrón que `mpr_schema_error_modal` en `base_mpr.html` (modal con overlay fijo, Tailwind, cierre con JS vanilla).

- El modal se renderiza condicionalmente con `{% if packs_sin_receta %}` directamente en `ventana_pack.html` (no en `base_mpr.html`), porque es específico de esta vista.  
- Se auto-muestra por su presencia en el DOM (no requiere JS adicional para abrirlo).  
- Un botón "Cerrar" elimina el modal del DOM con `onclick="document.getElementById('modal-sin-receta').remove()"`.  
- El usuario queda en Pantalla 1 con la tabla intacta y puede modificar la selección.

**Estructura del modal:**

```html
{% if packs_sin_receta %}
<div class="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm"
     id="modal-sin-receta" role="dialog" aria-modal="true" aria-labelledby="modal-sin-receta-titulo">
    <div class="w-full max-w-lg rounded-2xl border border-amber-200/90 bg-white p-6 shadow-2xl
                dark:border-amber-800/50 dark:bg-slate-800 sm:p-7">
        <div class="flex items-start gap-4">
            <span class="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-full
                         bg-amber-100 dark:bg-amber-900/40" aria-hidden="true">
                <span class="material-icons text-2xl text-amber-600 dark:text-amber-400">warning_amber</span>
            </span>
            <div class="min-w-0 flex-1">
                <h2 id="modal-sin-receta-titulo"
                    class="mb-1 text-lg font-bold tracking-tight text-slate-900 dark:text-white">
                    Pack(s) sin receta definida
                </h2>
                <p class="mb-4 text-sm text-slate-600 dark:text-slate-300">
                    Los siguientes artículos no tienen receta (BOM) cargada y no pueden incluirse
                    en una OPT. Cargue la receta en el módulo correspondiente antes de continuar.
                </p>
                <div class="overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-600">
                    <table class="min-w-full divide-y divide-slate-200 text-xs dark:divide-slate-600">
                        <thead class="bg-slate-50 dark:bg-slate-700">
                            <tr>
                                <th class="px-3 py-2 text-left font-semibold text-slate-500 dark:text-slate-300">
                                    Cód. Sistema
                                </th>
                                <th class="px-3 py-2 text-left font-semibold text-slate-500 dark:text-slate-300">
                                    Cód. Manual
                                </th>
                                <th class="px-3 py-2 text-left font-semibold text-slate-500 dark:text-slate-300">
                                    Descripción
                                </th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-slate-100 bg-white dark:divide-slate-700 dark:bg-slate-800">
                            {% for p in packs_sin_receta %}
                            <tr>
                                <td class="px-3 py-2 font-mono text-slate-700 dark:text-slate-200">
                                    {{ p.id_articulo }}
                                </td>
                                <td class="px-3 py-2 text-slate-700 dark:text-slate-200">
                                    {{ p.codigo_manual|default:"-" }}
                                </td>
                                <td class="px-3 py-2 text-slate-700 dark:text-slate-200">
                                    {{ p.descripcion_articulo|default:"-" }}
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
                <div class="mt-6 flex justify-end border-t border-slate-100 pt-5 dark:border-slate-700">
                    <button type="button"
                            onclick="document.getElementById('modal-sin-receta').remove();"
                            class="inline-flex min-h-10 items-center justify-center rounded-xl
                                   bg-slate-200 px-4 py-2 text-sm font-medium text-slate-800
                                   transition-colors hover:bg-slate-300 focus:outline-none
                                   focus-visible:ring-2 focus-visible:ring-slate-400 focus-visible:ring-offset-2
                                   dark:bg-slate-600 dark:text-slate-200 dark:hover:bg-slate-500
                                   dark:focus-visible:ring-offset-slate-800">
                        Cerrar
                    </button>
                </div>
            </div>
        </div>
    </div>
</div>
{% endif %}
```

---

### 2.6 Validación en cliente (defensa temprana, opcional pero recomendada)

El template ya tiene `data-receta="{{ f.receta_json|default:'[]'|escape }}"` en cada fila. Se puede agregar un interceptor en el botón "Continuar" que, antes de enviar el formulario, verifique que todos los checkboxes `sel` marcados corresponden a filas con `receta_json` no vacío.

- Si detecta algún pack sin receta, **previene el envío** y muestra el modal directamente en cliente (construido con JS vanilla, igual que el tooltip de receta ya existente).
- Esto **no reemplaza** la validación de servidor; es una mejora de UX que reduce round-trips innecesarios.
- La implementación JS se agrega al bloque de scripts al final del template, dentro del IIFE existente o en un nuevo IIFE.

**Diseño del interceptor JS:**

```javascript
(function () {
    var form = document.getElementById('form-crear-opt');
    if (!form) return;
    form.addEventListener('submit', function (ev) {
        var seleccionados = Array.from(
            form.querySelectorAll('input[name="sel"]:checked')
        );
        if (!seleccionados.length) return; // la validación de cantidad la maneja el servidor

        var sinReceta = [];
        seleccionados.forEach(function (chk) {
            var row = chk.closest('tr');
            if (!row) return;
            var trigger = row.querySelector('.receta-tooltip-trigger');
            if (!trigger) return;
            var raw = trigger.getAttribute('data-receta');
            var receta = [];
            try { if (raw) receta = JSON.parse(raw); } catch (e) {}
            if (!Array.isArray(receta) || receta.length === 0) {
                sinReceta.push({
                    idArticulo: chk.value,
                    codigoManual: row.dataset.codigoManual || '-',
                    descripcion: row.dataset.descripcion || '-',
                });
            }
        });

        if (sinReceta.length > 0) {
            ev.preventDefault();
            // Mostrar modal de error en cliente (misma estructura que el modal servidor)
            mostrarModalSinRecetaCliente(sinReceta);
        }
    });

    function mostrarModalSinRecetaCliente(items) { /* construye y muestra modal dinámico */ }
})();
```

Para que el JS de cliente pueda leer código manual y descripción de la fila, se agregan atributos `data-codigo-manual` y `data-descripcion` al elemento `<tr>` de cada pack en la tabla.

---

## 3. Diagrama de secuencia — POST "Continuar" con la nueva validación

```
Usuario          ventana_pack.html     VentanaPackAgruparView.post     Sesión Django
   |                    |                          |                        |
   |-- [Pulsa Continuar]→                          |                        |
   |  [JS intercepta]   |                          |                        |
   |  ¿sin receta?      |                          |                        |
   |  SÍ → modal cliente (previene POST)           |                        |
   |  NO → POST form ──────────────────────────────→                        |
   |                    |              sel=[], cant_* en request.POST        |
   |                    |                          |                        |
   |                    |              listar_ventana_pack() → lookup        |
   |                    |              construir filas_sesion (qty > 0)      |
   |                    |              _tiene_receta() por cada fila         |
   |                    |              ¿hay sin_receta?                      |
   |                    |              SÍ ─────────────────────────────────→ session["ventana_pack_sin_receta"]
   |                    |              redirect → mpr:ventana_pack           |
   |                    |                          |                        |
   |←── GET /demanda/ventana-pack/ ────────────────|                        |
   |    VentanaPackView.get_context_data()          |                        |
   |    packs_sin_receta = session.pop(...)         |←──────────────────────|
   |    context["packs_sin_receta"] = [...]         |                        |
   |    render ventana_pack.html                    |                        |
   |    {% if packs_sin_receta %} → modal DOM       |                        |
   |    [modal visible automáticamente]             |                        |
   |                    |                          |                        |
   |                    |              NO (todos tienen receta)              |
   |                    |              session["ventana_pack_seleccion"] = {filas}
   |                    |              redirect → mpr:ventana_pack_agrupar  |
   |←── GET /demanda/ventana-pack/agrupar/ (Pantalla 2)                     |
```

---

## 4. Cambios por archivo

| Archivo | Tipo de cambio | Descripción |
|---|---|---|
| `mpr/views.py` | Modificar | Agregar helper `_tiene_receta(fila)`. En `VentanaPackAgruparView.post` (rama Pantalla 1): tras construir `filas_sesion`, filtrar sin receta; si hay ≥1, guardar en sesión `ventana_pack_sin_receta` y hacer redirect a `mpr:ventana_pack`. En `VentanaPackView.get_context_data`: leer y limpiar `session.pop("ventana_pack_sin_receta", None)` y pasar al contexto. |
| `mpr/templates/mpr/ventana_pack.html` | Modificar | Agregar modal `{% if packs_sin_receta %}` al final del template (antes de `{% endblock %}`). Agregar atributos `data-codigo-manual` y `data-descripcion` en el `<tr>` de cada fila de la tabla de packs (para el JS cliente). Agregar IIFE de interceptor JS del botón Continuar. |
| `mpr/services.py` | Sin cambios | `listar_ventana_pack` ya genera `receta_json` correctamente; no se modifica. |
| `mpr/urls.py` | Sin cambios | Las URLs existentes son suficientes. |
| `mpr/tests/test_ventana_pack_bloqueo_sin_receta.py` | Crear | Tests unitarios nuevos (ver §5). |

---

## 5. Localización exacta de los cambios en `mpr/views.py`

### 5.1 Helper (añadir cerca de otras funciones privadas de la vista, por encima de `VentanaPackAgruparView`)

```python
import json as _json_receta  # si json ya está importado en el módulo, usar el existente

def _tiene_receta(fila: dict) -> bool:
    """True si el pack tiene BOM (receta_json decodifica a lista no vacía)."""
    raw = fila.get("receta_json")
    if not raw:
        return False
    try:
        receta = json.loads(raw)
    except (ValueError, TypeError):
        return False
    return isinstance(receta, list) and len(receta) > 0
```

### 5.2 En `VentanaPackAgruparView.post` — insertar tras el bloque que construye `filas_sesion`

Ubicación actual (líneas ~4106-4110 en `mpr/views.py`):

```python
# ACTUAL (líneas ~4106-4110):
if not filas_sesion:
    messages.error(request, "Seleccione al menos un artículo con cantidad a fabricar mayor a 0.")
    return redirect("mpr:ventana_pack")
request.session["ventana_pack_seleccion"] = {"filas": filas_sesion}
return redirect("mpr:ventana_pack_agrupar")
```

Reemplazar por:

```python
if not filas_sesion:
    messages.error(request, "Seleccione al menos un artículo con cantidad a fabricar mayor a 0.")
    return redirect("mpr:ventana_pack")

# Validación de receta: bloquear si algún pack seleccionado no tiene BOM
packs_sin_receta = [
    {
        "id_articulo": f["id_articulo"],
        "codigo_manual": f.get("codigo_manual", "-"),
        "descripcion_articulo": f.get("descripcion_articulo", "-"),
    }
    for f in (lookup.get(fila["id_articulo"]) or {} for fila in filas_sesion)
    if f and not _tiene_receta(f)
]
if packs_sin_receta:
    request.session["ventana_pack_sin_receta"] = packs_sin_receta
    request.session.modified = True
    return redirect("mpr:ventana_pack")

request.session["ventana_pack_seleccion"] = {"filas": filas_sesion}
return redirect("mpr:ventana_pack_agrupar")
```

> **Nota de implementación:** La list comprehension itera `filas_sesion` (que ya tiene qty > 0) y recupera la fila del `lookup` usando `id_articulo`; si por algún motivo no está en el lookup, se descarta con `if f`. El helper `_tiene_receta` cubre el caso `receta_json=None`, `receta_json=""`, JSON inválido, y lista vacía.

### 5.3 En `VentanaPackView.get_context_data` — leer y limpiar la sesión temporal

Añadir al comienzo de `get_context_data`, antes de poblar `context["filas"]`:

```python
# Leer y limpiar packs sin receta comunicados desde VentanaPackAgruparView
packs_sin_receta = self.request.session.pop("ventana_pack_sin_receta", None)
context["packs_sin_receta"] = packs_sin_receta or []
```

---

## 6. Edge cases y su tratamiento

| Edge case | Tratamiento |
|---|---|
| `receta_json` es `None` o ausente en el dict | `_tiene_receta` devuelve `False` → pack bloqueado |
| `receta_json` es string vacío `""` | `_tiene_receta` devuelve `False` → pack bloqueado |
| `receta_json` es JSON inválido (malformado) | `except (ValueError, TypeError)` → `False` → pack bloqueado (conservador) |
| `receta_json` es `"[]"` (lista vacía serializada) | `len(receta) == 0` → `False` → pack bloqueado |
| Selección vacía o todas con qty=0 | Cubierto por validación preexistente (redirige con `messages.error` antes de llegar a la validación de receta) |
| Todos los packs tienen receta | `packs_sin_receta = []` → continúa normal a Pantalla 2 |
| Pack en `filas_sesion` no encontrado en `lookup` | `lookup.get(id)` devuelve `None`; se descarta con `if f` (no bloquea) |
| Preselección desde `?articulo=` (tablero) | `VentanaPackView.get` redirige a Pantalla 2 sin pasar por `VentanaPackAgruparView.post`; esa rama no valida receta. **Riesgo menor:** el artículo desde tablero debería tener receta (si está en demanda activa). Documentar como deuda técnica si se quiere cubrir. |
| Flujo wizard (sesión `WIZARD_SESSION_KEY`) | La validación de receta no interactúa con el wizard; si el pack está bloqueado, se redirige a Pantalla 1 y el wizard sigue en paso 1 (correcto). |
| POST directo a `ventana_pack_agrupar` con pack sin receta (bypass JS) | Cubierto: la validación está en el servidor; el redirect vuelve a Pantalla 1 con el modal. |
| Sesión expirada entre el POST y el GET de vuelta | Si la sesión expiró, `session.pop("ventana_pack_sin_receta", None)` devuelve `None`; el modal no aparece, pero tampoco se avanzó a Pantalla 2. Comportamiento aceptable. |

---

## 7. Estrategia de tests

**Archivo nuevo:** `mpr/tests/test_ventana_pack_bloqueo_sin_receta.py`  
**Ejecución:** `docker exec Synap_app python manage.py test mpr.tests.test_ventana_pack_bloqueo_sin_receta`

### Escenarios a cubrir

| Test | Descripción | Assert esperado |
|---|---|---|
| `test_todos_con_receta_continua` | POST a `ventana_pack_agrupar` con 3 packs que tienen receta, qty > 0. Mock de `listar_ventana_pack` retorna filas con `receta_json='[{"articulo":"X","cantidad":1}]'`. | Response 302 a `ventana_pack_agrupar`; `session["ventana_pack_seleccion"]` contiene 3 filas; `"ventana_pack_sin_receta"` no está en sesión. |
| `test_uno_sin_receta_bloquea` | POST con 1 pack sin receta (`receta_json='[]'`). | Response 302 a `ventana_pack`; `"ventana_pack_seleccion"` no está en sesión; `session["ventana_pack_sin_receta"]` contiene 1 item con `id_articulo` correcto. |
| `test_mixto_bloquea_y_lista_solo_sin_receta` | POST con 4 packs: 3 con receta, 1 sin receta. | Response 302 a `ventana_pack`; `session["ventana_pack_sin_receta"]` tiene exactamente 1 item (el sin receta); los 3 con receta no aparecen. |
| `test_receta_json_none_se_trata_como_sin_receta` | `receta_json=None` en la fila del pack. | Response 302 a `ventana_pack`; `session["ventana_pack_sin_receta"]` tiene ese pack. |
| `test_receta_json_invalido_se_trata_como_sin_receta` | `receta_json='INVALID_JSON'` en la fila. | Igual: bloquea y lo incluye en `ventana_pack_sin_receta`. |
| `test_post_directo_sin_receta_bloqueado` | POST directo a `ventana_pack_agrupar` sin haber pasado por Pantalla 1 (simulando bypass), con pack sin receta en lookup. | Response 302 a `ventana_pack`; `session["ventana_pack_seleccion"]` no se guarda. |
| `test_get_ventana_pack_limpia_sesion_sin_receta` | Sesión tiene `ventana_pack_sin_receta = [...]`. GET a `ventana_pack`. | `packs_sin_receta` en contexto tiene los ítems; `"ventana_pack_sin_receta"` ya no existe en sesión. |
| `test_modal_renderizado_cuando_hay_sin_receta` | GET a `ventana_pack` con contexto `packs_sin_receta` poblado. | HTML de respuesta contiene `id="modal-sin-receta"` y el `id_articulo` del pack bloqueado. |

**Estrategia de mock:**  
Usar `unittest.mock.patch("mpr.views.listar_ventana_pack", return_value=[...])` para evitar conexiones a MySQL legacy en los tests.

---

## 8. Riesgos y decisiones abiertas

| Riesgo | Probabilidad | Mitigación |
|---|---|---|
| Preselección desde tablero (`?articulo=`) no valida receta | Baja (artículos en demanda urgente suelen tener BOM) | Documentar como deuda técnica; cubrir en issue separado si se reporta |
| La clave `receta_json` puede cambiar de nombre en `listar_ventana_pack` | Baja (campo estable) | El helper `_tiene_receta` centraliza el acceso; si cambia, solo se edita ahí |
| Modal no se muestra si el usuario llega a Pantalla 1 con sesión expirada | Muy baja | El usuario ve la tabla normal y puede volver a intentar; sin pérdida de datos |
| Validación JS de cliente no cubre todos los browsers | Baja (JS vanilla, no framework) | La validación de servidor es la autoritativa; el JS es mejora de UX opcional |
| Performance: `listar_ventana_pack` se llama dos veces en el flujo de error (una en POST de agrupar, otra en GET de ventana_pack) | Media | Aceptable: la segunda llamada ya ocurría antes de este cambio. No se agrega overhead neto |

---

## 9. Archivos de test existentes (referencia)

No existen tests previos para ventana_pack (`mpr/tests/test_ventana_pack*.py` → 0 archivos). El archivo de test nuevo `test_ventana_pack_bloqueo_sin_receta.py` será el primero para este flujo.

---

## Metadata

- **Author role:** sdd-design subagent  
- **Created:** 2026-07-02  
- **Status:** draft  
- **Spec cubierta:** `openspec/changes/opt-bloqueo-pack-sin-receta/specs/mpr-opt-creacion-ventana-pack/spec.md`  
- **Next phase:** sdd-tasks
