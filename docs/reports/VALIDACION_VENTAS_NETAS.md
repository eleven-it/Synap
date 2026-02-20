# Validación Ventas Netas – Datos y consultas

Revisión del reporte **Ventas Netas** (`ventas_netas`) frente a `CONTEXTO_TABLAS_VB6_INFORMES.md` y formularios VB6 (Exportacion, Lista_Pedidos_OPT, FacturaA/B, ConsultaComprobante, etc.).

---

## 1. Resumen del reporte

| Aspecto | Valor |
|--------|--------|
| **Slug** | `ventas_netas` |
| **Nombre** | Ventas Netas |
| **Descripción** | Ventas netas = Ventas (FA,FB,FC,FE,FM) − Notas de crédito (NCA–NCM), sin impuestos. Agrupado por mes, sucursal y punto de venta. |
| **Tabla principal** | `cuentacliente` |
| **Joins** | `sucursales` (s.id_sucursal = cc.CodSucursal), `punto_venta` (pv.id_punto_venta = cc.id_pv) |
| **Filtros** | `fecha_inicio`, `fecha_fin` (o día/mes/año actual), `base_empresa`, `punto_venta` (multi), `sucursales` (multi) |
| **Métricas** | `ventas_brutas`, `notas_credito`, `ventas_netas` (todas vía `SubtotalDesc`) |

---

## 2. Consulta actual (estructura)

```sql
SELECT
    DATE_FORMAT(cc.Fecha, '%Y-%m') AS mes,
    DATE_FORMAT(cc.Fecha, '%m/%Y') AS mes_formato,
    cc.CodSucursal AS id_sucursal,
    COALESCE(s.nombre_sucursal, 'Sin Sucursal') AS nombre_sucursal,
    cc.id_pv AS id_punto_venta,
    COALESCE(CAST(pv.nro_punto_venta AS CHAR), CAST(cc.id_pv AS CHAR), 'Sin PV') AS nro_punto_venta,
    SUM(CASE WHEN cc.TipoComprobante IN ('FA','FB','FC','FE','FM') THEN COALESCE(cc.SubtotalDesc, 0) ELSE 0 END) AS ventas_brutas,
    SUM(CASE WHEN cc.TipoComprobante IN ('NCA','NCB','NCC','NCE','NCM') THEN COALESCE(cc.SubtotalDesc, 0) ELSE 0 END) AS notas_credito,
    SUM(CASE
        WHEN cc.TipoComprobante IN ('FA','FB','FC','FE','FM') THEN COALESCE(cc.SubtotalDesc, 0)
        WHEN cc.TipoComprobante IN ('NCA','NCB','NCC','NCE','NCM') THEN -COALESCE(cc.SubtotalDesc, 0)
        ELSE 0
    END) AS ventas_netas
FROM cuentacliente cc
LEFT JOIN sucursales s ON s.id_sucursal = cc.CodSucursal
LEFT JOIN punto_venta pv ON pv.id_punto_venta = cc.id_pv
WHERE cc.Fecha >= %s
  AND cc.Fecha <= %s
  AND cc.Anulado = 'No'
  AND cc.CodigoMovimiento <> 0
  AND cc.TipoComprobante IN ('FA','FB','FC','FE','FM','NCA','NCB','NCC','NCE','NCM')
  -- + filtros opcionales: cc.id_pv IN (...), cc.CodSucursal IN (...)
GROUP BY DATE_FORMAT(cc.Fecha,'%Y-%m'), cc.CodSucursal, s.nombre_sucursal, cc.id_pv, pv.nro_punto_venta
ORDER BY mes DESC, nombre_sucursal, nro_punto_venta
```

---

## 3. Contexto VB6 relevante

### 3.1 Tabla `cuentacliente`

- **Uso**: Movimientos de cuenta cliente: facturas (FA, FB, FC, FE, FM), notas de crédito (NCA, NCB, NCC, NCE, NCM), notas de débito (NDA, NDB, etc.), remitos, etc.
- **Formularios**: Exportacion, Lista_Pedidos_OPT, ConsultaComprobante, FacturaA/B, informes de ventas/IVA/percepciones.
- **Campos relevantes**: `Fecha`, `TipoComprobante`, `Anulado`, `SubtotalDesc`, `ImporteVenta`, `CodigoMovimiento`, `Codigo` (cliente), `CodSucursal`, `id_pv`, `NroCompBusq`, etc.

### 3.2 Tipos de comprobante (ventas vs. notas de crédito)

En VB6, para facturación y ventas:

- **Ventas (facturas)**: `FA`, `FB`, `FC`, `FE`, `FM` — coinciden con el reporte.
- **Notas de crédito**: `NCA`, `NCB`, `NCC`, `NCE`, `NCM` (también `NCT` en algunos mapeos de AFIP). El reporte usa NCA–NCM; NCT no se incluye.
- **Notas de débito** (`NDA`, `NDB`, `NDC`, `NDE`): En Exportacion aparecen en queries de percepciones y afines. Son ajustes positivos (a favor del vendedor). El reporte **no** las incluye: solo FA–FM y NCA–NCM.

### 3.3 Valor: SubtotalDesc vs. ImporteVenta

- **SubtotalDesc**: Subtotal con descuentos, sin impuestos. Se usa en Exportacion, Lista_Pedidos_OPT (ventas), informes IVA, etc.
- **ImporteVenta**: En algunos listados se muestra como alternativa. Exportacion usa `SubtotalDesc` con fallback a `ImporteVenta` para monto de operación y percepción.

El reporte usa solo `COALESCE(cc.SubtotalDesc, 0)`. No hay fallback a `ImporteVenta`.

### 3.4 Anulados y CodigoMovimiento

- **Anulado = 'No'**: Criterio estándar en VB6 para excluir anulados.
- **CodigoMovimiento <> 0**: El reporte excluye filas con `CodigoMovimiento = 0`. En VB6 no se observa un filtro equivalente explícito en las consultas de ventas revisadas; suele usarse para dejar fuera movimientos “virtuales” o de sistema. Conviene validar en base si existen filas con `CodigoMovimiento = 0` y si deben quedar fuera de ventas.

### 3.5 Sucursal y punto de venta

- **cuentacliente**: `CodSucursal` → `sucursales.id_sucursal`, `id_pv` → `punto_venta.id_punto_venta`. El reporte hace `LEFT JOIN` a ambas y aplica filtros opcionales por `CodSucursal` e `id_pv`. Coherente con VB6.
- **punto_venta.cont = 'Si'**: En Exportacion, varios informes de facturación/ventas filtran por `punto_venta.cont = 'Si'` (solo puntos de venta “contribuyentes”). El reporte **no** aplica este filtro; incluye todos los PV, sin distinguir por `cont`.

### 3.6 Filtro por fecha

Se filtra por `cc.Fecha` en `[fecha_inicio, fecha_fin]`. Mismo criterio que en VB6 para informes por período. Correcto.

---

## 4. Validación campo a campo

| Campo / aspecto | Origen | VB6 / cuentacliente | Conclusión |
|-----------------|--------|----------------------|------------|
| **mes / mes_formato** | `cc.Fecha` | Fecha del movimiento | Correcto. |
| **id_sucursal, nombre_sucursal** | `cc.CodSucursal`, `sucursales` | CodSucursal, JOIN sucursales | Correcto. |
| **id_punto_venta, nro_punto_venta** | `cc.id_pv`, `punto_venta` | id_pv, JOIN punto_venta | Correcto. |
| **ventas_brutas** | `SUM` FA–FM de `SubtotalDesc` | Facturas, SubtotalDesc | Correcto. |
| **notas_credito** | `SUM` NCA–NCM de `SubtotalDesc` | NC, SubtotalDesc | Correcto. |
| **ventas_netas** | ventas_brutas − notas_credito | Mismo concepto | Correcto. |
| **Anulado = 'No'** | WHERE | Estándar en VB6 | Correcto. |
| **CodigoMovimiento <> 0** | WHERE | No usado en VB6 para ventas; posible exclusión de mov. virtuales | Validar en base si aplica. |
| **TipoComprobante IN (FA…NCM)** | WHERE + CASE | FA–FM y NCA–NCM; sin ND*, sin NCT | Correcto para definición actual; ver §5. |

---

## 5. Consistencia con otros reportes

| Reporte | Ventas netas | Tipos | Tabla | Notas |
|--------|----------------|-------|-------|-------|
| **Sales summary** (KPI Ventas Netas) | FA–FM − NCA–NCM, `SubtotalDesc` | Mismos | `cuentacliente` | Misma definición. No usa `CodigoMovimiento <> 0`. |
| **BO – Facturación** | FA–FM − NCA–NCM, `SubtotalDesc` | Mismos | `cuentacliente` | Sin filtro CodigoMovimiento. |
| **BO – Facturación por cliente** | Idem, por cliente | Mismos | `cuentacliente` + cliente, viajantes, erp_zona | Vendedor y zona desde cliente. |

La **definición** de ventas netas (tipos y `SubtotalDesc`) es consistente. La diferencia en `CodigoMovimiento <> 0` solo existe en el reporte `ventas_netas`; conviene unificar criterio si se confirma su uso.

---

## 6. Riesgos y mejoras sugeridas

### 6.1 Filtro `punto_venta.cont = 'Si'`

En VB6, varios informes de facturación limitan a puntos de venta con `punto_venta.cont = 'Si'`. El reporte incluye todos los PV.

- **Riesgo**: Si hay PV no contribuyentes con facturación en `cuentacliente`, las ventas netas del reporte podrían diferir de informes VB6 que filtran por `cont`.
- **Recomendación**: Definir si “Ventas Netas” debe restringirse a PV contribuyentes. Si sí, añadir `LEFT JOIN punto_venta` (o usar el existente) y `AND (pv.cont = 'Si' OR pv.cont IS NULL)` (o el criterio que corresponda según negocio).

### 6.2 Notas de débito (NDA, NDB, NDC, NDE)

El reporte no incluye ND*. Estas suelen ser ajustes positivos.

- **Riesgo**: Si el negocio considera ventas netas como “facturas − NC + ND”, el reporte quedaría incompleto.
- **Recomendación**: Confirmar con negocio. Si se deben incluir, ampliar `TipoComprobante` y sumar ND* en ventas (o en una métrica aparte).

### 6.3 NCT y otras NC

Se usan NCA–NCM. En VB6 aparece también `NCT` en mapeos AFIP. Si en la base hay NCT u otras NC con impacto en ventas, valorar incluirlas en “notas de crédito”.

### 6.4 CodigoMovimiento <> 0

Solo `ventas_netas` aplica este filtro; sales_summary y BO no.

- **Recomendación**: Validar en base si existen movimientos con `CodigoMovimiento = 0` y si deben excluirse. Si no, eliminar el filtro para alinear con los demás reportes.

### 6.5 SubtotalDesc vs. ImporteVenta

Se usa solo `SubtotalDesc`. Si en algunos movimientos `SubtotalDesc` es NULL y `ImporteVenta` está poblado, esos importes no se contabilizan.

- **Recomendación**: Opcionalmente usar `COALESCE(cc.SubtotalDesc, cc.ImporteVenta, 0)` como en Exportacion, si se confirma que en la base ocurre ese caso.

### 6.6 Sucursal / PV y nombres

Joins a `sucursales` y `punto_venta` son por `id_sucursal` y `id_punto_venta`. Validar en esquema real que `cuentacliente.CodSucursal` y `cuentacliente.id_pv` coinciden con esas PKs (como se indica en `VALIDACION_BO_REPORTE_CAMPOS.md` para comp_ped).

---

## 7. Resumen de validación

| Aspecto | Estado |
|--------|--------|
| Tabla `cuentacliente` | Correcto. |
| Tipos FA–FM, NCA–NCM | Correctos respecto a definición “ventas − NC”. |
| `SubtotalDesc` para importes | Correcto; valorar fallback a `ImporteVenta` si aplica. |
| `Anulado = 'No'` | Correcto. |
| Filtro por `Fecha` | Correcto. |
| Sucursal y PV (JOINs, filtros) | Correctos. |
| `CodigoMovimiento <> 0` | Solo en ventas_netas; validar y alinear con otros reportes. |
| `punto_venta.cont` | No aplicado; valorar si debe restringirse a PV contribuyentes. |
| ND* y NCT | No incluidos; confirmar con negocio si deben formar parte. |

En conjunto, **las consultas y la definición del reporte Ventas Netas están alineadas con el uso de `cuentacliente` y tipos de comprobante en VB6**. Las mejoras sugeridas son de **definición de negocio** (cont, ND*, NCT, CodigoMovimiento) y de **robustez** (SubtotalDesc/ImporteVenta), no errores evidentes en las fuentes de datos.

---

*Documento generado a partir del análisis de los formularios VB6 y del código del reporte. Validar con esquema real de la base y reglas de negocio antes de aplicar cambios.*
