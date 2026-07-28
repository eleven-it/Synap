# Runbook — revertir partes por fecha (dry-run)

Comando operativo para **inventariar** la reversión de partes MPR de una fecha concreta, sin modificar la base de datos.

## Comando

```bash
docker exec Synap_app python manage.py revertir_partes_fecha \
  --base-empresa=administranet \
  --fecha=22/07/2026
```

LAN planta (si el pool Synap no apunta a la misma MySQL con MPR):

```bash
docker exec Synap_app python manage.py revertir_partes_fecha \
  --base-empresa=administranet \
  --fecha=22/07/2026 \
  --host=192.168.0.2 \
  --port=30804
```

También acepta `--fecha=2026-07-22`.

## Parámetros

| Parámetro | Default | Descripción |
|-----------|---------|-------------|
| `--base-empresa` | `administranet` | Nombre de la BD MySQL. |
| `--fecha` | *(obligatorio)* | Fecha de producción (`YYYY-MM-DD` o `dd/MM/yyyy`). |
| `--host` / `--port` | — | Conexión directa (solo lectura). Sin esto usa el pool Synap. |
| `--apply` | — | **Bloqueado.** Rechaza con: *Apply deshabilitado hasta completar desarrollo; solo dry-run.* |

## Hallazgo auditoría 28/07/2026 (LAN `administranet`)

- **`mpr_transicion_lote`:** **0 filas** en toda la base (ningún CC registrado).
- Partes `fecha_produccion=22/07/2026`: 21 cabeceras; 20 con OPP físico (~36.444 pares Entrada a Producción).
- No hay CC a revertir antes de los partes en este entorno.
- Sí hay **salidas posteriores por motivo «Ajuste»** en algunos artículos (p. ej. 1459 −480): el apply futuro debe inventariarlas y decidir si compensar o dejarlas (no son CC).

## Qué muestra el dry-run

1. **Partes (`mpr_parte`)** del día: id, uuid, turno, `movimiento_fisico_ok`, Σ pares (líneas + ajustes).
2. **`movimiento_stock` OPP-parte** cuyo `detalle` contiene el UUID de cada parte (`OPP-parte {uuid} desde MPR`).
3. **Σ Entrada en `stock`** por artículo de esos movimientos OPP.
4. **`mpr_transicion_lote` (CC):**
   - filas con la misma `fecha_produccion`;
   - conteo agregado de CC de los artículos de esos partes en **cualquier** fecha (con desglose por fecha).
5. **Advertencia** si hay CC: un apply futuro debe revertir clasificación **antes** que los partes (no existe aún `anular_cc` en producto).

## Modo apply (futuro)

Hoy **no** se escribe en MySQL. Cuando se habilite `--apply` (solo tras desarrollo completo), deberá:

- si hay CC: revertir CC y MSTOCK Semi/2da/Scrap → Producción primero (capacidad a implementar);
- luego revertir OPP-parte (salida compensatoria / anulación) y ledgers (`mpr_parte_ajuste`, `mpr_parte_linea`, `mpr_parte`);
- verificar Fabricando post-apply (sube al bajar `partes_acumulados`).

Hasta entonces, usar solo dry-run.

## Referencias

- Scripts de auditoría previos: `tmp/diag_partes_2207.py`, `tmp/audit_cc_partes_2207.py`
- Partes y OPP: `docs/mpr/OPP_PARTE_PRODUCCION.md`
- CC: `docs/mpr/TRANSICIONES_LOTE.md`
