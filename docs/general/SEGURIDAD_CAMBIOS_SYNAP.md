# Cambios de seguridad en Synap (Django)

Documento de referencia que consolida **todas las mitigaciones de seguridad** incorporadas en el código (autenticación, APIs, configuración, XSS, rate limiting, medios y despliegue). Está alineado con el plan de producción ([PLAN_PRINCIPAL_FODA_BRECHAS_SYNAP.md](PLAN_PRINCIPAL_FODA_BRECHAS_SYNAP.md)) y con variables de entorno descritas en [.env.example](../../.env.example).

Para el contrato **Support ↔ RAG** (JWT, entornos), ver además [SEGURIDAD_API_SUPPORT_RAG.md](SEGURIDAD_API_SUPPORT_RAG.md).

---

## 1. Configuración y secretos (`django_project/settings.py`)

| Cambio | Descripción |
|--------|-------------|
| **`SECRET_KEY`** | Si `ENVIRONMENT` es `production` o `produccion`, es **obligatorio** definir `SECRET_KEY` no vacía en el entorno; en caso contrario se lanza `ImproperlyConfigured`. En desarrollo puede omitirse (se usa un placeholder solo para arranque local). |
| **`DB_PASSWORD` (MySQL)** | En producción/producción, **obligatorio** no vacío; sin default inseguro en código. |
| **`POSTGRES_PASSWORD`** | Misma regla en producción/producción. Fuera de producción, si está vacío se puede usar el valor por defecto de desarrollo documentado en `.env.example`. |
| **`DEBUG` duplicado** | Eliminada asignación duplicada; una sola lectura desde `decouple`. |
| **`SUPPORT_SYNAP_JWT_SECRET`** | Secret compartido con el backend Support para validar `Authorization: Bearer` en el endpoint de conocimiento RAG. |
| **`GOOGLE_GEOCODING_API_KEY`** | Clave de geocodificación **solo servidor**; el cliente ya no puede enviar `key` en la query. |
| **`ADMINISTRANET_MYSQL_AES_KEY`** | Clave AES para `AES_DECRYPT` de contraseñas en MySQL (paridad AdministraNET); configurable por env, default histórico `a7v8xx2`. |
| **Cookies en producción** | Con `ENVIRONMENT` production/produccion: `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`. |
| **`SESSION_COOKIE_HTTPONLY`** | Explícito `True` (sesión no legible por JS). |
| **`SECURE_CONTENT_TYPE_NOSNIFF`** | `True` (cabecera `X-Content-Type-Options: nosniff`). |
| **Logging raíz** | Nivel `INFO` cuando `DEBUG` es False; `DEBUG` cuando `DEBUG` es True (menos ruido en producción). |

---

## 2. Login y CSRF (`login/views.py`)

| Cambio | Descripción |
|--------|-------------|
| **Eliminado `@csrf_exempt`** | El POST de login queda protegido por el middleware CSRF estándar. |
| **`@ensure_csrf_cookie`** | Garantiza cookie `csrftoken` en GET para que el `fetch` del formulario (plantillas login) envíe `X-CSRFToken`. |
| **Errores genéricos** | Las excepciones no devuelven `str(e)` al cliente; mensajes en español y registro en log con `exc_info`. |
| **`JSONDecodeError`** | Respuesta 400 con mensaje genérico, sin detalle interno. |
| **Rate limiting POST login** | Límite por IP (ventana 5 minutos) vía `core.utils.rate_limit.check_rate_limit` para mitigar fuerza bruta. Si el cache/Redis no está disponible, se omite el límite y se registra un warning (no se bloquea el login en local). |

---

## 3. Autenticación MySQL (`login/administranet_auth.py`)

| Cambio | Descripción |
|--------|-------------|
| **AES en consulta SQL** | La clave de `AES_DECRYPT` se pasa como **parámetro** (`%s`), no embebida como literal en la cadena SQL. |
| **Origen de la clave** | `settings.ADMINISTRANET_MYSQL_AES_KEY` (variable de entorno recomendada en producción). |

---

## 4. API conocimiento RAG (`core/api/views.py`)

| Cambio | Descripción |
|--------|-------------|
| **`_support_rag_auth_error_response`** | Producción sin secret configurado → **503**. Producción con secret → JWT HS256 con `exp` obligatorio. |
| **Desarrollo / staging** | Sin secret: acceso sin token **solo** si `DEBUG=True`. Con `DEBUG=False` y sin secret → **503** (evita staging abierto). Con secret definido → JWT obligatorio igual que en pruebas alineadas a prod. |

Tests: `core/tests/test_support_conocimiento_api.py`.

---

## 5. APIs JSON auxiliares (`core/api/views.py`)

| Cambio | Descripción |
|--------|-------------|
| **`_json_session_required`** | Comprueba `request.session["user"]` (sesión administraNET) y responde **401** si falta. |
| **Vistas afectadas** | Búsquedas (contactos, países, responsabilidades fiscales, estados, monedas), `fecha_servidor_api`, `geocode_api`. |
| **`geocode_api`** | Requiere sesión; usa solo `GOOGLE_GEOCODING_API_KEY`; **503** sin clave; **502** con mensaje genérico si falla la red (sin filtrar excepciones crudas). |
| **`get_empresas_api`** (`login/views.py`) | Sigue **pública** (flujo previo al login); añadido **rate limit** por IP y mensaje de error genérico en 500 (sin `str(e)`). |

**Nota:** `get_empresas_api` no exige sesión por diseño; el rate limit reduce abuso de enumeración.

---

## 6. Tipos de envío por sucursal (IDOR) (`core/api/views.py`, `core/services/administranet_sucursales.py`)

| Cambio | Descripción |
|--------|-------------|
| **`_session_user_can_access_sucursal`** | Solo usuarios **admin** (supervisor administraNET vía `user.is_admin()`) o cuyo `id_sucursal` de sesión coincide con el `id_sucursal` de la URL pueden operar. |
| **`tipo_envio_pertenece_a_sucursal`** | Antes de PUT/DELETE sobre un tipo de envío, se verifica que el registro en `sucursales_envios` pertenezca a la sucursal indicada en la URL (columnas `id_sucursal` / `id_sucusal` según esquema). |

---

## 7. Archivos media (`core/views/media_views.py`)

| Cambio | Descripción |
|--------|-------------|
| **`PUBLIC_MEDIA_PREFIXES`** | Prefijo `empresas/logos/` accesible **sin sesión** (logos en pantalla de login). |
| **Resto de rutas** | Requieren `request.session["user"]`; si no, **404** (sin revelar existencia del recurso). |
| **Path traversal** | Se mantiene la validación de ruta bajo `MEDIA_ROOT`. |

---

## 8. Reportes y dashboard (XSS)

| Área | Cambio |
|------|--------|
| **Reportes declarativos** | `reports/views.py` expone `report_config_for_script`; la plantilla `reports/dashboard_detail.html` usa `|json_script` y `JSON.parse` para `window.REPORT_CONFIG` (evita ruptura por `</script>` en datos de BD). |
| **Dashboard** | `dashboard/views.py` añade `chart_js_bundle`; `dashboard/templates/dashboard/dashboard.html` usa `json_script` para datos del gráfico en lugar de `{{ ... \|safe }}`. |

Documentación de análisis actualizada en `docs/reports/ANALISIS_VENTAS_NETAS.md` (referencia a `report_config_for_script`).

---

## 9. Plantillas: reducción de `|safe` (`core/templatetags/security_extras.py`)

| Filtro | Uso |
|--------|-----|
| **`safe_svg_icon`** | Iconos SVG de menú / módulos (`floating_menu`, `dashboard_apps`, `module_menu_item`, botón de acción en `crud_subheader` si aplica). |
| **`safe_ui_slot`** | Slots HTML de filtros y chips en `crud_subheader` (bleach con etiquetas de formulario acotadas). |

Implementación con **bleach**; se eliminan scripts y atributos peligrosos según listas blancas.

---

## 10. `set-device-hint` (`core/views/device_views.py`)

| Cambio | Descripción |
|--------|-------------|
| **`@csrf_protect`** | Sustituye `csrf_exempt`; quien integre POST debe enviar token CSRF. |

Documentado en [SEGURIDAD_API_SUPPORT_RAG.md](SEGURIDAD_API_SUPPORT_RAG.md).

---

## 11. Limpieza de imports (`core/views/views.py`)

Eliminado import no usado de `csrf_exempt` (las vistas relevantes usan `csrf_protect` donde corresponde).

---

## 12. Utilidades (`core/utils/rate_limit.py`)

- **`client_ip`**: respeta `X-Forwarded-For` (primer hop).
- **`check_rate_limit`**: contador por IP con `cache.incr`; tolera fallo de cache (warning y sin bloqueo).

---

## 13. Variables de entorno y ejemplos

- **[.env.example](../../.env.example)**: `SECRET_KEY`, `POSTGRES_PASSWORD`, `DB_PASSWORD`, `SUPPORT_SYNAP_JWT_SECRET`, `GOOGLE_GEOCODING_API_KEY`, `ADMINISTRANET_MYSQL_AES_KEY`, comentarios de obligatoriedad en producción.
- **Support**: comentarios en `support/.env.example` y `support/backend/.env.example` sobre JWT obligatorio frente a Synap en producción.

---

## 14. Despliegue y operación

1. En **producción**: definir `SECRET_KEY`, `POSTGRES_PASSWORD`, `DB_PASSWORD`, `SUPPORT_SYNAP_JWT_SECRET` (y Support con el mismo JWT), `GOOGLE_GEOCODING_API_KEY` si se usa geocodificación, y `ADMINISTRANET_MYSQL_AES_KEY` alineada a AdministraNET Gestión.
2. **Redis/cache**: necesario para rate limiting efectivo; sin Redis el login no se bloquea por límite pero puede registrar warnings.
3. **Tests automatizados**: ejecutar en contenedor según [.cursorrules](../../.cursorrules): `docker exec Synap_app python manage.py test core.tests.test_support_conocimiento_api`.

---

## 15. Referencias rápidas de archivos

| Tema | Archivos principales |
|------|------------------------|
| Settings | `django_project/settings.py` |
| Login / empresas / rate limit | `login/views.py` |
| Auth MySQL | `login/administranet_auth.py` |
| APIs core | `core/api/views.py` |
| Sucursales / tipos envío | `core/services/administranet_sucursales.py` |
| Media | `core/views/media_views.py` |
| Device hint | `core/views/device_views.py` |
| Rate limit | `core/utils/rate_limit.py` |
| Filtros XSS | `core/templatetags/security_extras.py` |
| Reportes | `reports/views.py`, `reports/templates/reports/dashboard_detail.html` |
| Dashboard | `dashboard/views.py`, `dashboard/templates/dashboard/dashboard.html` |
| Tests RAG | `core/tests/test_support_conocimiento_api.py` |

---

*Última actualización: documentación de la rama de endurecimiento de seguridad (sesiones de auditoría y mitigación).*
