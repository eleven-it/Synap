# Deuda técnica — módulo e-com

- Estado plan [PLAN_FASES_MAYORISTAPP.md](./PLAN_FASES_MAYORISTAPP.md): Fase C cerrada; cierre formal de Fase D diferido a staging.
- Pendiente funcional: mantener FE mayoristapp en solo lectura (según plan) y robustecer operación de cola mail async (reintentos/cron) en productivo.
- Portar relays PHP a vistas/servicios Django con paridad funcional (priorizar `relay-ventas-netas*` → `reports`; relay Synap amplía `listarPor` mes/cliente/vendedor/rubro/subrubro/articulo/marca/zona/tipocliente/proveedor + `tipo` monto/unidades/peso (stock) + `queInforme` vt/ut/uti/seleccion + `grafico=1`; pendiente paridad fina con PHP y validación en DB real).
- `relay-filtros-estadisticas.php` y `relay-devoluciones.php` quedaron en v1 lectura. Integración ampliada en `test_devoluciones_relay_integration.py` (fechas/estado, `filtrarPor` cliente, sugerencias `NroCompBusq`, filtros `vendedor/proveedor/rubro/subrubro/usuario`, validación de formato `label/value` y orden ascendente); pendiente correr y ajustar contra dataset real de negocio con cobertura de combinaciones complejas.
- UI/UX Informes en `reports`: los informes se listan solo en **Indicadores operativos** o **Indicadores gerenciales** (`ReportDefinition.category`). Metadatos `catalog_legacy_section` / `catalog_legacy_order` sirven para orden relativo y etiqueta «Informe legacy» en tarjetas; migración `0031_catalog_legacy_metadata_and_placeholders` y placeholders `mayoristapp-*` en `sample_data.py`. Nuevos informes: `ReportDefinition` con categoría correcta, metadata de orden si aplica, y `query_runner` cuando corresponda.
- Sustituir autenticación AES en SQL por flujo seguro (`login` / usuarios Django / token legacy documentado).
- Externalizar credenciales removidas del código PHP en toda migración de scripts (`includes.inc.php`).
- Inventariar tareas cron (`sincroniza.php`, etc.) y decidir Celery vs `manage.py` + systemd.
- ~~Documentar `util-calculaprecio.inc.php` con fórmulas completas y tests de regresión numérica.~~ (hecho: [SPEC_PRECIOS.md](./SPEC_PRECIOS.md) + `ecom/services/price_calculator.py` + tests TDD)
- Añadir DRF + OpenAPI cuando existan API REST de negocio (no solo metadatos).
- Resolver `[DECISION PENDIENTE]` en [SPEC.md](./SPEC.md) (FK MySQL, dump de producción).
