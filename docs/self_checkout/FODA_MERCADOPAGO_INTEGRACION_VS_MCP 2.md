# FODA: Integración Mercado Pago actual (Synap) vs MCP Server

> **Solo referencia.** La app `mercadopago` **no está instalada** en la instalación mínima actual. Relevante si se integra MercadoPago en el futuro.

**Fecha:** 2025-01-31  
**Referencias:**  
- [Mercado Pago MCP Server – Resumen](https://www.mercadopago.com.ar/developers/es/docs/mcp-server/overview)  
- [Tools disponibles](https://www.mercadopago.com.ar/developers/es/docs/mcp-server/tools)  
- [Casos de uso](https://www.mercadopago.com.ar/developers/es/docs/mcp-server/use-cases)  
- Propuesta interna: `docs/PROPUESTA_SALES_DEPRECADO_MERCADOPAGO_SELF_CHECKOUT.md`

---

## Contexto

- **Integración actual:** Synap tiene una integración **en runtime** con Mercado Pago: app Django `mercadopago` (config por empresa, create-payment, webhook), flujo Self Checkout → payment_intent → preferencia MP → pago → webhook → `pago_aprobado` → `ConfirmationService` → cuentacliente, stock, caja (administraNET). Todo implementado con código propio y API REST de MP.
- **MCP Server:** Herramienta de **desarrollo** que implementa el [Model Context Protocol](https://modelcontextprotocol.io): el IDE (p. ej. Cursor) se conecta al servidor MCP de Mercado Pago y expone *tools* para buscar documentación, configurar webhooks, simular notificaciones, medir calidad de la integración, crear usuarios de prueba, etc. **No procesa pagos en producción**; acompaña el ciclo de desarrollo y mejora.

El FODA compara **mantener y evolucionar la integración actual** frente a **incorporar el MCP como recurso de desarrollo** (son complementarios, no sustitutos).

---

## FODA: Integración actual vs uso de MCP

| | **Fortalezas** | **Oportunidades** |
|--|----------------|-------------------|
| **Integración actual (Synap)** | • Control total del flujo: preferencia, webhook, payment_intent, cuentacliente, caja, FE.<br>• Sin dependencia de Sales; 100% Self Checkout + administraNET (DB).<br>• Trazabilidad en nuestra DB: `mercadopago_transaction`, `self_checkout_payment_intent`, audit_log.<br>• Encaje con administraNET: `write_caja_ingreso`, tipo "Tarjeta", id_caja_abm.<br>• Config por empresa (MercadoPagoConfig, base_empresa, sandbox). | • Completar UI del kiosco para “Pagar con MercadoPago” (botón, redirect, back_url_success) si aún no está expuesto.<br>• Usar **MCP** para consultar documentación y estándares de calidad sin salir del IDE.<br>• Usar **MCP** para configurar y simular webhooks y validar nuestro endpoint antes de producción.<br>• Usar **MCP** (create_test_user, add_money_test_user) para automatizar datos de prueba. |
| **MCP Server (Mercado Pago)** | • Acceso a documentación y buenas prácticas desde el IDE (lenguaje natural).<br>• Tools listas: búsqueda en docs, lista de campos de calidad, medición de calidad por payment_id, configuración de webhooks, simulación de notificaciones, diagnóstico de notificaciones, usuarios de prueba.<br>• Compatible con Cursor (v1+), VS Code, etc.; estándar abierto MCP.<br>• Acelera onboarding y cambios (ej. nuevos tópicos de webhook, pruebas de calidad). | • Reducir tiempo de debugging de webhooks y de preparación de entornos de prueba.<br>• Aprovechar “Generar código para integrar checkout” y “Optimizar calidad” para alinear nuestra implementación con estándares MP.<br>• Un solo canal (IDE + MCP) para documentación, calidad y pruebas. |

| | **Debilidades** | **Amenazas** |
|--|-----------------|--------------|
| **Integración actual (Synap)** | • Calidad y cumplimiento de estándares MP dependen de revisión manual o de procesos propios.<br>• Configuración y prueba de webhooks (URLs, tópicos) se hace fuera del flujo de desarrollo (panel MP o scripts).<br>• Usuarios/saldos de prueba hay que crearlos y mantenerlos a mano si no se usa MCP. | • Cambios en API o en requisitos de calidad de MP pueden obligar a refactors sin una guía integrada en el IDE.<br>• Errores en webhooks o en calidad retrasan certificación o go-live si no se detectan pronto. |
| **MCP Server (Mercado Pago)** | • **No sustituye** la integración en runtime: no crea preferencias ni recibe pagos reales; es solo herramienta de desarrollo.<br>• Requiere cliente MCP actualizado y credenciales MP configuradas en el cliente.<br>• Alcance limitado a las tools publicadas (hoy no hay tool de “crear preferencia” o “consultar pago” desde MCP). | • Dependencia de disponibilidad y evolución del MCP de MP (nuevas tools, cambios de contrato).<br>• Si el equipo no usa un IDE con MCP, el beneficio es bajo. |

---

## Matriz resumen

| Criterio | Integración actual (Synap) | MCP Server |
|----------|----------------------------|------------|
| **Rol** | Procesar pagos en producción (preferencia, webhook, confirmación, caja). | Apoyar desarrollo: documentación, webhooks, calidad, usuarios de prueba. |
| **Dónde corre** | Backend Django + MySQL (base_empresa) + frontend kiosco. | En el IDE (Cursor, etc.) conectado al servidor MCP de MP. |
| **Sustitución** | No puede ser reemplazada por MCP para el flujo de cobro. | No reemplaza nuestro backend; lo complementa. |
| **Recomendación** | Mantener y completar (UI kiosco, monitoreo, reintentos). | **Adoptar como recurso de desarrollo**: conectar MCP en Cursor, usar tools para docs, webhooks, calidad y pruebas. |

---

## Conclusión

- La **integración actual** es la que hace que los pagos con Mercado Pago funcionen en Synap (Self Checkout + administraNET); debe seguir siendo el núcleo del flujo de cobro.
- El **MCP Server** es un complemento para el **desarrollo**: consultar documentación, configurar y simular webhooks, medir calidad y crear usuarios de prueba desde el IDE, sin sustituir nuestro código.
- **Acción sugerida:** Configurar el [MCP Server de Mercado Pago](https://www.mercadopago.com.ar/developers/es/docs/mcp-server/connection) en Cursor (o el IDE que use el equipo), con las credenciales de la aplicación MP, y usar sus tools para documentación, configuración de notificaciones y pruebas de calidad de la integración existente.
