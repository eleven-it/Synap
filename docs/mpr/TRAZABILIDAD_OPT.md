# Trazabilidad OPT — MPR Etapa 6

## Resumen

La **Etapa 6** del pipeline MPR agrega trazabilidad drill-down para cada OPT (lista_produccion_agrupada). Permite ver el historial cronológico completo de eventos asociados a una orden de producción: liberación, partes producidos (OPP), ajustes, transiciones entre etapas, armados e imputaciones.

**Cambio**: `mpr-pipeline-etapa6-trazabilidad-opt`  
**Artefactos SDD**: Engram #1014 (proposal), #1015 (spec), #1016 (design), #1017 (tasks)

---

## Campo `id_lista_produccion` en `MprParte`

### Modelo

```python
# mpr/models.py → MprParte
id_lista_produccion = models.IntegerField(
    null=True, blank=True, db_index=True,
    help_text="ID de la OPT activa al momento de registrar el parte. Capturado best-effort para trazabilidad E6.",
)
```

### Captura automática

Al registrar un parte de producción con `registrar_parte_produccion`, se llama automáticamente a `_capturar_id_lista_opt_activa` para obtener el `id_lista_produccion` de la OPT activa (`en_proceso_produccion='Si'`):

- Si hay una OPT activa para los artículos del parte → persiste el id.
- Si hay múltiples activas → toma la de mayor id + emite `logger.warning`.
- Si no hay OPT activa o falla MySQL → persiste `None` (best-effort).
- No interrumpe la creación del parte ni el asiento físico.

### Migración

`mpr/migrations/0013_mprparte_id_lista_produccion.py` — `AddField` aditivo, nullable, sin defaults. Compatible con `SYNAP_MIGRATIONS_POSTGRES_ONLY=1`.

---

## Escritura a `lista_produccion_historico`

Después de cada asiento físico OPP-parte exitoso (en `_registrar_asiento_fisico_opp_parte`), se escribe un evento en `lista_produccion_historico`:

- `tipo_evento = 'OPP'`
- `id_lista_produccion = parte.id_lista_produccion`
- `id_articulo = id_art (pack)`
- `codigo_movimiento_mstock = codigo_mov`
- `id_operario = id_usuario`
- `fecha = fecha del movimiento`
- `hora_evento = hora actual`

**Fallback graceful**: la escritura está envuelta en `try/except` aislado. Si falla (tabla ausente, columna distinta, error MySQL), se loguea el warning y el asiento físico continúa normalmente. El commit de stock_deposito NO depende del historico.

Si `parte.id_lista_produccion is None` → se omite la escritura silenciosamente.

---

## Servicios de trazabilidad

### `construir_trazabilidad_opt(base_empresa, id_lista_produccion)`

Integra 6 fuentes de datos para construir el historial completo de una OPT:

| # | Fuente | Tipo de eventos | Modelo/Tabla |
|---|--------|-----------------|--------------|
| 1 | `lista_produccion_historico` | OPT, OPP, OPA | MySQL legacy |
| 2 | `movimiento_stock` (via `listar_opp_por_opt`) | OPP legacy | MySQL legacy |
| 3 | `MprParte` + `MprParteAjuste` | OPP, OPP-ajuste | PostgreSQL Django |
| 4 | `MprTransicionLote` | Transicion | PostgreSQL Django |
| 5 | `MprArmadoSurtidoMovimiento` | Armado | PostgreSQL Django |
| 6 | `MprImputacionArmado` | Imputacion | PostgreSQL Django |

**Retorno**:
```python
{
    "cabecera": {
        "id_lista": int,
        "id_articulo": int,
        "codigo_manual": str,
        "descripcion": str,
        "cantidad_pedida": int,
        "estado": "en_proceso" | "cerrada",
        "base_empresa": str,
    },
    "eventos": [
        {
            "tipo": str,          # OPT|OPP|OPP-ajuste|Transicion|Armado|Imputacion|sin_opt
            "fecha": str,         # dd/MM/yyyy
            "hora": str,          # HH:MM:SS
            "descripcion": str,
            "cantidad": float,
            "operario": str,
            "fuente": str,        # nombre de la fuente
            "codigo_movimiento": int | None,
            "id_lista_produccion": int | None,
        },
        ...
    ],
    "fuentes_fallidas": ["nombre_fuente", ...]
}
```

Cada fuente se integra con `try/except` independiente. Si una falla, se agrega a `fuentes_fallidas` y se continúa con las demás. Las fechas siempre se formatean como `dd/MM/yyyy`. Los eventos se ordenan cronológicamente por `(fecha, hora)`.

### `construir_trazabilidad_articulo(base_empresa, id_articulo, fecha_desde, fecha_hasta)`

Construye trazabilidad agregada para un artículo. Llama `listar_lista_produccion_agrupada` para obtener las OPTs del artículo y llama `construir_trazabilidad_opt` por cada una. Filtra por rango de fechas.

Los eventos sin `id_lista_produccion` se marcan con `fuente='sin_opt'` y `descripcion='sin OPT asociada'`.

---

## Vista `TrazabilidadOptView`

**URL**: `/mpr/opt/<id_lista>/trazabilidad/`  
**Nombre**: `mpr:opt_trazabilidad`  
**Clase**: `TrazabilidadOptView(MprLoginRequiredMixin, TemplateView)`

### Comportamiento

1. Extrae `base_empresa` de la sesión y `id_lista` de la URL.
2. Llama `construir_trazabilidad_opt(base_empresa, id_lista)`.
3. Si `cabecera` está vacía → `Http404` ("OPT no encontrada para esta empresa").
4. Si `cabecera.base_empresa` ≠ `base_empresa` de sesión → `Http404` (scoping de empresa).
5. Renderiza `mpr/trazabilidad_opt.html`.

### Contexto

```python
{
    "trazabilidad": {...},
    "cabecera": {...},
    "eventos": [...],
    "fuentes_fallidas": [...],
    "id_lista": int,
    "opt_detail_url": str,
    "tablero_url": str,
    "opt_list_url": str,
}
```

---

## Template `trazabilidad_opt.html`

- Extiende `base_mpr.html`.
- **Cabecera OPT**: código, descripción, cantidad pedida, estado (en progreso/cerrada).
- **Banner de advertencia**: si `fuentes_fallidas` no está vacío, muestra aviso amarillo con las fuentes que fallaron.
- **Timeline vertical**: `<ul>` con `<li>` por evento, usando Alpine.js para expandir detalles técnicos.
  - `OPT` → ícono azul (assignment)
  - `OPP` → ícono verde (factory)
  - `OPP-ajuste` → ícono ámbar (tune)
  - `Transicion` → ícono púrpura (swap_horiz)
  - `Armado` → ícono índigo (inventory_2)
  - `Imputacion` → ícono teal (link)
  - `sin_opt` / otros → ícono gris (info)
- Cada evento tiene un expandible Alpine.js con detalles técnicos (fuente, código de movimiento, id OPT).
- Fechas en formato `dd/MM/yyyy`.

---

## Enganches de navegación

### `opt_detail.html`

Botón "Ver trazabilidad" en el header de la OPT (junto a "Imprimir comprobante"):

```html
{% if id_lista %}
<a href="{% url 'mpr:opt_trazabilidad' id_lista=id_lista %}">Ver trazabilidad</a>
{% endif %}
```

### `tablero_produccion.html`

Botón "Trazabilidad" en la columna de Acciones por fila (solo visible si `fila.id_lista_produccion` está disponible):

```html
{% if fila.id_lista_produccion %}
<a href="{% url 'mpr:opt_trazabilidad' id_lista=fila.id_lista_produccion %}">Trazabilidad</a>
{% endif %}
```

> **Nota**: `listar_tablero_por_articulo` retorna datos al nivel de componente, sin `id_lista_produccion`. El botón aparece solo cuando se enriquezca el tablero con ese campo (tarea futura E6.5).

---

## Deprecación de `ejecutar_opp` / `RegistrarOppView`

Las funciones y vista legacy de OPP (`ejecutar_opp`, `ejecutar_opp_por_componentes`, `RegistrarOppView`) están marcadas como `DEPRECATED (E6)` con comentario en docstring. **No se eliminan** hasta migrar el wizard paso 3. Su comportamiento y firmas son intactos.

---

## Tests

**Archivo**: `mpr/tests/test_etapa6_trazabilidad.py`

| TestCase | Cobertura |
|----------|-----------|
| `TestIdListaPersistido` | id_lista persiste con OPT activa; null sin OPT; warning con múltiples OPTs; null si MySQL falla |
| `TestHistoricoOppParte` | INSERT llamado con id_lista presente; skip si id_lista None; graceful si tabla ausente; asiento físico no se rompe si historico falla |
| `TestConstruirTrazabilidadOpt` | cabecera correcta; eventos de MprParte integrados; orden cronológico; fuentes_fallidas sin 500; cabecera vacía → {} |
| `TestEventosHuerfanos` | id_lista=None → fuente='sin_opt'; lista vacía sin error |
| `TestTrazabilidadOptView` | GET 200 con contexto; 404 si cabecera vacía; 404 si empresa distinta; redirige sin sesión |

**Comando**:
```bash
docker exec Synap_app python manage.py test mpr.tests.test_etapa6_trazabilidad --keepdb --noinput
```

---

## Fuera de alcance (E6.5 en adelante)

- `id_lista_produccion` en `MprTransicionLote` (para correlación directa transición↔OPT).
- Eliminación efectiva de `ejecutar_opp` / `RegistrarOppView`.
- Reescritura del wizard paso 3.
- Enriquecimiento de filas del tablero con `id_lista_produccion`.
