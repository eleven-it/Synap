# Validación final — checklist (plantilla)

## 1. Smoke end-to-end

Guía ampliada (mayoristapp, CSRF, checkpoints): [SMOKE_MAYORISTAPP.md](./SMOKE_MAYORISTAPP.md).

Ejecutar contra entorno de desarrollo:

```bash
curl -s http://127.0.0.1:8000/ecom/api/health/
curl -s http://127.0.0.1:8000/ecom/api/migration-info/
curl -s http://127.0.0.1:8000/ecom/api/mayoristapp/relay-inventory/
# Con sesión autenticada y base_empresa:
curl -s -b cookies.txt 'http://127.0.0.1:8000/ecom/api/mayoristapp/catalogo/rubros/?idcategoria=1&ajax=1'
```

Comparar `migration-info` con [REVERSE_ENGINEERING.md](./REVERSE_ENGINEERING.md) Apéndice A. El `relay-inventory` debe tener 44 entradas y coincidir con [MAYORISTAPP_RELAYS.md](./MAYORISTAPP_RELAYS.md). Catálogo rubros: [SPEC_CATALOGO_RUBRO.md](./SPEC_CATALOGO_RUBRO.md). El arreglo `checkpoints` refleja verticales cerrados en Fase C.

## 2. [DECISION PENDIENTE] en SPEC.md

Revisar etiquetas en [SPEC.md](./SPEC.md) y cerrar o documentar en actas de equipo.

## 3. Checklist de seguridad

- [ ] `SECRET_KEY` solo desde entorno en producción
- [ ] `DEBUG=False` en producción
- [ ] `ALLOWED_HOSTS` acotado
- [ ] CSRF en formularios web (futuras pantallas e-com)
- [ ] ORM / consultas parametrizadas en `legacy_db` (sin concatenar SQL con entrada usuario)
- [ ] Contraseñas: PBKDF2 de Django, no AES legacy en nuevas rutas
- [ ] Credenciales y API keys en variables de entorno

### API e-com con sesión (`EcomMayoristappSessionPermission`)

Los POST bajo `/ecom/api/mayoristapp/…` usan sesión de usuario (cookies). Con **SessionAuthentication** de DRF, las peticiones mutantes desde navegador requieren **CSRF** (cookie + header `X-CSRFToken`). Clientes desde el mismo origen de Synap deben usar el token que expone Django (`csrf_token` en plantillas o cookie `csrftoken`). Llamadas servidor-a-servidor o tests que usan `APIClient`/`force_authenticate` no sustituyen el checklist de integración en navegador.

**Fase D:** además de validación manual en staging, correr smoke automatizado CSRF:

```bash
docker exec Synap_app python manage.py test ecom.tests.test_fase_d_csrf_smoke -v 2
```

Resultado de referencia (2026-03-31): **OK (2/2)**.

## 4. Funcionalidad PHP no migrada (inicial)

| Área | Motivo |
|------|--------|
| ~1280 scripts PHP de negocio | Fuera del alcance de esta entrega; plan por submódulos |
| Carrito `tmobile/jcart` | Pendiente especificación móvil |
| mPDF / Excel embebidos | Sustituir por reportes Synap / exportaciones existentes |

## 5. Referencia

Tests automatizados: `ecom/tests/test_parity.py`, `ecom/tests/test_views.py`.
