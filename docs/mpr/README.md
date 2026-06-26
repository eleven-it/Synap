# Documentación MPR (Módulo de Producción)

Documentación del módulo MPR en Synap: flujos, esquema de datos, manual de usuario, glosario y scripts SQL.

## Índice

| Documento | Descripción |
|------------|-------------|
| [ANALISIS_MPR_PROPUESTA_MVP.md](ANALISIS_MPR_PROPUESTA_MVP.md) | Análisis del proceso de producción y propuesta del módulo MPR (MVP). |
| [MPR_FLUJO_CREAR_OPT.md](MPR_FLUJO_CREAR_OPT.md) | Flujo detallado al crear la OPT (Generar OPT, liberar, OPP). |
| [MPR_PASO3_LINEAS_OPP_ANALISIS.md](MPR_PASO3_LINEAS_OPP_ANALISIS.md) | Análisis: líneas de artículos en paso 3 del wizard (Crear OPP). |
| [SCHEMA_MPR_ADMINISTRANET92.md](SCHEMA_MPR_ADMINISTRANET92.md) | Esquema de tablas MPR en base AdministraNET (lista_produccion_*, movimiento_stock, etc.). |
| [NORMALIZACION_TABLAS_MPR.md](NORMALIZACION_TABLAS_MPR.md) | Normalización de tablas DB (MPR / AdministraNET) y relaciones. |
| [MANUAL_USUARIO_MPR.md](MANUAL_USUARIO_MPR.md) | Manual de usuario del módulo MPR (§4 Pack y componentes). |
| [ARTICULO_PACK_COMPONENTE_MPR.md](ARTICULO_PACK_COMPONENTE_MPR.md) | **Implementación:** cómo se identifican pack y componente (`articulo`, BOM, OPT, armado surtido). |
| [GLOSARIO_MPR.md](GLOSARIO_MPR.md) | Glosario de términos MPR. |
| [SDD_ARMADO_SURTIDO_MVP.md](SDD_ARMADO_SURTIDO_MVP.md) | SDD — Armado surtido desde 2.ª selección (MVP implementado). |
| [SDD_ARMADO_SURTIDO_MULTI_LOTE.md](SDD_ARMADO_SURTIDO_MULTI_LOTE.md) | SDD — Armado surtido multi-pack (lote / carrito). |
| [SPEC_ARMADO_SURTIDO_MULTI_LOTE.md](SPEC_ARMADO_SURTIDO_MULTI_LOTE.md) | Especificación normativa — lote multi-pack armado surtido. |
| [DESIGN_ARMADO_SURTIDO_MULTI_LOTE.md](DESIGN_ARMADO_SURTIDO_MULTI_LOTE.md) | Diseño técnico — refactor TX, sesión, Alpine carrito. |
| [TASKS_ARMADO_SURTIDO_MULTI_LOTE.md](TASKS_ARMADO_SURTIDO_MULTI_LOTE.md) | Tareas de implementación (fases 1–9). |
| [MPR_ARMADO_STOCK_COMPONENTES.md](MPR_ARMADO_STOCK_COMPONENTES.md) | Armado, stock de componentes y flujo OPT/OPP. |
| [FLUJO_VB6_PEDIDO_PRODUCCION_MPR.md](FLUJO_VB6_PEDIDO_PRODUCCION_MPR.md) | Flujo VB6 "Pedido producción" (motivo OPT) – Análisis extremo a extremo. |

## Scripts SQL

En la carpeta [sql/](sql/):

| Script | Uso |
|--------|-----|
| [alter_lista_produccion_agrupada_mpr_opt.sql](sql/alter_lista_produccion_agrupada_mpr_opt.sql) | Columnas id_opt, codigo_movimiento_opt, id_operario_opt en lista_produccion_agrupada. |
| [alter_lista_produccion_agrupada_cantidad_fabricada_acumulada.sql](sql/alter_lista_produccion_agrupada_cantidad_fabricada_acumulada.sql) | Columna cantidad_fabricada_acumulada (acumulado de armado OPA por línea de demanda). |
| [backfill_cantidad_fabricada_acumulada_desde_historico.sql](sql/backfill_cantidad_fabricada_acumulada_desde_historico.sql) | Opcional: inicializar cantidad_fabricada_acumulada desde lista_produccion_historico (tipo_evento OPA). |
| [alter_mpr_id_operario_opt_detalle_historico_stock.sql](sql/alter_mpr_id_operario_opt_detalle_historico_stock.sql) | id_operario_opt en lista_produccion_detalle, lista_produccion_historico y stock (trazabilidad OPT/OPP/OPA). |
| [schema_mpr_administranet92.sql](sql/schema_mpr_administranet92.sql) | deposito.suma_stock, articulo.stock_reserva, lista_produccion_agrupada.fecha_objetivo. |
| [ALTER_deposito_tipo_mpr.sql](sql/ALTER_deposito_tipo_mpr.sql) | Columna tipo_mpr en deposito (Produccion, SemiElaborado, Terminado, etc.). |
| [fix_opt16_pendiente_tras_opp.sql](sql/fix_opt16_pendiente_tras_opp.sql) | Corrección puntual pendiente OPT tras OPP (referencia). |

Ejecutar los scripts en la base de la empresa (ej. administranet92) según corresponda.
