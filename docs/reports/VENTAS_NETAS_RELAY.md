# API relay Ventas netas (mayoristapp → Synap)

Migración parcial de `relay-ventas-netas.php` y `relay-ventas-netas-gerencia.php`. Especificación detallada y decisiones: [docs/ecom/SPEC_VENTAS_NETAS.md](../ecom/SPEC_VENTAS_NETAS.md) sección C.

## Endpoints

| Método | Ruta | Permiso DRF |
|--------|------|-------------|
| GET | `/api/reports/ventas-netas/relay/` | `reports.view_operational` |
| GET | `/api/reports/ventas-netas/relay/gerencia/` | `reports.view_managerial` |

## Requisitos de sesión

- `session["user"]["base_empresa"]`: nombre de base MySQL AdministraNET.
- Relay vendedor: `session["user"]["id_vendedor_usr"]` (CodViajante).
- Opcional supervisor: `session["user"]["vendedor_a_cargo"]` = lista de CodViajante (usa `IN` en el relay operativo).

## Parámetros GET (resumen)

- Obligatorios: `fechaDesde`, `fechaHasta` (YYYY-MM-DD; acepta alias `fecha_desde` / `fecha_hasta`).
- Opcionales: `listarPor` (`mes` | `cliente`), `tipo` (`monto`), `filtrarPor`, `rangoDoble`, `fechaDesdeDos`, `fechaHastaDos`, `opRango`, `ajax`.
- Gerencia además: `puntoVenta`, `queInforme`, `decimales`, `grafico`, `tipoInflacion`, `artEnsambVenta` (metadatos / futuro).

## Respuesta JSON

`data`, `cabeceras`, `titulos`, `meta`. Sin filas: listas vacías y HTTP 200 ([DECISIÓN-VN-4]).

Dimensiones sobre renglones `stock` excluyen `articulo.tipo_art = 'Gasto'` ([FILTRO_TIPO_ART_GASTO.md](FILTRO_TIPO_ART_GASTO.md)).

## Tests

`python manage.py test reports.tests.test_ventas_netas_relay`
