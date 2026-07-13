# Verify report — ecom-pedidos-hub-kanban-masivo-sucursales

**Fecha:** 13/07/2026  
**Artifact store:** openspec  
**Modo:** Standard (sin strict_tdd en `openspec/config.yaml`)  
**Resultado:** **PASS WITH WARNINGS**

## Completeness (tasks.md)

| Phase | Tasks | Estado |
|-------|-------|--------|
| 0 Docs + permisos | 0.1–0.4 | [x] |
| 1 Schema + modelos | 1.1–1.4 | [x] |
| 2 Config ternas | 2.1–2.3 | [x] |
| 3 Hub Lista\|Kanban | 3.1–3.5 | [x] |
| 4 Matriz masivo | 4.1–4.4 | [x] |
| 5 Batch checkout | 5.1–5.4 | [x] |
| 6 Verify | 6.1–6.3 | [x] |

**Total:** 26/26 tasks marcadas completas.

## Evidence — tests ejecutados

```text
docker exec Synap_app python manage.py test \
  ecom.tests.test_batch_checkout_masivo \
  ecom.tests.test_pedido_masivo_matriz \
  ecom.tests.test_pedido_masivo_draft \
  ecom.tests.test_pedidos_hub_pipeline \
  ecom.tests.test_vendedor_cliente_marca \
  --keepdb -v1
→ Ran 26 tests — OK
```

## Spec compliance (estático + tests)

| Spec / REQ | Evidencia | Verdict |
|------------|-----------|---------|
| REQ-HUB-01 Home Lista\|Kanban | `pedidos_hub.html`, pipeline | COMPLIANT |
| REQ-HUB-02 Columnas + borradores | `pedidos_hub_pipeline` + test | COMPLIANT |
| REQ-HUB-03 Recuperación / modal | Hub Alpine + archivar draft API | COMPLIANT |
| REQ-HUB-04 Detalle + fechas dd/MM/yyyy | Detalle existente + fechas pipeline | COMPLIANT |
| REQ-HUB-05 Filtro viajante | `_pedidos_mysql` + `puede_ver_todos` | COMPLIANT |
| REQ-VCM-01 Terna unique | DDL `anulado_activo` + 409 API | COMPLIANT |
| REQ-VCM-02 Pantalla config | `config_vendedor_cliente_marca.html` | COMPLIANT |
| REQ-VCM-03 usuario↔viajante | `ecom_usuario_viajante` + resolver | COMPLIANT |
| REQ-VCM-04 Alcance clientes | `listar_clientes_con_ternas` en masivo | COMPLIANT (masivo); WARN — búsqueda compra simple aún no fuerza ternas |
| REQ-MAS-01 Matriz | UI sticky + sucursales | COMPLIANT |
| REQ-MAS-02 Catálogo filtrado | `buscar_articulos_filtrados_ternas` + test | COMPLIANT |
| REQ-MAS-03 1 PED/sucursal | `confirmar_lote_masivo` + `id_cliente_domicilio` | COMPLIANT |
| REQ-MAS-04 Borrador persistente | draft + celdas + hub Continuar | COMPLIANT |
| REQ-MAS-05 Rollback | compensación `anular_pedido_relay` + test fail mid-lote | COMPLIANT |
| REQ-MAS-06 UI canon tablero | slate-800 header / sticky | COMPLIANT |
| REQ-CHK-MAS-01 Batch | API confirmar | COMPLIANT |
| REQ-CHK-MAS-02 Integridad lote | test compensación | COMPLIANT |

## Design decisions

| Decisión | Cumplida |
|----------|----------|
| Canon Tablero producción | Sí |
| Ternas ≠ vendedores_*_asignacion | Sí (tabla propia) |
| Draft Postgres + checkout MySQL | Sí |
| Compensar PED en fallo | Sí |

## Warnings

1. **REQ-VCM-04** en compra simple / relay clientes: el filtro por ternas está aplicado al flujo masivo; el hub/compra simple sigue usando fuentes legacy/`vendedores_clientes_asignacion` según config ecom existente. Aceptable para el alcance del change (masivo + config); follow-up si producto unifica.
2. **Checklist manual (6.2):** no ejecutado E2E en browser en esta sesión; validado por tests unitarios/integración mockeados de checkout.
3. **Suite ecom completa:** no se corrió `manage.py test ecom` entero (solo módulos del change, 26 OK).

## Issues críticos

Ninguno.

## Conclusión

El change está **listo para uso / archive** desde el punto de vista SDD apply+verify. Recomendación: `sdd-archive` cuando producto valide E2E en una empresa con DDL aplicado y ternas cargadas.
