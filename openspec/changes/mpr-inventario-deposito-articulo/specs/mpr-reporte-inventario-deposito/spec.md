# Spec — Inventario por depósito y artículo (MPR)

**Capability:** `mpr-reporte-inventario-deposito`  
**Change:** `mpr-inventario-deposito-articulo`

---

## Purpose

Reporte hub MPR alineado a Excel `Inventarios.xlsx` / `REP_INVENTARIOS`: existencias por depósito físico y artículo con medidas Stock (UM nativa) y Docenas (derivada), jerarquía Depósito→Marca→Artículo, totales y stock a fecha. MUST NOT reemplazar hub `demanda/stock` ni `/stock/inventario/`.

## Requirements

### REQ-INVDEP-01 — Punto de entrada hub

El sistema MUST exponer slug `inventario_deposito` en `/mpr/reportes/` (grupo **Demanda**), URL `?grupo=demanda&reporte=inventario_deposito`. MUST NOT alterar `reporte=stock` ni `/stock/inventario/`.

#### Scenario: Sin regresión reportes existentes

- GIVEN usuario con acceso MPR
- WHEN navega a `demanda/stock` o `/stock/inventario/`
- THEN el comportamiento previo se mantiene

### REQ-INVDEP-02 — Grano depósito×artículo

La consulta MUST devolver filas con grano `(id_deposito, id_articulo)` enriquecidas con Marca, Talle (CE), depósito y `tipo_mpr`. Solo MUST incluir depósitos con `anulado='No'` y `suma_stock='Si'`.

#### Scenario: Una fila por depósito-artículo

- GIVEN artículo con saldo en Producción y Terminado
- WHEN se consulta sin filtros restrictivos
- THEN aparecen filas separadas por depósito

### REQ-INVDEP-03 — Jerarquía Depósito→Marca→Artículo

La UI MUST agrupar **Depósito → Marca → Artículo** (Talle/CE por fila) con subtotales por Marca dentro de cada depósito.

#### Scenario: Marcas separadas

- GIVEN dos artículos de marcas distintas en el mismo depósito
- WHEN se renderiza el reporte
- THEN las filas quedan bajo encabezados de Marca distintos

### REQ-INVDEP-04 — Medidas Stock y Docenas (decisión A)

Cada fila MUST exponer **Stock** (UM nativa) y **Docenas** (derivada):

| `tipo_mpr` | UM Stock | Divisor docenas |
|------------|----------|-----------------|
| Produccion, SemiElaborado | Pares | 12 |
| Terminado, 2daSeleccion | Packs | `divisor_docena_pack(cantidad_promedio_bulto)` → 12, 6 o 4 |

MUST NOT aplicar divisor 12 global a todos los tipos.

#### Scenario: Pipeline — pares ÷12

- GIVEN saldo 24 pares en SemiElaborado
- WHEN se calculan medidas
- THEN Stock=24 y Docenas=2,0

#### Scenario: Terminado — divisor 6

- GIVEN 18 packs y divisor 6
- WHEN se calculan medidas
- THEN Stock=18 y Docenas=3,0

#### Scenario: Terminado — divisor 4

- GIVEN 8 packs y divisor 4
- WHEN se calculan medidas
- THEN Docenas=2,0

### REQ-INVDEP-05 — Total cabecera SUM(docenas)

El total de cabecera MUST ser **SUM(docenas)** del scope visible, no `SUM(stock)/12`. MUST calcularse en capa servicio.

#### Scenario: Mix pipeline y Terminado

- GIVEN filas con Docenas 2,0 y 3,0 en scope
- WHEN se muestra total cabecera
- THEN total = 5,0 docenas

### REQ-INVDEP-06 — 2da OFF por defecto (decisión B)

Default (`incluir_2da` ausente o `0`): MUST excluir `tipo_mpr = 2daSeleccion`. Con `incluir_2da=1`: MUST incluirlos con reglas pack.

#### Scenario: Default sin 2da

- GIVEN stock en 2daSeleccion
- WHEN se carga sin `incluir_2da`
- THEN esas filas no aparecen ni suman al total

#### Scenario: Opt-in 2da

- GIVEN mismo stock
- WHEN `incluir_2da=1`
- THEN filas 2da visibles

### REQ-INVDEP-07 — Stock a fecha (decisión C)

MUST aceptar `fecha_corte` (visualización **dd/MM/yyyy**, default hoy). Corte=hoy: saldo desde `stock_deposito.saldo`. Corte&lt;hoy: reconstrucción desde `stock` con criterio VB6 `Info_Stock.frm` (campo fecha validado spike S3). Tipos MUST normalizarse con `administranet_types`.

#### Scenario: Corte hoy

- GIVEN `fecha_corte` = hoy
- WHEN se consulta
- THEN saldos = `stock_deposito` actual

#### Scenario: Corte histórico

- GIVEN movimientos antes y después del corte
- WHEN `fecha_corte` &lt; hoy
- THEN saldo acumulado hasta corte inclusive

### REQ-INVDEP-08 — Filtros

MUST soportar URL persistente: depósito(s), marca(s), búsqueda artículo, `incluir_2da`, `fecha_corte`. Desde/Hasta del shell MAY ignorarse.

#### Scenario: Filtro marca

- GIVEN artículos marcas A y B
- WHEN filtro marca=A
- THEN solo filas A y total recalculado

### REQ-INVDEP-09 — Universo artículos

Default MUST incluir fabricación MPR, Terminado comercial y `tipo_art_fab=Tercero` (decisión 14/08/2026). MUST NOT filtrar por `tipo_art_fab` para excluir terceros.

#### Scenario: Tercero incluido

- GIVEN artículo `tipo_art_fab=Tercero` con saldo en Terminado
- WHEN se consulta con universo default
- THEN el artículo aparece con Stock y Docenas según reglas del depósito

### REQ-INVDEP-10 — Export Excel

MUST exportar con `format=xlsx`: Depósito, Marca, Artículo, Talle, Stock, Docenas y TOTAL = SUM(docenas). Encabezados español.

#### Scenario: Export con total

- GIVEN reporte con datos
- WHEN export Excel
- THEN archivo incluye filas y total docenas del scope

### REQ-INVDEP-11 — UI canon

MUST seguir `FUENTE_VERDAD_UI_REPORTES_MPR.md`. Español; fechas **dd/MM/yyyy**. MUST NOT usar `alert`/`confirm`/`prompt`; modales Synap y `mprShowAviso`/`SynapMessages`.

#### Scenario: Fecha visible dd/MM/yyyy

- GIVEN reporte cargado
- WHEN usuario ve `fecha_corte`
- THEN formato dd/MM/yyyy

### REQ-INVDEP-12 — Empty state

Sin filas: mensaje explicativo en español (ajustar depósito, marca o 2da).

#### Scenario: Sin resultados

- GIVEN filtros que excluyen todo
- WHEN se renderiza
- THEN empty state en español, sin error 500

### REQ-INVDEP-13 — Paridad Excel

SUM(docenas) por depósito MUST coincidir con Excel muestra dentro de tolerancia acordada (p. ej. ≤0,01 docenas).

#### Scenario: Validación muestra

- GIVEN datos de referencia `Inventarios.xlsx`
- WHEN se ejecuta comparación diagnóstica
- THEN delta docenas ≤ tolerancia
