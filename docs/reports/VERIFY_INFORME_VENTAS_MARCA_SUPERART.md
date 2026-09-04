# Verificación: Informe «Ventas por marca y SuperArt»

Fecha: 07/08/2026. Spec: [`SPEC_INFORME_VENTAS_MARCA_SUPERART.md`](SPEC_INFORME_VENTAS_MARCA_SUPERART.md).

---

## Matriz requisitos

| Req. | Criterio | Estado |
|------|----------|--------|
| R1 | Slug en catálogo / query_runner / seed 0036 | OK (código) |
| R2 | Nest Marca → SuperArt → Artículo + rollups | OK (tests unitarios) |
| R3 | Excel plano 6 columnas | OK (headers + path plano en export_service) |
| R4 | Facturación post-pie (paridad VMM) | OK (test SQL post-pie) |
| R5 | Fila «Ajustes sin mercadería» alinea con Ventas Netas | OK (nest/pin + runner mock) |

---

## Tests

```bash
docker exec Synap_app python manage.py test reports.tests.test_ventas_marca_superart
```

Resultado 07/08/2026: **8/8 OK** (nest/export). Tras alinear post-pie (03/09/2026): incluir test `VentasMarcaSuperartPostPieRunnerTest`. Tras fila de ajustes (03/09/2026): nest/pin y totales con cabecera sin mercadería.

Cobertura: nest/rollups, fallbacks Sin marca / Sin SuperArt, flatten, sort, headers export, filename, SQL post-pie, ajustes sin mercadería (pin, display, skip con filtro catálogo).

---

## Smoke manual sugerido

1. Abrir `/reports/dashboard/ventas-marca-superart/`
2. Elegir período facturación y Actualizar
3. Expandir Marca → SuperArt → ver artículos con Packs/Docenas/Facturación
6. Si hay FA/NC de cabecera sin mercadería, aparece al pie la fila **Ajustes sin mercadería**; expandir para ver clientes.
7. Exportar Excel y verificar columnas Marca | SuperArt | Articulo | Packs | Docenas | Facturacion (los ajustes salen con marca «Ajustes sin mercadería» y artículo = cliente)
8. Filtrar por SuperArt o marca (incluir) y confirmar que la fila de ajustes **no** aparece
