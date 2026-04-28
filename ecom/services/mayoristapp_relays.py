"""
Inventario canónico de relays bajo mayoristapp/ (administraNET-ecom).

Debe mantenerse alineado a docs/ecom/MAYORISTAPP_RELAYS.md y al clon PHP.
La longitud del tuple debe coincidir con RELAY_ENDPOINT_COUNT en migration_info.
"""

from __future__ import annotations

# Rutas relativas a mayoristapp/ (orden lexicográfico estable)
MAYORISTAPP_RELAY_PATHS: tuple[str, ...] = (
    "jcart/relay.php",
    "relay-art-rapido.php",
    "relay-art.php",
    "relay-articulo-remito.php",
    "relay-cliente-domicilio.php",
    "relay-cliente-rapido.php",
    "relay-clientes.php",
    "relay-comp-no-cancelados-resumen.php",
    "relay-comprobante-a-mail.php",
    "relay-comprobantes-ncancelados.php",
    "relay-consumos-resumen.php",
    "relay-contacto-cliente.php",
    "relay-ctacte.php",
    "relay-cuenta-corriente.php",
    "relay-devoluciones.php",
    "relay-envio-calculo.php",
    "relay-filtros-estadisticas.php",
    "relay-laboratorio.php",
    "relay-lista-precio.php",
    "relay-logistica-comprobantes.php",
    "relay-lote.php",
    "relay-marca.php",
    "relay-mas-vendidos.php",
    "relay-pedidos.php",
    "relay-presupuestos.php",
    "relay-promociones.php",
    "relay-proveedor.php",
    "relay-recibos.php",
    "relay-remitos.php",
    "relay-rubro-catalogo.php",
    "relay-rubro.php",
    "relay-stock-autocomplete.php",
    "relay-stock-existencias.php",
    "relay-tacc.php",
    "relay-tipo-cliente.php",
    "relay-ventas-netas-gerencia-old-31-10-2024.php",
    "relay-ventas-netas-gerencia.php",
    "relay-ventas-netas.php",
    "relay_factura_electronica.php",
    "relay_facturas_imputar.php",
    "relay_geolocalizacion.php",
    "relay_nota_credito.php",
    "relay_ruta_logistica.php",
    "tmobile/jcart/relay-mob.php",
)


def mayoristapp_relay_inventory_dict() -> dict:
    """Estructura para JSON (API inventario relays)."""
    return {
        "mayoristapp_relay_count": len(MAYORISTAPP_RELAY_PATHS),
        "relays": list(MAYORISTAPP_RELAY_PATHS),
    }
