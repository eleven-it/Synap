from django.core.management.base import BaseCommand
from django.utils import timezone

from reports_ai.models import QueryCorrection, SynonymMapping, RelationshipCandidate, ReportRequest


class Command(BaseCommand):
	help = "Crea sugerencias/correcciones de ejemplo para el Analista de Datos V2 (active learning)"

	def add_arguments(self, parser):
		parser.add_argument(
			"--apply",
			action="store_true",
			help="(Compat) Mantiene la bandera pero no es necesaria: las correcciones quedan disponibles inmediatamente",
		)

	def handle(self, *args, **options):
		self.stdout.write("\n🧪 Sembrando correcciones y sinónimos de ejemplo...")

		# 0) Crear una ReportRequest base para asociar las correcciones
		sample_query = "Cual es el ultimo pedido creado en estado pendiente?"
		request_id = f"seed-{int(timezone.now().timestamp())}"
		req = ReportRequest.objects.create(
			request_id=request_id,
			intent="report_data",
			query_text=sample_query,
			source="web",
			status="completed",
		)

		# 1) Corrección de 'pedido pendiente' → usar comp_ped (+ stockp para detalle). Wrong table
		wrong_sql = "SELECT * FROM inventario WHERE tipo = 'Pendiente' ORDER BY fecha_inventario DESC LIMIT 1;"
		corrected_sql = (
			"SELECT p.*\n"
			"FROM comp_ped p\n"
			"WHERE p.estado = 'Pendiente'\n"
			"ORDER BY p.fecha_creacion DESC, p.id DESC\n"
			"LIMIT 1;"
		)
		notes = (
			"Mapeo correcto: 'pedido' → tabla comp_ped. El estado 'Pendiente' se filtra en comp_ped. "
			"Para detalle de ítems usar join a stockp por la clave del pedido (p.id = s.id_pedido)."
		)

		qc1 = QueryCorrection.objects.create(
			report_request=req,
			original_query=sample_query,
			original_sql=wrong_sql,
			correction_type="wrong_table",
			corrected_sql=corrected_sql,
			correction_notes=notes,
		)
		qc1.applied_to_catalog = True
		qc1.save()

		# 1.b) Corrección adicional: wrong_column (TipoComprobante -> Estado)
		wrong_sql_col = (
			"SELECT p.*\n"
			"FROM comp_ped p\n"
			"WHERE p.TipoComprobante = 'Pendiente'\n"
			"ORDER BY p.fecha_creacion DESC, p.id DESC\n"
			"LIMIT 1;"
		)
		corrected_sql_col = corrected_sql  # mismo SQL correcto usando p.estado
		notes_col = (
			"El campo correcto para el estado del pedido es 'Estado', no 'TipoComprobante'. "
			"Usar p.estado = 'Pendiente' para filtrar el estado funcional."
		)
		qc2 = QueryCorrection.objects.create(
			report_request=req,
			original_query=sample_query,
			original_sql=wrong_sql_col,
			correction_type="wrong_column",
			corrected_sql=corrected_sql_col,
			correction_notes=notes_col,
		)
		qc2.applied_to_catalog = True
		qc2.save()

		# 2) Sinónimos de apoyo (negocio → patrón de columna)
		synonyms = [
			{"business_term": "pedido", "column_pattern": "comp_ped", "confidence": 0.95},
			{"business_term": "orden", "column_pattern": "comp_ped", "confidence": 0.90},
			{"business_term": "estado pendiente", "column_pattern": "comp_ped.estado", "confidence": 0.95},
			{"business_term": "pendiente", "column_pattern": "comp_ped.estado", "confidence": 0.90},
		]
		for syn in synonyms:
			SynonymMapping.objects.update_or_create(
				business_term=syn["business_term"],
				column_pattern=syn["column_pattern"],
				defaults={
					"confidence": syn["confidence"],
					"source": "sample_seed",
					"times_used": 0,
					"times_successful": 0,
				},
			)

		# 3) Asegurar relación candidata (si no existe) comp_ped ↔ stockp
		rel, _ = RelationshipCandidate.objects.get_or_create(
			source_table="comp_ped",
			source_column="id",
			target_table="stockp",
			target_column="id_pedido",
			defaults={
				"confidence_score": 0.9,
				"name_match_score": 0.9,
				"type_compatibility": 1.0,
				"domain_inclusion": 0.0,
				"uniqueness_score": 0.8,
				"cardinality": "1:N",
				"has_index": True,
				"logic_interpreter_hint": False,
			},
		)
		# No forzamos el join si el usuario no pide ítems, pero queda disponible en el grafo

		self.stdout.write(self.style.SUCCESS("\n✅ Correcciones y sinónimos de ejemplo creados/actualizados (applied_to_catalog=True)."))
		self.stdout.write("\nSiguiente paso sugerido:")
		self.stdout.write("  Repite tu consulta en el chat: el Orquestador cargará los learnings automáticamente.\n")
