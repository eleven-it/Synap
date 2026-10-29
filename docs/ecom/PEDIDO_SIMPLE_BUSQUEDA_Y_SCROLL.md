# Pedido simple: búsqueda y desplazamiento

Fecha: 13/10/2026.

En escritorio, el encabezado comercial y el pie pueden superar el alto que se
reservaba para la pantalla completa. Pedido simple permite ahora desplazar la
página y asigna un alto propio a la matriz para que sus filas conserven el
desplazamiento interno. El buscador de artículos ocupa la primera fila; al
enfocarlo, la matriz vuelve a esa fila.

En móvil, la búsqueda de cliente, sucursal y artículo usa el teclado nativo.
Las listas de cliente y sucursal abren hacia abajo. En pedido simple, al
enfocar el artículo se abre una vista de búsqueda que ocupa el área visible
encima del teclado: campo arriba, resultados desplazables y botón verde
«Ver (n)» junto a «Cerrar» en la cabecera. El botón indica cuántos artículos
están seleccionados y abre su revisión sin desplazarse al pie. `visualViewport`
ajusta la altura cuando aparece o se
oculta el teclado. Los filtros y el resto del pedido quedan detrás de esta
vista y reaparecen al cerrarla; el tamaño del teclado lo define Android o la
aplicación elegida por la persona. La ficha del artículo cierra la búsqueda
antes de abrirse. No se reacciona al desplazamiento del viewport para evitar
saltos repetidos en las búsquedas de cliente y sucursal.

El catálogo del pedido muestra artículos Tercero o Terminado, no discontinuados,
con e-commerce activo y marca asignada al vendedor para el cliente y la sucursal.
Los filtros opcionales de marca, rubro y subrubro se suman a esas condiciones.
La búsqueda por texto acepta nombre, código manual, código interno, código de
artículo, código de proveedor y ambos códigos de barras. El texto permanece
aplicado al cambiar filtros o pasar a galería; «Ver todos» limpia el texto.
Al escribir se ocultan los resultados anteriores mientras llega la nueva búsqueda.

Verificación funcional sugerida: abrir un borrador simple con artículos, bajar
por la página en escritorio y buscar/agregar un artículo; en Android, abrir
cada búsqueda, escribir con el teclado visible, recorrer resultados, abrir una
ficha y revisar varios artículos desde el botón de la cabecera.
