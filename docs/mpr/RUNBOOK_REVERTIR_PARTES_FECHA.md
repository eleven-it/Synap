# Runbook — reset total de partes por fecha

Comando operativo para **inventariar** y (con confirmación) **aplicar** el cutover de
partes MPR: **eliminar TODOS** los `mpr_parte` del día + anular OPP/stock.

## Dry-run

```bash
docker exec Synap_app python manage.py revertir_partes_fecha \
  --base-empresa=administranet1 \
  --fecha=22/07/2026 --fecha=23/07/2026 --fecha=24/07/2026 --fecha=27/07/2026 \
  --host=192.168.0.2 \
  --port=30804
```

## Apply (pruebas)

```bash
docker exec Synap_app python manage.py revertir_partes_fecha \
  --base-empresa=administranet1 \
  --fecha=22/07/2026 --fecha=23/07/2026 --fecha=24/07/2026 --fecha=27/07/2026 \
  --host=192.168.0.2 \
  --port=30804 \
  --apply --confirmar=RESET
```

- `--confirmar=RESET` es obligatorio con `--apply`.
- Base `administranet` (producción) está bloqueada salvo `--forzar-produccion`.
- Si hay filas CC (`mpr_transicion_lote`) en la fecha, el apply **aborta**.

## Qué hace el apply

1. Inventario (igual que dry-run).
2. Por cada OPP-parte del día: ajusta `stock_deposito` (`saldo += Salida - Entrada`), marca `stock` y `movimiento_stock` con `anulado='Si'`.
3. Limpia `lista_produccion_historico` por `codigo_movimiento_mstock` (o `codigo_movimiento` si existiera).
4. `DELETE` ajustes, líneas y cabeceras `mpr_parte` de la fecha.
5. Verifica 0 partes residuales.

## Parámetros

| Parámetro | Default | Descripción |
|-----------|---------|-------------|
| `--base-empresa` | `administranet` | Nombre de la BD MySQL. |
| `--fecha` | *(obligatorio)* | Fecha de producción. Repetible o CSV. |
| `--host` / `--port` | — | Conexión directa. |
| `--apply` | — | Ejecutar escritura. |
| `--confirmar` | — | Debe ser `RESET` con `--apply`. |
| `--forzar-produccion` | — | Permite apply sobre `administranet`. |

## Decisión cutover (28/07/2026)

- Reset total (no conservar 1.er parte). Fechas: 22, 23, 24 y 27/07/2026.
- Validar primero en `administranet1`; recién después evaluar producción.

## Referencias

- Partes y OPP: `docs/mpr/OPP_PARTE_PRODUCCION.md`
- CC: `docs/mpr/TRANSICIONES_LOTE.md`
