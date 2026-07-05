# Especificación: Reporte MPR — Movimientos del flujo diario

**Estado: IMPLEMENTADO**  
**Prioridad: Media**  
**Módulos afectados:** mpr (services), hub `/mpr/reportes/` (Trazabilidad), reports (QueryRunner opcional)  
**Slug reporte (Reports):** `mpr-movimientos-produccion`

---

## 1. Resumen

Actividad del **flujo MPR diario** en formato tabla: envíos (`mpr_envio_produccion`), partes (`mpr_parte_linea` / `mpr_parte`) y clasificaciones (`mpr_transicion_lote`). **No** usa `lista_produccion_*` ni `movimiento_stock` legacy (OPT/OPP).

---

## 2. Fuentes de datos

| Origen | Uso |
|--------|-----|
| `mpr_envio_produccion` | Envío desde tablero consolidado |
| `mpr_parte_linea` + `mpr_parte` | Partes de producción por operario |
| `mpr_transicion_lote` | Clasificación / transición de lote |
| `articulo` | Código y descripción del componente |

**Servicio:** `reporte_mpr_movimientos(base_empresa, fecha_desde, fecha_hasta, limit=200)`  
Helper interno: `_recolectar_eventos_ledgers_mpr`.

---

## 3. Entradas

| Parámetro | Obligatorio | Descripción |
|-----------|-------------|-------------|
| `base_empresa` | Sí | Base MySQL |
| `fecha_desde` / `fecha_hasta` | No | Default últimos 7 días (`_periodo_reporte_mpr`) |
| `limit` | No | Default 200, máx. 500 |

---

## 4. Salidas

| Campo | Descripción |
|-------|-------------|
| `fecha` | dd/MM/yyyy HH:mm |
| `tipo_mov` | Envío a producción / Parte de producción / Clasificación |
| `id_articulo`, `codigo_articulo`, `descripcion_articulo` | Componente |
| `cantidad` | Unidades del evento |
| `detalle` | Referencia ledger (id parte, destino, etc.) |
| `operario` | Nombre en partes; «-» en envío/clasificación |

Orden: más reciente primero.

---

## 5. Servicios legacy eliminados del hub

Los siguientes servicios basados en `lista_produccion_*` **fueron retirados** de `mpr/services.py` (sustituidos por agregadores MPR diarios en `/mpr/reportes/`):

- `reporte_mpr_pendiente` → usar `reporte_mpr_pendiente_componentes` (tablero consolidado)
- `reporte_mpr_wip`
- `reporte_mpr_produccion_por_operario` → usar `reporte_mpr_operario_parte`
- `reporte_mpr_opt_cerradas`

Las tablas `lista_produccion_*` siguen existiendo para el módulo **OPT** (VB6/Synap); el hub de reportes ya no las consulta.

---

## 6. Tests

```bash
docker exec Synap_app python manage.py test mpr.tests.test_reportes_mpr_services.TestReporteMprMovimientos --keepdb
```
