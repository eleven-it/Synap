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
- La pantalla resuelve automáticamente, sin selección manual:
  - **Operario**: mapeo `mpr_operario_usuario` (usuario de login → `sue_abm_empleado`).
  - **Turno**: `mpr_roster_dia` del día (`turno_del_operario_dia`).
  - **Línea**: `resolver_linea_operario` = override del roster del día > línea habitual (`mpr_operario_linea`).
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
- Estados de borde con mensaje claro: `sin_operario`, `sin_turno`, `sin_linea`, `sin_maquinas`.

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
`mpr.parte_operario`, `mpr.maquinas_lineas` y `mpr.aprobar_parte` como permisos válidos del
módulo `mpr` (en `core/module_registry.py`). Así, el **operario puro** (solo
`mpr.parte_operario`, sin `mpr.ver`) puede acceder a `/mpr/mi-parte/` sin quedar atrapado en
un bucle dashboard ⇄ carga. El catálogo Synap (`synap_permiso`) debe tener sembrados estos
permisos (seed idempotente `seed_synap_permiso_catalog` desde `PERMISOS_POR_MODULO`).

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
- Filtro MVP por línea: query `?id_linea=<id_mpr_linea>`.
- Búsqueda predictiva de artículos (API GET `/mpr/maquinas/api/articulos/buscar/`): solo
  artículos con `tipo_art_fab = 'Fabricado'`.
- Habilitar/deshabilitar vía API POST `/mpr/maquinas/api/articulos/accion/` (`accion`:
  `habilitar` | `deshabilitar`). Deshabilitar cierra la vigencia (`vigencia_hasta = hoy`);
  no hay undo silencioso ni cierre automático diario.
- Histórico por máquina: `/mpr/maquinas/<id>/articulos/` (vista detalle existente).

Servicio de contexto: `construir_grilla_carga_articulos` en `mpr/services_maquina_linea.py`.
Los artículos vigentes incluyen **TALLES** y **COLOR** desde campos especiales
(`articulo_ce` / `articulo_val_ce`, resueltos por caption, no por id fijo).

### Planilla Control de Calidad (impresión)

Botón único **Imprimir Control de Calidad** en el encabezado de la pantalla.
Genera una hoja **A4 horizontal** pensada para completar a mano:

- Título: `CONTROL DE CALIDAD — {día} {dd/MM/yyyy}` (día en español).
- Columnas: MÁQUINA | DETALLE (ARTÍCULO · COLOR · TALLE) | TURNO MAÑANA (1ra·2da) |
  TURNO TARDE (1ra·2da) | TURNO NOCHE (1ra·2da) | OBSERVACIONES.
- Anchos de impresión: las columnas **1ra/2da** de turnos son amplias (escritura a mano);
  **ARTÍCULO** cede espacio y hace wrap si hace falta.
- Filas: **solo lo visible en pantalla** (filtro de línea GET + búsqueda de máquina).
  Si filtrás una sola máquina, la planilla imprime únicamente esa fila/artículos.
- Turnos y observaciones en blanco.
- Si no hay filas imprimibles, **modal Synap** (no `alert` nativo del navegador).
- El encabezado de la hoja puede mostrar el filtro activo (línea / búsqueda).

Origen de COLOR/TALLES: ver [ARTICULO_CE_TALLES_COLOR.md](ARTICULO_CE_TALLES_COLOR.md).
Ver también [TRAZABILIDAD_MAQUINA_LINEA_OPERARIO.md](TRAZABILIDAD_MAQUINA_LINEA_OPERARIO.md#urls).
