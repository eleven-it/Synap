from django.core.management.base import BaseCommand
import pymssql
import os
from datetime import datetime


class Command(BaseCommand):
    help = 'Exportar estructura completa de la base de datos Azure SQL a markdown'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            type=str,
            default='azure_schema.md',
            help='Archivo de salida (default: azure_schema.md)',
        )
        parser.add_argument(
            '--include-data',
            action='store_true',
            help='Incluir muestras de datos de las tablas',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('📊 Exportando estructura de Azure SQL Database')
        )
        self.stdout.write('=' * 60)

        # Configuración de conexión
        connection_config = {
            'SERVER': 'm52q7iitok.database.windows.net',
            'DATABASE': 'BEST',
            'USER': 'interfase$bestsox',
            'PASSWORD': 'Parsimotion2012',
            'PORT': '1433'
        }

        output_file = options['output']
        include_data = options['include_data']

        try:
            # Conectar a la base de datos
            conn = pymssql.connect(
                server=connection_config['SERVER'],
                port=int(connection_config['PORT']),
                database=connection_config['DATABASE'],
                user=connection_config['USER'],
                password=connection_config['PASSWORD'],
                timeout=30
            )

            # Generar contenido markdown
            content = self.generate_schema_markdown(conn, include_data)
            
            # Guardar archivo
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(content)

            self.stdout.write(
                self.style.SUCCESS(f'✅ Estructura exportada a: {output_file}')
            )
            
            conn.close()

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error al exportar esquema: {e}')
            )

    def generate_schema_markdown(self, conn, include_data=False):
        """Generar contenido markdown con la estructura de la base de datos"""
        
        content = []
        content.append('# Estructura de Base de Datos Azure SQL - BEST')
        content.append('')
        content.append(f'**Fecha de exportación:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        content.append(f'**Servidor:** m52q7iitok.database.windows.net')
        content.append(f'**Base de datos:** BEST')
        content.append('')
        content.append('---')
        content.append('')

        with conn.cursor() as cursor:
            # Información general de la base de datos
            content.extend(self.get_database_info(cursor))
            
            # Esquemas
            content.extend(self.get_schemas_info(cursor))
            
            # Tablas
            content.extend(self.get_tables_info(cursor, include_data))
            
            # Vistas
            content.extend(self.get_views_info(cursor))
            
            # Procedimientos almacenados
            content.extend(self.get_stored_procedures_info(cursor))
            
            # Funciones
            content.extend(self.get_functions_info(cursor))
            
            # Relaciones (Foreign Keys)
            content.extend(self.get_foreign_keys_info(cursor))
            
            # Índices
            content.extend(self.get_indexes_info(cursor))

        return '\n'.join(content)

    def get_database_info(self, cursor):
        """Obtener información general de la base de datos"""
        content = []
        content.append('## 📊 Información General de la Base de Datos')
        content.append('')
        
        try:
            cursor.execute("SELECT DB_NAME(), DATABASEPROPERTYEX(DB_NAME(), 'Status')")
            db_info = cursor.fetchone()
            content.append(f'- **Nombre:** {db_info[0]}')
            content.append(f'- **Estado:** {db_info[1]}')
            
            cursor.execute("SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE'")
            table_count = cursor.fetchone()[0]
            content.append(f'- **Total de tablas:** {table_count}')
            
            cursor.execute("SELECT COUNT(*) FROM INFORMATION_SCHEMA.VIEWS")
            view_count = cursor.fetchone()[0]
            content.append(f'- **Total de vistas:** {view_count}')
            
            cursor.execute("SELECT COUNT(*) FROM INFORMATION_SCHEMA.ROUTINES WHERE ROUTINE_TYPE = 'PROCEDURE'")
            proc_count = cursor.fetchone()[0]
            content.append(f'- **Procedimientos almacenados:** {proc_count}')
            
            cursor.execute("SELECT COUNT(*) FROM INFORMATION_SCHEMA.ROUTINES WHERE ROUTINE_TYPE = 'FUNCTION'")
            func_count = cursor.fetchone()[0]
            content.append(f'- **Funciones:** {func_count}')
            
        except Exception as e:
            content.append(f'- **Error al obtener información:** {e}')
        
        content.append('')
        return content

    def get_schemas_info(self, cursor):
        """Obtener información de esquemas"""
        content = []
        content.append('## 📚 Esquemas')
        content.append('')
        
        try:
            cursor.execute("""
                SELECT SCHEMA_NAME, SCHEMA_OWNER
                FROM INFORMATION_SCHEMA.SCHEMATA
                ORDER BY SCHEMA_NAME
            """)
            
            schemas = cursor.fetchall()
            if schemas:
                content.append('| Esquema | Propietario |')
                content.append('|---------|-------------|')
                for schema in schemas:
                    content.append(f'| {schema[0]} | {schema[1]} |')
            else:
                content.append('No se encontraron esquemas.')
                
        except Exception as e:
            content.append(f'Error al obtener esquemas: {e}')
        
        content.append('')
        return content

    def get_tables_info(self, cursor, include_data=False):
        """Obtener información detallada de las tablas"""
        content = []
        content.append('## 🗂️ Tablas')
        content.append('')
        
        try:
            # Obtener todas las tablas
            cursor.execute("""
                SELECT TABLE_SCHEMA, TABLE_NAME
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_TYPE = 'BASE TABLE'
                ORDER BY TABLE_SCHEMA, TABLE_NAME
            """)
            
            tables = cursor.fetchall()
            
            for table in tables:
                schema_name = table[0]
                table_name = table[1]
                full_table_name = f"{schema_name}.{table_name}"
                
                content.append(f'### 📋 {full_table_name}')
                content.append('')
                
                # Información de la tabla
                content.extend(self.get_table_details(cursor, schema_name, table_name))
                
                # Columnas
                content.extend(self.get_table_columns(cursor, schema_name, table_name))
                
                # Claves primarias
                content.extend(self.get_primary_keys(cursor, schema_name, table_name))
                
                # Claves foráneas
                content.extend(self.get_table_foreign_keys(cursor, schema_name, table_name))
                
                # Índices
                content.extend(self.get_table_indexes(cursor, schema_name, table_name))
                
                # Muestra de datos (opcional)
                if include_data:
                    content.extend(self.get_table_sample_data(cursor, schema_name, table_name))
                
                content.append('---')
                content.append('')
                
        except Exception as e:
            content.append(f'Error al obtener tablas: {e}')
        
        return content

    def get_table_details(self, cursor, schema_name, table_name):
        """Obtener detalles de una tabla específica"""
        content = []
        
        try:
            # Información de la tabla
            cursor.execute("""
                SELECT 
                    t.TABLE_TYPE,
                    t.TABLE_CATALOG,
                    t.TABLE_SCHEMA,
                    t.TABLE_NAME
                FROM INFORMATION_SCHEMA.TABLES t
                WHERE t.TABLE_SCHEMA = %s AND t.TABLE_NAME = %s
            """, (schema_name, table_name))
            
            table_info = cursor.fetchone()
            if table_info:
                content.append(f'- **Tipo:** {table_info[0]}')
                content.append(f'- **Catálogo:** {table_info[1]}')
                content.append(f'- **Esquema:** {table_info[2]}')
                content.append(f'- **Nombre:** {table_info[3]}')
                content.append('')
                
        except Exception as e:
            content.append(f'- **Error:** {e}')
            content.append('')
        
        return content

    def get_table_columns(self, cursor, schema_name, table_name):
        """Obtener columnas de una tabla"""
        content = []
        content.append('#### Columnas')
        content.append('')
        
        try:
            cursor.execute("""
                SELECT 
                    COLUMN_NAME,
                    DATA_TYPE,
                    IS_NULLABLE,
                    COLUMN_DEFAULT,
                    CHARACTER_MAXIMUM_LENGTH,
                    NUMERIC_PRECISION,
                    NUMERIC_SCALE,
                    ORDINAL_POSITION
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                ORDER BY ORDINAL_POSITION
            """, (schema_name, table_name))
            
            columns = cursor.fetchall()
            
            if columns:
                content.append('| Columna | Tipo | Nullable | Default | Longitud | Precisión | Escala | Posición |')
                content.append('|---------|------|----------|---------|----------|-----------|--------|----------|')
                
                for col in columns:
                    col_name = col[0]
                    data_type = col[1]
                    is_nullable = col[2]
                    default_value = col[3] or ''
                    max_length = col[4] or ''
                    precision = col[5] or ''
                    scale = col[6] or ''
                    position = col[7]
                    
                    content.append(f'| {col_name} | {data_type} | {is_nullable} | {default_value} | {max_length} | {precision} | {scale} | {position} |')
            else:
                content.append('No se encontraron columnas.')
                
        except Exception as e:
            content.append(f'Error al obtener columnas: {e}')
        
        content.append('')
        return content

    def get_primary_keys(self, cursor, schema_name, table_name):
        """Obtener claves primarias de una tabla"""
        content = []
        content.append('#### 🔑 Clave Primaria')
        content.append('')
        
        try:
            cursor.execute("""
                SELECT 
                    COLUMN_NAME
                FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                WHERE TABLE_SCHEMA = %s 
                    AND TABLE_NAME = %s 
                    AND CONSTRAINT_NAME LIKE 'PK_%%'
                ORDER BY ORDINAL_POSITION
            """, (schema_name, table_name))
            
            pk_columns = cursor.fetchall()
            
            if pk_columns:
                pk_names = [col[0] for col in pk_columns]
                content.append(f'**Columnas:** {", ".join(pk_names)}')
            else:
                content.append('No tiene clave primaria definida.')
                
        except Exception as e:
            content.append(f'Error al obtener clave primaria: {e}')
        
        content.append('')
        return content

    def get_table_foreign_keys(self, cursor, schema_name, table_name):
        """Obtener claves foráneas de una tabla específica"""
        content = []
        content.append('#### 🔗 Claves Foráneas')
        content.append('')
        
        try:
            cursor.execute("""
                SELECT 
                    CONSTRAINT_NAME,
                    COLUMN_NAME,
                    REFERENCED_TABLE_SCHEMA,
                    REFERENCED_TABLE_NAME,
                    REFERENCED_COLUMN_NAME
                FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                WHERE TABLE_SCHEMA = %s 
                    AND TABLE_NAME = %s 
                    AND REFERENCED_TABLE_NAME IS NOT NULL
                ORDER BY CONSTRAINT_NAME, ORDINAL_POSITION
            """, (schema_name, table_name))
            
            fk_columns = cursor.fetchall()
            
            if fk_columns:
                content.append('| Constraint | Columna | Tabla Referenciada | Columna Referenciada |')
                content.append('|------------|--------|-------------------|---------------------|')
                
                for fk in fk_columns:
                    constraint_name = fk[0]
                    column_name = fk[1]
                    ref_schema = fk[2]
                    ref_table = fk[3]
                    ref_column = fk[4]
                    
                    ref_full_name = f"{ref_schema}.{ref_table}" if ref_schema else ref_table
                    content.append(f'| {constraint_name} | {column_name} | {ref_full_name} | {ref_column} |')
            else:
                content.append('No tiene claves foráneas.')
                
        except Exception as e:
            content.append(f'Error al obtener claves foráneas: {e}')
        
        content.append('')
        return content

    def get_table_indexes(self, cursor, schema_name, table_name):
        """Obtener índices de una tabla"""
        content = []
        content.append('#### 📈 Índices')
        content.append('')
        
        try:
            cursor.execute("""
                SELECT 
                    i.name AS IndexName,
                    i.type_desc AS IndexType,
                    i.is_unique,
                    i.is_primary_key,
                    STUFF((
                        SELECT ', ' + c.name
                        FROM sys.index_columns ic
                        JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
                        WHERE ic.object_id = i.object_id AND ic.index_id = i.index_id
                        ORDER BY ic.key_ordinal
                        FOR XML PATH('')
                    ), 1, 2, '') AS ColumnNames
                FROM sys.indexes i
                JOIN sys.objects o ON i.object_id = o.object_id
                WHERE o.schema_id = SCHEMA_ID(%s) AND o.name = %s
                ORDER BY i.name
            """, (schema_name, table_name))
            
            indexes = cursor.fetchall()
            
            if indexes:
                content.append('| Nombre | Tipo | Único | PK | Columnas |')
                content.append('|--------|------|-------|----|----------|')
                
                for idx in indexes:
                    name = idx[0]
                    index_type = idx[1]
                    is_unique = 'Sí' if idx[2] else 'No'
                    is_pk = 'Sí' if idx[3] else 'No'
                    columns = idx[4] or ''
                    
                    content.append(f'| {name} | {index_type} | {is_unique} | {is_pk} | {columns} |')
            else:
                content.append('No se encontraron índices.')
                
        except Exception as e:
            content.append(f'Error al obtener índices: {e}')
        
        content.append('')
        return content

    def get_table_sample_data(self, cursor, schema_name, table_name):
        """Obtener muestra de datos de una tabla"""
        content = []
        content.append('#### 📊 Muestra de Datos')
        content.append('')
        
        try:
            cursor.execute(f"SELECT TOP 5 * FROM [{schema_name}].[{table_name}]")
            sample_data = cursor.fetchall()
            
            if sample_data:
                # Obtener nombres de columnas
                columns = [desc[0] for desc in cursor.description]
                
                content.append('| ' + ' | '.join(columns) + ' |')
                content.append('|' + '|'.join(['---' for _ in columns]) + '|')
                
                for row in sample_data:
                    formatted_row = []
                    for cell in row:
                        if cell is None:
                            formatted_row.append('NULL')
                        elif isinstance(cell, (str, bytes)):
                            # Truncar strings largos
                            cell_str = str(cell)
                            if len(cell_str) > 50:
                                cell_str = cell_str[:47] + '...'
                            formatted_row.append(cell_str)
                        else:
                            formatted_row.append(str(cell))
                    
                    content.append('| ' + ' | '.join(formatted_row) + ' |')
            else:
                content.append('La tabla está vacía.')
                
        except Exception as e:
            content.append(f'Error al obtener muestra de datos: {e}')
        
        content.append('')
        return content

    def get_views_info(self, cursor):
        """Obtener información de vistas"""
        content = []
        content.append('## 👁️ Vistas')
        content.append('')
        
        try:
            cursor.execute("""
                SELECT 
                    TABLE_SCHEMA,
                    TABLE_NAME,
                    VIEW_DEFINITION
                FROM INFORMATION_SCHEMA.VIEWS
                ORDER BY TABLE_SCHEMA, TABLE_NAME
            """)
            
            views = cursor.fetchall()
            
            if views:
                content.append('| Esquema | Nombre | Definición |')
                content.append('|---------|--------|------------|')
                
                for view in views:
                    schema = view[0]
                    name = view[1]
                    definition = view[2][:100] + '...' if len(view[2]) > 100 else view[2]
                    
                    content.append(f'| {schema} | {name} | {definition} |')
            else:
                content.append('No se encontraron vistas.')
                
        except Exception as e:
            content.append(f'Error al obtener vistas: {e}')
        
        content.append('')
        return content

    def get_stored_procedures_info(self, cursor):
        """Obtener información de procedimientos almacenados"""
        content = []
        content.append('## 🔧 Procedimientos Almacenados')
        content.append('')
        
        try:
            cursor.execute("""
                SELECT 
                    ROUTINE_SCHEMA,
                    ROUTINE_NAME,
                    ROUTINE_DEFINITION
                FROM INFORMATION_SCHEMA.ROUTINES
                WHERE ROUTINE_TYPE = 'PROCEDURE'
                ORDER BY ROUTINE_SCHEMA, ROUTINE_NAME
            """)
            
            procedures = cursor.fetchall()
            
            if procedures:
                content.append('| Esquema | Nombre | Definición |')
                content.append('|---------|--------|------------|')
                
                for proc in procedures:
                    schema = proc[0]
                    name = proc[1]
                    definition = proc[2][:100] + '...' if len(proc[2]) > 100 else proc[2]
                    
                    content.append(f'| {schema} | {proc[1]} | {definition} |')
            else:
                content.append('No se encontraron procedimientos almacenados.')
                
        except Exception as e:
            content.append(f'Error al obtener procedimientos: {e}')
        
        content.append('')
        return content

    def get_functions_info(self, cursor):
        """Obtener información de funciones"""
        content = []
        content.append('## ⚙️ Funciones')
        content.append('')
        
        try:
            cursor.execute("""
                SELECT 
                    ROUTINE_SCHEMA,
                    ROUTINE_NAME,
                    ROUTINE_DEFINITION
                FROM INFORMATION_SCHEMA.ROUTINES
                WHERE ROUTINE_TYPE = 'FUNCTION'
                ORDER BY ROUTINE_SCHEMA, ROUTINE_NAME
            """)
            
            functions = cursor.fetchall()
            
            if functions:
                content.append('| Esquema | Nombre | Definición |')
                content.append('|---------|--------|------------|')
                
                for func in functions:
                    schema = func[0]
                    name = func[1]
                    definition = func[2][:100] + '...' if len(func[2]) > 100 else func[2]
                    
                    content.append(f'| {schema} | {name} | {definition} |')
            else:
                content.append('No se encontraron funciones.')
                
        except Exception as e:
            content.append(f'Error al obtener funciones: {e}')
        
        content.append('')
        return content

    def get_foreign_keys_info(self, cursor):
        """Obtener todas las relaciones de claves foráneas"""
        content = []
        content.append('## 🔗 Relaciones de Claves Foráneas')
        content.append('')
        
        try:
            cursor.execute("""
                SELECT 
                    fk.name AS FK_Name,
                    OBJECT_NAME(fk.parent_object_id) AS TableName,
                    COL_NAME(fkc.parent_object_id, fkc.parent_column_id) AS ColumnName,
                    OBJECT_NAME(fk.referenced_object_id) AS ReferencedTableName,
                    COL_NAME(fkc.referenced_object_id, fkc.referenced_column_id) AS ReferencedColumnName
                FROM sys.foreign_keys fk
                INNER JOIN sys.foreign_key_columns fkc ON fk.object_id = fkc.constraint_object_id
                ORDER BY TableName, ColumnName
            """)
            
            foreign_keys = cursor.fetchall()
            
            if foreign_keys:
                content.append('| Tabla | Columna | Tabla Referenciada | Columna Referenciada | Constraint |')
                content.append('|-------|---------|-------------------|---------------------|------------|')
                
                for fk in foreign_keys:
                    fk_name = fk[0]
                    table_name = fk[1]
                    column_name = fk[2]
                    ref_table = fk[3]
                    ref_column = fk[4]
                    
                    content.append(f'| {table_name} | {column_name} | {ref_table} | {ref_column} | {fk_name} |')
            else:
                content.append('No se encontraron claves foráneas.')
                
        except Exception as e:
            content.append(f'Error al obtener claves foráneas: {e}')
        
        content.append('')
        return content

    def get_indexes_info(self, cursor):
        """Obtener información general de índices"""
        content = []
        content.append('## 📈 Índices del Sistema')
        content.append('')
        
        try:
            cursor.execute("""
                SELECT 
                    OBJECT_SCHEMA_NAME(i.object_id) AS SchemaName,
                    OBJECT_NAME(i.object_id) AS TableName,
                    i.name AS IndexName,
                    i.type_desc AS IndexType,
                    i.is_unique,
                    i.is_primary_key
                FROM sys.indexes i
                WHERE i.object_id > 0
                ORDER BY SchemaName, TableName, IndexName
            """)
            
            indexes = cursor.fetchall()
            
            if indexes:
                content.append('| Esquema | Tabla | Índice | Tipo | Único | PK |')
                content.append('|---------|-------|--------|------|-------|----|')
                
                for idx in indexes:
                    schema = idx[0]
                    table = idx[1]
                    index_name = idx[2]
                    index_type = idx[3]
                    is_unique = 'Sí' if idx[4] else 'No'
                    is_pk = 'Sí' if idx[5] else 'No'
                    
                    content.append(f'| {schema} | {table} | {index_name} | {index_type} | {is_unique} | {is_pk} |')
            else:
                content.append('No se encontraron índices.')
                
        except Exception as e:
            content.append(f'Error al obtener índices: {e}')
        
        content.append('')
        return content


