# Firebase Deshabilitado - administraNET Analytics

## Resumen

Firebase ha sido completamente deshabilitado para administraNET Analytics. El sistema ahora usa autenticación directa contra MySQL de administraNET Gestión.

## Archivos Modificados

### 1. `django_project/firebase_config.py`
- Función `get_firebase_app()` ahora retorna `None` sin inicializar Firebase
- Todos los imports de Firebase comentados
- Logging informa que Firebase está deshabilitado

### 2. `core/views/views.py`
- Imports de Firebase comentados
- Código de creación de usuarios actualizado para no usar Firebase
- Genera UID usando hash MD5 del email
- Establece contraseña directamente en Django

### 3. `core/views/views_usuarios.py`
- Imports de Firebase comentados
- Llamada a `get_firebase_app()` comentada

### 4. `core/utils/utils.py`
- Imports de Firebase comentados
- Función `sincronizar_usuario_desde_firestore()` deshabilitada (retorna `NotImplementedError`)

### 5. `core/signals.py`
- Signal `sincronizar_usuario_firebase` completamente comentado

### 6. `django_project/auth.py`
- Función `get_current_user()` deshabilitada (retorna `NotImplementedError`)

## Cambios en Autenticación

### Antes (Firebase)
- Usuarios autenticados con Firebase Auth
- Tokens JWT de Firebase
- Sincronización con Firestore
- UID generado por Firebase

### Ahora (administraNET Gestión)
- Autenticación directa contra MySQL de administraNET Gestión
- Validación con `AES_DECRYPT(password_usuario, 'a7v8xx2')`
- Sesiones en tabla `sesion` de administraNET
- UID generado localmente (hash MD5 del email) para usuarios nuevos

## Notas Importantes

1. **No se eliminará Firebase del código**: Los archivos están comentados para facilitar restauración si es necesario
2. **Usuarios existentes**: Los usuarios con UID de Firebase seguirán funcionando
3. **Nuevos usuarios**: Se generan con UID basado en hash MD5 del email
4. **Autenticación**: Completamente reemplazada por `login/administranet_auth.py`

## Verificación

Para verificar que Firebase está deshabilitado:

```bash
# El servidor no debería mostrar mensajes de inicialización de Firebase
docker exec Synap_app python manage.py check
```

Si ves mensajes como:
```
[Firebase] Inicializando Firebase...
```

Significa que algún código aún está intentando inicializar Firebase. Revisar logs para encontrar la fuente.

## Restauración (si es necesario)

Si necesitas restaurar Firebase:

1. Descomentar imports en `firebase_config.py`
2. Restaurar función `get_firebase_app()` original
3. Descomentar código en `core/views/views.py` y otros archivos
4. Restaurar signals en `core/signals.py`

