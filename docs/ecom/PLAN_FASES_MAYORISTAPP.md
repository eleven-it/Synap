# Plan por fases — migración `mayoristapp` → Synap

**Alcance:** `administraNET-ecom/mayoristapp/` (repo `git@github.com:licPflores/administraNET-ecom.git`).  
**Alineado a:** metodología general del módulo e-com ([SPEC.md](./SPEC.md), [REVERSE_ENGINEERING.md](./REVERSE_ENGINEERING.md), [VALIDACION_FINAL.md](./VALIDACION_FINAL.md)).

---

## Visión de fases

| Fase | Nombre | Objetivo | Entregables |
|------|--------|----------|-------------|
| **A** | Inventario y trazabilidad | Saber *qué* migrar y en qué orden | [REVERSE_ENGINEERING.md](./REVERSE_ENGINEERING.md), [MAYORISTAPP_MIGRATION.md](./MAYORISTAPP_MIGRATION.md), [MAYORISTAPP_RELAYS.md](./MAYORISTAPP_RELAYS.md), constantes en `ecom.services.mayoristapp_relays` |
| **B** | Spec por vertical | Definir *cómo* (contratos, permisos, SQL parametrizado) | Un `SPEC_*` o sección por vertical; decisiones cerradas en docs; checkpoints `EcomMigrationCheckpoint` planificados |
| **C** | TDD e implementación | Código Django por vertical | Tests + servicios/vistas/API; checkpoint marcado al cerrar vertical |
| **D** | Validación y seguridad | Listo para uso controlado | [VALIDACION_FINAL.md](./VALIDACION_FINAL.md), smoke, revisión de permisos y secretos |

**Estado (seguimiento):** ver [CHECKLIST_FASES_MAYORISTAPP.md](./CHECKLIST_FASES_MAYORISTAPP.md).

| Fase | Estado |
|------|--------|
| **A** Inventario y trazabilidad | **Cerrada** (2026-03-30) |
| **B** Spec por vertical | **Cerrada** (2026-03-30) — [MAYORISTAPP_SPEC_INDICE.md](./MAYORISTAPP_SPEC_INDICE.md) |
| **C** TDD e implementación | **Cerrada** (decisión de avance de plan en esta tanda): verticales clientes/comprobantes/informes ventas netas implementadas y con checkpoint; remanentes de paridad fina quedan como validación operativa en Fase D |
| **D** Validación y seguridad | En curso (smoke/CSRF automatizado ejecutado; pendiente validación manual en entorno objetivo y cierre de seguridad operativa) |

---

## Verticales sugeridos (orden de negocio)

1. **Fundaciones:** sesión vendedor / permisos equivalentes a PHP (`login`, `core`) — prerequisito transversal.  
2. **Catálogo y precios:** relays rubro/art/stock/lista-precio/promos + `price_calculator`.  
3. **Clientes y domicilios:** `relay-cliente*`, contacto, tipo cliente.  
4. **Comprobantes:** pedidos, presupuestos, remitos, FE/NC.  
5. **Cuenta corriente y recibos:** `relay-ctacte`, `relay-cuenta-corriente`, recibos; cruzar con `administraNET-ecom/docs/.../modelo_base_datos.md`.  
6. **Informes:** `relay-ventas-netas*` → `reports` ([SPEC_VENTAS_NETAS.md](./SPEC_VENTAS_NETAS.md)).  
7. **Logística y envíos:** geolocalización, rutas, cálculo envío.  
8. **Carrito web/móvil:** `jcart/relay.php`, `tmobile/jcart/relay-mob.php` (último o subproyecto UI).

Cada vertical completado en Fase C debe tener un **`module_slug`** en `EcomMigrationCheckpoint` (ver [MAYORISTAPP_RELAYS.md](./MAYORISTAPP_RELAYS.md) columna sugerida).

---

## Criterios de cierre por vertical (Fase C)

- Tests automatizados que cubran el servicio principal (unitarios; integración MySQL opcional con `@pytest.mark.integration`).  
- Sin SQL concatenado con entrada de usuario; usar `legacy_db` / pool como en `reports`.  
- Permisos explícitos (operativo vs gerencial donde aplique).  
- Nota breve en el SPEC del vertical o en `MAYORISTAPP_RELAYS.md` (columna estado).

---

## Referencias rápidas

- Inventario máquina-verificable: `GET /ecom/api/mayoristapp/relay-inventory/` (lista de rutas relativas a `mayoristapp/`).  
- Paridad conteos: `GET /ecom/api/migration-info/`.
