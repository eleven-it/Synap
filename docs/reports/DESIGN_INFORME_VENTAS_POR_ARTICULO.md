# Diseño técnico: Informe «Ventas por artículo»

Especificación de producto: [`SPEC_INFORME_VENTAS_POR_ARTICULO.md`](SPEC_INFORME_VENTAS_POR_ARTICULO.md).

---

## Enfoque

Reutilizar el núcleo SQL de `run_ventas_objetivos_vs_bo` (facturación/unidades + detalle línea) con flag `solo_ventas_articulo` para slug `ventas-por-articulo`, y **rama de armado de árbol distinta** al final del runner. UI en módulo JS dedicado (no extender `objetivos_ventas_bo.js` con ramas vendedor).

---

## Decisiones

| Tema | Elección | Alternativa descartada | Motivo |
|------|----------|------------------------|--------|
| Runner | Flag + `_armar_arbol_ventas_por_articulo` en `ventas_objetivos_bo_runner.py` | Runner 100% nuevo | Misma SQL base y filtros VO; menos duplicación |
| JS | `ventas_por_articulo.js` nuevo | Fork masivo de `objetivos_ventas_bo.js` | Jerarquía distinta; VPV/VO intactos |
| SQL detalle | `GROUP BY id_art, cod_proveedor, id_cliente` | Reagrupar en Python desde árbol vendedor | Menos datos y rollups claros |
| Proveedor | `COALESCE(art.CodigoProveedor,0)` + `LEFT JOIN proveedor` | Solo código sin nombre | UX «Sin proveedor» |
| Listado clientes | Mantener consulta clientes con histórico (paridad VPV) | Solo clientes con venta en período | Consistencia con informe origen |

---

## Flujo de datos

```text
Filtros → run_ventas_objetivos_vs_bo (solo_ventas_periodo ∨ solo_ventas_articulo)
       → sql detalle (+ CodigoProveedor, proveedor.Nombre)
       → filas planas {id_art, cod_proveedor, id_cliente, uni, fac}
       → _nest_articulo_proveedor_cliente → jerarquia[]
       → JSON dashboard → ventas_por_articulo.js → tabla / export
```

### Contrato JSON (nodos)

```python
# Artículo (raíz)
{"tipo": "articulo", "id_art": int, "nombre_articulo": str,
 "cantidades_vendidas": float, "facturacion": float, "children": [...]}
# Proveedor
{"tipo": "proveedor", "codigo_proveedor": int, "nombre_proveedor": str, ...}
# Cliente (hoja)
{"tipo": "cliente", "codigo_cliente": int, "nombre_cliente": str, ...}
```

`codigo_proveedor == 0` → `nombre_proveedor == "Sin proveedor"`.

---

## Cambios por archivo

| Archivo | Acción |
|---------|--------|
| `reports/migrations/0032_add_ventas_por_articulo_report.py` | Crear `ReportDefinition` |
| `reports/services/ventas_objetivos_bo_runner.py` | SQL detalle art-prov-cli; flag slug; armado árbol |
| `reports/services/query_runner.py` | Slug, caché `vpa_v1`, dispatch |
| `reports/services/export_service.py` | Headers, nombre archivo, outline |
| `reports/services/catalog_service.py` | Slug en listados legacy |
| `reports/views.py` | Allowlist slug |
| `reports/urls.py` | Redirect corto |
| `reports/static/reports/js/ventas_por_articulo.js` | **Crear** renderer jerárquico |
| `reports/static/reports/js/dashboard.js` | Helpers slug, orden, realtime, loading |
| `reports/templates/reports/dashboard_detail.html` | Condiciones slug, script, columnas |
| `reports/templates/reports/includes/filters_*.html` | Incluir slug donde VPV |
| `reports/tests/test_ventas_por_articulo*.py` | Nest + export headers |
| `docs/reports/SPEC_*.md` | Este par de documentos |

---

## SQL detalle (delta sobre `sql_venta_por_art`)

Añadir en SELECT/GROUP BY:

- `COALESCE(art.CodigoProveedor, 0) AS codigo_proveedor`
- `COALESCE(MAX(prov.Nombre), '') AS nombre_proveedor` con `LEFT JOIN proveedor prov ON prov.Codigo = art.CodigoProveedor`
- Agrupar por `art.IDArt`, `art.CodigoProveedor`, `cc.Codigo` (sin rubro/subrubro en GROUP BY del informe artículo)

Filtros rubro/subrubro: mantener `vo_filtra_rubro` en WHERE (no en jerarquía).

---

## Ordenación

- Niveles: artículo, proveedor, cliente.
- Métricas: `facturacion_periodo` / `unidades_periodo` → campos `facturacion` / `cantidades_vendidas`.
- Desempate: nombre visible, luego id/código.

---

## Pruebas

| Capa | Qué |
|------|-----|
| Unit | `_nest_articulo_proveedor_cliente` rollups; Sin proveedor |
| Unit | Export `_resolve_export_headers` para slug |
| Integración | Suma por `id_art` vs VPV mismos filtros (mock DB o fixture) |

Ejecutar: `docker exec Synap_app python manage.py test reports.tests.test_ventas_por_articulo`.

---

## Migración / despliegue

1. Migración `0032` crea `ReportDefinition` global (`empresa=None`).
2. Deploy código + static.
3. Verificar catálogo y URL canónica.

Sin cambios MySQL legacy (solo lectura tablas existentes).

---

## Preguntas abiertas

Ninguna bloqueante; decisiones de producto cerradas en SDD explore.
