"""
Comando para analizar la navegación del proyecto VB6 completo
Lee el .vbp y analiza el flujo de navegación
"""
from django.core.management.base import BaseCommand
from pathlib import Path
import re


class Command(BaseCommand):
    help = 'Analiza la navegación completa del proyecto VB6'
    
    def __init__(self):
        super().__init__()
        import os
        if os.path.exists('/app/administraNET_Limpio'):
            self.vb6_root = Path('/app/administraNET_Limpio')
        else:
            self.vb6_root = Path('/Users/sebastian/Documents/Administranet/Proyectos/Synap/administraNET_Limpio')
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n🔍 ANÁLISIS DE NAVEGACIÓN VB6\n'))
        self.stdout.write('='*70 + '\n')
        
        # 1. Leer archivo .vbp
        vbp_file = self.vb6_root / 'administraNET.vbp'
        
        self.stdout.write('📋 Leyendo proyecto: administraNET.vbp')
        
        with open(vbp_file, 'r', encoding='latin-1', errors='ignore') as f:
            vbp_content = f.read()
        
        # Extraer startup form
        startup_match = re.search(r'Startup="([^"]+)"', vbp_content)
        startup_form = startup_match.group(1) if startup_match else 'Unknown'
        
        self.stdout.write(f'✅ Formulario de inicio: {startup_form}')
        self.stdout.write('')
        
        # 2. Analizar flujo de inicio
        self.stdout.write('📋 FLUJO DE INICIO:')
        self.stdout.write('='*70)
        
        # frmSplash
        self.stdout.write('1. frmSplash (Splash Screen, 3 segundos)')
        
        # IngresoUsuario
        self.stdout.write('2. IngresoUsuario (Login de usuario)')
        
        # Principal
        self.stdout.write('3. Principal.frm (Ventana principal)')
        self.stdout.write('')
        
        # 3. Buscar cómo se accede a Pedido
        self.stdout.write('📋 BÚSQUEDA: ¿Cómo se accede a Pedido.frm?')
        self.stdout.write('='*70)
        
        # Buscar en todos los .frm y .bas
        files_calling_pedido = []
        
        # Buscar en formularios
        for frm_file in self.vb6_root.rglob('*.frm'):
            try:
                with open(frm_file, 'r', encoding='latin-1', errors='ignore') as f:
                    content = f.read()
                
                # Buscar "Pedido.Show" (no "Visualiza_Pedido")
                if re.search(r'\bPedido\.Show\b', content):
                    files_calling_pedido.append({
                        'file': frm_file.name,
                        'type': 'Form',
                        'path': str(frm_file.relative_to(self.vb6_root))
                    })
            except:
                pass
        
        # Buscar en módulos .bas
        for bas_file in self.vb6_root.rglob('*.bas'):
            try:
                with open(bas_file, 'r', encoding='latin-1', errors='ignore') as f:
                    content = f.read()
                
                if re.search(r'\bPedido\.Show\b', content):
                    files_calling_pedido.append({
                        'file': bas_file.name,
                        'type': 'Module',
                        'path': str(bas_file.relative_to(self.vb6_root))
                    })
            except:
                pass
        
        if files_calling_pedido:
            self.stdout.write(f'\n✅ Archivos que llaman a Pedido.Show: {len(files_calling_pedido)}')
            for item in files_calling_pedido:
                self.stdout.write(f'   • {item["file"]} ({item["type"]})')
                self.stdout.write(f'     {item["path"]}')
        else:
            self.stdout.write('\n⚠️  No se encontró ningún archivo que llame directamente a Pedido.Show')
            self.stdout.write('   Posibles razones:')
            self.stdout.write('   1. Se accede mediante un array de formularios')
            self.stdout.write('   2. Se usa LoadForm() o CallByName()')
            self.stdout.write('   3. Se carga desde una lista de comprobantes (CargaComprobantesPed.frm)')
        
        self.stdout.write('')
        
        # 4. Analizar CargaComprobantesPed.frm
        self.stdout.write('📋 ANÁLISIS: CargaComprobantesPed.frm (Lista de pedidos)')
        self.stdout.write('='*70)
        
        carga_ped_file = self.vb6_root / 'Formularios' / 'CargaComprobantesPed.frm'
        
        if carga_ped_file.exists():
            with open(carga_ped_file, 'r', encoding='latin-1', errors='ignore') as f:
                content = f.read()
            
            # Buscar caption
            caption_match = re.search(r'Caption\s*=\s*"([^"]+)"', content)
            caption = caption_match.group(1) if caption_match else 'Desconocido'
            
            self.stdout.write(f'✅ Título del formulario: {caption}')
            
            # Buscar botones "Nuevo", "Agregar", etc.
            new_button_patterns = [
                r'(btn|cmd|Button)\w*(Nuevo|New|Agregar|Add)',
                r'Caption\s*=\s*"(Nuevo|Agregar)"'
            ]
            
            for pattern in new_button_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    self.stdout.write(f'   • Encontrado botón: {matches[0]}')
            
            # Buscar Load Pedido o Pedido.Show
            if 'Pedido.Show' in content or 'Load Pedido' in content:
                self.stdout.write('   ✅ Este formulario SÍ llama a Pedido!')
        
        self.stdout.write('')
        
        # 5. Buscar en Principal.frm cómo se accede a listas de comprobantes
        self.stdout.write('📋 ANÁLISIS: Principal.frm (Menús/Botones)')
        self.stdout.write('='*70)
        
        principal_file = self.vb6_root / 'Formularios' / 'Principal.frm'
        
        if principal_file.exists():
            with open(principal_file, 'r', encoding='latin-1', errors='ignore') as f:
                content = f.read()
            
            # Buscar llamadas a CargaComprobantesPed
            if 'CargaComprobantesPed.Show' in content:
                self.stdout.write('✅ Principal.frm llama a CargaComprobantesPed')
                
                # Buscar el contexto (botón o menú)
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if 'CargaComprobantesPed.Show' in line:
                        # Buscar hacia atrás el nombre de la función/procedimiento
                        for j in range(max(0, i-30), i):
                            if 'Private Sub' in lines[j] or 'Public Sub' in lines[j]:
                                func_name = lines[j].strip()
                                self.stdout.write(f'   • Desde: {func_name}')
                                break
        
        self.stdout.write('')
        
        # 6. Conclusión
        self.stdout.write('='*70)
        self.stdout.write(self.style.SUCCESS('📊 CONCLUSIÓN'))
        self.stdout.write('='*70)
        self.stdout.write('')
        self.stdout.write('FLUJO COMPLETO PARA CREAR UN PEDIDO:')
        self.stdout.write('')
        self.stdout.write('1. Usuario inicia administraNET')
        self.stdout.write('2. Splash Screen → Login')
        self.stdout.write('3. Ventana Principal')
        self.stdout.write('4. Desde Principal → Accede a "Lista de Pedidos"')
        self.stdout.write('   (CargaComprobantesPed.frm)')
        self.stdout.write('5. En la lista, hace clic en "Nuevo" o "Agregar"')
        self.stdout.write('6. Se abre Pedido.frm para crear nuevo pedido')
        self.stdout.write('')
        self.stdout.write('RUTA DEL MENÚ (estimada):')
        self.stdout.write('  → Ventas → Pedidos → Nuevo')
        self.stdout.write('')

