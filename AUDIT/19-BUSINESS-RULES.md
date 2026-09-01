# 19 — Reglas de Negocio Distribuidas

**Estado:** COMPLETE (Fase 19)  
**Fecha:** 25/08/2026

---

## Reglas por ubicación

### Models (PostgreSQL)

| Regla | Ubicación | Dominio |
|-------|-----------|---------|
| Validación expediente compra | factura_compra_captura/models/ | Compras |
| Estados agente IA | ia/models.py (choices) | IA |
| Versionado reportes | reports/models.py | Reportes |
| Políticas auditoría contable | contabilidad_audit/models.py | Contabilidad |

### Services (principal)

| Regla | Ubicación | Duplicada en |
|-------|-----------|:------------:|
| Validación stock disponible | core/administranet_stock.py | mpr/services.py, stock/ |
| Numeración talonarios | self_checkout/, mpr/services.py | core/administranet_stock.py | **Sí** |
| Cálculo backorder | reports/query_runner.py | — | No |
| Aprobación crédito pedidos | ecom/services/aprobacion_pedidos.py | — | No |
| Imputación contable | legacy_db/cont_recalculo_service.py | VB6 | **Sí** |
| Validación CAE/CAEA | fe_afip/services/ | VB6 FE | Parcial |
| Permisos por puesto | core/administranet_permisos_usuario.py | VB6 | **Sí** |
| Cotización BCRA | core/cotizacion_bcra | — | No |
| BOM artículos ensamblados | mpr/services.py | VB6 | Parcial |

### SQL directo

| Regla | Ubicación |
|-------|-----------|
| Formato fecha YYYYMMDD | reports/query_runner.py, mpr/ |
| Sí/No como string | Todos los módulos MySQL |
| Anulado = 'Si'/'No' | self_checkout, ecom, legacy_db |
| MAX(id)+1 para IDs | legacy_db (evita en puestos) |

### Templates/JS

| Regla | Ubicación | Riesgo |
|-------|-----------|--------|
| Cálculo totales carrito | ecom/js/compra_mayorista_*.mjs | Re-validar backend |
| Cálculo vuelto TPV | self_checkout/static/ | **Alto** |
| Formateo fechas display | Varios templates | Bajo |

### VB6 (referencia)

Reglas originales documentadas en `administranet_vb6/` y `docs/general/tablas/`. Synap replica subset.

---

## Reglas duplicadas (riesgo inconsistencia)

1. **Numeración talonarios** — self_checkout, mpr, core/administranet_stock
2. **Movimiento stock** — stock/, mpr/, core/administranet_stock
3. **Permisos** — permiso_sistema* vs synap_*
4. **Imputación contable** — legacy_db vs VB6
5. **Formato fechas** — INT YYYYMMDD vs DATE vs display

---

*Generado por auditoría READ ONLY.*
