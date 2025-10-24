# 🚀 Scripts de Instalación para WSL2

## 📁 Archivos Incluidos

1. **`deploy_wsl2_docker_desktop.md`** - Guía completa paso a paso
2. **`setup_windows_for_wsl2.ps1`** - Script PowerShell para preparar Windows
3. **`setup_wsl2.sh`** - Script Bash para instalar Synap en WSL2

---

## 🎯 Instalación Rápida

### Método 1: Instalación Automatizada (Recomendado)

#### Paso 1: Preparar Windows (PowerShell como Administrador)

```powershell
# Descargar el script
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/eleven-it/Synap/1.0/misc/scripts/setup_windows_for_wsl2.ps1" -OutFile "$env:TEMP\setup_windows_for_wsl2.ps1"

# Permitir ejecución
Set-ExecutionPolicy Bypass -Scope Process

# Ejecutar
& "$env:TEMP\setup_windows_for_wsl2.ps1"
```

#### Paso 2: Instalar Synap (En Ubuntu/WSL2)

```bash
# Descargar el script
curl -fsSL https://raw.githubusercontent.com/eleven-it/Synap/1.0/misc/scripts/setup_wsl2.sh -o /tmp/setup_wsl2.sh

# Dar permisos de ejecución
chmod +x /tmp/setup_wsl2.sh

# Ejecutar
/tmp/setup_wsl2.sh
```

---

### Método 2: Instalación Manual

Consulta la guía completa en: `misc/documentacion/deploy_wsl2_docker_desktop.md`

---

## 📋 Requisitos Previos

### Windows
- ✅ Windows 10 versión 2004+ o Windows 11
- ✅ Virtualización habilitada en BIOS/UEFI
- ✅ 8 GB RAM mínimo (16 GB recomendado)
- ✅ 50 GB espacio libre en disco

### Instalaciones Necesarias
- ✅ WSL2
- ✅ Docker Desktop para Windows
- ✅ Ubuntu 22.04 en WSL2

---

## 🔧 Uso de Scripts

### `setup_windows_for_wsl2.ps1`

**Propósito:** Preparar Windows para WSL2 y Docker Desktop

**Qué hace:**
- ✅ Verifica versión de Windows
- ✅ Verifica virtualización
- ✅ Habilita WSL
- ✅ Habilita Plataforma de Máquina Virtual
- ✅ Descarga e instala actualización del kernel
- ✅ Establece WSL2 como predeterminado
- ✅ Instala Ubuntu 22.04
- ✅ Descarga Docker Desktop (opcional)
- ✅ Crea archivo .wslconfig optimizado

**Uso:**

```powershell
# 1. Abrir PowerShell como Administrador
# 2. Permitir ejecución de scripts
Set-ExecutionPolicy Bypass -Scope Process

# 3. Ejecutar script
.\setup_windows_for_wsl2.ps1
```

---

### `setup_wsl2.sh`

**Propósito:** Instalar y configurar Synap automáticamente en WSL2

**Qué hace:**
- ✅ Verifica entorno WSL2
- ✅ Verifica Docker y Docker Compose
- ✅ Instala dependencias del sistema
- ✅ Configura Git
- ✅ Clona repositorio de Synap
- ✅ Configura archivo .env
- ✅ Construye imágenes Docker
- ✅ Inicia servicios
- ✅ Aplica migraciones
- ✅ Crea superusuario
- ✅ Recolecta archivos estáticos

**Uso:**

```bash
# 1. Asegurarse de estar en WSL2
# 2. Dar permisos de ejecución
chmod +x setup_wsl2.sh

# 3. Ejecutar
./setup_wsl2.sh
```

---

## 🎬 Flujo Completo de Instalación

### 1️⃣ Preparar Windows

```powershell
# En PowerShell como Administrador
.\setup_windows_for_wsl2.ps1
```

**Tiempo:** 10-15 minutos  
**Reinicio:** Puede requerir reinicio

---

### 2️⃣ Configurar Ubuntu

```bash
# Abrir Ubuntu 22.04 desde menú de inicio
# Crear usuario y contraseña cuando se solicite
```

---

### 3️⃣ Instalar Docker Desktop

1. Descargar: https://www.docker.com/products/docker-desktop/
2. Instalar con opción "Use WSL 2 instead of Hyper-V"
3. Settings > Resources > WSL Integration
4. Habilitar integración con Ubuntu-22.04

---

### 4️⃣ Instalar Synap

```bash
# En Ubuntu/WSL2
cd ~
curl -fsSL https://raw.githubusercontent.com/eleven-it/Synap/1.0/misc/scripts/setup_wsl2.sh -o setup_wsl2.sh
chmod +x setup_wsl2.sh
./setup_wsl2.sh
```

**Tiempo:** 10-15 minutos  
**Interactivo:** Solicitará configuraciones

---

### 5️⃣ Acceder a Synap

Abre tu navegador y ve a:

```
http://localhost:8002
```

---

## 🐛 Troubleshooting

### Problema: "Docker no está corriendo"

```bash
# Verificar que Docker Desktop esté iniciado
# En Windows, buscar Docker Desktop en la bandeja del sistema

# Verificar en WSL2
docker ps
```

### Problema: "wsl --install no funciona"

```powershell
# Instalar manualmente desde Microsoft Store
# Buscar "Ubuntu 22.04 LTS"
```

### Problema: "Puerto 8002 ocupado"

```bash
# Cambiar puerto en docker-compose.yml
# O detener proceso que usa el puerto
sudo lsof -i :8002
```

### Problema: Script setup_wsl2.sh falla

```bash
# Ejecutar paso a paso manualmente
# Consultar: misc/documentacion/deploy_wsl2_docker_desktop.md
```

---

## 📚 Documentación Adicional

- **Guía Completa:** `misc/documentacion/deploy_wsl2_docker_desktop.md`
- **Deploy Producción:** `misc/scripts/PRODUCTION_DEPLOY.txt`
- **README Principal:** `README.md`

---

## 🆘 Soporte

Si encuentras problemas:

1. Revisa los logs: `docker-compose logs -f`
2. Consulta la guía completa en `deploy_wsl2_docker_desktop.md`
3. Verifica prerequisitos (versión Windows, virtualización, etc.)
4. Crea un issue en GitHub: https://github.com/eleven-it/Synap/issues

---

## ✅ Checklist de Instalación

Antes de comenzar:
- [ ] Windows 10 2004+ o Windows 11
- [ ] Virtualización habilitada en BIOS
- [ ] 8+ GB RAM disponible
- [ ] 50+ GB espacio en disco

Después de `setup_windows_for_wsl2.ps1`:
- [ ] WSL habilitado
- [ ] WSL2 como predeterminado
- [ ] Ubuntu 22.04 instalado
- [ ] Docker Desktop instalado
- [ ] Integración WSL2-Docker habilitada

Después de `setup_wsl2.sh`:
- [ ] Git configurado
- [ ] Repositorio clonado
- [ ] Archivo .env creado
- [ ] Imágenes Docker construidas
- [ ] Servicios corriendo
- [ ] Migraciones aplicadas
- [ ] Superusuario creado
- [ ] Acceso a http://localhost:8002

---

## 🎉 ¡Instalación Exitosa!

Si completaste todos los pasos del checklist, tu instalación de Synap está lista.

**Próximos pasos:**
1. Configurar Tiendanube (OAuth)
2. Configurar AdministraNET (MySQL)
3. Ejecutar sincronización inicial
4. Configurar webhooks

---

*Última actualización: 2025-10-24*  
*Versión: 1.0*

