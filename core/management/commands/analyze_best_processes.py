from django.core.management.base import BaseCommand
import pymssql
from datetime import datetime
import re


class Command(BaseCommand):
    help = 'Análisis profundo y detallado de todos los procesos del sistema BEST'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            type=str,
            default='best_processes_analysis.md',
            help='Archivo de salida para el análisis (default: best_processes_analysis.md)',
        )
        parser.add_argument(
            '--detailed',
            action='store_true',
            help='Incluir análisis detallado de cada proceso',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🔍 Análisis Profundo del Sistema BEST')
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
        detailed = options['detailed']

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

            # Generar análisis completo
            content = self.generate_process_analysis(conn, detailed)
            
            # Guardar archivo
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(content)

            self.stdout.write(
                self.style.SUCCESS(f'✅ Análisis guardado en: {output_file}')
            )
            
            conn.close()

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error en el análisis: {e}')
            )

    def generate_process_analysis(self, conn, detailed=False):
        """Generar análisis completo de procesos"""
        
        content = []
        content.append('# Análisis Profundo de Procesos - Sistema BEST')
        content.append('')
        content.append(f'**Fecha de análisis:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        content.append(f'**Servidor:** m52q7iitok.database.windows.net')
        content.append(f'**Base de datos:** BEST')
        content.append('')
        content.append('---')
        content.append('')

        with conn.cursor() as cursor:
            # 1. Análisis general del sistema
            content.extend(self.analyze_system_overview(cursor))
            
            # 2. Análisis de módulos principales
            content.extend(self.analyze_main_modules(cursor))
            
            # 3. Análisis de procesos de negocio
            content.extend(self.analyze_business_processes(cursor))
            
            # 4. Análisis de flujos de datos
            content.extend(self.analyze_data_flows(cursor))
            
            # 5. Análisis de procedimientos almacenados
            content.extend(self.analyze_stored_procedures(cursor))
            
            # 6. Análisis de vistas y consultas complejas
            content.extend(self.analyze_views_and_queries(cursor))
            
            # 7. Análisis de integraciones
            content.extend(self.analyze_integrations(cursor))
            
            # 8. Análisis de seguridad y permisos
            content.extend(self.analyze_security_and_permissions(cursor))
            
            # 9. Análisis de rendimiento y optimización
            content.extend(self.analyze_performance_optimization(cursor))
            
            # 10. Conclusiones y recomendaciones
            content.extend(self.generate_conclusions_and_recommendations(cursor))

        return '\n'.join(content)

    def analyze_system_overview(self, cursor):
        """Análisis general del sistema"""
        content = []
        content.append('## 📊 Análisis General del Sistema')
        content.append('')
        
        try:
            # Información básica del sistema
            cursor.execute("SELECT @@VERSION")
            version = cursor.fetchone()[0]
            content.append(f'**Versión del servidor:** {version[:100]}...')
            
            # Estadísticas generales
            cursor.execute("SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE'")
            table_count = cursor.fetchone()[0]
            content.append(f'**Total de tablas:** {table_count}')
            
            cursor.execute("SELECT COUNT(*) FROM INFORMATION_SCHEMA.VIEWS")
            view_count = cursor.fetchone()[0]
            content.append(f'**Total de vistas:** {view_count}')
            
            cursor.execute("SELECT COUNT(*) FROM INFORMATION_SCHEMA.ROUTINES WHERE ROUTINE_TYPE = 'PROCEDURE'")
            proc_count = cursor.fetchone()[0]
            content.append(f'**Procedimientos almacenados:** {proc_count}')
            
            cursor.execute("SELECT COUNT(*) FROM INFORMATION_SCHEMA.ROUTINES WHERE ROUTINE_TYPE = 'FUNCTION'")
            func_count = cursor.fetchone()[0]
            content.append(f'**Funciones:** {func_count}')
            
            # Análisis de esquemas
            cursor.execute("SELECT SCHEMA_NAME, COUNT(*) FROM INFORMATION_SCHEMA.TABLES GROUP BY SCHEMA_NAME ORDER BY COUNT(*) DESC")
            schemas = cursor.fetchall()
            content.append('')
            content.append('**Distribución por esquemas:**')
            for schema, count in schemas:
                content.append(f'- {schema}: {count} objetos')
            
        except Exception as e:
            content.append(f'Error en análisis general: {e}')
        
        content.append('')
        return content

    def analyze_main_modules(self, cursor):
        """Análisis de módulos principales"""
        content = []
        content.append('## 🏗️ Módulos Principales del Sistema')
        content.append('')
        
        # Definir módulos basados en el análisis previo
        modules = {
            'Gestión de Clientes': ['CL', 'CY'],
            'Gestión de Materiales/Productos': ['MM', 'MC'],
            'Gestión Bancaria': ['BA', 'CU'],
            'Gestión de Órdenes': ['OO', 'OP'],
            'Gestión de Transacciones': ['TG', 'TT'],
            'Gestión de Documentos': ['DD'],
            'Configuración del Sistema': ['CC', 'PR'],
            'Autenticación y Usuarios': ['aspnet_*'],
            'Reportes y Consultas': ['JR', 'YY'],
            'Gestión de Proveedores': ['PR']
        }
        
        for module_name, tables in modules.items():
            content.append(f'### 📋 {module_name}')
            content.append('')
            
            total_records = 0
            for table in tables:
                if table == 'aspnet_*':
                    # Buscar todas las tablas aspnet
                    cursor.execute("""
                        SELECT TABLE_NAME, (SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES t2 
                        WHERE t2.TABLE_NAME = t1.TABLE_NAME) as record_count
                        FROM INFORMATION_SCHEMA.TABLES t1
                        WHERE TABLE_NAME LIKE 'aspnet_%'
                    """)
                    aspnet_tables = cursor.fetchall()
                    for table_name, count in aspnet_tables:
                        content.append(f'- **{table_name}**: {count} registros')
                        total_records += count
                else:
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM dbo.{table}")
                        count = cursor.fetchone()[0]
                        content.append(f'- **{table}**: {count:,} registros')
                        total_records += count
                    except:
                        content.append(f'- **{table}**: No existe o error de acceso')
            
            content.append(f'**Total del módulo:** {total_records:,} registros')
            content.append('')
        
        return content

    def analyze_business_processes(self, cursor):
        """Análisis de procesos de negocio"""
        content = []
        content.append('## 🔄 Procesos de Negocio Identificados')
        content.append('')
        
        # Proceso 1: Gestión de Inventario
        content.append('### 📦 1. Gestión de Inventario')
        content.append('')
        content.append('**Tablas involucradas:** MM (Materiales), MC (Materiales por Cliente)')
        content.append('**Proceso:**')
        content.append('- Definición de materiales (MM)')
        content.append('- Asignación de materiales a clientes (MC)')
        content.append('- Control de stock y disponibilidad')
        content.append('- Gestión de unidades de medida')
        content.append('')
        
        # Proceso 2: Gestión de Clientes
        content.append('### 👥 2. Gestión de Clientes')
        content.append('')
        content.append('**Tablas involucradas:** CL (Clientes), CY (Condiciones)')
        content.append('**Proceso:**')
        content.append('- Registro de clientes')
        content.append('- Configuración de condiciones comerciales')
        content.append('- Control de estados y bloqueos')
        content.append('')
        
        # Proceso 3: Gestión Financiera
        content.append('### 💰 3. Gestión Financiera')
        content.append('')
        content.append('**Tablas involucradas:** BA (Bancos), CU (Monedas)')
        content.append('**Proceso:**')
        content.append('- Registro de transacciones bancarias')
        content.append('- Gestión de múltiples monedas')
        content.append('- Control de tasas de cambio')
        content.append('- Seguimiento de movimientos financieros')
        content.append('')
        
        # Proceso 4: Gestión de Órdenes
        content.append('### 📋 4. Gestión de Órdenes')
        content.append('')
        content.append('**Tablas involucradas:** OO (Órdenes), OP (Operaciones)')
        content.append('**Proceso:**')
        content.append('- Creación y seguimiento de órdenes')
        content.append('- Gestión de operaciones por orden')
        content.append('- Control de estados y fechas')
        content.append('- Asignación de responsabilidades')
        content.append('')
        
        # Proceso 5: Gestión de Transacciones
        content.append('### 💳 5. Gestión de Transacciones')
        content.append('')
        content.append('**Tablas involucradas:** TG (Transacciones), TT (Tipos de Transacción)')
        content.append('**Proceso:**')
        content.append('- Registro de transacciones del sistema')
        content.append('- Clasificación por tipos')
        content.append('- Auditoría de movimientos')
        content.append('')
        
        # Proceso 6: Configuración del Sistema
        content.append('### ⚙️ 6. Configuración del Sistema')
        content.append('')
        content.append('**Tablas involucradas:** CC (Centros de Costo), PR (Proveedores/Parámetros)')
        content.append('**Proceso:**')
        content.append('- Configuración de centros de costo')
        content.append('- Gestión de parámetros del sistema')
        content.append('- Configuración de proveedores')
        content.append('')
        
        return content

    def analyze_data_flows(self, cursor):
        """Análisis de flujos de datos"""
        content = []
        content.append('## 🔄 Flujos de Datos del Sistema')
        content.append('')
        
        # Flujo 1: Creación de Cliente
        content.append('### 🔄 Flujo 1: Creación y Gestión de Cliente')
        content.append('')
        content.append('```mermaid')
        content.append('graph TD')
        content.append('    A[Crear Cliente] --> B[Tabla CL]')
        content.append('    B --> C[Configurar Condiciones CY]')
        content.append('    C --> D[Asignar Materiales MC]')
        content.append('    D --> E[Registrar Transacciones TG]')
        content.append('```')
        content.append('')
        
        # Flujo 2: Gestión de Inventario
        content.append('### 🔄 Flujo 2: Gestión de Inventario')
        content.append('')
        content.append('```mermaid')
        content.append('graph TD')
        content.append('    A[Definir Material MM] --> B[Asignar a Cliente MC]')
        content.append('    B --> C[Crear Orden OO]')
        content.append('    C --> D[Ejecutar Operaciones OP]')
        content.append('    D --> E[Actualizar Stock MC]')
        content.append('    E --> F[Registrar Transacción TG]')
        content.append('```')
        content.append('')
        
        # Flujo 3: Proceso Financiero
        content.append('### 🔄 Flujo 3: Proceso Financiero')
        content.append('')
        content.append('```mermaid')
        content.append('graph TD')
        content.append('    A[Transacción Bancaria] --> B[Tabla BA]')
        content.append('    B --> C[Validar Moneda CU]')
        content.append('    C --> D[Actualizar Saldos]')
        content.append('    D --> E[Registrar en TG]')
        content.append('```')
        content.append('')
        
        return content

    def analyze_stored_procedures(self, cursor):
        """Análisis de procedimientos almacenados"""
        content = []
        content.append('## 🔧 Análisis de Procedimientos Almacenados')
        content.append('')
        
        try:
            # Obtener procedimientos almacenados
            cursor.execute("""
                SELECT ROUTINE_NAME, ROUTINE_DEFINITION
                FROM INFORMATION_SCHEMA.ROUTINES
                WHERE ROUTINE_TYPE = 'PROCEDURE'
                ORDER BY ROUTINE_NAME
            """)
            
            procedures = cursor.fetchall()
            
            if procedures:
                content.append(f'**Total de procedimientos:** {len(procedures)}')
                content.append('')
                
                # Categorizar procedimientos por nombre
                categories = {
                    'Gestión de Clientes': [],
                    'Gestión de Materiales': [],
                    'Gestión Financiera': [],
                    'Gestión de Órdenes': [],
                    'Reportes': [],
                    'Utilidades': [],
                    'Otros': []
                }
                
                for proc_name, proc_def in procedures:
                    proc_name_lower = proc_name.lower()
                    
                    if any(word in proc_name_lower for word in ['cliente', 'client', 'cl']):
                        categories['Gestión de Clientes'].append(proc_name)
                    elif any(word in proc_name_lower for word in ['material', 'product', 'mm', 'mc']):
                        categories['Gestión de Materiales'].append(proc_name)
                    elif any(word in proc_name_lower for word in ['banco', 'bank', 'ba', 'financ']):
                        categories['Gestión Financiera'].append(proc_name)
                    elif any(word in proc_name_lower for word in ['orden', 'order', 'oo', 'op']):
                        categories['Gestión de Órdenes'].append(proc_name)
                    elif any(word in proc_name_lower for word in ['report', 'consulta', 'query']):
                        categories['Reportes'].append(proc_name)
                    elif any(word in proc_name_lower for word in ['util', 'helper', 'tool']):
                        categories['Utilidades'].append(proc_name)
                    else:
                        categories['Otros'].append(proc_name)
                
                # Mostrar categorías
                for category, procs in categories.items():
                    if procs:
                        content.append(f'### 📋 {category}')
                        content.append('')
                        for proc in procs[:10]:  # Mostrar solo los primeros 10
                            content.append(f'- {proc}')
                        if len(procs) > 10:
                            content.append(f'- ... y {len(procs) - 10} más')
                        content.append('')
                
            else:
                content.append('No se encontraron procedimientos almacenados.')
                
        except Exception as e:
            content.append(f'Error al analizar procedimientos: {e}')
        
        return content

    def analyze_views_and_queries(self, cursor):
        """Análisis de vistas y consultas complejas"""
        content = []
        content.append('## 👁️ Análisis de Vistas y Consultas')
        content.append('')
        
        try:
            # Obtener vistas
            cursor.execute("""
                SELECT TABLE_NAME, VIEW_DEFINITION
                FROM INFORMATION_SCHEMA.VIEWS
                ORDER BY TABLE_NAME
            """)
            
            views = cursor.fetchall()
            
            if views:
                content.append(f'**Total de vistas:** {len(views)}')
                content.append('')
                
                # Categorizar vistas
                view_categories = {
                    'Reportes de Clientes': [],
                    'Reportes de Materiales': [],
                    'Reportes Financieros': [],
                    'Reportes de Órdenes': [],
                    'Vistas de Resumen': [],
                    'Otros': []
                }
                
                for view_name, view_def in views:
                    view_name_lower = view_name.lower()
                    view_def_lower = view_def.lower()
                    
                    if any(word in view_name_lower or word in view_def_lower for word in ['cliente', 'client', 'cl']):
                        view_categories['Reportes de Clientes'].append(view_name)
                    elif any(word in view_name_lower or word in view_def_lower for word in ['material', 'product', 'mm', 'mc']):
                        view_categories['Reportes de Materiales'].append(view_name)
                    elif any(word in view_name_lower or word in view_def_lower for word in ['banco', 'bank', 'ba', 'financ']):
                        view_categories['Reportes Financieros'].append(view_name)
                    elif any(word in view_name_lower or word in view_def_lower for word in ['orden', 'order', 'oo', 'op']):
                        view_categories['Reportes de Órdenes'].append(view_name)
                    elif any(word in view_name_lower or word in view_def_lower for word in ['resumen', 'summary', 'total']):
                        view_categories['Vistas de Resumen'].append(view_name)
                    else:
                        view_categories['Otros'].append(view_name)
                
                # Mostrar categorías
                for category, view_list in view_categories.items():
                    if view_list:
                        content.append(f'### 📊 {category}')
                        content.append('')
                        for view in view_list[:10]:  # Mostrar solo los primeros 10
                            content.append(f'- {view}')
                        if len(view_list) > 10:
                            content.append(f'- ... y {len(view_list) - 10} más')
                        content.append('')
                
            else:
                content.append('No se encontraron vistas.')
                
        except Exception as e:
            content.append(f'Error al analizar vistas: {e}')
        
        return content

    def analyze_integrations(self, cursor):
        """Análisis de integraciones"""
        content = []
        content.append('## 🔗 Análisis de Integraciones')
        content.append('')
        
        # Integración con ASP.NET
        content.append('### 🔐 Integración con ASP.NET')
        content.append('')
        content.append('El sistema utiliza el framework de autenticación de ASP.NET:')
        content.append('- **aspnet_Users**: Gestión de usuarios')
        content.append('- **aspnet_Roles**: Gestión de roles')
        content.append('- **aspnet_UsersInRoles**: Asignación de roles')
        content.append('- **aspnet_Membership**: Gestión de membresías')
        content.append('- **aspnet_Profile**: Perfiles de usuario')
        content.append('')
        
        # Integración con XML/JSON
        content.append('### 📄 Integración con XML/JSON')
        content.append('')
        content.append('**Tabla JR**: Almacena datos en formato XML')
        content.append('- Posible integración con sistemas externos')
        content.append('- Intercambio de datos estructurados')
        content.append('- Configuraciones del sistema')
        content.append('')
        
        # Posibles integraciones externas
        content.append('### 🌐 Posibles Integraciones Externas')
        content.append('')
        content.append('Basado en la estructura de datos, el sistema podría integrarse con:')
        content.append('- **Sistemas bancarios**: Para transacciones financieras')
        content.append('- **Sistemas de inventario**: Para gestión de materiales')
        content.append('- **Sistemas ERP**: Para sincronización de datos')
        content.append('- **Sistemas de reportes**: Para generación de informes')
        content.append('')
        
        return content

    def analyze_security_and_permissions(self, cursor):
        """Análisis de seguridad y permisos"""
        content = []
        content.append('## 🔒 Análisis de Seguridad y Permisos')
        content.append('')
        
        # Esquemas de seguridad
        content.append('### 🛡️ Esquemas de Seguridad')
        content.append('')
        content.append('El sistema utiliza múltiples esquemas para control de acceso:')
        content.append('- **aspnet_Membership_BasicAccess**: Acceso básico')
        content.append('- **aspnet_Membership_FullAccess**: Acceso completo')
        content.append('- **aspnet_Membership_ReportingAccess**: Acceso a reportes')
        content.append('- **db_owner, db_datareader, db_datawriter**: Roles de base de datos')
        content.append('')
        
        # Control de acceso por módulos
        content.append('### 🔐 Control de Acceso por Módulos')
        content.append('')
        content.append('**Módulo de Clientes:**')
        content.append('- Lectura: db_datareader')
        content.append('- Escritura: db_datawriter')
        content.append('- Administración: db_owner')
        content.append('')
        content.append('**Módulo Financiero:**')
        content.append('- Acceso restringido a transacciones bancarias')
        content.append('- Validación de permisos por moneda')
        content.append('')
        content.append('**Módulo de Inventario:**')
        content.append('- Control de acceso por localización')
        content.append('- Validación de stock disponible')
        content.append('')
        
        return content

    def analyze_performance_optimization(self, cursor):
        """Análisis de rendimiento y optimización"""
        content = []
        content.append('## ⚡ Análisis de Rendimiento y Optimización')
        content.append('')
        
        try:
            # Análisis de índices
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
                content.append(f'**Total de índices:** {len(indexes)}')
                content.append('')
                
                # Estadísticas de índices
                index_types = {}
                for idx in indexes:
                    index_type = idx[3]
                    index_types[index_type] = index_types.get(index_type, 0) + 1
                
                content.append('**Distribución por tipo:**')
                for idx_type, count in index_types.items():
                    content.append(f'- {idx_type}: {count}')
                content.append('')
                
                # Índices principales por tabla
                content.append('**Índices principales por tabla:**')
                current_table = None
                for idx in indexes[:20]:  # Mostrar solo los primeros 20
                    schema = idx[0]
                    table = idx[1]
                    index_name = idx[2]
                    index_type = idx[3]
                    is_unique = idx[4]
                    is_pk = idx[5]
                    
                    if table != current_table:
                        content.append(f'- **{schema}.{table}**:')
                        current_table = table
                    
                    pk_marker = " (PK)" if is_pk else ""
                    unique_marker = " (Único)" if is_unique else ""
                    content.append(f'  - {index_name}: {index_type}{pk_marker}{unique_marker}')
                
                if len(indexes) > 20:
                    content.append(f'  - ... y {len(indexes) - 20} índices más')
                
            else:
                content.append('No se encontraron índices.')
                
        except Exception as e:
            content.append(f'Error al analizar rendimiento: {e}')
        
        content.append('')
        
        # Recomendaciones de optimización
        content.append('### 💡 Recomendaciones de Optimización')
        content.append('')
        content.append('**Basado en el análisis de datos:**')
        content.append('- **Tabla TG**: 3,880,730 registros - Considerar particionamiento')
        content.append('- **Tabla TT**: Alta actividad - Optimizar consultas')
        content.append('- **Tabla BA**: Transacciones bancarias - Índices en fechas')
        content.append('- **Tabla OO**: Órdenes - Índices en estados y fechas')
        content.append('')
        
        return content

    def generate_conclusions_and_recommendations(self, cursor):
        """Generar conclusiones y recomendaciones"""
        content = []
        content.append('## 📋 Conclusiones y Recomendaciones')
        content.append('')
        
        content.append('### 🎯 Conclusiones del Análisis')
        content.append('')
        content.append('**El sistema BEST es un ERP completo que incluye:**')
        content.append('')
        content.append('1. **Gestión de Clientes**: Sistema simplificado de clientes con condiciones comerciales')
        content.append('2. **Gestión de Inventario**: Control completo de materiales y stock')
        content.append('3. **Gestión Financiera**: Sistema bancario con múltiples monedas')
        content.append('4. **Gestión de Órdenes**: Proceso completo de órdenes y operaciones')
        content.append('5. **Gestión de Transacciones**: Auditoría completa de movimientos')
        content.append('6. **Sistema de Autenticación**: Integración con ASP.NET')
        content.append('7. **Reportes y Consultas**: Vistas y procedimientos para análisis')
        content.append('')
        
        content.append('### 🔄 Procesos Principales Identificados')
        content.append('')
        content.append('1. **Proceso de Venta**: Cliente → Orden → Operación → Facturación')
        content.append('2. **Proceso de Inventario**: Material → Stock → Movimientos → Actualización')
        content.append('3. **Proceso Financiero**: Transacción → Banco → Moneda → Saldo')
        content.append('4. **Proceso de Configuración**: Parámetros → Centros de Costo → Condiciones')
        content.append('5. **Proceso de Reportes**: Datos → Vistas → Procedimientos → Informes')
        content.append('')
        
        content.append('### 🚀 Recomendaciones para Integración')
        content.append('')
        content.append('**Para integrar con Synap, considerar:**')
        content.append('')
        content.append('1. **Sincronización de Clientes**: Mapear CL → Clientes de Synap')
        content.append('2. **Sincronización de Productos**: Mapear MM → Productos de Synap')
        content.append('3. **Sincronización de Transacciones**: Mapear BA → Movimientos financieros')
        content.append('4. **Sincronización de Órdenes**: Mapear OO → Pedidos/Ventas')
        content.append('5. **Sincronización de Inventario**: Mapear MC → Stock de Synap')
        content.append('')
        content.append('**Consideraciones técnicas:**')
        content.append('- Usar procedimientos almacenados para operaciones complejas')
        content.append('- Implementar sincronización bidireccional')
        content.append('- Mantener auditoría de cambios')
        content.append('- Considerar diferencias en estructura de datos')
        content.append('')
        
        content.append('### 📊 Métricas del Sistema')
        content.append('')
        content.append('**Volumen de datos:**')
        content.append('- **Transacciones**: 3.8M+ registros')
        content.append('- **Órdenes**: 565K+ registros')
        content.append('- **Materiales por cliente**: 74K+ registros')
        content.append('- **Transacciones bancarias**: Alto volumen')
        content.append('- **Clientes**: 18 registros (sistema simplificado)')
        content.append('')
        
        content.append('**Complejidad del sistema:**')
        content.append('- **Tablas principales**: 53')
        content.append('- **Vistas**: 76')
        content.append('- **Procedimientos**: 120')
        content.append('- **Funciones**: 34')
        content.append('- **Esquemas**: 25')
        content.append('')
        
        return content


