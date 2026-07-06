# Migración Odoo — API keys y rotación

## Usuario técnico en Odoo

Crear un usuario bot dedicado (ej. `synap_migracion`) con permisos mínimos de lectura/escritura en los modelos que migrará. Dejar contraseña vacía para deshabilitar login interactivo.

## Generación manual (bootstrap)

1. En Odoo: **Preferencias → Seguridad de la cuenta → Nueva clave API**.
2. Descripción: `Synap migración <entorno>`.
3. Duración: máximo **3 meses** (límite Odoo 19).
4. Copiar la clave inmediatamente (no se puede recuperar).
5. En Synap: **Migración Odoo → Conexiones → Nueva/Editar** y pegar la API key.

## Rotación programática

Requiere en Odoo el parámetro `base.enable_programmatic_api_keys = True` (Settings → Technical → System Parameters).

Endpoints JSON-2:

- `POST /json/2/res.users.apikeys/generate` — body: `key`, `scope`, `name`, `expiration_date`
- `POST /json/2/res.users.apikeys/revoke` — body: `key`

### Desde Synap

- UI: botón **Rotar key** en listado de conexiones (solo usuario `supervisor`).
- CLI: `docker exec Synap_app python manage.py odoo_rotate_api_key --connection-id=N`
- Prueba: `docker exec Synap_app python manage.py odoo_test_connection --connection-id=N`

### Reglas de rotación

1. Generar nueva clave **antes** de revocar la anterior.
2. Smoke test con la nueva clave (`res.users/context_get`).
3. Revocar la anterior autenticando con la nueva.
4. Synap alerta en el panel si la clave vence en ≤ 7 días.

## Almacenamiento en Synap

La API key se guarda cifrada en PostgreSQL (`OdooConnection.api_key_encrypted`) derivada de `SECRET_KEY`. En UI solo se muestra máscara (`••••••••••••1234`).

## Referencia

- [External JSON-2 API — Odoo 19](https://www.odoo.com/documentation/19.0/developer/reference/external_api.html)
