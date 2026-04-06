# Migración — `mayoristapp` (administraNET-ecom)

**Alcance:** únicamente el árbol **`administraNET-ecom/mayoristapp/`** (portal B2B mayorista / vendedor). La raíz del repo (`index.php`, `sincroniza.php`, `clientes-administranet.php`, etc.) queda fuera del núcleo de pantallas mayoristas pero puede compartir credenciales y convenciones.

**Repositorio Git:** `git@github.com:licPflores/administraNET-ecom.git`  
**Fuente de código:** clonar el repo (p. ej. carpeta hermana `administraNET-ecom` junto al proyecto Synap). Las métricas de §1 se revalidaron contra ese clon y coinciden con el backup histórico `Synap Completo BKP 2025-11-19/administraNET-ecom`.

**Documentación oficial del repo e-com:** carpeta **`administraNET-ecom/docs/`** (ver sección 2 abajo).

**Documentación Synap relacionada:** [PLAN_FASES_MAYORISTAPP.md](./PLAN_FASES_MAYORISTAPP.md) (fases A–D), [CHECKLIST_FASES_MAYORISTAPP.md](./CHECKLIST_FASES_MAYORISTAPP.md) (seguimiento), [MAYORISTAPP_SPEC_INDICE.md](./MAYORISTAPP_SPEC_INDICE.md) (Fase B), [MAYORISTAPP_RELAYS.md](./MAYORISTAPP_RELAYS.md) (44 relays), [REVERSE_ENGINEERING.md](./REVERSE_ENGINEERING.md) (inventario global), [SPEC.md](./SPEC.md), [SPEC_PRECIOS.md](./SPEC_PRECIOS.md), [SPEC_VENTAS_NETAS.md](./SPEC_VENTAS_NETAS.md), [README_MIGRATION.md](./README_MIGRATION.md).

---

## 1 — Métricas de `mayoristapp` (paridad inventario)

| Métrica | Valor | Nota |
|---------|------:|------|
| Archivos `.php` bajo `mayoristapp/` | **1276** | Casi el total del repo (11 `.php` solo en raíz del repo) |
| Endpoints `relay*.php` / `relay-*.php` | **44** | En la copia analizada, **todos** están bajo `mayoristapp/` (incl. subcarpetas) |
| `composer.json` a nivel `mayoristapp` | No | Dependencias locales en `_lib/`, `chosen/`, etc. |

Los valores **1287** PHP y **44** relays del documento global incluyen la raíz del repositorio; para checkpoints de migración “solo mayorista” usar **1276** + **44** como referencia de alcance.

La API `GET /ecom/api/migration-info/` expone además `mayoristapp_php_file_count` (ver `ecom.services.migration_info`).

---

## 2 — Documentación en `administraNET-ecom/docs`

En la copia disponible para análisis, la carpeta contiene:

| Ruta | Contenido |
|------|-----------|
| `docs/administranet_estructura/modelo_base_datos.md` | Modelo orientado a **recibos, cobranzas y `cuentacliente`**: tablas `cliente`, `cuentacliente`, `cuenta_banco`, `banco`, `librobanco`, `recibo_factura`, `caja_saldo`, `caja_abm`, `chequetercero`, `tc_comprobante`, `retenciones`, `descuento_rec_nc`, relaciones e ilustraciones en PHP. |

**Uso en migración Synap**

- Útil como **referencia de columnas y relaciones** de movimientos de caja/recibos cuando se portan relays de cuenta corriente, recibos o imputaciones.
- **No sustituye** el inventario de tablas del mayorista completo: catálogo, pedidos, stock, informes (`articulo`, `stock`, `comp_ped`, `viajantes`, …) están detallados en [REVERSE_ENGINEERING.md](./REVERSE_ENGINEERING.md) §1.1 y en la documentación de tablas AdministraNET en Synap (`docs/general/`, `docs/reports/` según módulo).

Si el clon local del usuario añade más archivos bajo `docs/`, conviene **listarlos aquí** en un commit posterior y enlazarlos.

---

## 3 — Mapa funcional de `mayoristapp` (resumen)

| Área | Ubicación | Rol |
|------|-----------|-----|
| Login y escritorio | raíz `mayoristapp/` | `index.php`, `control.php`, `escritorio.php`, `dashboard.php` |
| Includes | `mayoristapp/` | `sesion.inc.php`, `conexion*.inc.php`, `includes/` |
| Relays AJAX | principalmente raíz `mayoristapp/relay-*.php` | API procedural JSON para la UI |
| Carrito web | `mayoristapp/jcart/` | `relay.php` y afines |
| Carrito móvil | `mayoristapp/tmobile/jcart/` | `relay-mob.php`, `gateway.php`, … |
| Recibos | `mayoristapp/recibo/` | Altas y JSON de recibo |
| Procedimientos / ABM | `mayoristapp/p/`, `mayoristapp/p/json/` | `sp_*.php`, configuración puntos |
| Informes pesados | raíz | `relay-ventas-netas.php`, `relay-ventas-netas-gerencia.php`, otros `informe-*.php` |
| Precios | include compartido | `util-calculaprecio.inc.php` → [SPEC_PRECIOS.md](./SPEC_PRECIOS.md) |

---

## 4 — Orden sugerido de migración (mayoristapp)

1. **Sesión y permisos** alineados a Synap (`login`, `core`, flags equivalentes a `permiso_sistema_puesto`).
2. **Catálogo** (rubros, artículos, stock, precios) reutilizando `ecom.services.price_calculator` y reglas legacy MySQL.
3. **Comprobantes** (`comp_ped`, remitos, pedidos) vía `legacy_db` / servicios dedicados.
4. **Cuenta corriente y recibos** — cruzar con `modelo_base_datos.md` del repo e-com.
5. **Informes** — ventas netas relay vs reporte Synap existente: [SPEC_VENTAS_NETAS.md](./SPEC_VENTAS_NETAS.md).

---

## 5 — Checklist de trazabilidad

- [ ] Cada submódulo migrado registrado en `EcomMigrationCheckpoint` (`module_slug` estable, p. ej. `mayoristapp_catalogo`, `mayoristapp_relay_ctacte`).
- [ ] SQL nuevo siempre parametrizado (sin concatenar entrada de usuario).
- [ ] Paridad numérica documentada frente a PHP cuando el flujo sea crítico (precios, totales de informes).
