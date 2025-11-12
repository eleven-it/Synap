"""
Comando para entrenar el LogicInterpreterAgent con código real de Administranet
Extrae reglas de negocio de VB6 y PHP y las guarda en la base de datos
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from pathlib import Path
import re

from reports_ai.models import BusinessRule, GlossaryTerm
from reports_ai.tools.vb6_analyzer import VB6AnalyzerTool

User = get_user_model()


class Command(BaseCommand):
    help = 'Train LogicInterpreterAgent by extracting business rules from VB6/PHP code'

    def add_arguments(self, parser):
        parser.add_argument(
            '--module',
            type=str,
            default='all',
            help='Module to analyze (ventas, inventario, general, or all)'
        )
        parser.add_argument(
            '--save',
            action='store_true',
            help='Save extracted rules to database'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=100,
            help='Limit number of rules to extract per module'
        )

    def handle(self, *args, **options):
        module_filter = options['module']
        save_to_db = options['save']
        limit = options['limit']

        self.stdout.write(
            self.style.SUCCESS('╔' + '═' * 68 + '╗')
        )
        self.stdout.write(
            self.style.SUCCESS('║' + ' ' * 10 + 'ENTRENAMIENTO LogicInterpreterAgent' + ' ' * 23 + '║')
        )
        self.stdout.write(
            self.style.SUCCESS('╚' + '═' * 68 + '╝')
        )
        self.stdout.write('')

        # Inicializar analizador
        analyzer = VB6AnalyzerTool()
        
        if not analyzer.source_path.exists():
            self.stdout.write(
                self.style.ERROR(f'❌ Código fuente VB6 no encontrado: {analyzer.source_path}')
            )
            return

        self.stdout.write(f'✅ Código fuente encontrado: {analyzer.source_path}')
        self.stdout.write('')

        # Determinar módulos a analizar
        if module_filter == 'all':
            modules = ['general', 'ventas', 'inventario', 'cobranzas']
        else:
            modules = [module_filter]

        total_rules_extracted = 0
        total_rules_saved = 0
        all_rules = []

        # Analizar cada módulo
        for module_name in modules:
            self.stdout.write('━' * 70)
            self.stdout.write(f'📦 Analizando módulo: {module_name.upper()}')
            self.stdout.write('━' * 70)

            try:
                result = analyzer.extract_business_rules(module_name)
                
                rules = result.get('rules', [])
                count = len(rules)
                
                self.stdout.write(f'✅ Reglas extraídas: {count}')
                
                if count > 0:
                    total_rules_extracted += count
                    
                    # Limitar si es necesario
                    rules_to_process = rules[:limit]
                    
                    # Mostrar muestra
                    self.stdout.write('')
                    self.stdout.write('Muestra de reglas encontradas:')
                    for i, rule in enumerate(rules_to_process[:5], 1):
                        self.stdout.write(
                            f'  {i}. {rule.get("name", "Sin nombre")}'
                        )
                    
                    if count > 5:
                        self.stdout.write(f'  ... y {count - 5} reglas más')
                    
                    all_rules.extend(rules_to_process)
                
                self.stdout.write('')
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ Error analizando {module_name}: {e}')
                )

        # Guardar en base de datos si se solicita
        if save_to_db and all_rules:
            self.stdout.write('━' * 70)
            self.stdout.write('💾 Guardando reglas en base de datos...')
            self.stdout.write('━' * 70)
            self.stdout.write('')

            # Obtener usuario para asignar como creador
            user = User.objects.filter(is_superuser=True).first()
            
            if not user:
                self.stdout.write(
                    self.style.WARNING('⚠️  No se encontró superusuario. Creando reglas sin usuario.')
                )

            with transaction.atomic():
                for rule in all_rules:
                    try:
                        # Verificar si ya existe
                        existing = BusinessRule.objects.filter(
                            name=rule['name'],
                            module=rule['module']
                        ).first()

                        if existing:
                            self.stdout.write(
                                self.style.WARNING(f'  ⏭️  Ya existe: {rule["name"]}')
                            )
                            continue

                        # Crear regla
                        new_rule = BusinessRule.objects.create(
                            name=rule['name'],
                            description=rule['description'],
                            category=rule['category'],
                            module=rule['module'],
                            conditions=rule['conditions'],
                            actions=rule['actions'],
                            source_file=rule.get('source_file', ''),
                            source_line=rule.get('source_line'),
                            is_active=True,
                            created_by=user
                        )

                        total_rules_saved += 1
                        self.stdout.write(
                            self.style.SUCCESS(f'  ✅ Guardada: {new_rule.name}')
                        )

                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f'  ❌ Error guardando {rule.get("name")}: {e}')
                        )

        # Resumen final
        self.stdout.write('')
        self.stdout.write('╔' + '═' * 68 + '╗')
        self.stdout.write('║' + ' ' * 20 + 'RESUMEN DEL ENTRENAMIENTO' + ' ' * 23 + '║')
        self.stdout.write('╚' + '═' * 68 + '╝')
        self.stdout.write('')
        self.stdout.write(f'📊 Módulos analizados: {len(modules)}')
        self.stdout.write(f'📋 Reglas extraídas: {total_rules_extracted}')
        
        if save_to_db:
            self.stdout.write(f'💾 Reglas guardadas en DB: {total_rules_saved}')
            self.stdout.write(f'⏭️  Reglas ya existentes: {total_rules_extracted - total_rules_saved}')
        else:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('⚠️  Modo DRY-RUN: Use --save para guardar en base de datos'))
        
        self.stdout.write('')
        self.stdout.write('✅ ENTRENAMIENTO COMPLETADO')
        self.stdout.write('')
