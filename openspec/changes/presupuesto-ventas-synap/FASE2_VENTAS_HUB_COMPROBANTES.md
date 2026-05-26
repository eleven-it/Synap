# Pendiente fase 2 — Hub tipo `CargaComprobantesPed` (Ventas)

**Estado:** no implementar en v1 del Presupuesto Synap.  
**Relación:** complementa el cambio OpenSpec `presupuesto-ventas-synap` cuando existan en Synap los flujos **Pedido** y/o **Remito de venta** desde la misma experiencia que en VB6.

## Alcance futuro (referencia VB6)

- Shell única con **grilla de clientes**, menú contextual **Presupuesto / Pedido / Remito**, **`tipo_comp_carga`** (sistema vs talonario) antes de abrir el formulario de emisión correspondiente.
- Coherencia con `CargaComprobantesPed.frm` (`administranet_vb6`).

## Dependencias

- Implementación y rutas de **Pedido** y **Remito** en Synap (o decisión explícita de solo enlazar a VB6).
- Reutilizar los **mismos servicios** de dominio que v1 PRE (ya desacoplados de la lista principal como home).

## Notas

- La lista principal de **solo PRE** (home con estado y filtros, misma línea de UX acordada para v1) permanece; el hub es una **vista alternativa de entrada** para usuarios que trabajan como en el escritorio legacy.
