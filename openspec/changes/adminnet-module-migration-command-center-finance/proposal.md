# Proposal: Command Center — tesorería y ventas por cobro

**Cambio SDD:** `adminnet-module-migration-command-center-finance`  
**Exploraciones:** [cobros facturas](./exploration-cobros-facturas-venta.md), [tesorería](./exploration-tesoreria-administranet.md)

---

## Intent

Ampliar el **Command Center gerencial** con:

1. **Tesorería** — liquidez en **caja** (P0) y **banco** (P1), sin mezclar ambos en un solo saldo.
2. **Ventas por medio de cobro** — dos series: facturado al emitir vs cobrado en caja.

**Fuera de alcance:** impuestos/egresos impositivos (no entran en esta spec).  
**Fuera de alcance:** migrar pantallas VB6.

---

## Hallazgos clave

### Tesorería = dos capas

| Capa | Tablas | Command Center |
|------|--------|----------------|
| **Caja** | `caja_abm`, `caja_saldo`, `caja` | P0 — reutilizar lógica `cash_flow_*` en `query_runner` |
| **Banco** | `cuenta_banco`, `librobanco`, `transferencia`, `boletadeposito` | P1 — SQL nuevo (sin código en reports hoy) |

No sumar caja + banco en un único KPI: un mismo cobro puede pasar por caja y luego por depósito bancario.

### Movimientos internos en caja

Transferencias entre cajas y cierres de caja generan **egreso + ingreso** que se anulan en vista consolidada. Los informes Synap ya los excluyen del flujo operativo neto (`Tipo` LIKE `Transferencia de Fondos` / `Cierre de Caja`).

### Ventas por cobro = dos momentos

Ver [exploration-cobros-facturas-venta.md](./exploration-cobros-facturas-venta.md): facturación (`resumen_venta_cv` / `cuentacliente`) vs cobranza (`caja` + REC).

---

## Scope

### In scope

| Entregable | Descripción |
|------------|-------------|
| `tesoreria_metrics.py` | Agregados sobre `caja` (P0) |
| `ventas_cobros_metrics.py` | Facturado por medio + cobrado en caja (P0) |
| Endpoints P0 | Ver § Endpoints |
| Orquestador | Áreas `tesoreria`, `ventas_cobros` |
| UI Command Center | Dos tarjetas + sub-KPIs |
| Tests + `docs/reports/EXECUTIVE_DASHBOARD_API.md` | Contrato y documentación |

### Out of scope

- **Impuestos** / egresos por tipo impositivo (descartado en esta spec).
- Pantallas VB6 (Caja, LibroBanco, ReciboCobro, CargaMovCaja, arqueo).
- Escritura en MySQL.
- Refactor global de `query_runner`.
- Cierre/arqueo operativo (APIs TPV caja — otro cambio).
- Detalle paginado P1 (movimientos caja, libro banco) — solo diseño de rutas.

---

## Capabilities (para sdd-spec)

| Capability | Contenido |
|------------|-----------|
| `reports-executive-dashboard-tesoreria` | KPIs caja P0; banco P1 |
| `reports-executive-dashboard-ventas-cobros` | Facturado vs cobrado por medio |
| `reports-executive-dashboard` (delta) | Orquestador + áreas nuevas |

---

## Endpoints

### P0

```
GET /api/reports/executive-dashboard/tesoreria/resumen/
GET /api/reports/executive-dashboard/ventas/cobros/resumen/
```

### P1 (diseño, no P0)

```
GET /api/reports/executive-dashboard/tesoreria/banco/resumen/
GET /api/reports/executive-dashboard/tesoreria/movimientos-caja/
GET /api/reports/executive-dashboard/ventas/cobros/detalle/
```

---

## Contrato `tesoreria/resumen` (P0)

Solo **caja**. Campos orientativos:

```json
{
  "saldo_inicial": 0,
  "saldo_final": 0,
  "ingresos_operativos": 0,
  "egresos_operativos": 0,
  "variacion_neta": 0,
  "ingresos_ventas": 0,
  "ingresos_cobranzas": 0,
  "egresos_proveedores": 0,
  "por_tipo_caja": [
    { "tipo_caja": "Punto de Venta", "ingresos": 0, "egresos": 0, "variacion": 0 }
  ],
  "banco_disponible": false,
  "meta": {
    "notas_semanticas": [
      "Saldos y flujos desde tabla caja (último campo Saldo por caja_abm).",
      "Vista consolidada: excluye transferencias entre cajas y cierres de caja del neto operativo.",
      "No incluye libro banco (librobanco); ver endpoint tesoreria/banco en P1."
    ]
  }
}
```

**Fuentes SQL:** extraer de `_run_cash_flow_waterfall` + `_classify_movement` + `_run_cash_flow_by_account` (agrupado), en funciones puras en `tesoreria_metrics.py`.

---

## Contrato `ventas/cobros/resumen` (P0)

Sin cambios respecto a exploración previa; ver [exploration-cobros-facturas-venta.md](./exploration-cobros-facturas-venta.md).

```json
{
  "facturado_por_medio": {
    "efectivo": 0, "tarjeta": 0, "cuenta_corriente": 0,
    "cheque": 0, "transferencia": 0, "otros": 0, "total": 0
  },
  "cobrado_caja_por_medio": {
    "efectivo": 0, "tarjeta": 0, "cheque": 0,
    "transferencia": 0, "otros": 0, "total": 0
  },
  "meta": { "notas_semanticas": [] }
}
```

---

## Decisiones cerradas

| ID | Tema | Decisión |
|----|------|----------|
| D-IMP | Impuestos | **Fuera de esta spec** |
| D-TES-1 | Caja vs banco | Bloques separados; P0 solo caja |
| D-TES-2 | Saldo caja | Último `caja.Saldo` por `id_caja_abm_origen` (paridad cash-flow), no `caja_saldo` en P0 |
| D-TES-3 | Neto consolidado | Excluir transferencias y cierres de caja del neto operativo |
| D-TES-4 | Subcategorías | Exponer al menos ventas / cobranzas / proveedores en P0 |
| D-COB-1 | Ventas cobro | Dos series: facturado vs cobrado caja (ver exploración cobros) |
| D-COB-2 | `medio_cobpag` | P1 detalle REC; P0 usa `caja` + `resumen_venta_cv` |

---

## Approach técnico

1. **`tesoreria_metrics.py`:** funciones `fetch_tesoreria_resumen(cursor, filters)` copiando fragmentos de `query_runner` sin invocar POST query.
2. **`ventas_cobros_metrics.py`:** queries a `resumen_venta_cv` + fallback `cuentacliente`; query agregada `caja` con `_get_payment_method`.
3. **`command_center.py`:** registrar áreas y `ENDPOINTS_RELATIVOS`.
4. **UI:** tarjeta «Tesorería (caja)» con subfilas ventas/cobranzas/proveedores; tarjeta «Ventas por cobro» con dos bloques; sin tarjeta impuestos.
5. **Permisos:** `ManagerialReportsPermission` sin cambio.

---

## Riesgos

| Riesgo | Mitigación |
|--------|------------|
| Usuario espera “banco” en P0 | `banco_disponible: false` + nota en UI |
| Saldo caja vs `caja_saldo` | Documentar en meta |
| Doble conteo si mezclan series venta | Etiquetas claras en UI |

---

## Success criteria

- [ ] `tesoreria/resumen` y `ventas/cobros/resumen` responden 200 con `executive-dashboard-v1`.
- [ ] Orquestador incluye `tesoreria` y `ventas_cobros`.
- [ ] UI sin bloque impuestos; tesorería muestra solo caja en P0.
- [ ] UAT: totales caja ≈ informe `cash_flow_waterfall` (± redondeo) en empresa piloto.
- [ ] Tests de contrato en contenedor.

---

## Próximo paso

**`sdd-apply`** según `tasks.md` en esta carpeta.
