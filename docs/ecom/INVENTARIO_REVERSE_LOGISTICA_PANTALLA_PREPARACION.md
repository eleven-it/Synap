# Inventario e ingeniería inversa — `logistica_pantalla_preparacion.php`

## 1. Archivos legado analizados

| Archivo | Rol |
|---------|-----|
| `mayoristapp/logistica_pantalla_preparacion.php` | Página HTML: título «Estado de Pedidos», selector de sucursal + domicilio, reloj, tema claro/oscuro, botón cerrar → `escritorio.php`, tres columnas Kanban vacías al inicio. |
| `mayoristapp/ajax/json_pantalla_pedidos.php` | API JSON: sucursales y datos por columna. |

## 2. Flujo en PHP

1. Al cargar, `fetch('ajax/json_pantalla_pedidos.php?sucursales=1')` obtiene sucursales y rellena el `<select>`; selecciona la primera por defecto y muestra domicilio.
2. El usuario pulsa **Iniciar** (generado por JS) para arrancar `setInterval(actualizarTodasLasColumnas, 10000)`; antes la pantalla queda en pausa (solo botón Iniciar).
3. `actualizarTodasLasColumnas` hace GET a `ajax/json_pantalla_pedidos.php?cod_sucursal=...` (sin parámetro `ajax` en la query; el PHP no exige `ajax` para el Kanban).
4. Respuesta JSON con tres arrays; el JS asigna:
   - `data.en_preparacion` → lista DOM `#en-preparacion-list` (columna titulada **En Preparación**),
   - `data.preparado` → `#preparado-list` (columna **Preparado**),
   - `data.en_remito` → `#en-remito-list` (**En Remito**).
5. Orden visual en el HTML: **Preparado** (izquierda) | **En preparación** (centro) | **En remito** (derecha).

## 3. Consultas SQL (PHP)

Resumen de `json_pantalla_pedidos.php`:

- Filtro sucursal: `AND pedido.CodSucursal = $codSucursal` si viene `cod_sucursal`.
- **En preparación:** `Estado = 'En preparacion'` (sin tilde), join `usuarios` por `id_usuario_preparacion`, orden `fecha_hora_fin_preparacion ASC`.
- **Preparado:** `Estado = 'Preparado'`; el JSON solo empuja `comprobante` (no `usuario`).
- **En remito:** joins `rem_ped` y `comp_ped` remito; `rem_ped.Anulado='No'`, `pedido.Estado='En remito'`, `remito.Estado='Pendiente'`; orden `remito.fecha_control ASC`.

## 4. Diferencias y decisiones en Synap

| Tema | PHP | Synap |
|------|-----|--------|
| Estado «en preparación» | Solo `En preparacion` | `IN ('En preparacion', 'En preparación')` para tolerar datos con tilde. |
| Parámetro `ajax` en API Kanban | No requerido | Requerido `ajax=1` para alinear con otras APIs ecom y validación explícita. |
| Auto-refresh | 10 s fijos tras «Iniciar» | Intervalo configurable (30 s … 2 h) + tiempo real opcional (localStorage), patrón reportes. |
| Cierre de conexión en JSON | `mysqli_close($conexion)` sobre el recurso compartido | No aplica: pool MySQL en Django. |

## 5. Razón y objetivo de la pantalla (resumen ejecutivo)

**Razón:** en depósito/logística hace falta visibilidad **inmediata** del pipeline de pedidos (PED) antes de facturación: qué lotes ya están listos para entregar/remitir, cuáles están siendo preparados (idealmente con operario asignado) y cuáles ya pasaron a remito pendiente de cierre.

**Objetivo:** reducir consultas dispersas y dar una **pantalla única** tipo tablero (adecuada para monitor o tablet) alineada al flujo de estados en `comp_ped` y `rem_ped`, coherente con el módulo de preparación en VB6 (Pedido_prep / estados documentados en validación de pedidos pendientes).

No sustituye el informe tabular **Pedidos pendientes** (`pedidos-pendientes` en `reports`): ese listado es **analítico** por fechas; **Estado de pedidos** es **operativo** por estado y sucursal.
