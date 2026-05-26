# Matriz paridad TPV (VB6 / AdministraNET ↔ Synap)

Referencia breve **VB6 `TPV.frm` → Synap self-checkout**. Estado: **OK** implementado en Synap, **parcial** o **pendiente** según fila.

| Área VB6 (orden típico) | Synap actual | Estado |
|-------------------------|--------------|--------|
| Suma medios de cobro (efectivo + tarjeta + intereses) ≈ total venta | `evaluar_suma_medios_pago` + `ConfirmationService`; prechec `cart_confirm` si `modo_tpv` | OK |
| «Al menos un medio» si importes explícitos en cero | Mismo helper + códigos `E_TPV_MEDIOS_VACIOS` | OK |
| Default un medio = total cuando no hay desglose | Ambos importes `None` → tarjeta = total en confirmación | OK |
| Series obligatorias por ítem | `validar_series_carrito` (JOIN `articulo.serie`), modal + `requiere_series` en GET carrito; cliente TPV `asegurarSeriesCompletasTpv` | OK |
| obliga_selecpv / PV obligatorio | `evaluar_precheck_tpv_paridad` + `permisos_sistema.obliga_selecpv` | OK |
| obliga_cambvendedor | Mismo precheck + `cod_viajante` explícito en POST | OK |
| verificar_limites crédito cliente | `cliente.Credito` vs `saldo` + total venta | OK |
| limite_efectivo_caja | `caja_abm` vía `get_config_for_kiosk` + `limite_efectivo` / `activa_limite_efectivo` | OK |

Actualizar esta tabla al cerrar cada fase del cambio `paridad-tpv-administranet`.
