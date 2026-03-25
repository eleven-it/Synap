# Product Requirements: captura y aprobación de facturas de compras (PWA + desktop)

**Versión:** borrador de especificación.  
**Fuente legacy:** [auditoria_facturas_compras_resumen.md](auditoria_facturas_compras_resumen.md), [auditoria_facturas_compras_flujo_completo.md](auditoria_facturas_compras_flujo_completo.md), [auditoria_facturas_compras_reglas_negocio.md](auditoria_facturas_compras_reglas_negocio.md), [especificacion_tecnica_replicacion_factura_compra.json](especificacion_tecnica_replicacion_factura_compra.json).

**Convención:** *Confirmado por auditoría* | *Decisión nueva de producto* | *Riesgo pendiente*

---

## 1. Problema

Las facturas de compra siguen ingresándose en gran medida vía **AdministraNET Gestión (VB6)** con carga manual de datos. Eso genera:

- lentitud y errores de transcripción
- poca trazabilidad del **origen documental** (papel/PDF) antes del asiento en el ERP
- dificultad para equipos móviles o proveedores que envían PDF

*Decisión nueva de producto:* centralizar la **captura documental** (cámara / PDF) y un **workflow de revisión** antes de impactar el ERP compartido.

---

## 2. Objetivos

1. Permitir crear un **expediente en borrador** desde **foto** o **PDF**, con **OCR y extracción preliminar**, sin escribir en tablas legacy hasta **aprobación** explícita. *Decisión nueva de producto.*
2. Al **aprobar**, ejecutar un **posting** que respete el circuito documentado en la auditoría VB6 (numeración, cabecera, detalle, efectos colaterales, orden). *Confirmado por auditoría* como comportamiento a replicar en destino.
3. Reducir errores de datos mediante **revisión humana** (analista de compras) con estados claros y auditoría interna. *Decisión nueva de producto.*
4. Ofrecer experiencia **mobile-first PWA** sin renunciar a **desktop** para revisión intensiva. *Decisión nueva de producto.*

---

## 3. Alcance

- Captura: cámara y subida de PDF. *Decisión nueva de producto.*
- OCR / extracción estructurada **best-effort** + edición manual. *Decisión nueva de producto.*
- Estados: borrador → en revisión → aprobado / rechazado; registro de eventos. *Decisión nueva de producto.*
- Vinculación a **empresa / sucursal / usuario** del contexto Synap (equivalente a `Principal.*` en VB6 en el momento del posting). *Inferencia desde auditoría* (`idUsuario`, `codSucursal`, flags).
- Posting a MySQL legacy **solo en aprobación**, replicando validaciones y orden de la auditoría. *Confirmado por auditoría* (lista de tablas y flujo en `auditoria_facturas_compras_tablas_campos.md`, `auditoria_facturas_compras_sql.md`).

---

## 4. No alcance (fase inicial)

- Reemplazo completo de **CargaComprobantesP** / menú VB6 para todos los orígenes el día 1. *Decisión nueva de producto.*
- Contabilidad avanzada fuera del flujo estándar documentado (p. ej. nuevas parametrizaciones no presentes en `generar_asiento_cont`). *Riesgo pendiente* si el cliente tiene forks.
- Integración con AFIP u otros organismos desde esta app (el VB6 tampoco crea tabla explícita «libro_iva» en PFactura; ver [auditoria_facturas_compras_resumen.md](auditoria_facturas_compras_resumen.md)). *Confirmado por auditoría* (ausencia en PFactura).

---

## 5. Actores

| Actor | Rol |
|-------|-----|
| **Capturador** | Sube foto/PDF; puede ser mismo analista o rol logístico. *Decisión nueva de producto.* |
| **Analista de compras** | Revisa, edita, aprueba o rechaza. *Decisión nueva de producto.* |
| **Administrador** | Permisos, parámetros de workflow, posiblemente configuración de posting. *Decisión nueva de producto.* |
| **Sistema legacy AdministraNET** | MySQL compartido; consumido solo vía **posting** tras aprobación. *Confirmado por auditoría* (tablas impactadas). |

---

## 6. Casos de uso (resumen)

| ID | Caso | Resultado |
|----|------|-----------|
| UC-01 | Capturar con cámara | Expediente borrador + archivo + job OCR. *Decisión nueva.* |
| UC-02 | Subir PDF | Idem. *Decisión nueva.* |
| UC-03 | OCR exitoso | Campos prellenados editables; confianza por campo (opcional). *Decisión nueva.* |
| UC-04 | OCR fallido | Borrador igual; analista carga manual. *Decisión nueva.* |
| UC-05 | Enviar a revisión | Estado workflow; notificación opcional. *Decisión nueva.* |
| UC-06 | Editar borrador / en revisión | Validaciones de negocio Synap (formato, obligatorios); **sin** tocar legacy. *Decisión nueva.* |
| UC-07 | Rechazar | Estado rechazado + motivo; sin posting. *Decisión nueva.* |
| UC-08 | Aprobar | Dispara **posting legacy** atómico según spec. *Confirmado por auditoría* (qué escribir); *decisión nueva* (cuándo). Ver [adrs/0001-momento-escritura-mysql-legacy.md](adrs/0001-momento-escritura-mysql-legacy.md). |
| UC-09 | Posting con error | Rollback legacy; expediente en estado **error de posting** con diagnóstico. *Decisión nueva de UX*; *confirmado por auditoría* que VB6 hace `RollbackTrans` en `captura:`. |

---

## 7. Reglas funcionales

### 7.1 Reglas del producto (Synap, pre-posting)

- No escribir en tablas `cuentaproveedor`, `stock`, `codmov`, etc. mientras el expediente no esté **aprobado**. *Decisión nueva de producto* (explicitada en ADR-0001).
- Mantener **trazabilidad** de archivo original, hash opcional, y versiones de extracción OCR. *Decisión nueva de producto.*
- Permitir mapear **proveedor** y **ítems** a maestros Synap/legacy (IDs) antes de aprobar. *Decisión nueva de producto*; el legacy exige `CodigoProv`, `IDArt`, etc. *Confirmado por auditoría* (`auditoria_facturas_compras_tablas_campos.md` Anexo A).

### 7.2 Reglas en aprobación (deben alinearse al legacy)

Referencia principal: [auditoria_facturas_compras_reglas_negocio.md](auditoria_facturas_compras_reglas_negocio.md).

Ejemplos *confirmados por auditoría*:

- Período fiscal abierto y no vencido respecto a fecha de referencia del sistema (equivalente `Principal.Fecha` + consulta `periodos`/`years`).
- Numeración global `codmov` antes del cuerpo del comprobante (en VB6 en dos transacciones; ver ADR-0002).
- Contado: `cond_venta.Dias = "0"` → `caja` + `caja_saldo` + `Estado = Canc` en cabecera; crédito → `op_factura` + `N/Canc`.
- Origen **Factura Remito / OC / Vale**: mismas validaciones de buffer que VB6 sobre datos equivalentes (en Synap modelados en dominio interno, no en `cuerpostockp` hasta posting — ver ADR-0003).

---

## 8. Estados del workflow

*Decisión nueva de producto* (nombres orientativos):

| Estado | Descripción |
|--------|-------------|
| `borrador` | Creado; OCR en curso o pendiente. |
| `ocr_completado` | OCR terminó (éxito o fallo marcado). |
| `en_revision` | Asignado a analista. |
| `listo_para_aprobar` | Opcional: checklist cumplido. |
| `aprobado` | Posting **exitoso**; vínculo a `CodigoMovimiento` legacy. |
| `rechazado` | Sin posting; motivo obligatorio. |
| `error_posting` | Aprobación intentada; legacy falló; reintentable. |

Transiciones documentadas en [domain_model.md](domain_model.md).

---

## 9. Pantallas (UX)

*Decisión nueva de producto* — mobile-first:

1. **Inicio / lista de expedientes** (filtros por estado, fecha, proveedor).
2. **Nuevo: elegir cámara o PDF**.
3. **Detalle expediente**: vista documento + pestañas cabecera / renglones / totales / adjuntos.
4. **Edición**: formularios alineados a campos que el posting esperará (mapear a Anexo A y cabecera `cuentaproveedor` en auditoría).
5. **Aprobar / Rechazar** con confirmación y resumen de impacto legacy (texto ayuda).
6. **Historial / auditoría interna** (quién cambió qué).

**Decisiones UX clave:**

- Mostrar **advertencias** de validación legacy *antes* de aprobar (período cerrado, duplicado potencial, falta de lote obligatorio, etc.). *Basado en auditoría* (`Validacion_Comp`, validación lote ~4447 PFactura).
- No prometer «guardado en ERP» hasta aprobación exitosa.

---

## 10. Permisos

*Decisión nueva de producto* (a detallar con modelo de permisos Synap existente):

- `factura_compra_captura.crear`, `.ver`, `.editar`, `.revisar`, `.aprobar`, `.rechazar`, `.reintentar_posting`.
- Separar **aprobar** de **capturar** donde la gobernanza lo requiera.

---

## 11. Integración con MySQL legacy

- **Solo escritura** en tablas listadas en [legacy_integration_spec.md](legacy_integration_spec.md) y en `especificacion_tecnica_replicacion_factura_compra.json`.
- Uso de tipos normalizados según `.cursorrules`: `core.utils.administranet_types` en implementación futura.
- Conexión dedicada **legacy** (pool separado opcional) para no mezclar con DB interna del workflow.

---

## 12. Criterios de aceptación funcionales (muestra)

| ID | Criterio | Evidencia auditoría |
|----|----------|---------------------|
| CA-01 | Aprobar expediente contado genera registro en `caja` y actualiza `caja_saldo` coherente con `ImporteTotal` | `auditoria_facturas_compras_flujo_completo.md` §C.8 |
| CA-02 | Aprobar crédito genera `op_factura` y `cuentaproveedor.Estado = N/Canc` | Mismo + `reglas_negocio` §D |
| CA-03 | `proveedor.saldo` coincide con lógica cabecera según `cond_venta` | `tablas_campos` §1, `resumen` §3 |
| CA-04 | Cada ítem aprobado genera fila `stock` con campos mapeados según Anexo A | `tablas_campos` Anexo A |
| CA-05 | Período fiscal cerrado bloquea aprobación con mensaje claro | `reglas_negocio` §B |
| CA-06 | Duplicado FA/FC/FB detectado según reglas `Validacion_Comp` (y política FM por ADR-0004) | `auditoria_facturas_compras_sql.md`, `pendientes_dudas` |
| CA-07 | Error en mitad del posting deja legacy sin comprobante parcial (rollback) | `flujo_completo` §C.9 |

Lista extensible en [test_cases.md](test_cases.md).

---

## 13. Referencias cruzadas

- Arquitectura: [architecture.md](architecture.md)  
- Dominio: [domain_model.md](domain_model.md)  
- Índice del módulo: [README.md](README.md)
