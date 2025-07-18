#!/bin/bash

# Script para restaurar base de datos administraNET
# Uso: ./restore_administraNET.sh <archivo_backup.sql> [nombre_base_datos]

set -e  # Salir en caso de error

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para imprimir mensajes
print_message() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Verificar argumentos
BACKUP_FILE=$1
DB_NAME=${2:-administraNET_dev}

if [ -z "$BACKUP_FILE" ]; then
    print_error "Uso: $0 <archivo_backup.sql> [nombre_base_datos]"
    print_error "Ejemplo: $0 backup_administraNET_20241201.sql administraNET_dev"
    exit 1
fi

# Verificar que el archivo existe
if [ ! -f "$BACKUP_FILE" ]; then
    print_error "El archivo $BACKUP_FILE no existe"
    exit 1
fi

# Verificar que MySQL esté disponible
if ! command -v mysql &> /dev/null; then
    print_error "MySQL no está instalado o no está en el PATH"
    exit 1
fi

print_message "Iniciando restauración de base de datos administraNET..."
print_message "Archivo de backup: $BACKUP_FILE"
print_message "Base de datos destino: $DB_NAME"

# Verificar conexión a MySQL
print_message "Verificando conexión a MySQL..."
if ! mysql -u root -p -e "SELECT 1;" &> /dev/null; then
    print_error "No se puede conectar a MySQL. Verifica las credenciales."
    exit 1
fi

# Crear base de datos si no existe
print_message "Creando base de datos '$DB_NAME' si no existe..."
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS \`$DB_NAME\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# Verificar si la base de datos tiene tablas
TABLES_COUNT=$(mysql -u root -p -s -N -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = '$DB_NAME';")

if [ "$TABLES_COUNT" -gt 0 ]; then
    print_warning "La base de datos '$DB_NAME' ya contiene $TABLES_COUNT tablas"
    read -p "¿Deseas continuar y sobrescribir los datos? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_message "Restauración cancelada por el usuario"
        exit 0
    fi
fi

# Crear backup de la base actual si existe
if [ "$TABLES_COUNT" -gt 0 ]; then
    BACKUP_NAME="backup_${DB_NAME}_$(date +%Y%m%d_%H%M%S).sql"
    print_message "Creando backup de la base actual: $BACKUP_NAME"
    mysqldump -u root -p "$DB_NAME" > "$BACKUP_NAME"
    print_success "Backup creado: $BACKUP_NAME"
fi

# Restaurar backup
print_message "Restaurando backup..."
if mysql -u root -p "$DB_NAME" < "$BACKUP_FILE"; then
    print_success "Restauración completada exitosamente"
else
    print_error "Error durante la restauración"
    exit 1
fi

# Verificar restauración
print_message "Verificando restauración..."
NEW_TABLES_COUNT=$(mysql -u root -p -s -N -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = '$DB_NAME';")
print_success "Base de datos '$DB_NAME' ahora contiene $NEW_TABLES_COUNT tablas"

# Verificar tablas principales de administraNET
print_message "Verificando tablas principales..."
TABLES_TO_CHECK=("stock" "stock_deposito" "articulos" "depositos" "clientes" "proveedores")

for table in "${TABLES_TO_CHECK[@]}"; do
    if mysql -u root -p -s -N -e "SHOW TABLES LIKE '$table' IN \`$DB_NAME\`;" | grep -q "$table"; then
        ROW_COUNT=$(mysql -u root -p -s -N -e "SELECT COUNT(*) FROM \`$DB_NAME\`.\`$table\`;")
        print_success "Tabla '$table' encontrada con $ROW_COUNT registros"
    else
        print_warning "Tabla '$table' no encontrada"
    fi
done

print_success "Proceso de restauración completado"
print_message "Puedes conectarte a la base de datos con: mysql -u root -p $DB_NAME" 