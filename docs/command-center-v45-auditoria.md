# Command Center: auditoría de la línea base V45

Estado: investigación y preparación en `codex/command-center-v45`. Ninguno de los once tableros de administraNET se considera entregado por esta auditoría.

## Fuentes y trazabilidad

| Fuente | Identificación | Uso |
|---|---|---|
| `SYNAP_TABLERO_ADMINISTRANET_CONTEXTO_CODEX_R1_20261012.md` | SHA-256 `0CD5946B7F09D91FB6AE8D2C47CA09DCF40667EC88BE4BF38837D08DE2621D61` | Requisitos P1–P19 y anexo histórico de 162 KPI. |
| `411 - V45.zip` | Archivo 7z, SHA-256 `8A26ED92C8B7373A89E14D82BEC008031E3C94C0F76BE42F0E705D021BADDCD8` | Formularios y módulos VB6 `CM_*` / `modCM_*`. |
| Backup Smartclean del 12/10/2026 | SHA-256 `E0DD755B8E97D42AF2448BEFA73E8296F59A699E30B983C8DEC` | Consultas con datos de circuitos operativos. |
| Backup Best Sox del 09/10/2026 | SHA-256 `C44E8E94AA19F4ECE14130326DDD3C3DB057BB1F170DBBD3002FF4A90CBE25DA` | Conciliación contable y financiera. |
| Synap `origin/Desarrollo` | `6059158643a66e34ba2c82ae96cc9c603bcf5df3` | Línea base web. |

Los backups se restauraron en esquemas separados de MySQL 5.7 aislado, sin puertos publicados. No se incorporaron al repositorio. Best Sox: 598 tablas, 2.319 filas en `cuentacliente` y 8.574 **renglones** en `cont_asiento` (3.101 combinaciones distintas de ejercicio y número de asiento); hay 1.813 facturas `FA`/`FB` y 224 notas de crédito `NCA`/`NCB` en `cuentacliente`. Smartclean: 543 tablas, 68.280 filas en `cuentacliente` y 0 en `cont_asiento`. Esas cifras identifican el material de prueba; no son resultados de KPI.

## Inventario por tablero

Los conteos son del anexo histórico R6.8.65; deben cotejarse con V45 antes de darlos por vigentes.

| Tablero administraNET | KPI históricos | Permiso heredado | Estado en Synap `Desarrollo` |
|---|---:|---|---|
| Resumen general | 16 | `tablero_resumen_general` | Pendiente de migrar. |
| Comercial — Ventas | 16 | `tablero_comercial_ventas` | `ventas` existente es un subconjunto; falta paridad. |
| Comercial — Preparación de pedidos | 16 | `tablero_comercial_prep_pedidos` | Pendiente de migrar. |
| Abastecimiento — Compras | 14 | `tablero_abastecimiento_compras` | `compras` existente es un subconjunto; falta paridad. |
| Abastecimiento — Stock | 14 | `tablero_abastecimiento_stock` | `inventario` existente es un subconjunto; falta paridad. |
| Análisis financiero | 15 | `tablero_gestion_financiera` | `tesoreria` y `ventas_cobros` son subconjuntos; falta paridad. |
| Gestión contable | 14 | `tablero_gestion_contable` | Pendiente de migrar; validar con Best Sox. |
| Impuestos — Posiciones fiscales | 14 | `tablero_impuesto_posicion_fiscal` | Pendiente de migrar. |
| Contabilidad — Libros y estados | 14 | `tablero_contabilidad_libros_estados` | Pendiente de migrar; validar con Best Sox. |
| Logística — Hojas de ruta | 14 | `tablero_logistica_hoja_ruta` | Pendiente de migrar. |
| Análisis de gastos | 15 | `tablero_gestion_financiera` en V45 | Pendiente de migrar; confirmar permiso y fuentes. |

**No presentar las siete áreas parciales de Synap como equivalentes a estos once tableros.** El código actual añade además `manufactura` y `cruzados` como áreas web propias; no corresponden directamente a tableros homónimos del ERP.

## Diferencias verificadas y controles pendientes

1. `CM_ResumenEjecutivo.frm` abre un selector sin consulta inicial. Synap consultaba varias áreas al cargar la página. La pantalla debe quedar vacía hasta elegir un tablero y cada API debe autorizarlo por separado.
2. Las banderas `tablero_*` existen tanto en `permiso_sistema` como en `synap_permiso` de Best Sox. La autorización web debe tomar la empresa, el puesto y el usuario actuales, y denegar por defecto cuando falte una regla aplicable.
3. `modCM_FiltroPuntoVenta.bas` usa `punto_venta_usr` y deriva sucursales por `punto_venta.id_sucursal`. La copia Best Sox tiene 58 asignaciones de PV distribuidas entre 34 usuarios. Los servicios actuales de Synap no aplican todavía esta restricción de modo uniforme; por eso no se puede certificar seguridad territorial sólo filtrando las opciones del selector.
4. Varias consultas actuales usan `Fecha <= fecha_fin`. En ambos backups `comp_ped.Fecha`, `cuentacliente.Fecha` y `stockp.Fecha` son `DATE`, por lo que ese predicado incluye el último día para esas tres tablas. Antes de reutilizarlo en columnas `DATETIME`, deben verificarse sus tipos y emplearse un fin exclusivo al día siguiente.
5. El detalle, las comparaciones, los gráficos y las exportaciones de los once tableros requieren la misma autorización y el mismo contexto que el KPI padre. No deben inventarse valores cero ante consultas faltantes o fallidas.
6. El acceso a costos, rentabilidad, montos de caja, cuenta corriente, comprobantes y asientos necesita gates independientes antes de publicarse.

## Criterio de avance

Cada KPI se marcará `implementado` sólo con fórmula y fuente verificadas en V45, filtro territorial del servidor, permisos, respuesta explícita de no disponibilidad, detalle y comparación cuando correspondan, y conciliación numérica en la base adecuada. Los candidatos pasan por PR y pruebas en Desarrollo; Staging se considera después de esas verificaciones.
