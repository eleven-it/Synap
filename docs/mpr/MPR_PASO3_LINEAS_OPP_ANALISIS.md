# Análisis: líneas de artículos en paso 3 del wizard (Crear OPP)

## Dónde se muestran las líneas

- **Template:** `mpr/templates/mpr/wizard.html` (bloque `{% if wizard_paso == 3 %}`).
- **Variable de contexto:** `lineas` — lista de dicts con `id_articulo`, `codigo_articulo`, `descripcion_articulo`, `cantidad_pendiente_prod`, etc.
- Si `lineas` está vacía, la plantilla muestra: *"No hay líneas para esta OPT."*

## Cómo se obtienen las líneas (orden actual)

En `WizardProduccionView.get_context_data` cuando `paso == 3`:

1. **`id_lista`** = `wizard.get("id_lista")` (sesión del asistente).
2. **`lineas`** se rellena en este orden:
   - `get_opt_detalle(base_empresa, id_lista)` — líneas por `id_opt` o una sola por `id_lista_produccion`.
   - Si viene vacío: `get_op_detalle(base_empresa, id_lista)` — una o más filas por `id_lista_produccion` desde `lista_produccion_agrupada` (+ articulo).
   - Si sigue vacío: `get_lineas_opt_directo(base_empresa, id_lista)` — consulta directa a `lista_produccion_agrupada` por `id_lista_produccion` o `id_opt`.

Si las tres devuelven `[]`, la tabla no tiene filas.

## De dónde sale `id_lista` en el paso 3

- **Flujo asistente (paso 2 → 3):** Tras confirmar/liberar OPT, se hace `wizard["id_lista"] = id_lista` y `redirect("mpr:wizard")`. El paso 3 lee `id_lista` solo de la **sesión**.
- **Flujo ventana pack (Crear OPT → wizard):** Tras crear la OPT en agrupar, se hace `request.session[WIZARD_SESSION_KEY] = { "paso": 3, "id_lista": id_lista_principal, ... }` y `redirect("mpr:wizard")`. No se pasa `id_lista` en la URL; se depende solo de la sesión.
- **Desde detalle OPT:** El enlace "Registrar OPP" lleva a `wizard?paso=3&id_lista=<id>`. En el GET se hace `wizard["id_lista"] = id_lista` desde la URL.

Riesgo: si la sesión no se persiste o se pierde (otro navegador, cookie, worker distinto), en el flujo ventana pack el paso 3 puede no tener `id_lista` y entonces `lineas` queda vacío.

## Por qué las tres funciones pueden devolver []

1. **`base_empresa` distinta:** Si la sesión tiene otra empresa que la base donde se creó la OPT, las consultas se hacen a otra BD y no hay filas.
2. **Nombres de columnas en MySQL:** Si la tabla tiene columnas en otro casing (p. ej. `IdListaProduccion`, `ID_OPT`), `row.get("id_opt")` o `r.get("id_lista_produccion")` pueden ser `None` y la lógica que usa `id_opt` no se ejecuta; si además falla el SELECT por nombre de columna, también se puede acabar con 0 filas.
3. **Conexión a otra base:** El pool reutiliza conexiones; si no se hace `select_db(database)` al reutilizar (ya corregido), se podría leer de otra base.
4. **Sesión sin `id_lista`:** Si no se guardó o se perdió la sesión tras el redirect, `id_lista` es `None` y no se llama a los servicios con un id válido.

## Cambios aplicados (resumen)

- Redirigir al wizard con **`?paso=3&id_lista=<id>`** tras crear y liberar la OPT desde ventana pack, para no depender solo de la sesión.
- En **`get_opt_detalle`**, normalizar a minúsculas las claves del `row` (y de los `r` de `fetchall()`) al leer `id_opt` e `id_lista_produccion`, para ser tolerante al casing de MySQL.
- Mantener el fallback **`get_lineas_opt_directo`** (ya normaliza claves) como última opción.

## Comprobaciones si sigue sin verse la tabla

1. En la petición GET a `/mpr/wizard/` (paso 3), comprobar en logs o debug que `id_lista` llega (sesión o URL) y que `base_empresa` es la correcta.
2. En MySQL, en la base de `base_empresa`, verificar que existen filas en `lista_produccion_agrupada` con `id_lista_produccion = <id_lista>` o `id_opt = <id_lista>`.
3. Revisar si hay excepciones o warnings en logs al llamar a `get_opt_detalle`, `get_op_detalle` o `get_lineas_opt_directo`.
