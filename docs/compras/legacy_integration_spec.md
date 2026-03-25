# Legacy integration spec: boundary AdministraNET (MySQL)

**Referencias:** [auditoria_facturas_compras_tablas_campos.md](auditoria_facturas_compras_tablas_campos.md), [auditoria_facturas_compras_sql.md](auditoria_facturas_compras_sql.md), [auditoria_facturas_compras_flujo_completo.md](auditoria_facturas_compras_flujo_completo.md), [auditoria_facturas_compras_pendientes_dudas.md](auditoria_facturas_compras_pendientes_dudas.md), [especificacion_tecnica_replicacion_factura_compra.json](especificacion_tecnica_replicacion_factura_compra.json).

**Convención:** *Confirmado por auditoría* | *Decisión nueva de producto* | *Riesgo pendiente*

---

## 1. Propósito del boundary

El componente **LegacyPostingAdapter** (nombre lógico) traduce un **LegacyPostingCommand** aprobado en el dominio Synap hacia **escrituras MySQL** idénticas en **efecto** al `Guardar` de `PFactura.frm`. *Confirmado por auditoría* (procedimiento `Guardar`, `generar_asiento_cont`, `GuardarSerie`, `modificacion_comp` para flujos de edición legacy — fuera del alcance del expediente «primera alta» salvo que el producto lo incorpore).

---

## 2. Tablas legacy involucradas

Lista canónica: `especificacion_tecnica_replicacion_factura_compra.json` → `tablas_afectadas` + detalle en `auditoria_facturas_compras_tablas_campos.md` §Resumen.

**Agrupación funcional (*confirmado por auditoría*):**

| Grupo | Tablas |
|-------|--------|
| Numeración | `codmov` |
| Cabecera / CC | `cuentaproveedor`, `proveedor` |
| Condición | lectura `cond_venta` (no INSERT en posting estándar) |
| Contado | `caja`, `caja_saldo` |
| Crédito | `op_factura` |
| Detalle | `stock`, `stock_deposito`, `stockp`, `otro_egreso` |
| Lotes | `lote`, `lote_stock` |
| Artículo / precios | `articulo`, `iva`, `precios_historial` (según flags) |
| Puentes | `oc_factp`, `remp_factp` |
| Percepciones | `percep_prov`, `percepcion_prov_convenio` |
| Vales | `en_vale_factura`, `en_vale_viaje` |
| Series | `serie_entrada`, `serie_movimiento` (desde datos equivalentes a `serie_entrada_temp` en VB6) |
| Fiscal | `periodos`, `years` |
| Contabilidad | `configuracion`, `cont_paramatriz`, `cont_pc`, `cont_ejercicio`, `cont_periodo`, `cont_asiento`, `cont_ejercicio_saldo_cta`, `cont_periodo_saldo_cta`, `caja_abm` |
| Buffers VB6 **no usados por Synap en borrador** | `cuerpostockp`, `percep_prov_temp`, `serie_entrada_temp`, `en_vale_factura_temp` — *decisión nueva* sustituir por modelo interno; al posting escribir destinos finales directamente (ADR-0003). |

---

## 3. Orden de grabación

Orden recomendado alineado a `auditoria_facturas_compras_tablas_campos.md` §10 y JSON `orden_persistencia_recomendado`:

1. Reservar / incrementar **`codmov`** (bloqueo fuerte). *Confirmado por auditoría* (dos fases en VB6; ver ADR-0002 para estrategia Synap).
2. **`cuentaproveedor`** (cabecera completa según §1 del doc tablas).
3. **`proveedor.saldo`**.
4. Rama **contado**: `caja_saldo`, `caja`.
5. Bucle **líneas**: `stock` + efectos `stock_deposito`, `stockp`, `lote`/`lote_stock`, `otro_egreso`.
6. Opcional **lista compra**: `articulo`, `precios_historial`. *Confirmado por auditoría* (flags `Principal.actualiza_lista_compra`).
7. **op_factura** si crédito.
8. Actualizaciones **OC** / **REM** + inserts **`oc_factp`** / **`remp_factp`**.
9. **GuardarSerie** equivalente.
10. **generar_asiento_cont** equivalente si aplica.
11. Post-commit: **Balancea_asiento** equivalente. *Confirmado por auditoría*

*Decisión nueva:* ejecutar pasos 1–11 en **una transacción** MySQL salvo excepción documentada (ADR-0002).

---

## 4. Validaciones previas al INSERT (pre-posting)

*Confirmado por auditoría* — lista no exhaustiva (ver `auditoria_facturas_compras_reglas_negocio.md`):

| Validación | Referencia auditoría |
|------------|----------------------|
| Grilla / al menos un renglón | `Guardar` GridRenglon |
| Origen Remito/OC/Vale: datos mínimos en líneas | SELECT sobre buffers en VB6 → equivalente en comando Synap |
| Período fiscal `periodos`+`years` para fecha registro | `sql.md` ~3647 |
| Año en `Years` | ~3691 |
| Nro, NroSuc, ImporteTotal, total > 0 | ~3703 |
| Duplicados FA/FC/FB (`Validacion_Comp`) | `sql.md` ~7641; **FM excluido** — ADR-0004 |
| Lote obligatorio | ~4447 |
| Series cantidad (`ValCantSerie`) | `reglas_negocio` §B |
| Contabilidad: ejercicio/período no cerrado | `generar_asiento_cont` ~9228 |

---

## 5. Ramas contado / crédito

*Confirmado por auditoría* — `cond_venta.Dias`:

- **`"0"`** → `Estado = Canc`, movimiento `caja` + `caja_saldo`, sin sumar a saldo proveedor en cabecera de la misma forma que crédito.
- **`<> "0"`** → `N/Canc`, `op_factura`, saldo proveedor actualizado según fórmula documentada en `tablas_campos` §1.

---

## 6. Side effects obligatorios

Sincronizados con `especificacion_tecnica_replicacion_factura_compra.json` → `side_effects` y `auditoria_facturas_compras_resumen.md`.

Incluyen: saldo proveedor, caja, op_factura, stock/depósito, OC/stockp, remitos, percepciones, vales, series, contabilidad, redondeo asiento.

---

## 7. Qué replicar exacto (*confirmado por auditoría*)

- Valores literales de negocio donde existan en VB6: `TipoComp = "Compra"`, `Tipo = "Proveedor"`, `anulado = "No"`, tipos de `caja.Tipo`, textos de `otro_egreso.tipo_comp`, etc. (extraer del .frm vía `sql.md` y Anexo A).
- Formato numérico de comprobante y uso de `CodigoMovimiento` como PK lógica transversal.
- Secuencia de writes y validaciones previas listadas.

---

## 8. Qué puede abstraerse (*decisión nueva + auditoría*)

- **No usar** tablas temp legacy del usuario VB6; sustituir por datos en Synap hasta aprobar (ADR-0003).
- **Una transacción** en lugar de dos (ADR-0002).
- **SQL parametrizado** en lugar de concatenación ADO (mejora de seguridad y tests); mismo **resultado lógico**.
- Post-UI contable: tarea asíncrona «asignar CC» si se separa de la transacción principal (*riesgo pendiente* — ver `visualiza_asiento_cont` en auditoría).

---

## 9. Decisiones pendientes / riesgos de compatibilidad

| Tema | Tipo | Nota |
|------|------|------|
| FM en duplicados | Riesgo | `auditoria_facturas_compras_pendientes_dudas.md` §2; ADR-0004 |
| DELETE `serie_entrada_temp` OR | Riesgo | `pendientes_dudas` §1 — no replicar SQL ambiguo |
| `en_vale_factura_temp` cleanup | Riesgo | `pendientes_dudas` §3 |
| Sin fila `stock_deposito` | Confirmado | Anexo A — `Saldo`/`no_entregado_fact` pueden no setearse |
| Redondeo / `Format` VB6 | Riesgo | `integracion_django.md` del paquete auditoría |
| Triggers MySQL no documentados en VB6 | Riesgo | Validar en schema cliente |
| Concurrencia `codmov` | Riesgo | Tests de carrera + `FOR UPDATE` |

---

## 10. Contrato de salida del boundary

```python
# Pseudocódigo — especificación, no implementación final
@dataclass(frozen=True)
class LegacyPostingResult:
    codigo_movimiento: int
    nro_comprobante: str
    nro_asiento_contable: Optional[int]  # si contabilidad y éxito
    warnings: tuple[str, ...]  # no legacy: avisos producto
```

---

## 11. Trazabilidad obligatoria en implementación futura

Cada regla de posting debe poder enlazarse a:

- archivo auditoría + sección, o
- `PFactura.frm` línea (citada en docs auditoría), o
- JSON `especificacion_tecnica_replicacion_factura_compra.json`.

---

## 12. Contrato ejecutable y SQL (posting)

- [posting_contract.md](posting_contract.md) — `LegacyPostingCommand`, interfaces, transacción, idempotencia, errores.
- [posting_sql_spec.md](posting_sql_spec.md) — módulos P0–P10 y orden de sentencias.
- [posting_tests.md](posting_tests.md) — TDD antes de la lógica SQL real.
