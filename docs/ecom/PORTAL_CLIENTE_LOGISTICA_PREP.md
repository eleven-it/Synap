# Preparación — Portal de cliente · trazabilidad post-remito

**Estado:** contrato y columnas definidas; **sin** rutas públicas ni UI de portal en esta iteración.

## Fuente de verdad

- MySQL `comp_ped` (remito / pedido vinculados): `entregado`, `fecha_hora_entrega`, `id_usuario_no_entrega`, `motivo_no_entrega`, `detalle_no_entrega`.
- Catálogo opcional: tabla `logi_motivo_no_entrega` (motivos parametrizables; campo `visible_portal` para filtrar qué puede exponerse al cliente).

## Contrato de lectura (Python)

- Módulo `logistica.portal_compat`: `EntregaTrazabilidadCliente` y `entrega_desde_detalle_remito()` convierten el diccionario devuelto por `obtener_detalle_remito()` en una vista estable para futuras APIs del portal.

## Próximos pasos (fuera de alcance actual)

- Autenticación del cliente (token / enlace firmado / cuenta).
- Endpoints read-only filtrados por cliente y `visible_portal`.
- No duplicar escritura: el portal solo **consulta** el mismo estado que ya refleja el informe `comprobantes-rutas`.
