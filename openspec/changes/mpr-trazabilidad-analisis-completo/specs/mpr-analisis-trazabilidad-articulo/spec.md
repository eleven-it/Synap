# Spec — Análisis trazabilidad artículo (MPR)

**Capability:** `mpr-analisis-trazabilidad-articulo`  
**Change:** `mpr-trazabilidad-analisis-completo`

---

## Purpose

Informe canónico por artículo en hub **Producción → Reportes → Trazabilidad** (`kardex_articulo`): demanda PED, stock Terminado (incl. negativos), brecha Pedido vs PED Urgente, BOM pack, movimientos unificados con saldo corrido y export CSV. MUST ser la única fuente de verdad de datos para trazabilidad artículo; paridad operativa con análisis chat 610 T6 y fórmulas Tablero Pack.

## Requirements

### REQ-ANAL-01 — Servicio canónico

El sistema MUST exponer `construir_analisis_trazabilidad_articulo(base, id_articulo, desde, hasta, id_deposito?)` como único constructor del payload del slug `kardex_articulo`. MUST NOT mantener consultas paralelas duplicadas para los bloques DEMANDA, STOCK, BRECHA, MOVIMIENTOS o saldo corrido.

#### Scenario: Payload único para vista y export

- GIVEN artículo pack con movimientos en el período
- WHEN la vista `kardex_articulo` o el export CSV solicitan datos
- THEN ambos consumen el mismo servicio sin recomputar fuentes distintas

### REQ-ANAL-02 — Entrada hub

El slug `kardex_articulo` MUST permanecer en grupo **Trazabilidad** con búsqueda predictiva (`reportes_articulo_buscar_api`), filtros **Desde/Hasta** del shell y selector de depósito opcional (`Todos` = eje Terminado MPR / `suma_stock='Si'` como tablero pack).

#### Scenario: Depósito Todos usa eje Terminado

- GIVEN artículo pack y selector en «Todos»
- WHEN se calcula stock y saldo corrido
- THEN el eje MUST ser depósitos Terminado MPR, no un depósito Semi arbitrario

### REQ-ANAL-03 — Cabecera artículo

La UI MUST mostrar `id_articulo`, código manual, descripción completa, `tipo_art_fab` e indicador pack (BOM) vs componente. MUST desambiguar códigos duplicados (ej. varios «610»).

#### Scenario: Cabecera desambigua código

- GIVEN búsqueda que devuelve varios artículos con mismo código
- WHEN el usuario selecciona uno
- THEN la cabecera muestra descripción e IDArt distintivos

### REQ-ANAL-04 — Bloque DEMANDA PED

El sistema MUST listar renglones PED no anulados con estado comercial distinto de `Facturado` y `Cerrado`, usando `_listar_demanda_ped_vivo_fifo` (o equivalente vigente) filtrado por `id_articulo`. MUST mostrar nro pedido, cliente, fecha (dd/MM/yyyy), cantidad pedida/pendiente y estado OPT si existe. MUST agregar **Pedido (P_ped)** = suma pendiente comercial del artículo.

#### Scenario: Paridad tablero Pack

- GIVEN artículo pack con PED pendiente comercial
- WHEN se abre el análisis con mismas fechas que tablero Pack
- THEN P_ped coincide con tablero en docenas/pares según toggle hub

#### Scenario: Excluye Facturado/Cerrado

- GIVEN pedido PED en estado Facturado
- WHEN se construye demanda
- THEN ese pedido MUST NOT aparecer en el bloque DEMANDA

### REQ-ANAL-05 — Bloque STOCK actual

El sistema MUST mostrar saldo **Terminado** real (negativos visibles, sin clamp a 0) en depósitos `suma_stock='Si'`. SHOULD mostrar Semi / 2da / Producción cuando el artículo es componente o el pack tiene BOM.

#### Scenario: Terminado negativo visible

- GIVEN saldo Terminado −12 pares
- WHEN se renderiza STOCK
- THEN la UI muestra −12 con estilo de alerta, no 0

### REQ-ANAL-06 — Bloque BRECHA

El sistema MUST calcular con paridad Tablero Pack (pares internos; UI docenas|pares):

- `PED Urgente = max(0, P_ped − Terminado)`
- `TOT Urgente = max(0, P_ped + Reserva − Terminado)` donde `Reserva = articulo.stock_reserva`

MUST mostrar texto explicativo cuando Terminado < 0 (ej. «PED Urgente = Pedido + |Terminado|»).

#### Scenario: Brecha con Terminado negativo

- GIVEN P_ped=100 y Terminado=−20
- WHEN se calcula brecha
- THEN PED Urgente=120 y la UI explica la relación con Terminado negativo

### REQ-ANAL-07 — Bloque BOM (pack)

Para artículos pack, el sistema MUST listar componentes (código, descripción, cantidad BOM) con enlace al análisis del componente (`kardex_articulo` + `id_articulo` del componente). SHOULD mostrar `max_packs` armables desde Semi.

#### Scenario: Link a análisis componente

- GIVEN pack con 3 componentes en BOM
- WHEN el usuario activa el enlace de un componente
- THEN navega al análisis trazabilidad de ese componente, no a timeline aislado

### REQ-ANAL-08 — Movimientos unificados

El collector MUST unir cronológicamente en el período:

| Tipo | Fuente |
|------|--------|
| OPA/ARMADO, OPP | `movimiento_stock` MSTOCK |
| REM, FA | tabla `stock` (`Comprobante IN ('REM','FA')`) |
| Inventario/ajuste | MSTOCK por motivo / `TipoComp` |
| Envío/parte/clasificación MPR | tablas `mpr_*` |

MUST deduplicar OPP duplicados (MSTOCK vs `mpr_parte`) por `codigo_movimiento` o regla equivalente documentada. MUST etiquetar tipos OPA, REM, FA, INV, MPR en UI. MUST detallar salida de componentes Semi en OPA pack (subfilas o modal existente).

#### Scenario: REM y OPA en misma ventana

- GIVEN pack con OPA y REM en jul–sep/2026
- WHEN se lista movimientos
- THEN ambos aparecen ordenados cronológicamente con etiquetas distintas

#### Scenario: Dedupe OPP

- GIVEN mismo OPP en MSTOCK y `mpr_parte_linea`
- WHEN se unen movimientos
- THEN aparece una sola fila OPP en la tabla

### REQ-ANAL-09 — Saldo corrido Terminado

El saldo corrido MUST iniciar en stock real al **inicio** de `desde` (movimientos previos al período), no en 0 silencioso. Si el cálculo falla, MUST mostrar advertencia visible; MUST NOT usar 0 sin aviso.

#### Scenario: Saldo inicial real

- GIVEN saldo 50 al día anterior a `desde` y +10 OPA en ventana
- WHEN se calcula saldo corrido
- THEN la primera fila de ventana parte de 50 y cierra coherente con +10 neto

#### Scenario: Fallback con advertencia

- GIVEN error al resolver saldo inicial
- WHEN se renderiza MOVIMIENTOS
- THEN la UI muestra banner de advertencia y MUST NOT afirmar saldo inicial=0 sin calificar

### REQ-ANAL-10 — FA e inventario sin efecto depósito

Movimientos FA MUST listarse en MOVIMIENTOS. Si FA no afecta `stock_deposito` Terminado, MUST NOT sumarse al saldo corrido Terminado. MUST exponer columna o indicador **Afecta depósito**. Inventario MUST clasificarse por motivo (faltante/sobrante/inventario) y `TipoComp` cuando exista.

#### Scenario: FA visible sin mover saldo

- GIVEN movimiento FA que no impacta depósito Terminado
- WHEN se muestra en tabla
- THEN aparece etiquetado FA, «Afecta depósito»=No, y el saldo corrido no cambia en esa fila

### REQ-ANAL-11 — Bloque A PRODUCIR

MUST mostrar cantidad a fabricar/armar alineada a TOT Urgente (o PED Urgente según toggle docenas). SHOULD calcular capacidad desde Semi = `floor(min(saldo_semi_i / bom_i))` y alertar si PED Urgente > 0 y Semi = 0.

#### Scenario: Alerta Semi insuficiente

- GIVEN PED Urgente > 0 y saldo Semi del limitante = 0
- WHEN se renderiza A PRODUCIR
- THEN la UI muestra alerta de capacidad nula

### REQ-ANAL-12 — Export CSV v1

El hub MUST ofrecer **Exportar CSV** del análisis completo (UTF-8 BOM, encabezados español) con columnas por bloque o secciones lógicas equivalentes al Excel chat. Export Excel multi-hoja MAY diferirse (stretch).

#### Scenario: CSV refleja bloques pantalla

- GIVEN análisis renderizado con DEMANDA y MOVIMIENTOS
- WHEN el usuario exporta CSV
- THEN el archivo incluye filas de ambos bloques con encabezados en español

### REQ-ANAL-13 — UX, permisos y canon UI

MUST exigir permiso reportes MPR (`mpr.reportes` / mixin vigente). UI MUST estar en español, fechas dd/MM/yyyy, toggle Docenas|Pares del shell, canon `ui-fuente-verdad-reportes-mpr`. MUST NOT usar `alert`/`confirm`/`prompt` nativos.

#### Scenario: Acceso denegado

- GIVEN usuario sin permiso `mpr.reportes`
- WHEN intenta abrir `kardex_articulo`
- THEN el sistema deniega acceso según patrón MPR existente
