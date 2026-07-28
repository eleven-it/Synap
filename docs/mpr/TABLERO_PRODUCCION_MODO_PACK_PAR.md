# Tablero de producción — Toggle Pack | Par

Ruta: `/mpr/tablero-produccion/` · Vista: `mpr.views.TableroProduccionView`

**Chrome / densidad del encabezado:** ver [TABLERO_PRODUCCION_CHROME_DENSIDAD.md](TABLERO_PRODUCCION_CHROME_DENSIDAD.md) (toolbar clara, iconos+tooltips, sin hero oscuro).

## Objetivo

El tablero de producción ofrece dos consolidaciones de la demanda en vivo (desde
pedidos PED), seleccionables con el toggle **Pack | Par** del encabezado:

| Modo | Query | Consolida por | Servicio | Explosión BOM |
|------|-------|---------------|----------|:---:|
| **Par** (default) | `?modo=par` | **componente BOM** (par de componente) | `listar_tablero_por_articulo` | Sí |
| **Pack** | `?modo=pack` | **artículo pack terminado** (paridad BEST PCP Producción) | `listar_tablero_pack` | No |

- **Par** = componente BOM. Es la base del **envío a producción** (columna *Enviar
  docenas/pares*). Es el modo por defecto para no alterar el flujo operativo.
- **Pack** = terminado (PCP). Pedido / reserva / resta / stock se calculan a nivel
  del pack terminado, sin explotar la BOM (equivalente a la vista BEST PCP Producción).
  Lista **toda** la demanda a fabricar: pedidos PED abiertos **y** terminados con
  quiebre solo-reserva (`stock_reserva > 0` sin PED). El chip **Solo urgentes** no
  aplica en este modo (sí en Par).

Ayuda visible en el encabezado: *"Pack = terminado (PCP, pedido + reserva, sin explosión BOM); Par =
componente BOM (base del envío a producción)."*

## Comportamiento del botón "Enviar a producción"

- **Modo Par:** botón *Enviar a producción* + columna *Enviar docenas/pares* activos
  (flujo normal por componente). El POST a `mpr:tablero_produccion_enviar` conserva
  `modo=par` en `filtros_qs`.
- **Modo Pack:** el botón de envío se **oculta** y las filas **no** muestran input de
  envío (el envío es por componente, no por pack). En su lugar se muestra un CTA
  **"Ver en modo Par para enviar"** que enlaza a `?modo=par` preservando filtros.

## Columnas por modo

- **Par:** Artículo (`N` listados; se actualiza con el buscador) · Pedido · Reserva · **Urgente** · Fabricando · **Enviado** ·
  Producido · 2da Selección · Semi Elaborado · Total · Enviar.
- **Pack:** Artículo (`N` listados; se actualiza con el buscador) · Fecha entrega · Pedido · Reserva · **Urgente** ·
  Terminado (stock del pack).

### Indicadores Fabricando y Enviado (solo modo Par)

En la columna **Fabricando**, cada fila con artículo asignado a al menos una máquina
vigente (`mpr_maquina_articulo`) muestra un **chip violeta** sobre el cupo y un ícono
**engranaje** (`precision_manufacturing`). Hover sobre el ícono: tooltip BO con
«Máquina N» (lista si hay varias); clic abre el modal. El modal agrupa por **Fila**
en tabla: encabezado `Fila | Mañana (operarios) | Tarde | Noche` y **una fila de datos
por máquina** (`Máquina N | pares M | pares T | pares N`). Header con cupo Fabricando
(`enviado`) y CTAs a **Parte** y **Control de calidad** (fecha = `fecha_hasta` del
filtro o hoy). Payload: `fabricando_detalle.grupos_fila`. Si `enviado > 0` y **no** hay
máquina asignada, aparece un ícono ámbar de espera con tooltip «Fabricando sin máquina
asignada» y enlace a carga de artículos por máquina. Servicio:
`enriquecer_filas_tablero_indicadores_fabricando` en `mpr/services_maquina_linea.py`.
En el modal, el **nombre del artículo** es el título principal (`h3` bold); «Fabricando»
queda como eyebrow. Hover sobre «Máquina N» muestra tooltip estilo BO
(`bg-slate-900`, «Máquina X — nombre»).

La columna **Enviado** muestra la suma del ledger `mpr_envio_produccion` (envíos no
anulados). **No** confundir con **Fabricando** (`enviado` = envíos − acreditado en
stock del pipeline). El tope de la columna **Enviar** es `máx(0, Urgente − Enviado)`.

La columna **Resta total** se eliminó en ambos modos: **Urgente** unifica la brecha
a fabricar (`max(0, Pedido + Reserva − stock)`).

### Aviso «Sin receta» (modo Pack)

Si el pack terminado **no tiene BOM** (`id_en_abm` vacío/0 o sin componentes en
`en_abm_formula`):

- La fila se marca en **ámbar** con badge **Sin receta** (aviso recomendado).
- Un ícono de pedidos abre un **tooltip** con los PED vivos asociados (n.º, estado,
  fecha, cliente, cantidad) para revisión.
- **No bloquea envío** en el tablero: el envío solo ocurre en modo **Par**, y un pack
  sin receta **no genera** componentes allí (omisión silenciosa en la explosión).
- El bloqueo duro por falta de receta sigue en **OPT / ventana-pack** al generar OPT.

**Filtro «Sin receta» (chip en encabezado):** visible solo en modo Pack. Query
`solo_sin_receta=1|0` (default `0`). Persiste en sesión (`tablero_produccion_solo_sin_receta`).
Cuando está activo, la tabla muestra solo packs marcados con badge **Sin receta**; si no hay
coincidencias: «Sin packs sin receta con demanda en el rango especificado».

## Cálculos (modo Pack)

Sobre `listar_demanda_pack_desde_pedidos` (sin escribir en `lista_produccion_*`):

- Fuente: pedidos PED abiertos **+** terminados con `stock_reserva > 0` (solo-reserva).
- Los filtros de **fecha** aplican solo a líneas PED; la parte solo-reserva no depende de fechas.
- `dem_ped` (Pedido) = `cantidad_pedida_pedido` (P_ped del pack; 0 si solo-reserva).
- `dem_res` (Reserva) = `stock_reserva` (R maestro del terminado; colchón objetivo).
- `resta_urgente` = `resta_total` = `cantidad_a_fabricar` = `max(0, Pedido + Reserva − Terminado)`.
- `terminado` / `total` = `stock_terminado` (depósitos que suman stock).
- `enviado` (Fabricando) = `0` y `a_enviar` = `0`: el envío es por componente.
- **Solo urgentes:** no filtra en Pack; se muestran filas con demanda a fabricar. En Par filtra `resta_urgente > 0` (ahora = brecha demanda total).

Tooltips UI:

- **Reserva (Pack):** colchón objetivo del terminado (`articulo.stock_reserva`).
- **Urgente (Pack/Par):** `max(0, Pedido + Reserva − stock)`; hueco de stock frente a demanda (no indica cuánto enviar; ver Enviar / Enviado).
- **Reserva (Par):** colchón objetivo del pack terminado explotado por BOM
  (`coef × articulo.stock_reserva`), misma semántica que Reserva en modo Pack.
  La brecha operativa (Urgente / a_enviar) sigue usando `n_res_tail` tras descontar
  stock terminado del pack; Fabricando no depende de esta columna.

Los **KPIs del encabezado** (`calcular_kpis_tablero_produccion`) suman `resta_urgente` y
`resta_total`; en modo Pack ambos coinciden (Urgente unificado).

## Persistencia de filtros

El toggle **Pack|Par** preserva `fecha_desde/hasta`, marcas y
`presentacion` (docenas/pares). El toggle **Docenas|Pares** preserva a su vez `modo`.
En modo **Par**, el filtro *Solo urgentes* (`solo_urgente`) también se preserva entre
vistas; en modo **Pack** el chip *Solo urgentes* se oculta porque no tiene efecto.
En modo **Pack**, el chip *Sin receta* (`solo_sin_receta`, default desactivado) filtra
solo packs sin BOM y se preserva igual que el resto de filtros.

### Último estado en sesión (17/07/2026)

Además de la query string, el tablero **persiste en sesión** el último estado de:

| Preferencia | Clave de sesión | Default |
|-------------|-----------------|---------|
| Pack \| Par | `tablero_produccion_modo` | `par` |
| Docenas \| Pares | `mpr_presentacion_cantidad` | `docenas` |
| Solo urgentes | `tablero_produccion_solo_urgente` | `true` |
| Sin receta (Pack) | `tablero_produccion_solo_sin_receta` | `false` |

- Al abrir `?modo=pack` o `?presentacion=unidades`, se guarda en sesión.
- Sin el param en la URL (F5, «Actualizar vista», redirect post-envío), se reutiliza el valor de sesión.
- `_redirect_tablero_produccion` reinyecta `modo` y `presentacion` en la URL de retorno para que los toggles y bookmarks queden alineados.
- La búsqueda de artículo del chrome (filtro Alpine client-side) se persiste en `?q=`: el POST de **Actualizar** envía el texto actual y el redirect lo reinyecta; Pack|Par, Docenas|Pares y Solo urgentes reusan `modo_query_base` / `presentacion_query_base` que ya incluyen `q` cuando viene en la URL.

## Presentación docenas/pares

El toggle **Docenas | Pares** aplica en ambos modos: `enriquecer_filas_tablero_presentacion`
opera sobre las mismas claves (`dem_ped`, `dem_res`, `resta_total`, `resta_urgente`,
`total`, …), por lo que Pack y Par comparten la misma lógica de presentación.

## Tests

`mpr/tests/test_tablero_pack_modo.py` (suite pura, sin MySQL):

- `TestListarTableroPack`: mapeo de columnas a nivel pack, sin explosión BOM,
  Pack ignora `solo_urgente`, filtro `solo_sin_receta`, sin envío a nivel pack, orden y bordes.
- `TestModoPackVsPar`: la resta total del pack no multiplica por la BOM.
- `TestTableroProduccionViewModo`: `?modo=pack|par|inválido` selecciona el servicio
  correcto y expone `modo_tablero` en el contexto (default `par`).

`mpr/tests/test_tablero_solo_pendiente_sesion.py`:

- `TestModoTableroSesion`: `?modo=pack` persiste; GET sin `modo` reusa sesión;
  valor inválido no pisa sesión; `_redirect_tablero_produccion` reinyecta
  `modo`, `presentacion` y `solo_sin_receta`.
- `TestBusquedaArticuloRedirect`: `?q=` se preserva en el redirect; `q` vacío no se reinyecta.
- `TestSoloSinRecetaSesion`: query/sesión/redirect de `solo_sin_receta`.

Ejecutar:
`docker exec Synap_app python manage.py test mpr.tests.test_tablero_pack_modo mpr.tests.test_tablero_armado_fecha_entrega mpr.tests.test_tablero_solo_pendiente_sesion`
