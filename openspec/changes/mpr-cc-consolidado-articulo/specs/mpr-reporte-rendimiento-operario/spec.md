# Delta — Reporte rendimiento por operario (Semi consolidado)

**Capability:** `mpr-reporte-rendimiento-operario`  
**Change:** `mpr-cc-consolidado-articulo`  
**Base:** `openspec/changes/mpr-docenas-clasificacion-operario/specs/mpr-reporte-rendimiento-operario/spec.md`

---

## ADDED Requirements

### Requirement: Semi consolidado excluido de métricas por operario

Las transiciones SemiElaborado con `id_operario IS NULL` (confirmación CC consolidada por artículo) MUST NOT incrementar **Semi elaborado**, **% Apto** ni el stack/gráfico de **1ra selección por operario**. MUST NOT atribuirse a fila «Sin atribución» del operario nombrado ni prorratearse al fabricado del operario.

#### Scenario: Día con solo Semi consolidado

- DADO operario García con fabricado 600 u. y Semi 480 u. con `id_operario NULL` el mismo día
- CUANDO se consulta Producción → Por operario
- ENTONCES García muestra semi 0 en columna y % apto «—» o 0 según convención UI; el Semi NO aparece en su barra apilada de 1ra

#### Scenario: 2da y scrap siguen atribuidos

- DADO García con 60 u. a 2da y 60 u. a scrap con `id_operario` suyo
- CUANDO se consulta el reporte
- ENTONCES 2da y scrap sí suman en sus columnas y en el apilado de calidad del operario

---

## MODIFIED Requirements

### Requirement: Métricas de calidad por operario fabricante

El reporte **Producción → Por operario** SHALL calcular por operario en el período:

| Métrica | Definición |
|---------|------------|
| Fabricado | Σ `mpr_parte_linea.cantidad` (unidades) |
| Semi elaborado | Σ transiciones a semi con `id_operario` = operario (**MUST NOT** incluir `id_operario IS NULL`) |
| 2da selección | Σ transiciones a 2da con `id_operario` = operario |
| Scrap | Σ transiciones a scrap con `id_operario` = operario |
| % Apto | `semi / fabricado × 100` si fabricado > 0 |
| % Scrap | `scrap / fabricado × 100` si fabricado > 0 |

(Previously: Semi con operario del fabricante en cada fila de clasificación.)

#### Scenario: Operario con fabricado y clasificación mixta

- CUANDO García fabricó 600 u., Semi 480 con operario García (histórico) y además existe Semi 200 con `id_operario NULL` el mismo día
- ENTONCES el reporte muestra semi 480 (solo filas con operario), no 680

#### Scenario: Fabricado sin clasificación atribuible

- CUANDO hay parte pero ninguna transición con `id_operario` del operario
- ENTONCES semi, 2da y scrap muestran 0; % apto y % scrap muestran «—» o 0 según convención UI

---

### Requirement: Histórico sin atribución de operario

Las transiciones con `id_operario IS NULL` SHALL mostrarse en fila o sección **«Sin atribución»** cuando el reporte agrega Semi huérfano o histórico sin operario. MUST NOT sumarse al total Semi de ningún operario nombrado. MUST NOT duplicar conteo con filas que sí tienen operario.

(Previously: agrupaba NULL genérico sin excluir explícitamente Semi CC del stack por operario.)

#### Scenario: Mezcla histórico Semi con operario y Semi NULL

- CUANDO el período incluye Semi histórico con operario y Semi CC con NULL
- ENTONCES operarios nombrados solo suman sus Semi con operario; el NULL aparece solo en «Sin atribución» si el reporte lo expone

#### Scenario: Sin doble conteo

- CUANDO existe una sola fila Semi NULL por artículo/día
- ENTONCES esa cantidad MUST NOT repetirse en columnas de dos operarios distintos
