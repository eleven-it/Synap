"""
Comando para importar reglas de negocio desde código VB6/PHP
"""
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import transaction
import os
import re
from pathlib import Path

from reports_ai.models import BusinessRule
from reports_ai.services.code_analysis_service import CodeAnalysisService

User = get_user_model()


class Command(BaseCommand):
    help = 'Import business rules from VB6/PHP source code'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source-dir',
            type=str,
            default='/app/administraNET_Limpio',
            help='Source directory containing VB6/PHP files'
        )
        parser.add_argument(
            '--module-filter',
            type=str,
            help='Filter by specific module (e.g., ventas, inventario)'
        )
        parser.add_argument(
            '--file-patterns',
            type=str,
            default='*.frm,*.bas,*.cls,*.php',
            help='File patterns to analyze (comma-separated)'
        )
        parser.add_argument(
            '--auto-activate',
            action='store_true',
            help='Auto-activate imported rules'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be imported without actually importing'
        )
        parser.add_argument(
            '--user',
            type=str,
            help='Username to assign as creator of imported rules'
        )

    def handle(self, *args, **options):
        source_dir = options['source_dir']
        module_filter = options.get('module_filter')
        file_patterns = options['file_patterns'].split(',')
        auto_activate = options['auto_activate']
        dry_run = options['dry_run']
        username = options.get('user')

        # Validar directorio fuente
        if not os.path.exists(source_dir):
            raise CommandError(f'Source directory does not exist: {source_dir}')

        # Obtener usuario
        user = None
        if username:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                raise CommandError(f'User not found: {username}')
        else:
            # Usar el primer superusuario
            user = User.objects.filter(is_superuser=True).first()
            if not user:
                raise CommandError('No superuser found. Please specify --user or create a superuser.')

        self.stdout.write(
            self.style.SUCCESS(f'Starting import from: {source_dir}')
        )
        self.stdout.write(f'User: {user.username}')
        self.stdout.write(f'File patterns: {file_patterns}')
        self.stdout.write(f'Auto-activate: {auto_activate}')
        self.stdout.write(f'Dry run: {dry_run}')

        try:
            # Usar el servicio de análisis de código
            analyzer = CodeAnalysisService()
            results = analyzer.analyze_directory(
                source_dir=source_dir,
                module_filter=module_filter,
                file_patterns=file_patterns
            )

            self.stdout.write(
                self.style.SUCCESS(f'Found {len(results)} potential business rules')
            )

            if dry_run:
                self.stdout.write('\n' + '='*60)
                self.stdout.write('DRY RUN - Rules that would be imported:')
                self.stdout.write('='*60)
                
                for i, result in enumerate(results, 1):
                    self.stdout.write(f'\n{i}. {result["name"]}')
                    self.stdout.write(f'   Category: {result["category"]}')
                    self.stdout.write(f'   Module: {result["module"]}')
                    self.stdout.write(f'   File: {result["source_file"]}')
                    self.stdout.write(f'   Line: {result["source_line"]}')
                    self.stdout.write(f'   Description: {result["description"][:100]}...')
                
                self.stdout.write(f'\nTotal: {len(results)} rules would be imported')
                return

            # Importar reglas
            imported_count = 0
            skipped_count = 0

            with transaction.atomic():
                for result in results:
                    try:
                        # Verificar si ya existe una regla similar
                        existing_rule = BusinessRule.objects.filter(
                            name=result['name'],
                            module=result['module']
                        ).first()

                        if existing_rule:
                            self.stdout.write(
                                self.style.WARNING(f'Skipping existing rule: {result["name"]}')
                            )
                            skipped_count += 1
                            continue

                        # Crear nueva regla
                        rule = BusinessRule.objects.create(
                            name=result['name'],
                            description=result['description'],
                            category=result['category'],
                            module=result['module'],
                            priority=result.get('priority', 'medium'),
                            conditions=result['conditions'],
                            actions=result['actions'],
                            source_file=result['source_file'],
                            source_line=result['source_line'],
                            is_active=auto_activate,
                            created_by=user
                        )

                        imported_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(f'Imported: {rule.name}')
                        )

                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f'Error importing {result["name"]}: {str(e)}')
                        )
                        continue

            # Resumen final
            self.stdout.write('\n' + '='*60)
            self.stdout.write('IMPORT SUMMARY')
            self.stdout.write('='*60)
            self.stdout.write(f'Total found: {len(results)}')
            self.stdout.write(f'Imported: {imported_count}')
            self.stdout.write(f'Skipped: {skipped_count}')
            self.stdout.write(f'Errors: {len(results) - imported_count - skipped_count}')

            if imported_count > 0:
                self.stdout.write(
                    self.style.SUCCESS(f'\nSuccessfully imported {imported_count} business rules!')
                )
            else:
                self.stdout.write(
                    self.style.WARNING('\nNo new rules were imported.')
                )

        except Exception as e:
            raise CommandError(f'Import failed: {str(e)}')

    def _extract_business_rules_from_file(self, file_path, module_filter=None):
        """
        Extrae reglas de negocio de un archivo específico
        """
        rules = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = content.split('\n')
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error reading file {file_path}: {str(e)}')
            )
            return rules

        # Patrones para detectar reglas de negocio
        business_patterns = [
            r'if\s+.*stock.*then',  # Reglas de stock
            r'if\s+.*precio.*then',  # Reglas de precio
            r'if\s+.*cliente.*then',  # Reglas de cliente
            r'if\s+.*venta.*then',  # Reglas de venta
            r'validar.*:',  # Funciones de validación
            r'calcular.*:',  # Funciones de cálculo
        ]

        for i, line in enumerate(lines, 1):
            line_lower = line.lower().strip()
            
            # Buscar patrones de reglas de negocio
            for pattern in business_patterns:
                if re.search(pattern, line_lower):
                    rule = self._create_rule_from_line(
                        line, i, file_path, module_filter
                    )
                    if rule:
                        rules.append(rule)
                    break

        return rules

    def _create_rule_from_line(self, line, line_number, file_path, module_filter):
        """
        Crea una regla de negocio a partir de una línea de código
        """
        # Determinar módulo basado en el archivo
        module = self._determine_module_from_file(file_path)
        
        if module_filter and module_filter.lower() not in module.lower():
            return None

        # Extraer nombre de la regla
        rule_name = self._extract_rule_name(line)
        
        # Categorizar la regla
        category = self._categorize_rule(line)
        
        # Crear descripción
        description = f"Business rule extracted from {os.path.basename(file_path)} at line {line_number}"
        
        return {
            'name': rule_name,
            'description': description,
            'category': category,
            'module': module,
            'priority': 'medium',
            'conditions': line.strip(),
            'actions': 'Rule execution based on conditions',
            'source_file': file_path,
            'source_line': line_number
        }

    def _determine_module_from_file(self, file_path):
        """
        Determina el módulo basado en la ruta del archivo
        """
        path_lower = file_path.lower()
        
        if 'venta' in path_lower or 'sale' in path_lower:
            return 'ventas'
        elif 'inventario' in path_lower or 'inventory' in path_lower:
            return 'inventario'
        elif 'cliente' in path_lower or 'customer' in path_lower:
            return 'clientes'
        elif 'cobranza' in path_lower or 'collection' in path_lower:
            return 'cobranzas'
        elif 'finanza' in path_lower or 'finance' in path_lower:
            return 'finanzas'
        else:
            return 'general'

    def _extract_rule_name(self, line):
        """
        Extrae el nombre de la regla de la línea de código
        """
        # Limpiar la línea
        clean_line = re.sub(r'^\s*if\s+', '', line.strip())
        clean_line = re.sub(r'\s+then.*$', '', clean_line)
        clean_line = re.sub(r'^\s*validar\s+', 'Validar ', clean_line)
        clean_line = re.sub(r'^\s*calcular\s+', 'Calcular ', clean_line)
        
        # Limitar longitud
        if len(clean_line) > 100:
            clean_line = clean_line[:97] + '...'
        
        return clean_line or f"Rule from line {line}"

    def _categorize_rule(self, line):
        """
        Categoriza la regla basada en su contenido
        """
        line_lower = line.lower()
        
        if 'validar' in line_lower or 'valid' in line_lower:
            return 'validation'
        elif 'calcular' in line_lower or 'calcul' in line_lower:
            return 'calculation'
        elif 'stock' in line_lower or 'inventario' in line_lower:
            return 'business'
        elif 'precio' in line_lower or 'price' in line_lower:
            return 'business'
        elif 'cliente' in line_lower or 'customer' in line_lower:
            return 'business'
        else:
            return 'business'
