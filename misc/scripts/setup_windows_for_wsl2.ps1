# ============================================================================
# Script de Preparación de Windows para WSL2
# ============================================================================
# Este script prepara Windows para ejecutar WSL2 y Docker Desktop
# 
# IMPORTANTE: Ejecutar como Administrador
#
# Uso:
#   1. Abrir PowerShell como Administrador
#   2. Set-ExecutionPolicy Bypass -Scope Process
#   3. .\setup_windows_for_wsl2.ps1
#
# ============================================================================

# Verificar que se ejecuta como administrador
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
$isAdmin = $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "❌ ERROR: Este script debe ejecutarse como Administrador" -ForegroundColor Red
    Write-Host ""
    Write-Host "Pasos para ejecutar como Administrador:" -ForegroundColor Yellow
    Write-Host "1. Busca 'PowerShell' en el menú de inicio" -ForegroundColor Cyan
    Write-Host "2. Click derecho > Ejecutar como administrador" -ForegroundColor Cyan
    Write-Host "3. Ejecuta: Set-ExecutionPolicy Bypass -Scope Process" -ForegroundColor Cyan
    Write-Host "4. Ejecuta: .\setup_windows_for_wsl2.ps1" -ForegroundColor Cyan
    Write-Host ""
    pause
    exit 1
}

Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "       PREPARACIÓN DE WINDOWS PARA WSL2 Y DOCKER DESKTOP" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""

# Función para imprimir mensajes
function Print-Success {
    param($message)
    Write-Host "✅ $message" -ForegroundColor Green
}

function Print-Error {
    param($message)
    Write-Host "❌ $message" -ForegroundColor Red
}

function Print-Warning {
    param($message)
    Write-Host "⚠️  $message" -ForegroundColor Yellow
}

function Print-Info {
    param($message)
    Write-Host "ℹ️  $message" -ForegroundColor Blue
}

function Print-Header {
    param($message)
    Write-Host ""
    Write-Host "============================================================================" -ForegroundColor Cyan
    Write-Host "$message" -ForegroundColor Cyan
    Write-Host "============================================================================" -ForegroundColor Cyan
    Write-Host ""
}

# Verificar versión de Windows
Print-Header "Verificando Versión de Windows"

$osInfo = Get-CimInstance -ClassName Win32_OperatingSystem
$buildNumber = [int]$osInfo.BuildNumber

Print-Info "Windows $($osInfo.Caption)"
Print-Info "Build: $buildNumber"

if ($buildNumber -lt 19041) {
    Print-Error "WSL2 requiere Windows 10 versión 2004 (build 19041) o superior"
    Print-Error "Tu versión: $buildNumber"
    Print-Warning "Por favor actualiza Windows antes de continuar"
    pause
    exit 1
}

Print-Success "Versión de Windows compatible"

# Verificar virtualización
Print-Header "Verificando Soporte de Virtualización"

$virtualization = Get-CimInstance -ClassName Win32_Processor | Select-Object -ExpandProperty VirtualizationFirmwareEnabled

if ($virtualization) {
    Print-Success "Virtualización habilitada en BIOS"
} else {
    Print-Error "Virtualización NO habilitada en BIOS"
    Print-Warning "Debes habilitar Virtualización en la BIOS/UEFI"
    Print-Info "Busca opciones como: VT-x, AMD-V, SVM, Virtualization Technology"
    pause
    exit 1
}

# Habilitar WSL
Print-Header "Habilitando WSL (Windows Subsystem for Linux)"

$wslFeature = Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux

if ($wslFeature.State -eq "Enabled") {
    Print-Success "WSL ya está habilitado"
} else {
    Print-Info "Habilitando WSL..."
    Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux -NoRestart
    Print-Success "WSL habilitado"
    $needReboot = $true
}

# Habilitar Plataforma de Máquina Virtual
Print-Header "Habilitando Plataforma de Máquina Virtual"

$vmFeature = Get-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform

if ($vmFeature.State -eq "Enabled") {
    Print-Success "Plataforma de Máquina Virtual ya está habilitada"
} else {
    Print-Info "Habilitando Plataforma de Máquina Virtual..."
    Enable-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform -NoRestart
    Print-Success "Plataforma de Máquina Virtual habilitada"
    $needReboot = $true
}

# Descargar actualización del kernel de Linux
Print-Header "Descargando Actualización del Kernel de Linux para WSL2"

$kernelUpdateUrl = "https://wslstorestorage.blob.core.windows.net/wslblob/wsl_update_x64.msi"
$kernelUpdatePath = "$env:TEMP\wsl_update_x64.msi"

if (Test-Path $kernelUpdatePath) {
    Print-Info "Actualización del kernel ya descargada"
} else {
    Print-Info "Descargando actualización del kernel..."
    try {
        Invoke-WebRequest -Uri $kernelUpdateUrl -OutFile $kernelUpdatePath
        Print-Success "Actualización del kernel descargada"
    } catch {
        Print-Error "Error descargando actualización del kernel"
        Print-Warning "Descarga manual desde: https://aka.ms/wsl2kernel"
    }
}

# Instalar actualización del kernel
if (Test-Path $kernelUpdatePath) {
    Print-Info "Instalando actualización del kernel..."
    Start-Process msiexec.exe -Wait -ArgumentList "/i $kernelUpdatePath /quiet /norestart"
    Print-Success "Actualización del kernel instalada"
}

# Verificar si necesita reinicio
if ($needReboot) {
    Print-Header "REINICIO REQUERIDO"
    Print-Warning "Se han habilitado características que requieren reinicio"
    Print-Info "Después del reinicio, ejecuta este script nuevamente para continuar"
    Print-Info "O ejecuta manualmente los siguientes pasos:"
    Print-Info "  1. wsl --set-default-version 2"
    Print-Info "  2. wsl --install -d Ubuntu-22.04"
    Write-Host ""
    $reboot = Read-Host "¿Deseas reiniciar ahora? (S/N)"
    
    if ($reboot -eq "S" -or $reboot -eq "s") {
        Print-Info "Reiniciando en 10 segundos..."
        Start-Sleep -Seconds 10
        Restart-Computer
    } else {
        Print-Warning "Por favor reinicia manualmente para aplicar los cambios"
    }
    exit 0
}

# Establecer WSL2 como versión predeterminada
Print-Header "Configurando WSL2 como Versión Predeterminada"

try {
    wsl --set-default-version 2
    Print-Success "WSL2 establecido como versión predeterminada"
} catch {
    Print-Error "Error al establecer WSL2 como predeterminado"
    Print-Info "Intenta ejecutar manualmente: wsl --set-default-version 2"
}

# Verificar distribuciones instaladas
Print-Header "Verificando Distribuciones de Linux"

$wslList = wsl --list --verbose 2>$null

if ($LASTEXITCODE -eq 0 -and $wslList) {
    Print-Info "Distribuciones instaladas:"
    Write-Host $wslList
    Print-Success "WSL configurado correctamente"
} else {
    Print-Warning "No hay distribuciones de Linux instaladas"
    Print-Info "Instalando Ubuntu 22.04..."
    
    try {
        wsl --install -d Ubuntu-22.04
        Print-Success "Ubuntu 22.04 instalado"
        Print-Info "Abre Ubuntu desde el menú de inicio para completar la configuración"
    } catch {
        Print-Error "Error instalando Ubuntu"
        Print-Info "Instala manualmente desde Microsoft Store:"
        Print-Info "  https://www.microsoft.com/store/productId/9PN20MSR04DW"
    }
}

# Descargar Docker Desktop
Print-Header "Docker Desktop"

$dockerUrl = "https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe"
$dockerPath = "$env:USERPROFILE\Downloads\DockerDesktopInstaller.exe"

Print-Info "Docker Desktop debe ser instalado para usar contenedores"
Print-Info "URL de descarga: https://www.docker.com/products/docker-desktop/"

$downloadDocker = Read-Host "¿Deseas descargar Docker Desktop ahora? (S/N)"

if ($downloadDocker -eq "S" -or $downloadDocker -eq "s") {
    Print-Info "Descargando Docker Desktop..."
    Print-Warning "Esto puede tomar varios minutos (500+ MB)..."
    
    try {
        Invoke-WebRequest -Uri $dockerUrl -OutFile $dockerPath
        Print-Success "Docker Desktop descargado en: $dockerPath"
        
        $installDocker = Read-Host "¿Deseas instalar Docker Desktop ahora? (S/N)"
        
        if ($installDocker -eq "S" -or $installDocker -eq "s") {
            Print-Info "Instalando Docker Desktop..."
            Start-Process -FilePath $dockerPath -Wait
            Print-Success "Docker Desktop instalado"
            Print-Warning "Docker Desktop requiere reinicio"
        } else {
            Print-Info "Instala Docker Desktop manualmente ejecutando: $dockerPath"
        }
    } catch {
        Print-Error "Error descargando Docker Desktop"
        Print-Info "Descarga manual desde: https://www.docker.com/products/docker-desktop/"
    }
} else {
    Print-Info "Descarga Docker Desktop manualmente desde:"
    Print-Info "  https://www.docker.com/products/docker-desktop/"
}

# Configurar .wslconfig para optimizar rendimiento
Print-Header "Configurando .wslconfig"

$wslConfigPath = "$env:USERPROFILE\.wslconfig"
$wslConfigContent = @"
[wsl2]
memory=6GB
processors=4
swap=2GB
localhostForwarding=true

# Configuración de red
[network]
generateResolvConf=true
"@

if (Test-Path $wslConfigPath) {
    Print-Info "Archivo .wslconfig ya existe"
    $overwrite = Read-Host "¿Deseas sobrescribirlo con configuración optimizada? (S/N)"
    
    if ($overwrite -eq "S" -or $overwrite -eq "s") {
        $wslConfigContent | Out-File -FilePath $wslConfigPath -Encoding UTF8
        Print-Success "Archivo .wslconfig actualizado"
    }
} else {
    $wslConfigContent | Out-File -FilePath $wslConfigPath -Encoding UTF8
    Print-Success "Archivo .wslconfig creado"
}

Print-Info "Ubicación: $wslConfigPath"

# Crear script de acceso rápido
Print-Header "Creando Scripts de Acceso Rápido"

$quickAccessScript = @"
# Synap - Acceso Rápido a WSL2
# Guarda este script como synap.ps1 en tu escritorio

Write-Host "🚀 Abriendo Synap en WSL2..." -ForegroundColor Cyan
wsl -d Ubuntu-22.04 -e bash -c "cd ~/proyectos/Synap && bash"
"@

$quickAccessPath = "$env:USERPROFILE\Desktop\synap.ps1"

$createQuickAccess = Read-Host "¿Deseas crear un acceso rápido en el escritorio? (S/N)"

if ($createQuickAccess -eq "S" -or $createQuickAccess -eq "s") {
    $quickAccessScript | Out-File -FilePath $quickAccessPath -Encoding UTF8
    Print-Success "Acceso rápido creado en: $quickAccessPath"
}

# Resumen final
Print-Header "RESUMEN DE INSTALACIÓN"

Write-Host ""
Print-Success "✅ WSL habilitado"
Print-Success "✅ Plataforma de Máquina Virtual habilitada"
Print-Success "✅ Kernel de Linux actualizado"
Print-Success "✅ WSL2 como versión predeterminada"
Print-Success "✅ Archivo .wslconfig configurado"

Write-Host ""
Print-Info "PRÓXIMOS PASOS:"
Write-Host ""
Write-Host "1. Asegúrate de que Ubuntu 22.04 esté instalado:" -ForegroundColor Yellow
Write-Host "   wsl --list --verbose" -ForegroundColor Cyan
Write-Host ""
Write-Host "2. Si no está instalado, instálalo:" -ForegroundColor Yellow
Write-Host "   wsl --install -d Ubuntu-22.04" -ForegroundColor Cyan
Write-Host ""
Write-Host "3. Abre Ubuntu y configura usuario/contraseña" -ForegroundColor Yellow
Write-Host ""
Write-Host "4. Instala Docker Desktop:" -ForegroundColor Yellow
Write-Host "   https://www.docker.com/products/docker-desktop/" -ForegroundColor Cyan
Write-Host ""
Write-Host "5. En Docker Desktop, habilita integración con WSL2:" -ForegroundColor Yellow
Write-Host "   Settings > Resources > WSL Integration" -ForegroundColor Cyan
Write-Host ""
Write-Host "6. En Ubuntu, clona y configura Synap:" -ForegroundColor Yellow
Write-Host "   cd ~/proyectos" -ForegroundColor Cyan
Write-Host "   git clone https://github.com/eleven-it/Synap.git" -ForegroundColor Cyan
Write-Host "   cd Synap" -ForegroundColor Cyan
Write-Host "   chmod +x misc/scripts/setup_wsl2.sh" -ForegroundColor Cyan
Write-Host "   ./misc/scripts/setup_wsl2.sh" -ForegroundColor Cyan
Write-Host ""

Print-Header "¡CONFIGURACIÓN COMPLETADA! 🎉"

Write-Host ""
Write-Host "Para más información, consulta:" -ForegroundColor Yellow
Write-Host "  misc/documentacion/deploy_wsl2_docker_desktop.md" -ForegroundColor Cyan
Write-Host ""

pause

