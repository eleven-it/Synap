# Verificación: Informe «Ventas por marca y SuperArt»

Fecha: 07/08/2026. Spec: [`SPEC_INFORME_VENTAS_MARCA_SUPERART.md`](SPEC_INFORME_VENTAS_MARCA_SUPERART.md).

---

## Matriz requisitos

| Req. | Criterio | Estado |
|------|----------|--------|
| R1 | Slug en catálogo / query_runner / seed 0036 | OK (código) |
| R2 | Nest Marca → SuperArt → Artículo + rollups | OK (tests unitarios) |
| R3 | Excel plano 6 columnas | OK (headers + path plano en export_service) |

---

## Tests

```bash
docker exec Synap_app python manage.py test reports.tests.test_ventas_marca_superart
```

Resultado 07/08/2026: **8/8 OK**.

Cobertura: nest/rollups, fallbacks Sin marca / Sin SuperArt, flatten, sort, headers export, filename.

---

## Smoke manual sugerido

1. Abrir `/reports/dashboard/ventas-marca-superart/`
2. Elegir período facturación y Actualizar
3. Expandir Marca → SuperArt → ver artículos con Packs/Docenas/Facturación
4. Exportar Excel y verificar columnas Marca | SuperArt | Articulo | Packs | Docenas | Facturacion
5. Filtrar por SuperArt y por marca (incluir) y confirmar filtrado
