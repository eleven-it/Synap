# Inventario de relays — `mayoristapp/`

**Fuente:** clon `administraNET-ecom` (rama analizada 2026-03-30).  
**Total:** 44 archivos (`relay*.php` / `relay-*.php`).  
**Canónico en código:** `ecom.services.mayoristapp_relays.MAYORISTAPP_RELAY_PATHS` (los tests exigen que su longitud coincida con `RELAY_ENDPOINT_COUNT`).

---

## Leyenda columnas

| Columna | Significado |
|---------|-------------|
| **Ruta** | Relativa a `mayoristapp/` |
| **Área** | Agrupación funcional |
| **Destino Synap (sugerido)** | `ecom` / `reports` / `login` / `legacy_db` + servicio |
| **Checkpoint `module_slug`** | Valor sugerido para `EcomMigrationCheckpoint` al cerrar el vertical |
| **Estado** | `pendiente` hasta migración |

---

## Tabla

| # | Ruta | Área | Destino Synap (sugerido) | Checkpoint | Estado |
|---|------|------|---------------------------|------------|--------|
| 1 | `jcart/relay.php` | Carrito web | `ecom` + sesión | `mayoristapp_jcart_web` | pendiente |
| 2 | `relay-art-rapido.php` | Catálogo | `ecom` | `mayoristapp_catalogo` | pendiente |
| 3 | `relay-art.php` | Catálogo | `ecom` | `mayoristapp_catalogo` | pendiente |
| 4 | `relay-articulo-remito.php` | Catálogo / remito | `ecom` | `mayoristapp_catalogo` | pendiente |
| 5 | `relay-cliente-domicilio.php` | Clientes | `ecom` | `mayoristapp_clientes` | **v1** → `GET/POST …/clientes/domicilio/`, `GET …/domicilio-opciones-visita/` (JSON) |
| 6 | `relay-cliente-rapido.php` | Clientes | `ecom` | `mayoristapp_clientes` | **v1** → `POST …/clientes/seleccionar/`, `GET/POST …/clientes/rapido/` (lecturas, `obtieneCliente`, `altaCliente`, `editaCliente`, lista rápida en sesión) |
| 7 | `relay-clientes.php` | Clientes | `ecom` | `mayoristapp_clientes` | **v1 parcial** → `GET/POST …/clientes/buscar/`, `GET …/seleccionado/`, `GET …/comprobante-formulario/` (JSON; búsqueda PHP era HTML) |
| 8 | `relay-comp-no-cancelados-resumen.php` | Comprobantes | `ecom` | `mayoristapp_comprobantes` | pendiente |
| 9 | `relay-comprobante-a-mail.php` | Comprobantes | `ecom` | `mayoristapp_comprobantes` | **v1** → `GET …/comprobantes/comprobante-a-mail/?codMov=…&tipocomprobante=…` (payload/token a `fin-comprobante`; sin SMTP) |
| 10 | `relay-comprobantes-ncancelados.php` | Comprobantes | `ecom` | `mayoristapp_comprobantes` | pendiente |
| 11 | `relay-consumos-resumen.php` | Cuenta corriente | `ecom` | `mayoristapp_ctacte` | **v1** → `POST …/ctacte/consumos-resumen/` (JSON; precios subconjunto `price_calculator`, ver `advertencia_precios`) |
| 12 | `relay-contacto-cliente.php` | Clientes | `ecom` | `mayoristapp_clientes` | **v1** → `GET/POST …/clientes/contacto/` (JSON en lugar de HTML) |
| 13 | `relay-ctacte.php` | Cuenta corriente | `ecom` | `mayoristapp_ctacte` | **v1** → `POST …/ctacte/movimientos/`, `GET …/ctacte/sugerencias-nro/` (JSON; sesión `idcliente`) |
| 14 | `relay-cuenta-corriente.php` | Cuenta corriente | `ecom` | `mayoristapp_ctacte` | **v1** → `POST …/ctacte/pedidos/` + `GET …/ctacte/pedidos/sugerencias-nro/` (PED solo cliente sesión; JSON) |
| 15 | `relay-devoluciones.php` | Estadísticas | `ecom` / `reports` | `mayoristapp_informes` | **v1 lectura** → `POST …/estadisticas/devoluciones/` (`queAccion=seleccion|listar`) + `GET …/estadisticas/devoluciones/sugerencias-nro/`; `procesar` bloqueado por plan |
| 16 | `relay-envio-calculo.php` | Logística | `ecom` | `mayoristapp_logistica` | pendiente |
| 17 | `relay-filtros-estadisticas.php` | Estadísticas | `ecom` / `reports` | `mayoristapp_informes` | **v1** → `GET/POST …/estadisticas/filtros/?tabla=...` (JSON opciones por tabla) |
| 18 | `relay-laboratorio.php` | Catálogo | `ecom` | `mayoristapp_catalogo` | **v1** → `GET …/catalogo/laboratorios/` |
| 19 | `relay-lista-precio.php` | Precios | `ecom` (`precio_relays` + `configuracion`) | `mayoristapp_precios` | **v1** → `GET …/precios/lista-precio/` |
| 20 | `relay-logistica-comprobantes.php` | Logística | `ecom` | `mayoristapp_logistica` | pendiente |
| 21 | `relay-lote.php` | Catálogo | `ecom` | `mayoristapp_catalogo` | **v1** → `GET …/catalogo/lotes/` (JSON; PHP era HTML) |
| 22 | `relay-marca.php` | Catálogo | `ecom` | `mayoristapp_catalogo` | **v1** → `GET …/catalogo/marcas/` |
| 23 | `relay-mas-vendidos.php` | Catálogo | `ecom` | `mayoristapp_catalogo` | **v1** → `GET …/catalogo/mas-vendidos/` (SQL vía `mas-vendidos.php` include) |
| 24 | `relay-pedidos.php` | Comprobantes | `ecom` | `mayoristapp_comprobantes` | **v1** → `POST …/comprobantes/pedidos/` + `GET …/sugerencias-nro/` (JSON; sin anular) |
| 25 | `relay-presupuestos.php` | Comprobantes | `ecom` | `mayoristapp_comprobantes` | **v1** → `POST …/comprobantes/presupuestos/` (JSON) |
| 26 | `relay-promociones.php` | Precios | `ecom` | `mayoristapp_precios` | **v1** → `GET …/precios/promociones/?ajax=1` (JSON) |
| 27 | `relay-proveedor.php` | Catálogo / compras | `ecom` | `mayoristapp_catalogo` | **v1** → `GET …/catalogo/proveedores/` |
| 28 | `relay-recibos.php` | Cobranzas | `ecom` | `mayoristapp_recibos` | **v1** → `POST …/recibos/listado/?ajax=1&consulta=1` (JSON; requiere `id_usuario` salvo `filtraVendedor`) |
| 29 | `relay-remitos.php` | Comprobantes | `ecom` | `mayoristapp_comprobantes` | **v1** → `POST …/comprobantes/remitos/` (JSON) |
| 30 | `relay-rubro-catalogo.php` | Catálogo | `ecom` | `mayoristapp_catalogo` | **v1** → `POST …/filtro-rubro-catalogo/` |
| 31 | `relay-rubro.php` | Catálogo | `ecom` | `mayoristapp_catalogo` | **v1** → `GET …/catalogo/rubros/` y `…/catalogo/subrubros/` |
| 32 | `relay-stock-autocomplete.php` | Stock | `ecom` | `mayoristapp_stock` | pendiente (autocomplete vive en existencias PHP) |
| 33 | `relay-stock-existencias.php` | Stock | `ecom` | `mayoristapp_stock` | **v1 parcial** → `POST …/articulos/autocomplete/` |
| 34 | `relay-tacc.php` | Catálogo | `ecom` | `mayoristapp_catalogo` | **v1** → `GET …/catalogo/tacc-opciones/` |
| 35 | `relay-tipo-cliente.php` | Clientes | `ecom` | `mayoristapp_clientes` | **v1** → `GET …/subrubros-tipo-cliente/` |
| 36 | `relay-ventas-netas-gerencia-old-31-10-2024.php` | Informes (legacy) | — | — | **no migrar** (respaldo PHP) |
| 37 | `relay-ventas-netas-gerencia.php` | Informes | `reports` | `mayoristapp_informes_vn_gerencia` | **v1 parcial** → `GET …/ventas-netas/relay/gerencia/` |
| 38 | `relay-ventas-netas.php` | Informes | `reports` | `mayoristapp_informes_vn` | **v1 parcial** → `GET …/ventas-netas/relay/` |
| 39 | `relay_factura_electronica.php` | FE | `ecom` | `mayoristapp_fe` | **v1** → `POST …/fe/factura-electronica/listado/` + `GET …/fe/factura-electronica/sugerencias-nro/` (JSON) |
| 40 | `relay_facturas_imputar.php` | FE / cobranzas | `ecom` | `mayoristapp_fe` | **v1** → `POST …/fe/facturas-imputar/listado/` + `GET …/fe/facturas-imputar/sugerencias-nro/` (JSON; `accion` bloqueada por plan solo lectura) |
| 41 | `relay_geolocalizacion.php` | Logística | `ecom` | `mayoristapp_logistica` | pendiente |
| 42 | `relay_nota_credito.php` | NC | `ecom` | `mayoristapp_fe` | **v1** → `POST …/fe/nota-credito/listado/` + `GET …/fe/nota-credito/sugerencias-nro/` (JSON) |
| 43 | `relay_ruta_logistica.php` | Logística | `ecom` | `mayoristapp_logistica` | pendiente |
| 44 | `tmobile/jcart/relay-mob.php` | Carrito móvil | `ecom` | `mayoristapp_jcart_mob` | pendiente |

---

## Notas

- **`relay-ventas-netas-gerencia-old-31-10-2024.php`:** copia de respaldo en PHP; la migración debe basarse en `relay-ventas-netas-gerencia.php` y en [SPEC_VENTAS_NETAS.md](./SPEC_VENTAS_NETAS.md).  
- El conteo **44** incluye este archivo; si en el futuro se excluye del alcance, actualizar `MAYORISTAPP_RELAY_PATHS`, `RELAY_ENDPOINT_COUNT` y esta tabla en el mismo commit.
