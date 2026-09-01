# 24 — Testing Assessment

**Estado:** COMPLETE (Fase 24)  
**Fecha:** 25/08/2026

---

## Resumen

| Métrica | Valor |
|---------|------:|
| Archivos test_*.py | ~380 |
| Management commands | ~160 |
| Framework | Django TestCase + pytest |
| Ejecución | Docker `Synap_app` |

---

## Cobertura estimada por módulo

| Módulo | Tests | Coverage est. | Critical paths | Risk |
|--------|------:|:-------------:|:--------------:|:----:|
| ecom | 80 | Media-Alta | Pedidos, crédito, relays | Medio |
| mpr | 73 | Media-Alta | Partes, armado, tablero | Medio |
| reports | 38 | Media | Query runner, dashboards | **Alto** |
| factura_compra_captura | 36 | Media-Alta | OCR, expediente, posting | Medio |
| core | 27 | Media | Permisos, backup, pool | **Alto** |
| tiendanube | 27 | Media | Sync, webhooks, mappings | Medio |
| stock | 19 | Media | Inventario, movimientos | Medio |
| contabilidad_audit | 7 | Baja-Media | Checks lectura | Medio |
| legacy_db | 6 | Baja | Repositorios | **Alto** |
| odoo_migracion | 6 | Baja | Migration jobs | Bajo |
| ventas | 4 | Baja | Objetivos | Medio |
| logistica | 4 | Baja | Entregas | Medio |
| ia | 3 | Baja | LLM gateway | Medio |
| self_checkout | 3 | **Muy baja** | TPV venta, caja | **Alto** |
| login | 1 | **Muy baja** | Auth flow | **Alto** |
| fe_afip | 0 | **Ninguna** | Facturación AFIP | **Alto** |
| compras | 0 | **Ninguna** | Remitos | **Alto** |
| dashboard | 0 | N/A | Legacy stub | Bajo |

---

## Gaps críticos

1. **fe_afip** — sin tests; facturación electrónica es crítica
2. **self_checkout** — 3 tests para TPV completo
3. **login** — 1 test para auth de todo el sistema
4. **compras** — 0 tests
5. **Sin E2E** automatizados detectados
6. **Sin integration tests** MySQL reales en CI (mayoría mock/fixture)
7. **query_runner** — tests parciales, no cubren SQL dinámico

---

## Fixtures y patrones

- `ecom/tests/conftest.py` — fixtures MySQL
- `stock/tests/` — CACHES override en tests
- Tests usan `django.test.TestCase` predominantemente
- `pytest.ini` presente pero Django test runner dominante

---

*Generado por auditoría READ ONLY.*
