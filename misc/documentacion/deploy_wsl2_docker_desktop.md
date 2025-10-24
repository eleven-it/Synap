# 🚀 Guía de Deploy de Synap en WSL2 con Docker Desktop

## 📋 Tabla de Contenidos

1. [Requisitos Previos](#requisitos-previos)
2. [Instalación de Prerequisitos](#instalación-de-prerequisitos)
3. [Configuración de WSL2](#configuración-de-wsl2)
4. [Instalación de Docker Desktop](#instalación-de-docker-desktop)
5. [Clonar el Repositorio](#clonar-el-repositorio)
6. [Configuración del Proyecto](#configuración-del-proyecto)
7. [Despliegue con Docker Compose](#despliegue-con-docker-compose)
8. [Verificación del Deploy](#verificación-del-deploy)
9. [Comandos Útiles](#comandos-útiles)
10. [Troubleshooting](#troubleshooting)

---

## 🔧 Requisitos Previos

### Hardware Mínimo
- **RAM:** 8 GB (16 GB recomendado)
- **Disco:** 50 GB libres
- **CPU:** 4 cores (recomendado)

### Software
- **Windows 10/11** (versión 2004 o superior)
- **WSL2** habilitado
- **Docker Desktop** para Windows
- **Git** para Windows o en WSL2

---

## 📦 Instalación de Prerequisitos

### 1️⃣ Habilitar WSL2

#### Paso 1: Habilitar características de Windows

Abre **PowerShell como Administrador** y ejecuta:

```powershell
# Habilitar WSL
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart

# Habilitar plataforma de máquina virtual
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
```

#### Paso 2: Reiniciar Windows

```powershell
Restart-Computer
```

#### Paso 3: Descargar e instalar el paquete de actualización del kernel de Linux

Descarga desde: https://aka.ms/wsl2kernel

Ejecuta el instalador descargado.

#### Paso 4: Establecer WSL2 como versión predeterminada

```powershell
wsl --set-default-version 2
```

#### Paso 5: Instalar una distribución de Linux

Opción 1 - Desde Microsoft Store:
1. Abre **Microsoft Store**
2. Busca **Ubuntu 22.04 LTS**
3. Haz clic en **Instalar**
4. Una vez instalado, ábrelo y configura usuario/contraseña

Opción 2 - Desde PowerShell:
```powershell
wsl --install -d Ubuntu-22.04
```

#### Verificar instalación:

```powershell
wsl --list --verbose
```

Deberías ver algo como:
```
  NAME            STATE           VERSION
* Ubuntu-22.04    Running         2
```

---

## 🐳 Instalación de Docker Desktop

### 1️⃣ Descargar Docker Desktop

Descarga desde: https://www.docker.com/products/docker-desktop/

### 2️⃣ Instalar Docker Desktop

1. Ejecuta el instalador
2. Asegúrate de marcar: **"Use WSL 2 instead of Hyper-V"**
3. Completa la instalación
4. Reinicia Windows si es necesario

### 3️⃣ Configurar Docker Desktop para WSL2

1. Abre **Docker Desktop**
2. Ve a **Settings** (⚙️)
3. En **General**:
   - ✅ Marca **"Use the WSL 2 based engine"**
4. En **Resources > WSL Integration**:
   - ✅ Marca **"Enable integration with my default WSL distro"**
   - ✅ Marca tu distribución (Ubuntu-22.04)
5. Haz clic en **Apply & Restart**

### 4️⃣ Verificar instalación de Docker en WSL2

Abre **Ubuntu 22.04** desde el menú de inicio y ejecuta:

```bash
docker --version
docker-compose --version
```

Deberías ver:
```
Docker version 24.x.x
Docker Compose version v2.x.x
```

---

## 📥 Clonar el Repositorio

### 1️⃣ Abrir terminal de WSL2

Abre **Ubuntu 22.04** desde el menú de inicio.

### 2️⃣ Instalar Git (si no está instalado)

```bash
sudo apt update
sudo apt install git -y
```

### 3️⃣ Configurar Git

```bash
git config --global user.name "Tu Nombre"
git config --global user.email "tu.email@ejemplo.com"
```

### 4️⃣ Crear directorio de proyectos

```bash
mkdir -p ~/proyectos
cd ~/proyectos
```

### 5️⃣ Clonar el repositorio

```bash
git clone https://github.com/eleven-it/Synap.git
cd Synap
```

### 6️⃣ Cambiar a la rama correcta

```bash
git checkout 1.0
```

---

## ⚙️ Configuración del Proyecto

### 1️⃣ Crear archivo .env

```bash
cp .env.example .env
nano .env
```

### 2️⃣ Configurar variables de entorno

Edita el archivo `.env` con las siguientes variables:

```bash
# Django
DEBUG=True
SECRET_KEY=tu_clave_secreta_aqui_genera_una_nueva
ALLOWED_HOSTS=localhost,127.0.0.1
SITE_URL=http://localhost:8002

# Base de datos PostgreSQL
POSTGRES_DB=synap_db
POSTGRES_USER=synap_user
POSTGRES_PASSWORD=tu_password_seguro_aqui
POSTGRES_HOST=db
POSTGRES_PORT=5432

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# Tiendanube
TIENDANUBE_CLIENT_ID=tu_client_id
TIENDANUBE_CLIENT_SECRET=tu_client_secret

# AdministraNET (MySQL externo)
ADMINET_HOST=tu_host_mysql
ADMINET_PORT=3306
ADMINET_DATABASE=administranet
ADMINET_USER=tu_usuario
ADMINET_PASSWORD=tu_password
```

**⚠️ IMPORTANTE:** 
- Genera una nueva `SECRET_KEY` usando: 
  ```bash
  python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
  ```
- Usa contraseñas seguras para `POSTGRES_PASSWORD`

### 3️⃣ Crear archivo docker-compose.override.yml (Opcional)

Para desarrollo local con configuraciones específicas:

```bash
nano docker-compose.override.yml
```

Contenido:

```yaml
version: '3.8'

services:
  app:
    volumes:
      - .:/app
    environment:
      - DEBUG=True
```

---

## 🚀 Despliegue con Docker Compose

### 1️⃣ Construir las imágenes

```bash
docker-compose build
```

Esto puede tomar varios minutos la primera vez.

### 2️⃣ Iniciar los servicios

```bash
docker-compose up -d
```

Los servicios que se iniciarán:
- ✅ **app** - Aplicación Django (puerto 8002)
- ✅ **db** - PostgreSQL (puerto 5432)
- ✅ **redis** - Redis (puerto 6379)

### 3️⃣ Verificar que los contenedores estén corriendo

```bash
docker-compose ps
```

Deberías ver:
```
NAME                COMMAND                  SERVICE             STATUS              PORTS
Synap_app           "python manage.py ru…"   app                 running             0.0.0.0:8002->8002/tcp
Synap_db            "docker-entrypoint.s…"   db                  running             5432/tcp
Synap_redis         "docker-entrypoint.s…"   redis               running             6379/tcp
```

### 4️⃣ Inicialización Completa (Recomendado)

**Opción A: Script Automatizado (Recomendado)**

```bash
# Dar permisos de ejecución
chmod +x misc/scripts/init_synap_instance.sh

# Ejecutar inicialización completa
./misc/scripts/init_synap_instance.sh
```

Este script ejecuta automáticamente:
- ✅ Migraciones de base de datos
- ✅ Setup inicial del sistema
- ✅ Carga de datos iniciales
- ✅ Recolección de archivos estáticos
- ✅ Compilación de traducciones
- ✅ Verificación de servicios
- ✅ Muestra credenciales de administrador

**Opción B: Paso a Paso (Manual)**

```bash
# Aplicar migraciones
docker exec Synap_app python manage.py migrate

# Crear superusuario
docker exec -it Synap_app python manage.py createsuperuser

# Recolectar archivos estáticos
docker exec Synap_app python manage.py collectstatic --noinput
```

---

## ✅ Verificación del Deploy

### 1️⃣ Verificar que la aplicación esté corriendo

Abre tu navegador y ve a:

```
http://localhost:8002
```

Deberías ver la página de inicio de Synap.

### 2️⃣ Acceder al admin de Django

```
http://localhost:8002/admin
```

Usa las credenciales del superusuario que creaste.

### 3️⃣ Verificar logs

```bash
# Ver logs de todos los servicios
docker-compose logs -f

# Ver logs solo de la app
docker-compose logs -f app

# Ver últimas 100 líneas
docker-compose logs --tail=100 app
```

### 4️⃣ Verificar conexión a la base de datos

```bash
docker exec Synap_app python manage.py dbshell
```

Deberías poder acceder a la consola de PostgreSQL.

### 5️⃣ Verificar Redis

```bash
docker exec -it Synap_redis redis-cli ping
```

Deberías recibir: `PONG`

---

## 🛠️ Comandos Útiles

### Docker Compose

```bash
# Iniciar servicios
docker-compose up -d

# Detener servicios
docker-compose down

# Ver logs en tiempo real
docker-compose logs -f

# Reiniciar un servicio específico
docker-compose restart app

# Reconstruir imagen y reiniciar
docker-compose up -d --build app

# Ver estado de los servicios
docker-compose ps

# Detener y eliminar volúmenes (⚠️ CUIDADO: elimina datos)
docker-compose down -v
```

### Django Management

```bash
# Ejecutar comandos de Django
docker exec Synap_app python manage.py [comando]

# Aplicar migraciones
docker exec Synap_app python manage.py migrate

# Crear migraciones
docker exec Synap_app python manage.py makemigrations

# Shell de Django
docker exec -it Synap_app python manage.py shell

# Shell de base de datos
docker exec Synap_app python manage.py dbshell

# Crear superusuario
docker exec -it Synap_app python manage.py createsuperuser

# Recolectar estáticos
docker exec Synap_app python manage.py collectstatic --noinput
```

### Acceso a contenedores

```bash
# Entrar al contenedor de la app
docker exec -it Synap_app bash

# Entrar al contenedor de PostgreSQL
docker exec -it Synap_db psql -U synap_user -d synap_db

# Entrar al contenedor de Redis
docker exec -it Synap_redis redis-cli
```

### Git

```bash
# Ver estado
git status

# Actualizar código desde GitHub
git pull origin 1.0

# Ver ramas
git branch -a

# Cambiar de rama
git checkout nombre-rama

# Ver commits recientes
git log --oneline -10
```

### Sistema

```bash
# Ver uso de disco en WSL2
df -h

# Ver procesos de Docker
docker ps -a

# Ver imágenes
docker images

# Limpiar recursos no usados
docker system prune -a

# Ver uso de recursos
docker stats
```

---

## 🔍 Troubleshooting

### Problema: Docker Desktop no inicia

**Solución 1:** Verificar que WSL2 esté activo
```powershell
wsl --list --verbose
```

**Solución 2:** Reiniciar WSL2
```powershell
wsl --shutdown
```
Luego abre Docker Desktop nuevamente.

**Solución 3:** Reiniciar servicio de Docker
1. Cierra Docker Desktop
2. Abre **Services** (services.msc)
3. Busca **Docker Desktop Service**
4. Reinicia el servicio

---

### Problema: "Cannot connect to the Docker daemon"

**Solución 1:** Verificar que Docker Desktop esté corriendo
- Abre Docker Desktop desde el menú de inicio
- Espera a que muestre "Docker Desktop is running"

**Solución 2:** Verificar integración con WSL2
1. Abre Docker Desktop
2. Settings > Resources > WSL Integration
3. Marca tu distribución de Ubuntu
4. Apply & Restart

**Solución 3:** Reiniciar WSL2
```bash
# En PowerShell (como administrador)
wsl --shutdown

# Luego abre Ubuntu nuevamente
```

---

### Problema: Puerto 8002 ya en uso

**Solución 1:** Ver qué proceso usa el puerto
```bash
# En WSL2
sudo lsof -i :8002

# En Windows (PowerShell)
netstat -ano | findstr :8002
```

**Solución 2:** Cambiar el puerto en docker-compose.yml
```yaml
services:
  app:
    ports:
      - "8003:8002"  # Usar puerto 8003 en lugar de 8002
```

**Solución 3:** Detener el proceso que usa el puerto
```bash
# Detener contenedor de Docker
docker stop $(docker ps -q --filter ancestor=synap_app)
```

---

### Problema: Error al construir la imagen

**Solución 1:** Limpiar caché de Docker
```bash
docker builder prune -a
docker-compose build --no-cache
```

**Solución 2:** Verificar archivo Dockerfile
```bash
cat Dockerfile
```

**Solución 3:** Ver logs de construcción
```bash
docker-compose build --progress=plain
```

---

### Problema: Migraciones fallan

**Solución 1:** Verificar conexión a base de datos
```bash
docker exec Synap_app python manage.py dbshell
```

**Solución 2:** Verificar que la base de datos esté corriendo
```bash
docker-compose ps db
docker-compose logs db
```

**Solución 3:** Recrear base de datos (⚠️ CUIDADO: elimina datos)
```bash
docker-compose down -v
docker-compose up -d
docker exec Synap_app python manage.py migrate
```

---

### Problema: Error "No space left on device"

**Solución 1:** Limpiar imágenes y contenedores no usados
```bash
docker system prune -a --volumes
```

**Solución 2:** Aumentar espacio de WSL2

Edita o crea el archivo `.wslconfig` en tu home de Windows:

```powershell
# En PowerShell
notepad "$env:USERPROFILE\.wslconfig"
```

Contenido:
```ini
[wsl2]
memory=8GB
processors=4
swap=2GB
```

Luego reinicia WSL2:
```powershell
wsl --shutdown
```

**Solución 3:** Limpiar espacio en WSL2
```bash
# En Ubuntu
sudo apt clean
sudo apt autoclean
sudo apt autoremove -y

# Limpiar logs
sudo journalctl --vacuum-time=1d

# Limpiar Docker
docker system prune -af --volumes
```

---

### Problema: Lentitud en WSL2

**Solución 1:** Limitar recursos en .wslconfig

```ini
[wsl2]
memory=6GB
processors=2
localhostForwarding=true
```

**Solución 2:** Mover proyecto a sistema de archivos de Linux

❌ **EVITAR:**
```
/mnt/c/Users/tu_usuario/proyectos/Synap
```

✅ **USAR:**
```
/home/tu_usuario/proyectos/Synap
```

El sistema de archivos nativo de Linux (ext4) es **mucho más rápido** que acceder a NTFS a través de `/mnt/`.

**Solución 3:** Deshabilitar antivirus en carpeta de proyecto

Agrega la carpeta del proyecto como excepción en Windows Defender o tu antivirus.

---

### Problema: No se puede acceder a localhost:8002 desde Windows

**Solución 1:** Verificar que el servicio esté escuchando en 0.0.0.0

En `docker-compose.yml`:
```yaml
services:
  app:
    command: python manage.py runserver 0.0.0.0:8002
```

**Solución 2:** Verificar firewall de Windows

1. Abre **Windows Defender Firewall**
2. **Advanced settings**
3. **Inbound Rules**
4. Busca reglas para puerto 8002 o Docker
5. Asegúrate de que estén habilitadas

**Solución 3:** Usar IP de WSL2

```bash
# Obtener IP de WSL2
hostname -I
```

Accede desde: `http://[IP_WSL2]:8002`

---

### Problema: Cambios en código no se reflejan

**Solución 1:** Verificar volúmenes en docker-compose.yml

```yaml
services:
  app:
    volumes:
      - .:/app  # Debe estar presente
```

**Solución 2:** Reiniciar contenedor
```bash
docker-compose restart app
```

**Solución 3:** Usar modo desarrollo con hot-reload

En `docker-compose.override.yml`:
```yaml
services:
  app:
    environment:
      - DEBUG=True
      - DJANGO_SETTINGS_MODULE=config.settings
    command: python manage.py runserver 0.0.0.0:8002
```

---

## 📚 Recursos Adicionales

### Documentación Oficial

- **WSL2:** https://docs.microsoft.com/en-us/windows/wsl/
- **Docker Desktop:** https://docs.docker.com/desktop/windows/wsl/
- **Django:** https://docs.djangoproject.com/
- **Docker Compose:** https://docs.docker.com/compose/

### Comandos de Referencia Rápida

```bash
# Ver versión de WSL
wsl --version

# Listar distribuciones
wsl --list --verbose

# Establecer distribución por defecto
wsl --set-default Ubuntu-22.04

# Apagar WSL2
wsl --shutdown

# Actualizar WSL
wsl --update

# Entrar a WSL2 desde PowerShell
wsl

# Ejecutar comando en WSL2 desde PowerShell
wsl ls -la

# Ver IP de WSL2
wsl hostname -I
```

---

## 🎯 Checklist de Deploy

- [ ] WSL2 instalado y configurado
- [ ] Docker Desktop instalado
- [ ] Integración WSL2-Docker habilitada
- [ ] Git instalado en WSL2
- [ ] Repositorio clonado
- [ ] Rama correcta (1.0) checkout
- [ ] Archivo .env creado y configurado
- [ ] SECRET_KEY generada
- [ ] Contraseñas seguras configuradas
- [ ] docker-compose build ejecutado
- [ ] docker-compose up -d ejecutado
- [ ] Migraciones aplicadas
- [ ] Superusuario creado
- [ ] Archivos estáticos recolectados
- [ ] Aplicación accesible en localhost:8002
- [ ] Admin accesible en localhost:8002/admin
- [ ] Logs verificados (sin errores críticos)
- [ ] Base de datos conectada
- [ ] Redis funcionando

---

## ✅ Deploy Exitoso

Si completaste todos los pasos del checklist, tu instalación de Synap en WSL2 con Docker Desktop está **lista y funcionando**.

### Accesos:

- **Aplicación:** http://localhost:8002
- **Admin:** http://localhost:8002/admin
- **Base de datos:** PostgreSQL en puerto 5432
- **Redis:** Redis en puerto 6379

### Próximos Pasos:

1. Configurar Tiendanube (OAuth)
2. Configurar conexión a AdministraNET
3. Ejecutar migraciones de schema automáticas
4. Configurar webhooks
5. Realizar sincronización inicial

---

## 📞 Soporte

Si encuentras algún problema no cubierto en esta guía, puedes:

1. Revisar los logs: `docker-compose logs -f`
2. Verificar el estado de los servicios: `docker-compose ps`
3. Consultar la documentación del proyecto
4. Crear un issue en GitHub

---

**🎉 ¡Felicitaciones! Tu entorno de desarrollo con WSL2 y Docker Desktop está listo.**

---

*Última actualización: 2025-10-24*  
*Versión de la guía: 1.0*  
*Proyecto: Synap - Sistema de integración Tiendanube ↔ AdministraNET*

