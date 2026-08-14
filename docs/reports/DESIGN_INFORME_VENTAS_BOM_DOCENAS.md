# Diseño técnico: Informe «Ventas BOM en docenas»

Especificación de producto: [`SPEC_INFORME_VENTAS_BOM_DOCENAS.md`](SPEC_INFORME_VENTAS_BOM_DOCENAS.md).

---

## Enfoque

Runner dedicado `ventas_bom_docenas_runner.py`:

1. Consulta packs facturados (`stock` + `cuentacliente` + `articulo` pack).
2. Carga recetas `en_abm_formula` para los `id_en_abm` del período.
3. Explota en Python y agrega por componente.
4. Enriquece nombre/código/marca del componente.

UI: tabla genérica del dashboard + script ligero para KPIs y orden. Excel vía `ExportService` (hoja simple).

---

## Decisiones

| Tema | Elección | Alternativa descartada | Motivo |
|------|----------|------------------------|--------|
| Grano | Artículo BOM (componente) | Árbol pack→componente | Pedido de producto v1 |
| Docenas | pares / 12 | Factor comercial P1–P6 del pack | Protagonista = fabricado/planta |
| Líneas stock | `visualiza_ensamble = 'No'` | Incluir ensamble TPV | Evitar doble conteo |
| Explosión | Python post-query | JOIN SQL pack×formula | Claridad, reutilizable en tests |
| Métricas | pares + docenas | + facturación $ | Precio vive en el pack |

---

## Flujo de datos

```text
Filtros → SQL packs (IDArt pack, id_en_abm, qty_firmada)
       → bulk BOM (id_en_abm → [{id_articulo, cantidad_articulo}])
       → explode & aggregate por id_articulo componente
       → JOIN catálogo componente (código, nombre, marca)
       → QueryResult { data[], totals{pares, docenas, articulos_bom}, notes }
       → dashboard / Excel
```

### Contrato JSON (fila)

```python
{
  "id_art": int,
  "codigo_articulo": str,
  "nombre_articulo": str,
  "codigo_marca": int | None,
  "nombre_marca": str,
  "pares": float,
  "docenas": float,
}
```

---

## Archivos

| Archivo | Rol |
|---------|-----|
| `reports/services/ventas_bom_docenas_rules.py` | Constantes FA/NC, TipoComp, divisor 12 |
| `reports/services/ventas_bom_docenas_runner.py` | Query + explosión + agregado |
| `reports/services/ventas_bom_docenas_seed.py` | Seed / `ensure_*` |
| `reports/migrations/0031_add_ventas_bom_docenas_report.py` | Data migration |
| `reports/services/query_runner.py` | Dispatch slug + caché `vbd_v1` |
| `reports/services/export_service.py` | Filename, headers, números |
| `reports/views.py` | `ensure_*` al abrir dashboard |
| `reports/urls.py` | Atajo corto |
| `reports/templates/reports/dashboard_detail.html` | Export + filtros + contenedor |
| `reports/static/reports/js/dashboard.js` | Familia filtros/export + labels tabla |
| `reports/static/reports/js/ventas_bom_docenas.js` | KPIs / orden local |
| `reports/tests/test_ventas_bom_docenas.py` | Unit tests explosión y headers |

---

## Fórmula

```text
signo = +1 (FA*) | -1 (NC*)
pares[comp] += signo * Cantidad_pack * cantidad_articulo
docenas[comp] = round(pares[comp] / 12, 2)
```

---

## Rollback

Ver SPEC §8.
