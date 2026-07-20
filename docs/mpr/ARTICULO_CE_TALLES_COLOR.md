# Campos especiales CE: TALLES y COLOR

**Audiencia:** desarrollo / datos.  
**Relacionado UI:** grilla [Asignar artículo a máquina](CARGA_MOVIL_OPERARIO.md), [Inventario por etapa](../stock/INVENTARIO_TABLA_MPR.md).

## Modelo AdministraNET

| Tabla | Rol |
|-------|-----|
| `articulo_ce` | Hasta 10 slots (`id_articulo_ce` 1..10): `Caption` (ej. TALLES, COLOR) y `tipo_campo` (Lista / Texto). |
| `articulo_caption_ce` | Mirror denormalizado `caption1`..`caption10` (fila id=1). |
| `articulo_lista_valor_ce` | Valores de lista por slot (`valor_lista`, `Anulado`, `nro_orden`). |
| `articulo_val_ce` | Valor por artículo y slot: `valor_ce` + `id_lista_valor_ce`. |
| `articulo_valor_ce` | Fila ancha por artículo: `valor1`..`valor10` (espejo de slots 1..10). |

**Convención habitual Best Sox / Synap:** slot con caption **TALLES** → `valor1`; caption **COLOR** → `valor2`.  
En código MPR se resuelve por **caption** (`TALLES`/`TALLE`, `COLOR`), no hardcodear ids de slot.

Tipos: normalizar con `core.utils.administranet_types` al leer/escribir MySQL legacy.

## Lectura en Synap

| Pantalla | Fuente |
|----------|--------|
| `/mpr/maquinas/carga-articulos/` | `mpr/repositories/maquina_articulo.py` — JOIN `articulo_val_ce` por caption |
| `/stock/inventario/` | `stock/services/inventario_tabla.py` — LEFT JOIN `articulo_valor_ce` (`valor1`/`valor2`) |

## Catálogo por base

El catálogo **no es idéntico** entre bases:

| Base | TALLES típicos | Notas |
|------|----------------|-------|
| `administranet` (prod) | `T1`..`T6`, `TL`, `TM`, `S`/`M`/`L`/`XL`… | Inferir talle como token del nombre si está en lista |
| `administranet1` (Pruebas) | `1`..`6`, letras, etc. | Puede mapear `T4`→`4` vía diccionario BEST |

COLOR: sólidos (`Negro`, `Rosa`, `Gris Mel`…) y combinaciones con `/` (`Rosa/Gris`, `Negro/Blanco`…).

## Inferencia y carga masiva (scripts `tmp/`)

Solo operativos / one-shot; no son parte del runtime de la app.

| Script | Uso |
|--------|-----|
| `tmp/inferir_talle_color_excel.py <base>` | Excel de validación (sin escritura) |
| `tmp/importar_talle_color_ce.py <base>` | Importa Excel → `articulo_val_ce` + `articulo_valor_ce` |
| `tmp/corregir_combos_color.py <base>` | Combos con `/` en el nombre |
| `tmp/corregir_solidos_color.py <base>` | Sólidos faltantes en catálogo + artículos sin COLOR |
| `tmp/analizar_colores_dobles_solidos.py <base>` | Solo lectura: 2+ sólidos sin `/` (ej. Rosa Logo Gris) |
| `tmp/corregir_colores_logo_combo.py <base>` | Aplica esos casos → `Rosa/Gris` (+ catálogo) |

Ejecutar en contenedor: `docker exec Synap_app python -u /app/tmp/<script> <base>`.

### Reglas de negocio aplicadas en carga

1. **Talle** desde tokens `T1`..`T6` / `TL` / `TM` / letras si están en el catálogo de la base.
2. **Color sólido** o **combo con `/`** desde el nombre vs catálogo (match exacto / compacto / substring).
3. **Dos sólidos sin barra** (patrón `{Color} Logo {Color}`): tratar como combinación `Color1/Color2`, dar de alta en lista COLOR si falta, y actualizar el artículo.
4. No pisar a ciegas: los scripts de sólidos solo tocan `valor2` vacío; el de logo-combo actualiza los casos detectados.

## Referencias

- VB6: `CargaArticulo.frm`, `Articulo_ce.frm`
- Planilla CQ: [CARGA_MOVIL_OPERARIO.md](CARGA_MOVIL_OPERARIO.md)
- Inventario: [../stock/INVENTARIO_TABLA_MPR.md](../stock/INVENTARIO_TABLA_MPR.md)
