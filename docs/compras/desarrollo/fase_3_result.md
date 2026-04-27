# Resultado Fase 3 — Revisión humana y aprobación sin posting real

**Referencias:** [docs/compras/master_execution_plan.md](../master_execution_plan.md), [docs/compras/definition_of_done_by_phase.md](../definition_of_done_by_phase.md), [docs/compras/posting_contract.md](../posting_contract.md), ADR-0006.

## Flujo completo de revisión

1. Edición de cabecera y líneas con `PATCH /api/compras/expedientes/<uuid>/`.
2. Transiciones de revisión con `POST /api/compras/expedientes/<uuid>/transiciones/` (`enviar_revision`, `marcar_listo_para_aprobar`, `solicitar_aprobacion`, `rechazar`).
3. Aprobación sin posting real con `POST /api/compras/expedientes/<uuid>/aprobar/`.
4. Validación previa del comando v1 (`map_expediente_to_command_v1` + `validate_posting_command`).
5. Ejecución de stub fake (`FakeLegacyPostingAdapter`) con resultado consistente (`codigo_movimiento`, `nro_comprobante`).
6. Auditoría de eventos en `GET /api/compras/expedientes/<uuid>/eventos/`.

## Mapping preliminar a posting

- `ExpedienteFacturaCompra` + `lineas` + `metadata.posting_v1` se mapea a `LegacyPostingCommandV1`.
- Se validan reglas mínimas V-01, V-02, V-04, V-05, V-06, V-07, V-08, V-09 y campos de cabecera.
- No hay escritura en MySQL legacy en esta fase.

## Permisos y UI

- Permisos por codename: `crear`, `ver`, `editar`, `revisar`, `aprobar`, `rechazar`, `reintentar_posting`.
- **Alineación menú Compras / Stock (captura):** acceso web a listado y captura móvil y lecturas API equivalentes (`GET` listado/detalle/eventos/documentos) con `compras.ver` **o** `factura_compra_captura.ver`; alta de expediente y subida inicial de archivo también con `compras.ver` o `factura_compra_captura.crear`. La lógica compartida vive en `factura_compra_captura/permisos_modulo.py`.
- **Revisión y documento en iframe:** pantalla `revision` y `DocumentoFuenteServeView` exigen `factura_compra_captura.editar`, empresa activa en sesión y coincidencia con la empresa del expediente; se corrigió el caso en que sin empresa en sesión el PDF quedaba accesible.
- **Reintento OCR (API):** solo `editar` o `reintentar_posting` (no basta con `crear` ni `compras.ver`).
- Pantalla de revisión: `/compras/captura/revision/<uuid>/` (mobile-first + split desktop), con foco en escaneo visual rápido y edición eficiente.

## Congelamiento `LegacyPostingCommand` v1

- Código congelado: `factura_compra_posting/legacy_posting_command_v1.py` y `mapper_v1.py`.
- Gobernanza: [ADR-0006](../adrs/0006-congelamiento-legacy-posting-command-v1.md).

## Estado

- Fase 3 implementada sin posting real.
- Tests de aprobación/rechazo/validaciones/permisos en verde en suite de compras/posting.
