# Documento operativo: Presupuesto de ventas (`documento-presupuesto-ventas`)

Definición global en `reports.ReportDefinition` (migración `0032_add_documento_presupuesto_ventas_report`). Dataset y Excel comparten la misma lectura que las vistas Ventas (`comp_ped` tipo PRE, `stockp`, cliente en cabecera).

## Slug y categoría

| Campo | Valor |
|--------|--------|
| `slug` | `documento-presupuesto-ventas` |
| `category` | `operational` |
| `refresh_interval` | `realtime` |

## Payload

Ejemplo para `ExportService.export` o ejecución vía `QueryRunnerService.run`:

```json
{
  "filters": {
    "base_empresa": "nombre_base_mysql",
    "codigo_movimiento": 12345,
    "nro_comprobante_archivo": "PRE_0001"
  }
}
```

- **`base_empresa`** (obligatorio): base MySQL AdministraNET de la sesión.
- **`codigo_movimiento`** (obligatorio): `CodigoMovimiento` del PRE.
- **`nro_comprobante_archivo`** (opcional): fragmento sanitizado para el nombre del `.xlsx` (la vista de detalle lo rellena desde `comp_ped.NroComprobante`).

Si faltan base o movimiento, el runner devuelve metadatos vacíos y notas explicativas en español.

## Salidas

- **Excel:** generación dedicada en `reports/services/export_service.py` (`_generate_excel_documento_presupuesto_ventas`): cabecera en bloque superior y tabla de renglones con totales al pie.
- **PDF:** no implementado en la misma iteración; el slug queda estable para una plantilla posterior.

## Integración Ventas

- API lectura JSON (listado y detalle): ver **§9.6** en `docs/general/SPEC_PRESUPUESTO_VENTAS_SYNAP.md` (`/ventas/api/presupuestos/`, `/ventas/api/presupuestos/<codigo_movimiento>/`).
- Ruta **GET** (misma sesión que el detalle): `/ventas/presupuestos/<codigo_movimiento>/exportar-xlsx/`
- Permiso Synap: `ventas.presupuesto.ver`. Si el usuario tiene sucursal en sesión y el PRE es de otra sucursal, se rechaza la exportación (coherente con la vista de detalle).

## Referencias de código

- Runner: `reports/services/presupuesto_ventas_runner.py`
- Registro en `QueryRunnerService.run`: rama `documento-presupuesto-ventas`
- Lectura de datos: `ventas/services/presupuesto_mysql.py` (`obtener_presupuesto_cabecera`, `listar_lineas_presupuesto_stockp`)
