# Especificación de precios — `mayoristapp/util-calculaprecio.inc.php`

**Origen:** clase `CalculadorPreciosUtil` en administraNET-ecom (PHP).  
**Auditoría:** lectura integral del archivo (493 líneas).  
**Destino Synap:** servicio de dominio + tipos `Decimal` alineados a `core.utils.administranet_types`.

---

## A — Inventario de funciones

| Función | Parámetros de entrada | Retorno | Descripción en una línea |
|---------|------------------------|---------|---------------------------|
| `CalculadorPreciosUtil::calculaPrecios` | `$param` (objeto o array con claves `arti`, `listaPrecioCliente`, `descRenglon`, `usaReglaPrecio`, `codCliente`); `$connV` (`mysqli`, opcional si hay reglas masivas/generales) | `array` asociativo de precios calculados | Orquesta lista de precios, reglas opcionales, promociones del artículo, impuesto interno ABM y arma el resultado final. |
| `CalculadorPreciosUtil::reglasPrecioMasivas` | `$connV`, `$idArt`, `$codigoProveedor`, `$codigoRubro`, `$idSubRubro`, `$codCliente` | `int\|null` (id de regla) o `null` | Consulta `reglas_precio_masivas` y **devuelve la primera regla no anulada** (lógica de matching documentada como incompleta en comentario). |
| `CalculadorPreciosUtil::reglasPrecioGeneral` | `$connV`, `$idArt`, `$codigoProveedor`, `$codigoRubro`, `$idSubRubro` | `int\|null` | `SELECT` de una regla en `reglas_precio_alta_art` con `LIMIT 1`. |
| `CalculadorPreciosUtil::calcularImpuestoInterno` | `$arrParametros` (cantidad, neto, costo, descripcion, tipo, porcentaje, montoFijo, pesoCalculado, pagoMinimo, idUnimed) | `float` | Calcula monto de impuesto interno según `tipo`: Porcentaje, Porcentaje - Minimo, Monto fijo. |
| `CalculadorPreciosUtil::vigencia_promo` | `$desde`, `$hasta` (fechas), `$idArt`, `$promoTipo`, `$connV` (no usado en el cuerpo) | `"si"` \| `"no"` | Determina si la fecha actual cae en el rango de vigencia (con corrección año > 2038 → 2037). |

---

## B — Fórmulas y algoritmos (pseudocódigo Python-like)

### B.1 Selección de columnas según lista del cliente (`listaPrecioCliente`)

```python
def mapear_lista(arti, lista_precio_cliente):
    # switch sobre strings exactas: 'Lista 1' … 'Lista 5', 'Lista Oficial'
    # Para Lista 1..5:
    #   precio_neto = arti.Precio{i}V
    #   importe_iva = arti.impIva{i}
    #   importe_interno = arti.imp_interno{i}
    #   precio_venta = arti.Precio{i}VI  # precio con IVA precargado en tabla
    #   promo_lista = "si" si arti.promocion_lista{i} == "Si" else "no"
    # Lista Oficial:
    #   precio_neto = arti.PNOficial, importe_iva = arti.impOf, etc.
    #   promo_lista = "si" fijo
    # [DECISION PENDIENTE: qué ocurre si lista_precio_cliente no coincide con ningún case]
    #   → en PHP las variables precio_neto, etc. quedarían indefinidas (comportamiento no definido / riesgo de notice).
```

### B.2 Inicialización

- `precio_venta_final = precio_venta`
- `precio_neto_calc = precio_neto`
- `desc_final = 0` (se va sobrescribiendo según reglas/promo/descuento renglón)
- Flags: `uso_promocion = "Si"`, `aplico_regla = "no"`, etc.

### B.3 Orden de aplicación (alto nivel)

1. **Elegir precios base** según lista (neto, IVA, interno, precio venta “tabla”).
2. Si `usa_regla_precio == "Si"` y `connV`:
   - **Prioridad 1:** Si `arti` trae `tipo_calculo` no nulo → regla “embebida” en el objeto artículo.
   - **Prioridad 2:** `reglasPrecioMasivas` → carga fila `reglas_precio_masivas`.
   - **Prioridad 3:** `reglasPrecioGeneral` → carga fila `reglas_precio_alta_art`.
3. Si hay regla (`tipo_calculo` + `importe_regla`), **desactiva** promociones de artículo (`uso_promocion = "No"`) y aplica según tipo (ver B.4).
4. Si no hay regla o no aplica, **promociones** del artículo (`arti.promocion`, `promo_lista`, vigencia, `promoTipo`).
5. Ajuste **exento IVA** si neto “precio venta” coincide con neto calculado (B.4).
6. Si sesión `usa_impuesto_interno_abm == "Si"`: recalculo con `calcularImpuestoInterno` y descuento sobre neto (B.5).
7. Bloque `idCliente == 1` (B.6) — **variable no definida en este método** (ver sección D).
8. Armar array de salida.

### B.4 Reglas de precio (`tipo_calculo`)

**Descuento**

```python
# Si prioridad_regla existe y != "Desc. Cliente": desc_renglon = importe_regla
# Elif desc_renglon < importe_regla: desc_renglon = importe_regla  # max( desc manual, regla )
# desc_renglon_calc = desc_renglon * precio_neto / 100
# precio_neto_calc = precio_neto - desc_renglon_calc
# importe_iva = precio_neto_calc * Alic / 100
# importe_interno = precio_neto_calc * (impuesto_interno / 100)
# precio_venta_final = precio_neto_calc + iva + interno sobre precio_neto_calc
# desc_final = desc_renglon  # porcentaje aplicado
```

**Marcación** (sobre neto)

```python
# desc_renglon = importe_regla
# desc_renglon_calc = desc_renglon * precio_neto / 100
# precio_neto_calc = precio_neto + desc_renglon_calc  # recargo
# Nota: en el código, importe_iva e importe_interno se calculan sobre precio_neto_nuevo (neto original),
# no sobre precio_neto_calc — [DECISION PENDIENTE: ¿bug intencional o error de copia?]
# precio_venta_final recalcula sobre precio_neto_calc con Alic e impuesto_interno
```

**Precio fijo**

```python
# precio_neto_nuevo = importe_regla  # neto objetivo
# desc_renglon_calc = desc_renglon * precio_neto / 100  # descuento sobre neto *anterior* a la lista
# precio_neto_calc = precio_neto_nuevo - desc_renglon_calc
# Luego iva/interno y precio_venta_final; desc_final se pisa a 0 al final del case (líneas duplicadas)
```

**Cantidad - Unidad** (regla)

```python
# desc_renglon = 0; varios pasos de neto igual que descuento 0%
# SQL: reglas_precio WHERE id_articulo, tipo_calculo='Cantidad - Unidad', id_cliente = cod_cliente
# promo_cant, desc_final = promocion_por, promo = "si", cantidad = number_format(promo_cant)
```

### B.5 Promociones del artículo (`uso_promocion == "Si"`)

Condiciones: `arti.promocion == 'Si'` y `promo_lista == "si"`, y `vigencia_promo(...) == "si"`.

Tipos (`promoTipo`):

- **Cantidad - Intervalo:** `promo = "si"`, `desc_final = 0`, `cantidad = 1`.
- **Importe descuento:** compara `desc_renglon` vs `promo_porc`: el mayor “gana” como `desc_final`; recalcula neto con descuento % sobre neto; `precio_venta_final` con IVA sobre neto ya descontado.
- **Cantidad:** igual comparación; `cantidad = promo_cant`.
- **Cantidad - Unidad:** `promo = "si"`, `desc_final = promo_porc`, `cantidad = promo_cant`.
- **Monto fijo:** `precio_neto_calc = round(promo_porc / (1 + Alic/100), 4)`; `desc_final = round((precio_neto - precio_neto_calc) * 100 / precio_neto, 1)`; `precio_venta_final = promo_porc` (monto final con IVA incluido según fórmula).

**Redondeo explícito:** solo en rama **Monto fijo** (`round(..., 4)` y `round(..., 1)`). El resto usa aritmética float PHP sin `round` uniforme → **[DECISION PENDIENTE]** política de redondeo en Django (`ROUND_HALF_UP`, decimales).

### B.6 Exención IVA (neto = precio con IVA “viejo”)

```python
if precio_neto == precio_venta or precio_neto_calc == precio_venta_final:
    # Reexpresa neto/iva/iva final usando solo Alic; fuerza precio_venta y precio_venta_final como neto+iva
```

### B.7 Impuesto interno ABM (`$_SESSION['usa_impuesto_interno_abm'] == "Si"`)

```python
# Si arti.interno_descripcion: imp_interno = calcularImpuestoInterno(...)
# descuento_calculo = desc_final salvo promoTipo == 'Cantidad - Unidad' → 0
# precio_neto_calc = precio_neto - (precio_neto * descuento_calculo / 100)
# importe_iva = precio_neto_calc * Alic / 100
# precio_venta_final = precio_neto_calc + iva + importe_interno (impInterno)
```

### B.8 `calcularImpuestoInterno`

```python
if tipo == 'Porcentaje':
    valor = (cantidad * costo) * porcentaje / 100
if tipo == 'Porcentaje - Minimo':
    monto = (cantidad * costo) * porcentaje / 100
    valor = montoMinimo if monto < montoMinimo else monto  # [DECISION PENDIENTE: PHP usa $arrParametros['montoMinimo'] pero el caller pasa 'pagoMinimo' — posible bug]
if tipo == 'Monto fijo':
    valor = cantidad * montoFijo
# "Peso" y "Peso - Monto fijo" no implementados (comentario en código)
```

### B.9 `vigencia_promo`

- Si `desde` y `hasta`: `hoy` entre ambas (DateTime); si año de `hasta` > 2038 → se fuerza a 2037 antes de parsear (workaround).
- Si ambos `null` → vigente.
- Solo `hasta` → `hoy <= hasta`.
- Solo `desde` → `hoy >= desde`.

---

## C — Dependencias

### Tablas MySQL consultadas directamente

| Tabla | Uso |
|-------|-----|
| `reglas_precio_masivas` | `SELECT *` por id; listado inicial `WHERE Anulado = 'No'` |
| `reglas_precio_alta_art` | `SELECT *` por id; otra consulta `id` con `LIMIT 1` |
| `reglas_precio` | `promocion_por`, `promocion_cant` para tipo `Cantidad - Unidad` y cliente |

### Variables de sesión (`$_SESSION`)

| Clave | Uso |
|-------|-----|
| `usa_impuesto_interno_abm` | Si `"Si"`, activa bloque de recálculo con `calcularImpuestoInterno` y descuento sobre neto |

No se leen otras `$_SESSION` en este archivo.

### Includes / requisitos

- El archivo define una **clase**; no hace `require` interno. Quien incluye debe tener disponible `mysqli` y, si se usan reglas, `$connV`.
- Usa `DateTime` (extensión PHP estándar).
- Depende del **objeto `$arti`** con muchos campos: precios por lista, `Alic`, `impuesto_interno`, promociones, posibles `tipo_calculo`/`importe_regla` en artículo, `interno_*`, etc.

---

## D — Casos borde identificados

| Condición | Comportamiento en PHP |
|-----------|------------------------|
| `listaPrecioCliente` no coincide con ningún `case` | Variables de precio no inicializadas → **comportamiento indefinido** / errores. |
| `usa_regla_precio == "Si"` pero `connV` es `null` | Consultas a reglas masivas/generales/Cantidad-Unidad fallan o no se ejecutan. |
| `reglasPrecioMasivas` / `reglasPrecioGeneral` | Implementación **simplificada** (primera regla / LIMIT 1), no filtra por art/rubro/proveedor/cliente como sugiere la firma. |
| `desc_renglon` vs `promo_porc` (Importe descuento / Cantidad) | Se usa el **mayor** como porcentaje efectivo; si `desc_renglon` gana, `promo = "no"`. |
| Promoción sin vigencia (`aplica_promo == "no"`) y `desc_renglon > 0` | Aplica descuento de renglón manual sobre neto (bloque 278–291). |
| `arti.promocion == 'No'` o `promo_lista == "no"` | Reset cantidad/promo; posible promo solo `Cantidad - Intervalo` si vigencia; si `desc_renglon > 0` y no es ese tipo, aplica descuento renglón. |
| `precio_neto == precio_venta` o `precio_neto_calc == precio_venta_final` | Trata como exento / alineación de neto+IVA. |
| `isset($idCliente) && $idCliente == 1` | Pone todos los precios a 0; **`$idCliente` no se asigna en `calculaPrecios`** → probable **código muerto** o dependencia de variable global no visible. |
| `calcularImpuestoInterno` tipo `Porcentaje - Minimo` | Clave `montoMinimo` vs `pagoMinimo` en el caller — **inconsistencia de nombres**. |
| Año vigencia > 2038 | Ajuste a 2037 para evitar límite de `DateTime` en 32 bits. |

---

## E — Tabla de paridad (fixtures de test)

Valores numéricos **ilustrativos** para tests unitarios; deben validarse contra datos reales de `articulo` en MySQL.

Supuestos comunes en ejemplos: `Alic = 21`, `impuesto_interno = 0`, sin reglas ni promoción, lista `Lista 1` con `Precio1V = 1000`, `Precio1VI` coherente con neto+IVA si aplica.

| Descripción del caso | precio_neto (base lista) | lista | desc_renglon % | resultado esperado (precio_venta_final aprox.) | Notas |
|----------------------|--------------------------|-------|----------------|-----------------------------------------------|--------|
| Sin descuento, sin promo | 1000.00 | Lista 1 | 0 | `1000 + 1000*0.21 = 1210.00` si se usa fórmula estándar sobre neto_calc | Verificar contra `Precio1VI` precargado si el flujo no recalcula |
| Descuento 10% solo renglón (rama 309–318) | 1000.00 | Lista 1 | 10 | neto_calc=900; final ≈ `900 * 1.21 = 1089.00` | Tras promociones desactivadas o sin promo |
| Regla Descuento 15% vs desc_renglon 10% | 1000.00 | — | 10 | Regla fuerza 15% si `prioridad_regla != "Desc. Cliente"` o `max(10,15)` según rama | Cubrir ambas ramas de prioridad |
| Monto fijo promo (precio final TTC) | 1000 neto, `promo_porc=121` | Lista 1 | 0 | `precio_venta_final = 121` (TTC); neto_calc redondeado 4 dec | Caso `Monto fijo` |
| Lista Oficial | `PNOficial` | Lista Oficial | * | Igual pipeline con `promo_lista` forzada a "si" | |
| Vigencia nula ambas | * | * | * | `vigencia_promo` = "si" | Promo sin fechas |
| Cliente `codCliente` null en masivas | * | * | * | Se sustituye por `codCliente = 1` en `reglasPrecioMasivas` | |

**[DECISION PENDIENTE]** Generar fixtures con volcado real de una fila `articulo` + listas para coincidencia exacta con PHP (incl. floats).

### G — Comportamiento implementado en Synap (`ecom.services.price_calculator`)

| Tema | PHP legacy | Synap (2026-03) |
|------|------------|-----------------|
| Lista desconocida | Variables no inicializadas / error en runtime | Se lanza `ListaPrecioInvalidaError` si `lista_id` ∉ `{1,2,3,4,5,6}` |
| `lista_id` | Strings `"Lista 1"` … | Enteros `1`…`5` y `6` = Lista Oficial; el **precio base** ya debe corresponder a la lista elegida (el caller resuelve `Precio{i}V` como en PHP). |
| Descuento \> 100% | Implícito en float | `normalizar_descuento_porcentual` capa a **100%** (neto 0). |
| Cliente sin tipo | No modelado explícito en el snippet | Si se pasa explícitamente `tipo_cliente=None` en kwargs, el descuento de cliente se ignora (0%). |
| API principal | `calculaPrecios` masivo | `calcular_precio(precio_base, lista_id, descuento_cliente, **kwargs)` con flags `incluir_iva`, `promo_tipo="Monto fijo"`, `descuento_regla_pct`, etc. |
| Tests | — | `ecom/tests/test_price_calculator.py`, `test_price_regression.py`; integración MySQL: `test_price_integration.py` (`@pytest.mark.integration`). Cobertura del módulo `price_calculator.py`: **100%**. |

---

## F — Decisiones de diseño para Django

1. **Ubicación de la lógica:** Preferir un **servicio puro** (p. ej. `ecom.services.precios` o `legacy_db.services.precios`) que reciba un DTO del artículo + parámetros de lista/cliente/descuento. **No** en el modelo `Articulo` legacy (no ORM completo en MySQL) salvo métodos de conveniencia que deleguen al servicio.

2. **Tipo numérico:** `DecimalField(max_digits=..., decimal_places=4)` para netos y montos; **4 decimales** alineados al `round(..., 4)` del caso Monto fijo; exponer `decimal_places=2` solo en UI si negocio lo exige. Usar `Decimal` en Python y `quantize` con política explícita (**[DECISION PENDIENTE]** documento de redondeo único).

3. **`PriceCalculator` vs funciones:** Una clase **`PriceCalculator`** (o `CalculadorPreciosUtil` renombrado) con métodos estáticos o instancia inyectada con `conn` legacy **mejora testabilidad** y agrupa `vigencia`, `impuesto_interno`, reglas; las funciones sueltas son suficientes solo si el volumen no crece.

4. **Reglas masivas/general:** Reemplazar stubs por consultas parametrizadas y replicar **exactamente** la selección de reglas negocio (hoy incompleta en PHP) — **[DECISION PENDIENTE]** con negocio.

5. **Paridad:** Tests que comparen salida del servicio Django vs mismo input pasado a un script PHP aislado (o valores congelados en esta tabla) antes de sustituir en producción.

6. **Seguridad:** Nunca concatenar SQL con datos de cliente; usar parámetros o ORM/`legacy_db`.

---

## Referencias cruzadas

- [REVERSE_ENGINEERING.md](./REVERSE_ENGINEERING.md)  
- [SPEC.md](./SPEC.md)  

---

## H — Relays mayoristapp (precio / promoción) — Fase C v1

| Relay PHP | Ruta Synap | Contrato |
|-----------|------------|----------|
| `relay-lista-precio.php` | `GET /ecom/api/mayoristapp/precios/lista-precio/` | JSON `[{ "id", "name", "selected" }, …]` listas 1–5; textos desde `configuracion` (`lista_precio_web`, `desc_util1`…`desc_util5`). `selected`: query `cod_lista_cliente` o sesión `cliente_cod_lista_precio` / `mayoristapp.cliente.codListaPrecio`; si no, lista por defecto según `lista_precio_web`. |
| `relay-promociones.php` | `GET /ecom/api/mayoristapp/precios/promociones/?ajax=1` | JSON (no HTML): `articulos`, `intervalos_por_articulo`, `filtro_lista_precio`, `fecha_consulta`. Filtros: `categoria`, `rubro`, `subrubro`, `marca`, `modelo`; opcional `listaPrecio` / `lista_precio_cliente` (texto tipo `Lista 1`) o sesión `lista_precio_cliente` / `mayoristapp.cliente.listaPrecio` para columnas `articulo.promocion_lista*`. Implementación: `ecom.services.precio_relays`. |

Índice vertical: [MAYORISTAPP_SPEC_INDICE.md](./MAYORISTAPP_SPEC_INDICE.md).
