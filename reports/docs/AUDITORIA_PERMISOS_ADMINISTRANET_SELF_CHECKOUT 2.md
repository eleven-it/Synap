# Auditoría de permisos AdministraNET (VB6/MySQL) → Self-Checkout Synap

**Fecha:** 23-01-2025  
**Objetivo:** Mapear e implementar permisos Self-Checkout sobre el modelo AdministraNET.

---

## 1. Modelo de permisos AdministraNET (MySQL)

### 1.1 Tablas identificadas

| Tabla | Uso |
|-------|-----|
| **usuarios** | Usuarios del sistema. Campos: id_usuario, cod_usuario, id_empresa, id_sucursal, id_puesto, id_punto_venta, id_deposito, id_caja, baja_usuario |
| **puestos** | Roles/cargos. Campos: idpuesto, puesto (nombre), anulado |
| **permiso_sistema** | Catálogo de permisos (key_permiso). Usado por Synap para verificación granular |
| **permiso_sistema_puesto** | Asignación permiso↔puesto. Campos: id_permiso_sistema, id_puesto, valor_permiso ('Si'/'No') |
| **permisos_sistema** | Permisos legacy por columnas (Mod_Precio_Fact, acceso_pv, etc.). Una fila por IDPuesto |

**Fuentes:** `core/middleware/base_middleware.py`, `core/services/administranet_permisos_sistema.py`, `login/administranet_auth.py`.

### 1.2 Constantes Self-Checkout (key_permiso)

| key_permiso | Descripción | Alcance |
|-------------|-------------|---------|
| `self_checkout.kiosk` | Operar kiosco (venta, scan, RFID, pago) | Sucursal/pv/deposito asignado |
| `self_checkout.supervisor` | Supervisar kioscos (cancelar, ver audit, resolver errores) | Sucursal asignada |
| `self_checkout.admin` | Admin del módulo (config kioscos, reportes) | Sin restricción |

Definidas en `self_checkout/permissions.py` como `SCO_KIOSK`, `SCO_SUPERVISOR`, `SCO_ADMIN`.

---

## 2. Implementación

### 2.1 Helper `has_permission(user, perm_key, base_empresa)`

**Archivo:** `self_checkout/permissions.py`

- Consulta MySQL: `permiso_sistema` INNER JOIN `permiso_sistema_puesto`
- Usa valor más reciente por `id_permiso_sistema_puesto` (mismo criterio que base_middleware)
- Usuario `supervisor` (cod_usuario) tiene todos los permisos
- Retorna `True` si `valor_permiso = 'Si'` para el permiso y puesto del usuario

### 2.2 Decorator `require_self_checkout_permission(permission)`

**Archivo:** `self_checkout/decorators.py`

- Usa `has_permission()` para verificar contra MySQL
- Protege endpoints API: cart, items, email, confirm, articulo

### 2.3 Middleware `SelfCheckoutPermissionMiddleware`

**Archivo:** `self_checkout/middleware.py`

- Protege rutas `/self-checkout/*` y `/api/self-checkout/*`
- Exige `has_any_self_checkout_permission(user, base_empresa)`
- Respuesta API: 401/403 JSON; web: redirect a login o PermissionDenied

### 2.4 Comando de sincronización

```bash
python manage.py sync_self_checkout_permissions [--base-empresa X] [--dry-run]
```

Inserta `self_checkout.kiosk`, `self_checkout.supervisor`, `self_checkout.admin` en `permiso_sistema` si no existen.

---

## 3. Cómo asignar permisos desde AdministraNET

### 3.1 Opción A: Comando de sincronización (recomendado)

```bash
python manage.py sync_self_checkout_permissions [--base-empresa X]
```

Crea los permisos en `permiso_sistema` si no existen. Luego asignar a puestos vía SQL o desde la UI de AdministraNET si está disponible.

### 3.2 Opción B: Script SQL (manual)

```sql
-- En la base de la empresa (base_empresa)

-- 1. Verificar que los permisos existen
SELECT id_permiso_sistema, key_permiso FROM permiso_sistema
WHERE key_permiso IN ('self_checkout.kiosk', 'self_checkout.supervisor', 'self_checkout.admin');

-- 2. Asignar self_checkout.kiosk al puesto 1 (ej: Cajero)
INSERT INTO permiso_sistema_puesto (id_permiso_sistema, id_puesto, valor_permiso)
SELECT ps.id_permiso_sistema, 1, 'Si'
FROM permiso_sistema ps WHERE ps.key_permiso = 'self_checkout.kiosk'
ON DUPLICATE KEY UPDATE valor_permiso = 'Si';

-- 3. Asignar kiosk + supervisor al puesto 2 (ej: Supervisor)
INSERT INTO permiso_sistema_puesto (id_permiso_sistema, id_puesto, valor_permiso)
SELECT ps.id_permiso_sistema, 2, 'Si'
FROM permiso_sistema ps
WHERE ps.key_permiso IN ('self_checkout.kiosk', 'self_checkout.supervisor');

-- 4. Asignar admin al puesto 3 (ej: Administrador)
INSERT INTO permiso_sistema_puesto (id_permiso_sistema, id_puesto, valor_permiso)
SELECT ps.id_permiso_sistema, 3, 'Si'
FROM permiso_sistema ps WHERE ps.key_permiso = 'self_checkout.admin';
```

### 3.3 Desde AdministraNET (VB6)

Si AdministraNET tiene pantalla de asignación de permisos por puesto: buscar los permisos `self_checkout.kiosk`, `self_checkout.supervisor`, `self_checkout.admin` y marcar "Si" para el puesto deseado. La tabla `permiso_sistema_puesto` se actualiza con id_permiso_sistema, id_puesto, valor_permiso.

---

## 4. Pruebas manuales

### 4.1 Verificar estructura de tablas

```sql
-- En base empresa
DESCRIBE permiso_sistema;
DESCRIBE permiso_sistema_puesto;
DESCRIBE puestos;
DESCRIBE usuarios;
```

### 4.2 Verificar permisos creados

```sql
SELECT id_permiso_sistema, key_permiso, nombre_permiso
FROM permiso_sistema
WHERE key_permiso LIKE 'self_checkout.%';
```

### 4.3 Verificar asignación por puesto

```sql
-- Permisos del puesto X
SELECT ps.key_permiso, psp.valor_permiso
FROM permiso_sistema ps
INNER JOIN permiso_sistema_puesto psp ON ps.id_permiso_sistema = psp.id_permiso_sistema
WHERE psp.id_puesto = 1  -- cambiar por id_puesto a probar
  AND ps.key_permiso LIKE 'self_checkout.%';
```

### 4.4 Simular verificación has_permission

```sql
-- ¿El puesto 1 tiene self_checkout.kiosk?
SELECT 1
FROM permiso_sistema ps
INNER JOIN (
    SELECT psp1.id_permiso_sistema, psp1.valor_permiso
    FROM permiso_sistema_puesto psp1
    INNER JOIN (
        SELECT id_permiso_sistema, MAX(id_permiso_sistema_puesto) as max_id
        FROM permiso_sistema_puesto
        WHERE id_puesto = 1
        GROUP BY id_permiso_sistema
    ) psp2 ON psp1.id_permiso_sistema = psp2.id_permiso_sistema
           AND psp1.id_permiso_sistema_puesto = psp2.max_id
    WHERE psp1.id_puesto = 1 AND psp1.valor_permiso = 'Si'
) psp ON ps.id_permiso_sistema = psp.id_permiso_sistema
WHERE ps.key_permiso = 'self_checkout.kiosk'
LIMIT 1;
-- Si retorna 1 fila → tiene permiso
```

### 4.5 Verificar usuario → puesto

```sql
SELECT u.id_usuario, u.cod_usuario, u.id_puesto, p.puesto
FROM usuarios u
LEFT JOIN puestos p ON p.idpuesto = u.id_puesto
WHERE u.baja_usuario = 'No';
```

### 4.6 Casos de prueba

| Usuario | id_puesto | Permiso asignado | Esperado |
|---------|-----------|------------------|----------|
| cajero | 1 | self_checkout.kiosk | Acceso kiosco y API |
| supervisor | 2 | kiosk + supervisor | Acceso completo |
| admin | 3 | self_checkout.admin | Acceso configuración |
| sin permiso | 4 | (ninguno) | 403 |
| cod_usuario=supervisor | * | (por usuario) | Siempre acceso |

### 4.7 Verificación desde Django shell

```python
from self_checkout.permissions import has_permission, SCO_KIOSK
from core.middleware.base_middleware import get_usuario_extendiendo_desde_sesion

# Simular request con sesión
class MockRequest:
    session = {'user': {'id_puesto': 1, 'base_empresa': 'mi_empresa_db'}}

request = MockRequest()
user = get_usuario_extendiendo_desde_sesion(request)
print(has_permission(user, SCO_KIOSK, 'mi_empresa_db'))  # True/False
```

---

## 5. Resumen

| Elemento | Ubicación |
|----------|-----------|
| Constantes | `self_checkout/permissions.py` (SCO_KIOSK, SCO_SUPERVISOR, SCO_ADMIN) |
| Helper | `has_permission(user, perm_key, base_empresa)` |
| Decorator | `require_self_checkout_permission('kiosk'|'supervisor'|'admin')` |
| Middleware | `SelfCheckoutPermissionMiddleware` en settings |
| Sync permisos | `python manage.py sync_self_checkout_permissions` |
| constantes_permisos | `core/constantes_permisos.py` (módulo Self-Checkout) |
