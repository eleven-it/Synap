# Checklist — plan mayoristapp (fases A–D)

**Referencia:** [PLAN_FASES_MAYORISTAPP.md](./PLAN_FASES_MAYORISTAPP.md)  
**Repo PHP:** `git@github.com:licPflores/administraNET-ecom.git`

---

## Fase A — Inventario y trazabilidad

- [x] Inventario cuantitativo en [REVERSE_ENGINEERING.md](./REVERSE_ENGINEERING.md) (PHP repo / `mayoristapp`, relays).
- [x] Guía alcance [MAYORISTAPP_MIGRATION.md](./MAYORISTAPP_MIGRATION.md).
- [x] Tabla 44 relays + destinos sugeridos [MAYORISTAPP_RELAYS.md](./MAYORISTAPP_RELAYS.md).
- [x] Tupla canónica `ecom.services.mayoristapp_relays.MAYORISTAPP_RELAY_PATHS` + tests de longitud vs `RELAY_ENDPOINT_COUNT`.
- [x] API `GET /ecom/api/migration-info/` (incl. `mayoristapp_php_file_count`).
- [x] API `GET /ecom/api/mayoristapp/relay-inventory/`.

**Cierre Fase A:** 2026-03-30 (documentado en [PLAN_FASES_MAYORISTAPP.md](./PLAN_FASES_MAYORISTAPP.md)).

---

## Fase B — Spec por vertical

- [x] Índice de specs por vertical: [MAYORISTAPP_SPEC_INDICE.md](./MAYORISTAPP_SPEC_INDICE.md).
- [x] Fundaciones: [SPEC_MAYORISTAPP_FUNDACIONES.md](./SPEC_MAYORISTAPP_FUNDACIONES.md).
- [x] Catálogo y precios: gaps §5 en [SPEC_CATALOGO_RUBRO.md](./SPEC_CATALOGO_RUBRO.md), §H en [SPEC_PRECIOS.md](./SPEC_PRECIOS.md).
- [x] Clientes: [SPEC_MAYORISTAPP_CLIENTES.md](./SPEC_MAYORISTAPP_CLIENTES.md).
- [x] Comprobantes: [SPEC_MAYORISTAPP_COMPROBANTES.md](./SPEC_MAYORISTAPP_COMPROBANTES.md).
- [x] FE/NC: [SPEC_MAYORISTAPP_FE_NC.md](./SPEC_MAYORISTAPP_FE_NC.md).
- [x] Cuenta corriente / recibos: [SPEC_MAYORISTAPP_CTACTE_RECIBOS.md](./SPEC_MAYORISTAPP_CTACTE_RECIBOS.md) (enlace a `modelo_base_datos.md` del repo e-com).
- [x] Informes: puntero §D en [SPEC_VENTAS_NETAS.md](./SPEC_VENTAS_NETAS.md); pendiente funcional sigue en §C.3.
- [x] Logística y carrito: [SPEC_MAYORISTAPP_LOGISTICA_CARRITO.md](./SPEC_MAYORISTAPP_LOGISTICA_CARRITO.md).
- [x] `EcomMigrationCheckpoint`: criterios en MAYORISTAPP_SPEC_INDICE §Checkpoints.

**Cierre Fase B (documentación):** 2026-03-30.

---

## Fase C — TDD e implementación

- [x] Por vertical: servicios + vistas/API + tests (alcance definido en esta etapa); actualizar columna **Estado** en MAYORISTAPP_RELAYS.
- [x] Checkpoint en BD — vertical **clientes** (`mayoristapp_clientes`): migración `0002_checkpoint_mayoristapp_clientes`; listado en `GET /ecom/api/migration-info/` → `checkpoints`.
- [x] Checkpoint — vertical **comprobantes** listados v1 (`mayoristapp_comprobantes`): migración `0003_checkpoint_mayoristapp_comprobantes`.
- [x] Checkpoint — vertical **informes ventas netas** (`mayoristapp_informes_vn`, `mayoristapp_informes_vn_gerencia`): migración `0014_update_checkpoint_informes_vn`.
- [x] Vertical **informes (relay-ventas-netas*)**: cobertura v1 ampliada en `reports` con tests (`listarPor` mes/cliente/vendedor/rubro/subrubro/articulo/marca/zona/tipocliente/proveedor; `tipo` monto/unidades/peso en dimensiones `stock`; `queInforme` vt/ut/uti/seleccion; `grafico=1`).
- [x] Cierre de Fase C (decisión de plan): implementación finalizada para verticales priorizados; paridad fina con DB real se continúa en Fase D como validación operativa.

---

## Fase D — Validación y seguridad

- [x] Documentación smoke mayoristapp + CSRF: [SMOKE_MAYORISTAPP.md](./SMOKE_MAYORISTAPP.md), [VALIDACION_FINAL.md](./VALIDACION_FINAL.md) §1 y § API sesión.
- [x] Smoke automatizado CSRF: `docker exec Synap_app python manage.py test ecom.tests.test_fase_d_csrf_smoke -v 2` (OK, 2/2).
- [x] Smoke técnico sin sesión (health/migration-info/relay-inventory) ejecutado vía `manage.py shell` + `django.test.Client` (`HTTP_HOST=127.0.0.1`): `200/200/200`, `mayoristapp_relay_count=44`, `mayoristapp_php_file_count=1276`.
- [x] Script de ejecución manual en entorno objetivo creado: `scripts/fase_d_smoke_manual.sh` (usa `BASE_URL`, `SESSION_ID`, `CSRF_TOKEN`).
- [ ] Ejecución manual smoke en entorno objetivo (curl/health/migration-info + POST con sesión real).
- [ ] Revisión permisos/CSRF en endpoints POST nuevos (ver nota en VALIDACION_FINAL § API sesión).
- [ ] Secretos solo por entorno (sin credenciales PHP en repo). Pre-auditoría rápida por patrones en `ecom/` y `reports/` sin secretos hardcoded detectados; se observan usos de `mysql_config['PASSWORD']` (configurado por entorno).
