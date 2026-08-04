# Auditoría pipeline MPR (parte → CC → armado)

Comando read-only para integridad referencial y coherencia de movimientos de stock **por día**.

## Uso

```bash
# Prueba
docker exec Synap_app python manage.py auditar_pipeline_mpr \
  --base-empresa=administranet1 \
  --desde=22/07/2026 --hasta=03/08/2026 \
  --host=181.174.198.194 --port=30804 \
  --output=/app/tmp_exports/audit_pipeline_administranet1_20260722_20260803.json

# Producción (solo lectura)
docker exec Synap_app python manage.py auditar_pipeline_mpr \
  --base-empresa=administranet \
  --desde=22/07/2026 --hasta=03/08/2026 \
  --host=181.174.198.194 --port=30804 \
  --output=/app/tmp_exports/audit_pipeline_administranet_20260722_20260803.json
```

| Parámetro | Rol |
|-----------|-----|
| `--base-empresa` | **Obligatorio.** `administranet` (prod) o `administranet1` (prueba). |
| `--desde` / `--hasta` | Rango inclusive (`dd/MM/yyyy` o ISO). |
| `--host` / `--port` | Opcional; si se omiten usa el pool Synap (`DB_HOST`). |
| `--output` | JSON de salida. |

## Qué valida por día

1. **Parte:** cabeceras/líneas aprobadas, `movimiento_fisico_ok`, OPP no-transición vs `cuerpostock`.
2. **CC:** totales, fab vs cls (art×op×turno), excesos/déficits, huérfanos sin parte, dups de clave, join a `movimiento_stock` y `cuerpostock`.
3. **Armado:** lotes por `fecha_realizado`, `mpr_armado_surtido_movimiento` → mstock OPA, cuerpos y fechas distintas.

Código: `mpr/auditoria_pipeline.py`, comando `mpr/management/commands/auditar_pipeline_mpr.py`.

**Nota:** en MPR, los mstock de CC suelen usar `tipo_mov=OPP` con detalle `Transición MPR…`. El comando los distingue de OPP “otros”.
