# Pedidos masivos: marcas del vendedor

## Regla funcional

La plantilla Excel de pedidos masivos incluye los artículos de todas las
marcas activas asignadas globalmente al vendedor en
`vendedores_marcas_asignacion`.

Las mismas marcas quedan habilitadas para todas las sucursales activas del
cliente seleccionado. La generación y la importación de la planilla comparten
esta regla para evitar que una fila ofrecida en el template sea rechazada al
volver a cargarla.

## Filtros de artículos

Además de pertenecer a una marca asignada al vendedor, cada artículo debe
cumplir:

- `articulo.Discontinuo = 'No'`
- `articulo.ecommerce = 'Si'`
- `articulo.tipo_art_fab = 'Terminado'`

Las cuaternas de `ecom_vendedor_cliente_marca` continúan vigentes para los
flujos VCM y el catálogo por sucursal, pero no restringen la plantilla de
pedidos masivos.
