# Test cases: factura de compra — captura, workflow y posting legacy

**Referencias:** [product_requirements.md](product_requirements.md), [test_strategy.md](test_strategy.md), paquete `auditoria_facturas_compras_*`.

**Leyenda evidencia:** `[AUD:archivo§]` = trazabilidad a documento de auditoría.

---

## Convención por caso

Cada ID incluye: **precondiciones | entrada | esperado | side effects legacy | borde/rollback | evidencia**.

---

### Captura y documento

| ID | Nombre | Precondiciones | Entrada | Esperado | Legacy | Borde / rollback | Evidencia |
|----|--------|----------------|---------|----------|--------|------------------|-----------|
| TC-CAP-01 | Cámara crea borrador | Usuario con permiso crear | Imagen JPEG válida | Expediente `borrador`, `DocumentoFuente` almacenado | Ninguno | Archivo corrupto → error amigable | PRD *decisión nueva* |
| TC-CAP-02 | PDF crea borrador | Idem | PDF multipágina | Idem; job OCR encolado | Ninguno | PDF > límite → rechazo | PRD |
| TC-OCR-01 | OCR exitoso | Worker activo | Imagen clara | `ocr_completado`, campos cabecera parciales rellenos | Ninguno | Confianza baja → flags en UI | *decisión nueva* |
| TC-OCR-02 | OCR fallido | Motor error | Cualquier archivo | Estado marca fallo OCR; expediente editable manual | Ninguno | Reintento OCR | *decisión nueva* |

---

### Workflow

| ID | Nombre | Precondiciones | Entrada | Esperado | Legacy | Borde / rollback | Evidencia |
|----|--------|----------------|---------|----------|--------|------------------|-----------|
| TC-WF-01 | Enviar a revisión | `borrador` | Acción analista | `en_revision` | Ninguno | Sin permiso → 403 | PRD |
| TC-WF-02 | Editar cabecera | `en_revision` | PATCH datos | Persistido en DB Synap | Ninguno | Validación formato fechas/números | *decisión nueva* |
| TC-WF-03 | Rechazar | `en_revision` | Motivo texto | `rechazado` | Ninguno | Motivo vacío → 400 | PRD |
| TC-WF-04 | Aprobar sin permiso | `en_revision` | POST aprobar | 403 | Ninguno | — | PRD |
| TC-WF-05 | Doble aprobación | `aprobado` ya | POST aprobar | Idempotente o 409 (fijar en impl.) | No segundo posting | — | ADR-0005 |

---

### Posting — núcleo contado / crédito

| ID | Nombre | Precondiciones | Entrada | Esperado | Legacy | Borde / rollback | Evidencia |
|----|--------|----------------|---------|----------|--------|------------------|-----------|
| TC-POST-01 | Contado genera caja | `cond_venta.Dias=0`, período OK, proveedor OK | `LegacyPostingCommand` mínimo | `cuentaproveedor.Estado=Canc`; fila `caja` Tipo «Factura Compra Contado»; `caja_saldo` decrementado | `caja`, `caja_saldo`, `cuentaproveedor`, `proveedor`, `stock`… | Falla a mitad → rollback MySQL | [AUD:reglas_negocio§D], [AUD:flujo_completo§C.8] |
| TC-POST-02 | Crédito genera op_factura | `Dias<>0` | Command | `op_factura` existe; `Estado=N/Canc` | `op_factura`, `cuentaproveedor` | — | [AUD:resumen§4], [AUD:tablas_campos§7] |
| TC-POST-03 | Saldo proveedor | Saldo inicial S0 | Importe T | `proveedor.saldo` según fórmula cabecera crédito/contado | `proveedor` | — | [AUD:tablas_campos§1] |

---

### Posting — numerador y transacción

| ID | Nombre | Precondiciones | Entrada | Esperado | Legacy | Borde / rollback | Evidencia |
|----|--------|----------------|---------|----------|--------|------------------|-----------|
| TC-POST-04 | codmov incrementa | `codmov` conocido | Posting OK | Todas las tablas hijas con mismo `CodigoMovimiento` | `codmov` + hijas | Rollback no persiste incremento (ADR-0002) | [AUD:resumen§1], ADR-0002 |
| TC-POST-05 | Concurrencia codmov | Dos hilos | Dos postings paralelos | Un solo numerador consumido por transacción exitosa; la otra espera o reintenta | `codmov` | Sin duplicados | *riesgo* + [AUD:sql§3756] |

---

### Origen OC / Remito / Vale / Manual

| ID | Nombre | Precondiciones | Entrada | Esperado | Legacy | Borde / rollback | Evidencia |
|----|--------|----------------|---------|----------|--------|------------------|-----------|
| TC-POST-10 | Manual mínimo | Sin OC/remito | Líneas con `IDArt` | `stock` + depósito según Anexo A | `stock`, `stock_deposito` | Sin renglones → abort (como Grid vacío) | [AUD:flujo§C.1], Anexo A |
| TC-POST-11 | OC parcial | OC con `stockp` pendiente | Líneas vinculadas | `stockp.cantidad_pendiente`/`remitido_facturado` actualizados; `oc_factp` | `stockp`, `oc_factp`, `cuentaproveedor` OC | — | [AUD:reglas_negocio§G] |
| TC-POST-12 | Remito facturado | Remito pendiente | Origen remito | `remp_factp`; `estado_remito` REM | `remp_factp`, `cuentaproveedor` REM | — | [AUD:resumen§7] |
| TC-POST-13 | Vale | Vales en command | — | `en_vale_factura` + `en_vale_viaje` estado | ambas tablas | — | [AUD:sql§3849] |

---

### Percepciones, series, lotes

| ID | Nombre | Precondiciones | Entrada | Esperado | Legacy | Borde / rollback | Evidencia |
|----|--------|----------------|---------|----------|--------|------------------|-----------|
| TC-POST-20 | Percepciones IB | `PercepIB<>0` + líneas temp Synap | Command | `percep_prov` + `percepcion_prov_convenio` | ambas | Sin líneas temp → no insert percepciones detalle | [AUD:reglas_negocio§E] |
| TC-POST-21 | Serie | Artículo serie Sí | Series en command | `serie_entrada` + `serie_movimiento` | ambas | Cantidad ≠ series → error (como `ValCantSerie`) | [AUD:reglas_negocio§B] |
| TC-POST-22 | Lote obligatorio faltante | Lote=Sí sin cod/vto | Command inválido | Rechazo **antes** de commit; rollback | Ninguno | Msg equivalente VB6 | [AUD:tablas_campos Anexo A.4] |

---

### Contabilidad

| ID | Nombre | Precondiciones | Entrada | Esperado | Legacy | Borde / rollback | Evidencia |
|----|--------|----------------|---------|----------|--------|------------------|-----------|
| TC-POST-30 | Asiento generado | `activ_contabilidad` simulado | Command | `cont_asiento` líneas; saldos actualizados; `Balancea_asiento` efecto | `cont_*` | `ContCerrado` → Error_conta, rollback | [AUD:flujo§C.8], [AUD:reglas_negocio§K] |

---

### Validaciones fiscales y duplicados

| ID | Nombre | Precondiciones | Entrada | Esperado | Legacy | Borde / rollback | Evidencia |
|----|--------|----------------|---------|----------|--------|------------------|-----------|
| TC-VAL-01 | Período cerrado | `periodos` cerrado | Posting | Error claro; sin writes | Ninguno | — | [AUD:reglas_negocio§B] |
| TC-VAL-02 | Duplicado FA | Misma clave que factura existente | Posting | Error | Ninguno | — | [AUD:sql§7641] |
| TC-VAL-03 | FM duplicado modo paridad | Flag paridad VB6 | Mismo nro FM | Permitido (si se fija comportamiento) | — | — | ADR-0004, [AUD:pendientes§2] |
| TC-VAL-04 | FM duplicado modo Synap default | Flag default | Mismo nro FM | Rechazo | Ninguno | — | ADR-0004 |

---

### Datos maestros inexistentes

| ID | Nombre | Precondiciones | Entrada | Esperado | Legacy | Borde / rollback | Evidencia |
|----|--------|----------------|---------|----------|--------|------------------|-----------|
| TC-ERR-01 | Proveedor inexistente | ID inválido | Posting | Error pre-flight | Ninguno | — | *decisión nueva* validación |
| TC-ERR-02 | Artículo inexistente | ID inválido | Posting | Error | Ninguno | — | Anexo A `IDArt` |

---

### Rollback parcial simulado

| ID | Nombre | Precondiciones | Entrada | Esperado | Legacy | Borde / rollback | Evidencia |
|----|--------|----------------|---------|----------|--------|------------------|-----------|
| TC-ERR-10 | Falla post-stock | Mock falla en N-ésima línea | Posting | Rollback; `codmov` no consumido persistentemente (ADR-0002) | Ningún efecto neto | — | [AUD:flujo§C.9], ADR-0002 |

---

## Matriz trazabilidad auditoría → casos obligatorios (MVP posting)

| Regla auditoría | Casos |
|-----------------|-------|
| Dos fases VB6 / atomicidad Synap | TC-POST-04, TC-ERR-10 |
| Contado caja | TC-POST-01 |
| Crédito op_factura | TC-POST-02 |
| stock Anexo A | TC-POST-10 |
| OC/stockp | TC-POST-11 |
| Remito | TC-POST-12 |
| Vales | TC-POST-13 |
| Percepciones | TC-POST-20 |
| Series | TC-POST-21 |
| Lote | TC-POST-22 |
| Contabilidad | TC-POST-30 |
| Período fiscal | TC-VAL-01 |
| Duplicados | TC-VAL-02, TC-VAL-03, TC-VAL-04 |

---

## Notas

- Los IDs son estables para enlazar desde código `pytest.mark.parametrize` o tickets.
- Ampliar con casos `Principal.*` (embalaje, remite_factura_art, actualiza_lista_compra) replicando ramas del Anexo A y `Guardar`.
