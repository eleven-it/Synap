# Tablero de Demanda Consolidado por Artículo — MPR Etapa 2

**Fecha:** 2026-07-02 (actualizado 04/07/2026 — desacople OPT/OPP del flujo diario)  
**Change:** `mpr-pipeline-etapa2-tablero-consolidado`  
**Artefactos SDD:** Proposal #969, Spec #970, Design #971, Tasks #973  

> **Actualización Etapa 10 (03/07/2026):** se **elimina la columna «Planchado»**.
> El planchado deja de ser una etapa con stock (es un momento dentro de la producción y
> nunca deja saldo). El tablero pasa a **9 columnas de pipeline**. La clasificación sale
> directo de Producción hacia {Semi | 2da | Descarte} vía la pantalla única
> «Clasificación de producción» (ver `ACCIONES_LOTE_TABLERO.md`). Las referencias abajo a
> **Actualización Etapa 11 (04/07/2026):** el tablero consolidado es la **entrada principal**
> del módulo MPR (menú, URL del módulo y barra rápida). Ventana pack y asistente wizard quedan
> **Menú (04/07/2026):** solo flujo MPR diario; sin sección OPT legacy. Ver `NAVIGACION_MPR_ETAPA11.md`.


---

## Propósito

El **Tablero de producción** es una vista viva de solo lectura que consolida la demanda del pipeline MPR a nivel de artículo/componente. Explota la demanda de packs terminados (desde pedidos PED en vivo) mediante BOM al nivel de insumo/componente.

> **Desacople OPT/OPP (04/07/2026):** el tablero **no** lee `lista_produccion_*`, OPT liberadas ni OPP-parte. La columna **Fabricando** proviene únicamente de envíos directos (`mpr_envio_produccion`). Las tablas OPT legacy fueron eliminables vía `drop_mpr_lista_produccion_legacy`; el menú ya no expone ventana pack, wizard ni listado OPT.

A diferencia del Tablero de KPIs (`mpr/`), el Tablero de producción es una herramienta operativa de fábrica: muestra cuánto hay de cada componente en cada etapa del proceso, cuánto falta producir y cuánto ya fue enviado.

---

## Acceso

- **URL:** `mpr/tablero-produccion/`
- **Enlace desde Tablero de KPIs:** botón "Tablero de producción →" en el encabezado
- **Permisos:** requiere sesión MPR (mismo mixin que el resto del módulo)

---

## Columnas del tablero (alineación PCP — 07/07/2026)

| # | Columna | Tipo | Descripción |
|---|---------|------|-------------|
| 1 | **Artículo** | metadato | Código manual + descripción. Sticky-left. |
| 2 | **Pedido** | `dem_ped` | Pares (entero) |
| 3 | **Reserva** | `dem_res` | Pares (entero); explosión BOM reserva pack |
| 4 | **Resta total** | `resta_total` | Pares + Docenas (÷12, decimal PCP) |
| 5 | **Resta urgente** | `resta_urgente` | Pares + Docenas; base del **Enviar** |
| 6 | **Fabricando** | virtual | `max(0, Σ envíos − acreditado)`. Acreditado = `max(stock físico, clasificado CC, partes acumulados)`. |
| 7–10 | **Etapas stock** | físico | Producido, 2da, Semi, Desperdicio (no suma). **Sin Terminado** (componentes). |
| 11 | **Total** | derivado | Suma etapas sin Desperdicio ni Terminado. |
| 12 | **Enviar** | acción | Inputs docenas/pares; tope = `a_enviar`. |

`stock_proceso` = total sin Terminado (paridad PCP col G).

```
resta_urgente = MAX(0, dem_ped − stock_proceso)      # PCP col L — sin envíos ledger
resta_total   = MAX(0, demanda − stock_proceso)      # PCP col H — demanda = dem_ped + dem_res
fabricando    = MAX(0, Σ envíos_tablero − acreditado)   # acreditado ver REPORTES_MPR.md
a_enviar      = si Fabricando>0: MAX(0, MIN(urgente − Σ envíos, resta_total));
                si Fabricando=0 y urgente>0: MIN(urgente, resta_total)  # reabre
```

**Importante (24/07/2026, ajustado):** con **Fabricando > 0**, `a_enviar` descuenta
**envíos ledger** (`max(0, resta_urgente − Σ envíos)`), no el Fabricando en sí, para no
doble-contar el stock de proceso ya restado en la brecha PCP. Si **Fabricando = 0** y el
recálculo deja **Resta urgente > 0**, el tope **se reabre** a esa Resta urgente (ciclo
anterior acreditado; el hueco urgente es demanda nueva). El tope no puede superar
`resta_total`. En UI modo docenas el input se deshabilita si `a_enviar_docenas_pcp = 0`
(pares sueltos sin docena entera).

La columna **Resta urgente** sigue mostrando la brecha PCP; **Enviar** usa `a_enviar` para precargar, deshabilitar inputs y validar el POST (hidden `pendiente_*` / `resta_urgente_*`).

Filtro por defecto: **Solo urgentes** (`resta_urgente > 0`). Diseño UX: `docs/mpr/DISENO_TABLERO_PRODUCCION_REFACTOR_PCP.md`.

---

## Columnas legacy (referencia histórica)

| # | Columna | Notas |
|---|---------|-------|
| — | **Pendiente** | Alias de `resta_total` en servicio/reportes. |

---

## Algoritmo del Servicio `listar_tablero_por_articulo()`

```
Paso 1:  listar_demanda_pack_desde_pedidos(base, limit*2, fecha_desde, fecha_hasta)
         → filas_pack (demanda en vivo desde stockp + comp_ped PED)

Paso 2:  _query_enviados_todos_componentes(base)
         → componentes con envío directo al tablero (sin demanda pack)

Paso 3:  Explosión BOM: dem_ped, dem_res desde filas_pack

Paso 4:  comp_ids = demanda ∪ envíos directos

Paso 5:  Enviado (Fabricando) = _fabricando_por_componentes()
         acreditado = max(stock físico, clasificado CC, partes acumulados)
         Ver fórmula en § Columnas del tablero y ENVIO_PRODUCCION_TABLERO.md

Paso 6:  stock_pivot, desc_map, construir filas, ordenar por pendiente
```

La demanda **no** depende de «Actualizar demanda» ni de `lista_produccion_*`. El botón **Actualizar vista** solo refresca el timestamp de sesión.

### Invariantes de diseño

- `enviado` (Fabricando) y `produccion` (Producido) son **independientes**: Fabricando viene de `mpr_envio_produccion`; Producido de `stock_deposito`.
- `desperdicio` (**Scrap**) **no se incluye en `total`**. Está separado visualmente.
- `pendiente` nunca es negativo (`max(0, ...)`).

---

## Columna Enviado — Fórmula Definitiva (Etapa 4)

Desde **Etapa 4**, la columna **Enviado a producción** usa la fórmula definitiva:

```
Enviado_virtual(pack) = max(0, OPT_liberado_acumulado(pack) − OPP_parte_acumulado(pack))

enviado_comp[id_comp] = Σ (Enviado_virtual[id_pack] × coef_bom[id_comp])
```

donde:
- `OPT_liberado_acumulado(pack)` = `SUM(cantidad_asignada_opt)` de `lista_produccion_agrupada` WHERE `codigo_movimiento_opt > 0`.
- `OPP_parte_acumulado(pack)` = `SUM(MprParteLinea.cantidad + MprParteAjuste.delta)` — ledger Django.

### Backward-safe

Si no hay partes registrados (`OPP_parte_acumulado = 0`), `Enviado = OPT_liberado_acumulado` (mismo comportamiento que Etapas 1–3). El tablero sigue funcionando aunque la tabla `mpr_parte` esté vacía.

### Paso 2b en el algoritmo

```python
# Paso 2b: descontar OPP-parte acumulado (Etapa 4)
if enviado_pack_map:
    opp_map = opp_parte_acumulado_por_pack(base_empresa, list(enviado_pack_map))
    if opp_map:
        enviado_pack_map = {
            aid: max(0.0, enviado_pack_map.get(aid, 0) - float(opp_map.get(aid, 0)))
            for aid in set(enviado_pack_map) | set(opp_map)
        }
```

### Sin tooltip PROVISIONAL

El tooltip y la nota al pie "PROVISIONAL" se eliminaron en Etapa 4. La columna muestra la fórmula definitiva sin indicadores de aproximación.

---

## Filtros

| Filtro | Tipo | Descripción |
|--------|------|-------------|
| Fecha desde / hasta | server-side | Restringe la **demanda** a pedidos PED (`comp_ped.Fecha`) en el rango. No filtra stock ni envíos del pipeline. Etiqueta UI: «Demanda — fecha del pedido PED». |
| Búsqueda por artículo | client-side (Alpine.js) | Filtra filas visibles por `data-descripcion` (descripción + código). Sin round-trip. |
| Solo con pendiente | server-side | Toggle que filtra en Python antes de renderizar (`pendiente > 0`). |

---

## Actualización de Demanda

El botón **"Actualizar demanda"** invoca `actualizar_pedidos_produccion()` (servicio existente), que sincroniza `lista_produccion_detalle` y `lista_produccion_agrupada` desde los pedidos PED activos.

Tras la actualización:
- Se guarda en sesión el timestamp como `tablero_produccion_ultima_actualizacion`.
- Se muestra en la UI como "Última actualización: dd/MM/yyyy HH:mm".

> El stock físico (`stock_deposito`) se refleja en tiempo real al cargar la vista (REQ-026). La demanda, en cambio, requiere presionar "Actualizar" para incorporar pedidos nuevos.

---

## Performance

**Índice `idx_sd_art_dep`** en `stock_deposito(id_articulo, id_deposito)`:

- Creado idempotentemente por `run_mpr_deposito_articulo_mysql()` en `core/services/legacy_mysql_schema/catalog.py`.
- Soporta la consulta pivote de stock del tablero (GROUP BY id_articulo, tipo_mpr).
- Guard idempotente: `indice_existe()` verifica antes de ejecutar `CREATE INDEX`.

> En bases de producción con `stock_deposito` grande, ejecutar la función de migración en ventana de mantenimiento (la creación del índice puede bloquear la tabla brevemente).

---

## Diagrama de Flujo

```
[lista_produccion_agrupada]
  WHERE cod_mov_opt > 0   ──────►  _query_enviado_packs()
  (OPTs liberadas)                       │
                                   enviado_pack_map
                                         │
[listar_ventana_pack()]            bulk_id_en_abm()  ◄──── art_ids = union(pending+enviado)
  WHERE cod_mov_opt NOT > 0              │
  (packs con demanda pendiente)     bulk_bom_detalle()
        │                                │
        │         ┌──────────────────────┤
        ▼         │                      ▼
 _explosion_dem…()       _enviado_produccion_por_componente()
        │                      │
  dem_ped, dem_res         enviado_comp
        │                      │
        └──────┬───────────────┘
               ▼
        comp_ids (solo componentes con demanda > 0)
               │
     _pivot_stock_por_tipo_mpr()  ─── 1 SQL GROUP BY id_articulo, tipo_mpr
               │
        stock_pivot{id_art: {tipo_mpr: saldo}}
               │
     _fetch_descripciones_articulo()  ─── 1 SQL
               │
     ┌─────────▼────────────────────────────────┐
     │  Por cada comp_id con demanda > 0:         │
     │  total = Σ(tipos ∈ TIPOS_QUE_SUMAN_STOCK) │
     │  enviado = enviado_comp.get(id, 0)         │
     │  pendiente = max(0, demanda−[env+total])   │
     └──────────────────────────────────────────┘
               │
       sort(pendiente DESC) → [:limit]
               ▼
        List[Dict] → contexto → tablero_produccion.html
```

---

## Archivos Involucrados

| Archivo | Acción |
|---------|--------|
| `mpr/services.py` | Funciones `_query_enviado_packs`, `_pivot_stock_por_tipo_mpr`, `_enviado_produccion_por_componente`, `_fetch_descripciones_articulo`, `listar_tablero_por_articulo` |
| `mpr/views.py` | Clases `TableroProduccionView`, `TableroProduccionActualizarView` |
| `mpr/urls.py` | Rutas `tablero-produccion/` y `tablero-produccion/actualizar/` |
| `mpr/templates/mpr/tablero_produccion.html` | Plantilla nueva — 10 columnas, sticky-left, Alpine, dark mode |
| `mpr/templates/mpr/tablero.html` | Enlace de acceso "Tablero de producción →" |
| `core/services/legacy_mysql_schema/catalog.py` | Índice `idx_sd_art_dep` idempotente en `run_mpr_deposito_articulo_mysql()` |
| `mpr/tests/test_tablero_consolidado.py` | Suite de tests sin MySQL real |

---

## Tests

Archivo: `mpr/tests/test_tablero_consolidado.py`

Comando:
```bash
docker exec Synap_app python manage.py test mpr.tests.test_tablero_consolidado
```

Cobertura de los tests:
- Consolidación por componente (dos packs → una fila acumulada)
- Total excluye Desperdicio (Scrap)
- Total respeta `suma_stock` por depósito (etapa con `suma_stock='No'` no cuenta en Total pero sí en su columna)
- Pendiente derivado en 4 escenarios (sin stock, con stock, con enviado+stock, no negativo)
- Enviado ≠ Producción por construcción
- Tablero vacío sin error
- Artículo sin BOM no aparece
- Toggle **Solo pendientes** activo por defecto; la elección se persiste en sesión (`tablero_produccion_solo_pendiente`) por usuario
- Ordenamiento descendente por pendiente
- Idempotencia del índice `idx_sd_art_dep`
- Constantes TIPOS_QUE_SUMAN_STOCK excluyen Scrap

---

## Columna Producción — Post-Etapa 5

> **Cambio Etapa 5 (2026-07-03):** La columna **Producción** ya no se alimenta de `ejecutar_liberar_opt`.
> Ahora es el stock escrito por `registrar_parte_produccion` (OPP-parte) vía `_registrar_asiento_fisico_opp_parte`.

**Antes de Etapa 5:**
- `ejecutar_liberar_opt` → INSERT stock + UPDATE stock_deposito[Produccion]
- Producción = stock físico escrito al liberar OPT

**Después de Etapa 5:**
- `ejecutar_liberar_opt` conserva: INSERT movimiento_stock OPT + UPDATE lista_produccion_agrupada
- `registrar_parte_produccion` → INSERT stock + UPDATE stock_deposito[Produccion]
- Producción = stock físico escrito al registrar parte (OPP-parte)

**Consecuencia:** Entre la liberación de una OPT (`ejecutar_liberar_opt`) y el registro del parte (`registrar_parte_produccion`), el stock de Producción es 0 para ese artículo. La columna Enviado = OPT_liberado_acum − OPP_parte_acum refleja la cantidad en tránsito.

**Sin doble conteo:**

```
Enviado    = max(0, OPT_liberado_acum − OPP_parte_acum)
Producción = stock_deposito[Produccion]  ← escrito por OPP-parte
Enviado + Producción ≤ OPT_liberado_acum  (no hay overlap)
```

**Acciones contextuales (col 11):** desde Etapa 5, el tablero muestra botones de transición por fila:
- Si `enviado > 0`: enlace a Registrar parte
- Si `produccion > 0`: menú Inspección → Planchado / Desperdicio
- Si `planchado > 0`: menú Transición → 2da Selección / Semi Elaborado

Ver [TRANSICIONES_LOTE.md](TRANSICIONES_LOTE.md) para detalles del servicio.

---

---

## Columna Enviado — Fórmula Etapa 7 (dos fuentes, sin doble conteo)

> **Cambio Etapa 7 (03/07/2026):** La columna **Enviado** ahora combina dos fuentes independientes.

### Fórmula definitiva E7

```
Enviado[comp] = Enviado_OPT[comp] + Enviado_tablero[comp]

Enviado_OPT[comp]     = max(0, OPT_liberado_acum − OPP_parte_acum)   ← E4, intacto
Enviado_tablero[comp] = max(0, SUM(envíos_tablero[comp]) − acreditado[comp])
acreditado = max(stock_componente, clasificado_desde_producción)
stock_componente = Producido + Semi + 2da + Scrap
clasificado_desde_producción = SUM(mpr_transicion_lote WHERE tipo_origen = 'Produccion')
```

**Sin doble conteo:** al clasificar hacia Semi/2da/Scrap, el stock físico acredita envíos. Si el semi ya salió por armado del pack, la trazabilidad en `mpr_transicion_lote` evita que Fabricando repunte.

### Paso 7b en el algoritmo

```
Paso 8:  comp_ids = set(dem_ped) | set(dem_res)

→ Paso 7b: envios_tablero = _query_enviado_tablero_componente(base, list(comp_ids))
           Backward-safe: {} si tabla vacía, comp_ids vacío o error de DB.

Paso 9:  stock_pivot, stock_suma_pivot = _pivot_stock_por_tipo_mpr(base, list(comp_ids))

Paso 11 (por comp_id):
   enviado_opt         = enviado_comp.get(comp_id, 0.0)
   stock_prod          = stock_pivot[comp_id].get(TIPO_MPR_PRODUCCION, 0.0)
   envios_dir          = float(envios_tablero.get(comp_id, 0))
   enviado_tablero_val = max(0.0, envios_dir - acreditado)   # ver _calcular_fabricando_componente
   enviado             = enviado_opt + enviado_tablero_val
     pendiente           = max(0.0, (demanda - total) - envios_dir)
```

### Columna "Enviar" (col 11, nueva en E7)

- Input numérico habilitado cuando `pendiente > 0`, deshabilitado si `pendiente <= 0`.
- Al hacer click en **Enviar a producción**, se confirma con `window.confirm` y se hace `POST` al endpoint E7.
- El form usa el atributo HTML5 `form="form-enviar-lote"` para evitar forms anidados con los modales E5.
- **colspan** del empty-state: 12 (antes 11).

### Acciones contextuales (cols 11-12)

- **Col 11 — Enviar:** input para envío directo a producción (E7).
- **Col 12 — Trazabilidad** _(renombrada en E9)_: solo muestra el botón «Trazabilidad» cuando
  la fila tiene `id_lista_produccion`. Los botones «Registrar parte», «Inspección ▾» y
  «Transición ▾» fueron eliminados en E9 (reemplazados por botones globales en la barra superior).

Ver [ENVIO_PRODUCCION_TABLERO.md](ENVIO_PRODUCCION_TABLERO.md) para el detalle completo de la capability E7.

---

## Cambios E9: Barra Superior — Botones Globales

A partir de la Etapa 9 la barra superior del Tablero incluye dos botones adicionales
tras «Parte de producción»:

| Botón | Icono | URL |
|-------|-------|-----|
| Inspección | `search` | `/mpr/tablero-produccion/inspeccion/` |
| Clasificación | `category` | `/mpr/tablero-produccion/clasificacion/` |

Estilo: `border-slate-500 bg-slate-700` (igual que los botones existentes).

Las acciones de transición (Producción→Planchado/Scrap y Planchado→2daSelección/SemiElaborado)
se realizan **exclusivamente** desde estas pantallas globales de lote.

Ver [ACCIONES_LOTE_TABLERO.md](ACCIONES_LOTE_TABLERO.md) para el detalle completo de E9.

---

## Fuera de Alcance (Etapa 2)

- **Transiciones por lote:** **implementadas en Etapa 5** (ver [TRANSICIONES_LOTE.md](TRANSICIONES_LOTE.md))
- **OPP como parte:** `MprParte` / `MprParteLinea` — **implementado en Etapa 4** (ver [OPP_PARTE_PRODUCCION.md](OPP_PARTE_PRODUCCION.md))
- **Turnos:** `MprTurno` / `MprRoster` (etapa 3)
- **Fórmula definitiva de Enviado:** **implementada en Etapa 4** (paso 2b) y extendida con dos fuentes en **Etapa 7**
- **Envío directo a producción desde Tablero:** **implementado en Etapa 7** (ver [ENVIO_PRODUCCION_TABLERO.md](ENVIO_PRODUCCION_TABLERO.md))
- **Parte de producción por componente (Fabricando):** **implementado en Etapa 8** (ver [PARTE_PRODUCCION.md](PARTE_PRODUCCION.md)); grilla usa `MprEnvioProduccion` (no `lista_produccion_agrupada`); asiento directo sin explosión BOM; `id_lista_produccion=None`.
- **WebSockets / auto-refresh:** diferido
- **Desmontaje de `ejecutar_liberar_opt`:** **implementado en Etapa 5**
