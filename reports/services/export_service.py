from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
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
        
        # Asegurar base_empresa dentro de filters para reportes que lo usan (ventas_netas, etc.)
        if payload.get("base_empresa"):
            payload.setdefault("filters", {})["base_empresa"] = payload["base_empresa"]
        
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

    def _declarative_export_headers(self, report: ReportDefinition, sample_row: Dict[str, Any]) -> Optional[List[str]]:
        """
        Orden de columnas alineado con WidgetEngine.renderTable: table_dimensions, table_metrics,
        y el mismo criterio cuando faltan esas claves (dimensiones del schema; sin métricas si kind=table
        y no hay table_metrics en options).
        """
        from .schema_service import ReportSchemaService

        try:
            schema = ReportSchemaService().build_schema(report)
        except Exception as exc:
            logger.warning("Export Excel: build_schema falló para %s: %s", report.slug, exc)
            return None

        table_widgets = [w for w in schema.default_widgets if w.kind == "table"]
        if not table_widgets:
            return None

        def _widget_sort_key(w):
            opts = w.options or {}
            o = opts.get("order")
            if o is None:
                o = 10**6
            return (o, str(w.id))

        table_widgets.sort(key=_widget_sort_key)
        w = table_widgets[0]
        opts = w.options or {}
        available = set(sample_row.keys())
        insertion_order = list(sample_row.keys())
        metric_names_schema: Set[str] = {m.name for m in schema.metrics}

        headers: List[str] = []

        if "table_dimensions" in opts and isinstance(opts["table_dimensions"], list):
            for name in opts["table_dimensions"]:
                if name in available:
                    headers.append(name)
        else:
            for d in schema.dimensions:
                if d.name in available:
                    headers.append(d.name)

        opts_tm = opts.get("table_metrics")
        explicit_tm = opts_tm is not None and isinstance(opts_tm, list)
        if explicit_tm:
            for name in opts_tm:
                if name in available:
                    headers.append(name)

        seen = set(headers)
        skip_metrics_tail: Set[str] = set()
        if w.kind == "table" and (not explicit_tm or (isinstance(opts_tm, list) and len(opts_tm) == 0)):
            skip_metrics_tail = set(metric_names_schema)

        for k in insertion_order:
            if k in seen:
                continue
            if k in skip_metrics_tail:
                continue
            headers.append(k)
            seen.add(k)

        return headers

    def _resolve_export_headers(self, report: ReportDefinition, sample_row: Dict[str, Any]) -> List[str]:
        """
        Define orden y columnas exportables (misma lógica que la tabla en pantalla cuando aplica).
        """
        if not sample_row:
            return []

        slug = report.slug
        cfg = report.config or {}
        insertion_order = list(sample_row.keys())
        available = set(sample_row.keys())

        if slug in ("ventas_netas", "ventas-netas"):
            preferred = [
                "mes_formato",
                "nombre_sucursal",
                "nro_punto_venta",
                "ventas_netas",
                "notas_credito",
                "ventas_brutas",
            ]
            return [h for h in preferred if h in available]

        if slug == "uninvoiced_remitos":
            preferred = [
                "fecha",
                "nro_comprobante",
                "sucursal",
                "punto_venta",
                "subtotal_desc",
            ]
            headers = [h for h in preferred if h in available]
            seen = set(headers)
            for k in insertion_order:
                if k in seen or k in ("id_sucursal", "id_punto_venta"):
                    continue
                headers.append(k)
                seen.add(k)
            return headers

        if slug == "pedidos-pendientes":
            preferred = [
                "fecha",
                "nro_comprobante",
                "cliente",
                "nombre_cliente",
                "subtotal_desc",
            ]
            headers = [h for h in preferred if h in available]
            seen = set(headers)
            for k in insertion_order:
                if k in seen or k in ("tipo_comprobante", "estado"):
                    continue
                headers.append(k)
                seen.add(k)
            return headers

        if cfg.get("version") == "declarative-v1":
            decl = self._declarative_export_headers(report, sample_row)
            if decl:
                return decl

        headers = list(insertion_order)
        if slug == "uninvoiced_remitos":
            headers = [h for h in headers if h not in ("id_sucursal", "id_punto_venta")]
        elif slug == "pedidos-pendientes":
            headers = [h for h in headers if h not in ("tipo_comprobante", "estado")]
        return headers

    def _generate_excel(self, file_path: Path, report: ReportDefinition, query_result, payload: Dict):
        """
        Genera un archivo Excel con los datos del reporte.
        
        Args:
            file_path: Ruta donde guardar el archivo
            report: Definición del reporte
            query_result: Resultado de la consulta (QueryResult)
            payload: Payload con filtros
        """
        if report.slug == "bo-stock-facturacion":
            self._generate_excel_bo(file_path, report, query_result)
            return
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
                # Orden y columnas alineados con la tabla del dashboard / schema declarativo
                headers = self._resolve_export_headers(report, query_result.data[0])
                
                # Traducir headers al español si es necesario
                header_translations = {
                    "mes": "Mes",
                    "mes_formato": "Mes (Formato)",
                    "id_sucursal": "ID Sucursal",
                    "nombre_sucursal": "Sucursal",
                    "id_punto_venta": "ID Punto de Venta",
                    "nro_punto_venta": "Punto de Venta",
                    "ventas_brutas": "Ventas Brutas",
                    "notas_credito": "Notas Crédito",
                    "ventas_netas": "Ventas Netas",
                    "fecha": "Fecha",
                    "nro_comprobante": "N° Comprobante",
                    "tipo_comprobante": "Tipo Comprobante",
                    "subtotal_desc": "Subtotal",
                    "estado": "Estado",
                    "sucursal": "Sucursal",
                    "punto_venta": "Punto de Venta",
                    "cliente": "Cliente",
                    "nombre_cliente": "Cliente",
                }
                # Ventas Netas: etiqueta "Mes" para la primera columna (mes_formato)
                if report.slug in ("ventas_netas", "ventas-netas"):
                    header_translations = {**header_translations, "mes_formato": "Mes"}
                
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
                    
                    # Escribir la fila completa (row ya apunta a la siguiente fila libre)
                    ws.append(total_row)
                    
                    # Mismo criterio de columnas numéricas que en las filas de datos
                    currency_headers_data = ["ventas_brutas", "notas_credito", "ventas_netas", "subtotal_desc"]
                    # Aplicar estilo y formato a la fila de totales (la que acabamos de escribir en row)
                    for col_num in range(1, len(total_row) + 1):
                        if col_num <= len(total_row):
                            cell = ws.cell(row=row, column=col_num)
                            cell.font = Font(bold=True)
                            cell.fill = PatternFill(start_color="D3D3D3", end_color="D3D3D3", fill_type="solid")
                            cell.border = border
                            
                            if col_num == 1:
                                cell.alignment = Alignment(horizontal='center', vertical='center')
                            else:
                                header = headers[col_num - 1]
                                # Mismo formato moneda que las filas de datos
                                if header in currency_headers_data:
                                    value = total_row[col_num - 1]
                                    if isinstance(value, (int, float)):
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

    def _generate_excel_bo(self, file_path: Path, report: ReportDefinition, query_result):
        """
        Genera un archivo Excel multi-hoja para el reporte BO vs Stock vs Facturación.
        Cada tab del reporte se exporta como una hoja.
        """
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter

        extra = query_result.meta.get("extra") or {}
        tabs = extra.get("tabs") or {}

        # Orden y nombre de hojas (key en tabs, título en Excel, clave de datos si difiere)
        sheets_config = [
            ("resumen", "Resumen", None),
            ("detalle_sin_stock", "Detalle sin stock", None),
            ("detalle_con_stock", "Detalle con stock", None),
            ("detalle_con_ingreso", "Detalle con ingreso", None),
            ("facturacion", "Facturación", None),
            ("remitos", "Remitos", None),
            ("backorder_detalle_rows", "Backorder detalle", None),
        ]

        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF", size=11)
        title_font = Font(bold=True, size=14, color="1E40AF")
        border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin'),
        )
        currency_headers = {
            "importe", "sub_total", "subtotal_desc", "bo_importe", "con_stock_importe",
            "con_ingreso_importe", "sin_stock_importe", "precio_x_renglon", "costo", "saldo_valorizado",
        }

        def sanitize_sheet_name(name: str) -> str:
            invalid = set('\\/*?:[]')
            out = "".join(c if c not in invalid else " " for c in name)
            return (out or "Hoja")[:31]

        wb = openpyxl.Workbook()
        first_sheet = True

        for sheet_key, sheet_title, data_key in sheets_config:
            data = tabs.get(data_key or sheet_key)
            if data is None:
                data = []
            if not isinstance(data, list):
                data = []

            # Excluir columnas no exportables (listas/dicts)
            if data and isinstance(data[0], dict):
                all_keys = list(data[0].keys())
                headers = [k for k in all_keys if not isinstance(data[0].get(k), (list, dict))]
                # Backorder detalle: no exportar cantidad, estado, id_cliente (alineado con la UI)
                if sheet_key == "backorder_detalle_rows":
                    headers = [h for h in headers if h not in ("cantidad", "estado", "id_cliente")]
            elif sheet_key == "resumen":
                headers = ["concepto", "importe", "tipo"]
                if not data:
                    data = []
            else:
                headers = []

            if first_sheet:
                ws = wb.active
                first_sheet = False
            else:
                ws = wb.create_sheet()
            ws.title = sanitize_sheet_name(sheet_title)

            row = 1
            # Título del reporte y período solo en la primera hoja
            if ws == wb.active:
                ws.merge_cells(f"A{row}:D{row}")
                cell = ws[f"A{row}"]
                cell.value = report.name
                cell.font = title_font
                cell.alignment = Alignment(horizontal='left', vertical='center')
                row += 1
                if query_result.notes:
                    ws.merge_cells(f"A{row}:D{row}")
                    cell = ws[f"A{row}"]
                    cell.value = query_result.notes[0] if query_result.notes else ""
                    cell.font = Font(size=10, italic=True)
                    row += 1
                row += 1

            if not headers:
                ws.cell(row=row, column=1).value = "Sin datos"
                row += 1
            else:
                header_labels = {
                    "concepto": "Concepto",
                    "importe": "Importe",
                    "tipo": "Tipo",
                    "codigo": "Código",
                    "articulo": "Artículo",
                    "categoria": "Categoría",
                    "bo_qty": "Cant. Pendientes",
                    "bo_importe": "Pendiente valorizado",
                    "stock_actual": "Stock actual",
                    "stock_reservado": "Stock reservado",
                    "disponible": "Disponible",
                    "costo": "Costo",
                    "saldo_valorizado": "Saldo valorizado",
                    "oc_pendiente": "OC pendiente",
                    "con_stock_qty": "Con stock cant.",
                    "con_stock_importe": "Con stock importe",
                    "con_ingreso_qty": "Con ingreso cant.",
                    "con_ingreso_importe": "Con ingreso importe",
                    "sin_stock_qty": "Sin stock cant.",
                    "sin_stock_importe": "Sin stock importe",
                    "nro": "Nº",
                    "id_cliente": "ID Cliente",
                    "cliente": "Cliente",
                    "sub_total": "Subtotal",
                    "porc_ventas": "% Ventas",
                    "ultima_compra": "Última compra",
                    "vendedor": "Vendedor",
                    "zona": "Zona",
                    "telefono": "Teléfono",
                    "email": "Email",
                    "cuit": "CUIT",
                    "fecha": "Fecha",
                    "nro_comprobante": "N° Comprobante",
                    "id_sucursal": "ID Sucursal",
                    "sucursal": "Sucursal",
                    "id_punto_venta": "ID Punto de venta",
                    "punto_venta": "Punto de venta",
                    "subtotal_desc": "Subtotal",
                    "nro_comp": "N° Comp.",
                    "descripcion": "Descripción",
                    "cod_manual": "Cód. manual",
                    "cantidad": "Cantidad",
                    "cant_pend": "Cant. pend.",
                    "estado": "Estado",
                    "precio_x_renglon": "Pendiente valorizado",
                    "nombre_rubro": "Rubro",
                    "nombre_sub_rubro": "Subrubro",
                    "nombre_vendedor": "Vendedor",
                    "id_art": "ID Art.",
                }
                translated = [header_labels.get(h, h.replace("_", " ").title()) for h in headers]
                ws.append(translated)
                for col_num, _ in enumerate(translated, 1):
                    c = ws.cell(row=row, column=col_num)
                    c.fill = header_fill
                    c.font = header_font
                    c.alignment = Alignment(horizontal='center', vertical='center')
                    c.border = border
                row += 1

                for data_row in data:
                    row_vals = []
                    for h in headers:
                        val = data_row.get(h, "")
                        if isinstance(val, (list, dict)):
                            val = ""
                        row_vals.append(val)
                    ws.append(row_vals)
                    for col_num, (header, value) in enumerate(zip(headers, row_vals), 1):
                        cell = ws.cell(row=row, column=col_num)
                        cell.border = border
                        if header in currency_headers and isinstance(value, (int, float)):
                            cell.number_format = '"$"#,##0.00'
                            cell.alignment = Alignment(horizontal='right', vertical='center')
                        else:
                            cell.alignment = Alignment(horizontal='left', vertical='center')
                    row += 1

            for col_num in range(1, ws.max_column + 1):
                col_letter = get_column_letter(col_num)
                max_len = 0
                for cell in ws[col_letter]:
                    if cell.value is not None:
                        max_len = max(max_len, len(str(cell.value)))
                ws.column_dimensions[col_letter].width = min(max_len + 2, 50)

        wb.save(file_path)
        logger.info(f"✅ Archivo Excel BO generado con {len(sheets_config)} hojas: {file_path}")

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
