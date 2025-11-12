"""
Django management command para analizar el schema de MySQL
"""
from django.core.management.base import BaseCommand
from reports_ai.services.schema_analyzer import SchemaAnalyzer
import json


class Command(BaseCommand):
    help = 'Analiza el schema completo de MySQL de AdministraNET'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--table',
            type=str,
            help='Analizar solo una tabla específica'
        )
        parser.add_argument(
            '--relationships',
            action='store_true',
            help='Mostrar relaciones descubiertas'
        )
        parser.add_argument(
            '--export',
            type=str,
            help='Exportar schema a archivo JSON'
        )
        parser.add_argument(
            '--refresh',
            action='store_true',
            help='Forzar refresh del caché'
        )
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🔍 Schema Analyzer para AdministraNET'))
        self.stdout.write('=' * 70)
        self.stdout.write('')
        
        analyzer = SchemaAnalyzer()
        
        # Analizar schema
        self.stdout.write(self.style.WARNING('Analizando schema completo...'))
        schema = analyzer.get_complete_schema(force_refresh=options['refresh'])
        
        self.stdout.write(self.style.SUCCESS(f'✅ Schema analizado exitosamente'))
        self.stdout.write('')
        
        # Estadísticas generales
        metadata = schema.get('metadata', {})
        self.stdout.write(f"📊 Tablas analizadas: {metadata.get('total_tables', 0)}")
        self.stdout.write(f"📋 Columnas totales: {metadata.get('total_columns', 0)}")
        self.stdout.write(f"🔗 Relaciones: {metadata.get('total_fks', 0)}")
        self.stdout.write('')
        
        # Si se especifica tabla
        if options['table']:
            table_name = options['table']
            table_info = schema['tables'].get(table_name)
            
            if not table_info:
                self.stdout.write(self.style.ERROR(f'❌ Tabla "{table_name}" no encontrada'))
                return
            
            self.stdout.write(self.style.SUCCESS(f'📄 Tabla: {table_name}'))
            self.stdout.write('=' * 70)
            self.stdout.write(f"Comentario: {table_info.get('comment', 'N/A')}")
            self.stdout.write(f"Filas estimadas: {table_info.get('estimated_rows', 0):,}")
            self.stdout.write('')
            
            # Primary Key
            pk = table_info.get('primary_key', [])
            if pk:
                self.stdout.write(self.style.SUCCESS(f"🔑 Primary Key: {', '.join(pk)}"))
            
            # Columnas
            self.stdout.write('')
            self.stdout.write('📋 Columnas:')
            self.stdout.write('-' * 70)
            
            for col in table_info['columns'][:10]:  # Mostrar primeras 10
                key_info = []
                if col['key_info']['is_primary']:
                    key_info.append('PK')
                if col['key_info']['is_foreign']:
                    key_info.append('FK')
                if col['key_info']['is_unique']:
                    key_info.append('UNIQUE')
                
                key_str = ', '.join(key_info) if key_info else ''
                nullable = 'NULL' if col['nullable'] else 'NOT NULL'
                auto_inc = ' (AUTO_INCREMENT)' if col['auto_increment'] else ''
                
                self.stdout.write(
                    f"  • {col['name']:30s} {col['type']['raw']:20s} {nullable:10s} {key_str} {auto_inc}"
                )
            
            if len(table_info['columns']) > 10:
                self.stdout.write(f'  ... y {len(table_info["columns"]) - 10} más')
            
            # Relaciones
            self.stdout.write('')
            self.stdout.write('🔗 Relaciones:')
            self.stdout.write('-' * 70)
            
            relationships = analyzer.find_related_tables(table_name)
            if relationships:
                for rel in relationships:
                    if rel['from_table'] == table_name:
                        direction = f"{table_name}.{rel['from_column']} → {rel['to_table']}.{rel['to_column']}"
                    else:
                        direction = f"{rel['from_table']}.{rel['from_column']} → {table_name}"
                    
                    source = rel.get('source', 'unknown')
                    confidence = rel.get('confidence', 0)
                    
                    self.stdout.write(f"  • {direction} [{source}] (confianza: {confidence})")
            else:
                self.stdout.write('  (Sin relaciones descubiertas)')
        
        # Si se piden relaciones
        elif options['relationships']:
            relationships = schema.get('relationships', [])
            
            self.stdout.write('🔗 Relaciones descubiertas:')
            self.stdout.write('=' * 70)
            
            for rel in relationships:
                self.stdout.write(
                    f"{rel['from_table']}.{rel['from_column']} → {rel['to_table']}.{rel['to_column']} "
                    f"[{rel.get('source', 'unknown')}] confianza: {rel.get('confidence', 0)}"
                )
        
        # Exportar a JSON
        if options['export']:
            output_file = options['export']
            
            # Simplificar schema para JSON (remover objetos complejos)
            exportable_schema = {
                'metadata': schema['metadata'],
                'tables': {},
                'relationships': schema['relationships']
            }
            
            for table_name, table_info in schema['tables'].items():
                exportable_schema['tables'][table_name] = {
                    'name': table_info['name'],
                    'columns': [
                        {
                            'name': col['name'],
                            'type': col['type']['base'],
                            'nullable': col['nullable'],
                            'is_primary': col['key_info']['is_primary'],
                            'is_foreign': col['key_info']['is_foreign']
                        }
                        for col in table_info['columns']
                    ],
                    'primary_key': table_info['primary_key'],
                    'estimated_rows': table_info['estimated_rows'],
                    'comment': table_info['comment']
                }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(exportable_schema, f, indent=2, ensure_ascii=False)
            
            self.stdout.write(self.style.SUCCESS(f'💾 Schema exportado a: {output_file}'))
        
        # Resumen final
        if not options['table'] and not options['relationships'] and not options['export']:
            self.stdout.write('')
            self.stdout.write('📋 Primeras 10 tablas:')
            self.stdout.write('-' * 70)
            
            for i, (table_name, table_info) in enumerate(list(schema['tables'].items())[:10]):
                col_count = len(table_info['columns'])
                pk = ', '.join(table_info['primary_key'])
                self.stdout.write(
                    f"  {i+1:2d}. {table_name:30s} {col_count:3d} columnas  PK: {pk}"
                )
            
            self.stdout.write('')
            self.stdout.write('💡 Usa --help para ver más opciones')
            self.stdout.write('   Ejemplo: python manage.py analyze_schema --table comp_ped')

