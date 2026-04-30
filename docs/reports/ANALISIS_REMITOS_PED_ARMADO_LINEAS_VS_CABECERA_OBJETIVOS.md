# Análisis: remitos y pedidos en armado — líneas (`stockp`) vs cabecera (`comp_ped`)

**Objetivo:** verificar si se puede implementar **remitos** y **pedidos en armado** por **artículo** en el informe `ventas-objetivos-vs-bo`, manteniendo coherencia con los totales **por cliente** que ya calcula `ventas_objetivos_bo_runner.py`.

**Fecha del documento:** 30/04/2026

---

## 1. Estado actual del informe objetivos

| Métrica | Fuente actual | Granularidad |
|---------|---------------|--------------|
| Facturación / unidades / árbol rubro-sub-art | `stock` + `cuentacliente` + `articulo` | Por cliente y `IDArt` (renglón de movimiento de factura/NC) |
| Remitos | `comp_ped` con `TipoComprobante = 'REM'`, `Estado = 'Pendiente'`, **filtro `cp.Fecha` en el período de facturación** | **`SUM(SubtotalDesc)` agrupado solo por `cp.Codigo` (cliente)** |
| Pedidos en armado | `comp_ped` PED, `Estado IN ('En preparación','Preparado')`, **sin filtro de fecha** (paridad `total-consolidado-operativo`) | **`SUM(SubtotalDesc)` por cliente** |

Los remitos **no entran** en `_nest_venta_detalle_rubro_subrubro_articulo`: el código indica que son montos de **cabecera** y no se reparten en el árbol.

---

## 2. Hipótesis para reparto por artículo

En AdministraNET, pedidos y remitos de venta modelan **renglones en `stockp`** ligados a la cabecera por `stockp.CodigoMovimiento = comp_ped.CodigoMovimiento` (véase `reports/docs/CONTEXTO_TABLAS_VB6_INFORMES.md`, `stockp.md`).

Si la suma de importes por renglón **coincide** (dentro de tolerancia) con `comp_ped.SubtotalDesc` por comprobante y, agregado, por cliente, se puede:

1. Agregar en backend `remitos_por_art` / `ped_arm_por_art` como `(id_cliente, id_art) → importe`.
2. Fusionar en cada nodo **articulo** del JSON (similar a `_merge_bo_en_detalle_arbol`).
3. Mantener rubro/subrubro en «—» o calcularlos como suma de hijos (decisión de producto).

Si **no cuadra**, hay que definir reglas explícitas (p. ej. diferencia en cabecera sin líneas, gastos, descuentos globales) antes de mostrar valores por artículo.

---

## 3. Campo monetario en línea (recomendación técnica)

- El detalle de **facturación** del mismo informe usa **`PrecioNetoxR`** en tabla **`stock`** unido a `cuentacliente` (`sql_venta_por_art` en `ventas_objetivos_bo_runner.py`).
- El reporte **BO** usa **`stockp.PrecioNetoxR`** para importe por renglón de PED en modo pendiente (`reports/tests/test_bo_report_real_db.py`, queries de diagnóstico).

**Propuesta de reconciliación e implementación:** usar **`SUM(COALESCE(stockp.PrecioNetoxR, 0))`** por documento y por `(cliente, IDArt)`, alineado al BO y al neto por renglón de ventas.

Alternativa a contrastar en datos reales si hubiera sistemática divergencia: `PrecioVentaxR` (bruto por renglón); debe documentarse si se adoptara.

---

## 4. Filtros que deben coincidir con el runner

### 4.1 Remitos

Mismo núcleo que `sql_rem_cli` en `ventas_objetivos_bo_runner.py`:

- `cp.Fecha >= fecha_inicio AND cp.Fecha <= fecha_fin` (SQL date del período de facturación del informe).
- `TipoComprobante = 'REM'`, `Anulado = 'No'`, `Estado = 'Pendiente'`.
- Opcionalmente: `CodSucursal`, `id_pv`, exclusiones por cliente/vendedor (las mismas que aplique el runner en ese entorno).

### 4.2 Pedidos en armado

Mismo núcleo que `sql_ped_arm`:

- **Sin** filtro por `cp.Fecha` (igual que total consolidado operativo para este concepto).
- `TipoComprobante = 'PED'`, `Estado IN ('En preparación','Preparado')`, `Anulado = 'No'`.
- Mismos filtros opcionales sucursal / PV / exclusiones.

---

## 5. Join `stockp` — condiciones prácticas

Siguiendo el patrón ya usado en BO / reservado en el mismo runner:

- `INNER JOIN stockp sp ON sp.CodigoMovimiento = cp.CodigoMovimiento`
- `(sp.anulado IS NULL OR sp.anulado = 'No')`
- `(sp.Comprobante = 'PED' OR sp.Comprobante IS NULL)` para PED (y análogo **`'REM'`** para remitos, más filas con `NULL` según legacy).

**Artículos tipo Gasto:** el BO del proyecto excluye `articulo.tipo_art = 'Gasto'` en varias consultas. Para reconciliación se recomienda ejecutar **dos** totales de líneas:

1. **Todas las líneas** (salvo anuladas).
2. **Excluyendo Gasto** (`tipo_art <> 'Gasto'` o `IDArt` nulo).

Si (2) cuadra mejor con cabecera pero (1) no, la cabecera podría incluir conceptos que no se modelan como artículo vendible.

---

## 6. Qué puede impedir cuadratura perfecta

| Riesgo | Efecto |
|--------|--------|
| Cabecera con **SubtotalDesc** total pero **sin** líneas en `stockp` | Importe cliente correcto en informe actual; **no** hay reparto por artículo sin regla extra (prorrateo o bucket «sin detalle»). |
| Líneas con **`IDArt` NULL** o artículo dummy | Suma por artículo no agota el total; conviene métrica «sin IDArt» en la verificación. |
| Descuentos / impuestos / redondeos solo en cabecera | Delta por documento entre `SubtotalDesc` y suma `PrecioNetoxR`. |
| **`ImporteVenta`** poblado pero **`SubtotalDesc`** en cero en algunos PED | Ya documentado en `VALIDACION_PEDIDOS_PENDIENTES.md`; puede afectar comparación si solo se lee cabecera. |
| Remitos / PED con **Comprobante** en líneas distinto del esperado | Mitigar con `(sp.Comprobante IN (...,'REM') OR sp.Comprobante IS NULL)` según muestra real. |

Ninguno impide **mostrar por artículo** lo que sí está en líneas; obliga a decidir qué hacer con el **resto** respecto al total cliente ya mostrado.

---

## 7. Herramienta de verificación en datos reales

Comando Django (MySQL empresa):

```bash
docker exec Synap_app python manage.py verify_objetivos_remitos_ped_lineas_vs_cabecera \
  --base-empresa NOMBRE_BD \
  --fecha-inicio 2026-04-01 \
  --fecha-fin 2026-04-30
```

Opcional:

- `--tol 1.0` — tolerancia en pesos entre cabecera y líneas por cliente.
- `--sin-excluir-gasto` — por defecto el comando también calcula líneas **excluyendo** `tipo_art = 'Gasto'` para comparar.

**Salida esperada:**

1. Totales globales REM: cabecera vs líneas (todas / sin gasto).
2. Totales globales PED armado: idem (PED **sin** filtro fecha).
3. Cantidad de clientes con `|cabecera - líneas| > tol`.
4. Muestra de comprobantes con mayor delta por documento (`CodigoMovimiento`).
5. Conteo de REM/PED sin ninguna línea en `stockp`.

Interpretación antes de implementar:

- Si los totales globales y por cliente cuadran dentro de `tol` → implementación por artículo **factible** con `PrecioNetoxR`.
- Si hay muchos documentos sin líneas pero cabecera > 0 → en UI por artículo habrá «hueco» respecto al total cliente hasta definir bucket o prorrateo **solo para ese remanente**.
- Si solo cuadra excluyendo Gasto → adoptar el mismo criterio que BO para líneas.

---

## 8. Relación con este documento y siguiente paso

**Actualización:** el informe `ventas-objetivos-vs-bo` incorpora en `venta_detalle` los campos **`remitos_lineas`** y **`pedidos_armado_lineas`** por artículo (misma base que este análisis y el comando de verificación).

Este documento sigue siendo la referencia de riesgos y del comando `verify_*`. El siguiente paso operativo es:

1. Ejecutar el comando en **staging/producción de datos** con períodos representativos.
2. Archivar CSV o captura de divergencias grandes para auditoría.
3. Decidir política para **delta cabecera − líneas** (mostrar solo líneas; columna «Otros»; o no implementar hasta limpiar datos).

Referencias cruzadas: `SPEC_INFORME_OBJETIVOS_VENTAS_BO.md`, `ventas_objetivos_bo_runner.py`, `VALIDACION_PEDIDOS_PENDIENTES.md`, `VALIDACION_BO_REPORTE_CAMPOS.md`.
