# Design: Endurecimiento CustomerMapping

## Arquitectura

```
CustomerMappingForm.clean()
    → services/customer_mapping_validation.py
        → TiendanubeService.get_customer()
        → AdministraNETService.get_customer()
        → CustomerMapping uniqueness check

AdministraNETService.create_customer()
    → get_customer_by_email / get_customer_by_cuit (pre-insert)

CustomerMappingListView
    → queryset sin filtro estricto dual-ID
    → GET ?link=complete|incomplete|all

UI
    → badge is_fully_linked
    → botón POST sync_mapping_ajax
```

## Migración 0023

- `UniqueConstraint` en `adminet_codigo` con `condition=Q(adminet_codigo__isnull=False)`.
- AlterField defaults: `sync_enabled=False`, `sync_direction=tiendanube_to_adminet` (solo default Django; filas existentes sin cambio).

## Compatibilidad

- Webhooks y sync masivo siguen usando `create_customer`; anti-duplicado aplica a todos.
- Mapeos legacy con `adminet_codigo` duplicado: migración fallará → comando de limpieza documentado si aplica.
