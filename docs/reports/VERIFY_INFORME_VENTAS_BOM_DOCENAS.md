# Verificación: Ventas BOM en docenas

## Tests automatizados

```bash
docker exec Synap_app python manage.py test reports.tests.test_ventas_bom_docenas
```

Cobertura: explosión `qty × cantidad_articulo`, signos FA/NC, packs sin BOM omitidos, docenas ÷12, filename Excel, defaults del seed.

## Checklist UI

1. Abrir `/reports/dashboard/ventas-bom-docenas/` (o atajo `/reports/ventas-bom-docenas/`).
2. Ver título, filtros de período / sucursal / PV / clientes a excluir.
3. Actualizar: KPIs docenas / pares / artículos BOM + tabla plana.
4. Exportar Excel: nombre `Ventas_BOM_docenas_ddMMyyyy_ddMMyyyy.xlsx`, columnas Código BOM, Artículo BOM, Marca, Pares, Docenas, bloque filtros.

## SQL piloto (MySQL `base_empresa`)

```sql
-- Packs vendidos con BOM en un período
SELECT art.IDArt, art.CodigoArticuloT, art.id_en_abm, SUM(st.Cantidad) AS packs
FROM stock st
JOIN cuentacliente cc ON cc.CodigoMovimiento = st.CodigoMovimiento
JOIN articulo art ON art.IDArt = st.IDArt
WHERE cc.Fecha BETWEEN '2026-03-01' AND '2026-03-31'
  AND cc.Anulado = 'No'
  AND cc.TipoComprobante IN ('FA','FB','FC','FE','FM')
  AND st.Anulado = 'No'
  AND COALESCE(st.visualiza_ensamble,'No') = 'No'
  AND art.id_en_abm IS NOT NULL AND art.id_en_abm <> 0
GROUP BY art.IDArt, art.CodigoArticuloT, art.id_en_abm
ORDER BY packs DESC
LIMIT 10;

-- Receta de un pack piloto
SELECT f.id_articulo, a.CodigoArticuloT, a.NombreArticulo, f.cantidad_articulo, ab.descuenta_en
FROM en_abm_formula f
JOIN articulo a ON a.IDArt = f.id_articulo
JOIN en_abm ab ON ab.id_en_abm = f.id_en_abm
WHERE f.id_en_abm = /* id_en_abm del pack */
  AND COALESCE(f.anulado,'No') <> 'Si';
```

Conciliar: `docenas_informe ≈ (packs_FA - packs_NC) × cantidad_articulo / 12` para 2–3 SKU.
