# Exploración — Trazabilidad MPR por Máquina / Línea / Operario

**Change:** `mpr-trazabilidad-maquina-linea-operario`
**Fecha:** 08/07/2026
**Estado:** Exploración (base para propose/spec/design/tasks)
**Modo persistencia:** openspec

> **Estándar de nombres:** todas las tablas nuevas en MySQL AdministraNET usan separador `_` (snake_case), p. ej. `mpr_linea`, `mpr_maquina`, `mpr_maquina_linea`, `mpr_maquina_articulo`, `mpr_operario_linea`.

---

## 1. Necesidad de negocio (fábrica de medias — Best Sox)

La fábrica tiene ~100 máquinas de producción agrupadas por **líneas**; cada línea se asigna a un **operario**. Cada máquina produce artículos configurados con insumos (hilos, etc.). Se requiere:

1. Asignar a cada máquina los **artículos que puede fabricar**, con **histórico de fechas** de seteo (trazabilidad).
2. Que cada **operario** cargue, desde su **dispositivo móvil** al fin de turno, la producción **por máquina** (docenas / pares), viendo solo los artículos habilitados de las máquinas de **su línea** y turno.
3. Que el **supervisor** levante esos partes, los controle, **corrija desvíos (gap)** y **apruebe**. La **aprobación** es la que envía el stock al depósito **"Producción"** del pipeline.

`1 unidad = 1 par`, `1 docena = 12 pares` (dominio Best Sox).

---

## 2. Estado actual del código (app `mpr`)

### 2.1 Parte de producción (hoy)
- Vista `/mpr/parte-produccion/` → `registrar_parte_produccion` (`mpr/services.py`), grilla **componente × operario** por **fecha + turno**.
- Al **guardar**, mueve stock **de inmediato**: `_registrar_asiento_fisico_opp_parte(..., ya_componentes=True)` sube `stock_deposito` del depósito **"Producción"**. Ledger `mpr_parte` / `mpr_parte_linea` (MySQL).
- **No hay estado ni aprobación**: lo cargado es stock real.
- Validaciones fuertes de cupo **Fabricando** (contra `mpr_envio_produccion`) — hoy siempre activas.

### 2.2 Turnos y roster (ya existe — base a reutilizar)
- `MprTurno` (`mpr/models.py`): nombre, hora_inicio, hora_fin (soporta nocturno), activo, por `base_empresa`.
- `MprRosterDia`: `(base_empresa, fecha, id_operario)` único → FK `MprTurno`. Modela **operario ↔ turno ↔ fecha**.
- Persistencia MySQL: `mpr_turno`, `mpr_roster_dia` (línea "MySQL fuente única").

### 2.3 Operarios
- Datos maestros en tabla legacy `sue_abm_empleado` (`id_sue_abm_empleado`, `nombre_empleado`, `id_cliente`, `anulado`). **No** tienen usuario de login.
- CRUD en `mpr/services.py` (`listar_operarios_crud`, `crear_operario`, etc.) y vistas `/mpr/operarios/...`.

### 2.4 Login / roles
- Autenticación contra tabla `usuarios` de AdministraNET (`login/administranet_auth.py`, `validate_user`); dict `user` en sesión (no modelo Django). Password AES; trae `id_puesto`, `id_sucursal`, `id_deposito`.
- Permisos MPR: `_usuario_tiene_permiso_mpr` (`mpr/views.py`); supervisor = `cod_usuario == "supervisor"` o rol administrador. Mixins `MprLoginRequiredMixin`, `MprPermisoMixin`.
- Esquema permisos Synap: `core/services/synap_permisos_seed`.

### 2.5 Depósito "Producción"
- No hardcodeado: `deposito.tipo_mpr = "Produccion"`; resolver `get_deposito_produccion_mpr` (`mpr/services.py`). Config en `/mpr/config-depositos/`.

### 2.6 Artículos / BOM / insumos
- Artículo = tabla `articulo` (código UI = `id_manual`). BOM: `en_abm` (cabecera) + `en_abm_formula` (componentes/insumos, incluye hilos).
- Insumos NO entran en alcance de este change (solo ingreso de producción terminada).

### 2.7 Mobile
- `core/utils/template_selector.get_template_for_device` + PWA. Las vistas MPR hoy usan templates fijos → la UI móvil de captura es trabajo nuevo.

### 2.8 Persistencia de esquema legacy
- Regla del repo: DDL nuevo vía catálogo central `core/services/legacy_mysql_schema/catalog.py` (+ SQL runtime en `mpr/sql/`). Único proveedor MPR actual: `mpr_deposito_articulo`.

### 2.9 GAP crítico
- **No existe** ningún concepto de **máquina** ni **línea** (ni modelos Synap ni tablas legacy). Es lo nuevo a modelar.
- **No existe** flujo de aprobación de dos etapas.

---

## 3. Decisiones confirmadas con el usuario (contrato)

1. **Login operario:** crear usuario en tabla `usuarios` de AdministraNET por operario, **mapeado** a `sue_abm_empleado` (reusa el login actual).
2. **Coexistencia de flujos:** el supervisor puede cargar parte **directo** (como hoy) y/o el operario carga por **móvil** en **borrador** hasta la **revisión/aprobación** del supervisor. Requiere **rol Supervisor MPR** explícito.
3. **Máquina ↔ línea VERSIONADA** con histórico de fechas.
4. **Un operario por línea por turno** (ve todas las máquinas de su línea).
5. **Operario ↔ línea MIXTA:** línea habitual por operario + **override por día/turno** integrado al roster existente.
6. **Máquina ↔ artículo:** **varios artículos habilitados a la vez** por máquina; el operario elige cuál/cuáles cargó; **histórico de vigencia** por artículo.
7. **Cupo Fabricando:** carga del operario **libre** (producción real, sin tope); el control/validación se hace en la **aprobación** del supervisor.
8. **Aprobación del parte COMPLETO de una vez**, pero se guarda **línea por línea**: `cantidad_declarada`, `cantidad_aprobada`, `gap`, `motivo`.
9. **Insumos/hilos fuera de alcance**: la aprobación solo ingresa producción terminada al depósito "Producción" (sin consumo BOM).
10. **Habilitación máquina→artículo a nivel máquina** (no depende del turno); el turno es solo contexto del operario para atribuir la carga.
11. **Persistencia** en MySQL legacy vía catálogo central `catalog.py` (línea "MySQL fuente única").

---

## 4. Modelo de datos propuesto (alto nivel — snake_case)

| Tabla nueva | Propósito | Notas |
|---|---|---|
| `mpr_linea` | Catálogo de líneas | `base_empresa`, `nombre`, `activo` |
| `mpr_maquina` | Catálogo de máquinas | `base_empresa`, `codigo`/`nombre`, `activo` |
| `mpr_maquina_linea` | Pertenencia máquina→línea **versionada** | `id_maquina`, `id_linea`, `vigencia_desde`, `vigencia_hasta` (NULL = vigente) |
| `mpr_maquina_articulo` | Habilitación máquina→artículo **versionada** | `id_maquina`, `id_articulo`, `vigencia_desde`, `vigencia_hasta` |
| `mpr_operario_linea` | Línea habitual por operario | `id_operario`, `id_linea` (+ override en roster) |
| `mpr_operario_usuario` (o campo en mapa) | Mapeo operario↔usuario login | `id_operario` ↔ `id_usuario`/`cod_usuario` |

**Extensiones de ledger existente:**
- `mpr_parte`: `estado` (`borrador`/`pendiente`/`aprobado`), auditoría de aprobación (`id_usuario_supervisor`, `aprobado_en`), `origen` (`movil_operario`/`directo_supervisor`).
- `mpr_parte_linea`: `id_maquina` (+ snapshot nombre), `cantidad_declarada`, `cantidad_aprobada`, `gap`, `motivo`.
- `mpr_roster_dia`: `id_linea` override (opcional por día/turno).

---

## 5. Riesgos / pendientes operativos
- Carga libre + stock en aprobación puede dejar stock en "Producción" no respaldado por `mpr_envio_produccion` (desvío descrito en `docs/mpr/PARTE_PRODUCCION.md`) → conviene reporte de conciliación envíos↔producción.
- Proceso de alta/baja de usuarios de operario en `usuarios` (AES, `id_puesto`, sucursal) y su mapeo.
- UI móvil nueva sobre vistas MPR (hoy templates fijos).

---

## 6. Antecedentes / docs relevantes
- `docs/mpr/PARTE_PRODUCCION.md`, `docs/mpr/TURNOS_Y_ROSTER.md`, `docs/mpr/GLOSARIO_MPR.md`.
- `docs/mpr/PLAN_REPORTE_POR_OPERARIO_TEJEDOR_Y_CONTINUIDAD_HISTORICA.md` (fact_produccion, mapa tejedor).
- `docs/mpr/BEST_SOX_*`, `docs/general/HERRAMIENTA_GLOBAL_MIGRACION_ESQUEMA_MYSQL.md`.
- Change previo análogo: `openspec/changes/mpr-docenas-clasificacion-operario/`.
