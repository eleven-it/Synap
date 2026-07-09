# Tareas — Trazabilidad MPR por Máquina / Línea / Operario

**Change:** `mpr-trazabilidad-maquina-linea-operario`
**Proposal:** [proposal.md](./proposal.md) · **Design:** [design.md](./design.md) · **Specs:** [specs/](./specs/)

> Convención: tablas/columnas nuevas en snake_case; DDL vía `core/services/legacy_mysql_schema/catalog.py` + `mpr/sql/`; tests/manage.py en contenedor (`docker exec Synap_app ...`).

---

## Fase 1 — Esquema y migración (base)

- [x] 1.1 Crear `mpr/sql/003_mpr_maquina_linea_tables.sql`: tablas `mpr_linea`, `mpr_maquina`, `mpr_maquina_linea`, `mpr_maquina_articulo`, `mpr_operario_linea`, `mpr_operario_usuario` (índices y unicidades del diseño §2.1). **Hecho** (PKs `id_mpr_*`).
- [x] 1.2 Crear `mpr/sql/004_mpr_parte_maquina_gap.sql`: ALTERs a `mpr_parte` (`estado`, `origen`, `id_usuario_supervisor`, `aprobado_en`), `mpr_parte_linea` (`id_mpr_maquina`, `maquina_nombre`, `cantidad_declarada`, `cantidad_aprobada`, `gap`, `motivo`), `mpr_roster_dia` (`id_mpr_linea`). Backfill `estado='aprobado'`, `origen='directo_supervisor'` para históricos. **Hecho**.
- [x] 1.3 Añadir proveedor `mpr_maquina_linea_trazabilidad` (`run_mpr_maquina_linea_mysql`) en `catalog.py` + registrarlo en `PROVIDER_REGISTRY`; idempotente (helpers `columna_existe`/`indice_existe`/`nombre_tabla_real`). **Hecho** (incluye backfill de `cantidad_declarada/aprobada` y unicidad con máquina).
- [ ] 1.4 (Si aplica espejo Postgres) migración Django en `mpr/migrations/` para modelos nuevos/campos (`SYNAP_MIGRATIONS_POSTGRES_ONLY=1`). **Decisión (design R2):** N/A por ahora — se lee MySQL vía repositorios (patrón turnos/roster); se agregará solo si alguna vista lo requiere.
- [x] 1.5 Aplicado y verificado en `administranet93` (contenedor `Synap_app`): 6 tablas nuevas + columnas en `mpr_parte`/`mpr_parte_linea`/`mpr_roster_dia` + índices `uk_mpr_parte_linea_maq`/`idx_mpr_pl_parte`. **Idempotencia OK** (2ª corrida sin re-aplicar). Comando: `apply_mpr_maquina_linea <base>`.

## Fase 2 — Catálogos máquina/línea (`mpr-catalogo-maquina-linea`)

- [x] 2.1 Repos `mpr/repositories/maquina_linea.py` (CRUD + vigencias half-open `[desde, hasta)`).
- [x] 2.2 Servicios en `mpr/services_maquina_linea.py`: `listar_lineas/crear_linea/actualizar_linea/toggle_linea_activa`; ídem máquinas; normalizar con `administranet_types`. (Se usó módulo dedicado en lugar de `mpr/services.py` para no engrosar el archivo monolítico; se importa desde vistas.)
- [x] 2.3 Servicio `asignar_maquina_linea` (cierra vigencia previa, invariante 1 vigente por máquina) + `listar_historico_maquina_linea`.
- [x] 2.4 Vistas + URLs `/mpr/lineas/`, `/mpr/maquinas/` (CRUD, toggle, asignación) con `MprLoginRequiredMixin` + `MprPermisoMixin` (`mpr.maquinas_lineas`; supervisor/admin pasan por short-circuit hasta la siembra de Fase 4).
- [x] 2.5 Templates (patrón `turnos_list.html` / toggle activo) + histórico de vigencias en `maquina_form.html`.
- [x] 2.6 Validación en contenedor (`administranet93`): unicidad nombre/código (IntegrityError→mensaje), reasignación cierra vigencia previa, vigencia half-open (hoy=línea previa, mañana=línea nueva), histórico ordenado. Pendiente: suite automatizada en Fase de tests.

## Fase 3 — Habilitación máquina→artículo (`mpr-asignacion-maquina-articulo`)

- [x] 3.1 Repo `mpr/repositories/maquina_articulo.py` (varias vigentes por máquina; vigencia half-open; búsqueda y detalle de artículos desde tabla `articulo`).
- [x] 3.2 Servicios en `mpr/services_maquina_linea.py`: `habilitar_articulo_maquina` / `deshabilitar_articulo_maquina` / `listar_articulos_vigentes_maquina(fecha)` / `historico_maquina_articulo` / `buscar_articulos`.
- [x] 3.3 Vista + URL `/mpr/maquinas/<id>/articulos/` (`MaquinaArticulosView`): buscador por `id_manual`/código/descripción, alta/baja y histórico; enlace desde el listado de máquinas.
- [x] 3.4 Validación en contenedor (`administranet93`): varios artículos vigentes, alta duplicada rechazada, deshabilitar cierra vigencia (y baja repetida rechazada), histórico con `vigencia_hasta`. Pendiente: suite automatizada en Fase de tests.

## Fase 4 — Login operario, permisos, landing y menú (`mpr-operario-login`)

- [x] 4.1 Repo `mpr/repositories/operario_usuario.py` (resolver/map/desmapear/listar_mapeos/listar_usuarios) + servicios `mpr/services_operario.py` (`map_operario_usuario`, `resolver_operario_por_usuario`, etc.).
- [x] 4.2 Integrar en `login/views.py`: tras login se resuelve `id_operario` (si hay mapeo) y se guarda en `session["user"]["id_operario"]` (no crítico si falla).
- [x] 4.3 Permisos nuevos en `PERMISOS_POR_MODULO["Producción (MPR)"]` (`mpr.maquinas_lineas`, `mpr.aprobar_parte`, `mpr.parte_operario`); siembra en `synap_permiso` verificada en `administranet93`.
- [x] 4.4 `_usuario_tiene_permiso_mpr` (`mpr/views.py`) reconoce rol **Supervisor MPR** (y variantes) además de administrador/supervisor; permisos nuevos vía `tiene_permiso`.
- [x] 4.5 Vista móvil `ParteMovilOperarioView` exige `mpr.parte_operario` (`MprPermisoMixin`) y verifica operario mapeado (mensaje si falta); `MprLoginRequiredMixin` para sesión.
- [x] 4.6 **Landing por rol:** `mpr/landing.py` (`es_operario_puro`, `landing_url_para_usuario`, alias `resolver_landing_usuario`) usado en `dashboard_view`; `/` redirige a `/core/dashboard/` (cubre raíz); login redirige a dashboard (que aplica la landing). Validado: operario puro→`/mpr/mi-parte/`, supervisor/otros→normal.
- [x] 4.7 **Menú:** items nuevos en `APPS_MENU` (`core/utils/utils.py`): Líneas, Máquinas, Operarios y usuarios (permission `mpr.maquinas_lineas`). Artículos por máquina accesible desde el listado de máquinas. Partes pendientes → Fase 7 (URL aún inexistente).
- [x] 4.8 **App móvil enfocada:** `MobileLevelAOnlyMiddleware` ya permite `/mpr/...`; la carga usa `base_app.html` y el operario no ve apps en el navbar (mega-menú gateado por permisos que no posee). Plantilla `mpr/parte_operario.html` responsive.
- [x] 4.9 Vista supervisor `OperarioUsuarioMapView` (`/mpr/operarios-usuarios/`): vincular/desvincular operario↔usuario con listados y validación de unicidad.
- [x] 4.10 Validación en contenedor: mapeo (map/resolve/re-map/desmapear), unicidad por usuario, siembra de permisos, landing por rol (operario puro vs supervisor). Pendiente: suite automatizada (requests 403/redirect) en Fase de tests.

## Fase 5 — Asignación operario→línea + roster (`mpr-parte-movil-operario` / delta `mpr-turnos-roster`)

- [x] 5.1 Repo `mpr/repositories/operario_linea.py` (versionado) + servicios en `mpr/services_operario.py`: `set_linea_habitual_operario`, `linea_habitual_operario`, `historico_linea_operario`, `resolver_linea_operario(id_operario, fecha, id_turno)` (override > habitual). UI: `OperarioLineaView` (`/mpr/operarios-lineas/`) + menú.
- [x] 5.2 Roster extendido con override de línea (columna real `mpr_roster_dia.id_mpr_linea`; el spec la nombra `id_linea`): `upsert_roster(..., id_mpr_linea)`, `override_linea_roster`, `listar_roster_rango` incluye línea; `asignar_turno_roster`/`AsignarTurnoRosterView` aceptan `id_linea` (None = habitual, compatible con filas previas). Pendiente menor: selector de línea en la grilla de planificación (capacidad backend lista).
- [x] 5.3 Validación en contenedor (`administranet93`): sin override usa habitual; override del roster prevalece; otra fecha sin override vuelve a la habitual; duplicado de habitual rechazado; histórico correcto. Pendiente: suite automatizada.

## Fase 6 — Carga móvil del operario (`mpr-parte-movil-operario`)

- [x] 6.1 `construir_grilla_carga_movil(id_operario, fecha, id_turno)` (máquinas de la línea → artículos vigentes; inputs docenas/pares en 0). — `mpr/services_parte_movil.py`; resuelve turno (roster del día) y línea (habitual/override), prefill desde parte editable.
- [x] 6.2 `registrar_parte_movil(...)`: crea `mpr_parte(estado=pendiente, origen=movil_operario)` + líneas con `id_maquina`+snapshot, `cantidad_declarada`; **sin** asiento físico; carga libre. — `mpr/repositories/parte_movil.py` (`cantidad`=0 hasta aprobación; `cantidad_declarada`=docenas×12+pares).
- [x] 6.3 Guardado como borrador y reenvío a pendiente. — mismo parte editable reutilizado (borrador↔pendiente); borrador admite vacío, pendiente exige carga.
- [x] 6.4 Vistas + URLs móviles usando `get_template_for_device` + `mpr/templates/mpr/mobile/`. — `ParteMovilOperarioView` (GET grilla + POST guardar) en `/mpr/mi-parte/`; `mpr/mobile/parte_operario.html` (móvil) + fallback desktop.
- [x] 6.5 Tests: solo artículos vigentes de su línea/turno; guardar deja `pendiente` sin mover stock; conversión docenas×12+pares. — validado en `administranet96` (parte pendiente/origen, `cantidad`=0, `cantidad_declarada`=41 y 48, `stock_deposito.saldo` sin cambio, reedición mismo parte, bordes sin_turno/sin_linea, borrador vacío OK).

## Fase 7 — Aprobación del supervisor (`mpr-aprobacion-parte-supervisor` / delta `mpr-opp-parte-produccion`)

- [x] 7.1 Refactor: extraer del `registrar_parte_produccion` una función reutilizable de validación de cupo (`validar_cupo_parte`) + asiento físico reutilizado (`_registrar_asiento_fisico_opp_parte`, `ya_componentes=True`). `registrar_parte_produccion` ahora usa `validar_cupo_parte`.
- [x] 7.2 `aprobar_parte_produccion(id_parte, correcciones, id_usuario_supervisor, forzar_cupo)`: setea `cantidad_aprobada`/`gap`/`motivo` (motivo obligatorio si `gap!=0`), sincroniza `cantidad`=aprobada, valida cupo sobre aprobada (bloquea salvo `forzar_cupo`), ejecuta asiento a depósito "Producción", `estado=aprobado` + auditoría (`id_usuario_supervisor`, `aprobado_en`), idempotente (`movimiento_fisico_ok`).
- [x] 7.3 Parte directo del supervisor: sin cambios de código; `crear_parte_con_lineas` hereda los defaults del ALTER (`estado='aprobado'`, `origen='directo_supervisor'`) y mueve stock en el acto (comportamiento vigente). El refactor 7.1 preserva la validación.
- [x] 7.4 Bandeja `/mpr/partes-pendientes/` (`PartesPendientesView`): lista filtrable (fecha/turno/borradores) + detalle editable `/partes-pendientes/<id>/` (`PartePendienteDetailView`) con declarada/aprobada/gap/motivo y **cupo Fabricando** de referencia + acción "Aprobar parte" (con opción "forzar cupo"). Menú: `mpr_prod_partes_pendientes` (permiso `mpr.aprobar_parte`).
- [x] 7.5 Tests (administranet96): aprobación sube stock por `cantidad_aprobada` (39); gap=-2 + motivo obligatorio; idempotencia (reaprobar no duplica stock); bloqueo de cupo sin forzar; parte directo conserva defaults aprobado/directo_supervisor.

## Fase 8 — Reportes (P1)

- [x] 8.1 Reporte de conciliación envíos↔producción (grupo Trazabilidad → "Conciliación envíos↔producción"): `reporte_mpr_conciliacion_envios_produccion` compara envíos (`mpr_envio_produccion`) vs producción aprobada (`mpr_parte_linea` de partes `aprobado`) por componente y marca lo "no respaldado" (producido > enviado). Validado en administranet96.
- [x] 8.2 Reporte "Por operario y máquina" (grupo Producción): `reporte_mpr_operario_maquina` agrupa por operario × máquina (con línea vigente) sumando declarada/aprobada/gap. Alinea con el plan tejedor (dimensión máquina/línea + gap). Validado en administranet96.

## Fase 9 — Documentación y cierre

- [x] 9.1 Nuevo doc `docs/mpr/TRAZABILIDAD_MAQUINA_LINEA_OPERARIO.md` del circuito (máquina/línea/operario, flujo dos etapas, gap) + `docs/mpr/REPORTES_MPR.md` (reportes Fase 8).
- [x] 9.2 Actualizado `docs/mpr/PARTE_PRODUCCION.md` (flujo dos etapas) y `docs/mpr/TURNOS_Y_ROSTER.md` (override de línea).
- [x] 9.3 Actualizado `docs/general/HERRAMIENTA_GLOBAL_MIGRACION_ESQUEMA_MYSQL.md` (proveedor `mpr_maquina_linea_trazabilidad`).
- [x] 9.4 Verificación SDD (verify-report PASS) y archivado: specs delta fusionadas + 5 specs nuevas sincronizadas + change movido a `archive/2026-07-08-...`.

---

## Notas de secuencia / dependencias
- Fase 1 es prerequisito de todo.
- Fases 2, 3, 4 pueden avanzar en paralelo tras la Fase 1.
- Fase 5 depende de 2 (líneas) y 4 (operario).
- Fase 6 depende de 3 y 5. Fase 7 depende de 6 (y del refactor 7.1).
- Fase 8 depende de 7.
