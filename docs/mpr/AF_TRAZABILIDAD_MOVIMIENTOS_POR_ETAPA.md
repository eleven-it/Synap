# Trazabilidad por artículo: movimientos por depósito/etapa (paridad con inventario)

**Estado:** listo para arquitecto de solución · **Tipo:** análisis funcional · **Fecha:** 17/09/2026  
**Producto:** Synap MPR · **Pantalla:** Análisis trazabilidad (kardex por artículo)  
**Referencia de paridad:** Inventario por etapa (ámbito Fabricados)

---

## Qué se necesita (en una frase)

Que el **historial de movimientos** del análisis de trazabilidad de un **componente fabricado** se pueda leer **por depósito/etapa del pipeline** (Producción, Semi elaborado, 2da Selección), de modo que la reconstrucción del saldo en el tiempo **coincida** con lo que muestra el inventario por etapa (columnas + consolidado), no solo con el total pipeline.

---

## Problema de negocio

Hoy el usuario ve:

| Vista | Qué muestra | Ejemplo art. IDArt 1115 |
|-------|-------------|-------------------------|
| **Inventario por etapa** (Fabricados) | Saldo **actual** partido: Producción / Semi elaborado / 2da Selección / **Consolidado** | 79 + 28 + 0 = **107** |
| **Análisis trazabilidad** | Un solo corrido de saldo sobre el **pipeline consolidado** | STOCK **107**, sin saber cuánto en cada etapa |

El consolidado cuadra, pero **no se puede auditar** “cómo llegaron a 79 en Producción y 28 en Semi” ni explicar transferencias internas del pipeline (p. ej. OPP Producción → Semi) como cambio de etapa: en el kardex consolidado suelen **netear** o quedar opacas.

**Impacto:** gerencia/producción no puede conciliar el kardex con el tablero de inventario por etapa; la trazabilidad pierde valor de control operativo.

---

## Alcance

### Incluido

- Reporte hub MPR:  
  `/mpr/reportes/?grupo=trazabilidad&reporte=kardex_articulo&id_articulo=…&desde=…&hasta=…&presentacion=…`
- Artículos **componente** (no pack) cuyo eje actual es **pipeline fabricados**  
  (`tipo_eje = pipeline_fabricados`: depósitos Producción + Semi elaborado + 2da Selección).
- Presentaciones ya existentes (Pares / Docenas) y export CSV alineado al nuevo desglose.
- Criterio de paridad con **Inventario por etapa · Fabricados** (mismas etapas y orden de columnas).

### Excluido (fuera de este pedido)

- Rediseñar el **inventario por etapa** (ya es la fuente de verdad de saldos actuales por etapa).
- Timeline de una OPT (`/mpr/opt/<id>/trazabilidad/`) — es otro producto.
- Inventario físico / campañas de conteo.
- Cambiar reglas de negocio de OPP/OPA/REM/FA (solo **cómo se presentan y se acumulan** por depósito).
- Packs en depósito Terminado: hoy ya van por eje `terminado` (un depósito); no es el gap principal de este AF. El arquitecto puede decidir si reutiliza el mismo patrón multi-eje más adelante.

---

## Actores y casos de uso

| Actor | Necesidad |
|-------|-----------|
| Supervisor / planificación MPR | Entender en qué etapa está el stock y cómo se movió entre etapas. |
| Auditoría / calidad | Reconstruir histórico hasta el consolidado y por columna de etapa. |
| Operación | Confirmar que un OPP/OPA entre depósitos del pipeline explica el cambio Producción ↔ Semi. |

**Caso de uso principal**

1. Usuario abre Análisis trazabilidad de un componente fabricado (rango de fechas).
2. Ve movimientos con **identificación de depósito/etapa**.
3. Puede seguir el **saldo por etapa** (y el consolidado) a lo largo del tiempo.
4. Al cierre del rango (o “hoy”), los saldos por etapa concilian con Inventario por etapa para el mismo artículo.

---

## Situación actual (as-is)

### Inventario por etapa (contrato de referencia)

- Ámbito **Fabricados**: columnas `Produccion` → «Producción», `SemiElaborado` → «Semi elaborado», `2daSeleccion` → «2da Selección», más **Consolidado** = suma de las tres.
- Fuente: `stock_deposito` + `deposito.tipo_mpr` (instantáneo, no histórico).
- Implementación: `stock/services/inventario_tabla.py`, UI Stock / MPR inventario.

### Análisis trazabilidad (as-is)

- Servicio: `mpr/services_kardex_articulo.py` → `construir_analisis_trazabilidad_articulo`.
- UI: `mpr/templates/mpr/reportes/partials/kardex_articulo.html`.
- Componente no-pack: filtra `CodDeposito IN` pipeline (`get_depositos_pipeline_fabricados_mpr`), etiqueta «Stock consolidado pipeline», **un** `saldo_corrido`.
- Tabla movimientos: Fecha | Tipo | Comprobante | Qué pasó | Conteo | Entrada | Salida | **Saldo** — **sin Depósito/Etapa**.
- **Qué pasó (OPP de parte):** `Parte · turno {nombre} · OPT {n} · {operario}`. Fecha de producción solo si difiere de la fecha del movimiento; hora (`HH:mm`) solo si ese turno tiene más de un parte. Sin UUID y sin copiar el comprobante. Filas legado `OPP-parte {uuid}` se rehidratan desde `mpr_parte` (MySQL empresa).
- Agrupación por comprobante / neto entre depósitos del mismo movimiento: las transferencias internas del pipeline **no reconstruyen** saldos por etapa.
- Depósito aparece solo en subfilas OPA (componentes de armado), no en el corrido principal del componente.
- CSV: sin columna depósito/etapa.

### Distinción pack vs componente (as-is)

| Tipo artículo | Eje | `tipo_eje` |
|---------------|-----|------------|
| Pack (tiene ABM pack) | Depósito Terminado | `terminado` |
| Componente, ≥2 depósitos pipeline | Producción + Semi + 2da | `pipeline_fabricados` |
| Componente, 1 depósito pipeline | Ese depósito | `semi` |

Este AF apunta al caso **`pipeline_fabricados`**.

---

## Situación objetivo (to-be)

### Principio

**Misma semántica de etapas que el inventario fabricados**, aplicada al **historial**:

1. Cada movimiento que afecta stock del pipeline declara **depósito (o etapa `tipo_mpr`)** de impacto.
2. Existe **saldo corrido por etapa** (y consolidado = suma de etapas del ámbito).
3. Una transferencia entre dos depósitos del pipeline se ve como **salida en origen + entrada en destino** (dos impactos o una fila con origen/destino explícitos), **sin perder** el efecto neto por etapa.
4. Al final del período (o al “hoy”),  
   `saldo_etapa(trazabilidad) ≈ saldo_etapa(inventario)`  
   para Producción, Semi elaborado, 2da Selección y Consolidado (tolerancia de redondeo de presentación Pares/Docenas).

### Experiencia de usuario (mínimo viable funcional)

Sin diseñar UI detallada (eso es del arquitecto/UX), el producto debe permitir:

| Capacidad | Descripción |
|-----------|-------------|
| Ver etapa en cada movimiento | El usuario identifica en qué depósito/etapa impactó (Producción / Semi / 2da). |
| Seguir saldos por etapa | Puede leer cómo evolucionó cada columna, no solo el consolidado. |
| Consolidado coherente | El consolidado del kardex = suma de etapas en cada punto del corrido (o al menos en inicial y cierre). |
| Filtrar o enfocarse (deseable) | Ver una etapa o todas; el AF no impone el control exacto (tabs, filtro, columnas). |
| Export | CSV incluye etapa/depósito y, si hay saldos por etapa, columnas suficientes para auditar. |

### Ejemplo de aceptación (artículo 1115, ilustrativo)

Datos de inventario (captura 17/09/2026, presentación Pares):

| Etapa | Saldo |
|-------|------:|
| Producción | 79 |
| Semi elaborado | 28 |
| 2da Selección | 0 |
| Consolidado | 107 |

En trazabilidad (mismo artículo, rango que cubra “hoy”):

- El cierre del corrido (o badge de stock) debe poder desglosarse como **79 / 28 / 0** y consolidado **107**.
- Los OPP/OPA del rango deben atribuirse a la etapa correcta; un movimiento Producción → Semi debe **bajar** Producción y **subir** Semi en el histórico, dejando el consolidado según el neto real (a menudo sin cambio de consolidado en transferencia pura).

---

## Requisitos funcionales

### MUST

1. **RF-01** Para componentes con eje `pipeline_fabricados`, cada movimiento que afecta depósito debe asociarse a al menos un **depósito del pipeline** (o su `tipo_mpr`).
2. **RF-02** El análisis debe exponer **saldos por etapa** del pipeline (Producción, Semi elaborado, 2da Selección) en el corrido histórico (inicial + tras cada movimiento relevante, o modelo equivalente verificable).
3. **RF-03** El **consolidado** del análisis = suma de las tres etapas del ámbito fabricados (misma regla que inventario).
4. **RF-04** Transferencias / OPP entre depósitos del pipeline **no** deben ocultarse en un neto único que impida reconstruir saldos por etapa.
5. **RF-05** Con rango que incluye la fecha de hoy (o “Hasta ≥ hoy”), los saldos por etapa al cierre deben **conciliar** con Inventario por etapa (Fabricados) para el mismo artículo y unidad de presentación, salvo diferencia documentada (p. ej. movimientos posteriores al “ahora” de la consulta).
6. **RF-06** La UI del reporte de movimientos debe mostrar la dimensión depósito/etapa de forma explícita (columna, agrupación o equivalente usable).
7. **RF-07** Export CSV debe incluir la dimensión depósito/etapa alineada a la grilla.

### SHOULD

8. **RF-08** Permitir filtrar o focalizar una etapa sin perder el consolidado de referencia.
9. **RF-09** Badges/KPIs de cabecera: además del consolidado, mostrar desglose por etapa (o enlace claro al desglose).
10. **RF-10** Mantener comportamiento actual de packs (eje Terminado) sin regresiones; documentar si se unifica el patrón multi-eje.

### MUST NOT (restricciones de producto)

11. **RF-11** No cambiar el significado de columnas del inventario por etapa.
12. **RF-12** No usar diálogos nativos del navegador en cambios de UI Synap.
13. **RF-13** No inventar etapas fuera del catálogo `tipo_mpr` del pipeline fabricados para este ámbito.

---

## Criterios de aceptación (verificación)

- [ ] Componente pipeline: en la grilla de movimientos se identifica la etapa/depósito de cada impacto.
- [ ] Saldo inicial histórico se calcula **por etapa** (y consolidado = suma), no solo un número pipeline.
- [ ] Tras reproducir el rango, cierre Producción / Semi / 2da / Consolidado cuadra con inventario por etapa (caso de prueba con artículo real de pipeline, p. ej. el de la captura 1115 o fixture de tests).
- [ ] Un movimiento documentado Producción → Semi altera esas dos columnas en sentidos opuestos y deja el consolidado coherente.
- [ ] Pack (eje Terminado): sin regresión de saldo único / UI.
- [ ] CSV exportable con etapa/depósito.
- [ ] Textos automatizados de contrato: paridad cierre kardex vs saldos `stock_deposito` por `tipo_mpr` del pipeline.

---

## Reglas de negocio a preservar (contexto para el arquitecto)

- FA puede listarse pero **no mueve** saldo de depósito en el corrido actual (`afecta_deposito=False`) — confirmar si se mantiene.
- Presentación Pares/Docenas afecta solo visualización/factor de conversión, no la existencia de etapas.
- Pipeline MPR fabricados: `TIPOS_MPR_PIPELINE_FABRICADOS` = `Produccion`, `SemiElaborado`, `2daSeleccion` (`mpr/services.py`).
- Inventario fabricados no incluye Terminado en el consolidado de ese ámbito.

---

## Preguntas abiertas (cerradas en diseño oleada 1 — 17/09/2026)

1. **UI MVP:** columna **Etapa** + columnas de saldo por etapa y **Consolidado** (una sola fila de encabezado). Filtro/pestaña por etapa → oleada 2 (RF-08).
2. **Transferencias pipeline:** **dos renglones** (salida origen, entrada destino), salida primero.
3. **Corrido multi-etapa:** cálculo **solo en backend** (`saldos_por_etapa` + consolidado derivado).
4. **Packs Terminado:** **fuera de oleada 1**; eje `terminado` sin desglose por etapa.
5. **Conciliación:** estricta por etapa solo si **`Hasta >= hoy`**; sin snapshot histórico de etapas.

---

## Entregables esperados del arquitecto (siguiente paso)

1. Diseño de solución (modelo de datos en memoria / consultas, contrato API del análisis, cambios UI/CSV).
2. Decisión de agrupación de movimientos (dejar de netear transferencias internas del pipeline).
3. Plan de tests de paridad (kardex cierre vs `inventario_tabla` / `stock_deposito`).
4. Estimación de oleadas si se parte MVP (p. ej. solo columna etapa + saldos cierre por etapa) vs corrido multi-columna completo.
5. Actualización de este doc o spec SDD enlazada cuando exista change.

---

## Referencias técnicas (as-is, no son diseño)

| Pieza | Path |
|-------|------|
| Análisis trazabilidad | `mpr/services_kardex_articulo.py` |
| Vista hub reportes | `mpr/views.py` (`ReportesMPRView`, grupo trazabilidad) |
| Partial UI | `mpr/templates/mpr/reportes/partials/kardex_articulo.html` |
| CSV hub | `mpr/reportes_hub.py` |
| Pipeline depósitos | `mpr/services.py` (`get_depositos_pipeline_fabricados_mpr`, `TIPOS_MPR_PIPELINE_FABRICADOS`) |
| Inventario por etapa | `stock/services/inventario_tabla.py` |
| Tests kardex / análisis | `mpr/tests/test_kardex_articulo.py`, `mpr/tests/test_analisis_trazabilidad_articulo.py` |

---

## Checklist de handoff AF → Arquitecto

- [x] Problema y valor de negocio enunciados
- [x] As-is vs to-be contrastados con ejemplo real
- [x] Alcance / fuera de alcance
- [x] Requisitos MUST/SHOULD/MUST NOT
- [x] Criterios de aceptación verificables
- [x] Preguntas abiertas listadas
- [x] Punteros a código as-is
- [ ] Firma de producto (pendiente humano)
- [ ] Diseño de solución (pendiente arquitecto)
