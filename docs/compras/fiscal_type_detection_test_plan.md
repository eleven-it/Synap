# Plan de pruebas: detección fiscal

## Detección

| ID | Caso | Esperado |
|----|------|----------|
| D1 | Letra C aislada + COD. 011 (texto multilínea) | FC, código 11, consistent |
| D2 | Solo COD. 011 (sin “Factura C” en una línea) | FC |
| D3 | “FACTURA C” en texto | FC |
| D4 | Letra A en texto + COD. 011 | inconsistent, prevalece FC |
| D5 | Sin letra ni código reconocible | adminnet null, unknown |
| D6 | Texto vacío | null, unknown (nunca FA) |

## OCR / layout

| ID | Caso | Esperado |
|----|------|----------|
| D7 | Línea OCR estructurada con FACTURA + letra | structured source |
| D8 | Texto ruidoso con “COD.. 011” o espacios | código 11 |

## Mapeo

| ID | Caso | Esperado |
|----|------|----------|
| D9 | 011 / 11 / 0011 normalizan a 11 | |
| D10 | adminnet_mapping refleja doc AFIP | |

## Parser / UI

| ID | Caso | Esperado |
|----|------|----------|
| D11 | `parsear_cabecera_documento` con C+011 → FC | |
| D12 | Sin tipo, cabecera no fuerza FA | |

Comando: `docker exec Synap_app python manage.py test factura_compra_captura.tests.test_fiscal_type_detector`
