# Bugfix VB6 — Módulo artículos ensamblados (BOM) y borrado de artículos

Fecha: 21/07/2026 · Sesión de debug `89c516` · Bases afectadas por el saneo de datos: `administranet` y `administranet1`.

## Contexto

La ingeniería inversa del módulo VB6 de artículos terminados y recetas (`En_abm.frm`, `En_CargaAbm.frm`, `En_abmDef.frm`) detectó tres causas raíz de inconsistencias de datos, confirmadas con evidencia en ambas bases (35 `en_abm` activos sin artículo, 69 líneas de fórmula con insumo inexistente y duplicados activos por nombre):

| Bug | Causa | Ubicación original |
|---|---|---|
| A | Borrado físico de `articulo` validando solo movimientos en `stock`, sin verificar referencias BOM | `Sub Eliminar()` en `AltaArticulo.frm` y `ABMArticulo_seleccion.frm` |
| B | Alta en dos fases: la cabecera `en_abm` se comitea en `En_CargaAbm` y el `articulo` recién se crea si el usuario completa después «Definición de fórmula» (F4). Si no lo hace, queda un huérfano | `En_CargaAbm.Aceptar_Click` + `En_abmDef.Cancelar_Click` |
| C | Validación de nombre duplicado solo en una de las tres ramas de guardado, sin TRIM, sin escape de comillas y sin guarda anti doble click | `En_CargaAbm.Aceptar_Click` |

## Saneo de datos aplicado (previo al fix)

En ambas bases (`administranet` y `administranet1`), con scripts auditables en `tmp/`:

- 30 artículos terminados creados (IDArt 1549–1578, códigos `1.1.1541`–`1.1.1570`, `id_manual='-'` pendiente de completar por negocio), sin carga de stock (filas `stock_deposito` en 0).
- 5 conjuntos reutilizan artículos existentes (IDArt 1415, 1219, 592).
- Purga física de 35 cabeceras `en_abm` + 68 líneas de fórmula + 5 líneas rotas de los conjuntos 82/97/188.
- Verificación final: 0 `en_abm` sin artículo, 0 líneas rotas, 0 duplicados activos.

## Fixes VB6 (formularios de `administraNET.vbp`)

Los `.frm` son ISO-8859-1 con CRLF; los parches se aplicaron preservando encoding y fin de línea.

### Bug A — `AltaArticulo.frm` y `ABMArticulo_seleccion.frm` (`Sub Eliminar`)

Antes del `DELETE FROM articulo` se agregan dos validaciones bloqueantes:

1. El artículo es **insumo** de fórmulas activas (`en_abm_formula.anulado='No'` con `en_abm.anulado='No'`) → mensaje con la cantidad de fórmulas afectadas.
2. El artículo es el **producto de un ensamblado activo** (`articulo.id_en_abm` → `en_abm.anulado='No'`) → exige anular primero el ensamblado.

### Bug B — flujo de alta encadenado + compensación

- `En_CargaAbm.Aceptar_Click` (alta manual): tras el commit de la cabecera captura el `id_en_abm` generado y **abre automáticamente `En_abmDef`** (definición de fórmula) para ese registro, evitando que el alta quede a mitad de camino.
- `En_abmDef.Cancelar_Click`: si es un alta (`modificacion="No"`, `Val(IDArt)=0`) y se cancela, ofrece **eliminar el encabezado incompleto**. El `DELETE` es defensivo: solo borra si el `en_abm` sigue sin artículo asociado y sin fórmula guardada. Nota de tipos: `IDArt` es `Public ... As String`, se compara con `Val(IDArt & "")` para evitar *Type Mismatch*.

### Bug C — validación de duplicados unificada

- Nueva `Private Function ExisteNombreEnAbm(nombre, idExcluir)` en `En_CargaAbm.frm`: compara con `TRIM`, escapa comillas simples, excluye el propio registro en modificación y tiene su propio `On Error GoTo ManejoError` con `Principal.Guardar_Error`.
- Se invoca en las **tres ramas** de `Aceptar_Click`: alta manual, alta desde ABM Artículo (`DeArtaArtE="Si"`, antes sin validación) y modificar (antes se podía renombrar a un nombre existente).

### Reaplicación v2 (21/07/2026, tarde)

La primera aplicación se **reversó por completo** (bloque a bloque, verificado sin restos) tras un reporte de rotura, y se reaplicó una versión v2 conservadora con estas diferencias:

- Textos nuevos 100% ASCII (sin acentos) para eliminar todo riesgo de encoding ANSI.
- Se quitó la guarda `Static enProceso` anti doble click (7 puntos de contacto en `Aceptar_Click`, riesgo/beneficio desfavorable: tras `Unload Me` el segundo click no llega al formulario).
- Validación estructural automática post-parche: sección de diseño byte a byte intacta (líneas `Object=`, bloques `Begin/End`, `BeginProperty/EndProperty` balanceados), `VERSION 5.00` al inicio, `Sub/Function` balanceados, sin constructos .NET, CRLF puro, sin BOM UTF-8, `.frx` sin tocar (solo cambios de texto en sección de código).
- Scripts: `tmp/patch_vb6_bom_v2.py` (aplicar) y `tmp/revert_vb6_bom.py` (reversa de v1).

## Pendientes relacionados (Synap)

- Validación de nombre duplicado en `crear_conjunto_bom` (`/mpr/bom/`).
- Salvaguarda en `delete_product` para artículos referenciados en `en_abm_formula` o vinculados a `en_abm`.
- Duplicado preexistente en `articulo` (IDArt 1346 vs 1352, «2400 TM Atomik Media Stripe Negro 2P») **resuelto 25/08/2026**: receta BOM `id_en_abm=228` unificada en IDArt **1346** (artículo con stock/movimientos); IDArt **1352** eliminado. Comando: `python manage.py unificar_articulo_duplicado_bom --base-empresa <base> --id-destino 1346 --id-origen 1352 --id-en-abm 228`.

## Seguimiento 23/07/2026 — artículo 938382-16 (`administranet`)

Caso reportado como «8382-16»: `IDArt=1219` (`CodArtProv=938382-16 T110`) apuntaba a `id_en_abm=292` sin componentes; además había cabeceras duplicadas vacías `181`, `290`, `291`.

Saneo (solo anulación, sin borrar ni tocar el artículo):

| `id_en_abm` | Acción |
|-------------|--------|
| 181, 290, 291 | `anulado='Si'` (duplicados vacíos, sin artículo armado ni fórmula) |
| **292** | Se deja **activa** y enlazada a 1219 para recargar la fórmula en VB6 |

El bug de alta/duplicados en formularios VB6 ya estaba corregido (sección anterior). Negocio: cargar insumos en definición de fórmula de la receta **292**.

### Ajuste posterior (mismo día)

Para empezar limpio desde VB6: `articulo` **1219** → `ensamblado='No'`, `id_en_abm=NULL`; cabecera **292** → `anulado='Si'`. Sin artículos apuntando a 292.
