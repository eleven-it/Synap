# 28 — Código Muerto y Legacy

**Estado:** COMPLETE (Fase 28)  
**Fecha:** 25/08/2026

---

## Módulos no utilizados

| Módulo | Estado | Evidencia |
|--------|--------|-----------|
| `mtrix/` | **Huérfano** | Solo `__pycache__`, sin fuentes |
| `sia/` | **No instalado** | Completo pero no en INSTALLED_APPS ni urls |
| `mercadopago/` | **Comentado** | No en INSTALLED_APPS; activable via ModuleConfig |
| `dashboard/` | **Stub** | Firebase legacy, funcionalidad en core/ |

## Apps comentadas en settings (código residual posible)

`reports_ai`, `administraNET_integration`, `sales`, `inventory`, `tiendanube`, `accounting`, `purchases`, `clover`, `logistics`, `finance`

## Código comentado/eliminado

| Artefacto | Ubicación | Estado |
|-----------|-----------|--------|
| Celery config | django_project/celery.py | Comentado |
| Firebase auth | login/, FIREBASE_DESHABILITADO.md | Deshabilitado |
| Context processors | settings.py líneas 151-154 | Comentados |
| CDNCacheMiddleware | settings.py | Comentado |
| AuditoriaMiddleware | middleware/__init__.py | No activo |
| RateLimitMiddleware | middleware/__init__.py | No activo |

## Archivos duplicados sospechosos

| Patrón | Ubicación | Acción sugerida |
|--------|-----------|----------------|
| `* 2.py` | fe_afip, factura_compra_captura, self_checkout | Verificar y eliminar duplicados |
| `docker-compose.mysql 2.yml` | Raíz | Eliminar copia |
| `docs/general/PEDIDO_MASIVO_IMPORT_EXCEL 2.md` | docs/ | Eliminar copia |

## Implementaciones reemplazadas

| Viejo | Nuevo | Estado viejo |
|-------|-------|-------------|
| dashboard/ Firebase | core/views dashboard | Stub presente |
| permiso_sistema* | synap_* tables | Dual mode |
| UsuarioExtendido Firebase | AdministraNETUser session | Modelo legacy presente |
| reports_ai | ia/ | App eliminada |
| administraNET_integration | Integrado en módulos | App eliminada |

## Versiones paralelas

| Componente | Versiones | Nota |
|------------|-----------|------|
| Permisos | legacy / synap / dual | Feature flag |
| OCR factura | legacy / preprocess_only / structured_ocr | FACTURA_COMPRA_OCR_ENGINE_MODE |
| Posting compras | fake / noop / legacy | FACTURA_COMPRA_POSTING_BACKEND |

## Feature flags antiguas

| Flag | Default | Nota |
|------|---------|------|
| WEBAUTHN_UNLOCK_ENABLED | False | Marcado deprecado |
| SYNAP_AUTO_SYNC_PERMISSIONS | False | "En desuso" en settings |
| REPORTS_CACHE_ENABLED | False | Desactivado permanentemente? |

---

*No se eliminó código — solo inventario. Generado por auditoría READ ONLY.*
