# Precheck TPV — permisos y límites legacy

Solo aplica cuando el kiosco tiene **`modo_tpv`** activo; la vista `cart_confirm` llama a **`evaluar_precheck_tpv_paridad`** después de validar series y medios de cobro.

## Entrada de permisos

| VB6 / AdministraNET | Tabla / campo | Comportamiento Synap |
|---------------------|----------------|------------------------|
| `obliga_selecpv` | `permisos_sistema.obliga_selecpv` (por `IDPuesto` = sesión `user.id_puesto`) | Si valor **Sí**: el carrito debe tener `id_punto_venta` > 0. |
| `obliga_cambvendedor` | `permisos_sistema.obliga_cambvendedor` | Si **Sí**: el POST de confirmación debe incluir **`cod_viajante`** explícito (no alcanza solo el default del kiosco). |
| `verificar_limites` (crédito) | `cliente.Credito`, `cliente.saldo`, `Codigo` = `id_cliente` | Si `Credito` > 0 y `saldo + total_venta > Credito` → rechazo. Consumidor final (`id_cliente` ≤ 1) no se evalúa. |
| `limite_efectivo_caja` | `caja_abm.limite_efectivo`, `activa_limite_efectivo`, caja desde `get_config_for_kiosk` | Si límite activo y efectivo TPV supera el tope → rechazo. |

Sin **`id_puesto`** en sesión no se cargan filas de `permisos_sistema`; las flags **obliga_*** quedan como **No** (no se fuerza PV/vendedor por permiso hasta que el usuario tenga puesto en sesión).

## Códigos HTTP 400

| Código API | Uso |
|------------|-----|
| `E_TPV_OBLIGA_PV` | Falta punto de venta válido en carrito con permiso activo. |
| `E_TPV_OBLIGA_VENDEDOR` | Falta `cod_viajante` en el POST con permiso activo. |
| `E_TPV_CREDITO_EXCEDIDO` | Venta supera cupo de crédito. |
| `E_TPV_LIMITE_EFECTIVO_CAJA` | Efectivo informado supera `limite_efectivo` de la caja. |

Los rechazos generan auditoría `tpv_rechazo_validacion` igual que otros `E_TPV_*`.
