# 05 — Notification Artifacts

**Estado:** COMPLETE

| Channel | Implementation | Use case |
|---------|----------------|----------|
| **Toast (UI)** | `SynapMessages` | Success/error inline |
| **Modal aviso** | `mprShowAviso` | MPR confirmations/info |
| **Django messages** | session flash → toast | Form redirects |
| **Email** | `core/services/outbound_email.py` | SMTP configurable |
| **Email queue** | `EcomMailQueue` + `process_ecom_mail_queue` | Comprobantes async |
| **Backup notify** | `core/backup/services/notify.py` | DR alerts |
| **Crédito avisos** | `ecom/credito_pedidos/avisos.py` | Finance queue |
| **Webhook** | TN inbound | External notification |

**Not found:** WhatsApp, SMS, push notifications (beyond PWA install).

## Inconsistency

3 UI feedback channels (toast, modal, inline) — unify under design system.
