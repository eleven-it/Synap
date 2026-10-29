# Pedido individual: textos del comprobante y stock Terminado

En el pie del pedido individual se pueden escribir **Detalle de comprobante**
y **Observación interna**. Al confirmar, Synap guarda el primer texto en
`comp_ped.Detalle` y el segundo en `comp_ped.observacion_interna`, para que
ambos aparezcan en la cabecera del pedido normal de administraNET. Al abrir
un pedido existente, los campos muestran los valores guardados.

La ficha de un artículo muestra el desglose de stock por depósito únicamente
para depósitos cuyo `tipo_mpr` es `Terminado`. El indicador «Stock disponible
del pedido» conserva el cálculo del depósito asignado al pedido.

Verificación funcional: crear un pedido individual con ambos textos, abrirlo
en administraNET y comprobar que las dos cabeceras coinciden. Abrir la ficha
de un artículo con existencias en depósitos de distinto tipo y comprobar que
solo figuran en el desglose los depósitos Terminado.
