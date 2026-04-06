# Migración administraNET-ecom → Synap

**Código fuente PHP:** repositorio `git@github.com:licPflores/administraNET-ecom.git` (clonar como `administraNET-ecom` en el entorno de desarrollo).

## Alcance entregado (fase inicial)

- Documentación de ingeniería inversa: [REVERSE_ENGINEERING.md](./REVERSE_ENGINEERING.md).
- **Migración focalizada `mayoristapp/`** y cruce con `administraNET-ecom/docs`: [MAYORISTAPP_MIGRATION.md](./MAYORISTAPP_MIGRATION.md).
- **Plan por fases (A–D) e inventario de relays:** [PLAN_FASES_MAYORISTAPP.md](./PLAN_FASES_MAYORISTAPP.md), [CHECKLIST_FASES_MAYORISTAPP.md](./CHECKLIST_FASES_MAYORISTAPP.md), [MAYORISTAPP_RELAYS.md](./MAYORISTAPP_RELAYS.md).
- **Relay catálogo rubros:** [SPEC_CATALOGO_RUBRO.md](./SPEC_CATALOGO_RUBRO.md).
- **Fase B — índice specs por vertical:** [MAYORISTAPP_SPEC_INDICE.md](./MAYORISTAPP_SPEC_INDICE.md).
- Especificación: [SPEC.md](./SPEC.md).
- App Django `ecom` con:
  - API de metadatos de paridad: `GET /ecom/api/migration-info/`
  - Health: `GET /ecom/api/health/`
  - Modelo `EcomMigrationCheckpoint` (PostgreSQL) para marcar submódulos migrados.

## Despliegue

1. Instalar dependencias de desarrollo (tests): `pip install -r requirements-dev.txt`
2. Migraciones: `python manage.py migrate ecom`
3. URLs montadas en `django_project/urls.py` bajo el prefijo `/ecom/`.

## Tests

En el contenedor de la app (recomendado en este proyecto):

```bash
docker exec Synap_app pip install -r requirements-dev.txt
docker exec Synap_app python -m pytest ecom/tests/ -v --cov=ecom --cov-report=term-missing
```

Criterio: cobertura del paquete `ecom` ≥ 80% (la implementación actual supera ese umbral).

### Calculador de precios (paridad PHP parcial)

- Servicio: `ecom.services.price_calculator` (solo `Decimal`).
- Tests unitarios y regresión: `ecom/tests/test_price_calculator.py`, `test_price_regression.py`.
- Integración MySQL (opcional): `ecom/tests/test_price_integration.py` con `@pytest.mark.integration`.
- Documentación: [SPEC_PRECIOS.md](./SPEC_PRECIOS.md) sección G.

## Paridad con PHP

Los valores expuestos en `/ecom/api/migration-info/` deben coincidir con el Apéndice A de `REVERSE_ENGINEERING.md`. Los tests en `ecom/tests/test_parity.py` validan esa coincidencia.

## OpenAPI / Swagger

No aplica en esta fase (respuestas JSON sin DRF). Cuando se expongan viewsets DRF, registrar esquemas en el proyecto.

## Rama Staging

Según política del repositorio, la carpeta `docs/` no se mergea a Staging; el código de `ecom/` sí.
