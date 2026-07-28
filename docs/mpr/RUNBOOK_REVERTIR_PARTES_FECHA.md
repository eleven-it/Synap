# Runbook — reset total de partes por fecha (dry-run)

Comando operativo para **inventariar** el cutover de partes MPR de una o más fechas:
**eliminar TODOS** los `mpr_parte` del día + revertir OPP/stock. No modifica la base
hasta que `--apply` esté habilitado (hoy bloqueado).

## Comando

```bash
docker exec Synap_app python manage.py revertir_partes_fecha \
  --base-empresa=administranet \
  --fecha=22/07/2026
```

Cutover Best Sox (4 fechas) en LAN planta:

```bash
docker exec Synap_app python manage.py revertir_partes_fecha \
  --base-empresa=administranet \
  --fecha=22/07/2026 --fecha=23/07/2026 --fecha=24/07/2026 --fecha=27/07/2026 \
  --host=192.168.0.2 \
  --port=30804
```

También acepta `--fecha=2026-07-22` o CSV: `--fecha=22/07/2026,23/07/2026`.

## Parámetros

| Parámetro | Default | Descripción |
|-----------|---------|-------------|
| `--base-empresa` | `administranet` | Nombre de la BD MySQL. |
| `--fecha` | *(obligatorio)* | Fecha de producción (`YYYY-MM-DD` o `dd/MM/yyyy`). Repetible o CSV. |
| `--host` / `--port` | — | Conexión directa (solo lectura). Sin esto usa el pool Synap. |
| `--apply` | — | **Bloqueado.** Reset total pendiente de OK explícito. |

## Decisión cutover (28/07/2026)

- **No** conservar el 1.er parte: la grilla histórica no es fuente de verdad (INSERT + precarga suma).
- Apply futuro: revertir OPP/stock de **todos** los UUID del día → borrar líneas/ajustes/cabeceras → 0 partes → planta recarga con upsert/borrador.
- Fechas: 22, 23, 24 y 27/07/2026.

## Hallazgo auditoría LAN `administranet`

- **`mpr_transicion_lote`:** **0 filas** en toda la base (ningún CC registrado).
- Partes `fecha_produccion=22/07/2026`: 21 cabeceras; mayoría con OPP físico.
- Sí hay **salidas posteriores por motivo «Ajuste»** en algunos artículos: el apply futuro debe inventariarlas.

## Qué muestra el dry-run

1. **Partes (`mpr_parte`)** del día a **eliminar**: id, uuid, turno, físico, Σ pares.
2. **`movimiento_stock` OPP-parte** ligados por UUID.
3. **Σ Entrada en `stock`** por artículo de esos OPP.
4. **`mpr_transicion_lote` (CC)** por fecha y por artículos del día.
5. Advertencia si hay CC.

## Modo apply (futuro)

Hoy **no** se escribe en MySQL. Cuando se habilite `--apply` (OK explícito):

- si hay CC: revertir CC primero;
- revertir OPP-parte + ledgers;
- borrar **todos** los `mpr_parte` / líneas / ajustes de la fecha;
- verificar Fabricando post-apply.

## Referencias

- Partes y OPP: `docs/mpr/OPP_PARTE_PRODUCCION.md`
- CC: `docs/mpr/TRANSICIONES_LOTE.md`
