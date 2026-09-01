# Operación del módulo Mtrix

App Django `mtrix` en `/mtrix/`. Exporta sell-out AdministraNET al portal MTRIX con el **contrato CSV congelado** de Accera V.3.5 (`Principal.bas`).

## Permisos

| Código | Uso |
|--------|-----|
| `mtrix.ver` | Hub, preview, listado y detalle de jobs, descarga |
| `mtrix.configurar` | Configuración (exportación, SFTP, programador) y prueba de conexión |
| `mtrix.generar` | Disparar generación on-demand |
| `mtrix.enviar_sftp` | Enviar o reenviar CSV por SFTP |
| `mtrix.*` | Acceso total al módulo |

Tras desplegar, sincronizar el catálogo Synap (`sincronizar_permisos` / seed de `PERMISOS_POR_MODULO`) y asignar los códigos al puesto.

## Encoding

Los CSV se emiten en **latin-1** (`errors=replace`), igual que la conexión VB6 `CHARSET=latin1`. El preview en pantalla no cambia ese archivo: solo formatea fechas `dd/MM/yyyy` y textos para lectura.

Nombre: `{TIPO}-INT{ddmmyyyyhhmmssSSS}.csv` (sin versión de layout). Delimitador `;`. Header en la línea 1.

Una corrida genera **como máximo un archivo por categoría** (CI, PD, ES, VD, FV). La lista de proveedores filtra PD/ES/VD con `IN (...)`; no produce un CSV por código.

En **Configuración**, los proveedores se eligen con un **buscador predictivo** (nombre, código o CUIT). Vacío = todos. Se guardan como códigos separados por coma (`5` o `23,29,31`).

## Cron del host

Igual que `backup_tick`: el programador vive en la UI (`/mtrix/configuracion/`) y el host consulta cada minuto.

```cron
* * * * * docker exec Synap_app python manage.py generar_mtrix --scheduled
```

Variante horaria (si el cron no puede ir al minuto):

```cron
0 * * * * docker exec Synap_app python manage.py generar_mtrix --scheduled --match-hour-only
```

Reglas:

- `programador_activo` debe estar Activo y `schedule_json` con `{dow: 0=lunes, time: HH:MM}`.
- Dedupe ~50 minutos (no lanza otro job cron si ya hubo uno reciente).
- Si hay un job `queued` o `running` de esa `base_empresa`, se omite.
- `sftp_enviar_automatico` default **No**. El cron solo sube SFTP si el toggle está Activo. On-demand siempre pide confirmación en modal Synap.

On-demand (UI o comando):

```bash
docker exec Synap_app python manage.py generar_mtrix --job-id=<uuid>
```

Fechas no personalizadas: `CURDATE()` de MySQL de la empresa, no el reloj del contenedor.

## CEP (CI y VD)

Diversey **no acepta CEP vacío ni `0`**. Si el departamento del cliente no tiene `cod_postal` válido (vacío, NULL, `0`, solo ceros, `NA` o menos de 4 dígitos), Synap completa con **`9400`** — el CEP más frecuente en la base (SMART CLEAN / Río Gallegos). Un CEP real (p. ej. `9405`) se conserva tal cual.

## CUIT y marca de agua de VD

- **CUIT empresa** (`datosempresa.CUIT`): se usa como `CNPJ_DISTRIBUIDOR` y, con prefijo `AR`, como `CNPJ_FORNECEDOR`. No se carga en la UI.
- **CI / PD / ES / FV:** cada corrida regenera el snapshot completo. **FV** emite una sola línea por CUIT (`IDENTIFICACAO CLIENTE`); VB6 también diferenciaba por `cliente.Codigo`.
- **VD:** primera corrida automática sin marca de agua → `Días a procesar`. Después → desde el último `fecha_hasta` enviado por SFTP OK (solape de 1 día) hasta hoy.
- La marca (`last_vd_enviado_hasta`) **solo avanza** si el SFTP de esa corrida terminó OK (y no retrocede si se reenvía un rango más viejo).
- **Fecha personalizada** aplica a Generar ahora y al preview. El programador (cron) la ignora.

## Artefactos

`MEDIA_ROOT/mtrix/<base_empresa>/<job_id>/*.csv`

Jobs y config en PostgreSQL (`MtrixConfig`, `MtrixJob`, `MtrixArtifact`). Solo lectura MySQL AdministraNET.

Credenciales SFTP: Fernet con pepper `synap-mtrix-sftp` (no reutiliza `BACKUP_SFTP_*`).

## Rollback

1. Quitar la entrada cron `generar_mtrix --scheduled` (o desactivar el programador en la UI).
2. Quitar el ítem de menú / desactivar visibilidad si hace falta.
3. Revertir la migración Django `mtrix` (`migrate mtrix zero`) y quitar `mtrix` de `INSTALLED_APPS` y `urls.py`.
4. Los CSV ya generados en `MEDIA_ROOT/mtrix/` se pueden archivar o borrar a mano; no hay ALTER de tablas VB6 que deshacer.
