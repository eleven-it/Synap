# Módulo Mtrix

Exportación de sell-out AdministraNET → portal **MTRIX** (Diversey / DSI-VMI).

Migración del exe VB6 desatendido `Importacion_Accera.exe` (ACCERA V.3.5) a una app Django Synap. La **estructura de los CSV de exportación queda congelada** respecto de `Principal.bas` V.3.5. Synap agrega preview en pantalla, descarga, SFTP y programador.

Cada corrida genera **como máximo un archivo por categoría** (CI, PD, ES, VD, FV). La lista de proveedores filtra PD/ES/VD con `IN (...)`; no se emite un CSV por código.

## Documentos

| Documento | Contenido |
|-----------|-----------|
| [PLAN_MIGRACION.md](PLAN_MIGRACION.md) | Plan cerrado: decisiones, alcance, fases, pantallas |
| [INVENTARIO_EXPORTACION_VB6.md](INVENTARIO_EXPORTACION_VB6.md) | Inventario de generadores, config y reglas VB6 |

## Change SDD

`openspec/changes/mtrix-modulo-synap/`

## Origen VB6

`/Users/sebastian/Documents/Accera/ACCERA V.3.5/Software/Principal.bas`
