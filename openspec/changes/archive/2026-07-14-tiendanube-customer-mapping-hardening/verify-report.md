# Informe de verificación

**Change**: tiendanube-customer-mapping-hardening  
**Versión spec**: delta `tiendanube-customer-mapping`  
**Modo**: Standard (strict_tdd no configurado)  
**Fecha**: 14/07/2026  
**Ejecutor**: sdd-verify (hybrid)

---

## Completitud de tareas

| Métrica | Valor |
|--------|-------|
| Tareas totales | 8 |
| Tareas completadas | 8 |
| Tareas incompletas | 0 |

Todas las tareas en `tasks.md` están marcadas `[x]`: migración 0023, validación, anti-duplicado, listado, defaults, tests y documentación.

---

## Ejecución de build y tests

**Build / check**: ✅ Aprobado

```bash
docker exec Synap_app python manage.py check
# System check identified no issues (0 silenced).
```

**Tests** (módulos de mapeo cliente / ecom): ✅ 15 pasaron / ❌ 0 fallaron / ⚠️ 0 omitidos

```bash
docker exec Synap_app python manage.py test \
  tiendanube_administranet.tests.test_customer_mapping_validation \
  tiendanube_administranet.tests.test_customer_lookup \
  tiendanube_administranet.tests.test_customer_email_dedup \
  --keepdb -v 2
# Ran 15 tests in 0.180s — OK
```

**Cobertura**: ➖ No disponible (sin umbral configurado en `openspec/config.yaml`)

**Nota operativa**: sin `--keepdb`, la creación de BD de test falla por `test_mydatabase` ya existente (prompt interactivo). Usar `--keepdb` en CI/local.

---

## Matriz de cumplimiento de escenarios

| Requisito | Escenario | Test | Resultado |
|-----------|-----------|------|-----------|
| Validación de IDs en formulario | ID Tienda Nube inexistente | (ninguno) | ❌ UNTESTED |
| Validación de IDs en formulario | Código AdministraNET inexistente | (ninguno) | ❌ UNTESTED |
| Unicidad adminet_codigo | Código AdministraNET ya mapeado | `test_customer_mapping_validation.py > test_codigo_ya_mapeado` | ✅ COMPLIANT |
| Anti-duplicado en alta AdministraNET | Email duplicado en MySQL | `test_customer_mapping_validation.py > test_rechaza_email_duplicado` | ✅ COMPLIANT |
| Listado incluye mapeos incompletos | Mapeo solo Tienda Nube | (ninguno) | ❌ UNTESTED |
| Sync explícito desde UI | Acción Sincronizar ahora (lista/detalle) | (ninguno) | ❌ UNTESTED |
| Defaults seguros al crear | Creación sin activar sync | (ninguno) | ❌ UNTESTED |

**Resumen de cumplimiento**: 2/7 escenarios compliant (29 %)

---

## Correctitud (evidencia estática)

| Requisito | Estado | Notas |
|-----------|--------|-------|
| Validación IDs TN/Adminet | ✅ Implementado | `customer_mapping_validation.py` + `CustomerMappingForm.clean()` |
| Unicidad adminet_codigo | ✅ Implementado | Migración `0023`, constraint + `validate_adminet_codigo_unique_mapping` |
| Anti-duplicado create_customer | ✅ Implementado | `_reject_duplicate_adminet_customer` por email y CUIT |
| Listado incompletos | ✅ Implementado | `CustomerMappingListView` filtro `?link=`, badge `is_fully_linked` |
| Sync explícito UI | ✅ Implementado | `sync_mapping_ajax`, botones en lista y detalle |
| Defaults seguros | ✅ Implementado | Modelo migración + `CustomerMappingForm.__init__`; señal solo encola si `sync_enabled` |

---

## Coherencia (diseño)

| Decisión | ¿Seguida? | Notas |
|----------|-----------|-------|
| Validación vía `customer_mapping_validation.py` | ✅ Sí | Flujo form → servicio → APIs |
| Anti-duplicado pre-insert en `create_customer` | ✅ Sí | Email y CUIT |
| ListView sin filtro estricto dual-ID | ✅ Sí | Queryset `all()` + filtro opcional |
| Migración 0023 constraint + defaults | ✅ Sí | Archivo presente y aplicable |
| UI badge + POST sync | ✅ Sí | Templates y vista AJAX alineados |

---

## Issues encontrados

**CRITICAL** (debe corregirse antes de archive):

- Ninguno bloqueante de ejecución (tests verdes, implementación presente).

**WARNING** (debería corregirse):

- 5/7 escenarios de spec sin test de comportamiento en runtime (validación IDs inexistentes, listado incompleto, sync AJAX, defaults sin Celery).
- Anti-duplicado por CUIT implementado pero sin test dedicado (solo email cubierto en spec).
- `manage.py test` sin `--keepdb` puede bloquearse en entornos con BD de test residual.

**SUGGESTION** (nice to have):

- Añadir tests de vista (`Client`) para `CustomerMappingListView` con `?link=incomplete` y `sync_mapping_ajax`.
- Tests de integración con mocks de `TiendanubeService.get_customer` / `AdministraNETService.get_customer` en formulario.
- Test de señal `post_save` verificando que no se llama `_schedule_sync_pending_async` cuando `sync_enabled=False`.

---

## Veredicto

**PASS WITH WARNINGS**

Implementación completa y coherente con spec y design; 15 tests relacionados pasan y `manage.py check` sin errores. La brecha principal es cobertura de escenarios de spec (2/7 con evidencia runtime). Se recomienda ampliar tests antes de archive o aceptar el riesgo documentado.

**Siguiente fase recomendada**: `sdd-archive` (con warnings) o `sdd-apply` si se exige cobertura mínima de escenarios.
