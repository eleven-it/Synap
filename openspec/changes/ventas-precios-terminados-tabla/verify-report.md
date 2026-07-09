# Verify — ventas-precios-terminados-tabla

**Fecha:** 09/07/2026  
**Veredicto:** READY (MVP P0)

## Tests automáticos

```
docker exec Synap_app python manage.py test ventas.tests.test_precios_terminados
→ 8 tests OK
```

## Criterios de aceptación

| # | Criterio | Estado |
|---|----------|--------|
| 1 | Filtro primario Terminado/2da con reset secundarios | OK |
| 2 | Tags multi + código predictivo | OK |
| 3 | Recálculo neto↔final + dirty | OK |
| 4 | Masivo server-side con preview | OK |
| 5 | Guardado articulo + util + historial | OK (código; validar en BD manual) |
| 6 | UI patrón tablero MPR | OK |
| 7 | Permiso y menú Ventas | OK |

## Pendiente manual

- Asignar permiso `ventas.precios_terminados.editar` al puesto de pricing en empresa real.
- Probar guardado contra MySQL legacy y verificar fila en `precios_historial`.
- Relay Tiendanube: fuera de alcance MVP.
