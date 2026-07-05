# Inventario — Alta de recibo (mayoristapp)

**Origen:** `administraNET-ecom/mayoristapp/recibo/alta_recibo.php`, `recibo/ajax/json_recibo.php`  
**Destino Synap:** `/ecom/mayoristapp/recibos/alta/`, APIs bajo `/ecom/api/mayoristapp/recibos/alta/` y facturas-imputar.

## Componentes PHP → Synap

| Componente origen | Synap | Estado |
|-------------------|-------|--------|
| Control `fact_temporal` | `recibo_alta_service.control_fact_temporal_libre` | ✅ |
| Selector PV / tipo numeración | UI paso 1 + `recibo_catalogos_service.listar_puntos_venta_usuario` | ✅ |
| Talonario manual | `iniciar_recibo_sesion` tipo `talonario` + verificación duplicado | ✅ |
| `nuevo_recibo` / sesión recibo | `iniciar_recibo_sesion` | ✅ |
| Listado facturas imputar | `facturas-imputar/listado` | ✅ |
| Imputar / desimputar factura | `facturas-imputar/accion` | ✅ |
| `finImputacion` | `fin_imputacion_sesion` | ✅ |
| Efectivo pesos/dólar | `recibo_medios_sesion.alta_efectivo_sesion` | ✅ |
| Cheques | `recibo_medios_sesion` + persistencia en `recibo_guardado_completo_service` | ✅ |
| Transferencias | idem | ✅ |
| Tarjetas | idem + catálogos `tarjetas` / `planes-tarjeta` | ✅ |
| Retenciones | idem + catálogo `retenciones` | ✅ |
| Descuentos | `alta_descuento_sesion` + `descuento_rec_nc` al guardar | ✅ |
| Saldo a favor existente | `traer_saldo_a_cuenta_cliente` + aplicar en wizard (`saldoAFavor` sesión) | ✅ |
| Consumo saldo a favor al guardar | `recibo_saldo_favor_service.persistir_consumo_saldo_favor` (FIFO) | ✅ |
| Saldo a favor nuevo (sobrepago) | `aCuenta` en sesión + `recibo_factura` al guardar | ✅ |
| Resumen / control final | `recibo_totales_sesion` | ✅ |
| `guardar_recibo` completo | `recibo_guardado_completo_service` (1 transacción) | ✅ |
| Asiento contable automático | `recibo_asiento_contable_service` si `activ_contabilidad` y PV `cont=Si` | ✅ |
| `cliente.saldo` | UPDATE en guardado completo | ✅ |
| Wizard UI | `alta_recibo_mayoristapp.html` + JS 4 pasos | ✅ |

## APIs

- `POST …/recibos/alta/accion/?ajax=1` — iniciar, medios, retenciones, descuento, `saldoAFavor`, resumen, guardar, cancelar.
- `GET …/recibos/alta/catalogos/?ajax=1&tipo=…` — PV, cotización, caja, saldo a cuenta, `lineas-saldo-a-cuenta`, retenciones, cuentas, tarjetas, planes.

## Flags y permisos

- `ecom.cobranzas.editar` — escritura.
- `cobranzas_write_enabled` en ModuleConfig ecom.
- **Menú navbar:** entrada en `core/utils/utils.py` → `APPS_MENU` (`id: ecom`); requiere módulo activo en Module Management **y** permiso `ecom.ver` (o `ecom.*` / `*`).

## Pendiente menor

- Tests `@pytest.mark.integration` con MySQL real (marcador documentado en `test_recibo_guardado_integration`).
