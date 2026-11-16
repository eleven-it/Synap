# Command Center V45: contraste y escala del detalle

Corrección visual para la prueba de Best Sox del 13/10/2026:

- El diálogo de detalle se muestra por encima de la barra de navegación (barra `z-index: 60`, diálogo `z-index: 70`), por lo que su encabezado y botón Cerrar quedan visibles.
- Los selectores de Vista, Agrupación, Gráfico y Orden definen colores de texto y fondo para sus opciones en tema claro y oscuro.
- La superficie del detalle y los KPI tienen color de texto explícito en ambos temas; las tablas de ranking heredan el contraste correspondiente.
- Los SVG de los gráficos del tablero se limitan a 720 px de ancho para mantener una altura comparable entre gráficos de dos columnas y comparaciones de ancho completo.

Validación funcional pendiente en Best Sox: abrir Ventas netas y Posiciones fiscales, alternar claro/oscuro con el detalle abierto, desplegar Agrupación, verificar el encabezado y comparar tamaños de los gráficos en escritorio y celular.
