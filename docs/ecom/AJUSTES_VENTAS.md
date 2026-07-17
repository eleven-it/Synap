# Ajustes de ventas (ecom)

**Ruta:** `/ecom/mayoristapp/ajustes-ventas/`  
**Permiso:** `ecom.config_ajustes_ventas`  
**Fecha:** 16/07/2026

## Propósito

Pantalla tipo Odoo para parámetros del flujo de pedidos mayorista.

| Parámetro | Key MySQL `configuracion_ecom` | Default |
|-----------|-------------------------------|---------|
| Validar stock al confirmar pedidos | `ecom_validar_stock_pedidos` | **Si** |
| Enviar mail al confirmar pedido | `ecom_enviar_mail_confirmar_pedido` | **Si** |
| Workflow jerarquía comercial (master) | `ecom_workflow_jerarquia_comercial` | **No** |
| Aprobación comercial de pedidos (subflag) | `ecom_aprobacion_pedidos_activa` | **No** |
| Umbral monto aprobación | `ecom_aprobacion_umbral_monto` | vacío (regla inactiva) |
| Umbral descuento pie (%) | `ecom_aprobacion_umbral_desc_pie` | vacío |
| Umbral descuento renglón (%) | `ecom_aprobacion_umbral_desc_renglon` | vacío |
| Atajo objetivos en hub pedidos | `ecom_objetivos_en_pedidos` | **No** |
| Atajo backorder en hub pedidos | `ecom_backorder_en_pedidos` | **No** |

## Comportamiento

### Validación de stock

- **Si (Activo):** comportamiento legacy — el carrito y el checkout PED validan stock disponible; el preview masivo **no** valida stock (solo calcula totales).
- **No (Inactivo):** se permiten pedidos simple y masivo sin bloqueo por stock en carrito y commit; el faltante puede cubrirse fabricando vía MPR.

### Mail de confirmación al confirmar PED

- **Si (Activo):** tras confirmar un pedido (PED), si el checkout incluye `enviar_mail_cliente` y el cliente tiene email, se encola mail en `EcomMailQueue`.
- **No (Inactivo):** no se encola mail automático al confirmar (sigue disponible el encolado manual desde la UI de comprobantes).
- Requiere **AND** con el flag del checkout `enviar_mail_cliente` y SMTP configurado (`core.services.outbound_email`).

### Workflow comercial

- **Master OFF:** paridad actual — carteras JSON legacy, alcance propio, sin aprobación comercial efectiva aunque el subflag diga Sí en DB.
- **Master ON:** alcance vía organigrama G→S→V (`alcance_viajantes_comercial`); ABM jerarquía en la misma pantalla (permiso `ecom.jerarquia.editar`).
- **Subflag aprobación:** solo tiene efecto con master ON; umbrales vacíos = regla inactiva (comportamiento conservador).
- **Atajos hub:** toggles independientes para enlaces objetivos/backorder desde el hub de pedidos (`pedidos_hub.html`).

Servicio de lectura/escritura: `ecom.services.ecom_config_mysql` (`pedidos_validan_stock`, `pedidos_envian_mail_confirmacion`, `workflow_jerarquia_comercial_activo`, `aprobacion_pedidos_activa`, `guardar_config_workflow_comercial`, `escribir_valor_configuracion_ecom`).

## API

| Método | Path | Body |
|--------|------|------|
| GET | `/ecom/api/mayoristapp/ajustes-ventas/` | — |
| POST | `/ecom/api/mayoristapp/ajustes-ventas/` | `{ "validar_stock_pedidos": true \| false, "enviar_mail_confirmar_pedido": true \| false }` (al menos uno) |
| GET | `/ecom/api/mayoristapp/ajustes/workflow/` | — |
| POST | `/ecom/api/mayoristapp/ajustes/workflow/` | `{ "workflow_jerarquia_comercial": bool, "aprobacion_pedidos_activa": bool, "objetivos_en_pedidos": bool, "backorder_en_pedidos": bool, "umbral_monto": string, "umbral_desc_pie": string, "umbral_desc_renglon": string }` |
| GET/POST | `/ecom/api/mayoristapp/jerarquia/nodos/` | ABM árbol (permiso `ecom.jerarquia.editar`) |
| GET | `/ecom/api/mayoristapp/jerarquia/usuarios/?q=` | Búsqueda predictiva de usuarios con `CodViajante` para el ABM |

## Seed de parámetros

Provider global MySQL:

1. **`vendedores_asignacion`** — inserta `ecom_validar_stock_pedidos` y el resto de claves en `_ECOM_AJUSTES_VENTAS_CONFIG`.
2. **`ecom_jerarquia_aprobacion`** — además asegura las claves de workflow/aprobación/atajos al aplicar DDL de jerarquía.

Inserta filas en `configuracion_ecom` y `configuracion_ecom_conf` si no existen.

**UI:** Archivo → **Migración esquema MySQL (legacy)** → proveedor correspondiente sobre la base empresa.

## UI (cards)

Orden de las tarjetas en `ecom/ajustes_ventas.html` (canon slate/sky, toggles Activo/Inactivo):

1. **Validación de stock** — toggle `validar_stock_pedidos`.
2. **Correo al confirmar pedido** — toggle `enviar_mail_confirmar_pedido`. Nota UI: al confirmar un PED, si el cliente tiene email se encola el comprobante; requiere correo saliente configurado y el worker `process_ecom_mail_queue`. Se guarda junto a `validar_stock_pedidos` en el mismo POST a `api_ajustes_ventas`.
3. **Workflow comercial** — flags/umbrales de aprobación y atajos del hub.
4. **Jerarquía comercial** — ABM G→S→V. Gerente/Supervisor: búsqueda de usuarios con puesto **Supervisor**, **Administrador**/**Administración** o **Ventas** (etiqueta = nombre y apellido). Vendedor: búsqueda en catálogo **viajantes** (no usuarios). Permiso `ecom.jerarquia.editar`.

## Menú

Ventas → sección **Ajustes** → **Ajustes de ventas**.
