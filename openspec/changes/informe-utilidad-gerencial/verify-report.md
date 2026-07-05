# Verify report — Informe utilidad gerencial

**Change:** `informe-utilidad-gerencial`
**Fecha:** 02/07/2026
**Estado:** ✅ Implementado y verificado

## Resumen

Migración del informe gerencial **Utilidad** (+ variante **inflación**) desde
`administraNET-ecom/mayoristapp/relay-ventas-netas-gerencia.php` (modos `ut`/`uti`)
a Synap `reports/`, con servicio dedicado, relays operativo/gerencial, UI canónica,
`ReportDefinition` y checkpoint.

## Artefactos

| Artefacto | Ruta |
|---|---|
| Servicio | `reports/services/utilidad_gerencial.py` |
| Relays | `reports/utilidad_gerencial_relay_views.py` |
| Rutas | `reports/api_urls.py` (`utilidad-gerencial/relay/` y `.../gerencia/`) |
| UI | `reports/templates/reports/dashboard_utilidad_gerencial.html` + slug en `reports/views.py` |
| Migración | `reports/migrations/0035_add_utilidad_gerencial_report.py` |
| Tests | `reports/tests/test_utilidad_gerencial_relay.py` |

## Paridad de negocio (vs PHP)

- Universo `stock` + `cuentacliente`, `Anulado='No'`, `visualiza_ensamble='No'`,
  `TipoComp IN ('Venta','Venta TPV','Devol - Cliente','ND Anul NC')`; signo negativo solo `Devol - Cliente`.
- Columnas: **Venta** (`PrecioVentaxR`), **Neto** (`PrecioNetoxR`), **Costo** (`PrecioCostoxR`), **Utilidad** (`Neto-Costo`).
- **NC/Desc** desde `cuentacliente` (devolución `ImpDesc1+ImpDesc2`; ND `SubtotalDesc`; NC `-SubtotalDesc`; factura `-(ImpDesc1+ImpDesc2)`; excluye `concepto_nd='Anulacion NC - Mercaderia'`), **solo** en dimensiones `cliente/tipocliente/vendedor/zona` sin filtro de artículo (paridad `traigoArrayNc`).
- **Venta Neta** = `Neto+Desc`, **Utilidad** = `Utilidad+Desc`, **Utilidad %** = `(Neto+Desc)/Costo` (0 si `Costo=0`).
- **Inflación**: 2º rango (`mensual` = lapso desplazado; `anual` = -1 año), **Índice** = `AVG(PrecioCostoxU r1)/AVG(PrecioCostoxU r2)` por dimensión, **Venta Esp** = `(Neto2+DescAnt)*Índice`, **Resultado** = `Neto/((Neto2+DescAnt)*Índice)` (1 si denominador 0).

## Seguridad

- SQL 100% parametrizado; ids normalizados a `int`; filtros anti-inyección (solo numéricos, ignora `todos`).
- Operativo: scope forzado a `id_vendedor_usr` de sesión (no ampliable por `filtrarPor`); 403 si falta.
- Gerencial/supervisor: `vendedor_a_cargo` salvo filtro explícito de vendedor.

## Resultados de verificación

- Tests: `docker exec Synap_app python manage.py test reports.tests.test_utilidad_gerencial_relay` → **17/17 OK**.
- Migración: `migrate reports` → `0035_add_utilidad_gerencial_report ... OK`.
- Registro: `ReportDefinition(slug=utilidad-gerencial, managerial, section=gerenciales, order=10, active)` + rutas API resueltas.

## Decisiones / limitaciones (v1)

- `cod` de cliente = `cli.Codigo` (aunque `usa_id_manual`) para casar con NC (`cc.Codigo`); id manual en el nombre.
- Sin pivote por sub-período: se agrega sobre el rango (coherente con `controlarFechas` ~1 mes en el legacy).
- NC no aplicada en dimensiones de artículo (fiel al comportamiento PHP, no un gap).
