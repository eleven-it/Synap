# Delta — Shell reportes MPR

**Capability:** `mpr-reportes-shell`  
**Change:** `mpr-inventario-deposito-articulo`

## MODIFIED Requirements

### REQ-SHELL-02 — Filtro de período sticky

The system MUST provide campos **Desde** y **Hasta** con formato de visualización **dd/MM/yyyy** y presets: Hoy, Últimos 7 días, Mes actual, Mes anterior.

The filter MUST persist in URL query parameters and apply to all reportes del grupo activo excepto trazabilidad (que MAY override con artículo obligatorio) e **inventario_deposito** (que MUST usar `fecha_corte` en lugar de Desde/Hasta).

(Previously: solo trazabilidad exceptuaba el filtro de período.)

#### Scenario: Inventario depósito ignora período shell

- GIVEN hub en reporte `inventario_deposito`
- WHEN usuario cambia preset «Mes actual» en Desde/Hasta
- THEN la consulta sigue gobernada por `fecha_corte`, no por Desde/Hasta

### REQ-SHELL-03 — Navegación por grupos

The system MUST organize reportes en grupos:

| Grupo | Reportes |
|-------|----------|
| Producción | Resumen diario, Operario, Cadena pipeline, Pendiente componentes |
| Demanda | Brecha pack, Pedidos por estado (P1), **Inventario depósito** (`inventario_deposito`) |
| Trazabilidad | Línea de tiempo, Movimientos (P1) |
| Histórico OPT | OPT cerradas, WIP OPT, Desperdicio legacy |

Default group MUST be **Producción** → **Resumen diario**.

(Previously: Demanda no listaba Inventario depósito.)

#### Scenario: Navegación a inventario depósito

- GIVEN hub cargado
- WHEN usuario elige Demanda → Inventario depósito
- THEN URL `grupo=demanda&reporte=inventario_deposito` y partial del reporte

## ADDED Requirements

### REQ-SHELL-10 — Export Excel por reporte

Cuando el reporte activo declare soporte Excel en el registro del hub, el shell MUST ofrecer **Exportar Excel** (`format=xlsx`) además de CSV. MUST respetar filtros activos y encabezados en español. Con `inventario_deposito` activo, export xlsx MUST incluir Stock y Docenas.

#### Scenario: Export Excel inventario

- GIVEN `inventario_deposito` con datos
- WHEN usuario exporta Excel
- THEN descarga `.xlsx` con filtros vigentes y total docenas

#### Scenario: Reporte solo CSV

- GIVEN reporte sin flag Excel en hub
- WHEN se muestra barra de acciones
- THEN solo Exportar CSV visible
