# Especificación — `relay-ventas-netas.php` y `relay-ventas-netas-gerencia.php`

**Fuente:** administraNET-ecom `mayoristapp/` (lectura integral por secciones; ~4555 y ~5353 líneas respectivamente).  
**Destino migración:** app `reports` en Synap (no duplicar lógica ya cubierta por reportes de ventas netas existentes; cruzar con [`reports`](../../reports/) antes de implementar).  
**Relacionado:** [REVERSE_ENGINEERING.md](./REVERSE_ENGINEERING.md), [SPEC.md](./SPEC.md), [SPEC_PRECIOS.md](./SPEC_PRECIOS.md) (precios de artículos; estos relays operan sobre **movimientos / cuenta corriente / stock**, no sobre el calculador de lista de precios).

---

## A.1 — Parámetros de entrada

Ambos scripts exigen `require_once 'sesion.inc.php'` (sesión PHP activa). El handler AJAX principal comprueba **`ajax`** en la petición.

### `relay-ventas-netas.php`

| Parámetro | Método | Tipo PHP | Obligatorio | Descripción |
|-----------|--------|----------|-------------|-------------|
| `ajax` | GET o POST (`$_REQUEST`) | flag | Sí (para entrar al handler) | Activa el bloque final (~4464+) |
| `queInforme` | `$_REQUEST` | string | Sí | `vt` ventas totales, `vtr` por rubro, `vtrp` rubro+proveedor, `seleccion` combos filtros |
| `tabla` | `$_REQUEST` | string | No | Solo si `queInforme=seleccion`: qué listado (`cliente`, `tipocliente`, `articulo`, etc.) |
| `tipoResumen` | `$_REQUEST` | string | Sí si no es `seleccion` | Período: `dia`, `semana`, `mes` (según funciones) |
| `queSalida` | `$_REQUEST` | string | Sí si no es `seleccion` | Vista: p. ej. `html` o JSON (según rama; se asigna a `$salida`) |
| `rangoDoble` | `$_REQUEST` | int/string | Sí | `1` = segundo rango de fechas; si no, fechas secundarias null y `opRango` forzado a `"suma"` |
| `fechaDesde` | `$_REQUEST` | string (fecha) | Sí | Inicio período |
| `fechaHasta` | `$_REQUEST` | string (fecha) | Sí | Fin período |
| `opRango` | `$_REQUEST` | string | Sí | Operación entre rangos si `rangoDoble==1` |
| `fechaDesdeDos` | `$_REQUEST` | string | Condicional | Si `rangoDoble==1` |
| `fechaHastaDos` | `$_REQUEST` | string | Condicional | Si `rangoDoble==1` |
| `filtrarPor` | `$_REQUEST` | string | No | Cadena codificada `clave\|valor\|\|` múltiple (ver filtros en código) |
| `listarPor` | `$_REQUEST` | string | No | `cliente`, `articulo`, `vendedor`, `rubro`, `subrubro`, `proveedor`, `zona`, `tipocliente`, `marca`, etc. |
| `tipo` | `$_REQUEST` | string | Sí si aplica | P. ej. `un` unidades, `peso`, `monto` — altera expresiones `SUM` |

**Nota:** En el handler, `$grafico` se fija en **0** (no se lee de request en el fragmento analizado). `$puntoVenta` se fuerza a **null**.

### `relay-ventas-netas-gerencia.php`

| Parámetro | Método | Tipo PHP | Obligatorio | Descripción |
|-----------|--------|----------|-------------|-------------|
| `ajax` | **GET** (`isset($_GET['ajax'])`) | flag | Sí | Entrada al bloque ~26–157 |
| `queInforme` | `$_GET` | string | Sí | `vt` ventas, `ut` utilidades, `uti` utilidad × inflación, `seleccion` |
| `tabla` | `$_GET` | string | No | Tabla para `seleccion` |
| `tipoResumen` | `$_GET` | string | Sí (si no `seleccion`) | Igual concepto período |
| `queSalida` | `$_GET` | string | Sí | Salida |
| `fechaDesde` / `fechaHasta` | `$_GET` | string | Sí | Rango principal |
| `rangoDoble` | `$_GET` | int | Sí | Segundo rango |
| `fechaDesdeDos` / `fechaHastaDos` | `$_GET` | string | Condicional | Si `rangoDoble==1` |
| `opRango` | `$_GET` | string | Condicional | Si no hay segundo rango puede quedar null en rama else |
| `decimales` | `$_GET` | string | No | Precisión presentación |
| `tipo` | `$_GET` | string | No | Tipo agregación |
| `listarPor` / `filtrarPor` | `$_GET` | string | No | Igual idea que base |
| `puntoVenta` | `$_GET` | string | Sí en rama informes | Filtro PV |
| `grafico` | `$_GET` | string/int | No | Si `1`, se arman estructuras Chart |
| `tipoInflacion` | `$_GET` | string | No | Solo `uti` |
| `artEnsambVenta` | `$_GET` | string | No | Artículos ensamblados en venta |

**Nota:** Cerrado en **[DECISIÓN-VN-2]** (sección B.3).

---

## A.2 — Consultas SQL

El SQL se **arma por concatenación** en funciones grandes (`ventas_totales`, `ventas_totales_todos`, `ventas_totales_rubro`, `ventas_totales_rubro_proveedor`, `ventas_totales_todos` en gerencia con más ramas, `utilidades_totales_todos`, etc.). No hay un único SQL estático por endpoint.

### Tablas recurrentes (inventario no exhaustivo)

`cuentacliente` (alias `cc`), `stock`, `articulo`, `cliente`, `tipo_cliente`, `viajantes`, `proveedor`, `erp_zona`, `rubro`, `rubro_categoria`, `subrubro`, `marca`, `punto_venta`, `articulo_val_ce`, y en NC adicionales sobre `cc`.

### Ejemplo A — `ventas_totales` (dinámico, por `cuentacliente`)

Fragmento **tal cual** la plantilla central (líneas ~282–309 del base; variables `$primerAgrupo`, `$comoSumo`, `$leftJoin`, `$where`, `$agrupar`, `$orderby` dependen de `listarPor`, `filtrarPor`, `periodo`, `usaIdManual`):

```sql
SELECT 
                    {$primerAgrupo}
                    {$segundoAgrupo}
                    DAY(cc.Fecha) As dia,
                    WEEKOFYEAR(cc.Fecha) AS semana,
                    MONTH(cc.Fecha) AS mes,
                    YEAR(cc.Fecha) AS aa,
                    DATE_FORMAT(
                        STR_TO_DATE(CONCAT(YEARWEEK(cc.Fecha),
                        'Monday'),'%X%V %W'),'%d/%m') AS PrimerDiaSemana,  
                    DATE_FORMAT(
                    STR_TO_DATE(CONCAT(YEARWEEK(cc.Fecha),
                    'Saturday'),'%X%V %W'),'%d/%m') AS UltimoDiaSemana, 
                    {$comoSumo}       
            FROM cuentacliente AS cc
            {$leftJoin}
            LEFT JOIN cliente AS cli ON (cli.Codigo= cc.Codigo) 
            LEFT JOIN erp_zona AS zonas ON (zonas.id_zona=cli.id_zona)
            WHERE
            cc.CodViajante = {$vendedor}
            AND cc.Fecha BETWEEN '{$desde}' AND '{$hasta}'
            AND cc.`TipoComprobante`<>'NDA' 
            AND cc.`TipoComprobante`<>'NDB' 
            AND cc.`TipoComprobante`<>'REC' 
            AND cc.`Anulado` ='No'
             {$where}    

            GROUP BY {$agrupar} ORDER BY {$orderby} cc.Fecha ASC
```

- **Filtros dinámicos:** `$where` acumula `IN (...)` por cliente, tipo cliente, vendedor, artículo, proveedor, zona, rubro, subrubro, marca según `filtrarPor` (`||` y `|`).
- **Joins:** `LEFT JOIN` a `stock`/`articulo` si `listarPor=='articulo'` (`$leftJoin`).
- **SUM:** `comoSumo` alterna suma de `SubTotalDesc` en `cc` (excluye NCA/NCB o las resta) vs suma desde `stock.PrecioNetoxR` según tipo.

### Ejemplo B — `ventas_totales_rubro` (por `stock` + rubros)

SQL efectivo (tras acumular `$where` y `$whereVendedores`; líneas ~1104–1141 base):

```sql
SELECT
            DAY(stock.Fecha)as dia,
            WEEKOFYEAR(stock.Fecha) as semana,
            MONTH(stock.Fecha) as mes,
            YEAR(stock.Fecha) AS aa,
            ru.id_categoria AS codCat,
            ru.CodigoRubro AS codR,
            CONCAT(cat.nombre_categoria,' ',ru.NombreRubro) AS nomR,
            DATE_FORMAT(STR_TO_DATE(CONCAT(YEARWEEK(stock.Fecha),'Monday'),'%X%V %W'),'%d/%m') as PrimerDiaSemana,  
            DATE_FORMAT(STR_TO_DATE(CONCAT(YEARWEEK(stock.Fecha),'Saturday'),'%X%V %W'),'%d/%m') as UltimoDiaSemana,  
            {$comoSumo}  
            FROM stock 
                LEFT JOIN cuentacliente AS cc ON (cc.CodigoMovimiento= stock.CodigoMovimiento) 
                LEFT JOIN articulo AS arti ON arti.IDArt = stock.IDArt
                LEFT JOIN articulo_val_ce AS kg ON (kg.id_articulo = arti.IDArt AND kg.id_articulo_ce=1)
                LEFT JOIN rubro AS ru ON ru.CodigoRubro = arti.CodigoRubro
                LEFT JOIN rubro_categoria AS cat ON cat.id_categoria=ru.id_categoria
                LEFT JOIN marca ON marca.CodMarca=arti.CodigoMarca
                LEFT JOIN cliente AS cli ON cli.Codigo=stock.CodigoCP
                LEFT JOIN erp_zona AS zonas ON (zonas.id_zona=cli.id_zona)
                LEFT JOIN proveedor AS prov ON prov.Codigo = arti.CodigoProveedor
                LEFT JOIN punto_venta AS ppv ON ( ppv.id_punto_venta=cc.id_pv)
                LEFT JOIN tipo_cliente AS tpcli ON tpcli.IDTipoCliente = cli.TipoCliente
            WHERE
                 
                ({$rangoFecha})
                {$where}  
                AND cc.Anulado='No' 
                AND stock.Anulado='No'
                AND ru.anulado='No'
               
                AND (stock.TipoComp = 'Venta' 
                    OR stock.TipoComp = 'Venta TPV' 
                    OR stock.TipoComp = 'Devol - Cliente' 
                    OR stock.TipoComp = 'ND Anul NC'
                    )
                 
            GROUP BY {$agrupar} ,ru.CodigoRubro ORDER BY ru.CodigoRubro ASC ,stock.Fecha ASC
```

- **`$rangoFecha`:** `(stock.Fecha BETWEEN ...)` u OR segundo rango si `rangoDoble==1`.
- **Vendedores:** `stock.CodViajante` / `cc.CodViajante` acotados por `$vendedor` o lista `vendedor_a_cargo`.

### `listado_seleccion` — consultas por `tabla`

**Base (`relay-ventas-netas.php`):** cliente con filtro `todos_clientes` y `vendedor_a_cargo` (SQL ~2469–2474); otras tablas sin lógica gerencial extendida.

**Gerencia:** mismas tablas con ramas extra (ej. cliente ~217–235 gerencia) según `inf_gerenciales`, `supervisor_venta`, `todos_clientes`, `vendedor_a_cargo`.

**Anexo SQL:** Si se requiere paridad byte-a-byte con `ventas_totales_todos` / gerencia, volcar el SQL en un anexo aparte (miles de líneas); no bloquea la spec Django B.

---

## A.3 — Lógica de transformación (PHP → respuesta)

1. **Ejecución:** `mysqli_query` + `mysqli_fetch_assoc` en bucles → arrays PHP.
2. **Vacío:** varias funciones devuelven la cadena **`"vacio"`** si no hay filas.
3. **Agregación en memoria:** construcción de matrices `$renglon`, `$cabeceraTT`, `$titulo`; recálculo de porcentajes (`port` sobre total general), subtotales por fila (`subt`).
4. **Notas de crédito:** ramas con `$traigoArrayNc`, `$sqlNC`, fusión `fusion_ventas_nc` para alinear claves entre ventas y NC.
5. **Formato:** `number_format($valor, 2, ",", ".")` y prefijo `"$"` en celdas para JSON de gráficos (Google Charts style: `{v, f}`).
6. **Salida JSON principal** (patrón al final de armado de tabla/json, ~4397–4439 base):

```php
$arrayFinal = array(
    "titulos" => $titulo,
    "cabeceras" => $cabeceraTT,
    "data" => $renglon,
    // si grafico == 1: "goption", "gdata", "goptionT", "gdataT"
    // si NC: "impNC" => ...
);
return json_encode($arrayFinal);
```

7. **Handler:** `echo $resultado` (string JSON o HTML según función).

---

## A.4 — Delta: base vs gerencia

| Aspecto | `relay-ventas-netas.php` | `relay-ventas-netas-gerencia.php` |
|---------|---------------------------|-----------------------------------|
| Entrada AJAX | `isset($_REQUEST['ajax'])` | `isset($_GET['ajax'])` |
| Informes | `vt`, `vtr`, `vtrp`, `seleccion` | `vt`, `ut`, `uti`, `seleccion` |
| Utilidades | No en switch principal | `ut`, `uti` (utilidad total e utilidad con inflación) |
| `puntoVenta` | Forzado null en handler | Leído de GET |
| `grafico` | Forzado 0 en handler | Leído (charts) |
| `decimales`, `artEnsambVenta`, `tipoInflacion` | No en handler base | Presentes en gerencia |
| `listado_seleccion` | Firma `(tabla, codViajante, connV)`; permisos simples (`todos_clientes` + `vendedor_a_cargo`) | Firma `(connV, tabla, arrVendCargo)` + usa `inf_gerenciales`, `supervisor_venta`, `todos_clientes`, ramas supervisor/gerente |
| Permisos en combos cliente | Menos ramas | Filtra `cliente.CodViajante` según gerencia/supervisor/todos |

**Recomendación migración Django:** un **servicio común** de consultas (ventas por dimensión + mismos JOINs) parametrizado; **dos vistas o acciones** (vendedor vs gerencia) que solo varién política de filtro (`WHERE` vendedor / equipo / todos) y flags `utilidades` / inflación — evitar duplicar el SQL largo.

---

## A.5 — Permisos y sesión

### Variables `$_SESSION` (apariciones relevantes)

| Clave | Uso típico |
|-------|------------|
| `vendedor` | Objeto vendedor; `CodViajante` para filtros |
| `vendedor_a_cargo` | Array de códigos viajante (supervisor) |
| `todos_clientes` | `Si`/`No` — si puede listar todos los clientes (base en `listado_seleccion`) |
| `usa_id_manual` | Listados con id manual cliente/artículo/proveedor |
| `inf_gerenciales` | Solo gerencia — informes gerenciales (`Si`/`No`) |
| `supervisor_venta` | Gerencia — supervisor (`Si`/`No`) |
| `pemiso_supervisor_venta` | Typo en gerencia línea 56 — coexiste con `supervisor_venta` |
| `uso_bulto_promedio` | Gerencia — cálculos peso/bulto |
| `usa_domicilio_cliente_informes` | Gerencia — ramas domicilio |

### Permiso `permiso_sistema_puesto` (PHP login)

En `control.php` el permiso **96** se asocia a `ver_informes_gerencia_web` y alimenta variables de sesión de informes. Este relay **no** consulta `permiso_sistema_puesto` en SQL directo: el filtrado efectivo es por **flags ya cargados en sesión** al iniciar sesión.

**Mapeo Synap:** Ver **[DECISIÓN-VN-3]** (sección B.3): permiso canónico `reports.view_managerial` vía `ManagerialReportsPermission`; clave legado en permisos de sistema `ver_informes_gerencia_web` (etiqueta en UI).

### Lógica “solo mis ventas” vs “todo”

- **Base:** `ventas_totales` filtra `cc.CodViajante = {$vendedor}` en el ejemplo; en rubros, `stock`/`cc` se restringen por `$vendedor` o lista `vendedor_a_cargo` si no está vacía.
- **Gerencia:** `listado_seleccion` cliente combina `verTodosClientes`, `permisoGerencial`, `supervisorVenta` y `vendedor_a_cargo` para decidir el `WHERE` en `cliente.CodViajante`.

---

## Referencias

- Paridad numérica con reportes Synap: validar contra [`reports`](../../reports/) y documentación en `docs/reports/` (p. ej. ventas netas) antes de fusionar endpoints.

---

## B — Spec Django (servicio, vistas, URLs)

### B.0 — Respuestas a la pre-condición (auditoría código Synap)

**1. ¿Reportes que consultan `cuentacliente` o `stock`?**

- **`cuentacliente`:** Sí. Servicio **`QueryRunnerService`** en `reports/services/query_runner.py`: método **`_run_ventas_netas`** (slug `ventas_netas` / `ventas-netas`) — `FROM cuentacliente cc` con `WHERE` armado en listas (`where_conditions` + `params`) y **`cursor.execute(sql, params)`** (~L368–L546). También **`_get_ventas_netas_total`** (total FA/FB/… − NC para otros reportes).
- **`stock`:** Sí en el mismo servicio: p. ej. **`_run_backorder_vs_stock_vs_facturacion`** (slug `bo-stock-facturacion`) une `stock` / `stockp` / `cuentacliente` con el mismo patrón pool + `execute(sql, params)`.

**Patrón a reutilizar:** `get_mysql_pool()` → `with pool.get_connection(base_empresa) as conn:` → `cursor = conn.cursor()` → condiciones fijas en SQL, **valores siempre en `params`**; para `IN` dinámico, generar solo placeholders `%s` repetidos (como en `_run_ventas_netas` para PV/sucursales/clientes excluidos), sin interpolar datos del usuario en el string SQL.

**2. Permiso gerencial `inf_gerenciales` / `ver_informes_gerencia_web`**

- En API REST de reportes: clase **`ManagerialReportsPermission`** (`reports/permissions.py`), `required_permission = "reports.view_managerial"`, comprobado con **`user.tiene_permiso(...)`** o **`get_permisos_totales()`** (igual que **`OperationalReportsPermission`**).
- Uso típico: **`ReportQueryAPIView`** (`reports/api_views.py`) con `permission_classes = [OperationalReportsPermission | ManagerialReportsPermission]` y luego, por fila de reporte, `report.is_managerial()` + `ManagerialReportsPermission().has_permission(...)`.
- Catálogo Django: `core/constantes_permisos.py` — `("reports.view_managerial", "Informes gerenciales")`. En pantallas de permisos sistema aparece la clave legado **`ver_informes_gerencia_web`** (`core/views/views_permisos_sistema.py`, `core/services/administranet_permisos_sistema.py`). La vista gerencia del relay debe usar **exactamente** `ManagerialReportsPermission` (mismo criterio que informes gerenciales en `reports`).

**3. Clase base y respuesta JSON en `reports`**

- **API de ejecución de consultas:** `rest_framework.views.APIView` — **`ReportQueryAPIView`**, método **`post`**; salida vía **`ReportQueryResponseSerializer`** (`reports/serializers.py`): cuerpo con `meta`, `data`, `totals`, `notes` — **`Response(serializer.data)`**.
- **Vistas HTML (catálogo, etc.):** **`ReportsLoginRequiredMixin`** + genéricas `TemplateView` (`reports/views.py`).
- **Relay e-com (paridad PHP):** si la respuesta debe incluir `titulos` / `cabeceras` / `data` como el PHP, puede usarse otra forma de serialización **sin romper** el contrato de `ReportQueryAPIView`; ver **[DECISIÓN-VN-4]**.

**4. Router `legacy_db` y MySQL**

- **`legacy_db/db_router.py`:** modelos `legacy_db` → alias Django **`mysql`** (lectura/escritura ORM).
- **Reportes y SQL crudo:** no pasan por el router; abren la base **`base_empresa`** con **`core.mysql_pool`** / `reports/services/connection_pool.py` (**re-export** del pool). Mismo motor MySQL que `DATABASES['mysql']`, distinto esquema: conexión por nombre de base de la sesión.

---

### B.1 — Servicio común

Ubicación acordada: **`reports/services/ventas_netas.py`** (módulo dedicado al relay PHP), **llamado** desde `QueryRunnerService` o desde vistas API nuevas, **reutilizando** el patrón de conexión y `execute(sql, params)` de `query_runner.py` (no duplicar lógica del reporte mensual `ventas_netas` existente salvo factor común explícito).

```python
# reports/services/ventas_netas.py
# Patrón MySQL: igual que QueryRunnerService._run_ventas_netas / BO stock
# (get_mysql_pool, get_connection(base_empresa), cursor.execute(sql, params)).

def get_ventas_netas(
    fecha_desde,        # date
    fecha_hasta,        # date
    vendedor_id,        # int | None → None = gerencia (todos)
    listar_por,         # str: 'cliente'|'articulo'|'rubro'|...
    tipo,               # str: 'monto'|'unidades'|'peso'
    filtros,            # dict parseado desde filtrarPor PHP
    rango_doble,        # bool
    fecha_desde_dos,    # date | None
    fecha_hasta_dos,    # date | None
    op_rango,           # str: 'suma'|... | None
    incluir_utilidades, # bool → solo gerencia
    **kwargs
):
    """
    Servicio central. Construye query parametrizada equivalente
    al SQL dinámico del PHP.
    vendedor_id=None → sin filtro de vendedor (vista gerencia).
    NUNCA concatenar filtros como strings — usar parámetros %s.
    """
```

**Reglas WHERE (parametrizado):**

- Cada clave de `filtrarPor` válida agrega `AND campo IN (...)` con **lista como parámetros** (expansión de `%s`), no concatenación de valores.
- `vendedor_id is not None` → `AND cc.CodViajante = %s` (o el alias de tabla que corresponda en la rama).
- `vendedor_a_cargo` no vacío → `AND cc.CodViajante IN (...)` con tupla/lista en `params`.
- Prohibido: f-strings con input de usuario; los f-strings solo para estructura SQL fija y placeholders.

---

### B.2 — Vistas

Dos vistas que invocan **`get_ventas_netas`** (misma firma de servicio; distinta política):

| Vista | `vendedor_id` | Utilidades / inflación / gráfico | Permiso DRF |
|--------|----------------|-----------------------------------|-------------|
| **VentasNetasView** | Desde sesión Synap (viajante actual / reglas supervisor) | No utilidades; sin flags gerencia extra | `OperationalReportsPermission` (informe operativo; no exponer “todos los vendedores”) |
| **VentasNetasGerenciaView** | `None` (todos) | Acepta `decimales`, `artEnsambVenta`, `tipoInflacion`, `grafico` según spec PHP | **`ManagerialReportsPermission`** únicamente (equivalente a `inf_gerenciales` / flujo `ver_informes_gerencia_web` → `reports.view_managerial`) |

Clase base: **`rest_framework.views.APIView`** (mismo estilo que `ReportQueryAPIView`), **no** sustituir el contrato POST del endpoint genérico `reports/query/`.

Respuesta: **`rest_framework.response.Response`**, status **200**; cuerpo alineado a **[DECISIÓN-VN-4]** para filas vacías.

---

### B.3 — URLs y decisiones cerradas

Rutas sugeridas (prefijo bajo el mismo `include` de API de reportes o `ecom`, según corte de despliegue; nombres orientativos):

| Ruta (implementadas) | Vista | Método HTTP |
|----------------|--------|-------------|
| `api/reports/ventas-netas/relay/` | `VentasNetasRelayAPIView` | **GET** (paridad query string PHP base; ver VN-2) |
| `api/reports/ventas-netas/relay/gerencia/` | `VentasNetasGerenciaRelayAPIView` | **GET** |

#### [DECISIÓN-VN-1] Queries existentes en `reports`

- **Sí** hay consultas a **`cuentacliente`** y **`stock`** en `QueryRunnerService` (`reports/services/query_runner.py`).
- El reporte **`ventas_netas`** ya implementado en Synap es un **agregado mensual por sucursal/PV** (distinto del relay PHP multi-dimensión).
- **Decisión:** implementar **`reports/services/ventas_netas.py`** con **`get_ventas_netas`**, importando/reutilizando **solo el patrón** de pool + `params` + `execute` del mismo archivo; **no** reemplazar `_run_ventas_netas` existente sin diseño explícito. Opcionalmente, factores comunes (fechas, `base_empresa`) pueden delegar en helpers ya usados por `QueryRunnerService`.

#### [DECISIÓN-VN-2] Método HTTP (gerencia y base)

- PHP gerencia solo evalúa **`$_GET['ajax']`**.
- API genérica Synap **`ReportQueryAPIView`** usa **POST** (`reports/api_urls.py` → `query/`).
- **Decisión:** endpoints **relay** orientados al front e-com / paridad PHP: **GET** con query params. Si más adelante el front Synap unifica todo en el cliente de reportes estándar, se puede añadir POST alternativo sin quitar GET.

#### [DECISIÓN-VN-3] Permiso gerencial

- **Reutilizar** `ManagerialReportsPermission` y el permiso **`reports.view_managerial`** (sin crear permiso nuevo). Equivalente funcional al flag PHP **`inf_gerenciales`** y a la línea de permiso sistema **`ver_informes_gerencia_web`** en AdministraNET.

#### [DECISIÓN-VN-4] Respuesta vacía (PHP vs Django)

- PHP devuelve el string **`"vacio"`** en algunas ramas.
- **Decisión Django:** HTTP **200** con cuerpo JSON estructurado, p. ej. `{"data": [], "cabeceras": [], "titulos": []}` (y claves opcionales de gráfico vacías si aplica). Documentado como cambio explícito respecto al PHP para consumo JSON predecible.

---

## C — Implementación Synap (relay v1)

### C.1 — Archivos

| Componente | Ruta |
|------------|------|
| Servicio | `reports/services/ventas_netas.py` — `get_ventas_netas`, `parse_filtrar_por` |
| Vistas GET | `reports/ventas_netas_relay_views.py` |
| URLs | `reports/api_urls.py` — nombres `reports-ventas-netas-relay`, `reports-ventas-netas-relay-gerencia` |
| Tests | `reports/tests/test_ventas_netas_relay.py` |

### C.2 — Alcance v1 (paridad parcial PHP)

- **`listar_por`:** `mes` (default), `cliente` y `vendedor` sobre `cuentacliente` (`vendedor` con join `viajantes.Nombre`); `rubro`, `subrubro`, `articulo`, `marca`, `zona`, `tipocliente` y `proveedor` sobre `stock` inner join `cuentacliente`, `articulo`, `rubro` (más `subrubro`/`marca`/`cliente+erp_zona`/`tipo_cliente`/`proveedor` según dimensión), con suma por renglón `stock.PrecioNetoxR` y filtro `stock.TipoComp` (`Venta`, `Venta TPV`, `Devol - Cliente`, `ND Anul NC`), `stock.Anulado = 'No'`, y rubro no anulado (`ru.anulado = 'No'` o sin rubro).
- **`tipo`:**
  - `monto`: suma neta por comprobante (FA/FB/… − NC).
  - `unidades` y `peso`: habilitados para dimensiones basadas en `stock` (`rubro`, `subrubro`, `articulo`, `marca`, `zona`, `tipocliente`, `proveedor`), usando `stock.Cantidad` y `stock.Cantidad * articulo_val_ce.valor` (`id_articulo_ce=1`) respectivamente.
  - En dimensiones no `stock` (`mes`, `cliente`, `vendedor`) se mantiene respuesta vacía con nota para `unidades/peso`.
- **`queInforme=seleccion`:** implementado en relay vendedor/gerencia reutilizando `listado_filtros_estadisticas` (respuesta JSON de opciones `label/value` por `tabla`).
- **`queInforme=ut|uti` (gerencia):** soportado sobre dimensiones basadas en `stock` como utilidad neta estimada por renglón (`PrecioNetoxR - Cantidad*PrecioCosto`), con ajuste de inflación si `tipoInflacion` es numérico.
- **`grafico=1`:** respuesta incluye `gdata`/`goption` para consumo de gráfico simple en frontend.
- **Fechas:** un rango o dos rangos (`rangoDoble` + `fechaDesdeDos` / `fechaHastaDos`) con `OR` parametrizado.
- **`filtrarPor`:** parseo tipo PHP; whitelist en `cc` (`cliente` → `cc.Codigo`, `vendedor`/`codviajante` → `cc.CodViajante`); en `rubro`/`articulo` además `rubro` → `ru.CodigoRubro`, `subrubro` → `art.IDSubRubro`, `articulo` → `art.IDArt`.
- **Vendedor relay:** `session["user"]["id_vendedor_usr"]` → `cc.CodViajante = %s`. Si existe `session["user"]["vendedor_a_cargo"]` (lista de enteros), se usa `IN (...)` y no el filtro único.
- **Gerencia:** sin `CodViajante` salvo `vendedor_a_cargo` en sesión; `puntoVenta` opcional; `queInforme` `ut`/`uti` activa flag `incluir_utilidades` (lógica de utilidades pendiente).
- **Respuesta:** `data`, `cabeceras`, `titulos`, `meta` (incluye `scope`: `vendedor` | `gerencia`).

### C.3 — Pendiente (paridad completa relay PHP)

Paridad fina de exclusiones/composición idéntica al SQL dinámico PHP (casos avanzados de negocio en DB real), más ajustes de formato/gráficos complejos del frontend PHP si se requieren.

### C.4 — Ejemplo de llamada

```http
GET /api/reports/ventas-netas/relay/?fechaDesde=2026-01-01&fechaHasta=2026-01-31&listarPor=mes
```

Sesión Synap con `user.base_empresa` y `user.id_vendedor_usr`. Permiso `reports.view_operational`.

```http
GET /api/reports/ventas-netas/relay/gerencia/?fechaDesde=2026-01-01&fechaHasta=2026-01-31&listarPor=cliente
```

Permiso `reports.view_managerial`.

---

## D — Índice plan mayoristapp (Fase B)

Este documento cubre el vertical **informes / ventas netas relay**. La vista global de specs por vertical y checkpoints: [MAYORISTAPP_SPEC_INDICE.md](./MAYORISTAPP_SPEC_INDICE.md).
