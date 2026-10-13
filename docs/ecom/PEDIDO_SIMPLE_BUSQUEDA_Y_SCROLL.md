# Pedido simple: búsqueda y desplazamiento

Fecha: 13/10/2026.

En escritorio, el encabezado comercial y el pie pueden superar el alto que se
reservaba para la pantalla completa. Pedido simple permite ahora desplazar la
página y asigna un alto propio a la matriz para que sus filas conserven el
desplazamiento interno. El buscador de artículos ocupa la primera fila; al
enfocarlo, la matriz vuelve a esa fila.

En móvil, la búsqueda de cliente, sucursal y artículo usa el teclado nativo.
La lista de artículos abre hacia arriba; las de cliente y sucursal, hacia
abajo. En artículos, «Revisar seleccionados» queda al pie de la lista, junto
al buscador. Tras estabilizarse el teclado, se acomoda una sola vez el campo y se
limita la lista al espacio disponible según `visualViewport`. No se reacciona
al evento de desplazamiento del viewport para evitar saltos repetidos. El pie
de totales se oculta durante la búsqueda y reaparece al cerrarla. El tamaño
del teclado lo define Android o la aplicación de teclado elegida por la
persona.

Verificación funcional sugerida: abrir un borrador simple con artículos, bajar
por la página en escritorio y buscar/agregar un artículo; en Android, abrir
cada búsqueda, escribir con el teclado visible, recorrer resultados y elegir
uno sin que el pie tape la lista.
