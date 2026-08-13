# ADR: Versionado API Tienda Nube / Nuvemshop

## Estado

Aceptado — 09/06/2026

## Contexto

Synap integra Tienda Nube vía API HTTP versionada. La documentación oficial referencia **2025-03** como versión actual de integración.

## Decisión

1. **Constante única:** `NUVEMSHOP_API_VERSION = "2025-03"` en `tiendanube_administranet/services/tiendanube_service.py`.
2. **URLs base:** `https://api.tiendanube.com/{version}/{store_id}` (AR/MX) o dominio BR según tienda.
3. **No usar `/v1`** en código nuevo; el campo modelo `TiendanubeConfig.api_url` es referencia/documentación con default alineado a 2025-03.
4. **Header auth:** Mantener `Authentication: bearer {token}` (funciona en producción; distinto del ejemplo docs `Authorization: Bearer`).
5. **Webhooks HMAC:** Cabecera `x-linkedstore-hmac-sha256`, secret en `TiendanubeConfig.webhook_secret`.
6. **Rate limit:** 2 req/s + headers `x-rate-limit-*` + reintentos 429 vía `services/rate_limit.py` en `TiendanubeService._request`. Ver también sync inicial: `docs/ecom/TIENDANUBE_CUSTOMER_MAPPING_HARDENING.md` § Sync inicial por lotes.

## Consecuencias

- Cambio de versión mayor Nuvemshop → actualizar constante, migración default `api_url`, checklist en `docs/ecom/CHECKLIST_HABILITACION_TIENDANUBE_ADMINISTRANET.md` y pruebas smoke.
- Partners API (`partners.tiendanube.com/api/v1`) es API distinta; no mezclar con store API.

## Referencias

- `docs/ecom/TIENDANUBE_WEBHOOKS_API_2025-03.md`
- `docs/ecom/TIENDANUBE_DEUDA_TECNICA_P0_P2.md`
