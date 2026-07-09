# Verify — ventas-analitica-precios-historial

## Tests automáticos

```bash
docker exec Synap_app python manage.py test ventas.tests.test_precios_historial
```

## Checklist manual

- [ ] Asignar `ventas.precios_historial.ver` a un puesto de consulta
- [ ] `/ventas/evolucion-precios/` — ranking con filtros fecha/lista/marca/rubro
- [ ] `/ventas/precios-terminados/` — botón historial en fila abre modal con serie temporal
- [ ] Reports slug `evolucion-precios` devuelve mismas columnas que ranking SSR
- [ ] Guardar precio en terminados genera fila en `precios_historial` visible en modal

## Notas

- Deltas calculados en Python; no requiere `LAG` en MySQL legacy.
- Permiso de edición `ventas.precios_terminados.editar` también habilita historial.
