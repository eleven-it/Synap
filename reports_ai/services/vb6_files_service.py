"""
Servicio para obtener listados de archivos VB6 disponibles
"""
from pathlib import Path
from typing import List, Dict
import logging
import os

logger = logging.getLogger(__name__)


class VB6FilesService:
    """
    Servicio para listar archivos VB6 disponibles en el proyecto
    """
    
    def __init__(self):
        # Detectar ruta
        if os.path.exists('/app/administraNET_Limpio'):
            self.vb6_root = Path('/app/administraNET_Limpio')
        else:
            self.vb6_root = Path('/Users/sebastian/Documents/Administranet/Proyectos/Synap/administraNET_Limpio')
    
    def get_vb6_forms(self) -> List[str]:
        """
        Obtiene lista de formularios VB6 (.frm)
        
        Returns:
            Lista de nombres de formularios ordenados
        """
        forms = []
        
        try:
            # Buscar en Formularios
            formularios_dir = self.vb6_root / 'Formularios'
            
            if formularios_dir.exists():
                for frm_file in formularios_dir.glob('*.frm'):
                    forms.append(frm_file.name)
            
            # Buscar recursivamente otros .frm
            for frm_file in self.vb6_root.rglob('*.frm'):
                if frm_file.name not in forms:
                    forms.append(frm_file.name)
        
        except Exception as e:
            logger.error(f"Error obteniendo formularios VB6: {e}")
        
        return sorted(forms)
    
    def get_vb6_modules(self) -> List[str]:
        """
        Obtiene lista de módulos VB6 (.bas, .cls)
        
        Returns:
            Lista de nombres de módulos ordenados
        """
        modules = []
        
        try:
            # Buscar en Modulos
            modulos_dir = self.vb6_root / 'Modulos'
            
            if modulos_dir.exists():
                for mod_file in modulos_dir.glob('*.bas'):
                    modules.append(mod_file.name)
                
                for cls_file in modulos_dir.glob('*.cls'):
                    modules.append(cls_file.name)
            
            # Buscar en Modulos de clase
            modulos_clase_dir = self.vb6_root / 'Modulos de clase'
            
            if modulos_clase_dir.exists():
                for cls_file in modulos_clase_dir.glob('*.cls'):
                    if cls_file.name not in modules:
                        modules.append(cls_file.name)
        
        except Exception as e:
            logger.error(f"Error obteniendo módulos VB6: {e}")
        
        return sorted(modules)
    
    def get_forms_by_category(self) -> Dict[str, List[str]]:
        """
        Obtiene formularios agrupados por categoría inferida
        
        Returns:
            Dict con categorías y sus formularios
        """
        categorized = {
            'Ventas': [],
            'Compras': [],
            'Stock': [],
            'Clientes': [],
            'Cobranzas': [],
            'Configuración': [],
            'General': []
        }
        
        all_forms = self.get_vb6_forms()
        
        for form in all_forms:
            name_lower = form.lower()
            
            # Categorizar por nombre
            if any(keyword in name_lower for keyword in ['pedido', 'presupuesto', 'factura', 'venta', 'remito', 'notacred', 'notadeb']):
                categorized['Ventas'].append(form)
            elif any(keyword in name_lower for keyword in ['proveedor', 'compra', 'orden']):
                categorized['Compras'].append(form)
            elif any(keyword in name_lower for keyword in ['stock', 'deposito', 'inventario', 'articulo', 'movstock']):
                categorized['Stock'].append(form)
            elif any(keyword in name_lower for keyword in ['cliente', 'carga_cliente']):
                categorized['Clientes'].append(form)
            elif any(keyword in name_lower for keyword in ['cobro', 'pago', 'recibo', 'cobranza', 'cheque']):
                categorized['Cobranzas'].append(form)
            elif any(keyword in name_lower for keyword in ['configuracion', 'parametro', 'empresa', 'sucursal', 'usuario', 'puesto']):
                categorized['Configuración'].append(form)
            else:
                categorized['General'].append(form)
        
        # Filtrar categorías vacías
        return {k: v for k, v in categorized.items() if v}
    
    def get_common_modules(self) -> List[str]:
        """
        Obtiene lista de módulos funcionales comunes
        
        Returns:
            Lista predefinida de módulos
        """
        return [
            'Ventas',
            'Compras',
            'Stock',
            'Clientes',
            'Proveedores',
            'Cobranzas',
            'Pagos',
            'Facturación',
            'Contabilidad',
            'CRM',
            'Logística',
            'Configuración',
            'Administración',
            'Reportes'
        ]
    
    def get_common_entities(self) -> List[str]:
        """
        Obtiene lista de entidades comunes del dominio
        
        Returns:
            Lista predefinida de entidades
        """
        return [
            'Pedido',
            'Presupuesto',
            'Factura',
            'Remito',
            'NotaCredito',
            'NotaDebito',
            'Cliente',
            'Proveedor',
            'Articulo',
            'Stock',
            'Deposito',
            'Vendedor',
            'Sucursal',
            'Transporte',
            'Ruta',
            'CondicionVenta',
            'FormaPago',
            'Impuesto',
            'Precio',
            'Descuento',
            'Cobranza',
            'Pago',
            'Cheque',
            'Recibo'
        ]

