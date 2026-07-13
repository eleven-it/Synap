# Alta de artículo AdministraNET desde Synap

## Alcance

Servicio reutilizable `core.services.administranet_articulo.crear_articulo` para INSERT mínimo en MySQL `articulo` + filas `stock_deposito` (saldo 0), alineado a la lógica de **CargaArticulo.frm** (secuencia `CodigoArticulo` por rubro/subrubro, `id_manual` único, NOT NULL de schema).

**No** es el ABM completo VB6 (fotos, proveedores, presentaciones, CE, etc.).

## Uso en migración BEST

En `/mpr/migracion-best/articulos/`, filas **Sin candidato** / **Sin match** sin `admin_idart`:

| Acción | POST `accion` | Efecto |
|--------|---------------|--------|
| Dar de alta en Admin | `alta` | Crea artículo + valida mapeo |
| Dar de alta seleccionados | `alta_seleccion` + `sel[]` | Lote |

Campos tomados de BEST (`BestArticuloMap` + consulta precio):

| Admin | Origen BEST |
|-------|-------------|
| `id_manual` | `best_id_articulo` (MMID) |
| `NombreArticulo` | `best_articulo` |
| `CodArtProv` | primera variante / `best_codigo` |
| `Precio1V`…`Precio5V` | `MC.MCSTDC` (CC 3000) si > 0; si no, `REP_INVENTARIOS.Precio`. Si BEST no tiene precio, quedan en 0 |
| `PrecioCosto` | siempre 0 (BEST no trae costo unitario confiable) |
| `IDSubRubro` | = `CodigoSubRubro` |
| `id_unimed` | fijo `1` (Unidad / pares) |
| `cantidad_promedio_bulto` | desde pack BEST (1→12, 2→6, 3→4…) |
| `NroCodBarra` / `Simbologia` | `RRRSSSAAAAAA` + CODE128 |
| `CodigoMarca` | diccionario marca BEST/MMID → `marca.CodMarca` |
| `Detalle` | nota de origen migración + fuente de precio |

Defaults estructurales: plantilla del último `tipo_art_fab=Terminado` activo (rubro, IVA, UM); si no hay, rubro `1` / sub `1.1`, Alicuota 1, etc. Siempre `Discontinuo=No`, `tipo_art_fab=Terminado`.

## API

```python
from core.services.administranet_articulo import crear_articulo

crear_articulo(
    base_empresa="administranet1",
    id_manual="LE7870CRCR4",
    nombre_articulo="Levis 7870-W004 …",
    cod_art_prov="7870-W004",
    tipo_art_fab="Terminado",
)
# → {success, idart, codigo_articulo_t, stock_depositos_creados, …}
```

Si ya existe `id_manual`, lanza `ValueError` (usar Asignar).

## Referencias

- Schema: `docs/general/tablas/articulo.md`
- VB6: `docs/general/MIGRACION_ADMINISTRANET_VB6_ANALISIS.md` §5.4
- Módulo BEST: `docs/mpr/MODULO_MIGRACION_BEST_MPR.md`
