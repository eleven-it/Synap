# Smoke — APIs e-com mayoristapp (Fase D)

**Referencia:** [VALIDACION_FINAL.md](./VALIDACION_FINAL.md) §1.  
**Entorno:** sustituir host/puerto y cookies según despliegue.

## Sin autenticación

```bash
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/ecom/api/health/
curl -s http://127.0.0.1:8000/ecom/api/migration-info/ | head -c 400
curl -s http://127.0.0.1:8000/ecom/api/mayoristapp/relay-inventory/ | head -c 400
```

Comprobar en `migration-info` el arreglo `checkpoints` (verticales cerrados en Fase C).

Evidencia de referencia (2026-03-31, smoke técnico sin sesión vía `manage.py shell` + `django.test.Client`):

- `health`: 200
- `migration-info`: 200 (`mayoristapp_php_file_count=1276`)
- `relay-inventory`: 200 (`mayoristapp_relay_count=44`)

## Con sesión (POST mayoristapp)

Tras login en Synap, guardar cookies y usar **CSRF** en POST desde navegador. Para prueba manual con `curl`:

1. Obtener `csrftoken` y `sessionid` (login vía formulario o herramienta).
2. Enviar header `X-CSRFToken: <valor>` y cookie `Cookie: sessionid=...; csrftoken=...`.

Ejemplo de cuerpo mínimo (listado pedidos, mismo origen que la app):

```bash
curl -s -X POST 'http://127.0.0.1:8000/ecom/api/mayoristapp/comprobantes/pedidos/?ajax=1' \
  -H 'Content-Type: application/json' \
  -H 'X-CSRFToken: <TOKEN>' \
  -b 'sessionid=<SID>; csrftoken=<TOKEN>' \
  -d '{"vendedor":"true","campoBusca":"-"}'
```

Sin CSRF válido, Django devolverá **403** en métodos inseguros (comportamiento esperado en producción).

Script reusable para entorno objetivo (sesión real + CSRF real):

```bash
BASE_URL="http://127.0.0.1:8000" \
SESSION_ID="<SID>" \
CSRF_TOKEN="<TOKEN>" \
./scripts/fase_d_smoke_manual.sh
```

## Tests automatizados

```bash
docker exec Synap_app python manage.py test ecom.tests.test_fase_d_csrf_smoke -v 2
docker exec Synap_app python manage.py test ecom
docker exec Synap_app pytest /app/ecom/tests/ -q
```
