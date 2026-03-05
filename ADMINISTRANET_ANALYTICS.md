# administraNET Analytics

Fork de Synap diseñado específicamente para análisis y reportes de administraNET Gestión.

## Características

- ✅ Autenticación directa con MySQL de administraNET Gestión
- ✅ Selección de empresa en el login
- ✅ Compatibilidad con usuarios existentes de administraNET
- ✅ Módulos habilitados: Core, Dashboard, Reports, Reports AI
- ✅ Módulos deshabilitados: Sales, Inventory, Purchases, TiendaNube, etc.

## Configuración

### Variables de Entorno

El sistema utiliza las siguientes variables del archivo `.env`:

```bash
# Base de datos MySQL (administraNET)
DB_NAME=administranet
DB_USER=administranet
DB_PASSWORD=a7v8xx0805
DB_HOST=190.15.214.142  # IP del servidor MySQL
DB_PORT=3306
```

Estas variables se leen automáticamente desde el archivo `.env` y se usan para la conexión a la base de datos MySQL de administraNET Gestión.

### Base de Datos

El sistema se conecta directamente a la base de datos MySQL de administraNET Gestión usando:
- Base `empresas`: Para obtener lista de empresas disponibles
- Base específica de empresa: Para validar usuarios y cargar datos

## Autenticación

### Flujo de Login

1. Usuario selecciona servidor (por defecto el configurado)
2. Usuario selecciona empresa del dropdown
3. Usuario ingresa código de usuario y contraseña
4. Sistema valida contra MySQL usando `AES_DECRYPT(password_usuario, 'a7v8xx2')`
5. Se crea sesión en tabla `sesion` de administraNET
6. Se guarda información en sesión Django

### Estructura de Sesión

```python
request.session["user"] = {
    "id_usuario": int,
    "cod_usuario": str,
    "nombre_usuario": str,
    "apellido_usuario": str,
    "nombre_completo": str,
    "id_empresa": int,
    "id_sucursal": int,
    "id_puesto": int,
    "base_empresa": str,  # Nombre de la base de datos
    "idioma": str,  # 'es', 'en', 'pt'
    "id_sesion": int  # ID de sesión en administraNET
}
```

## Archivos Modificados/Creados

### Nuevos Archivos

- `login/administranet_auth.py`: Servicio de autenticación con administraNET
- `login/templates/login/login_administranet.html`: Template de login nuevo

### Archivos Modificados

- `login/views.py`: Reemplazada lógica de Firebase por administraNET
- `login/urls.py`: Actualizadas rutas (removidas Firebase)
- `core/middleware/base_middleware.py`: Actualizado para soportar nueva estructura de sesión
- `django_project/settings.py`: 
  - Deshabilitados módulos no necesarios
  - Configurada conexión MySQL
  - Removidas configuraciones de Firebase

## Compatibilidad

El sistema mantiene compatibilidad con el código existente mediante un objeto usuario mock (`AdministraNETUser`) que implementa la interfaz esperada por el middleware y vistas existentes.

## Próximos Pasos

1. Implementar selección de servidor desde archivo `conexion.txt`
2. Agregar validación de permisos desde tabla `permisos_sistema`
3. Implementar sincronización de datos si es necesario
4. Agregar tests de autenticación

## Notas de Seguridad

- Las contraseñas se validan usando `AES_DECRYPT` con la clave `'a7v8xx2'` (misma que administraNET Gestión)
- Las sesiones se registran en la tabla `sesion` de administraNET
- Se recomienda usar HTTPS en producción
- Considerar implementar rate limiting adicional

