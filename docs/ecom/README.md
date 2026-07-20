# Documentación E-commerce / Ventas (ecom)

Documentación del módulo **ecom** en Synap: portal mayorista, pedidos, cobranzas, logística e integraciones.

## Manual de usuario

| Documento | Descripción |
|-----------|-------------|
| [MANUAL_USUARIO_VENTAS.md](MANUAL_USUARIO_VENTAS.md) | **Manual de usuario Ventas** (presupuestos, pedidos, precios, ajustes, objetivos). Primera versión. |
| [manual_usuario_ventas.html](manual_usuario_ventas.html) | **Manual HTML** navegable (generado desde el MD). En la app: **`/ecom/manual/`** (requiere login). Regenerar: `python3 scripts/generar_manuales_html.py`. |

### Botón Ayuda en pantallas

Las pantallas del menú **Ventas** incluyen un botón **Ayuda** (`includes/btn_manual_ayuda.html`) que abre `/ecom/manual/#<sección>` en una pestaña nueva. Secciones: presupuestos, pedidos-hub, pedido-masivo, vendedor-cliente-marca, precios-terminados, evolucion-precios, ajustes-ventas, asignacion-vendedor, objetivos-venta.

## Índice técnico

Ver [MAYORISTAPP_SPEC_INDICE.md](MAYORISTAPP_SPEC_INDICE.md) y [SPEC.md](SPEC.md) para especificaciones detalladas del portal mayorista.
