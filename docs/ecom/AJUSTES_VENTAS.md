# Ajustes de ventas (ecom)

**Ruta:** `/ecom/mayoristapp/ajustes-ventas/`  
**Permiso:** `ecom.config_ajustes_ventas`  
**Fecha:** 14/07/2026

## Propósito

Pantalla tipo Odoo para parámetros del flujo de pedidos mayorista. Hoy expone un único toggle:

| Parámetro | Key MySQL `configuracion_ecom` | Default |
|-----------|-------------------------------|---------|
| Validar stock al confirmar pedidos | `ecom_validar_stock_pedidos` | **Si** |

## Comportamiento

- **Si (Activo):** comportamiento legacy — el carrito y el checkout PED validan stock disponible; el preview masivo **no** valida stock (solo calcula totales).
- **No (Inactivo):** se permiten pedidos simple y masivo sin bloqueo por stock en carrito y commit; el faltante puede cubrirse fabricando vía MPR.

Servicio de lectura/escritura: `ecom.services.ecom_config_mysql` (`pedidos_validan_stock`, `escribir_valor_configuracion_ecom`).

## API

| Método | Path | Body |
|--------|------|------|
| GET | `/ecom/api/mayoristapp/ajustes-ventas/` | — |
| POST | `/ecom/api/mayoristapp/ajustes-ventas/` | `{ "validar_stock_pedidos": true \| false }` |

## Seed del parámetro

Provider global MySQL: **`vendedores_asignacion`** (`run_vendedores_asignacion_mysql` en `core/services/legacy_mysql_schema/catalog.py`).

Inserta la fila `ecom_validar_stock_pedidos` en `configuracion_ecom` y `configuracion_ecom_conf` si no existe (valor default **Si**).

**UI:** Archivo → **Migración esquema MySQL (legacy)** → proveedor **Asignación vendedor ↔ cliente / marca** (`vendedores_asignacion`) sobre la base empresa.

## Menú

Ventas → sección **Ajustes** → **Ajustes de ventas**.
