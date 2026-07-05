# Spec — Cuenta corriente, consumos y recibos (mayoristapp)

**Relays:** `relay-ctacte.php`, `relay-cuenta-corriente.php`, `relay-consumos-resumen.php`, `relay-recibos.php`.  
**FE / imputaciones relacionadas:** `relay_facturas_imputar.php` (también [SPEC_MAYORISTAPP_FE_NC.md](./SPEC_MAYORISTAPP_FE_NC.md)).  
**Checkpoints:** `mayoristapp_ctacte`, `mayoristapp_recibos`.

---

## 1 — Modelo de datos de referencia (repo e-com)

Documentación en el clon PHP:

`administraNET-ecom/docs/administranet_estructura/modelo_base_datos.md`

Contenido útil: tablas `cuentacliente`, `recibo_factura`, `librobanco`, `caja_*`, cheques, tarjetas, retenciones, vínculos con movimientos.

**Nota:** no sustituye el esquema completo AdministraNET en Synap; sirve de glosario para nombres de columnas y relaciones en recibos/cobranzas.

---

## 2 — Synap objetivo

- Consultas parametrizadas sobre `cuentacliente` y tablas satélite según el relay.
- Para recibos: alinear con reglas de negocio VB6 si existen servicios ya migrados en otras apps.

---

## 3 — API Synap v1 (`relay-ctacte.php`)


| Acción PHP                 | Método | Ruta Synap                                                 | Notas                                                                                                                                                                                                                                |
| -------------------------- | ------ | ---------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Listado ajax               | POST   | `/ecom/api/mayoristapp/ctacte/movimientos/?ajax=1`         | Cuerpo JSON: `campoBusca` (`-` | `Fecha` | `NroComprobante`), `fechaDesde`/`fechaHasta`, `numeroComp`, `limit`. Respuesta `{ "total", "filas" }`. Requiere `**idcliente`** en sesión (mayoristapp) y `cliente_accesible_por_sesion`. |
| Autocomplete `queryString` | GET    | `/ecom/api/mayoristapp/ctacte/sugerencias-nro/?ajax=1&q=…` | Lista de `NroCompBusq` con prefijo.                                                                                                                                                                                                  |

### 3.1 — API v1 (`relay-cuenta-corriente.php`)

Listado de **pedidos** (`comp_ped`, `TipoComprobante='PED'`) solo para el cliente en sesión. Misma lógica de filtros que `POST …/comprobantes/pedidos/` en modo cliente, pero **no** se acepta forzar `vendedor`: el cuerpo ignora `vendedor`. Fechas `YYYY-MM-DD` (el PHP antiguo usaba `dd/mm/yyyy`).

| Acción PHP | Método | Ruta Synap | Notas |
|------------|--------|------------|--------|
| Listado ajax | POST | `/ecom/api/mayoristapp/ctacte/pedidos/?ajax=1` | `campoBusca` (`Fecha`, `NroComprobante`), `estadoPedido`, `limit`. `{ "total", "filas" }`. |
| Autocomplete `queryString` | GET | `/ecom/api/mayoristapp/ctacte/pedidos/sugerencias-nro/?ajax=1&q=…` | `NroCompBusq` PED con prefijo, solo ese cliente. |

### 3.2 — API v1 (`relay-consumos-resumen.php`)

Top artículos por **cantidad vendida** al cliente (`stock.CodigoCP`), ventana por defecto últimos **365 días**, `limit` default **20** (máx. 100).

| Acción PHP | Método | Ruta Synap | Notas |
|------------|--------|------------|--------|
| Tabla ajax | POST | `/ecom/api/mayoristapp/ctacte/consumos-resumen/?ajax=1` | Cuerpo opcional: `fechaDesde`, `fechaHasta` (`YYYY-MM-DD`), `limit`. Respuesta `{ "total", "filas", "advertencia_precios" }`. Lista de precios / desc. renglón / tipo cliente desde sesión (`mayoristapp.cliente[0]`) o MySQL. `iva_incluido` desde `mayoristapp.iva_incluido` o `ivaIncluido`. |

**Alcance precios v1.1:** usa motor `price_rules_engine` + `price_calculator`:
- resolución de reglas en orden particular → masiva → general (aproximación robusta),
- promociones de artículo por lista y vigencia,
- cálculo final con Decimal.

`advertencia_precios` queda como mensaje operativo de versión, pero la brecha de reglas/promociones queda cerrada en Fase C.

---

## 4 — API Synap v1 (`relay-recibos.php`)


| Acción PHP           | Método | Ruta Synap                                                 | Notas                                                                                                                                                                                                                                                                                      |
| -------------------- | ------ | ---------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Listado `consulta=1` | POST   | `/ecom/api/mayoristapp/recibos/listado/?ajax=1&consulta=1` | Cuerpo JSON: `campoBusca` (`Fecha` + `fechaDesde`/`fechaHasta`), `filtraCliente`, `filtraVendedor` (`todos` u omitido con `IdUsuario` de sesión). Respuesta `{ "total", "filas" }`. Requiere `**id_usuario`** en sesión si no se envía `filtraVendedor`. Checkpoint `mayoristapp_recibos`. |


---

## 6 — Alta de recibo (`recibo/alta_recibo.php` + `json_recibo.php`)

Wizard móvil por pasos: inicio → imputación de facturas → medios de cobro (MVP: efectivo) → confirmación y guardado.

| Acción PHP | Método | Ruta Synap | Notas |
|------------|--------|------------|--------|
| `altaRecibo=1` | POST | `/ecom/api/mayoristapp/recibos/alta/accion/?ajax=1` | Cuerpo `{ "iniciar": 1, "tipoNro": "sistema" \| "talonario", ... }`. Inicializa `session['recibo']`. |
| `listarFacturas=1` | POST | `/ecom/api/mayoristapp/fe/facturas-imputar/listado/?ajax=1` | Reutilizado del relay FE. |
| `imputarFactura` / `desimputarFactura` / `finImputacion` | POST | `/ecom/api/mayoristapp/fe/facturas-imputar/accion/?ajax=1` | Sesión `recibo.facturas`; `finImputacion` fija `totalImputado`. |
| `altaEfectivo` / cheques / tarjetas / transferencias / retenciones / descuento / `saldoAFavor` | POST | `…/recibos/alta/accion/?ajax=1` | Ver `INVENTARIO_FORMULARIO_ALTA_RECIBO.md`. |
| Catálogos (PV, cotización, cuentas, tarjetas…) | GET | `…/recibos/alta/catalogos/?ajax=1&tipo=…` | Solo lectura; no requiere `cobranzas.editar`. |
| `traeResumenRecibo` / `controlFinalRecibo` | POST | `…/recibos/alta/accion/?ajax=1` | `{ "resumen": 1 }`, `{ "controlFinal": 1 }`. |
| `guardarRecibo=1` | POST | `…/recibos/alta/accion/?ajax=1` o facturas-imputar/accion | Reserva `codmov` + talonario REC (sistema), persiste imputación (`guardar_recibo_imputacion_legacy`) e ingreso caja si hay efectivo. |

**UI:** `/ecom/mayoristapp/recibos/alta/` (`alta_recibo_mayoristapp.html`). Requiere cliente en sesión; enlace desde hub «Alta recibo».

**Permisos:** `ecom.cobranzas.editar` en APIs de escritura. **Flags módulo ecom:** `cobranzas_write_enabled` (guardar/alta/efectivo), `fe_write_enabled` o `cobranzas_write_enabled` para imputar. Overrides Django: `MAYORISTAPP_RECIBO_WRITE_ENABLED`, `MAYORISTAPP_FE_WRITE_ENABLED`.

**Asiento contable:** si `configuracion.activ_contabilidad = 'Si'` y el PV del recibo tiene `cont = 'Si'`, `guardar_recibo` genera asiento en `cont_asiento` (paridad `generar_asiento_cont`).

**Saldo a favor:** el wizard permite aplicar saldo existente (`saldoAFavor` en sesión); al guardar se consumen líneas `recibo_factura` REC/NCA/… en orden FIFO.

---

## 7 — Pendientes Fase C

- Tests de integración MySQL (`@pytest.mark.integration`).

