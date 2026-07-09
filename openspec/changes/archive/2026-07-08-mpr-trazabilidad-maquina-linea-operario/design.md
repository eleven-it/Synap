# Diseño — Trazabilidad MPR por Máquina / Línea / Operario

**Change:** `mpr-trazabilidad-maquina-linea-operario`
**Fecha:** 08/07/2026
**Proposal:** [proposal.md](./proposal.md) · **Specs:** [specs/](./specs/) · **Exploración:** [exploration.md](./exploration.md)

---

## 1. Contexto y restricciones

- **Persistencia MySQL "fuente única":** los ledgers MPR viven en MySQL por empresa (una BD = una empresa), creados vía `core/services/legacy_mysql_schema/catalog.py` (proveedor `mpr_core_tables` → `mpr/sql/001_mpr_core_tables.sql`) **sin** columna `base_empresa`. Existen además modelos Django espejo en `mpr/models.py` (Postgres) durante la transición (`mpr-mysql-fuente-unica`). **Este change sigue la misma convención**: DDL nuevo en `mpr/sql/` + proveedor en `catalog.py`; los modelos Django se extienden solo si el flujo de ese código los usa.
- **Nombres:** todas las tablas/columnas nuevas en snake_case con separador `_` (estándar AdministraNET).
- **Tipos AdministraNET:** normalizar con `core.utils.administranet_types` (`to_int_or_none`, `to_date_or_none`, `str_or_default`, `to_decimal_or_none`) al leer/escribir MySQL.
- **Depósito destino:** `deposito.tipo_mpr='Produccion'`, resuelto por `get_deposito_produccion_mpr` (`mpr/services.py`).
- **UI canónica:** reportes `/reports/dashboard/<slug>/` y MPR `/mpr/wizard/`, `/mpr/opt/...`; móvil vía `core/utils/template_selector.get_template_for_device` + `mpr/templates/mpr/mobile/`.

---

## 2. Modelo de datos

### 2.1 Tablas nuevas (MySQL, snake_case)

```
mpr_linea
  id_linea            INT PK AUTO_INCREMENT
  nombre              VARCHAR(100)  -- único por BD (empresa)
  activo              TINYINT(1) DEFAULT 1
  creado_en           DATETIME

mpr_maquina
  id_maquina          INT PK AUTO_INCREMENT
  codigo              VARCHAR(50)   -- único por BD (identificador visible, ej. M-001)
  nombre              VARCHAR(100) NULL
  activo              TINYINT(1) DEFAULT 1
  creado_en           DATETIME

mpr_maquina_linea            -- pertenencia versionada
  id_maquina_linea    INT PK AUTO_INCREMENT
  id_maquina          INT
  id_linea            INT
  vigencia_desde      DATE
  vigencia_hasta      DATE NULL    -- NULL = vigente
  creado_en           DATETIME
  INDEX (id_maquina, vigencia_hasta), INDEX (id_linea, vigencia_hasta)

mpr_maquina_articulo         -- habilitación versionada (varios activos)
  id_maquina_articulo INT PK AUTO_INCREMENT
  id_maquina          INT
  id_articulo         INT
  vigencia_desde      DATE
  vigencia_hasta      DATE NULL
  creado_en           DATETIME
  INDEX (id_maquina, vigencia_hasta)

mpr_operario_linea           -- línea habitual del operario
  id_operario_linea   INT PK AUTO_INCREMENT
  id_operario         INT          -- sue_abm_empleado.id_sue_abm_empleado
  id_linea            INT
  vigencia_desde      DATE
  vigencia_hasta      DATE NULL
  INDEX (id_operario, vigencia_hasta)

mpr_operario_usuario         -- mapeo operario <-> usuario login
  id_operario_usuario INT PK AUTO_INCREMENT
  id_operario         INT          -- sue_abm_empleado.id_sue_abm_empleado
  id_usuario          INT          -- usuarios.id_usuario (AdministraNET)
  activo              TINYINT(1) DEFAULT 1
  UNIQUE (id_usuario) WHERE activo  -- un usuario resuelve a lo sumo un operario
```

> Regla de invariante (servicio, no solo DDL): a lo sumo **una** fila vigente por máquina en `mpr_maquina_linea`; en `mpr_maquina_articulo` pueden coexistir varias vigentes por máquina (distinto artículo). Reasignar/deshabilitar **cierra** la vigencia previa (`vigencia_hasta = hoy − regla de corte`).

### 2.2 Extensiones a ledger existente

```
mpr_parte  (+)
  estado                VARCHAR(12)  -- 'borrador' | 'pendiente' | 'aprobado'  (default 'aprobado' backfill)
  origen                VARCHAR(20)  -- 'movil_operario' | 'directo_supervisor'
  id_usuario_supervisor INT NULL
  aprobado_en           DATETIME NULL

mpr_parte_linea  (+)
  id_maquina            INT NULL
  maquina_nombre        VARCHAR(100) NULL     -- snapshot
  cantidad_declarada    DECIMAL(15,2)         -- operario
  cantidad_aprobada     DECIMAL(15,2) NULL    -- supervisor
  gap                   DECIMAL(15,2) DEFAULT 0
  motivo                VARCHAR(255) NULL

mpr_roster_dia  (+)
  id_linea              INT NULL              -- override; NULL = usar habitual
```

- **Compatibilidad:** la columna `cantidad` histórica se conserva; para partes nuevos `cantidad == cantidad_aprobada`. Partes previos sin `estado` se leen como `aprobado`/`directo_supervisor` (backfill por defecto en el ALTER o en lectura).

### 2.3 Migración de esquema

- Nuevos SQL en `mpr/sql/`: `003_mpr_maquina_linea_tables.sql` (tablas nuevas) y `004_mpr_parte_maquina_gap.sql` (ALTERs a `mpr_parte`, `mpr_parte_linea`, `mpr_roster_dia`).
- Nuevo proveedor en `PROVIDER_REGISTRY` de `catalog.py`, p. ej. `mpr_maquina_linea_trazabilidad` (`run_mpr_maquina_linea_mysql`), idempotente (usar helpers `columna_existe`, `indice_existe`, `nombre_tabla_real`).
- Si se mantiene el espejo Django, migración en `mpr/migrations/` con `SYNAP_MIGRATIONS_POSTGRES_ONLY=1`.

---

## 3. Arquitectura de servicios (`mpr/services.py` + `mpr/repositories/`)

### 3.1 Catálogos y asignaciones (nuevos servicios)
- `listar_lineas / crear_linea / actualizar_linea / toggle_linea_activo`
- `listar_maquinas / crear_maquina / actualizar_maquina / toggle_maquina_activo`
- `asignar_maquina_linea(id_maquina, id_linea, desde)` → cierra vigencia previa + inserta.
- `habilitar_articulo_maquina(id_maquina, id_articulo, desde)` / `deshabilitar_articulo_maquina(...)`.
- `set_linea_habitual_operario(id_operario, id_linea)`.
- `map_operario_usuario(id_operario, id_usuario)` / `resolver_operario_por_usuario(id_usuario)`.
- Repos nuevos en `mpr/repositories/` (p. ej. `maquina_linea.py`, `maquina_articulo.py`, `operario_usuario.py`).

### 3.2 Resolución de línea del operario
```
resolver_linea_operario(id_operario, fecha, id_turno):
    override = mpr_roster_dia(fecha, id_operario).id_linea
    return override or mpr_operario_linea.vigente(id_operario, fecha).id_linea
```

### 3.3 Grilla de carga móvil
- `construir_grilla_carga_movil(id_operario, fecha, id_turno)`:
  1. `id_linea = resolver_linea_operario(...)`.
  2. Máquinas vigentes de la línea (`mpr_maquina_linea` vigente a `fecha`).
  3. Por máquina, artículos con `mpr_maquina_articulo` vigente a `fecha`.
  4. Devuelve filas (máquina × artículo) con inputs docenas/pares en 0.

### 3.4 Split declaración / aprobación (refactor del parte)
- **Declarar (móvil):** `registrar_parte_movil(...)`:
  - Crea `mpr_parte` con `estado='pendiente'` (o `'borrador'`), `origen='movil_operario'`.
  - `mpr_parte_linea` con `id_maquina`+snapshot, `cantidad_declarada` (pares), `id_operario` = operario logueado.
  - **No** llama al asiento físico. Carga libre (sin validación de cupo).
- **Aprobar (supervisor):** `aprobar_parte_produccion(id_parte, correcciones)`:
  - Setea `cantidad_aprobada`, `gap`, `motivo` por línea (motivo obligatorio si `gap != 0`).
  - Ejecuta validación de cupo Fabricando/techo envíos sobre `cantidad_aprobada` (reutiliza `_validar_parte_contra_cupo_fabricando` / `_validar_parte_contra_techo_envios`, adaptadas a la cantidad aprobada).
  - Llama `_registrar_asiento_fisico_opp_parte(..., ya_componentes=True)` con `cantidad_aprobada`, guarda `estado='aprobado'`, `id_usuario_supervisor`, `aprobado_en`, `movimiento_fisico_ok=True` (idempotente).
- **Parte directo supervisor:** `registrar_parte_produccion` actual se conserva; setea `origen='directo_supervisor'`, nace `aprobado` y mueve stock en el acto (comportamiento vigente).

> **Refactor mínimo:** extraer del `registrar_parte_produccion` actual la parte de "asiento físico + validación" a una función reutilizable que consuma `aprobar_parte_produccion` y el parte directo, evitando duplicar lógica de stock.

---

## 4. Flujo (secuencia)

```
Operario (móvil)                Sistema                         Supervisor (escritorio)
    |  login (usuarios)  ------> resolver_operario_por_usuario
    |  abre carga        ------> construir_grilla_carga_movil (línea/turno/fecha)
    |  ingresa doc/pares ------> registrar_parte_movil -> mpr_parte(pendiente)  [SIN stock]
                                                                   |  abre bandeja pendientes
                                                                   |  revisa/corrige (gap+motivo)
                                                                   |  aprueba parte completo
                                 aprobar_parte_produccion  <-------|
                                 valida cupo (aprobada)
                                 asiento físico -> stock_deposito(Produccion) sube
                                 mpr_parte(aprobado, supervisor, ts)
```

---

## 5. Login, roles y permisos

- **Autenticación:** reutiliza `login/administranet_auth.py` (tabla `usuarios`). Tras login, resolver `id_operario` desde `mpr_operario_usuario` y guardarlo en sesión.
- **Rol Supervisor MPR:** extender `_usuario_tiene_permiso_mpr` (`mpr/views.py`) para reconocer el rol (además de `cod_usuario="supervisor"` / administrador). Alta del rol vía esquema Synap (`core/services/synap_permisos_seed` / `synap_permisos_tables`).
- **Permiso operario:** nuevo permiso p. ej. `mpr.cargar_parte_movil`; mixin que exige operario mapeado. Operario NO accede al tablero (`TableroProduccionView`).

---

## 6. Permisos, landing por rol y acceso restringido del operario

### 6.1 Modelo de permisos (nuevos en `core/constantes_permisos.py` → `PERMISOS_POR_MODULO["Producción (MPR)"]`)

| Permiso | Descripción | Rol típico |
|---|---|---|
| `mpr.ver` (existente) | Ver módulo Producción (MPR) completo (tablero, reportes, config) | Supervisor / Admin |
| `mpr.parte_operario` (**nuevo**) | Cargar parte de producción desde móvil (solo su línea/turno) | **Operario** |
| `mpr.maquinas_lineas` (**nuevo**) | Gestionar catálogos máquina/línea y habilitación de artículos | Supervisor MPR |
| `mpr.aprobar_parte` (**nuevo**) | Revisar y aprobar partes pendientes (mueve stock) | Supervisor MPR |

**Principio de separación:** el operario "puro" tiene **solo** `mpr.parte_operario` y **NO** `mpr.ver`. Como el mega-menú MPR y todas las pantallas de escritorio exigen `mpr.ver` (o los permisos de supervisor), el operario **no puede** ver ni navegar nada más que su carga. No se apoya en ocultar UI: el permiso es la barrera real (backend).

### 6.2 Landing por rol (redirección post-login)

- **Regla:** si el usuario tiene `mpr.parte_operario` y **NO** `mpr.ver` → su "home" es `mpr:parte_movil_operario`.
- **Puntos de intercepción** (los tres, para robustez):
  1. `login/views.py::login_view` (~l.120): resolver destino por permiso antes de `reverse("core:dashboard")`.
  2. `/` en `django_project/urls.py` y `core/views/views_general.py::dashboard_view`: si es operario puro, `redirect` a la pantalla móvil.
  3. Helper único `resolver_landing_usuario(user)` (nuevo, en `core/` o `mpr/`) reutilizado por los tres puntos, para no duplicar la regla.
- El operario que intente abrir cualquier otra URL recibe `PermissionDenied` (falta `mpr.ver`) + el `MobileLevelAOnlyMiddleware` ya acota rutas móviles.

### 6.3 Navbar y experiencia "app dedicada"

- **Operario puro:** sin navbar completo. En móvil, el navbar hoy se filtra por `PWA_MENU_APP_IDS` (`core/pwa_nivel_a.py`) que solo deja TPV; para el operario se sirve la pantalla de carga como **app full-screen** (sin mega-menú), con a lo sumo un header propio (contexto + cerrar sesión). No se agrega MPR a `PWA_MENU_APP_IDS` para el operario (evita exponer otros items).
- **Supervisor:** ve el módulo MPR normal con los items nuevos (§6.5).

### 6.4 Diseño UX — Pantalla móvil de carga (mobile-first)

Contexto de uso: operario en planta, al **fin de turno**, en su teléfono, con prisa y posibles guantes; conectividad Wi-Fi de fábrica variable. Objetivo: **cero configuración**, captura rápida y sin errores.

**Principios**
1. **Contexto automático:** al entrar, el sistema ya resuelve *operario* (login → `mpr_operario_usuario`), *línea* (habitual + override roster), *turno* y *fecha* (hoy). El operario no elige nada de eso; se muestra en un header compacto (editar fecha solo si carga diferida, comportamiento secundario).
2. **Una máquina a la vez, lista escaneable:** la línea puede tener ~25 máquinas → lista de **tarjetas por máquina** con estado (Pendiente / Cargada / Sin producción) y buscador/salto por número de máquina.
3. **Captura grande y tolerante a error:** por artículo, **stepper** de docenas (botones −/+ grandes) + teclado numérico; campo de **pares sueltos** secundario. Objetivos táctiles ≥ 48px, alto contraste.
4. **Total en vivo:** barra fija con total de docenas del parte y progreso ("6/25 máquinas").
5. **Autosave como borrador:** guardado local + servidor por máquina, para sobrevivir cortes de conexión; reanuda donde quedó.
6. **Confirmar antes de enviar:** pantalla de resumen (máquinas cargadas/omitidas, total) → "Enviar parte". Post-envío: estado **"Pendiente de aprobación"**, editable hasta que el supervisor apruebe.

**Arquitectura de pantallas (flujo)**

```
[Login]
   │  (operario puro → landing directa)
   ▼
[Carga de parte]  ← HOME del operario
   ├─ Header contexto: Operario · Línea 3 · Turno Noche · 08/07/2026
   ├─ Barra fija: Total 41 doc · Progreso 6/25 · [Buscar máquina]
   ├─ Lista de máquinas (tarjetas):
   │     M-051  [Sin cargar]  2 artículos habilitados
   │     M-052  [Cargada 12 doc]
   │     ...
   │  (tap en tarjeta → expande)
   │     ▼ M-051
   │        Art. A "Media deportiva"   [– 3 +] doc   [ 5 ] pares
   │        Art. B "Media invisible"   [– 0 +] doc   [ 0 ] pares
   │        [Guardar máquina]
   └─ Bottom bar fija: [Revisar y enviar]
         ▼
[Revisar parte] (resumen por máquina/artículo, total, editar)
         ▼  [Enviar parte]
[Enviado] "Parte pendiente de aprobación · 08/07/2026 22:14"  [Ver / Editar]
```

**Estados y bordes**
- Sin línea asignada / sin turno en roster → mensaje claro y contacto a supervisor (no pantalla vacía).
- Máquina sin artículos habilitados vigentes → tarjeta informativa, no cargable.
- Parte ya enviado del turno → abre en modo lectura con opción "Editar" (mientras esté `pendiente`).
- Envío sin conexión → se encola y reintenta; feedback "Se enviará al recuperar conexión".
- Carga libre (sin tope): nunca bloquea por exceder cupo.

**Componentes** (reutilizando canon UI del repo, Tailwind + Alpine): `machine_card`, `article_row` (stepper docenas + pares), `sticky_totals`, `bottom_action_bar`, `status_chip`, `search_jump`, `toast`. Templates bajo `mpr/templates/mpr/mobile/` servidos por `get_template_for_device`.

**Accesibilidad / planta:** fuentes ≥ 16px, contraste AA, botones grandes, evitar gestos finos, confirmación explícita de envío, sin dependencias de hover.

### 6.5 Escritorio (supervisor)

- **Catálogos:** `/mpr/lineas/`, `/mpr/maquinas/` (CRUD, toggle activo, patrón `operarios_list.html`), asignación máquina↔línea y habilitación máquina↔artículo con histórico de vigencias. Permiso `mpr.maquinas_lineas`.
- **Bandeja de aprobación:** `/mpr/partes-pendientes/` — lista filtrable (fecha/turno/línea), detalle editable con columnas declarada/aprobada/gap/motivo y cupo Fabricando de referencia; acción "Aprobar parte". Permiso `mpr.aprobar_parte`.
- **Mapeo operario↔usuario:** vista de administración del mapeo (permiso supervisor).

### 6.6 Entradas de menú nuevas (`APPS_MENU` en `core/utils/utils.py`)

> Se agregan al bloque `mpr` existente; el operario **no** las ve porque exigen permisos que no posee.

| Sección | Item | `permission` | `menu_item_id` |
|---|---|---|---|
| Producción diaria | Partes pendientes (aprobación) | `mpr.aprobar_parte` | `mpr_prod_partes_pendientes` |
| Configuración | Líneas de producción | `mpr.maquinas_lineas` | `mpr_cfg_lineas` |
| Configuración | Máquinas | `mpr.maquinas_lineas` | `mpr_cfg_maquinas` |
| Configuración | Artículos por máquina | `mpr.maquinas_lineas` | `mpr_cfg_maquina_articulo` |
| Configuración | Mapeo operario↔usuario | `mpr.ver` | `mpr_cfg_operario_usuario` |

La pantalla de carga del operario **no** se agrega al mega-menú (es landing directa). Todas las vistas nuevas usan `MprLoginRequiredMixin` + `MprPermisoMixin` con el permiso correspondiente.

---

## 7. Decisiones de arquitectura (rationale)

| Decisión | Alternativa descartada | Rationale |
|---|---|---|
| Máquina como **dimensión** en `mpr_parte_linea` | Cabecera de parte por máquina | Un parte puede abarcar varias máquinas de la línea; la máquina es atributo de la línea de detalle |
| Versionado por `vigencia_desde/hasta` | Tabla de log de cambios | Consulta puntual "qué estaba vigente a la fecha X" es directa e indexable |
| Split declaración/aprobación reutilizando asiento OPP | Nuevo motor de stock | Minimiza riesgo; el asiento físico ya está probado |
| Carga libre + control en aprobación | Tope en la carga | Refleja producción real; el supervisor concilia |
| Coexistencia parte directo | Reemplazo total | Continuidad operativa ante fallas del móvil |
| MySQL fuente única | Solo Postgres | Alinea con `mpr-mysql-fuente-unica` y estándar AdministraNET |

---

## 8. Riesgos técnicos y mitigaciones

- **Doble motor de stock:** centralizar el asiento en una única función reutilizada por aprobación y parte directo (evita divergencias).
- **Stock no respaldado por envíos:** validación en aprobación + reporte de conciliación (P1). Documentar en `docs/mpr/`.
- **Solapamiento de vigencias:** el servicio cierra la vigencia previa dentro de la misma transacción; test de invariante.
- **Backfill de `estado`:** ALTER con default `aprobado` y lectura tolerante para históricos.
- **DDL sobre BD compartida VB6:** solo tablas/columnas nuevas aditivas; idempotencia con helpers del catálogo.

---

## 9. Plan de pruebas (resumen)

- **Esquema:** proveedor idempotente (doble ejecución sin error).
- **Servicios:** versionado (reasignación cierra vigencia; no dos vigentes), resolución de línea (habitual vs override), grilla móvil (solo artículos vigentes de la línea/turno).
- **Flujo:** parte móvil → `pendiente` sin stock; aprobación → stock sube por `cantidad_aprobada`; gap con motivo obligatorio; idempotencia de aprobación.
- **Regresión:** parte directo del supervisor mueve stock como hoy.
- **Login/rol:** operario sin mapeo bloqueado; operario no aprueba; supervisor aprueba.
- Ejecutar en contenedor: `docker exec Synap_app python manage.py test mpr ...`.

---

## 10. Documentación a actualizar (`docs/mpr/`)
- Nuevo doc del circuito (máquina/línea/operario, flujo dos etapas, gap).
- Actualizar `PARTE_PRODUCCION.md` (estado/origen/asiento diferido) y `TURNOS_Y_ROSTER.md` (override de línea).
- `HERRAMIENTA_GLOBAL_MIGRACION_ESQUEMA_MYSQL.md` (nuevo proveedor).
