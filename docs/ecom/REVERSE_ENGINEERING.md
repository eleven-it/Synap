# Ingeniería inversa — administraNET-ecom (PHP)

**Repositorio Git:** `git@github.com:licPflores/administraNET-ecom.git`  
**Fuente analizada:** árbol `administraNET-ecom` (clon del repo anterior). En verificación contra ese clon local (misma revisión que el backup `Synap Completo BKP 2025-11-19/administraNET-ecom`), los conteos **1287 / 1276 / 44** coinciden; no hay divergencia de inventario entre backup y remoto en esa revisión.  
**Fecha de análisis:** 2026-03-30.  
**Destino de migración:** Synap (Django), integración MySQL legacy vía `legacy_db` y reportes vía `reports` donde aplique.

**Alcance mayorista (`mayoristapp/`):** guía dedicada y cruce con la documentación del repo e-com en [MAYORISTAPP_MIGRATION.md](./MAYORISTAPP_MIGRATION.md). En `administraNET-ecom/docs/` existe al menos `administranet_estructura/modelo_base_datos.md` (modelo recibos / `cuentacliente`); resumen y uso en esa guía.

---

## 1.1 — Inventario de la aplicación

### Resumen cuantitativo

| Métrica | Valor |
|--------|-------|
| Archivos `.php` (recursivo, repo completo) | 1287 |
| Archivos `.php` solo bajo `mayoristapp/` | 1276 |
| Scripts `relay*.php` / `relay-*.php` (todo el repo; en la copia analizada están bajo `mayoristapp/`) | 44 |
| `composer.json` en raíz | No (aplicación no basada en Composer a nivel proyecto) |

### Framework PHP

- **No** se utiliza Laravel, Symfony ni CodeIgniter como esqueleto MVC.
- Patrón **procedural / por script**: cada URL suele mapear a un `.php` con `require_once` de includes (`sesion.inc.php`, `conexion.inc.php`, etc.).
- **Extensiones DB:** principalmente **`mysqli_*`** sobre MySQL; en scripts antiguos aparece **`mysql_connect`** (API deprecada, p. ej. `test-articulo.php`, `sincroniza.php`).
- **Sesión:** `session_start()` y superglobal `$_SESSION` (PHP nativo).

### Agrupación de archivos por responsabilidad

| Rol | Ubicación típica | Ejemplos |
|-----|------------------|----------|
| Entrada / login vendedor | `mayoristapp/` | `index.php`, `control.php` |
| Conexión y constantes DB | `mayoristapp/` | `conexion-general.inc.php`, `conexion.inc.php`, `conexion-vendedor.inc.php`, `includes/includes.inc.php` |
| Sesión y cabeceras | `mayoristapp/` | `sesion.inc.php`, `header-vendedor.inc.php`, `header-cliente.inc.php` |
| Endpoints AJAX / JSON (relays) | `mayoristapp/` | `relay-rubro.php`, `relay-ventas-netas.php`, `relay-stock-existencias.php`, … |
| Informes y listados HTML | `mayoristapp/` | `informe-ventas-total.php`, `datos_informe_compras.php`, `lista-comprobantes-ncancelados.php` |
| Carrito móvil | `mayoristapp/tmobile/jcart/` | `jcart-mob.php`, `relay-mob.php`, `gateway.php` |
| Recibos (subflujo) | `mayoristapp/recibo/` | `alta_recibo.php`, `json/json_recibo.php` |
| Procedimientos / ABM puntos | `mayoristapp/p/` | `sp_*.php`, `mostrame.php` |
| JSON API interna | `mayoristapp/p/json/` | `sp_configuracion.php`, `gestion-puntos-json.php` |
| Raíz del repo (pocas entradas) | `/` | `index.php`, `sincroniza.php`, `clientes-administranet.php`, `cmp.php` |
| Librerías vendor | `mayoristapp/_lib/mpdf2/`, `mayoristapp/chosen/` | `composer.json` locales (mPDF, chosen) |
| Excel legacy | `mayoristapp/Classes/` | `PHPExcel.php` (librería embebida) |

### Dependencias externas

- **Composer (locales):** mPDF y dependencias bajo `mayoristapp/_lib/mpdf2/`; `chosen` bajo `mayoristapp/chosen/`.
- **Front:** jQuery 1.x (`_scripts/jquery-1.11.1.min.js`), Font Awesome CDN, hojas `_css/`.
- **Inclusión manual:** `require` / `require_once` de `.inc.php` sin autoload PSR-4.

### Motor de base de datos

- **MySQL** (puerto típico `3306`, constante `puerto_db` en `includes.inc.php`).
- **Catálogo de empresas:** conexión inicial a base **`empresas`** (`mysqli_select_db($conexionT,"empresas")` en `conexion-general.inc.php`).
- **Base operativa por cliente:** elegida desde tabla `empresas` (`base_empresa`, `web_base_defecto`); segunda conexión `connV` a esa base (`conexion.inc.php`).
- **Credenciales:** definidas en `includes/includes.inc.php` (`usuario_db`, `password_db`, `servidor_db`, `puerto_db`). **[RIESGO]** Credenciales en claro en el repositorio; en Synap deben ser solo variables de entorno.

### Tablas y relaciones (inferidas del código)

No hay un único archivo de migraciones SQL en el repo PHP; el esquema es el de **AdministraNET (MySQL)**. Tablas citadas de forma recurrente (lista no exhaustiva; FKs típicas ERP cliente→pedido→renglones):

| Tabla | Uso en e-com |
|-------|----------------|
| `empresas` | Listado de bases/sedes web; selección de `base_empresa` |
| `usuarios` | Login vendedor (`control.php`), join con `puestos`, `sucursales` |
| `permiso_sistema_puesto` | Permisos granulares web (ids 3,5,38,43,…,196) |
| `puestos`, `sucursales` | Datos de usuario y sucursal |
| `cliente`, `cliente_domicilio` | Maestro cliente y domicilios |
| `articulo`, `rubro`, `subrubro`, `marca`, `deposito`, `stock` | Catálogo, filtros e inventario |
| `articulo_tipo_cliente` | Restricciones por tipo de cliente |
| `comp_ped` | Comprobantes/pedidos (notas, facturas electrónicas en relays) |
| `cuentacliente` | Cuenta corriente / ventas |
| `recibo_factura` | Imputaciones recibo-factura |
| `logi_hoja_ruta` | Logística |
| `tipo_cliente`, `viajantes`, `proveedor`, `erp_zona`, `rubro_categoria` | Filtros e informes |
| `permiso_sistema_puesto` | Existencia comprobada con `SHOW TABLES LIKE 'permiso_sistema_puesto'` |

**Relaciones FK:** según convención AdministraNET (documentación de tablas en Synap: índice previsto en `reports/docs/DB_INDICE_TABLAS.md` cuando exista en la rama). **[DECISION PENDIENTE]** Validar FK exactas contra dump MySQL de producción.

---

## 1.2 — Mapa de rutas y endpoints

En PHP “plano”, la ruta HTTP = ruta del archivo bajo el virtual host (p. ej. `/mayoristapp/control.php`). Método inferido por uso de `$_POST` / `$_GET`.

### Entradas principales

| Método | Ruta (ejemplo) | Archivo | Auth | Descripción breve |
|--------|----------------|---------|------|-------------------|
| GET | `/mayoristapp/index.php` | `mayoristapp/index.php` | No | Pantalla login vendedores |
| POST | `/mayoristapp/control.php` | `mayoristapp/control.php` | No | Valida usuario/clave y crea sesión |
| GET | `/mayoristapp/sesion.inc.php` | include | Sí | Arranque de sesión; redirige si falta `id_sesion` |
| GET/POST | `/mayoristapp/relay-*.php` | varios | Sí (`sesion.inc.php`) | AJAX JSON para UI |
| GET | `/mayoristapp/escritorio.php` | `escritorio.php` | Sí | Escritorio |
| GET | `/mayoristapp/dashboard.php` | `dashboard.php` | Sí | Dashboard |

### Endpoints relay (AJAX) — inventario de archivos

Inventario exhaustivo con checkpoints sugeridos: [MAYORISTAPP_RELAYS.md](./MAYORISTAPP_RELAYS.md). API Synap: `GET /ecom/api/mayoristapp/relay-inventory/`.

Cada fila: **GET/POST** según parámetros; casi todos incluyen `sesion.inc.php` (sesión requerida).

| Archivo | Descripción breve |
|---------|-------------------|
| `relay-art.php`, `relay-art-rapido.php` | Búsqueda artículos |
| `relay-articulo-remito.php` | Artículos en contexto remito |
| `relay-cliente-rapido.php`, `relay-clientes.php`, `relay-cliente-domicilio.php`, `relay-contacto-cliente.php` | Clientes y domicilios |
| `relay-rubro.php`, `relay-rubro-catalogo.php` | Rubros/subrubros/catálogo |
| `relay-marca.php`, `relay-laboratorio.php`, `relay-lote.php` | Filtros de producto |
| `relay-stock-existencias.php`, `relay-stock-autocomplete.php` | Stock |
| `relay-lista-precio.php`, `relay-promociones.php`, `relay-mas-vendidos.php` | Precios y promociones |
| `relay-pedidos.php`, `relay-presupuestos.php`, `relay-remitos.php`, `relay-recibos.php` | Comprobantes |
| `relay-ventas-netas.php`, `relay-ventas-netas-gerencia.php` | Informes ventas (muy extensos) |
| `relay-ctacte.php`, `relay-cuenta-corriente.php`, `relay-consumos-resumen.php` | Cuenta corriente |
| `relay-proveedor.php`, `relay-pagos_*` (vía listados) | Compras / proveedores |
| `relay_factura_electronica.php`, `relay_nota_credito.php`, `relay_facturas_imputar.php` | FE / NC / imputaciones |
| `relay_geolocalizacion.php`, `relay_ruta_logistica.php`, `relay-logistica-comprobantes.php` | Logística |
| `relay-envio-calculo.php` | Cálculo envíos |
| `relay-comprobantes-ncancelados.php`, `relay-comp-no-cancelados-resumen.php` | Comprobantes no cancelados |
| `relay-comprobante-a-mail.php` | Envío por mail |
| `relay-tipo-cliente.php`, `relay-tacc.php` | Tipo cliente / TACC |
| `relay-filtros-estadisticas.php`, `relay-devoluciones.php` | Estadísticas / devoluciones |
| `mayoristapp/jcart/relay.php`, `tmobile/jcart/relay-mob.php` | Carrito |

---

## 1.3 — Mapa de modelos de dominio (entidades)

### Usuario vendedor (sesión)

- **Origen:** fila de `usuarios` + permisos de `permiso_sistema_puesto` + joins `puestos`, `sucursales`.
- **Campos típicos en sesión:** `id_sesion`, `tipousuario` (`vendedor` / `cliente`), `servidor`, `baseConecto`, datos de `vendedor`, listas de PV, flags de módulos (`mod_inventario`, etc. — ver `control.php`).

### Cliente (sesión vendedor actuando para cliente)

- `$_SESSION['cliente']` puede ser objeto o arreglo `[objeto, arreglo]` según `sesion.inc.php`.

### Catálogo / artículo

- **Tablas:** `articulo`, `rubro`, `subrubro`, `marca`, filtros `ecommerce='Si'`, `anulado='No'` en consultas de `relay-rubro.php`.

### Comprobantes

- **Tabla central:** `comp_ped` (pedidos, facturas, notas según tipo).
- **Imputaciones:** `recibo_factura`.

### Equivalencia tipos (Django / Python) — orientativo

| MySQL (PHP) | Python / Django |
|-------------|-----------------|
| INT PK | `IntegerField` / `BigIntegerField` |
| VARCHAR | `CharField` / `TextField` |
| DECIMAL | `DecimalField` |
| DATE/DATETIME | `DateField` / `DateTimeField` |
| AES en columna password | **No replicar:** usar PBKDF2 en Synap; migración de contraseñas vía flujo único |

---

## 1.4 — Lógica de negocio crítica (pseudocódigo)

### Login vendedor (`control.php`)

```
POST usuario, clave
escapar strings SQL
si existe tabla permiso_sistema_puesto:
    armar SQL dinámico de columnas según permisos encontrados
    validar password con AES_DECRYPT(usuarios.password_usuario, CLAVE) = pass
sino:
    [rama legacy alternativa más abajo en el archivo]
si credenciales OK:
    session: id_sesion, tipousuario, vendedor, baseConecto, servidor, módulos...
    redirect escritorio
sino:
    redirect index.php?cartel=2
```

**Notas:** uso de `AES_DECRYPT` en SQL; **no** portar tal cual a Django (usar hash de contraseña estándar y mapeo de usuarios legacy).  
**Control horario opcional:** si `$controlHorario=="si"`, comparar `CURTIME()` con ventana; fuera de ventana → `cartel=3`.

### Filtros catálogo (`relay-rubro.php` con `ajax`)

```
si GET idcategoria:
    SQL rubros desde articulo JOIN rubro WHERE ecommerce, id_categoria, ...
    devolver JSON [{id,name}, ...]
si GET idrubro:
    SQL subrubros agrupados...
    devolver JSON UTF-8
```

### Precios

- Lógica en `util-calculaprecio.inc.php` (listas, descuentos) — **[DECISION PENDIENTE]** documentar fórmulas línea a línea en iteración siguiente leyendo el archivo completo.

### Integraciones externas

- **HTTPS:** `seguro.inc.php` redirige a URL fija según `SERVER_NAME` (dyndns).
- **Sincronización:** `sincroniza.php` con dos conexiones `mysql_connect` origen/destino (script de mantenimiento, no router MVC).

### Cron / colas

- No hay evidencia de Laravel Queue; tareas probables vía **cron del SO** llamando PHP sueltos (`sincroniza.php`). **[DECISION PENDIENTE]** inventariar en servidor de despliegue.

---

## 1.5 — Sesión, caché y estado

| Aspecto | Implementación |
|---------|----------------|
| Sesión | PHP nativa (`session_start()`, `$_SESSION`) |
| Claves relevantes | `id_sesion`, `tipousuario`, `servidor`, `baseConecto`, `cliente`, `vendedor`, `caminoDisp`, listas PV |
| Caché aplicación | No centralizada en código revisado; posible caché en servidor (OPcache PHP). Sin Redis en includes base |
| Estado servidor | Principalmente sesión + conexiones mysqli por request |

---

## Apéndice A — Paridad para tests

Valores de referencia para tests de regresión (snapshot lógico, no datos reales):

- **Cantidad archivos PHP (repo completo):** 1287  
- **Cantidad archivos PHP (`mayoristapp/`):** 1276  
- **Cantidad relays:** 44  
- **Framework:** `procedural_php_mysqli`  

La app Django `ecom` expone un endpoint de metadatos que replica estos números para verificación automatizada (`/ecom/api/migration-info/`), incluyendo `mayoristapp_php_file_count` y el arreglo `checkpoints` (filas `EcomMigrationCheckpoint`, cierre de verticales Fase C).

---

## Apéndice B — Hallazgos de seguridad (migración)

- Credenciales DB y claves de cifrado en archivos PHP versionados — **eliminar en Synap**; usar env + rotación.
- Contraseñas con AES en MySQL — migrar a modelo de autenticación Django estándar.
- Posible SQL concatenado en relays con parámetros GET — en Django usar ORM/`legacy_db` parametrizado.
