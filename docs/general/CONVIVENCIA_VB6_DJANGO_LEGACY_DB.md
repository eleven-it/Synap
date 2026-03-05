# Convivencia VB6 + Django y capa Legacy-Compatible Write Layer

## Objetivo

Mantener **VB6 y Django operativos** sobre la misma base MySQL 5.7 (administraNET), sin romper schema ni semántica. Toda escritura de Django en tablas compartidas pasa por la app **`legacy_db`** (repositories + services) para garantizar paridad con VB6.

## Invariantes que no se rompen

- **Mismas tablas y columnas:** sin renombrar ni cambiar tipos.
- **Mismos valores de negocio:** tipos comprobante FA/FB/FC/FM/NC/ND/OP, estados, anulaciones.
- **Misma lógica** de numeración, estados, saldos e imputaciones.
- **Misma unidad de confirmación:** lo que VB6 considera "Guardado OK", Django debe hacerlo igual (mismo conjunto de writes en el mismo orden).

## Qué sí se mejora (sin cambiar el guardado)

- Parametrización de consultas (cero SQL concatenado).
- Transacciones atómicas por "Confirmar comprobante" (commit/rollback).
- Auditoría y trazabilidad (logs, correlación).
- UX: búsquedas con debounce, paginación real, errores tipados (CAI_VENCIDO, OP_BLOQUEADA, etc.), drafts fuera de tablas legacy.

## Estructura de `legacy_db`

| Componente | Uso |
|------------|-----|
| **models_legacy.py** | Modelos Django `managed=False` para referencia de schema (proveedor, contribuyentes, sucursales, op_factura, fact_temporalp, descuento_op_nc). Las escrituras se hacen por repositories con SQL parametrizado. |
| **repositories.py** | Único punto de lectura/escritura parametrizada: proveedores, sucursales, fact_temporalp (lock OP), op_factura, descuento_op_nc. Usan `core.utils.administranet_types`. |
| **validators.py** | Reglas idénticas a VB6: CAI vigente, obliga_oc_carga_comp, tipo FA/FB/FC según IDIVA. |
| **mappers.py** | DTO ⇄ filas legacy con normalización de tipos. |
| **services/** | Orquestación: orden_pago_service (open/close lock, confirmar OP), factura_compra_service, imputaciones_service. Cada "Confirmar" = una transacción. |

## Concurrencia y locks

- **fact_temporalp:** Django respeta y escribe igual que VB6. `acquire_lock_op_proveedor` al abrir OP, `release_lock_op_proveedor` al cerrar/cancelar. Ver [legacy_db/repositories.py](../../legacy_db/repositories.py).
- **Numeradores:** Si VB6 usa tabla o SP, Django debe usar lo mismo dentro de la transacción; si calcula a mano, replicar con `SELECT ... FOR UPDATE` donde aplique.
- **op_factura (saldos/estados):** No recalcular con lógica nueva; seguir la misma secuencia que VB6 (insertar → imputar → actualizar saldo/estado).

## Cambios seguros en DB durante convivencia

**Permitido:** índices nuevos, vistas (solo lectura), tablas nuevas que VB6 no toca (ej. `web_drafts`).

**Evitar por ahora:** cambiar tipos/longitudes, renombrar tablas o columnas, cambiar significado de estados/códigos, normalizaciones que alteren tablas compartidas.

## API hub (FORM-001)

- `GET /api/legacy-hub/proveedores/` — Listado/búsqueda parametrizada, paginación COUNT(*), order_by whitelist.
- `GET /api/legacy-hub/sucursales/` — Listado sucursales.
- `GET /api/legacy-hub/precheck/?accion=keyFact&codigo_proveedor=...` — Precheck antes de abrir acción (devuelve códigos CAI_VENCIDO, REQUIERE_OC, OP_BLOQUEADA, etc.).
- `GET /api/legacy-hub/op-lock-info/?codigo_proveedor=...` — Información de bloqueo OP ("en uso por usuario X").

## UI hub en Synap (menú Compras y Stock)

La pantalla **Facturas de Compra / NC / ND / Orden de Pago** (paridad CargaComprobantesP) está en:
- **Compras** (barra superior) → Facturas de Compra / NC / ND / Orden de Pago (y Remito de Compra).
- **Stock** → Comprobantes de compra → Facturas de Compra / NC / ND / Orden de Pago.

El menú **Compras** es un módulo core (no requiere activación en Module Management); el usuario debe tener permiso **compras.ver**. Usa los mismos repositories y validadores que la API; al elegir acción se ejecuta el precheck y se redirige al formulario (Factura, OP, NC, ND, Cta Cte, Imputación, Desimputación). Los formularios de comprobante se implementan por fases; la escritura en tablas legacy se hará siempre vía `legacy_db`. Ver [MIGRACION_HUB_COMPROBANTES_STOCK.md](MIGRACION_HUB_COMPROBANTES_STOCK.md) y [MANUAL_USUARIO_COMPRAS.md](MANUAL_USUARIO_COMPRAS.md).

## Checklist de compatibilidad por comprobante

Antes de dar por OK un módulo Django que escribe comprobantes:

1. ¿Inserta/actualiza exactamente las mismas tablas que VB6?
2. ¿En el mismo orden lógico (cabecera → detalle → numeración → op_factura/saldos)?
3. ¿Mismos defaults y valores vacío/cero (vía `administranet_types`)?
4. ¿Respeta numeradores y estados (sin nuevos códigos)?
5. ¿Impacta igual en op_factura (saldo, estado, anulado)?
6. ¿El comprobante queda visible y consistente al abrirlo desde VB6 justo después de guardar desde Django?

Fichas por comprobante: ver `docs/general/COMPAT_LEGACY_*.md` (crear por cada tipo al implementar escritura completa).

## Referencias

- Plan: Dual-run y Legacy-Compatible Write Layer (cursor/plans).
- Inventario ingeniería inversa hub: [INVENTARIO_INGENIERIA_INVERSA_CARGA_COMPROBANTES_P.md](INVENTARIO_INGENIERIA_INVERSA_CARGA_COMPROBANTES_P.md).
- Tipos de datos: [TIPOS_DATOS_ADMINISTRANET.md](TIPOS_DATOS_ADMINISTRANET.md).
