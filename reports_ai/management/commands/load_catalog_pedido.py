"""
Comando para cargar el catálogo inicial con el procedimiento "Crear Pedido"
"""
from django.core.management.base import BaseCommand
from reports_ai.models import FunctionalCatalog


class Command(BaseCommand):
    help = 'Carga el catálogo funcional inicial con el procedimiento "Crear Pedido"'
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n🚀 Cargando Catálogo Funcional Inicial\n'))
        
        # Crear o actualizar entrada de "Crear Pedido"
        catalog_entry, created = FunctionalCatalog.objects.update_or_create(
            module='Ventas',
            procedure='Crear pedido',
            defaults={
                'description': (
                    'Procedimiento completo para crear y guardar un nuevo pedido de cliente. '
                    'Incluye validaciones de crédito, límites, generación de numeración, '
                    'guardado de cabecera y detalle, actualización de stock reservado, '
                    'y relaciones con presupuestos.'
                ),
                
                # Archivos fuente
                'vb6_forms': 'Pedido.frm',
                'vb6_modules': '',
                'php_scripts': '',
                
                # Modelo de negocio
                'entities': 'Pedido, Cliente, Articulo, DatosEntrega, Deposito, Transporte, Ruta',
                'candidate_tables': 'comp_ped, cuerpostockpe, cliente, articulo, cliente_datos_adicionales, stock_deposito, percep_cli, pedido_presupuesto, ped_pd',
                'master_table': 'comp_ped',
                'detail_table': 'cuerpostockpe',
                'key_fields': 'CodigoMovimiento, Codigo, IDArt, Cantidad, Total, Fecha, Estado, PrecioVentaxU, Pordesc',
                
                # Lógica
                'relevant_events': 'Guardar(), BeginTrans, CommitTrans',
                'business_rules': (
                    'El pedido debe tener al menos un artículo. '
                    'El importe total debe ser mayor a 0. '
                    'El cliente debe tener crédito disponible suficiente (si es Cta Cte). '
                    'Los descuentos no pueden superar el límite configurado por puesto. '
                    'El stock reservado se incrementa al crear el pedido. '
                    'Si se crea desde un presupuesto, éste cambia a estado "En Pedido". '
                    'Todas las operaciones son transaccionales.'
                ),
                'validations': (
                    'Vendedor seleccionado (si obligatorio), '
                    'Importe > 0, '
                    'Número de comprobante válido (si talonario), '
                    'Condición de venta permitida, '
                    'Límite de descuento no superado, '
                    'Crédito del cliente no excedido, '
                    'Límite de días no superado'
                ),
                'dependencies': 'Presupuesto, PedidoDelivery, Numeración (talonarios), Stock por Depósito',
                
                # Relaciones
                'table_relationships': {
                    'comp_ped.CodigoMovimiento': 'cuerpostockpe.CodigoMovimiento',
                    'comp_ped.Codigo': 'cliente.Codigo',
                    'cuerpostockpe.IDArt': 'articulo.IDArt',
                    'cuerpostockpe.CodDeposito': 'deposito.id_deposito',
                    'cliente_datos_adicionales.CodigoMovimiento': 'comp_ped.CodigoMovimiento',
                    'percep_cli.codigo_movimiento': 'comp_ped.CodigoMovimiento',
                    'pedido_presupuesto.codigo_movimiento_ped': 'comp_ped.CodigoMovimiento',
                    'stock_deposito.id_articulo': 'articulo.IDArt'
                },
                
                # Operaciones
                'insert_tables': 'comp_ped, cliente_datos_adicionales, cuerpostockpe, percep_cli, pedido_presupuesto, ped_pd',
                'update_tables': 'codmov, talonarios, stock_deposito, presupuesto, cuerpostockpe',
                
                # Calidad
                'confidence': 0.94,
                'priority': 10,
                'is_active': True,
                'notes': (
                    'Procedimiento extraído del análisis de Pedido.frm (12,162 líneas). '
                    'Incluye manejo de transacciones, validaciones de crédito, '
                    'actualización de stock reservado, y relaciones con presupuestos '
                    'y pedidos delivery. Última revisión: 27/10/2025'
                )
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'✅ Creada nueva entrada: {catalog_entry}'))
        else:
            self.stdout.write(self.style.SUCCESS(f'✅ Actualizada entrada existente: {catalog_entry}'))
        
        # Mostrar resumen
        self.stdout.write('\n' + '='*70)
        self.stdout.write(self.style.SUCCESS('📊 RESUMEN DEL CATÁLOGO'))
        self.stdout.write('='*70 + '\n')
        
        self.stdout.write(f'🗂️  Módulo: {catalog_entry.module}')
        self.stdout.write(f'📋 Procedimiento: {catalog_entry.procedure}')
        self.stdout.write(f'📂 Formularios VB6: {catalog_entry.vb6_forms}')
        self.stdout.write(f'🏷️  Entidades: {len(catalog_entry.get_entities_list())} ({", ".join(catalog_entry.get_entities_list()[:5])}...)')
        self.stdout.write(f'🗄️  Tablas: {len(catalog_entry.get_tables_list())} ({", ".join(catalog_entry.get_tables_list()[:5])}...)')
        self.stdout.write(f'🔑 Campos clave: {len(catalog_entry.get_fields_list())}')
        self.stdout.write(f'🔗 Relaciones: {len(catalog_entry.table_relationships)} relaciones definidas')
        self.stdout.write(f'📈 Confianza: {catalog_entry.confidence}')
        self.stdout.write(f'⭐ Prioridad: {catalog_entry.priority}/10')
        
        self.stdout.write('\n' + '='*70)
        self.stdout.write(self.style.SUCCESS('✅ Catálogo cargado correctamente'))
        self.stdout.write('='*70 + '\n')
        
        # Mostrar próximos pasos
        self.stdout.write('\n🎯 Próximos pasos:')
        self.stdout.write('1. Entrenar Logic Interpreter en modo GUIADO')
        self.stdout.write('   → Analizará solo Pedido.frm')
        self.stdout.write('   → Generará Business Rules con contexto rico')
        self.stdout.write('   → Tiempo estimado: 2-3 minutos')
        self.stdout.write('\n2. Probar consulta en el chat:')
        self.stdout.write('   → "Cómo crear un pedido"')
        self.stdout.write('   → Debería responder con el procedimiento detallado')
        self.stdout.write('\n')

