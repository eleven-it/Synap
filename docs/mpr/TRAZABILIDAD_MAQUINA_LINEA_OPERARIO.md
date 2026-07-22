# Trazabilidad de producción por Máquina / Línea / Operario — MPR

**Change:** `mpr-trazabilidad-maquina-linea-operario`
**Fecha:** 08/07/2026
**Estado:** Implementado

> Incorpora al MPR la dimensión física de planta que antes no existía: **máquinas**
> agrupadas por **líneas**, con **operarios** que cargan su producción por máquina desde
> el **móvil** al fin de turno, y un **supervisor** que revisa, concilia desvíos (**gap**)
> y **aprueba**. La aprobación es el evento que envía el stock al depósito **«Producción»**.
>
> Dominio Best Sox: **1 docena = 12 pares**. La captura móvil es en docenas + pares
> sueltos; la persistencia es en **pares**.

> **Persistencia MySQL «fuente única»:** todas las tablas nuevas viven en MySQL por empresa
> (una BD = una empresa), **sin** columna `base_empresa` (el tenancy es la BD conectada).
> Nombres en snake_case con separador `_` (estándar AdministraNET). Se crean vía el catálogo
> central `core/services/legacy_mysql_schema/catalog.py` (proveedor
> `mpr_maquina_linea_trazabilidad`). Ver §[Migración de esquema](#migración-de-esquema).

---

## Índice

1. [Circuito completo (resumen)](#circuito-completo)
2. [Modelo de datos](#modelo-de-datos)
3. [Versionado por vigencias](#versionado-por-vigencias)
4. [Mapeo operario ↔ usuario](#mapeo-operario-usuario)
5. [Línea habitual + override de roster](#línea-habitual--override-de-roster)
6. [Flujo de dos etapas (declaración → aprobación)](#flujo-de-dos-etapas)
7. [Permisos y menú](#permisos-y-menú)
8. [URLs](#urls)
9. [Migración de esquema](#migración-de-esquema)

---

## Circuito completo (resumen) {#circuito-completo}

```
Operario (móvil)                Sistema                         Supervisor (escritorio)
    │  login (usuarios)  ──────► resolver_operario_por_usuario
    │  abre /mpr/mi-parte ─────► contexto automático (operario/línea/turno/fecha)
    │  ingresa doc/pares ─────► registrar_parte_movil → mpr_parte(pendiente)  [SIN stock]
                                                                   │  abre bandeja pendientes
                                                                   │  revisa/corrige (gap+motivo)
                                                                   │  aprueba el parte completo
                                 aprobar_parte_produccion  ◄───────┤
                                 valida cupo (sobre aprobada)
                                 asiento físico → stock_deposito(«Producción») sube
                                 mpr_parte(aprobado, supervisor, ts)
```

El **parte directo del supervisor** (`registrar_parte_produccion`) sigue disponible y
**conserva el comportamiento actual**: nace `aprobado` / `directo_supervisor` y mueve stock
en el acto (ver [PARTE_PRODUCCION.md](PARTE_PRODUCCION.md)).

El detalle operativo de la carga móvil y de la pantalla de aprobación está documentado en
**[CARGA_MOVIL_OPERARIO.md](CARGA_MOVIL_OPERARIO.md)** (grilla, contexto automático, borrador
vs. envío, bandeja y detalle de aprobación). Este documento describe el **circuito y el modelo
de datos**; no duplica ese detalle.

---

## Modelo de datos {#modelo-de-datos}

### Tablas nuevas (MySQL, snake_case)

DDL: `mpr/sql/003_mpr_maquina_linea_tables.sql` (`CREATE TABLE IF NOT EXISTS`, idempotente).
PK internas con prefijo `id_mpr_<tabla>`.

| Tabla | Propósito | Columnas clave |
|-------|-----------|----------------|
| `mpr_linea` | Catálogo de líneas de producción | `id_mpr_linea`, `nombre` (único por BD), `activo`, `creado_en` |
| `mpr_maquina` | Catálogo de máquinas | `id_mpr_maquina`, `codigo` (único, ej. `M-001`), `nombre`, `activo`, `creado_en` |
| `mpr_maquina_linea` | Pertenencia **versionada** máquina→línea | `id_mpr_maquina`, `id_mpr_linea`, `vigencia_desde`, `vigencia_hasta` (NULL = vigente) |
| `mpr_maquina_articulo` | Habilitación **versionada** máquina→artículo | `id_mpr_maquina`, `id_articulo`, `vigencia_desde`, `vigencia_hasta` (NULL = vigente) |
| `mpr_operario_linea` | Línea **habitual** del operario (versionada) | `id_operario` (FK lógica `sue_abm_empleado`), `id_mpr_linea`, `vigencia_desde`, `vigencia_hasta` |
| `mpr_operario_usuario` | Mapeo operario ↔ usuario de login | `id_operario`, `id_usuario` (FK lógica `usuarios`), `activo`; `UNIQUE (id_usuario)` |

> **Invariante (servicio, no solo DDL):** a lo sumo **una** fila vigente por máquina en
> `mpr_maquina_linea`; en `mpr_maquina_articulo` pueden coexistir varias vigentes por máquina
> (distinto artículo). Reasignar o deshabilitar **cierra** la vigencia previa antes de insertar
> la nueva, dentro de la misma transacción.

### Extensiones al ledger existente

DDL: `mpr/sql/004_mpr_parte_maquina_gap.sql` (aplicado de forma idempotente por el proveedor,
que usa `columna_existe` / `indice_existe` / `nombre_tabla_real`).

**`mpr_parte` (cabecera del parte) — columnas nuevas:**

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `estado` | `VARCHAR(12)` NOT NULL DEFAULT `'aprobado'` | `borrador` \| `pendiente` \| `aprobado` (backfill de históricos a `aprobado`) |
| `origen` | `VARCHAR(20)` NOT NULL DEFAULT `'directo_supervisor'` | `movil_operario` \| `directo_supervisor` |
| `id_usuario_supervisor` | `INT` NULL | Supervisor que aprobó |
| `aprobado_en` | `DATETIME` NULL | Timestamp de aprobación |

Índice nuevo: `idx_mpr_parte_estado (estado)`.

**`mpr_parte_linea` (detalle por línea) — columnas nuevas:**

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id_mpr_maquina` | `BIGINT` NULL | FK lógica `mpr_maquina.id_mpr_maquina` |
| `maquina_nombre` | `VARCHAR(100)` NULL | Snapshot del código/nombre de la máquina |
| `cantidad_declarada` | `DECIMAL(15,2)` NOT NULL DEFAULT 0 | Declarada por el operario (pares) |
| `cantidad_aprobada` | `DECIMAL(15,2)` NULL | Aprobada por el supervisor (pares) |
| `gap` | `DECIMAL(15,2)` NOT NULL DEFAULT 0 | `cantidad_aprobada − cantidad_declarada` |
| `motivo` | `VARCHAR(255)` NULL | Obligatorio si `gap != 0` |

- **Unicidad:** pasa de `uk_mpr_parte_linea` a
  **`uk_mpr_parte_linea_maq (id_mpr_parte, id_articulo, id_operario, id_mpr_maquina)`**
  (una fila por parte × artículo × operario × máquina). El proveedor crea antes un índice
  de respaldo `idx_mpr_pl_parte (id_mpr_parte)` para poder reemplazar la unique key que
  usaba la FK a `mpr_parte`.
- **Backfill legacy:** para líneas previas se copia `cantidad_declarada = cantidad_aprobada = cantidad`.
- **Compatibilidad:** la columna histórica `cantidad` se conserva; en partes nuevos
  `cantidad == cantidad_aprobada`. Los partes previos sin `estado` se leen como
  `aprobado` / `directo_supervisor`.

**`mpr_roster_dia` — columna nueva:**

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id_mpr_linea` | `BIGINT` NULL | Override de línea del día; NULL = usar la línea habitual |

---

## Versionado por vigencias {#versionado-por-vigencias}

Las pertenencias y habilitaciones no se borran ni se pisan: se **versionan** con el par
`vigencia_desde` / `vigencia_hasta` (patrón `NULL = vigente`).

- Consultar «qué estaba vigente a la fecha X» es directo e indexable
  (`KEY (id_mpr_maquina, vigencia_hasta)`, `KEY (id_mpr_linea, vigencia_hasta)`,
  `KEY (id_operario, vigencia_hasta)`).
- Al **reasignar** una máquina a otra línea, **deshabilitar** un artículo de una máquina o
  **cambiar** la línea habitual de un operario, el servicio **cierra** la fila vigente
  (`vigencia_hasta = fecha de corte`, típicamente hoy) e **inserta** la nueva en la misma
  transacción cuando corresponde. **No hay cierre automático diario** de habilitaciones:
  la vigencia es dinámica hasta que el supervisor deshabilita explícitamente (con
  confirmación en la UI de carga).
- `mpr_maquina_linea`: a lo sumo una vigente por máquina. `mpr_maquina_articulo`: varias
  vigentes por máquina (una por artículo habilitado).

Esto habilita el **histórico**: qué artículo estuvo seteado en cada máquina y a qué línea
perteneció cada máquina en cualquier fecha pasada.

---

## Mapeo operario ↔ usuario {#mapeo-operario-usuario}

El operario de planta (empleado en `sue_abm_empleado`) y el usuario de login (`usuarios` de
AdministraNET) son entidades distintas. `mpr_operario_usuario` las vincula:

- `id_operario` → `sue_abm_empleado.id_sue_abm_empleado`.
- `id_usuario` → `usuarios.id_usuario`.
- `UNIQUE (id_usuario)`: un usuario resuelve a lo sumo **un** operario.

Tras el login, el sistema resuelve el `id_operario` del usuario autenticado
(`resolver_operario_por_usuario`) y lo usa como identidad del operario en toda la carga móvil.
Un usuario sin mapeo **no** puede cargar parte (borde `sin_operario`).

Administración del mapeo: `/mpr/operarios-usuarios/` (permiso `mpr.ver`).

---

## Línea habitual + override de roster {#línea-habitual--override-de-roster}

Cada operario tiene una **línea habitual** versionada en `mpr_operario_linea`. Para un día
puntual (rotación, refuerzo) se puede fijar un **override** en el roster:
`mpr_roster_dia.id_mpr_linea`.

Resolución de la línea del operario para una fecha/turno (`resolver_linea_operario`):

```
resolver_linea_operario(id_operario, fecha, id_turno):
    override = mpr_roster_dia(fecha, id_operario).id_mpr_linea
    return override or mpr_operario_linea.vigente(id_operario, fecha).id_mpr_linea
```

Regla: **override > habitual**. Si el roster del día trae `id_mpr_linea`, manda; si es NULL,
se usa la línea habitual vigente a esa fecha. Ver
[TURNOS_Y_ROSTER.md](TURNOS_Y_ROSTER.md#override-de-línea-por-día).

Con la línea resuelta, la grilla móvil (`construir_grilla_carga_movil`) lista las **máquinas
vigentes** de esa línea y, por máquina, los **artículos habilitados vigentes** a la fecha.

---

## Flujo de dos etapas (declaración → aprobación) {#flujo-de-dos-etapas}

### Etapa 1 — Declaración móvil (no mueve stock)

`registrar_parte_movil(...)` (`mpr/services_parte_movil.py` →
`crear_o_actualizar_parte_movil` en `mpr/repositories/parte_movil.py`):

- Crea/reutiliza el parte editable del usuario para fecha + turno con
  `estado = 'pendiente'` (o `'borrador'`), `origen = 'movil_operario'`,
  `movimiento_fisico_ok = 0`.
- Por cada (máquina, artículo) con carga > 0 inserta `mpr_parte_linea` con:
  `id_mpr_maquina` + `maquina_nombre` (snapshot), `id_operario` + `operario_nombre`,
  `cantidad_declarada = docenas × 12 + pares`, `cantidad = 0`, `gap = 0`,
  `cantidad_aprobada = NULL`.
- **No** ejecuta asiento físico ni toca `stock_deposito`. Carga libre (sin validación de cupo).
- Los partes `pendiente` guardan `cantidad = 0`, por lo que **no** contaminan los acumulados
  basados en `mpr_parte_linea.cantidad` (OPP acumulado, cupo).

### Etapa 2 — Aprobación del supervisor (mueve stock)

`aprobar_parte_produccion(base, id_parte, correcciones, id_usuario_supervisor, forzar_cupo)`
(`mpr/services.py`):

- Por línea: fija `cantidad_aprobada` (default = declarada), `gap = aprobada − declarada`,
  `motivo` **obligatorio si `gap != 0`**; sincroniza `cantidad = cantidad_aprobada`.
- Valida cupo Fabricando + techo de envíos sobre lo aprobado (`validar_cupo_parte`, extraída
  para reutilizarse tanto aquí como en el parte directo); bloquea salvo `forzar_cupo=True`.
- Ejecuta el **asiento físico** al depósito «Producción» reutilizando el asiento OPP
  (`_registrar_asiento_fisico_opp_parte`, `ya_componentes=True`).
- Cierra el parte: `estado = 'aprobado'`, `id_usuario_supervisor`, `aprobado_en`,
  `movimiento_fisico_ok = 1`. **Idempotente**: reaprobar un parte ya aprobado no duplica stock.

### Parte directo del supervisor (sin cambios)

`registrar_parte_produccion` se conserva: nace `estado = 'aprobado'`,
`origen = 'directo_supervisor'` (defaults del ALTER) y mueve stock en el acto. Ver
[PARTE_PRODUCCION.md](PARTE_PRODUCCION.md#flujo-de-dos-etapas).

---

## Permisos y menú {#permisos-y-menú}

Permisos nuevos (en `core/constantes_permisos.py`, módulo «Producción (MPR)»):

| Permiso | Descripción | Rol típico |
|---------|-------------|------------|
| `mpr.parte_operario` | Cargar parte de producción desde el móvil (solo su línea/turno) | **Operario** |
| `mpr.maquinas_lineas` | Gestionar catálogos máquina/línea y habilitación de artículos | Supervisor MPR |
| `mpr.aprobar_parte` | Revisar y aprobar partes pendientes (mueve stock) | Supervisor MPR |

**Separación de roles:** el operario «puro» tiene **solo** `mpr.parte_operario` y **NO**
`mpr.ver`. Como el mega-menú MPR y las pantallas de escritorio exigen `mpr.ver` (o los
permisos de supervisor), el operario no puede ver ni navegar nada más que su carga; el permiso
es la barrera real (backend), no se apoya en ocultar UI. Tras el login, el operario puro
aterriza directamente en `/mpr/mi-parte/`.

**Menú (supervisor):** los items nuevos se agregan al bloque MPR de `APPS_MENU`, filtrados por
permiso (el operario no los ve):

| Sección | Item | Permiso |
|---------|------|---------|
| Producción diaria | Partes pendientes (aprobación) | `mpr.aprobar_parte` |
| Configuración | Líneas de producción | `mpr.maquinas_lineas` |
| Configuración | Máquinas | `mpr.maquinas_lineas` |
| Configuración | Artículos por máquina | `mpr.maquinas_lineas` |
| Configuración | Mapeo operario ↔ usuario | `mpr.ver` |

---

## URLs {#urls}

| URL | Uso | Permiso |
|-----|-----|---------|
| `/mpr/mi-parte/` | Carga móvil del operario (landing del operario puro) | `mpr.parte_operario` |
| `/mpr/partes-pendientes/` | Bandeja de partes pendientes de aprobación | `mpr.aprobar_parte` |
| `/mpr/partes-pendientes/<id>/` | Detalle de aprobación (declarada/aprobada/gap/motivo) | `mpr.aprobar_parte` |
| `/mpr/lineas/` | CRUD de líneas de producción | `mpr.maquinas_lineas` |
| `/mpr/maquinas/` | CRUD de máquinas y asignación máquina↔línea | `mpr.maquinas_lineas` |
| `/mpr/maquinas/carga-articulos/` | Asignar artículo a máquina (grilla) | `mpr.maquinas_lineas` |
| `/mpr/maquinas/<id>/articulos/` | Histórico y detalle de artículos por máquina | `mpr.maquinas_lineas` |
| `/mpr/maquinas/api/articulos/buscar/` | API JSON búsqueda predictiva (solo `tipo_art_fab = Fabricado`) | `mpr.maquinas_lineas` |
| `/mpr/maquinas/api/articulos/accion/` | API JSON habilitar/deshabilitar artículo en máquina | `mpr.maquinas_lineas` |
| `/mpr/operarios-usuarios/` | Mapeo operario ↔ usuario de login | `mpr.ver` |
| `/mpr/operarios-lineas/` | Línea habitual por operario | `mpr.maquinas_lineas` |

El listado de `/mpr/maquinas/` (y el de máquinas por línea) ordena por `codigo`
en sentido **numérico ascendente** (`CAST(codigo AS UNSIGNED) ASC`).

La pantalla **`/mpr/maquinas/carga-articulos/`** concentra la carga operativa en grilla
(filtro opcional `?id_linea=`); la ruta **`/mpr/maquinas/<id>/articulos/`** queda para
consulta histórica por máquina. La búsqueda de artículos para habilitar filtra solo
artículos con `tipo_art_fab = 'Fabricado'` (normalizado con `TRIM`/`COALESCE`).
Incluye botón **Imprimir Control de Calidad** (planilla A4 horizontal filtrada por lo
visible en pantalla: máquina / línea; modal Synap con selector de fecha; aviso Synap si
no hay filas). Columnas: máquina, artículo, color, talle, turnos mañana/tarde/noche
1ra·2da (ancho generoso para escritura a mano; **1ra precargada** desde partes del día
en fila producción; fila CC vacía por artículo), observaciones (persistente por máquina en
`mpr_maquina.observacion_planilla`, API `maquina_observacion_planilla_api` y
`maquina_planilla_control_calidad_api`). Artículos
ordenados por antigüedad de asignación. Operadores de turno en MAYÚSCULAS (temporales,
solo impresión). Color y talle salen de `articulo_val_ce` según
captions `COLOR` / `TALLES` en `articulo_ce` (detalle: [ARTICULO_CE_TALLES_COLOR.md](ARTICULO_CE_TALLES_COLOR.md)).

El detalle de la carga y la aprobación (pantallas, bordes, borrador vs. envío) está en
[CARGA_MOVIL_OPERARIO.md](CARGA_MOVIL_OPERARIO.md).

---

## Migración de esquema {#migración-de-esquema}

- **Proveedor:** `mpr_maquina_linea_trazabilidad` (título UI «MPR — máquina/línea/trazabilidad»),
  función `run_mpr_maquina_linea_mysql`, registrado en `PROVIDER_REGISTRY` de
  `core/services/legacy_mysql_schema/catalog.py`.
- **SQL:** `mpr/sql/003_mpr_maquina_linea_tables.sql` (tablas nuevas, incluye
  `mpr_maquina.observacion_planilla`) y
  `mpr/sql/004_mpr_parte_maquina_gap.sql` (ALTERs a `mpr_parte`, `mpr_parte_linea`,
  `mpr_roster_dia`). El `003_*` se ejecuta tal cual (`CREATE TABLE IF NOT EXISTS`); el `004_*`
  documenta el DDL, cuya aplicación idempotente vive en `catalog.py`.
- **Idempotente:** helpers `columna_existe` / `indice_existe` / `nombre_tabla_real`; segura de
  ejecutar varias veces.
- **Ejecución:**
  - UI: **Archivo → Parámetros → Migración esquema MySQL (legacy)** → «MPR — máquina/línea/trazabilidad».
  - CLI: `docker exec Synap_app python manage.py apply_mpr_maquina_linea <base_empresa>`.

Ver [../general/HERRAMIENTA_GLOBAL_MIGRACION_ESQUEMA_MYSQL.md](../general/HERRAMIENTA_GLOBAL_MIGRACION_ESQUEMA_MYSQL.md).

---

_Change SDD `mpr-trazabilidad-maquina-linea-operario` (08/07/2026)._
_Relacionado: [CARGA_MOVIL_OPERARIO.md](CARGA_MOVIL_OPERARIO.md), [PARTE_PRODUCCION.md](PARTE_PRODUCCION.md), [TURNOS_Y_ROSTER.md](TURNOS_Y_ROSTER.md)._
