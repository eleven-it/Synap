# Flujo proveedor en captura/aprobación de factura compra

## Regla de resolución

El flujo de revisión de expedientes aplica esta prioridad obligatoria:

1. Buscar proveedor en AdministraNET por CUIT (`buscar_proveedores`, misma base que remitos/compras).
2. Si existe: vincular `codigo_proveedor_legacy` y usar datos legacy.
3. Si no existe: consultar **padrón AFIP** con la misma infraestructura que self-checkout/TPV (`consultar_condicion_fiscal`: certificados FE, padrón A5 con fallback A5).
4. Si AFIP responde correctamente: **alta del proveedor en AdministraNET** (`crear_proveedor_desde_borrador`) y asignación del código.
5. Si AFIP no está configurado o falla: se devuelve borrador parcial en `metadata.proveedor_synap` sin código (el usuario puede completar datos o corregir CUIT).

Tras **Resolver proveedor** (POST), si quedó código y el expediente está en `borrador` u `ocr_completado`, se intenta **enviar a revisión** automáticamente; si faltan líneas o artículos, la API devuelve `enviar_revision: { realizado: false, detail: ... }` y el usuario puede guardar y reintentar.

### Carga automática del código legacy (GET expediente)

En cada **GET** `/api/compras/expedientes/<id>/`, si `codigo_proveedor_legacy` es nulo y hay un CUIT de 11 dígitos en `metadata.proveedor_synap` o en el OCR del último documento completado (`campos_cabecera.proveedor_cuit_texto`), se ejecuta la misma resolución que el botón **Resolver proveedor** (búsqueda en AdministraNET primero) y se persiste el resultado. Así la pantalla de revisión muestra el código sin paso manual cuando el CUIT ya está identificado.

## Metadata usada en expediente

Se persiste en `ExpedienteFacturaCompra.metadata.proveedor_synap`:

- `modo`: `legacy_vinculado` o `borrador_nuevo`
- `cuit`
- `razon_social`
- `tipo_factura_sugerida` (cuando proviene de AFIP)
- `padron_detalle` (errores o detalle técnico de AFIP)
- `origen`
- `actualizado_en`

## Aprobación

Antes de mapear a `LegacyPostingCommandV1`:

1. Si el expediente no tiene `codigo_proveedor_legacy`, se reintenta lookup por CUIT en MySQL legacy.
2. Si sigue sin existir, se crea proveedor en `proveedor` con datos mínimos del borrador.
3. Recién luego corre validación y posting de comprobante.

Esto garantiza la secuencia pedida: proveedor legacy primero, comprobante después.
