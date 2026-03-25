# Contrato técnico ejecutable: posting legacy (factura de compra)

**Estado:** especificación — no sustituye implementación.  
**Referencias:** [auditoria_facturas_compras_tablas_campos.md](auditoria_facturas_compras_tablas_campos.md) (Anexo A, §1 cabecera), [legacy_integration_spec.md](legacy_integration_spec.md), [adrs/0002-transaccion-atomica-vs-dos-fases-vb6.md](adrs/0002-transaccion-atomica-vs-dos-fases-vb6.md), [adrs/0004-validacion-duplicados-fm.md](adrs/0004-validacion-duplicados-fm.md), [especificacion_tecnica_replicacion_factura_compra.json](especificacion_tecnica_replicacion_factura_compra.json).

**Convención:** tipos en notación **Python 3.10+** (`|` union) como contrato ejecutable futuro (`pydantic` v2 o `dataclasses` + validación).

**SQL detallado:** [posting_sql_spec.md](posting_sql_spec.md).  
**Tests:** [posting_tests.md](posting_tests.md).

---

## 1. `LegacyPostingCommand` completo

### 1.1 Raíz del comando

```python
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional
from uuid import UUID

OrigenComprobante = Literal["MANUAL", "REMITO", "OC", "VALE"]
LetraFiscal = Literal["FA", "FB", "FC", "FM"]
TipoFacturaCabecera = Literal["Factura", "Factura Remito", "Factura OC", "Factura Vale"]


@dataclass(frozen=True)
class LegacyPostingCommand:
    """Comando inmutable: única entrada al boundary MySQL (salvo enriquecimiento read-only previo)."""

    # --- Correlación e idempotencia (Synap; no existen en VB6) ---
    idempotency_key: str
    """Clave única por intento lógico de posting (ej. f'{expediente_id}:{posting_attempt}')."""
    expediente_id: UUID
    synap_empresa_id: int  # o UUID según modelo Synap; necesario para auditoría multi-tenant

    # --- Contexto operativo (equivalente fragmentos de Principal + usuario) ---
    context: PostingContext

    # --- Cabecera comprobante (mapea a cuentaproveedor + ramas caja/op) ---
    header: PostingHeader

    # --- Renglones (mapean a stock + efectos colaterales por ítem) ---
    lines: tuple[StockLineCommand, ...]

    # --- Colecciones opcionales ---
    percepciones_ib: tuple[PercepcionIBCommand, ...] = ()
    vales: tuple[ValeVinculoCommand, ...] = ()
    series: tuple[SerieEntradaCommand, ...] = ()  # filas a persistir como en GuardarSerie (no temp legacy)

    # --- Puentes agregados (después del bucle de líneas en VB6) ---
    oc_bridges: tuple[OcFactPCommand, ...] = ()
    remito_bridges: tuple[RemitoFactPCommand, ...] = ()

    # --- Contabilidad (opcional; si ausente = no generar asiento) ---
    accounting: Optional[AccountingSliceCommand] = None

    # --- Segundo pase lista de compra (opcional; flag en context) ---
    price_list_updates: tuple[PriceListUpdateCommand, ...] = ()
```

### 1.2 `PostingContext`

Sustituye lecturas de `Principal.*` y sesión VB6. *Decisión Synap:* todos los flags necesarios deben venir **explícitos** (no globals ocultos).

```python
@dataclass(frozen=True)
class PostingContext:
    id_usuario_legacy: int
    id_vendedor_usuario: int  # VB6: Principal.id_vendedor_usr → caja.cod_vendedor
    cod_sucursal: int
    modifica_sucursal_comp: bool
    id_sucursal_comprobante: Optional[int]  # si modifica_sucursal_comp

    # Fecha de referencia fiscal (VB6: Principal.Fecha como string dd/mm/yyyy; aquí normalizada)
    fecha_servidor: date

    # Stock / embalaje
    remite_factura_art_permiso: bool  # Principal.remite_factura_art == "Si"
    remite_factura_art_entrega_mercaderia: Optional[bool]
    """None = no aplica combo; True = entrega (ListIndex 0 VB6); False = no entrega."""
    utiliza_embalaje: bool
    utiliza_bulto_cerrado: bool
    utiliza_display: bool
    usa_multiplica_bulto_promedio: bool
    decimales_peso: str  # Principal.Decimales para Format peso

    # Compras
    actualiza_lista_compra: bool
    compras_cambia_prov_factura: bool
    valida_pv_comp_compra: bool
    mod_talonario: bool  # ramas Validacion_Comp
    duplicate_check_includes_fm: bool
    """False = paridad VB6 (FM fuera del anti-duplicado); True = default Synap (ADR-0004)."""

    # Proyecto
    activ_proyecto: bool
    id_proyecto: Optional[int]

    # Caja contado
    fact_caja_fondo_fijo: bool
    """True = usar id caja desde UI fondo fijo (Caja.caja_abm); False = caja_abm estándar."""
    id_caja_abm: int
    moneda_caja_literal: Literal["Pesos"] = "Pesos"  # fijo en VB6 para este flujo

    # Contabilidad
    activ_contabilidad: bool
    conta_sucursal: bool  # gating generar_asiento_cont
    selec_ejer_per_cont: bool
    id_ejercicio_contable: Optional[int]
    id_periodo_contable: Optional[int]
```

### 1.3 `PostingHeader`

Alineado a [auditoria_facturas_compras_tablas_campos.md](auditoria_facturas_compras_tablas_campos.md) §1 (`cuentaproveedor` en `Guardar`).

```python
@dataclass(frozen=True)
class PostingHeader:
    # Proveedor y condición
    codigo_proveedor: int
    id_cond_compra: int
    cond_compra_texto: str  # CV.Text
    cond_compra_dias: str
    """VB6 compara con string '0'. Normalizar a str sin espacios."""

    # Fechas
    fecha_comprobante: date
    fecha_registro: date
    vencimiento: date

    # Numeración PV + número (componentes; el formateado final va en nro_comprobante_formateado)
    nro_suc_pv: int
    nro_comprobante_crudo: int
    nro_comp_busqueda: str  # Nro.Text tal cual para NroCompBusq

    # Letra / tipo
    tipo_factura: LetraFiscal
    tipo_factura_cabecera: TipoFacturaCabecera  # TipoFactura en cuentaproveedor
    origen: OrigenComprobante

    # Texto
    detalle: str

    # Totales y tributos (Decimal; 2 decimales salvo regla específica)
    importe_total: Decimal
    subtotal1: Decimal
    subtotal2: Decimal
    subtotal3: Decimal
    subtotal_gral: Decimal
    iva1: Decimal
    iva2: Decimal
    iva3: Decimal
    alicuota1: Decimal
    alicuota2: Decimal
    alicuota3: Decimal
    exento: Decimal
    percep_ib_total: Decimal
    percep_gan: Decimal
    percep_iva: Decimal
    otros_imp: Decimal
    impuesto_interno: Decimal
    sobretasa_iva: Decimal
    imp_desc1_1: Decimal
    total_desc: Decimal
    subtotal_desc1: Decimal
    subtotal_desc2: Decimal
    subtotal_desc3: Decimal
    subtotal_desc: Decimal

    # CAI
    nro_cai: Optional[str]
    fecha_cai: Optional[date]

    # Cotización
    coti_dolar: Decimal

    # Flags cabecera ya resueltos (VB6 combina Principal + TipoComprobante + combo)
    remite_factura_art_valor: Optional[str]  # "Si" / "No"
    estado_fact_remito: Optional[str]  # ej. "Pendiente"

    # Numeración final (calculada por mapper Synap con misma regla que Validacion_Comp / VB6)
    nro_comprobante_formateado: str
```

### 1.4 `StockLineCommand`

Anexo A + ramas condicionales. Una fila = un `stock` INSERT + efectos.

```python
@dataclass(frozen=True)
class StockLineCommand:
    orden: int

    # Artículo / identificación
    id_art: int
    codigo_articulo: str
    descripcion: str
    tipo_art: str  # "Articulo", "Materia prima", servicio/gasto según schema
    cod_laboratorio: int

    # Depósito
    cod_deposito: int

    # Precios por unidad y renglón
    precio_venta_x_u: Decimal
    precio_costo_x_u: Decimal
    precio_iva_x_u: Decimal
    precio_bruto_x_u: Decimal
    imp_desc: Decimal
    por_desc: Decimal
    precio_venta_x_r: Decimal
    precio_costo_x_r: Decimal
    precio_iva_x_r: Decimal
    precio_bruto_x_r: Decimal
    precio_neto_x_r: Decimal

    alicuota: int  # id iva en artículo / línea
    imp_alicuota_iva: Decimal
    tipo_iva: str

    # Cantidad y embalaje (según contexto se interpreta en el servicio detalle)
    cantidad: Decimal
    multiplicador_comp: Decimal
    multiplicador_vta: Decimal
    cantidad_uni: Decimal
    id_unimed: int
    id_presentacion: int
    nombre_unimed: str
    nombre_presentacion: str

    # Gasto / otro egreso
    cod_gasto: int  # 0 = no gasto

    detalle_renglon: str
    imp_desc_bonif: Decimal
    por_desc_bonif: Decimal

    # Opcionales vínculos
    id_manual: Optional[int] = None
    nro_presupuesto: Optional[int] = None
    codmov_presupuesto: Optional[int] = None
    nro_oc: Optional[int] = None
    codmov_oc: Optional[int] = None
    id_stock: Optional[int] = None  # id_stockp / línea OC
    nro_remito: Optional[int] = None
    codmov_remito: Optional[int] = None

    # Lote
    requiere_lote: bool  # Lote == "Si"
    cod_lote: Optional[str] = None
    vto_lote: Optional[date] = None

    # Serie (cabecera línea stock)
    es_serie: bool
    desc_serie: Optional[str] = None

    # Peso
    unidad_art_peso: Optional[Decimal] = None

    impuesto_interno_subtotal: Decimal

    # Flags ya resueltos por dominio Synap (evitar re-leer articulo en posting si ya validado)
    entrada_fisica_deposito: bool
    """True si esta línea debe actualizar stock_deposito y setear stock.Saldo / no_entregado_fact coherente."""
```

### 1.5 Otras estructuras anidadas

```python
@dataclass(frozen=True)
class PercepcionIBCommand:
    id_jurisdiccion: int
    importe_percep: Decimal


@dataclass(frozen=True)
class ValeVinculoCommand:
    codigo_movimiento_vale: int


@dataclass(frozen=True)
class SerieEntradaCommand:
    """Equivalente fila lista para INSERT masivo serie_entrada / luego serie_movimiento."""
    id_articulo: int
    nro_serie: str
    desc_serie: str
    vto_serie: Optional[date]
    id_deposito: int
    orden_linea: int  # correlación con StockLineCommand.orden


@dataclass(frozen=True)
class OcFactPCommand:
    codigo_movimiento_oc: int


@dataclass(frozen=True)
class RemitoFactPCommand:
    codigo_movimiento_remito: int
    nro_remito: int


@dataclass(frozen=True)
class AccountingSliceCommand:
    """Parámetros ya resueltos o datos mínimos para delegar a ContabilidadPostingService interno."""
    id_ejercicio: int
    id_periodo: Optional[int]
    # Alternativa: matriz de líneas pre-armada en Synap (si se replica lógica fuera de MySQL)
    lineas_asiento: tuple[AsientoLineDraft, ...]


@dataclass(frozen=True)
class AsientoLineDraft:
    id_pc: int
    debe: Decimal
    haber: Decimal


@dataclass(frozen=True)
class PriceListUpdateCommand:
    """Una operación lógica de actualización post-stock (segundo barrido VB6)."""
    id_art: int
    # ... campos a definir cuando se traslade el bloque ~4674–5083 de PFactura a spec detallada
    payload: dict[str, Decimal | int | str]  # placeholder hasta segunda iteración de auditoría de ese bloque
```

> **Riesgo pendiente:** el segundo barrido `articulo`/`precios_historial` es extenso; el contrato admite `PriceListUpdateCommand.payload` tipado fuerte en iteración posterior o lista cerrada de campos auditados.

---

## 2. Validaciones mínimas (`LegacyPostingCommand.validate()`)

Ejecutar **antes** de abrir transacción MySQL (fallo rápido; errores de negocio).

| Código | Regla | Evidencia |
|--------|-------|-----------|
| V-01 | `len(lines) >= 1` | [auditoria_facturas_compras_reglas_negocio.md](auditoria_facturas_compras_reglas_negocio.md) Grid vacío |
| V-02 | `importe_total > 0` | mismo |
| V-03 | `nro_suc_pv`, `nro_comprobante_crudo` coherentes con enteros positivos | VB6 ~3703 |
| V-04 | Origen REMITO: al menos una línea con `codmov_remito` not null | `sql.md` |
| V-05 | Origen OC: al menos una línea con `codmov_oc` not null | idem |
| V-06 | Origen VALE: `len(vales) >= 1` | idem |
| V-07 | Período fiscal: **no** en command; validación con lectura DB en `PreflightLegacyPostingService` | `reglas_negocio` §B |
| V-08 | Anti-duplicado: **no** en command puro; preflight query | `sql.md` Validacion_Comp |
| V-09 | Lote: si `requiere_lote` → `cod_lote` y `vto_lote` obligatorios | Anexo A.4 |
| V-10 | Series: conteo `series` por línea vs cantidad esperada (regla ValCantSerie) | `reglas_negocio` |
| V-11 | `cond_compra_dias == "0"` implica rama contado; distinto implica crédito | `reglas_negocio` §D |
| V-12 | `percep_ib_total != 0` implica `len(percepciones_ib) >= 1` | `Guardar` VB6 |

Validaciones **dentro de transacción** (dependen de estado DB): existencia `proveedor`, `cond_venta`, filas `stock_deposito`, `stockp`, etc. → `PreflightLegacyPostingService` + locks.

---

## 3. Mappers desde `ExpedienteFacturaCompra` (dominio Synap)

### 3.1 Rol del mapper

`ExpedienteToLegacyCommandMapper.map(expediente: ExpedienteFacturaCompra, ctx: SynapRuntimeContext) -> LegacyPostingCommand`

- **Puro** donde sea posible (sin I/O); lecturas maestras (proveedor, condición) pueden ocurrir **antes** y pasarse como DTO en `SynapRuntimeContext`.
- *Decisión Synap:* el expediente **no** contiene flags `Principal`; deben resolverse desde **configuración empresa/usuario** y pasarse a `PostingContext`.

### 3.2 Reglas de transformación (resumen)

| Origen Synap | Destino command | Reglas / defaults |
|--------------|-----------------|-------------------|
| `expediente.proveedor_id` | `header.codigo_proveedor` | FK legacy resuelta pre-map |
| `expediente.condicion_compra_id` | `header.id_cond_compra` + `cond_compra_dias` | Leer `cond_venta` en pre-map; `dias` como **str** como VB6 |
| Fechas editadas | `fecha_comprobante`, `fecha_registro`, `vencimiento` | timezone empresa → `date` |
| Letra / origen | `tipo_factura`, `tipo_factura_cabecera`, `origen` | Misma taxonomía que [ORIGEN_DATOS_FACTURA_COMPRA_VB6.md](ORIGEN_DATOS_FACTURA_COMPRA_VB6.md) |
| Líneas expediente | `StockLineCommand` | 1:1; campos monetarios `Decimal`; `entrada_fisica_deposito` calculado con **misma matriz** que VB6 (Principal + origen + remito_factura_art) — documentar en código como tabla de verdad |
| Percepciones expediente | `percepciones_ib` | Solo si `percep_ib_total != 0` en cabecera |
| Vales seleccionados | `vales` | Lista `codigo_movimiento_vale` |
| Series capturadas | `series` | Aplanado por línea + orden |
| OC/Remito desde expediente | `oc_bridges`, `remito_bridges` | Dedup por `codigo_movimiento_oc` / remito |
| Numeración | `header.nro_comprobante_formateado` | Invocar **misma** función que posting usará para validar duplicados (Ceros_Nro_pv / Ceros_Nro_Comp) — parámetros desde config legacy |
| `idempotency_key` | `f"{expediente.id}:{expediente.posting_attempt}"` | Ver §6 |

### 3.3 Defaults

| Campo | Default si ausente en expediente |
|-------|----------------------------------|
| `detalle` | `""` o `"-"` según `administranet_types.str_or_default` para VARCHAR legacy |
| CAI | `None` → no escribir o NULL según columna |
| `exento` | `Decimal("0")` |
| Percepciones | `()` y totales 0 |
| `accounting` | `None` si `activ_contabilidad` falso |
| `price_list_updates` | `()` si flag falso |

---

## 4. Interfaces del posting

### 4.1 `LegacyPostingAdapter` (fachada)

```python
class LegacyPostingAdapter(Protocol):
    def execute(self, cmd: LegacyPostingCommand) -> LegacyPostingResult: ...

    def preflight(self, cmd: LegacyPostingCommand) -> PreflightResult:
        """Validaciones que requieren DB (sin commit). Opcionalmente fusionado en execute."""
        ...
```

### 4.2 Resultados y errores

Ver **§7** y tipos:

```python
@dataclass(frozen=True)
class LegacyPostingResult:
    success: Literal[True]
    codigo_movimiento: int
    nro_comprobante: str
    nro_asiento_contable: Optional[int]
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class LegacyPostingFailure:
    success: Literal[False]
    code: str  # p.ej. DUPLICATE_INVOICE, FISCAL_PERIOD_CLOSED
    message: str
    detail: dict[str, str | int | None]
    rollback_performed: bool
```

### 4.3 Servicios internos (orquestación)

| Servicio | Responsabilidad | Transacción |
|----------|-----------------|-------------|
| `NumeradorCodmovService` | `SELECT … FOR UPDATE` + incremento `codmov` | Dentro misma TX |
| `CabeceraCuentaproveedorService` | INSERT `cuentaproveedor` + vales INSERT + percepciones + proveedor saldo + rama caja inicial si orden lo requiere | Orden exacto [posting_sql_spec.md](posting_sql_spec.md) |
| `CajaContadoService` | `caja_saldo`, `caja` | Tras cabecera según spec SQL |
| `DetalleStockService` | Por cada `StockLineCommand`: stock, stock_deposito, stockp, lote, otro_egreso | Bucle |
| `ListaCompraUpdateService` | `articulo`, `precios_historial` | Si flag |
| `OpFacturaCreditoService` | INSERT `op_factura` | Si crédito |
| `PuentesOcRemitoService` | UPDATE cabeceras OC/REM + INSERT `oc_factp`/`remp_factp` | Post-bucle |
| `SeriesPostingService` | INSERT `serie_entrada`, `serie_movimiento` | Tras stock |
| `ContabilidadPostingService` | Asiento + saldos + numeración ejercicio | Si `accounting` |
| `BalanceoAsientoService` | Ajuste centavos | Tras líneas asiento |
| `PreflightLegacyPostingService` | periodos, years, duplicados, existencia maestros | READ solo o TX separada read-only |

**Nota:** el orden fino entre cabecera parcial y caja debe seguir **posting_sql_spec.md** (alineado a VB6).

---

## 5. Manejo de transacción

Ver [adrs/0002-transaccion-atomica-vs-dos-fases-vb6.md](adrs/0002-transaccion-atomica-vs-dos-fases-vb6.md).

1. `connection.begin()`
2. `SET autocommit=0` si aplica al driver
3. `NumeradorCodmovService.lock_and_next()` → `codigo_movimiento`
4. Secuencia de servicios internos (sin commit intermedio)
5. `connection.commit()` si todo OK
6. `connection.rollback()` en cualquier excepción

**Locking `codmov`:**

```sql
SELECT CodigoMovimiento FROM codmov WHERE codigo = 1 FOR UPDATE;
-- incrementar en aplicación y UPDATE codmov SET CodigoMovimiento = %s WHERE codigo = 1;
```

*Riesgo pendiente:* nombre exacto de columna en MySQL cliente — validar contra DDL.

---

## 6. Estrategia de idempotencia

### 6.1 Problema

Doble clic «Aprobar» o reintento de worker no debe generar dos comprobantes legacy.

### 6.2 Campos a persistir en Synap (antes/después posting)

| Campo modelo expediente (conceptual) | Cuándo |
|--------------------------------------|--------|
| `posting_status` | `pending` → `in_progress` → `posted` \| `failed` |
| `posting_attempt` | Incremento al iniciar intento exclusivo |
| `idempotency_key_last` | Clave del último intento completado |
| `legacy_codigo_movimiento` | Set solo si `posted` |
| `legacy_nro_comprobante` | Idem |
| `posted_at` | Timestamp UTC |
| `last_posting_error_code` | Si `failed` |

### 6.3 Algoritmo

1. Transacción Synap: `SELECT … FOR UPDATE` expediente.
2. Si `posting_status == posted` y `idempotency_key` coincide → retornar éxito **sin** llamar MySQL (o retornar idempotente con mismos IDs).
3. Si otro hilo tiene `in_progress` con lease reciente → `409 Conflict`.
4. Marcar `in_progress`, `commit` Synap.
5. Ejecutar `LegacyPostingAdapter.execute`.
6. En éxito: actualizar `posted`, `legacy_*`; en fallo: `failed` + error.

*Decisión Synap:* la **fuente de verdad** de idempotencia es la DB Synap; MySQL no tiene tabla de idempotencia Synap.

---

## 7. Estrategia de errores

### 7.1 Clasificación

| Tipo | Ejemplos | HTTP / UI |
|------|----------|-----------|
| **Negocio (preflight)** | Duplicado, período cerrado, lote faltante, proveedor inexistente | 422 + `LegacyPostingFailure` |
| **Negocio (mid-tx)** | Deadlock retryable (opcional), restricción FK | Rollback + 422/503 |
| **Técnico** | Timeout, pérdida conexión, bug | 500 + log + rollback |

### 7.2 Qué retorna el adapter

- **Éxito:** `LegacyPostingResult` (inmutable).
- **Fallo:** excepción interna capturada por fachada y mapeada a `LegacyPostingFailure`, **o** resultado discriminated union:

```python
LegacyPostingOutcome = LegacyPostingResult | LegacyPostingFailure
```

*Recomendación TDD:* usar `Outcome` para forzar manejo explícito en tests.

### 7.3 Códigos de error estables (contrato)

| `code` | Significado |
|--------|-------------|
| `DUPLICATE_INVOICE` | Validacion_Comp |
| `FISCAL_PERIOD_CLOSED` | periodos/years |
| `FISCAL_PERIOD_EXPIRED` | vencimiento_fiscal |
| `YEAR_NOT_FOUND` | Years |
| `MISSING_LOTE` | validación lote |
| `SERIES_COUNT_MISMATCH` | ValCantSerie |
| `CONTAB_PERIOD_CLOSED` | ContCerrado |
| `MASTER_NOT_FOUND` | proveedor, artículo, depósito |
| `CONSTRAINT_VIOLATION` | FK / unique MySQL |
| `UNKNOWN` | resto |

---

## 8. Relación con otros documentos

- Queries y orden: [posting_sql_spec.md](posting_sql_spec.md)
- Tests unitarios (primero): [posting_tests.md](posting_tests.md)
