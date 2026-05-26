# Propuesta: Presupuesto de ventas en Synap (PRE)

## Intención

Implementar el circuito **Presupuesto de cliente** (`TipoComprobante='PRE'` en MySQL) con paridad de proceso y persistencia respecto a AdministraNET VB6, exclusión CRM y módulo ERP proyecto, permisos por **puesto** (`permisos_sistema`), y PDF mediante el **módulo Reportes** (documento operativo, sin Crystal).

## Documento funcional de referencia

`docs/general/SPEC_PRESUPUESTO_VENTAS_SYNAP.md` (revisar versión vigente en cabecera) e inventario `docs/general/INVENTARIO_PRESUPUESTO_VENTAS_ADMINISTRANET_VB6.md`. Lista de tareas: `tasks.md`.

## Capabilities

### New Capabilities

| ID | Descripción |
|----|-------------|
| **ventas-presupuesto** | Emisión, consulta, modificación y numeración de PRE en Synap con escritura legacy alineada y reglas de permisos y reportes indicadas en el SPEC. |

### Modified Capabilities

Ninguna (no existe spec OpenSpec previo en `openspec/specs/` para este dominio).

## Enfoque

- Servicios transaccionales sobre MySQL legacy (patrón similar a otros flujos con `codmov`, `comp_ped`, `stockp`).
- Reutilizar `AdministraNETPermisosSistemaService` y sesión de usuario/puesto.
- Definición de reporte “Presupuesto” en `reports` como documento operativo.

## Riesgos / rollback

Riesgo: divergencia numérica con VB6 → mitigar con tests de integración MySQL y comparación de filas. Rollback: desactivar rutas/flags de feature hasta corregir.
