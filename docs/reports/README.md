# Documentación Reports

## Manual de usuario

| Documento | Descripción |
|-----------|-------------|
| [MANUAL_USUARIO_REPORTES.md](MANUAL_USUARIO_REPORTES.md) | **Manual de usuario Informes** (Ventas marcas mensual + Ventas Mensuales Licenciatarios). Actualizado 07/08/2026. |
| [manual_usuario_reportes.html](manual_usuario_reportes.html) | Manual HTML navegable. En la app: **`/reports/manual/`**. Regenerar: `python3 scripts/generar_manuales_html.py`. |

## Planes abiertos

| Documento | Descripción |
|-----------|-------------|
| [PLAN_FILTROS_PV_SUCURSAL_VENTAS.md](PLAN_FILTROS_PV_SUCURSAL_VENTAS.md) | Filtros Punto de venta y/o Sucursal en informes de ventas — **implementado** (31/08/2026) |

### Oleadas completadas — filtros PV / sucursal en ventas

Resumen consolidado del change `filtros-pv-sucursal-ventas`. Detalle técnico y criterios de aceptación en [PLAN_FILTROS_PV_SUCURSAL_VENTAS.md](PLAN_FILTROS_PV_SUCURSAL_VENTAS.md) §8.

| Oleada | Alcance | Tests principales |
|--------|---------|-------------------|
| **1** | Whitelist PV visible en familia BO (VO, VPV, VPA, VMSA, BOM, VMM); excluye `bo-stock-facturacion` | `test_filtros_pv_sucursal_ventas.py::TestOleada1Whitelist` |
| **2.A** | Ventas mensuales licenciatarios: filtros solo tramo ANET post-cutover | `test_ventas_mensuales_licenciatarios.py` |
| **2.B** | Clientes sin ventas: filtros en `ON` del anti-join + relay | `test_clientes_sin_ventas_relay.py` |
| **3** | Relay ventas-netas con listas `sucursales` / `punto_venta` + compat escalar | `test_ventas_netas_relay.py` |
| **4.A** | Resumen ejecutivo: `_cc_scope_sql` + API + tags PV | `test_executive_summary_contract.py` |
| **4.B** | Command Center: multi-select sucursales/PV, compat `?sucursal=` | `test_executive_dashboard_contract.py` |
| **7** | Cascada sucursal→PV en UI | **N/A** (producto no exigió — ver plan §8.4.C) |
| **8** | Regresión sin filtros, suite verify, smoke template PV | `test_filtros_pv_sucursal_ventas.py::TestFase8Regresion` |

Comando suite Fase 8:

```bash
docker exec Synap_app python manage.py test \
  reports.tests.test_filtros_pv_sucursal_ventas \
  reports.tests.test_ventas_mensuales_licenciatarios \
  reports.tests.test_clientes_sin_ventas_relay \
  reports.tests.test_ventas_netas_relay \
  reports.tests.test_executive_summary_contract \
  reports.tests.test_executive_dashboard_contract
```

## Specs clave (marcas / licenciatarios)

| Documento | Descripción |
|-----------|-------------|
| [INVENTARIO_DEPOSITO_ARTICULO.md](INVENTARIO_DEPOSITO_ARTICULO.md) | Inventario por depósito (catálogo; motor MPR) |
| [SPEC_INFORME_VENTAS_MARCAS_MENSUAL.md](SPEC_INFORME_VENTAS_MARCAS_MENSUAL.md) | Spec VMM |
| [SPEC_INFORME_VENTAS_MARCA_SUPERART.md](SPEC_INFORME_VENTAS_MARCA_SUPERART.md) | Spec Ventas por marca y SuperArt |
| [DESIGN_INFORME_VENTAS_MARCA_SUPERART.md](DESIGN_INFORME_VENTAS_MARCA_SUPERART.md) | Diseño técnico VMSA |
| [VERIFY_INFORME_VENTAS_MARCA_SUPERART.md](VERIFY_INFORME_VENTAS_MARCA_SUPERART.md) | Verificación VMSA |
| [SPEC_INFORME_VENTAS_BOM_DOCENAS.md](SPEC_INFORME_VENTAS_BOM_DOCENAS.md) | Spec Ventas BOM en docenas |
| [DESIGN_INFORME_VENTAS_BOM_DOCENAS.md](DESIGN_INFORME_VENTAS_BOM_DOCENAS.md) | Diseño técnico Ventas BOM |
| [VERIFY_INFORME_VENTAS_BOM_DOCENAS.md](VERIFY_INFORME_VENTAS_BOM_DOCENAS.md) | Verificación Ventas BOM |
| [SPEC_INFORME_VENTAS_MENSUALES_LICENCIATARIOS.md](SPEC_INFORME_VENTAS_MENSUALES_LICENCIATARIOS.md) | Spec VML |
| [ANALISIS_MONTHLY_REPORTING_BEST_SOX_LICENCIATARIOS.md](ANALISIS_MONTHLY_REPORTING_BEST_SOX_LICENCIATARIOS.md) | Análisis plantillas Monthly Reporting |
