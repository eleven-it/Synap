# Documentación MPR (Módulo de Producción)

Documentación del módulo MPR en Synap: flujos, esquema de datos, manual de usuario, glosario y scripts SQL.

## Índice

| Documento | Descripción |
|------------|-------------|
| [ANALISIS_MPR_PROPUESTA_MVP.md](ANALISIS_MPR_PROPUESTA_MVP.md) | Análisis del proceso de producción y propuesta del módulo MPR (MVP). |
| [MPR_FLUJO_CREAR_OPT.md](MPR_FLUJO_CREAR_OPT.md) | Flujo detallado al crear la OPT (Generar OPT, liberar, OPP). |
| [MPR_PASO3_LINEAS_OPP_ANALISIS.md](MPR_PASO3_LINEAS_OPP_ANALISIS.md) | Análisis: líneas de artículos en paso 3 del wizard (Crear OPP). |
| [SCHEMA_MPR_ADMINISTRANET92.md](SCHEMA_MPR_ADMINISTRANET92.md) | Esquema de tablas MPR en base AdministraNET (lista_produccion_*, movimiento_stock, etc.). |
| [PLAN_MIGRACION_MPR_MYSQL_FUENTE_UNICA.md](PLAN_MIGRACION_MPR_MYSQL_FUENTE_UNICA.md) | **Plan** — Migrar ledgers MPR de Postgres a MySQL (`mpr_*`), FK, utf8mb4, deprecación OPT/lista_produccion. OpenSpec: `openspec/changes/mpr-mysql-fuente-unica/`. |
| [NORMALIZACION_TABLAS_MPR.md](NORMALIZACION_TABLAS_MPR.md) | Normalización de tablas DB (MPR / AdministraNET) y relaciones. |
| [MANUAL_USUARIO_MPR.md](MANUAL_USUARIO_MPR.md) | **Manual de usuario** del módulo MPR (flujo diario, OPT, trazabilidad máquina/línea, planilla CQ, reportes). |
| [manual_usuario_mpr.html](manual_usuario_mpr.html) | **Manual HTML navegable** (generado desde el MD). En la app: **`/mpr/manual/`** (requiere login). Regenerar: `python scripts/generar_manuales_html.py`. |
| [TRAZABILIDAD_MAQUINA_LINEA_OPERARIO.md](TRAZABILIDAD_MAQUINA_LINEA_OPERARIO.md) | **Trazabilidad** máquina / línea / operario: modelo, permisos, flujo dos etapas (móvil + aprobación). |
| [CARGA_MOVIL_OPERARIO.md](CARGA_MOVIL_OPERARIO.md) | Carga móvil del operario (`/mpr/mi-parte/`), grilla asignar artículo, planilla Control de Calidad. |
| [ARTICULO_CE_TALLES_COLOR.md](ARTICULO_CE_TALLES_COLOR.md) | **Desarrollo** — Campos especiales CE TALLES/COLOR: tablas, lectura en UI, inferencia/carga masiva. |
| [ARTICULO_PACK_COMPONENTE_MPR.md](ARTICULO_PACK_COMPONENTE_MPR.md) | **Implementación:** cómo se identifican pack y componente (`articulo`, BOM, OPT, armado surtido). |
| [GLOSARIO_MPR.md](GLOSARIO_MPR.md) | Glosario de términos MPR. |
| [SDD_ARMADO_SURTIDO_MVP.md](SDD_ARMADO_SURTIDO_MVP.md) | SDD — Armado surtido desde 2.ª selección (MVP implementado). |
| [SDD_ARMADO_SURTIDO_MULTI_LOTE.md](SDD_ARMADO_SURTIDO_MULTI_LOTE.md) | SDD — Armado surtido multi-pack (lote / carrito). |
| [SPEC_ARMADO_SURTIDO_MULTI_LOTE.md](SPEC_ARMADO_SURTIDO_MULTI_LOTE.md) | Especificación normativa — lote multi-pack armado surtido. |
| [DESIGN_ARMADO_SURTIDO_MULTI_LOTE.md](DESIGN_ARMADO_SURTIDO_MULTI_LOTE.md) | Diseño técnico — refactor TX, sesión, Alpine carrito. |
| [TASKS_ARMADO_SURTIDO_MULTI_LOTE.md](TASKS_ARMADO_SURTIDO_MULTI_LOTE.md) | Tareas de implementación (fases 1–9). |
| [SDD_ARMADO_UNIFICADO_IMPUTACION.md](SDD_ARMADO_UNIFICADO_IMPUTACION.md) | **Propuesto** — Armado 1ra/2da unificado (fuera de OPT) + imputación supervisor 1ra. OpenSpec: `armado-unificado-imputacion-1ra`. |
| [SPEC_ARMADO_UNIFICADO_IMPUTACION.md](SPEC_ARMADO_UNIFICADO_IMPUTACION.md) | Especificación normativa — armado unificado e imputación. |
| [DESIGN_ARMADO_UNIFICADO_IMPUTACION.md](DESIGN_ARMADO_UNIFICADO_IMPUTACION.md) | Diseño técnico — vista unificada, TX 1ra, imputación supervisor. |
| [TASKS_ARMADO_UNIFICADO_IMPUTACION.md](TASKS_ARMADO_UNIFICADO_IMPUTACION.md) | Tareas de implementación (Fases A–D + verify). |
| [MPR_ARMADO_STOCK_COMPONENTES.md](MPR_ARMADO_STOCK_COMPONENTES.md) | Armado, stock de componentes y flujo OPT/OPP. |
| [FLUJO_VB6_PEDIDO_PRODUCCION_MPR.md](FLUJO_VB6_PEDIDO_PRODUCCION_MPR.md) | Flujo VB6 "Pedido producción" (motivo OPT) – Análisis extremo a extremo. |
| [PROPUESTA_MIGRACION_PEDIDOS_BEST_A_MPR_CUTOVER.md](PROPUESTA_MIGRACION_PEDIDOS_BEST_A_MPR_CUTOVER.md) | ⛔ **SUSPENDIDA (08/07/2026)** — Corte «off BEST / on Synap MPR» de pedidos. Suspendida por falta de mapeo viable (SKU nuevos) y porque MPR ya opera OPT/OPP/OPA nativo. Se conserva como referencia (topología, PED nativo, plan de corte). |
| [e2e/REGISTRO_FLUJO_E2E.md](e2e/REGISTRO_FLUJO_E2E.md) | Registro E2E Playwright (demanda → OPT → OPP) con capturas en [e2e/capturas/](e2e/capturas/). Suite en `tests/e2e/mpr/`. |
| [e2e/MANUAL_USUARIO_MPR.html](e2e/MANUAL_USUARIO_MPR.html) | **Manual visual HTML** (demanda → OPT → OPP) con capturas E2E; abrir en navegador desde `docs/mpr/e2e/`. |
| Comando `e2e_mpr_trazabilidad` | **E2E programático** flujo diario (tablero → envío → parte → CC → armado → imputación) con informe de saldos por depósito. `mpr/management/commands/e2e_mpr_trazabilidad.py`. |
| [e2e/REGISTRO_FLUJO_DIARIO_E2E.md](e2e/REGISTRO_FLUJO_DIARIO_E2E.md) | Registro E2E flujo diario con saldos por fase (validación 09/07/2026, administranet96). |
| [TABLERO_CONSOLIDADO.md](TABLERO_CONSOLIDADO.md) | **Etapa 2** — Tablero de demanda consolidado por artículo: 10 columnas, algoritmo, columna Enviado (fórmula definitiva desde Etapa 4), índice `idx_sd_art_dep`. |
| [TURNOS_Y_ROSTER.md](TURNOS_Y_ROSTER.md) | **Etapa 3** — Turnos de producción (CRUD) + Roster rotativo (planificación semanal de asignación de turnos a operarios). Modelos `MprTurno`/`MprRosterDia`, servicios, vistas/URLs, UI, validaciones, migración 0010, tests. |
| [OPP_PARTE_PRODUCCION.md](OPP_PARTE_PRODUCCION.md) | **Etapa 4 + 5** — Parte de producción: captura ledger OPP-parte (E4) + asiento físico MySQL en depósito Producción (E5). `movimiento_fisico_ok`, `ajuste_fisico_ok`. Migración 0011+0012, servicios, vistas `/mpr/parte-produccion/`. |
| [TRANSICIONES_LOTE.md](TRANSICIONES_LOTE.md) | **Etapa 5** — Transiciones de stock entre etapas MPR: `transferir_stock_entre_etapas`, `MprTransicionLote`, TRANSICIONES_LEGALES, UI columna Acciones en tablero. Migración 0012. |
| [TRAZABILIDAD_OPT.md](TRAZABILIDAD_OPT.md) | **Etapa 6** — Trazabilidad OPT drill-down: `id_lista_produccion` en `MprParte`, escritura a `lista_produccion_historico`, servicios `construir_trazabilidad_opt` / `construir_trazabilidad_articulo`, vista `TrazabilidadOptView` (`/mpr/opt/<id>/trazabilidad/`). Migración 0013. |
| [ENVIO_PRODUCCION_TABLERO.md](ENVIO_PRODUCCION_TABLERO.md) | **Etapa 7** — Envío directo a producción desde el Tablero (ledger-componente, lote): `MprEnvioProduccion`, `enviar_a_produccion_lote`, `_query_enviado_tablero_componente`, `EnviarProduccionLoteView`, fórmula Enviado dos fuentes. Migración 0014. |
| [PARTE_PRODUCCION.md](PARTE_PRODUCCION.md) | **Etapa 8** — Parte de producción por componente: grilla desde Fabricando (E7), asiento físico directo sin BOM (`ya_componentes=True`), validaciones cupo Fabricando + envíos, compatibilidad E6 (`id_lista_produccion=None`). Migración 0015. |
| [DOCENAS_CLASIFICACION_OPERARIO_MPR.md](DOCENAS_CLASIFICACION_OPERARIO_MPR.md) | **Docenas operativas** + **control de calidad por operario fabricante**; impacto en tablero, parte, CC y reportes. |
| [REPORTES_MPR.md](REPORTES_MPR.md) | **Hub reportes** `/mpr/reportes/`: resumen diario, por operario, cadena pipeline, pendientes; modelo envío → parte → CC → armado. |
| [DISENO_ARMADO_TABLERO_PCP.md](DISENO_ARMADO_TABLERO_PCP.md) | Vista tabla armado PCP (resta armar, 1er fecha entrega, terminado pack). |
| [ACCIONES_LOTE_TABLERO.md](ACCIONES_LOTE_TABLERO.md) | **Etapa 9 + 10** — Acciones de lote (supersedido por clasificación global E10). Ver también clasificación única desde Producción. |
| [NAVIGACION_MPR_ETAPA11.md](NAVIGACION_MPR_ETAPA11.md) | **Etapa 11** — Hub de navegación: tablero consolidado como operación diaria; ventana pack/wizard como trazabilidad OPT avanzada; menú, CTAs y `crear_opp_url` → parte de producción. |

## Scripts SQL

En la carpeta [sql/](sql/):

| Script | Uso |
|--------|-----|
| [001_mpr_core_tables.sql](sql/001_mpr_core_tables.sql) | **Tablas core MPR Synap** (`mpr_*`): config, turnos, envíos, partes, transiciones, armado. Proveedor «MPR — tablas core Synap». |
| [alter_lista_produccion_agrupada_mpr_opt.sql](sql/alter_lista_produccion_agrupada_mpr_opt.sql) | Columnas id_opt, codigo_movimiento_opt, id_operario_opt en lista_produccion_agrupada. |
| [alter_lista_produccion_agrupada_cantidad_fabricada_acumulada.sql](sql/alter_lista_produccion_agrupada_cantidad_fabricada_acumulada.sql) | Columna cantidad_fabricada_acumulada (acumulado de armado OPA por línea de demanda). |
| [backfill_cantidad_fabricada_acumulada_desde_historico.sql](sql/backfill_cantidad_fabricada_acumulada_desde_historico.sql) | Opcional: inicializar cantidad_fabricada_acumulada desde lista_produccion_historico (tipo_evento OPA). |
| [alter_mpr_id_operario_opt_detalle_historico_stock.sql](sql/alter_mpr_id_operario_opt_detalle_historico_stock.sql) | id_operario_opt en lista_produccion_detalle, lista_produccion_historico y stock (trazabilidad OPT/OPP/OPA). |
| [schema_mpr_administranet92.sql](sql/schema_mpr_administranet92.sql) | deposito.suma_stock, articulo.stock_reserva, lista_produccion_agrupada.fecha_objetivo. |
| [ALTER_deposito_tipo_mpr.sql](sql/ALTER_deposito_tipo_mpr.sql) | Columna tipo_mpr en deposito (Produccion, SemiElaborado, Terminado, etc.). |
| [fix_opt16_pendiente_tras_opp.sql](sql/fix_opt16_pendiente_tras_opp.sql) | Corrección puntual pendiente OPT tras OPP (referencia). |

Ejecutar los scripts en la base de la empresa (ej. administranet92) según corresponda.

## Comandos de diagnóstico (manage.py)

En entorno Docker: `docker exec Synap_app python manage.py <comando> ... --base-empresa=administranet96`

| Comando | Uso |
|---------|-----|
| `auditar_opt_trazabilidad` | Audita coherencia agrupada + OPP/OPA + métricas UI. |
| `inspeccionar_opt` | Detalle DB de una OPT (agrupada, movimiento OPT, stock). |
| `eliminar_opt` | Borra OPT(s) de prueba: agrupada, detalle, histórico, movimientos y renglones stock (revierte `stock_deposito`). Dry-run por defecto; `--confirmar` para ejecutar. |
| `e2e_mpr_trazabilidad` | Prueba E2E del flujo diario MPR con informe de saldos por fase (pack + componentes BOM). Opciones: `--base`, `--dry-run`, cantidades por etapa. |

**Armado 1ra desde OPT:** al ejecutar lote con `id_lista` en POST, el movimiento OPA debe llevar `Armado OPT {id}` en `movimiento_stock.detalle` y `id_lista_produccion` en `MprArmadoSurtidoMovimiento` para que el listado deje de mostrar «Armado pend.».

