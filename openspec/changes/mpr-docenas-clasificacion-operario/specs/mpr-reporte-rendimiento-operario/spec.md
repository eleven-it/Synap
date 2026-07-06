# Spec — Reporte rendimiento por operario

**Capability:** `mpr-reporte-rendimiento-operario`  
**Change:** `mpr-docenas-clasificacion-operario`  
**Estado:** Propuesto  
**Relacionado:** `openspec/changes/mpr-reportes-trazabilidad-produccion/specs/mpr-reporte-operario/spec.md`

---

## ADDED Requirements

### Requirement: Métricas de calidad por operario fabricante

El reporte **Producción → Por operario** SHALL extender sus columnas para incluir, por operario en el período filtrado:

| Métrica | Definición |
|---------|------------|
| Fabricado | Σ `mpr_parte_linea.cantidad` (unidades) |
| Semi elaborado | Σ transiciones a semi con `id_operario` = operario |
| 2da selección | Σ transiciones a 2da con `id_operario` = operario |
| Scrap | Σ transiciones a scrap con `id_operario` = operario |
| % Apto | `semi / fabricado × 100` si fabricado > 0 |
| % Scrap | `scrap / fabricado × 100` si fabricado > 0 |

#### Scenario: Operario con fabricado y clasificación

- **WHEN** García fabricó 600 u. y se clasificaron 480 semi, 60 2da, 60 scrap en el período
- **THEN** el reporte muestra fabricado 50 doc. (si presentación docenas), semi 40 doc., 2da 5 doc., scrap 5 doc., % apto 80, % scrap 10

#### Scenario: Fabricado sin clasificación aún

- **WHEN** hay parte pero ninguna transición con `id_operario` del operario
- **THEN** semi, 2da y scrap muestran 0; % apto y % scrap muestran «—» o 0 según convención UI existente

---

### Requirement: Presentación docenas en reporte operario

El reporte SHALL respetar el parámetro de presentación del hub de reportes; cuando es `docenas`, las columnas de cantidad se muestran en docenas con el mismo formato que otros reportes MPR.

#### Scenario: Coherencia con stock

- **WHEN** presentación docenas activa
- **THEN** las celdas usan `texto_docenas_unidades` o equivalente del módulo reportes

---

### Requirement: Histórico sin atribución de operario

Las transiciones con `id_operario IS NULL` SHALL agruparse en fila o sección «Sin atribución» y MUST NOT atribuirse a ningún operario nombrado.

#### Scenario: Mezcla histórico y nuevo

- **WHEN** el período incluye transiciones pre-migración y post-migración
- **THEN** el reporte totaliza correctamente sin doble conteo

---

### Requirement: Filtros del reporte

El reporte SHALL aceptar al menos: rango de fechas, turno opcional, marca opcional y búsqueda por operario o artículo si el patrón del hub lo soporta.

#### Scenario: Filtro por turno

- **WHEN** el usuario filtra turno Mañana del 08/07/2026
- **THEN** fabricado y clasificaciones se limitan a ese turno

---

### Requirement: Entrega en mismo release

La ampliación del reporte SHALL desplegarse en el **mismo release** que la grilla de clasificación por operario, para que supervisores validen rendimiento con datos nuevos.

#### Scenario: Release coordinado

- **WHEN** se despliega clasificación por operario sin reporte ampliado
- **THEN** el criterio de release P0 no se cumple — ambos deben ir juntos

---

## MODIFIED Requirements

### Requirement: Reporte operario solo fabricado (comportamiento anterior)

El reporte que mostraba únicamente cantidad fabricada desde parte queda **modificado** para incluir el desglose de calidad descrito arriba; la columna fabricado se mantiene como métrica base.

#### Scenario: Columna fabricado preservada

- **WHEN** un consumidor esperaba solo «producido»
- **THEN** la columna fabricado/producido sigue disponible sin renombrar el slug del reporte

---

## P1 (opcional)

### Requirement: Gráfico apilado semi / 2da / scrap

En P1 el reporte MAY incluir gráfico de barras apiladas por operario con las tres categorías de calidad.

#### Scenario: Vista gráfica

- **WHEN** P1 está activo y hay datos
- **THEN** el usuario puede alternar tabla y gráfico sin cambiar filtros
