# Design: Informe DABRA consolidado remitos

**Change:** `reports-dabra-consolidado-remitos` · **Spec:** [specs/reports-dabra-consolidado-remitos/spec.md](./specs/reports-dabra-consolidado-remitos/spec.md)
**Patrón de referencia:** `reports-cobranzas-vendedor` (servicio + relay + `ReportDefinition` + template dedicado).
**Evidencia LAN** (`192.168.0.2:30804/administranet`, BEST SOX, FA 24/07/2026 PV 0008, `CodigoMovimiento` 1194/1200/1204/1207).

## Technical Approach

Servicio de lectura sobre MySQL legacy (`core.mysql_pool`, `base_empresa` de sesión) que materializa filas línea×remito, calcula alarmas y validación de totales, y devuelve un payload único que alimenta preview (JSON) y export (openpyxl). El exporter no consulta la base: consume el payload del servicio, garantizando paridad preview↔Excel.

## Architecture Decisions

| # | Decisión | Elección | Alternativa rechazada | Rationale (evidencia) |
|---|---|---|---|---|
| 1 | Multi-remito por FA | Expandir: repetir cada línea de FA por cada remito de `rem_fact` (`Anulado='No'`) → `CompRef`/`NumeroRef` del remito. 0 remitos ⇒ refs vacías + alarma (fila igualmente exportada) | Un solo remito (MIN) o concatenar refs | Producto: “un pedido por remito”; conserva trazabilidad. La expansión **duplica importes**, por eso la validación Σ (dec. 4) corre **antes** de expandir, sobre líneas únicas |
| 2 | Entrega / Suc | `cliente_domicilio.NroCalle` vía `cliente_datos_adicionales.id_cliente_domicilio` del `CodigoMovimiento` del **REM**; por bloque de remito. Sin remito ⇒ fallback al domicilio de la FA + alarma; si tampoco, vacío | Domicilio del cliente maestro | Dato real: REM 1205 → `id_cliente_domicilio=46` → `NroCalle='178'` (nro de sucursal DABRA, no calle) |
| 3 | PuntoVenta / NumeroLegal | Parsear `NroComprobante` `^0*(\d+)-0*(\d+)$` → PV int, legal int. Columna `PuntoVenta` con zero-pad 5; `NumeroLegal` int con máscara 8. String tipo sample = **letra + PV(4) + legal(8)**: FA→`A`, REM→`R` (mapa `FA:A, FB:B, FC:C, FE:E, FM:M`) | Usar `id_pv`/`NroCompBusq` | Real: `0008-00000004`; sample `A000400020777` / `R000100027655` descompone en letra+4+8 |
| 4 | Validación importes | Por FA: Σ `Cantidad×PrecioNetoxU` vs `SubTotal1`, y Σ `Cantidad×(PrecioNetoxU+PrecioIVAxU)` vs `ImporteVenta`. Tolerancia `max(0.05, 0.01×n_lineas)`. Fuera de tolerancia ⇒ `errores[]`, **export 409**; preview muestra el error | Igualdad exacta | FA 1200 (31 líneas) difiere 0,02 en IVA por redondeo por línea: la igualdad exacta bloquearía datos válidos |
| 5 | Bonificación línea | `bonif % = pordesc_bonif if pordesc_bonif≠0 else PorDesc` (Decimal) | Sólo `PorDesc` | Ambos campos son 0 en todas las FA DABRA existentes ⇒ no discriminable con datos; la regla cubre ambos orígenes sin recalcular importes |
| 6 | IVA y precios de línea | Alícuota % = `stock.imp_alicuota_iva`; **no** `stock.Alicuota` (es código: vale `1.00` con IVA 21%). Precio unitario neto pre-bonif = `PrecioVentaxU`; Importe = `Cantidad×PrecioNetoxU`; IVA = `Cantidad×PrecioIVAxU` | Usar `PrecioBrutoxU` como bruto pre-bonif | `PrecioBrutoxU` = neto×1,21 (IVA incluido), no es bruto pre-bonificación |
| 7 | Item / Talle / Categoría | `articulo.CodArtProv` split por último espacio: item = prefijo, talle = último token. Categoría = `subrubro.NombreSubRubro` si es significativo, si no `ACCESORIOS` | Parsear `NombreArticulo` | Real: `CodArtProv='888869-10 XL'`; rubro/subrubro son placeholders (`Rubro 1`) ⇒ default aplica |
| 8 | Slug / permiso / CUIT | Slug `dabra-consolidado-remitos`; permiso `reports.dabra_consolidado_remitos` (clase `DabraConsolidadoRemitosPermission`); CUIT emisor de `datosempresa.CUIT` normalizado a 11 dígitos | Reusar `reports.view_operational`; CUIT hardcode | Informe con dato sensible de un cliente; `datosempresa.CUIT='30-69074961-7'` es la fuente por base |
| 9 | TOTAL FACTURAS | Una fila **por FA** (no por par FA+REM): `Comprobante`(letra+PV4+legal8), `Nro Remito` (primer remito; alarma si >1), `Imp Neto=SubTotal1`, `Imp Bruto=ImporteVenta` | Una fila por par FA+REM | El sample resume cabeceras; evita duplicar importes al expandir remitos |

## Data Flow

    Dashboard (mes, año) ──→ Relay API ──→ servicio dabra_consolidado_remitos
                                              │  MySQL (base_empresa sesión)
                                              │  cuentacliente ⨝ stock ⨝ articulo
                                              │  ⨝ rem_fact ⨝ comp_ped ⨝ cda ⨝ cliente_domicilio
                                              ▼
                              payload {filas, totales_facturas, alarmas, errores}
                                    │                           │
                             preview JSON (tabs)         exporter openpyxl → DABRA MMYYYY.xlsx
                                                          (409 si errores)

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `reports/services/dabra_consolidado_remitos.py` | Create | SQL parametrizado, materialización línea×remito, alarmas, validación Σ, `COLUMNS_PREVIEW` |
| `reports/services/dabra_consolidado_remitos_export.py` | Create | Exporter openpyxl: hojas `REPORTE` (A–AW, O/P vacías, Y–AW=0, sin `NombreArticulo`) y `TOTAL FACTURAS`; `HttpResponse` con nombre `DABRA MMYYYY.xlsx` |
| `reports/dabra_consolidado_remitos_relay_views.py` | Create | `...RelayAPIView` (GET preview) y `...ExportAPIView` (GET xlsx); valida `mes`/`anio` (400) y errores Σ (409) |
| `reports/api_urls.py` | Modify | `dabra-consolidado-remitos/relay/` y `.../relay/export/` |
| `reports/permissions.py` | Modify | `DabraConsolidadoRemitosPermission` |
| `core/constantes_permisos.py` | Modify | `("reports.dabra_consolidado_remitos", "Informe DABRA consolidado remitos")` |
| `reports/views.py` | Modify | Slug → template dedicado + contexto (`dabra_api_url`, `dabra_export_url`) |
| `reports/templates/reports/dashboard_dabra_consolidado_remitos.html` | Create | Canon reportes: filtros Mes/Año, tabs REPORTE / TOTAL FACTURAS, panel alarmas/errores, botón Exportar; feedback `SynapMessages` (sin diálogos nativos) |
| `reports/templates/reports/includes/filters_mes_anio.html` | Create | Include de filtros Mes (1–12) + Año |
| `reports/migrations/0032_add_dabra_consolidado_remitos_report.py` | Create | `ReportDefinition` slug con guarda de tabla y `reverse` (patrón `0030`) |
| `reports/tests/test_dabra_consolidado_remitos.py` | Create | Servicio (mock cursor), parseos, tolerancia Σ, relay y exporter |
| `docs/reports/INFORME_DABRA_CONSOLIDADO_REMITOS.md` | Create | Mapeo columna↔campo legacy, alarmas, override dev |

## Interfaces / Contracts

```python
def get_dabra_consolidado_remitos(base_empresa: str, *, mes: int, anio: int) -> Dict[str, Any]:
    """{'columns', 'filas', 'totales_facturas', 'alarmas', 'errores', 'meta'}"""

def exportar_dabra_xlsx(payload: Dict[str, Any], *, mes: int, anio: int) -> HttpResponse
```

Cada fila: `codigo_movimiento, punto_venta, numero_legal, comprobante, fecha, cae, vto_cae, cuit_emisor, doc_type=1, comp_ref, numero_ref, nro_remito, entrega, suc, item, talle, categoria, nombre_articulo (solo preview), cantidad, precio_unitario, bonificacion, alicuota_iva, importe, importe_iva`. Montos `Decimal` internos, `float` en JSON; fechas `dd/MM/yyyy` en UI/Excel. Normalización vía `core.utils.administranet_types`.

## Testing Strategy

| Layer | Qué | Cómo |
|-------|-----|------|
| Unit | Parse `NroComprobante`, letra por tipo, `CodArtProv`→item/talle, bonif fallback, tolerancia Σ, default `ACCESORIOS` | Funciones puras |
| Unit | SQL parametrizado (mes/año, `Codigo=368`, `TipoComprobante='FA'`, `Anulado='No'`, CAE presente) | Mock cursor |
| Integration | Relay 403 sin permiso, 400 sin mes/año, 409 con mismatch Σ; expansión multi-remito | APIClient + servicio mockeado |
| Integration | Exporter: 2 hojas, nombre archivo, O/P vacías, Y–AW=0, sin `NombreArticulo` | openpyxl en memoria |
| Manual | Paridad vs sample `DABRA MMYYYY.xlsx` con FA 24/07/2026 PV 0008 | `docker exec Synap_app` + override dev |

Ejecución: `docker exec Synap_app python manage.py test reports.tests.test_dabra_consolidado_remitos`.

## Migration / Rollout

Sin DDL MySQL. Migration Django solo crea `ReportDefinition` (reversible). Alta del permiso a los perfiles autorizados.
**Override dev:** no se modifica `.env`; se valida seteando `base_empresa` de la sesión (o fixture de test con esa base) hacia la instancia LAN BEST SOX. El código de producción usa siempre `base_empresa` de sesión.

## Open Questions

- [ ] Zero-pad del PV: producto pide 5 en columna `PuntoVenta`, el string del sample usa 4 (`A0004...`). Confirmar contra sample antes de fijar el formato.
- [ ] Regla de bonificación no verificable con datos (todo en 0): validar con una FA DABRA con bonificación real.
- [ ] Semántica exacta de `CompRef` vs `NumeroRef` en el sample (tipo vs número de remito) a confirmar en la primera comparación.
