# Plan de migración Accera V.3.5 → módulo Synap Mtrix

**Estado:** decisiones cerradas el 12/08/2026.  
**Change SDD:** `openspec/changes/mtrix-modulo-synap/`  
**Origen:** `/Users/sebastian/Documents/Accera/ACCERA V.3.5/Software/Principal.bas`

## 1. Decisiones cerradas

| # | Pregunta | Decisión |
|---|----------|----------|
| 1 | Fuente de verdad | ACCERA V.3.5 (CSV MTRIX). No se migra el layout Accera `H/V/E`. |
| 2 | Entrega | Todo: preview en pantalla, descarga local y envío SFTP. |
| 3 | Ejecución | On-demand + cron con programador en UI. |
| 4 | NC/ND | Tipo documento `N` y cantidad negativa (código VB6). |
| 5 | FV / jerarquía | Se mantiene la exportación plana (`GERENTE GENERAL` / `SUPERVISOR`). En pantalla se puede formatear. |
| 6 | CI | Solo clientes con ventas en el período, como ahora. |
| — | Contrato CSV | **No se cambia** el armado de archivos. Solo se agregan preview, SFTP, on-demand y programador. |
| — | CNPJ fornecedor | CUIT de `datosempresa` (mismo que distribuidor). No es campo de formulario. |
| — | Reenvío VD | Marca de agua + solape 1 día tras SFTP OK. CI/PD/ES/FV siempre snapshot. |

Quirks de V.3.5 (p. ej. `REPRESENTATIVIDADE` con `FORMAT` `de_DE`) se **replican en el CSV**. El preview puede mostrar el valor de forma legible.

## 2. Qué es Mtrix en Synap

App Django `mtrix` en `/mtrix/`. Lee MySQL AdministraNET (solo SELECT, `get_mysql_pool()`, `administranet_types`). Persiste config, jobs y artefactos en PostgreSQL. No altera tablas VB6.

Patrones a copiar:

- Jobs/config: `odoo_migracion`
- SFTP: `core/backup/services/sftp_upload.py` (paramiko), credenciales **por empresa** cifradas (como API key Odoo), no el SFTP de backup
- Programador UI: `/core/backups/configuracion/`
- Look & feel: reportes `/reports/dashboard/` y MPR (`base_mpr`, `opt_list`, wizard). No usar pantallas de `ventas/`
- Feedback: modales Synap / `SynapMessages` / `synapShowPostLoading`. Sin `alert`/`confirm`

## 3. Arquitectura

```
UI preview (formato humano)
        │  mismos extractores
        ▼
extractors CI/PD/ES/VD/FV  ──► serializer CSV V.3.5 (congelado) ──► artefactos
        │                                                              │
        └──────────────────────► tabla en pantalla                     ├─ descarga
                                                                       └─ SFTP MTRIX
```

Un solo motor de datos. Dos presentaciones: pantalla vs CSV. El serializer de exportación es la copia fiel de `Principal.bas`.

### Modelos PostgreSQL (propuestos)

- `MtrixConfig` — por `base_empresa`: fechas, proveedores, CNPJ fornecedor, `pvnf`, multiplicadores, tipos habilitados, SFTP (host/puerto/usuario/path, secreto cifrado), programador (activo, hora, días).
- `MtrixJob` — corrida (origen: ui / cron), estado, rango de fechas, usuario, log, error.
- `MtrixArtifact` — archivo (tipo CI/PD/ES/VD/FV, proveedor, nombre, checksum, bytes), estado SFTP.

### Permisos

`mtrix.ver`, `mtrix.configurar`, `mtrix.generar`, `mtrix.enviar_sftp`, `mtrix.*`

## 4. Pantallas

| Ruta | Rol |
|------|-----|
| `/mtrix/` | Hub: última corrida, KPIs, accesos a los cinco reportes, Generar, Enviar |
| `/mtrix/preview/ci/` … `/fv/` | Validación en tabla (paginada, totales, filtros del config). Fechas `dd/MM/yyyy` |
| `/mtrix/configuracion/` | Parámetros de exportación + SFTP (probar conexión) + programador |
| `/mtrix/jobs/` | Historial |
| `/mtrix/jobs/<id>/` | Log, artefactos, re-descarga, reenvío SFTP |

Flujo on-demand: configurar → validar en preview → confirmar (modal) → job en background → descargar y/o SFTP.

Flujo cron: el programador dispara el mismo pipeline **sin preview**; el operador revisa el job a posteriori.

Una sola corrida activa por `base_empresa` (equivalente a `PrevInstance`).

## 5. Fases

| Fase | Entrega | Hecho cuando |
|------|---------|--------------|
| 0 | Docs + SDD (este plan) | Change con proposal |
| 1 | App, menú, permisos, `MtrixConfig` | Hub autenticado |
| 2 | Extractors + serializer CSV + `generar_mtrix` | Golden tests vs reglas V.3.5 |
| 3 | Preview UI de los cinco tipos | Validar en pantalla con los mismos datos |
| 4 | Jobs, descarga ZIP/CSV | Paridad operativa con Salida/Histórico |
| 5 | SFTP (test + envío + reenvío) | Upload al path remoto; fallo no borra local |
| 6 | Programador UI + `--scheduled` | Cron host + calendario en config |

Orden de generadores en el job: CI → PD → ES → VD → FV.

## 6. Fuera de alcance

- Layout Accera antiguo (`ACC_PDVS`, `ACC_CADSITE`, `ACC_NFS`, marcadores H/V/E)
- Tablas `gerentes` / `supervisores` o cambio de jerarquía FV
- Ampliar CI a todo el padrón de clientes
- Cambiar headers, nombres de archivo, tipos de documento o fórmulas de agrupación VD
- Escrituras a MySQL AdministraNET
- Celery beat (el scheduler es cron de host + UI, como backup)

## 7. Riesgos

| Riesgo | Mitigación |
|--------|------------|
| Drift del CSV vs VB6 | Golden tests por tipo; serializer único; preview no reimplementa SQL |
| VD pesado (agrupación en memoria) | Streaming/agregación controlada; job async; loading Synap |
| SFTP caído | Artefacto local + `sftp_status=failed`; reenvío |
| Credenciales | Cifrado Postgres; permiso `mtrix.configurar`; nunca en `config.ini` |
| Dos corridas a la vez | Lock por `base_empresa` |

## 8. Criterios de éxito

- CSV de cada tipo cumple el inventario (headers, reglas NC/ND, consumidor final, **un archivo por categoría** por corrida).
- Preview muestra los mismos registros que irán al CSV, con formato de pantalla.
- Operador genera on-demand, descarga y envía por SFTP.
- Programador UI + `manage.py generar_mtrix --scheduled` produce un job equivalente.
- Cero diálogos nativos; UI en español; fechas al usuario en `dd/MM/yyyy`.
