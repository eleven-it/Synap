# Diagnóstico: comp_ped no incluido en el reporte BO (Backorder)

## Cuándo un comprobante SÍ entra en el Backorder

El reporte **BO vs Stock vs Facturación** (`bo-stock-facturacion`) incluye un pedido en el Backorder **solo si se cumplen todas** estas condiciones (ver `reports/services/query_runner.py`, `_run_backorder_vs_stock_vs_facturacion`):

| # | Condición | Tabla / campo |
|---|-----------|----------------|
| 1 | Existen renglones en `stockp` con el mismo `CodigoMovimiento` que el pedido | `stockp.CodigoMovimiento = comp_ped.CodigoMovimiento` |
| 2 | Tipo comprobante es PED | `comp_ped.TipoComprobante = 'PED'` |
| 3 | Estado del pedido es **Pendiente** | `comp_ped.Estado IN ('Pendiente')` |
| 4 | Pedido no anulado | `comp_ped.Anulado = 'No'` |
| 5 | Renglones no anulados | `stockp.anulado IS NULL OR stockp.anulado = 'No'` |
| 6 | Comprobante en stockp coherente | `stockp.Comprobante = 'PED' OR stockp.Comprobante IS NULL` |
| 7 | **Fecha del renglón dentro del rango del reporte** | `stockp.Fecha >= fecha_inicio_bo AND stockp.Fecha <= fecha_fin_bo` |
| 8 | Artículo no es tipo Gasto | `articulo.tipo_art IS NULL OR articulo.tipo_art <> 'Gasto'` |
| 9 | Cliente no está en la lista de exclusión | (si aplica filtro de clientes) |

**Importante:** El reporte arma el BO desde **stockp** (renglones) y hace `INNER JOIN comp_ped`. Si no hay filas en `stockp` para ese `CodigoMovimiento`, o si todas quedan fuera por estado/fecha/artículo, el comprobante no aparece.

---

## Motivos habituales por los que un comprobante NO aparece

1. **Estado distinto de "Pendiente"**  
   Si el pedido está en "En preparación", "Preparado" o "Parcial", entra en **Reservado**, no en Backorder. El BO solo considera `Estado = 'Pendiente'`.

2. **Fecha de los renglones fuera del rango**  
   Se filtra por `stockp.Fecha` en el intervalo elegido (fecha inicio/fin del reporte). Si los renglones tienen otra fecha, no se suman al BO.

3. **Sin renglones en stockp**  
   Si el pedido no tiene filas en `stockp` con ese `CodigoMovimiento`, el `INNER JOIN` lo deja fuera.

4. **Pedido o renglones anulados**  
   `comp_ped.Anulado <> 'No'` o `stockp.anulado` distinto de NULL/'No'.

5. **Solo artículos tipo Gasto**  
   Los renglones con `articulo.tipo_art = 'Gasto'` se excluyen; si todos los renglones del comprobante son Gasto, no aporta al BO.

6. **Cliente excluido**  
   Si el reporte se ejecuta con filtro de clientes y este cliente está en la lista de exclusión.

7. **Base de datos o servidor distinto**  
   El reporte BO usa **siempre** la conexión MySQL definida en la aplicación (`.env`: `DB_HOST`, `DB_PORT`, `DB_NAME`) y el nombre de base `base_empresa` (selector en la UI, usuario o `DEFAULT_BASE_EMPRESA`). Si los comprobantes existen en **otra base** o en **otro servidor** (por ejemplo la base que probaste en otro host/puerto), no aparecerán mientras la app esté apuntando a otro `DB_HOST`/base. **Comprobar:** en las notas del reporte se indica "Base de datos utilizada: …"; debe coincidir con la base donde existen los pedidos. En la respuesta del API, `meta.extra.base_empresa_used` también indica la base usada.

---

## Consulta de diagnóstico para un comprobante

Para analizar por qué **`comp_ped.nrocomprobante = '0001-00010474'`** no se tiene en cuenta en el BO, ejecutar en la base de la empresa (por ejemplo `administranet`):

```sql
-- 1) Cabecera comp_ped
SELECT
    cp.CodigoMovimiento,
    cp.NroComprobante,
    cp.Fecha          AS cp_fecha,
    cp.TipoComprobante,
    cp.Estado         AS cp_estado,
    cp.Anulado        AS cp_anulado,
    cp.Codigo         AS id_cliente
FROM comp_ped cp
WHERE cp.NroComprobante = '0001-00010474';

-- 2) Renglones stockp de ese comprobante (usar CodigoMovimiento del resultado anterior)
SELECT
    sp.id_stock,
    sp.CodigoMovimiento,
    sp.Fecha          AS sp_fecha,
    sp.Comprobante    AS sp_comprobante,
    sp.anulado        AS sp_anulado,
    sp.IDArt,
    sp.Cantidad,
    sp.PrecioNetoxR,
    a.id_manual       AS codigo_articulo,
    a.tipo_art
FROM stockp sp
LEFT JOIN articulo a ON a.IDArt = sp.IDArt
WHERE sp.CodigoMovimiento = (
    SELECT CodigoMovimiento FROM comp_ped WHERE NroComprobante = '0001-00010474' LIMIT 1
);

-- 3) ¿Cumple todas las condiciones del BO? (reemplazar FECHA_INICIO y FECHA_FIN por el rango del reporte, formato YYYYMMDD o YYYY-MM-DD según el tipo de columna Fecha)
-- Si stockp.Fecha es INT (YYYYMMDD):
--   SET @fecha_inicio = 20250301;
--   SET @fecha_fin   = 20250331;
-- Si stockp.Fecha es DATE:
--   SET @fecha_inicio = '2025-03-01';
--   SET @fecha_fin   = '2025-03-31';
SELECT
    cp.NroComprobante,
    cp.Estado         AS cp_estado,
    cp.Anulado        AS cp_anulado,
    cp.TipoComprobante,
    sp.Fecha          AS sp_fecha,
    sp.CodigoMovimiento IS NOT NULL AS tiene_renglones,
    (sp.anulado IS NULL OR sp.anulado = 'No')       AS renglon_no_anulado,
    (a.IDArt IS NULL OR a.tipo_art IS NULL OR a.tipo_art <> 'Gasto') AS articulo_no_gasto
FROM comp_ped cp
INNER JOIN stockp sp ON sp.CodigoMovimiento = cp.CodigoMovimiento
LEFT JOIN articulo a ON a.IDArt = sp.IDArt
WHERE cp.NroComprobante = '0001-00010474';
```

Interpretación rápida:

- Si **no hay filas** en (1): no existe ese `NroComprobante` en `comp_ped`.
- Si (1) tiene fila pero (2) **no devuelve filas**: el pedido no tiene renglones en `stockp` → no puede entrar al BO.
- Si en (1) **`Estado` no es 'Pendiente'**: por diseño del reporte, ese estado no se considera Backorder (sí Reservado si es En preparación/Preparado).
- Si en (2) **`sp.Fecha`** está fuera del rango con el que se ejecutó el reporte: ese comprobante queda fuera del período y no se incluye en el BO.
- Si en (2) todos los artículos tienen **`tipo_art = 'Gasto'`**: se excluyen del BO.

---

## Diagnóstico por lote (varios comprobantes)

Para revisar de una vez varios comprobantes que no aparecen en el BO (por ejemplo 0001-00010474, 0001-00010076, 0001-00010603, 0001-00010604), usar:

```sql
-- Cabecera: estado, anulado, tipo y si tiene renglones en stockp
SELECT
    cp.NroComprobante,
    cp.CodigoMovimiento,
    cp.Fecha          AS cp_fecha,
    cp.TipoComprobante,
    cp.Estado         AS cp_estado,
    cp.Anulado        AS cp_anulado,
    cp.Codigo         AS id_cliente,
    (SELECT COUNT(*) FROM stockp sp WHERE sp.CodigoMovimiento = cp.CodigoMovimiento) AS num_renglones_stockp
FROM comp_ped cp
WHERE cp.NroComprobante IN (
    '0001-00010474',
    '0001-00010076',
    '0001-00010603',
    '0001-00010604'
)
ORDER BY cp.NroComprobante;

-- Detalle por renglón: fechas en stockp y tipo de artículo (para ver si entran en el rango del reporte y si son Gasto)
SELECT
    cp.NroComprobante,
    cp.Estado         AS cp_estado,
    sp.Fecha         AS sp_fecha,
    sp.Comprobante   AS sp_comprobante,
    sp.anulado       AS sp_anulado,
    a.id_manual      AS codigo_articulo,
    a.tipo_art       AS tipo_art,
    sp.Cantidad,
    -- ¿Cumple condiciones BO?
    CASE WHEN cp.Estado = 'Pendiente' THEN 'Sí' ELSE 'No (BO solo Pendiente)' END AS estado_ok_bo,
    CASE WHEN (a.IDArt IS NULL OR a.tipo_art IS NULL OR a.tipo_art <> 'Gasto') THEN 'Sí' ELSE 'No (excl. Gasto)' END AS articulo_ok_bo
FROM comp_ped cp
INNER JOIN stockp sp ON sp.CodigoMovimiento = cp.CodigoMovimiento
LEFT JOIN articulo a ON a.IDArt = sp.IDArt
WHERE cp.NroComprobante IN (
    '0001-00010474',
    '0001-00010076',
    '0001-00010603',
    '0001-00010604'
)
ORDER BY cp.NroComprobante, sp.Fecha, sp.id_stock;
```

Para ejecutar el diagnóstico con datos reales desde el proyecto (usa la base MySQL configurada en `DB_NAME` o `--database`):

```bash
docker exec Synap_app python manage.py diagnostico_bo_comprobantes
# Con otra base (la misma con la que ejecutás el reporte BO):
docker exec Synap_app python manage.py diagnostico_bo_comprobantes --database administranet92
# Con otros comprobantes:
docker exec Synap_app python manage.py diagnostico_bo_comprobantes --comprobantes 0001-00010474 0001-00010500
# MySQL en otro servidor / host (ej. localhost:3307): pasar variables de conexión (desde host use host.docker.internal):
docker exec -e DB_NAME=administranet -e DB_USER=administranet -e DB_PASSWORD=administranet_local -e DB_HOST=host.docker.internal -e DB_PORT=3307 Synap_app python manage.py diagnostico_bo_comprobantes
```

Interpretación del lote:

- **Ningún comprobante encontrado** → Esos `NroComprobante` no existen en `comp_ped` en esa base. Si el reporte BO lo ejecutás con otra base (selector de empresa), usá `--database <nombre_base>`.
- **num_renglones_stockp = 0** → ese comprobante no puede aparecer en el BO (no tiene renglones).

### Causa determinada (base administranet, comprobantes 0001-00010474, 0001-00010076, 0001-00010603, 0001-00010604)

Ejecutando el diagnóstico contra la base **administranet** (host.docker.internal:3307) se comprobó:

- Los cuatro comprobantes **existen** en `comp_ped`, con **Estado = Pendiente**, no anulados y con renglones en `stockp`.
- Todos los renglones cumplen **estado_ok_bo** y **articulo_ok_bo** (no son Gasto).
- **Fechas en stockp:** 0001-00010474 → 2026-02-10; 0001-00010076 → 2026-02-13; 0001-00010603 y 0001-00010604 → 2026-02-27.

En esa base los comprobantes cumplen todas las condiciones (Estado Pendiente, renglones en stockp, no Gasto). Por tanto, si **en la interfaz** no se muestran, las causas probables son:

1. **Base o servidor distinto al ejecutar el reporte en el navegador:** la app usa la conexión MySQL del `.env` (ej. `DB_HOST=190.15.214.142`, `DB_NAME=administranet89`). Si los comprobantes están en **otra base/servidor** (ej. `administranet` en `host.docker.internal:3307`), el reporte en la UI no los incluirá. **Qué hacer:** revisar en las notas del reporte la línea "Base de datos utilizada: …" y asegurarse de que sea la misma base donde existen los pedidos; si no, configurar `DB_HOST`/`DB_NAME` (o el selector de base empresa) para esa conexión.
2. **Rango de fechas:** si el período del reporte no incluye las fechas de los renglones (ej. 2026-02-10, 2026-02-13, 2026-02-27), quedan fuera. Ejecutar el reporte con un rango que las incluya.
3. **Clientes excluidos:** si el cliente de ese pedido está en "Clientes a excluir", el comprobante se filtra. Revisar que no esté en la lista.
- **cp_estado** distinto de `'Pendiente'` → el reporte no lo cuenta como Backorder (sí como Reservado si es En preparación/Preparado).
- **sp_fecha** fuera del rango de fechas del reporte → queda fuera del período del BO.
- **articulo_ok_bo = 'No (excl. Gasto)'** en todos los renglones → el comprobante no aporta al BO.

---

## Referencia en código

- Filtro BO (detalle y row-level): `reports/services/query_runner.py` líneas 3209–3268 (`sql_bo_detalle`) y 3623–3645 (`sql_bo_rows`).
- Estados BO: `bo_estados = "('Pendiente')"` (línea 3193).
- Fechas: `parse_fecha_bo_yyyymmdd` (líneas 26–43); ambas consultas usan las mismas `fecha_inicio_bo`, `fecha_fin_bo`.
