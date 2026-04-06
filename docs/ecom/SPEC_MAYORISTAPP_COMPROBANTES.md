# Spec — Comprobantes mayoristapp (pedidos, presupuestos, remitos, mail)

**Relays:** `relay-pedidos.php`, `relay-presupuestos.php`, `relay-remitos.php`, `relay-comprobantes-ncancelados.php`, `relay-comp-no-cancelados-resumen.php`, `relay-comprobante-a-mail.php`.  
**Checkpoint sugerido:** `mayoristapp_comprobantes` (salvo mail: puede unificarse al mismo vertical).

---

## 1 — Alcance

- Listados filtrados por vendedor/cliente/estado (paridad con sesión PHP).
- Resúmenes de no cancelados.
- Envío de comprobante por correo (integración posterior; no hardcodear credenciales).

---

## 2 — Synap objetivo

- Tablas centrales AdministraNET: `comp_ped` y relacionadas (ver docs tablas en `docs/general/` / `docs/reports/`).
- Escrituras compatibles VB6 solo vía políticas ya definidas en `legacy_db` si aplica.

---

## 3 — Decisiones Fase B

- **[DECISIÓN-B-C1]** Priorizar **solo lectura** en primera iteración salvo que negocio exija alta desde e-com.
- **[DECISIÓN-B-C2]** Mail: usar capa de notificaciones Django (async opcional); no portar lógica SMTP embebida del PHP sin revisión de seguridad.

---

## 4 — API Synap v1 (solo lectura)

| Relay PHP | Método | Ruta Synap | Notas |
|-----------|--------|------------|--------|
| `relay-pedidos.php` (listado ajax) | POST | `/ecom/api/mayoristapp/comprobantes/pedidos/?ajax=1` | Cuerpo JSON: `vendedor`, `campoBusca`, `fechaDesde`/`fechaHasta`, `numeroComp`, `estadoPedido`, `tipoPedido`, `listaPed`, `filtraVendedor`, `limit`. Respuesta `{ "total", "filas" }`. |
| `relay-presupuestos.php` | POST | `/ecom/api/mayoristapp/comprobantes/presupuestos/?ajax=1` | Mismo estilo; `TipoComprobante` = PRE en servidor. |
| `relay-remitos.php` | POST | `/ecom/api/mayoristapp/comprobantes/remitos/?ajax=1` | `tipoRemito` opcional; filtro cliente (`idcliente` sesión) o `IdUsuario`. |
| Autocomplete `queryString` | GET | `/ecom/api/mayoristapp/comprobantes/sugerencias-nro/?ajax=1&q=…&tipo=PED\|PRE\|REM` | Lista de `NroCompBusq` con prefijo. |
| `relay-comprobantes-ncancelados.php` | POST | `/ecom/api/mayoristapp/comprobantes/no-cancelados/?ajax=1` | Filtra en `recibo_factura` (`Estado='N/Canc'`, `Anulado='No'`, `Saldo<>0`, `idcliente` sesión). Devuelve `SaldoSigned` y `SaldoAcum` por fila. |
| `relay-comp-no-cancelados-resumen.php` | POST | `/ecom/api/mayoristapp/comprobantes/no-cancelados-resumen/?ajax=1` | Mismos filtros; salida resumida con campo `Resumen` y `saldo_al_dia`. |
| `relay-pedidos.php` (`anularPedido=1`) | POST | `/ecom/api/mayoristapp/comprobantes/anular-pedido/?ajax=1` | Actualiza `Anulado='Si'` en `comp_ped`, `stockp`, `percep_cli` dentro de transacción. |
| `relay-comprobante-a-mail.php` | GET | `/ecom/api/mayoristapp/comprobantes/comprobante-a-mail/?codMov=…&tipocomprobante=…` | Resuelve comprobante (`cuentacliente`/`comp_ped`) y devuelve `{ comprobante, token, redirect_path }` para `fin-comprobante`; sin envío SMTP en v1. |
| Enqueue mail async | POST | `/ecom/api/mayoristapp/comprobantes/comprobante-a-mail/enqueue/?ajax=1` | Encola envío a `email` con `codMov` + `tipocomprobante`; procesa por comando `process_ecom_mail_queue`. |
| Estado cola mail | GET | `/ecom/api/mayoristapp/comprobantes/comprobante-a-mail/queue-status/?ajax=1&queue_id=...` | Consulta estado de envío (`pending/sent/error`), intentos y último error. |

Columna importes: se usa `comp_ped.SubtotalDesc` (nombre físico MySQL). SMTP productivo: disponible vía cola async (`ecom.EcomMailQueue`) + worker por comando.

### UX Synap (lista presupuestos vendedor)

| PHP | Synap |
|-----|--------|
| `lista-presupuestos-vendedor.php` | GET `/ecom/mayoristapp/presupuestos-vendedor/` (`ecom:mayoristapp_presupuestos_vendedor`) |

- Plantilla `ecom/templates/ecom/presupuestos_vendedor.html` (estilo Synap: `base_app`, Tailwind).
- Filtros alineados al PHP: vendedor/viajante (combo desde `viajantes` según `id_puesto`), clientes (todos / seleccionado en sesión), estado, buscar por fecha / número / tipo presupuesto.
- Resultados: POST JSON a `/ecom/api/mayoristapp/comprobantes/presupuestos/?ajax=1` (mismo cuerpo que `relay-presupuestos.php`).
- Tabla con totales de subtotal, IVA y total; filas en rojo si `Anulado` = Sí.
- **Pendiente:** modal PDF / mail como en PHP (`ver_presupuesto-movil.php`, `relay-comprobante-a-mail.php`) — enlaces se pueden añadir cuando exista ruta equivalente en Synap.

Comando worker recomendado:
- `docker exec Synap_app python manage.py process_ecom_mail_queue --limit 50`
- `docker exec Synap_app python manage.py process_ecom_mail_queue --limit 50 --retries --max-attempts 5`

---

## 5 — Pendientes Fase C

- Un spec anexo por flujo crítico (pedido vs remito) si divergen mucho.
- Tests con MySQL integración marcados `@pytest.mark.integration`.
- Demás escrituras fuera de anulación (si negocio las requiere) según política `legacy_db`.
