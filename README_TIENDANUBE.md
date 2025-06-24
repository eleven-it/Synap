# 🚀 Integración TiendaNube - Synap ERP

## 📋 Descripción

Esta integración permite sincronizar productos y stock entre Synap ERP y TiendaNube de forma automática y manual.

## 🛠️ Características

- ✅ **Sincronización bidireccional** de productos y stock
- ✅ **API REST completa** para integraciones externas
- ✅ **Dashboard web** con estadísticas en tiempo real
- ✅ **Sincronización automática** configurable
- ✅ **Webhooks** para actualizaciones en tiempo real
- ✅ **Logs detallados** de todas las operaciones
- ✅ **Manejo de errores** robusto
- ✅ **Configuración flexible** por tienda
- ✅ **Variables de entorno** para configuración automática

## 🔧 Instalación y Configuración

### 1. Variables de Entorno

Crea un archivo `.env` en la raíz del proyecto con las siguientes variables:

```bash
# TiendaNube Configuration
TIENDANUBE_ACCESS_TOKEN=tu_access_token_aqui
TIENDANUBE_STORE_ID=tu_store_id_aqui
TIENDANUBE_WEBHOOK_SECRET=tu_webhook_secret_aqui
TIENDANUBE_API_URL=https://api.tiendanube.com/v1
TIENDANUBE_AUTO_SYNC=True
TIENDANUBE_SYNC_INTERVAL=30
```

### 2. Migraciones

Ejecuta las migraciones para crear las tablas necesarias:

```bash
python manage.py makemigrations inventario
python manage.py migrate
```

### 3. Configuración Inicial

#### Opción A: Configuración Automática (Recomendada)
1. Accede al dashboard de TiendaNube: `/inventario/tiendanube/`
2. Si las variables de entorno están configuradas, verás un mensaje de confirmación
3. Haz clic en "Crear desde Variables de Entorno" para crear la configuración automáticamente
4. Prueba la conexión
5. Activa la sincronización automática si lo deseas

#### Opción B: Configuración Manual
1. Accede al dashboard de TiendaNube: `/inventario/tiendanube/`
2. Configura manualmente tu Store ID y Access Token
3. Prueba la conexión
4. Activa la sincronización automática si lo deseas

#### Opción C: Comando de Línea
```bash
# Crear configuración desde variables de entorno
python manage.py sync_tiendanube --create-config

# O crear y ejecutar sincronización
python manage.py sync_tiendanube --create-config --force
```

## 📊 Dashboard

### Acceso
- URL: `/inventario/tiendanube/`
- Permisos requeridos: `inventario.ver_stock`

### Funcionalidades
- **Estado de sincronización** en tiempo real
- **Estadísticas** de productos sincronizados
- **Configuración** de la integración
- **Logs** de sincronización
- **Acciones manuales** de sincronización
- **Creación automática** de configuración desde variables de entorno

### Indicadores de Estado
- 🟢 **Variables de Entorno Configuradas**: Muestra información de la configuración
- 🟡 **Variables de Entorno No Configuradas**: Permite crear configuración automáticamente
- 🔴 **Error de Configuración**: Requiere configuración manual

## 🔌 API REST

### Endpoints Disponibles

#### Estado de Sincronización
```http
GET /api/inventario/tiendanube/status/
```

#### Sincronizar Productos
```http
POST /api/inventario/tiendanube/sync/products/
Content-Type: application/json

{
    "limit": 100,
    "offset": 0
}
```

#### Sincronizar Stock
```http
POST /api/inventario/tiendanube/sync/stock/
Content-Type: application/json

{
    "product_id": 123  // Opcional
}
```

#### Listar Productos
```http
GET /api/inventario/tiendanube/products/?synced_only=true&limit=50&offset=0
```

#### Logs de Sincronización
```http
GET /api/inventario/tiendanube/logs/?limit=20
```

#### Probar Conexión
```http
POST /api/inventario/tiendanube/test-connection/
```

#### Configuración
```http
GET /api/inventario/tiendanube/config/
PUT /api/inventario/tiendanube/config/
```

#### Crear Configuración desde Variables de Entorno
```http
POST /api/inventario/tiendanube/config/create-from-env/
```

#### Webhook Handler
```http
POST /api/inventario/tiendanube/webhook/
```

#### Datos del Dashboard
```http
GET /api/inventario/tiendanube/dashboard/
```

### Autenticación
Todos los endpoints requieren autenticación y el permiso `inventario.ver_stock`.

## ⚙️ Comandos de Gestión

### Sincronización Manual
```bash
# Sincronización completa
python manage.py sync_tiendanube

# Solo productos
python manage.py sync_tiendanube --type products

# Solo stock
python manage.py sync_tiendanube --type stock

# Con límite personalizado
python manage.py sync_tiendanube --limit 50

# Forzar sincronización
python manage.py sync_tiendanube --force

# Configuración específica
python manage.py sync_tiendanube --config-id 1
```

### Crear Configuración Automáticamente
```bash
# Crear configuración desde variables de entorno
python manage.py sync_tiendanube --create-config

# Crear y ejecutar sincronización
python manage.py sync_tiendanube --create-config --force
```

### Sincronización Automática
Para activar la sincronización automática, configura un cron job:

```bash
# Cada 30 minutos
*/30 * * * * cd /path/to/synap && python manage.py sync_tiendanube

# Cada hora
0 * * * * cd /path/to/synap && python manage.py sync_tiendanube
```

## 🔄 Flujo de Sincronización

### Productos desde TiendaNube → Synap
1. Obtiene productos de la API de TiendaNube
2. Crea o actualiza productos en Synap
3. Mapea variantes y atributos
4. Actualiza estado de sincronización

### Stock desde Synap → TiendaNube
1. Calcula stock disponible por producto
2. Actualiza stock en TiendaNube
3. Registra movimiento en logs

### Webhooks
- Recibe notificaciones de cambios en TiendaNube
- Procesa actualizaciones automáticamente
- Mantiene sincronización en tiempo real

## 📈 Monitoreo

### Logs
Los logs se almacenan en la tabla `TiendaNubeSyncLog` con:
- Tipo de sincronización
- Estado (éxito/error/parcial)
- Detalles de la operación
- Estadísticas de procesamiento
- Timestamps

### Métricas
- Productos totales vs sincronizados
- Porcentaje de sincronización
- Tiempo de última sincronización
- Productos con errores

## 🛡️ Seguridad

- **Tokens encriptados** en la base de datos
- **Validación de webhooks** con secret
- **Permisos granulares** por usuario
- **Logs de auditoría** completos
- **Rate limiting** en API
- **Variables de entorno** para configuración sensible

## 🔧 Configuración Avanzada

### Variables de Entorno Disponibles
```bash
# Requeridas
TIENDANUBE_ACCESS_TOKEN=tu_token_aqui
TIENDANUBE_STORE_ID=tu_store_id

# Opcionales
TIENDANUBE_WEBHOOK_SECRET=tu_webhook_secret
TIENDANUBE_API_URL=https://api.tiendanube.com/v1
TIENDANUBE_AUTO_SYNC=True
TIENDANUBE_SYNC_INTERVAL=30
```

### Múltiples Tiendas
Puedes configurar múltiples tiendas de TiendaNube:

```python
# Crear configuración adicional
config = TiendaNubeConfig.objects.create(
    store_id='tienda_2',
    access_token='token_2',
    auto_sync=True,
    sync_interval=60
)

# Usar configuración específica
service = TiendaNubeService(config)
```

### Personalización de Mapeo
Los productos se mapean automáticamente, pero puedes personalizar:

```python
# Configurar mapeo específico
mapping = TiendaNubeProductMapping.objects.get(product=product)
mapping.sync_price = False  # No sincronizar precio
mapping.sync_stock = True   # Sincronizar stock
mapping.save()
```

## 🚨 Solución de Problemas

### Error de Conexión
1. Verifica el Access Token
2. Confirma el Store ID
3. Revisa la conectividad de red
4. Consulta los logs de error

### Productos No Sincronizados
1. Verifica el estado del mapeo
2. Revisa los logs de sincronización
3. Ejecuta sincronización manual
4. Verifica permisos de API

### Stock Desactualizado
1. Verifica el cálculo de stock disponible
2. Revisa las ubicaciones internas
3. Ejecuta sincronización de stock
4. Verifica webhooks

### Variables de Entorno No Detectadas
1. Verifica que el archivo `.env` esté en la raíz del proyecto
2. Confirma que las variables estén escritas correctamente
3. Reinicia el servidor Django
4. Usa configuración manual como alternativa

## 📞 Soporte

Para soporte técnico:
- Revisa los logs en el dashboard
- Consulta la documentación de la API de TiendaNube
- Verifica la configuración de red
- Contacta al equipo de desarrollo

## 🔄 Actualizaciones

### v1.1.0 - Variables de Entorno
- ✅ Configuración automática desde variables de entorno
- ✅ Dashboard mejorado con indicadores de estado
- ✅ Comando `--create-config` para configuración automática
- ✅ Endpoint para crear configuración desde variables de entorno
- ✅ Mejor manejo de errores y validaciones

### v1.0.0 - Lanzamiento Inicial
- ✅ Sincronización básica de productos
- ✅ Sincronización de stock
- ✅ Dashboard web
- ✅ API REST
- ✅ Comandos de gestión
- ✅ Webhooks
- ✅ Logs y monitoreo

### Próximas Funcionalidades
- 🔄 Sincronización de pedidos
- 🔄 Sincronización de clientes
- 🔄 Reportes avanzados
- 🔄 Notificaciones por email
- 🔄 Integración con más plataformas 