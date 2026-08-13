# Manual de usuario — Reportes

## Ventas BOM en docenas

**Ruta:** Catálogo de reportes → *Ventas BOM en docenas* (`/reports/dashboard/ventas-bom-docenas/`).

### Para qué sirve

Muestra cuántos **artículos fabricados (componentes BOM)** salieron por venta, explosionando cada pack facturado según su lista de materiales. Las cantidades se expresan en **docenas** (y pares como control).

### Cómo usarlo

1. Abrí el informe.
2. Elegí el **período** (día, mes, año o personalizado).
3. Opcional: filtrá por sucursal y punto de venta; podés excluir clientes.
4. Pulsá **Actualizar**.
5. Revisá la tabla (una fila por artículo BOM) y los totales de docenas.
6. Pulsá **Exportar Excel** para descargar el mismo resultado en `.xlsx`.

### Notas

- Solo entran packs con receta BOM. Los packs sin lista de materiales no aparecen.
- Una nota de crédito resta cantidades.
- No muestra importe en pesos: el precio de venta corresponde al pack, no al componente.
