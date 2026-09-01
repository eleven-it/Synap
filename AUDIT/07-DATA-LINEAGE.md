# 07 — Data Lineage

**Estado:** COMPLETE (Fase 7)  
**Fecha:** 25/08/2026

---

## Procesos críticos — flujos SOURCE → UI

### 1. Login y sesión

```
MySQL database "empresas"
    ↓ SELECT id_empresa, base_empresa
AdministraNETAuth.get_empresas()
    ↓
Formulario login (usuario elige empresa)
    ↓ validate_user(cod, pass, base_empresa)
MySQL database base_empresa → tabla usuarios
    ↓
bootstrap_synap_session()
    ↓
Django session["user"] {base_empresa, id_usuario, id_puesto, ...}
    ↓
RequestScopedMysqlMiddleware → pool MySQL
    ↓
Todas las vistas/servicios del request
```

### 2. Reporte dashboard

```
Usuario → GET /reports/dashboard/{slug}/
    ↓
reports.views.dashboard_detail
    ↓
ReportDefinition (PostgreSQL) → config JSON
    ↓
QueryRunner / ReportExecutionEngine
    ↓
mysql_pool.mysql_cursor(base_empresa)
    ↓
SELECT ... FROM cuentacliente, articulo, stockp ... (MySQL)
    ↓
[Opcional] Redis cache (si REPORTS_CACHE_ENABLED)
    ↓
Template dashboard + widgets Alpine.js
    ↓
Browser
```

### 3. TPV — Venta self-checkout

```
Operador TPV → POST /api/self-checkout/venta/
    ↓
self_checkout services
    ↓
mysql_cursor(base_empresa)
    ↓
INSERT compventa, cuerpocompventa (MySQL)
UPDATE stockp, stock_deposito (MySQL)
UPDATE talonarios (MySQL)
    ↓
fe_afip services → pyafipws SOAP → AFIP (CAE)
    ↓
UPDATE compventa.cae (MySQL)
    ↓
JSON response + ticket impresión
```

### 4. Pedido e-commerce mayorista

```
Vendedor → POST /ecom/api/pedido/
    ↓
ecom/services/pedido_service.py
    ↓
[Opción A] SQL directo → comp_ped, cuerpo_comp_ped (MySQL)
[Opción B] HTTP relay → administraNET-ecom PHP → MySQL
    ↓
EcomCart (PostgreSQL) — estado carrito
    ↓
Aprobación crédito → ecom_credito_evaluacion (MySQL synap table)
    ↓
Confirmación → notificación + mail queue (PostgreSQL)
```

### 5. Captura factura compra

```
Usuario → POST /api/compras/expediente/ (upload PDF/imagen)
    ↓
ExpedienteFacturaCompra (PostgreSQL)
DocumentoFuente (PostgreSQL) — archivo en MEDIA_ROOT
    ↓
[thread] OCR → Tesseract/OpenCV → campos extraídos
    ↓
LineaExpedienteCompra (PostgreSQL)
    ↓
Revisión UI → /compras/captura/revision/{uuid}/
    ↓
Posting → factura_compra_posting → legacy_db (futuro) → cuentaproveedor (MySQL)
```

### 6. Auditoría contable

```
Operador → POST /contabilidad/auditoria/ejecutar/
    ↓
contabilidad_audit.services.checks.*
    ↓
mysql_pool → SELECT cont_asiento, cont_detalle, cuentaproveedor (MySQL)
    ↓
CorridaAuditoria (PostgreSQL) — resultados
PlanCorreccion (PostgreSQL) — si aplica
    ↓
[Futuro] legacy_db.cont_recalculo_service → WRITE cont_asiento (MySQL)
```

### 7. Sync Tienda Nube

```
Webhook Tienda Nube → POST /tiendanube_administranet/webhook/
    ↓
WebhookEvent (PostgreSQL)
    ↓
[Celery task — sin worker] o tiendanube_drain_inbox command
    ↓
ProductMapping / CustomerMapping (PostgreSQL)
    ↓
MySQL → INSERT/UPDATE articulo, cliente (MySQL)
    ↓
SyncLog (PostgreSQL)
```

### 8. MPR — Parte de producción

```
Operario → POST /mpr/api/parte/
    ↓
mpr/services.py
    ↓
INSERT mpr_parte, mpr_parte_linea (MySQL synap tables)
UPDATE stockp, stock_deposito (MySQL adminet tables)
INSERT stockp movimiento (MySQL)
    ↓
MprParte (PostgreSQL) — metadata
    ↓
Tablero KPI → reports integration
```

### 9. Asistente IA

```
Usuario → POST /api/ia/conversacion/
    ↓
AgentDefinition (PostgreSQL) → system_prompt, tools
    ↓
LlmGatewayService → HTTP → OpenAI/Anthropic API
    ↓
[Si tool_call] → servicio interno → mysql_pool (MySQL)
    ↓
AgentMessage, AgentMemoryItem (PostgreSQL)
    ↓
JSON response
```

### 10. Backup DR

```
Cron → manage.py backup_tick
    ↓
BackupJob (PostgreSQL)
    ↓
pg_dump → PostgreSQL artifact
mysqldump → MySQL artifact (por base_empresa)
    ↓
BackupArtifact (PostgreSQL) — SHA256 manifest
    ↓
[SFTP upload] → servidor remoto
```

---

## Transformaciones ocultas

| Transformación | Dónde | Impacto |
|----------------|-------|---------|
| Fecha INT YYYYMMDD ↔ DATE | `query_runner.parse_fecha_bo_yyyymmdd` | Inconsistencia agregados vs renglones |
| latin1 ↔ utf-8 | MySQL charset config | Caracteres especiales |
| AES password AdministraNET | `login/administranet_auth.py` | Compatibilidad VB6 |
| BOM artículos ensamblados | `core/management/commands/unificar_articulo_duplicado_bom.py` | Modifica articulo MySQL |
| Permisos legacy → synap | `backfill_synap_permisos_from_legacy` | Duplicación permisos |
| Cotización BCRA | `sincronizar_cotizacion_bcra` | Actualiza ExchangeRate PG |

---

*Generado por auditoría READ ONLY.*
