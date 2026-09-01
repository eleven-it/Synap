# Análisis trazabilidad artículo (hub MPR)

**Ruta:** `/mpr/reportes/?grupo=trazabilidad&reporte=kardex_articulo`  
**Change:** `mpr-trazabilidad-analisis-completo`  
**Plan:** [PLAN_TRAZABILIDAD_ANALISIS_COMPLETO.md](PLAN_TRAZABILIDAD_ANALISIS_COMPLETO.md)

---

## Propósito

Informe **canónico** por artículo que **reconstruye la historia del rango** pedido:

1. **Lista de materiales (BOM)** — de qué se arma el artículo  
2. **Demanda de pedidos** — PED abiertos con pendiente (**demanda viva** actual; no es historial comercial)  
3. **Movimientos** — solo del rango Desde–Hasta que **mueven** stock, con saldo corrido

**Contrato de reconstrucción**

- Lo **anterior al Desde** no se lista fila a fila: se consolida en **saldo inicial histórico**.  
- En el rango se listan movimientos con `afecta_deposito` (OPA, REM, INV, OPP…). **FA** y similares se omiten.  
- Saldo corrido = saldo inicial + movimientos del rango → explica el stock **al Hasta** (y, si Hasta es hoy, debería conciliar con **Terminado actual**).

Cabecera: artículo, rango, pack/componente, Terminado actual.  
**No se muestra** «A producir» ni timeline MPR duplicada. KPI strip: Pedido / Terminado / Movimientos.

Al **Analizar** / **Actualizar** se muestra el **modal de espera Synap** (`mpr-post-loading` / `synapShowPostLoading`).

La entrada del hub se llama **Análisis trazabilidad** (slug `kardex_articulo`, retrocompatible).

---

## Fuente de datos

Servicio único: `construir_analisis_trazabilidad_articulo` en `mpr/services_kardex_articulo.py`.

| Bloque | Origen |
|--------|--------|
| Demanda PED | `listar_demanda_ped_por_articulo` → `_listar_demanda_ped_vivo_fifo` |
| Stock / brecha | Stock Terminado + fórmulas tablero pack (brechas en payload; UI no las destaca) |
| Movimientos | OPP/OPA MSTOCK + REM (`stock`) + **Stock Inicial** + **inventario/faltante/sobrante/conteo** MSTOCK; FA omitido en listado |
| Pre-período | Misma recolección con `solo_pre_periodo` → `saldo_inicial` |
| Saldo corrido | Arranca en saldo inicial histórico; solo filas `afecta_deposito` |

**Línea de tiempo** (`reporte=timeline`) delega al mismo servicio + enlace a este informe `#timeline`.

---

## Golden sample (resultado esperado)

Archivo: [`exports/kardex_610_t6_terminado.xlsx`](../../exports/kardex_610_t6_terminado.xlsx)  
Generador: `exports/_gen_kardex_610_t6.py` (base Bestsox · familia pack **610 T6**).

El informe Synap debe reproducir la **misma narrativa** sobre el depósito `tipo_mpr=Terminado` (en el sample, CodDeposito **6**):

| Hoja Excel | Equivalente en Synap |
|------------|----------------------|
| Resumen (PED vivos) | §2 Demanda viva |
| OPA y Remitos | Contexto de demanda; en UI el detalle de armado va en subfilas OPA |
| Kardex Mix / Blanco / Negro | §3 Movimientos + saldo corrido + KPI Terminado |

**Kardex Blanco (IDArt 1399) — historia canónica que explica Terminado = −130**

1. OPA +130 → saldo 130  
2. Faltante (INV) −130 → saldo 0  
3. REM −130 → saldo **−130** (= `stock_deposito` Terminado)  
4. FA aparece en el Excel solo como referencia (`Afecta depósito = No`); **en Synap no se lista**

Misma lógica para Mix (−29) y Negro (−131): OPA(s) + Faltante + REM; FA no mueve saldo.

**Contrato de eje:** el depósito se resuelve **automáticamente** según el artículo analizado: **pack → Terminado** (`tipo_mpr=Terminado`), **componente → Semi elaborado**. No hay selector manual en la UI; la cabecera muestra el eje elegido.

Los eventos MPR (envío, parte, clasificación) **no** entran al saldo corrido: no mueven `stock_deposito` (ver `ENVIO_PRODUCCION_TABLERO.md`). Van en `eventos_mpr` / timeline, no en §3 Movimientos.

---

## Reglas de saldo y clasificación

### FA y movimientos que no mueven stock

`afecta_deposito=False` (típicamente **FA**) **no se listan**.

### Clases en pantalla

| Clase UI | Origen | Saldo |
|----------|--------|-------|
| `opp` | Entrada producción | Suma entrada |
| `opa` | Armado pack | Entrada pack / salida componentes |
| `rem` | Remito cliente | Salida |
| `fa` | Factura | **Omitido** |
| `inventario` | Ajuste MSTOCK (faltante/sobrante/conteo/inventario) | Según entrada/salida; columna **Conteo** = saldo depósito tras el ajuste |
| `stock_inicial` | MSTOCK Stock Inicial (alta inicial en depósito) | Entrada |

### Saldo inicial histórico

Al `desde`: suma de movimientos previos que mueven Terminado. Si falla → advertencia y `calculado_ok=false`.  
Si Hasta ≥ hoy y `saldo_final ≠ Terminado` del depósito analizado, se agrega advertencia de descuadre.  
Si se alcanza el `limit` (default 2000) en pre-período o rango → advertencia de truncado.

---

## Bloques en pantalla (orden)

1. Filtros artículo (+ fechas en shell; depósito automático)  
2. Cabecera: historia reconstruida del período  
3. KPI strip: Pedido, Terminado, Movimientos  
4. **§1 BOM**  
5. **§2 Demanda viva** — tabla PED + resumen **Stock / Cubierto con stock / PED Urgente** (sobre el total pendiente)  
6. **§3 Movimientos**: tarjetas saldo inicial / saldo al cierre + tabla (columnas: Conteo, Entrada, Salida, Saldo)

---

## Export CSV

Botón **Exportar CSV** del shell: `analisis_trazabilidad.csv` multi-sección (el servicio puede seguir exponiendo brechas / a_producir en el payload aunque la UI no los muestre).

---

## Permisos y UX

- Permiso: `mpr.ver` **OR** `mpr.reportes`  
- UI en español; fechas **dd/MM/yyyy**  
- Sin `alert`/`confirm`/`prompt`; modal Synap de espera al cargar  
- Canon UI: reportes MPR / [FUENTE_VERDAD_UI_REPORTES_MPR.md](../general/FUENTE_VERDAD_UI_REPORTES_MPR.md)

---

## Tests

```bash
docker exec Synap_app python manage.py test \
  mpr.tests.test_analisis_trazabilidad_articulo \
  mpr.tests.test_kardex_articulo \
  mpr.tests.test_reportes_trazabilidad \
  --keepdb
```

---

## Referencias

- [REPORTES_MPR.md](REPORTES_MPR.md) — catálogo hub  
- `exports/_gen_kardex_610_t6.py` — referencia empírica pack 610  
- Change SDD: `openspec/changes/mpr-trazabilidad-analisis-completo/`
