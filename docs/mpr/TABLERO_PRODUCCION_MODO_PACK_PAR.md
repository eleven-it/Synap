# Tablero de producción — Toggle Pack | Par

Ruta: `/mpr/tablero-produccion/` · Vista: `mpr.views.TableroProduccionView`

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

Ayuda visible en el encabezado: *"Pack = terminado (PCP, sin explosión BOM); Par =
componente BOM (base del envío a producción)."*

## Comportamiento del botón "Enviar a producción"

- **Modo Par:** botón *Enviar a producción* + columna *Enviar docenas/pares* activos
  (flujo normal por componente). El POST a `mpr:tablero_produccion_enviar` conserva
  `modo=par` en `filtros_qs`.
- **Modo Pack:** el botón de envío se **oculta** y las filas **no** muestran input de
  envío (el envío es por componente, no por pack). En su lugar se muestra un CTA
  **"Ver en modo Par para enviar"** que enlaza a `?modo=par` preservando filtros.

## Columnas por modo

- **Par:** Artículo · Pedido · Reserva · Resta total · Resta urgente · Fabricando ·
  Producido · 2da Selección · Semi Elaborado · Desperdicio · Total · Enviar.
- **Pack:** Pack terminado · Fecha entrega · Pedido · Reserva · Resta total ·
  Resta urgente · Terminado (stock del pack).

## Cálculos (modo Pack)

Sobre `listar_demanda_pack_desde_pedidos` (sin escribir en `lista_produccion_*`):

- `dem_ped` (Pedido) = `cantidad_pedida_pedido` (P_ped del pack).
- `dem_res` (Reserva) = `cantidad_demanda_reserva`.
- `resta_total` = `cantidad_a_fabricar` = `max(0, Pedido + Reserva − Terminado)`.
- `resta_urgente` = `cantidad_urgente_abs` = `max(0, Pedido − Terminado)`.
- `terminado` / `total` = `stock_terminado` (depósitos que suman stock).
- `enviado` (Fabricando) = `0` y `a_enviar` = `0`: el envío es por componente.

Los **KPIs del encabezado** (`calcular_kpis_tablero_produccion`) se recalculan sobre
las filas del modo activo (resta urgente / resta total en pares y docenas).

## Persistencia de filtros

El toggle **Pack|Par** preserva `fecha_desde/hasta`, `solo_urgente`, marcas y
`presentacion` (docenas/pares). El toggle **Docenas|Pares** y el filtro *Solo urgentes*
preservan a su vez `modo`.

### Último estado en sesión (17/07/2026)

Además de la query string, el tablero **persiste en sesión** el último estado de:

| Preferencia | Clave de sesión | Default |
|-------------|-----------------|---------|
| Pack \| Par | `tablero_produccion_modo` | `par` |
| Docenas \| Pares | `mpr_presentacion_cantidad` | `docenas` |
| Solo urgentes | `tablero_produccion_solo_urgente` | `true` |

- Al abrir `?modo=pack` o `?presentacion=unidades`, se guarda en sesión.
- Sin el param en la URL (F5, «Actualizar vista», redirect post-envío), se reutiliza el valor de sesión.
- `_redirect_tablero_produccion` reinyecta `modo` y `presentacion` en la URL de retorno para que los toggles y bookmarks queden alineados.

## Presentación docenas/pares

El toggle **Docenas | Pares** aplica en ambos modos: `enriquecer_filas_tablero_presentacion`
opera sobre las mismas claves (`dem_ped`, `dem_res`, `resta_total`, `resta_urgente`,
`total`, …), por lo que Pack y Par comparten la misma lógica de presentación.

## Tests

`mpr/tests/test_tablero_pack_modo.py` (suite pura, sin MySQL):

- `TestListarTableroPack`: mapeo de columnas a nivel pack, sin explosión BOM,
  `solo_urgente`, sin envío a nivel pack, orden y bordes.
- `TestModoPackVsPar`: la resta total del pack no multiplica por la BOM.
- `TestTableroProduccionViewModo`: `?modo=pack|par|inválido` selecciona el servicio
  correcto y expone `modo_tablero` en el contexto (default `par`).

`mpr/tests/test_tablero_solo_pendiente_sesion.py`:

- `TestModoTableroSesion`: `?modo=pack` persiste; GET sin `modo` reusa sesión;
  valor inválido no pisa sesión; `_redirect_tablero_produccion` reinyecta
  `modo` y `presentacion`.

Ejecutar:
`docker exec Synap_app python manage.py test mpr.tests.test_tablero_pack_modo mpr.tests.test_tablero_solo_pendiente_sesion`
