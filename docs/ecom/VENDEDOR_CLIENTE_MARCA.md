# Vendedor → Cliente → Sucursal → Marca (territorio comercial)

**Change:** `ecom-pedidos-hub-kanban-masivo-sucursales` (+ extensión relación)  
**Ruta config:** `/ecom/mayoristapp/config/vendedor-cliente-marca/`  
**Fecha:** 16/07/2026

## Regla de negocio

Relación `(CodViajante, id_cliente, id_cliente_domicilio, CodMarca)`.  
**Unique activo:** `(id_cliente, id_cliente_domicilio, CodMarca)` → un solo vendedor por sucursal.  
La misma marca en el mismo cliente puede ir a **distinto vendedor** si es **otra sucursal**.

Ejemplo válido:

- Vendedor 1 → Cliente 1 → Sucursal A → Marca X  
- Vendedor 2 → Cliente 1 → Sucursal B → Marca X  

Inválido: Vendedor 2 → Cliente 1 → Sucursal A → Marca X (conflicto; informar dueño).

**Visibilidad de cliente** para un vendedor: tiene ≥1 relación activa (EXISTS sin filtrar sucursal).

## Tabla MySQL (legacy por empresa)

`ecom_vendedor_cliente_marca` — DDL:

- Instalación nueva: `ecom/sql/001_ecom_vendedor_cliente_marca.sql`
- Upgrade bases existentes: `ecom/sql/002_ecom_vendedor_cliente_marca_sucursal.sql` (vía catálogo idempotente)

Proveedor catálogo: `ecom_vendedor_cliente_marca`.

Columna clave: `id_cliente_domicilio` (`cliente_domicilio.id_cliente_domicilio`; `0` = edge case sin domicilios).

### Migración de ternas existentes (bases ya pobladas)

Al ejecutar el proveedor en **Archivo → Migración esquema MySQL**:

1. Añade `id_cliente_domicilio` si falta.
2. Reemplaza unique `uk_evcm_cliente_marca_activo` por `uk_evcm_cliente_sucursal_marca_activo`.
3. Por cada fila activa con `id_cliente_domicilio=0`:
   - Si el cliente tiene domicilios activos (`anulado='No'`): inserta una fila por domicilio y **anula** la fila sin sucursal.
   - Si el cliente **no** tiene domicilios: conserva una fila con `id_cliente_domicilio=0` (documentado como edge case).

## Feature flag

`ecom_usa_vcm_ternas`: `Si` | `No` | `auto` (default). Semántica sin cambios.

## Permisos

| Key | Uso |
|-----|-----|
| `ecom.config_vendedor_cliente_marca` | ABM relaciones (supervisor ventas) |

## Endpoints API

| Método | Path | Descripción |
|--------|------|-------------|
| GET | `/ecom/api/mayoristapp/vendedor-cliente-marca/ternas/` | Lista (filtros `CodViajante`, `id_cliente`, `id_cliente_domicilio`, `solo_activas`; límite predeterminado `5000`, máximo `20000`) |
| POST | `/ecom/api/mayoristapp/vendedor-cliente-marca/crear/` | Alta con `id_cliente_domicilio` / `ids_cliente_domicilio` y `CodMarca` / `CodMarcas` (cartesiano sucursales × marcas); **409** `code=conflicto_marca` + `dueno` (simple) o `resumen` (lote); **201** si alguna creada; **200** si solo ya existían |
| POST | `/ecom/api/mayoristapp/vendedor-cliente-marca/anular/` | Soft-delete `{id}` o lote `{ids: [...]}` |
| GET | `.../vendedores/`, `.../clientes/`, `.../sucursales/?id_cliente=`, `.../marcas/` | Búsqueda predictiva `?q=` |

UI: `/ecom/mayoristapp/config/vendedor-cliente-marca/` — formulario con 4 combobox: Vendedor, Cliente, **Sucursal** (multi-select: una o más sucursales del cliente; chips + checkboxes en listado; botones Todas/Ninguna), **Marca** (multi-select, mismo patrón). Un clic en **Asignar** crea el cartesiano (mismo vendedor y cliente × cada sucursal × cada marca).

**Paquete PUM / PUS / PUW:** esas tres marcas se asignan siempre juntas. En el alta, marcar o desmarcar una selecciona o quita las tres. En datos existentes, si un vendedor tiene al menos una de las tres en una sucursal, deben estar las tres en esa misma cuaterna.

**Anulación:** **Anular** en la hoja (una relación) o selección múltiple (checkbox en hoja, en encabezado de vendedor/cliente/sucursal, o «todas»). Barra **Anular seleccionadas** + modal Synap. API: `{id}` o `{ids: [...]}`.

## Completitud paquete PUM / PUS / PUW (01/09/2026)

**Entorno:** Server2 `181.174.198.194:30804`, base `administranet`.  
**Códigos:** PUM=`13`, PUS=`14`, PUW=`15`.

Criterio: por cada `(CodViajante, id_cliente, id_cliente_domicilio)` con al menos una de las tres activa, completar las que falten al mismo vendedor. Unique intacto; no se pisó a otro dueño.

| Métrica | Valor |
|---------|-------|
| Grupos incompletos antes | 170 |
| Filas insertadas | 316 |
| Conflictos (otro vendedor) | 0 |
| Grupos incompletos después | 0 |
| Filas activas del trío después | 1200 |

`usuario_mod = synap-vcm-paquete-pu`.

**Listado de relaciones:** árbol colapsable de 4 niveles `Vendedor → Cliente → Sucursal → Marca` (cada nivel con chevron y badge «N relaciones»; **inicia siempre contraído**; estado en `gruposColapsados` con claves string `v:<cod>`, `v:<cod>:c:<idc>`, `v:<cod>:c:<idc>:s:<idd>`), armado client-side con `arbolCuaternas()`/`filasArbol()` y orden natural (`cmpNatural`) en cada nivel; columnas de la hoja `Marca | Alta | (acciones)` con tabulación alineada al texto de Sucursal. Botones **Expandir todo** / **Contraer todo** (mismo patrón que informes VO). Se muestra solo el dato legible, **sin códigos entre paréntesis ni índices** (`nombre_viajante`, `nombre_cliente`, `nombre_marca`); en sucursal, si no hay domicilio (id 0/vacío) o la etiqueta es solo un índice, se muestra «Sin sucursal». Los 4 combobox y el filtro de vendedor usan búsqueda predictiva con orden natural, recarga al borrar el texto y flecha abajo para traer todo el catálogo (`onInput`/`flechaAbajo`).

La pantalla de configuración solicita explícitamente `limit=10000` para cargar todas las relaciones activas del árbol.

## Filtros operativos

| Flujo | Comportamiento |
|-------|----------------|
| Pedido masivo — clientes | ≥1 relación activa con viajante efectivo |
| Pedido masivo — sucursales | Solo domicilios con ≥1 relación (vendedor, cliente) si VCM activo |
| Pedido masivo / simple — marcas | Con `id_cliente_domicilio`: marcas de esa sucursal; sin domicilio: **unión** de todas las sucursales del par vendedor-cliente |
| Pedido masivo — import Excel | Cada celda con packs > 0 exige cuaterna activa (vendedor del borrador, cliente, sucursal de la columna, marca del artículo). Sucursal o marca fuera de territorio → error, no se importa. |
| Carrito simple `agregar_item` | Valida marca contra relaciones; sin domicilio en sesión usa unión |

Ver también `docs/ecom/PEDIDO_MASIVO_SUCURSALES.md`.

## Carga masiva desde Excel (producción `administranet`)

**Fecha:** 22/07/2026  
**Fuente:** `vendedor_cliente_marca_unicos.xlsx` (3 columnas: Nombre vendedor, Nombre cliente, Marca).  
**Script:** `tmp/cargar_vcm_administranet_prod.py` (misma lógica que la carga en `administranet1`).

### Criterios

- Resolución solo por **nombre** (cliente y marca); no se usan códigos BEST.
- Se omiten clientes faltantes, nombres ambiguos y marcas no confirmadas (en esta corrida: **BC**, **DM**).
- Cada par cliente–marca se expande a **todas** las sucursales activas del cliente.
- Gustavo Ursela: 0 pares confirmados (todos los clientes faltaban) → no se creó viajante.

### Resultado en `administranet`

| Vendedor | CodViajante | Relaciones activas |
|----------|-------------|--------------------|
| Alejandro Bruschini | 26 | 26 |
| Diego Cannarella | 27 | 8 |
| Esteban Carrizo | 28 | 170 |
| Felipe | 29 | 4 |
| Francisco Balantzian | 30 | 677 |
| Guillermo Bruschini | 31 | 13 |
| Guillermo Carraccioli | 32 | 1 |
| Miguel Diez | 33 | 26 |
| Raul Cabrera | 34 | 32 |
| Ricardo Lozada | 35 | 20 |
| Walter esquivel | 36 | 23 |

- **Filtro Excel:** 195 confirmadas, 34 cliente faltante, 8 ambiguo, 2 marca.
- **Francisco:** usuario `francisco` (id=7) ya existía; se creó viajante 30 y se vinculó (`CodViajante` pasó de 2 → 30). Se actualizaron 3 filas G→S. Tres ternas DABRA/PUM que estaban en viajante genérico 2 se reasignaron a 30.
- **Resto de vendedores:** solo alta de viajante (sin usuario de login), igual que en pruebas.

## Reasignación de nombres y VCM (18/08/2026)

**Motivo:** tras el cutover coexistían placeholders `Vendedor X` (con clientes/ventas) y fichas con nombre real (nomenclatura del sistema anterior, con VCM). Se conservan los `CodViajante` de los placeholders; no se reescriben pedidos ni facturas.

**Entorno:** Server2 `181.174.198.194:30804`, base `administranet`.

**Criterio de mapeo:** por `viajantes.Nombre` (el nro del Excel no es `CodViajante`; `CodViajante=1` es `-Ninguno-`).

| Nombre vigente | Destino (en uso) | Origen (`NO USAR`) | VCM movidas |
|----------------|------------------|--------------------|-------------|
| Diego Cannarella | 4 | 27 | 8 |
| Francisco Balantzian | 6 (ya tenía el nombre) | 30 `Francisco Balantzian (NUEVO)` → `Francisco Balantzian NO USAR` | 677 |
| Walter Esquivel | 8 | 36 | 23 |
| Alejandro Bruschini | 9 | 26 | 26 |
| Felipe Rosales | 11 | 29 | 4 |
| Miguel Diez | 12 | 33 | 26 |
| Esteban Carrizo | 14 | 28 | 170 |
| Ricardo Lozada | 15 | 35 | 20 |
| Guillermo Bruschini | 16 | 31 | 13 |
| Raul Cabrera | 18 | 34 | 32 |
| Guillermo Caraccioli | 24 | 32 (DB: `Carraccioli`) | 1 |
| Gustavo Ursela | 25 (`Vendedor 28`) | no existía ficha origen | 0 |

**Operación (transacción):**

1. `UPDATE ecom_vendedor_cliente_marca.CodViajante` origen → destino (1000 activas; unique cliente+sucursal+marca intacto).
2. Origen: `Nombre` → `{vigente} NO USAR`. Destino: `Vendedor X` → nombre vigente.
3. Usuario `francisco` (`id_usuario=7`): `usuarios.CodViajante` 30 → 6, para que el login vea el territorio vigente.

**No se tocó:** `cliente.CodViajante`, comprobantes, ni alta de los 11 usuarios de login que aún no existen.

**Verificación post:** VCM activas=1000 en destinos; orígenes con VCM=0; `ecom_usuario_viajante` sigue vacía.
