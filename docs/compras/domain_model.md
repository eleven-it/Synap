# Domain model: expedientes de factura de compra + posting legacy

**Fuente legacy:** [auditoria_facturas_compras_objetos_vb6.md](auditoria_facturas_compras_objetos_vb6.md), [auditoria_facturas_compras_tablas_campos.md](auditoria_facturas_compras_tablas_campos.md), [ORIGEN_DATOS_FACTURA_COMPRA_VB6.md](ORIGEN_DATOS_FACTURA_COMPRA_VB6.md).

**Convención:** *Confirmado por auditoría* | *Decisión nueva de producto* | *Riesgo pendiente*

---

## 1. Separación de contextos

### 1.1 Dominio nuevo (Synap — bounded context «Captura y aprobación»)

*Decisión nueva de producto.*

- **ExpedienteFacturaCompra** (aggregate root): encapsula ciclo de vida del borrador hasta aprobación o rechazo.
- **DocumentoFuente**: archivo (imagen/PDF), metadatos, almacenamiento.
- **ExtraccionOCR**: resultado del pipeline asíncrono; campos candidatos y confianza.
- **Revision** / **DecisionAprobacion**: actor, timestamp, comentarios.
- **AuditLogInterno**: eventos de dominio (no confundir con tablas legacy de auditoría si existieran).

No persiste en `cuerpostockp`, `percep_prov_temp`, etc. *Decisión nueva* — ver ADR-0003.

### 1.2 Dominio legacy (bounded context «Posting AdministraNET»)

*Confirmado por auditoría:* entidades **no son ORM Django sobre el mismo modelo de expediente**, sino **efectos** sobre tablas MySQL existentes (`cuentaproveedor`, `stock`, …).

- **LegacyComprobanteCompraPosted**: value object / DTO de resultado: `CodigoMovimiento`, `NroComprobante`, timestamps, posible `nro_asiento` si contabilidad.
- **LegacyPostingCommand**: comando inmutable construido desde el expediente aprobado + referencias a maestros legacy.

---

## 2. Entidades principales (Synap)

### 2.1 ExpedienteFacturaCompra (aggregate root)

**Invariantes (*decisión nueva*, alineadas a validaciones legacy en aprobación):**

- No puede pasar a `aprobado` sin **proveedor legacy resuelto** (`CodigoProv`).
- No puede pasar a `aprobado` sin **condición de compra** (`id_condcompra` / días) coherente con la rama contado/crédito esperada.
- Renglones: cada uno con **artículo** (`IDArt`) o gasto (`Codgasto`) según reglas; si lote obligatorio en legacy, debe estar completo antes de aprobar (*confirmado por auditoría*, validación ~4447 PFactura).
- **Origen del comprobante** (*confirmado por auditoría*): análogo a `TipoComprobante` / origen en [ORIGEN_DATOS_FACTURA_COMPRA_VB6.md](ORIGEN_DATOS_FACTURA_COMPRA_VB6.md): Manual, Remito, OC, Vale.

**Identidad:** UUID o bigserial interno Synap; distinto de `CodigoMovimiento` legacy.

### 2.2 DocumentoFuente

- Tipo: `imagen` | `pdf`
- URI almacenamiento, MIME, tamaño, hash SHA-256 (recomendado). *Decisión nueva.*

### 2.3 LineaExpedienteCompra

Mapeo lógico a una fila futura de `stock` + datos para `stock_deposito` / `stockp` / lote / serie.

Campos candidatos alineados a **Anexo A** de `auditoria_facturas_compras_tablas_campos.md` (*confirmado por auditoría* para nombres legacy objetivo).

### 2.4 PercepcionExpediente

Análogo funcional a filas que en VB6 pasan por `percep_prov_temp` → `percep_prov` (*confirmado por auditoría*).

### 2.5 ValeVinculado (opcional)

Si el producto soporta origen Vale: referencias a movimientos de vale a enlazar en posting (`en_vale_factura`, `en_vale_viaje`). *Confirmado por auditoría* para tablas; *riesgo pendiente* limpieza temp en VB6.

---

## 3. Value objects

| VO | Descripción |
|----|-------------|
| **Money** | Importe + moneda; en posting legacy pesos según VB6 para caja (`"Pesos"` en flujo contado). *Confirmado por auditoría* (`PFactura` ~4039). |
| **NumeroComprobanteFormateado** | PV + guión + número con ceros; misma regla que VB6. *Confirmado por auditoría* (`flujo_completo` / `sql`). |
| **LetraFiscal** | FA, FB, FC, FM desde reglas fiscales proveedor/empresa. *Confirmado por auditoría* (CargaComprobantesP / PFactura). |
| **OrigenComprobante** | Enum: `MANUAL`, `REMITO`, `OC`, `VALE`. *Confirmado por auditoría* (`ORIGEN_DATOS…`). |

---

## 4. Aggregates y límites transaccionales

| Aggregate | Límite transaccional Synap | Límite transaccional legacy |
|-----------|----------------------------|-----------------------------|
| Expediente + líneas + percepciones + documentos | Una transacción DB Synap por operación de usuario (guardar borrador, aprobar intento interno) | **No participa** hasta comando posting |
| Posting | N/A | **Una transacción atómica** recomendada (ADR-0002) sobre MySQL |

---

## 5. Lifecycle (estado)

```
[borrador] → ocr_completado → [en_revision] → (rechazado)
                              ↘ [listo_para_aprobar] opcional
                              → [aprobación solicitada]
                              → éxito → [aprobado] + LegacyPosted
                              → fallo → [error_posting]
```

*Decisión nueva de producto* para nombres; transiciones validadas por máquina de estados en tests ([test_cases.md](test_cases.md)).

---

## 6. Servicios de dominio (contratos conceptuales, sin implementación)

```text
ExpedienteService.crear_desde_captura(archivo, metadatos_usuario) -> ExpedienteId
OCRPipeline.encolar(expediente_id) -> job_id
ExpedienteService.actualizar_datos_legacy_preview(expediente_id, dto) -> None
AprobacionService.solicitar_aprobacion(expediente_id, actor_id) -> None
PostingLegacyService.ejecutar(LegacyPostingCommand) -> LegacyComprobanteCompraPosted
```

`LegacyPostingCommand` se construye desde expediente **solo** si invariantes y pre-validaciones legacy pasan. *Confirmado por auditoría* el contenido mínimo del comando equivale a datos usados en `Guardar` (`auditoria_facturas_compras_flujo_completo.md`).

---

## 7. Mapeo conceptual expediente → `Guardar` VB6

| Concepto Synap | Analogía VB6 | Auditoría |
|----------------|--------------|-----------|
| Cabecera expediente | `cuentaproveedor` + controles PFactura | `tablas_campos` §1 |
| Líneas | `CuerpoStock` / `cuerpostockp` → `stock` | Anexo A |
| Percepciones IB | `percep_prov_temp` | `sql.md`, `reglas_negocio` §E |
| Origen OC/Remito/Vale | `TipoComprobante` | `ORIGEN_DATOS…` |
| Numerador | `codmov` | `resumen`, ADR-0002 |

---

## 8. Invariantes en posting (legacy)

Resumen *confirmado por auditoría*:

- Orden: ver `auditoria_facturas_compras_tablas_campos.md` §10.
- No commit parcial si falla asiento cuando contabilidad activa y `Error_conta` (*confirmado por auditoría*, `generar_asiento_cont` + rollback en `Guardar`).

---

## 9. Incertidumbres

- Equivalencia exacta de **todos** los campos opcionales de cabecera si OCR no los provee (*riesgo pendiente* — defaults deben documentarse en `legacy_integration_spec.md`).
- Post-commit **centros de costo** (`visualiza_asiento_cont`): si el producto obliga asignación en Synap post-aprobación (*decisión nueva*).
