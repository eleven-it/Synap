# Carga móvil del operario (parte de producción)

> Estado: implementado en Fase 6 del change `mpr-trazabilidad-maquina-linea-operario`.
> Dominio Best Sox: **1 docena = 12 pares**. Captura en docenas + pares sueltos, persistencia en pares.

## Objetivo

Permitir que el operario, al finalizar su turno, registre desde su dispositivo móvil
la producción **por máquina** de su línea, seleccionando solo los artículos habilitados
vigentes. La carga queda **pendiente de aprobación** del supervisor y **no mueve stock**
hasta esa aprobación (modelo de dos etapas).

## Acceso y contexto automático

- Ruta: `/mpr/mi-parte/` (`mpr:parte_movil_operario`). Permiso: `mpr.parte_operario`.
- El operario "puro" (con `mpr.parte_operario` y sin `mpr.ver`) aterriza aquí tras el login.
- El operario con **`mpr.parte_operario` + `mpr.tablero_ver`** (sin `mpr.ver`) también aterriza en `/mpr/mi-parte/`; puede consultar el tablero en solo lectura desde el menú MPR (ítem «Tablero de producción»), sin acceso a enviar, CC, reportes ni resto del escritorio MPR.
- La pantalla resuelve automáticamente, sin selección manual salvo multi-turno:
  - **Operario**: mapeo `mpr_operario_usuario` (usuario de login → `sue_abm_empleado`).
  - **Turno(s)**: `turnos_del_operario_dia` (lista). Si hay **un** turno, se usa directo; si hay **varios**, chips selector (`?turno=<id>`) y campo oculto `id_turno` al guardar.
  - **Línea**: `resolver_linea_operario(fecha, id_turno)` = override del roster **por turno** > línea habitual.
  - **Máquinas**: `maquinas_de_linea` (pertenencia vigente a la fecha).
  - **Artículos por máquina**: `listar_articulos_vigentes` (habilitación vigente).

## Guardado (sin asiento físico)

`registrar_parte_movil(...)` (en `mpr/services_parte_movil.py`) → `crear_o_actualizar_parte_movil`
(en `mpr/repositories/parte_movil.py`):

- Crea/reutiliza el parte editable del usuario para fecha+turno con
  `mpr_parte.estado = 'pendiente'` (o `'borrador'`) y `origen = 'movil_operario'`,
  `movimiento_fisico_ok = 0`.
- Por cada (máquina, artículo) con carga > 0 inserta `mpr_parte_linea` con:
  - `id_mpr_maquina` + `maquina_nombre` (snapshot), `id_operario` + `operario_nombre`.
  - `cantidad_declarada = docenas × 12 + pares`.
  - `cantidad = 0` (la cantidad física se completa recién en la aprobación del supervisor,
    Fase 7, con `cantidad_aprobada`), `gap = 0`, `cantidad_aprobada = NULL`.
- **No** ejecuta asiento físico ni toca `stock_deposito`.

### Borrador vs. envío

- **Borrador**: admite guardar sin cargas (para retomar luego).
- **Enviar**: exige al menos una carga; deja el parte `pendiente` de aprobación.
- Reeditar reutiliza el mismo parte (reemplaza líneas), tanto en `borrador` como en `pendiente`.

## UI

- Móvil: `mpr/templates/mpr/mobile/parte_operario.html` (vía `get_template_for_device`),
  con header de contexto (línea/turno/fecha), lista de máquinas colapsables → artículos,
  inputs docenas/pares **vacíos por defecto** (vacío = 0 al guardar; solo se muestran
  cifras si hay precarga de borrador/pendiente &gt; 0), total en vivo (Alpine),
  progreso `cargadas/total` y confirmación antes de enviar.
- Escritorio: `mpr/templates/mpr/parte_operario.html`. Extiende `mpr/base_mpr.html`
  (misma shell que Tablero/Parte de producción: barra de acceso rápido MPR, contenedor
  `mpr-contenedor-pagina` de ancho fluido, migas de pan y **frame de encabezado oscuro**
  con título e ícono). Mantiene el mismo comportamiento y modal de confirmación que el móvil.
- Estados de borde con mensaje claro: `sin_operario`, `sin_turno`, `sin_linea`, `sin_maquinas`, `turno_bloqueado` (parte aprobado/CC en ese turno; el operario puede elegir otro turno del día).

### Navegación PWA relacionada

Si el usuario tiene además `mpr.ver`, el bottom nav compartido (`mpr/includes/mobile_nav_mpr.html`) enlaza **KPIs** (`/mpr/`) e **Inventario** (`/mpr/inventario/`) además de **Mi parte**. Detalle: [PWA_TABLERO_INVENTARIO.md](./PWA_TABLERO_INVENTARIO.md).

### Buscador predictivo y comodidad de carga (UX)

Para líneas con muchas máquinas (p. ej. 20), ambas plantillas incluyen un **buscador
predictivo sticky** (client-side, Alpine) que filtra en vivo por:

- **Máquina**: código (`mpr_maquina.codigo`) o nombre.
- **Artículo**: código o descripción de los artículos habilitados de la máquina.

Comportamiento y decisiones de diseño:

- **"Ocultar máquinas sin artículos" activado por defecto**: como esas máquinas no son
  cargables, la vista arranca mostrando solo las operativas. Toggle para ver todas.
- **Contador "Mostrando X de N máquinas"** para dar contexto del filtro.
- En móvil, al buscar por artículo se **auto-expande** la tarjeta que coincide.
- **Botón limpiar (×)** y **estado vacío** ("Sin resultados") con mensaje contextual.
- El filtrado es solo visual (`display`): **no** altera el envío; los datos cargados en
  máquinas ocultas igual se envían.
- **Confirmación de envío unificada** (móvil y escritorio): el botón "Revisar y enviar"
  abre un modal que resume docenas y máquinas antes de confirmar, evitando envíos accidentales.

### Acceso al módulo por permiso granular

El middleware de permisos por módulo (`ModulePermissionMiddleware`) reconoce
`mpr.parte_operario`, `mpr.tablero_ver`, `mpr.reportes`, `mpr.maquinas_lineas` y `mpr.aprobar_parte` como permisos válidos del
módulo `mpr` (en `core/module_registry.py`). Así, el **operario puro** (solo
`mpr.parte_operario`, sin `mpr.ver`) puede acceder a `/mpr/mi-parte/` sin quedar atrapado en
un bucle dashboard ⇄ carga. Con **`mpr.tablero_ver`** además puede entrar al módulo MPR y ver
`/mpr/tablero-produccion/` en solo lectura (sin `mpr.ver`). Con solo **`mpr.reportes`** puede abrir
`/mpr/reportes/` sin Parte, CC, Armado ni configuración. El catálogo Synap (`synap_permiso`) debe tener sembrados estos
permisos (seed idempotente `seed_synap_permiso_catalog` desde `PERMISOS_POR_MODULO`).

### Matriz de permisos — operario + tablero + reportes

| Permiso | Operario puro (`parte_operario`) | Operario + tablero (`parte_operario` + `tablero_ver`) | Solo reportes (`mpr.reportes`) | Escritorio MPR (`mpr.ver`) |
|---------|----------------------------------|--------------------------------------------------------|--------------------------------|----------------------------|
| Landing post-login | `/mpr/mi-parte/` | `/mpr/mi-parte/` | `/mpr/reportes/` | Dashboard normal |
| Menú MPR | Oculto (sin acceso al módulo) | Solo «Tablero de producción» | Solo «Reportes MPR» | Menú completo |
| GET tablero / actualizar / manual | 403 | 200 (solo lectura) | 403 | 200 (completo) |
| POST enviar / CC / escritorio | 403 | 403 | 403 | 200 (según pantalla) |
| GET reportes | 403 | 403 | 200 | 200 |
| UI tablero | — | Oculta Enviar, E5, enlaces Parte/CC/KPI | — | Acciones completas |

## Validación (administranet96)

- Parte `pendiente`/`movil_operario`; `cantidad`=0; `cantidad_declarada`=41 (3×12+5) y 48 (4×12).
- `stock_deposito.saldo` sin cambios tras guardar.
- Reedición reutiliza el mismo parte; prefill de docenas/pares correcto.
- Bordes `sin_turno`/`sin_linea` y borrador vacío OK.

## Aprobación del supervisor (Fase 7)

Segunda etapa del flujo. Solo la aprobación mueve stock.

- **Bandeja** `/mpr/partes-pendientes/` (`PartesPendientesView`, permiso `mpr.aprobar_parte`):
  lista de partes `pendiente` (y opcional `borrador`), filtrable por fecha/turno.
- **Detalle** `/mpr/partes-pendientes/<id>/` (`PartePendienteDetailView`): tabla por línea con
  `cantidad_declarada`, **cupo Fabricando** de referencia, input de `cantidad_aprobada` y `motivo`.
- **Servicio** `aprobar_parte_produccion(base, id_parte, correcciones, id_usuario_supervisor, forzar_cupo)`
  (en `mpr/services.py`):
  - Por línea: `cantidad_aprobada` (default = declarada), `gap = aprobada − declarada`,
    `motivo` **obligatorio si `gap != 0`**; sincroniza `cantidad = cantidad_aprobada`.
  - Valida cupo Fabricando + techo de envíos sobre lo aprobado (`validar_cupo_parte`);
    bloquea salvo `forzar_cupo=True` (checkbox "Aprobar aunque supere el cupo").
  - Ejecuta el **asiento físico** a depósito "Producción" reutilizando el asiento OPP
    (`_registrar_asiento_fisico_opp_parte`, `ya_componentes=True`).
  - Cierra el parte: `estado='aprobado'`, `id_usuario_supervisor`, `aprobado_en`,
    `movimiento_fisico_ok=1`. **Idempotente**: reaprobar un parte ya aprobado no duplica stock.

### Refactor y coexistencia

- Se extrajo `validar_cupo_parte(base, lineas)` reutilizada por el parte directo (al guardar)
  y por la aprobación (sobre `cantidad_aprobada`).
- El **parte directo del supervisor** (`registrar_parte_produccion`) se conserva: nace
  `estado='aprobado'`, `origen='directo_supervisor'` (defaults del ALTER) y mueve stock en el acto.

### Nota sobre acumulados

Los partes `pendiente` guardan `cantidad = 0`, por lo que **no** contaminan los acumulados
basados en `mpr_parte_linea.cantidad` (OPP acumulado, cupo). Al aprobar, `cantidad` pasa a
`cantidad_aprobada` y recién ahí cuenta en el pipeline.

## Asignar artículo a máquina (supervisor)

Pantalla de escritorio para habilitar/deshabilitar artículos en la grilla de máquinas
(antes de que el operario cargue producción en `/mpr/mi-parte/`):

- Menú: **Producción diaria → Asignar artículo a máquina**.
- Ruta: `/mpr/maquinas/carga-articulos/` (`mpr:maquinas_carga_articulos`). Permiso: `mpr.maquinas_lineas`.
- **Selector de fecha** en el encabezado (GET `?fecha=dd/MM/yyyy`, default hoy; mismo patrón que Parte de producción).
  Los chips muestran artículos **vigentes a esa fecha** (`listar_articulos_vigentes_todas_maquinas`).
  Fechas futuras se rechazan (clamp a hoy en la grilla; error en API).
- **Fecha pasada:** aviso en pantalla («solo ese día»). Agregar crea vigencia `[F, F+1)`; quitar hace split
  sin romper otros días. **Agregar** permitido aunque el día tenga parte aprobado u otros artículos con parte;
  **quitar** bloqueado si existe línea de `mpr_parte`/`mpr_parte_linea` para esa máquina×artículo×fecha.
- Filtro MVP por línea: query `?id_linea=<id_mpr_linea>` (conserva `fecha` en el formulario).
- Búsqueda predictiva de artículos (API GET `/mpr/maquinas/api/articulos/buscar/`): solo
  artículos con `tipo_art_fab = 'Fabricado'`.
- En la grilla, los vigentes se muestran como **chips de multiselección** (pill
  `rounded-full` púrpura + input en el mismo contenedor tipo `tags-filter`), no como
  lista de tags aparte del campo «Agregar».
- Habilitar/deshabilitar vía API POST `/mpr/maquinas/api/articulos/accion/` (`accion`:
  `habilitar` | `deshabilitar`; payload incluye `fecha` en `dd/MM/yyyy`). En **hoy**, habilitar abre vigencia
  (`vigencia_hasta = NULL`) y deshabilitar la cierra (`vigencia_hasta = hoy`). En **fecha pasada**, habilitar
  asigna solo ese día; deshabilitar quita cobertura de F (borra fila solo-día o split en intervalos largos).
- Histórico por máquina: `/mpr/maquinas/<id>/articulos/` (vista detalle existente).

Servicio de contexto: `construir_grilla_carga_articulos` en `mpr/services_maquina_linea.py`.
Los artículos vigentes incluyen **TALLES** y **COLOR** desde campos especiales
(`articulo_ce` / `articulo_val_ce`, resueltos por caption, no por id fijo).

### Planilla Control de Calidad (impresión)

Botón único **Imprimir Control de Calidad** en el encabezado de la pantalla.
Abre un **modal Synap** (sin `alert`/`confirm` nativos) para elegir la **fecha** de la
planilla (por defecto hoy). **Cancelar** cierra el modal; **Confirmar e imprimir** obtiene
los datos vía API y lanza `window.print()`.

API: `GET /mpr/maquinas/api/planilla-control-calidad/?fecha=YYYY-MM-DD&id_linea=`  
Servicio: `construir_datos_planilla_control_calidad` en `mpr/services_maquina_linea.py`.

Genera una hoja **A4 horizontal** (`@page size: A4 landscape`, márgenes 6 mm) pensada
para completar a mano. El bloque de impresión usa flujo normal (no `position: absolute`)
para paginar sin recortes; la cabecera de la tabla se repite en cada hoja
(`thead { display: table-header-group }`). Cada casillero 1ra/2da apila **prod + CC**
en la misma celda (bandas de ~7 mm) para que un salto de página no pierda la franja CC.

- Título: `CONTROL DE CALIDAD — {día} {dd/MM/yyyy}` (día en español; fecha elegida en el modal).
- Columnas: MÁQUINA | DETALLE (ARTÍCULO · COLOR · TALLE) | TURNO MAÑANA (1ra·2da) |
  TURNO TARDE (1ra·2da) | TURNO NOCHE (1ra·2da) | OBSERVACIONES.
- Anchos de impresión: las columnas **1ra/2da** de turnos son amplias (escritura a mano);
  **ARTÍCULO** cede espacio y hace wrap si hace falta.
- Filas: **solo lo visible en pantalla** (filtro de línea GET + búsqueda de máquina client-side).
  Si filtrás una sola máquina, la planilla imprime únicamente esa fila/artículos.
- **Por cada artículo, un solo `<tr>`** (`break-inside: avoid`):
  - En cada casillero 1ra/2da: banda superior = producción (1ra precargada / 2da vacía);
    banda inferior = CC vacía (escritura manual), separadas por línea.
  - Así no se usa `rowspan=2` entre prod y CC (ese esquema perdía la 2.ª banda al paginar
    con **todas las líneas**).
  - Máquina y observaciones: `rowspan = n_artículos`.
- **Artículos por fecha:**
  - Fecha **≤ hoy:** vigentes en `mpr_maquina_articulo` a esa fecha
    (`listar_articulos_vigentes_todas_maquinas`).
  - Fecha **futura:** mismos artículos vigentes **hoy**; cantidades vacías.
- **Cantidades 1ra** (solo fecha ≤ hoy): suma por máquina×artículo×franja desde partes de esa
  fecha (`cantidades_parte_planilla_por_fecha`). Parte `aprobado` → `cantidad_aprobada`
  (o 0 si null); otro estado → `cantidad_declarada`. Franja vía `id_mpr_turno` +
  `_franja_horaria_turno`. Solo líneas con `id_mpr_maquina` no null. Sin parte → vacío.
  Si hay artículos pero sin cantidades, **se imprime igual**.
- **Operadores por turno**: roster del **día de la planilla** (`operarios_roster_por_linea`).
  Misma granularidad: nombres en cabecera mañana/tarde/noche. Sin roster → celda vacía; se imprime igual.
- **Observación por máquina**: cada máquina de la grilla tiene un campo «Observación
  (planilla)» (máx. 220 caracteres). Ese texto se imprime **una sola vez por máquina**
  en la columna OBSERVACIONES (celda con `rowspan` sobre sus artículos),
  no una celda por artículo. Se **persiste en MySQL** (`mpr_maquina.observacion_planilla`)
  y se guarda al salir del campo (blur); API `POST /mpr/maquinas/api/observacion-planilla/`.
- **Orden de artículos** en la planilla: por antigüedad de asignación
  (`vigencia_desde`, `creado_en`, `id_mpr_maquina_articulo` ASC).
- Si no hay filas imprimibles tras confirmar el modal, **modal Synap** de aviso (no `alert` nativo).
- El encabezado de la hoja puede mostrar el filtro activo (línea / búsqueda).

Origen de COLOR/TALLES: ver [ARTICULO_CE_TALLES_COLOR.md](ARTICULO_CE_TALLES_COLOR.md).
Ver también [TRAZABILIDAD_MAQUINA_LINEA_OPERARIO.md](TRAZABILIDAD_MAQUINA_LINEA_OPERARIO.md#urls).
