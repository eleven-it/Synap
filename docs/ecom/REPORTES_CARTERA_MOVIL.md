# Reportes de cartera en móvil

Las pantallas **Cuenta corriente** y **Comprobantes a cobrar** muestran el cliente activo y un buscador predictivo dentro del informe. Al enfocar o vaciar el buscador se listan hasta 15 clientes accesibles de la cartera; al escribir se filtra por nombre o código. Flecha abajo permite ampliar a 50 resultados. La selección guarda el cliente en la sesión y recarga el informe, que consulta sus datos automáticamente. **Actualizar** repite la consulta y **Descargar reporte** exporta las filas visibles como CSV.

El endpoint `mayoristapp_clientes_buscar` acepta `modoBus=lista` con texto vacío para el desplegable inicial. Mantiene la misma restricción de vendedor y el parámetro `cartera=1` que la búsqueda con texto. El servidor vuelve a comprobar que el cliente seleccionado pertenece a la cartera antes de mostrar cualquiera de los dos informes.
