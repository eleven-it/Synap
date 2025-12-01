from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List
import logging

from django.conf import settings
from django.utils import timezone
from django.http import HttpResponse

from .query_runner import QueryRunnerService
from ..models import ReportDefinition

logger = logging.getLogger(__name__)


@dataclass
class ExportResult:
    """Resultado estandarizado de exportaciones."""

    path: str
    created_at: str
    expires_at: str | None = None
    filename: str | None = None


class ExportService:
    """Servicio para generar exportaciones PDF/XLSX."""

    def __init__(self, user):
        self.user = user

    def export(self, report_slug: str, payload: Dict, export_type: str) -> ExportResult:
        """
        Exporta un reporte a Excel.
        
        Args:
            report_slug: Slug del reporte a exportar
            payload: Payload con filtros y configuración
            export_type: Tipo de exportación ('xlsx' o 'xls')
        
        Returns:
            ExportResult con la ruta del archivo generado
        """
        if export_type not in ['xlsx', 'xls']:
            raise ValueError(f"Tipo de exportación no soportado: {export_type}")
        
        # Obtener la definición del reporte
        try:
            report = ReportDefinition.objects.get(slug=report_slug, is_active=True)
        except ReportDefinition.DoesNotExist:
            raise ValueError(f"Reporte no encontrado: {report_slug}")
        
        # Ejecutar la consulta para obtener los datos
        query_service = QueryRunnerService(self.user)
        query_result = query_service.run(report, payload)
        
        # Generar el archivo Excel
        export_dir = Path(settings.MEDIA_ROOT) / "reports" / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)

        timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{report_slug}_{timestamp}.xlsx"
        file_path = export_dir / filename
        
        # Generar Excel usando openpyxl
        self._generate_excel(file_path, report, query_result, payload)

        return ExportResult(
            path=str(file_path.relative_to(settings.MEDIA_ROOT)),
            created_at=timezone.now().isoformat(),
            expires_at=None,
            filename=filename,
        )
    
    def _generate_excel(self, file_path: Path, report: ReportDefinition, query_result, payload: Dict):
        """
        Genera un archivo Excel con los datos del reporte.
        
        Args:
            file_path: Ruta donde guardar el archivo
            report: Definición del reporte
            query_result: Resultado de la consulta (QueryResult)
            payload: Payload con filtros
        """
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter
        
        # Crear workbook
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = report.name[:31]  # Excel limita a 31 caracteres
        
        # Estilos
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF", size=11)
        title_font = Font(bold=True, size=14, color="1E40AF")
        border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        row = 1
        
        # 1. Título del reporte
        ws.merge_cells(f'A{row}:D{row}')
        cell = ws[f'A{row}']
        cell.value = report.name
        cell.font = title_font
        cell.alignment = Alignment(horizontal='left', vertical='center')
        row += 1
        
        # 2. Información del período (desde notes)
        if query_result.notes:
            ws.merge_cells(f'A{row}:D{row}')
            cell = ws[f'A{row}']
            cell.value = query_result.notes[0] if query_result.notes else ""
            cell.font = Font(size=10, italic=True)
            cell.alignment = Alignment(horizontal='left', vertical='center')
            row += 1
        
        row += 1  # Espacio
        
        # 3. Headers y datos según el tipo de reporte
        if report.slug == "sales_summary":
            # Resumen de Ventas: mostrar como tabla de totales
            headers = ["Concepto", "Valor"]
            ws.append(headers)
            
            # Aplicar estilo a headers
            for col_num, header in enumerate(headers, 1):
                cell = ws.cell(row=row, column=col_num)
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal='center', vertical='center')
                cell.border = border
            
            row += 1
            
            # Datos del resumen
            if query_result.data and len(query_result.data) > 0:
                data_row = query_result.data[0]
                summary_data = [
                    ["Ventas Netas", data_row.get("ventas_netas", 0)],
                    ["Remitos no Facturados", data_row.get("remitos_no_facturados", 0)],
                    ["Pedidos Pendientes", data_row.get("pedidos_pendientes", 0)],
                    ["Total Consolidado", data_row.get("total_consolidado", 0)],
                ]
                
                for concept, value in summary_data:
                    ws.append([concept, value])
                    # Formatear valor como moneda
                    value_cell = ws.cell(row=row, column=2)
                    value_cell.number_format = '"$"#,##0.00'
                    value_cell.alignment = Alignment(horizontal='right', vertical='center')
                    value_cell.border = border
                    # Aplicar borde a la celda de concepto
                    concept_cell = ws.cell(row=row, column=1)
                    concept_cell.border = border
                    concept_cell.alignment = Alignment(horizontal='left', vertical='center')
                    row += 1
        else:
            # Otros reportes: mostrar datos en tabla
            if not query_result.data:
                ws.append(["Sin datos disponibles"])
                row += 1
            else:
                # Obtener headers desde las claves del primer registro
                headers = list(query_result.data[0].keys())
                
                # Para "uninvoiced_remitos", excluir id_sucursal e id_punto_venta
                if report.slug == "uninvoiced_remitos":
                    headers = [h for h in headers if h not in ["id_sucursal", "id_punto_venta"]]
                
                # Traducir headers al español si es necesario
                header_translations = {
                    "mes": "Mes",
                    "mes_formato": "Mes (Formato)",
                    "id_sucursal": "ID Sucursal",
                    "nombre_sucursal": "Sucursal",
                    "id_punto_venta": "ID Punto de Venta",
                    "nro_punto_venta": "Punto de Venta",
                    "ventas_brutas": "Ventas Brutas",
                    "notas_credito": "Notas de Crédito",
                    "ventas_netas": "Ventas Netas",
                    "fecha": "Fecha",
                    "nro_comprobante": "N° Comprobante",
                    "tipo_comprobante": "Tipo Comprobante",
                    "subtotal_desc": "Subtotal",
                    "estado": "Estado",
                    "sucursal": "Sucursal",
                    "punto_venta": "Punto de Venta",
                }
                
                translated_headers = [header_translations.get(h, h.replace("_", " ").title()) for h in headers]
                
                # Escribir headers
                ws.append(translated_headers)
                
                # Aplicar estilo a headers
                for col_num, header in enumerate(translated_headers, 1):
                    cell = ws.cell(row=row, column=col_num)
                    cell.fill = header_fill
                    cell.font = header_font
                    cell.alignment = Alignment(horizontal='center', vertical='center')
                    cell.border = border
                
                row += 1
                
                # Escribir datos
                for data_row in query_result.data:
                    row_values = []
                    # Convertir valores numéricos a float para asegurar formato correcto
                    for header in headers:
                        value = data_row.get(header, "")
                        # Si es un campo numérico, convertir a float
                        if header in ["ventas_brutas", "notas_credito", "ventas_netas", "subtotal_desc"]:
                            try:
                                if value == "" or value is None:
                                    row_values.append(0.0)
                                else:
                                    row_values.append(float(value))
                            except (ValueError, TypeError):
                                row_values.append(0.0)
                        else:
                            row_values.append(value)
                    
                    ws.append(row_values)
                    
                    # Aplicar formato a valores numéricos y bordes
                    for col_num, (header, value) in enumerate(zip(headers, row_values), 1):
                        cell = ws.cell(row=row, column=col_num)
                        cell.border = border
                        
                        # Formatear valores numéricos como moneda
                        if header in ["ventas_brutas", "notas_credito", "ventas_netas", "subtotal_desc"]:
                            if isinstance(value, (int, float)):
                                cell.number_format = '"$"#,##0.00'
                                cell.alignment = Alignment(horizontal='right', vertical='center')
                            else:
                                cell.alignment = Alignment(horizontal='left', vertical='center')
                        else:
                            cell.alignment = Alignment(horizontal='left', vertical='center')
                    
                    row += 1
                
                # Agregar fila de totales si existe
                if query_result.totals:
                    row += 1
                    
                    # Mapeo de headers a nombres de totales en query_result.totals
                    # Algunos reportes usan "total_<campo>" en lugar de solo "<campo>"
                    header_to_total_map = {
                        "subtotal_desc": "total_subtotal_desc",
                        "ventas_netas": "total_ventas_netas",
                        "ventas_brutas": "total_ventas_brutas",
                        "notas_credito": "total_notas_credito",
                    }
                    
                    # Construir la fila de totales con los valores correctos
                    total_row = ["TOTALES"]
                    for header in headers[1:]:  # Saltar el primer header (ya pusimos "TOTALES")
                        # Buscar el total usando el nombre del header o el mapeo
                        total_key = header_to_total_map.get(header, header)
                        if total_key in query_result.totals:
                            total_value = query_result.totals[total_key]
                            if isinstance(total_value, (int, float)):
                                total_row.append(total_value)
                            else:
                                total_row.append("")
                        # Si no se encuentra con el mapeo, intentar con el nombre original
                        elif header in query_result.totals:
                            total_value = query_result.totals[header]
                            if isinstance(total_value, (int, float)):
                                total_row.append(total_value)
                            else:
                                total_row.append("")
                        else:
                            total_row.append("")
                    
                    # Escribir la fila completa
                    ws.append(total_row)
                    
                    # Aplicar estilo solo a las celdas de la fila de totales que tienen contenido
                    # Limitar el rango a solo las columnas que realmente existen en la fila
                    for col_num in range(1, len(total_row) + 1):
                        if col_num <= len(total_row):
                            cell = ws.cell(row=row, column=col_num)
                            cell.font = Font(bold=True)
                            cell.fill = PatternFill(start_color="D3D3D3", end_color="D3D3D3", fill_type="solid")
                            cell.border = border
                            
                            # Aplicar formato según el tipo de contenido
                            if col_num == 1:
                                # Primera columna: "TOTALES"
                                cell.alignment = Alignment(horizontal='center', vertical='center')
                            else:
                                # Otras columnas: valores numéricos o vacíos
                                header = headers[col_num - 1]
                                total_key = header_to_total_map.get(header, header)
                                if total_key in query_result.totals or header in query_result.totals:
                                    total_value = query_result.totals.get(total_key) or query_result.totals.get(header)
                                    if isinstance(total_value, (int, float)):
                                        cell.number_format = '"$"#,##0.00'
                                        cell.alignment = Alignment(horizontal='right', vertical='center')
                                    else:
                                        cell.alignment = Alignment(horizontal='right', vertical='center')
                                else:
                                    cell.alignment = Alignment(horizontal='right', vertical='center')
        
        # 4. Ajustar anchos de columna
        for col_num in range(1, ws.max_column + 1):
            column_letter = get_column_letter(col_num)
            max_length = 0
            
            for cell in ws[column_letter]:
                try:
                    if cell.value:
                        max_length = max(max_length, len(str(cell.value)))
                except:
                    pass
            
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column_letter].width = adjusted_width
        
        # 5. Guardar archivo
        wb.save(file_path)
        logger.info(f"✅ Archivo Excel generado: {file_path}")
    
    def get_file_response(self, export_result: ExportResult) -> HttpResponse:
        """
        Retorna una HttpResponse con el archivo para descarga.
        
        Args:
            export_result: Resultado de la exportación
        
        Returns:
            HttpResponse con el archivo
        """
        file_path = Path(settings.MEDIA_ROOT) / export_result.path
        
        if not file_path.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {file_path}")
        
        with open(file_path, 'rb') as f:
            response = HttpResponse(f.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = f'attachment; filename="{export_result.filename}"'
            return response
