"""
Comando para inspeccionar la estructura de la tabla 'articulos' y tablas relacionadas
en MySQL para el reporte de Backorder vs Stock vs Facturación.
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from reports.services.connection_pool import get_mysql_pool
from typing import Dict, List, Optional


class Command(BaseCommand):
    help = 'Inspecciona la estructura de la tabla articulos y tablas relacionadas en MySQL'

    def add_arguments(self, parser):
        parser.add_argument(
            '--base-empresa',
            type=str,
            required=True,
            help='Nombre de la base de datos MySQL (base_empresa)',
        )
        parser.add_argument(
            '--table',
            type=str,
            default='articulos',
            help='Nombre de la tabla a inspeccionar (default: articulos)',
        )
        parser.add_argument(
            '--all-tables',
            action='store_true',
            help='Inspeccionar todas las tablas relacionadas (articulos, comp_ped_reng, stock, categorias)',
        )

    def handle(self, *args, **options):
        base_empresa = options['base_empresa']
        table_name = options['table']
        all_tables = options['all_tables']

        # Obtener connection pool
        pool = get_mysql_pool()
        
        try:
            with pool.get_connection(base_empresa) as conn:
                cursor = conn.cursor()

                self.stdout.write(self.style.SUCCESS(f'✅ Conectado a MySQL: {base_empresa}'))
                self.stdout.write('=' * 80)

                if all_tables:
                    # Inspeccionar todas las tablas relacionadas
                    tables_to_check = [
                        'articulos',
                        'comp_ped',
                        'comp_ped_reng',
                        'stock',
                        'inventario',
                        'productos_stock',
                        'categorias',
                        'rubros',
                        'rubro',
                    ]
                    
                    for tbl in tables_to_check:
                        self.stdout.write(f'\n📋 Tabla: {tbl}')
                        self.stdout.write('-' * 80)
                        if self.table_exists(cursor, base_empresa, tbl):
                            self.inspect_table(cursor, base_empresa, tbl)
                        else:
                            self.stdout.write(self.style.WARNING(f'   ⚠️  Tabla "{tbl}" no existe'))
                else:
                    # Inspeccionar solo la tabla especificada
                    self.stdout.write(f'\n📋 Tabla: {table_name}')
                    self.stdout.write('-' * 80)
                    if self.table_exists(cursor, base_empresa, table_name):
                        self.inspect_table(cursor, base_empresa, table_name)
                    else:
                        self.stdout.write(self.style.ERROR(f'❌ Tabla "{table_name}" no existe'))
                        # Sugerir tablas similares
                        self.suggest_similar_tables(cursor, base_empresa, table_name)

                # Mostrar campos requeridos para el reporte
                self.stdout.write('\n' + '=' * 80)
                self.stdout.write(self.style.SUCCESS('📊 CAMPOS REQUERIDOS PARA EL REPORTE'))
                self.stdout.write('=' * 80)
                self.show_required_fields()

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error: {e}'))
            import traceback
            self.stdout.write(traceback.format_exc())

    def table_exists(self, cursor, database: str, table_name: str) -> bool:
        """Verifica si una tabla existe en la base de datos."""
        try:
            cursor.execute("""
                SELECT COUNT(*) 
                FROM information_schema.TABLES 
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
            """, (database, table_name))
            return cursor.fetchone()[0] > 0
        except Exception:
            return False

    def inspect_table(self, cursor, database: str, table_name: str):
        """Inspecciona la estructura de una tabla."""
        try:
            # Obtener información detallada de columnas
            cursor.execute("""
                SELECT 
                    COLUMN_NAME,
                    DATA_TYPE,
                    COLUMN_TYPE,
                    IS_NULLABLE,
                    COLUMN_KEY,
                    COLUMN_DEFAULT,
                    EXTRA,
                    COLUMN_COMMENT
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = %s
                AND TABLE_NAME = %s
                ORDER BY ORDINAL_POSITION
            """, (database, table_name))

            columns = cursor.fetchall()

            if not columns:
                self.stdout.write(self.style.WARNING(f'   ⚠️  No se encontraron columnas'))
                return

            # Encabezado de tabla
            self.stdout.write(f'{"Campo":<30} {"Tipo":<25} {"Null":<8} {"Key":<8} {"Default":<15} {"Extra":<15}')
            self.stdout.write('-' * 80)

            for col in columns:
                col_name = col[0]
                data_type = col[1]
                col_type = col[2]
                is_nullable = col[3]
                col_key = col[4] or ''
                col_default = str(col[5]) if col[5] is not None else 'NULL'
                extra = col[6] or ''
                comment = col[7] or ''

                # Truncar valores largos
                col_default = col_default[:14] if len(col_default) > 14 else col_default
                extra = extra[:14] if len(extra) > 14 else extra

                self.stdout.write(
                    f'{col_name:<30} {col_type:<25} {is_nullable:<8} {col_key:<8} {col_default:<15} {extra:<15}'
                )
                if comment:
                    self.stdout.write(f'   └─ Comentario: {comment}')

            # Contar registros
            try:
                cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
                count = cursor.fetchone()[0]
                self.stdout.write(f'\n   📊 Total de registros: {count:,}')
            except Exception:
                pass

            # Mostrar índices
            self.show_indexes(cursor, database, table_name)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   ❌ Error inspeccionando tabla: {e}'))

    def show_indexes(self, cursor, database: str, table_name: str):
        """Muestra los índices de una tabla."""
        try:
            cursor.execute("""
                SELECT 
                    INDEX_NAME,
                    COLUMN_NAME,
                    NON_UNIQUE,
                    SEQ_IN_INDEX
                FROM information_schema.STATISTICS
                WHERE TABLE_SCHEMA = %s
                AND TABLE_NAME = %s
                ORDER BY INDEX_NAME, SEQ_IN_INDEX
            """, (database, table_name))

            indexes = cursor.fetchall()
            if indexes:
                self.stdout.write(f'\n   🔑 Índices:')
                current_index = None
                for idx in indexes:
                    idx_name = idx[0]
                    col_name = idx[1]
                    non_unique = idx[2]
                    unique_str = 'UNIQUE' if non_unique == 0 else 'INDEX'
                    
                    if idx_name != current_index:
                        if current_index is not None:
                            self.stdout.write('')
                        current_index = idx_name
                        self.stdout.write(f'      {idx_name} ({unique_str}): {col_name}', ending='')
                    else:
                        self.stdout.write(f', {col_name}', ending='')
                self.stdout.write('')

        except Exception as e:
            pass  # Ignorar errores al mostrar índices

    def suggest_similar_tables(self, cursor, database: str, table_name: str):
        """Sugiere tablas con nombres similares."""
        try:
            cursor.execute("""
                SELECT TABLE_NAME
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = %s
                AND TABLE_NAME LIKE %s
                ORDER BY TABLE_NAME
            """, (database, f'%{table_name}%'))

            similar = cursor.fetchall()
            if similar:
                self.stdout.write(f'\n   💡 Tablas con nombre similar:')
                for row in similar:
                    self.stdout.write(f'      - {row[0]}')
        except Exception:
            pass

    def show_required_fields(self):
        """Muestra los campos requeridos para el reporte de Backorder vs Stock vs Facturación."""
        required_fields = {
            'articulos': [
                'CodProducto / CodigoProducto (PK)',
                'CodManual (opcional)',
                'CodSistema (opcional)',
                'Descripcion / Nombre',
                'CodCategoria / CodRubro (FK a categorías)',
            ],
            'comp_ped_reng': [
                'NroComprobante (FK a comp_ped)',
                'Renglon (opcional, para PK compuesta)',
                'CodProducto / CodigoProducto (FK a articulos)',
                'Cantidad / CantidadPendiente',
                'PrecioUnitario / Precio',
                'Subtotal / Importe',
            ],
            'stock / inventario': [
                'CodProducto / CodigoProducto (FK a articulos)',
                'StockActual / Cantidad / Stock',
                'StockReservado (opcional, puede calcularse)',
            ],
            'categorias / rubros': [
                'CodCategoria / CodRubro (PK)',
                'Nombre / Descripcion',
            ],
        }

        for table_group, fields in required_fields.items():
            self.stdout.write(f'\n📦 {table_group.upper()}:')
            for field in fields:
                self.stdout.write(f'   • {field}')
