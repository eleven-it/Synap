# Especificación — relays catálogo mayoristapp → Synap

**Implementación:** `ecom.services.catalogo_rubro`, `ecom.services.catalogo_maestros`, `ecom.services.catalogo_lotes`, `ecom.services.catalogo_tacc`, `ecom.services.catalogo_mas_vendidos`, `ecom.services.catalogo_articulo`, `ecom.services.mayoristapp_session`, vistas `ecom.catalogo_relay_views`.  
**Permiso común:** `EcomMayoristappSessionPermission` (sesión con `user.base_empresa`).

---

## 1 — `relay-rubro.php`

**Fuente PHP:** `mayoristapp/relay-rubro.php`

- Requiere `sesion.inc.php` y `isset($_GET['ajax'])`.
- `idcategoria`: rubros con artículos `ecommerce='Si'`, primera fila `- todos -`.
- `idrubro`: subrubros vía join `articulo` + `subrubro` (solo subrubros con artículos).

| Método | Ruta |
|--------|------|
| GET | `/ecom/api/mayoristapp/catalogo/rubros/?idcategoria=<int>&ajax=1` |
| GET | `/ecom/api/mayoristapp/catalogo/subrubros/?idrubro=<int>&ajax=1` |

Respuesta: array JSON `{id, name}`.

---

## 2 — `relay-rubro-catalogo.php`

**Fuente PHP:** guarda `$_SESSION["buscaRubro"]` y `$_SESSION["claseLista"]="galeria"`.

**Synap:** `session["mayoristapp"]["busca_rubro"]` y `session["mayoristapp"]["clase_lista"]` (no mezclar con claves planas PHP).

| Método | Ruta | Cuerpo |
|--------|------|--------|
| POST | `/ecom/api/mayoristapp/catalogo/filtro-rubro-catalogo/` | JSON o form: `idr` |

Respuesta: `{"status": "ok"}`.

---

## 3 — Autocomplete artículos (`relay-stock-existencias.php`)

**Fuente PHP:** `buscarArticulosAutocomplete` (POST `autocomplete=1`, `term`).

Tabla `articulo`: columnas `IDArt`, `Codigo`, `nombre`, `id_manual`, `activo='Si'`.

| Método | Ruta | Cuerpo |
|--------|------|--------|
| POST | `/ecom/api/mayoristapp/catalogo/articulos/autocomplete/` | `autocomplete: 1`, `term: string` |

Respuesta: `[{ "id", "label", "value" }, ...]` (máx. 15 filas por defecto, tope 50).

**Nota:** el PHP original usa más acciones en el mismo archivo (`buscarStock`, depósitos, etc.); aquí solo el autocomplete.

---

## 4 — `relay-tipo-cliente.php` (subrubros)

**Fuente PHP:** `$_REQUEST['ajax']`, `idrubro`; con `tipoCliente` filtra por `articulo_tipo_cliente`.

| Método | Ruta |
|--------|------|
| GET | `/ecom/api/mayoristapp/catalogo/subrubros-tipo-cliente/?idrubro=<int>&ajax=1` |
| GET | mismo + `tipoCliente=<int>` (opcional) |

- Sin `tipoCliente`: lista desde maestro `subrubro` (paridad rama `else` del PHP).
- Con `tipoCliente`: join `articulo_tipo_cliente` (paridad rama con filtro).

---

## 5 — `relay-marca.php`

Listado de marcas con al menos un artículo `ecommerce='Si'`, `marca.anulado='No'`, `marca.ecommerce='Si'` (mismo criterio que rubros ecommerce).

| Método | Ruta |
|--------|------|
| GET | `/ecom/api/mayoristapp/catalogo/marcas/?ajax=1` |

Respuesta: `[{ "id", "name" }, ...]` (`CodMarca`, `NombreMarca` titulados).

---

## 6 — `relay-laboratorio.php`

Laboratorios con artículo ecommerce y `laboratorio.anulado='No'`.

| Método | Ruta |
|--------|------|
| GET | `/ecom/api/mayoristapp/catalogo/laboratorios/?ajax=1` |

Respuesta: `[{ "id", "name" }, ...]` (`CodLaboratorio`, `NombreLaboratorio`).

---

## 7 — `relay-proveedor.php`

Proveedores con artículo ecommerce; excluye `proveedor.Codigo = 1` (convención “ninguno” en AdministraNET).

| Método | Ruta |
|--------|------|
| GET | `/ecom/api/mayoristapp/catalogo/proveedores/?ajax=1` |

Respuesta: `[{ "id", "name" }, ...]` (`Codigo`, `Nombre`).

---

## 8 — `relay-lote.php`

**Fuente PHP:** `mayoristapp/relay-lote.php` (respuesta HTML con radios). Synap devuelve JSON.

Lotes con stock en depósito: tablas `lote`, `lote_stock` (`id_articulo`, `id_deposito`, `stock_lote > 0`, `anulado = 'No'`), orden por `fecha_vto_lote` ASC.

| Método | Ruta | Query |
|--------|------|--------|
| GET | `/ecom/api/mayoristapp/catalogo/lotes/?ajax=1` | `idArt`, `idDeposito` (enteros; alias `id_art` / `id_deposito`) |

Respuesta: lista de `{ id_lote, cod_lote, fecha_vto_lote, stock_total_lote, stock_lote, valor_seleccion }` donde `valor_seleccion` = `id_lote|stock_lote` (equivalente al `value` del radio PHP).

---

## 9 — `relay-tacc.php`

**Fuente PHP:** `relay-tacc.php` — si existe columna `articulo.sin_tacc`, devuelve `{"mensaje":"ok","valores":[...]}`; si no, `sinTacc`.

| Método | Ruta |
|--------|------|
| GET | `/ecom/api/mayoristapp/catalogo/tacc-opciones/?ajax=1` |

La comprobación de columna usa `information_schema` (misma semántica que `SHOW COLUMNS` en PHP).

---

## 10 — `relay-mas-vendidos.php` / bloque más vendidos

**Fuente PHP:** la consulta operativa está en `inventario/includes/mas-vendidos.php` (top por movimientos `stock` tipo `Venta` / `Venta TPV`, artículos ecommerce). El archivo `relay-mas-vendidos.php` delega en funciones; Synap implementa la consulta del include.

| Método | Ruta | Query (opcionales) |
|--------|------|---------------------|
| GET | `/ecom/api/mayoristapp/catalogo/mas-vendidos/?ajax=1` | `idcategoria`, `idrubro`, `idsubrubro`, `limit` (1–50, default 15) |

Respuesta: array JSON de filas con contador `cuantos`, datos de artículo y rubros/subrubro (subconsulta agregada para compatibilidad con `ONLY_FULL_GROUP_BY`).

---

## Pendientes / diferencias

- `relay-stock-existencias.php`: `buscarStock`, depósitos, paginación DataTables — no portados.
- `relay-rubro.php`: comentario de tipo de cliente en subrubros del primer script sigue cubierto por §4, no por `/subrubros/`.
- POST requiere CSRF en navegador (sesión Django estándar).

---

## 11 — Gaps catálogo (Fase C)

Pendientes de API Synap (priorizar según pantalla): `relay-art.php`, `relay-art-rapido.php`, `relay-articulo-remito.php`, `relay-stock-autocomplete.php`, stock completo en `relay-stock-existencias.php`.

**v1 Synap:** §5–§10 (marca, laboratorio, proveedor, lote, tacc, más vendidos); revisar paridad fina frente al PHP del repo `administraNET-ecom`.

Índice global: [MAYORISTAPP_SPEC_INDICE.md](./MAYORISTAPP_SPEC_INDICE.md).
