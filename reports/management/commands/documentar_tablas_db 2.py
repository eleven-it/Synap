"""
Documenta todas las tablas de la base MySQL (AdministraNET) y su uso en VB6/Synap.

Usa SemanticService para obtener schema (columnas, PK, FK) y relaciones del catálogo.
Además extrae:
- Relaciones inferidas desde consultas SQL (JOINs en VB6 y Synap) para una DB no normalizada.
- Uso de cada tabla en AdministraNET (formularios/procedimientos que leen/escriben).

Salida:
- reports/docs/DB_INDICE_TABLAS.md: índice de tablas con enlaces.
- reports/docs/tablas/<nombre_tabla>.md: documento por tabla (schema, relaciones, uso).

Uso:
  python manage.py documentar_tablas_db
  python manage.py documentar_tablas_db --base-empresa administranet89
  python manage.py documentar_tablas_db --solo-schema   # sin escanear VB6/Synap
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from pathlib import Path

from reports.services.semantic_service import (
    SemanticService,
    SemanticDatasource,
    SemanticField,
    SemanticRelationship,
)
from reports.services.documentacion_db_service import (
    extraer_uso_tablas_vb6,
    extraer_relaciones_desde_sql_vb6,
    extraer_relaciones_desde_sql_synap,
    extraer_uso_tablas_synap,
    agrupar_relaciones_por_tabla,
    UsoTabla,
    RelacionDesdeSQL,
)


class Command(BaseCommand):
    help = "Documenta tablas de la DB (schema, relaciones desde SQL, uso en AdministraNET)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--base-empresa",
            type=str,
            default=None,
            help="Base de datos MySQL (default: DEFAULT_BASE_EMPRESA)",
        )
        parser.add_argument(
            "--solo-schema",
            action="store_true",
            help="Solo generar schema desde information_schema, sin escanear VB6/Synap",
        )
        parser.add_argument(
            "--vb6",
            type=str,
            default=None,
            help="Ruta a carpeta administranet_vb6 (default: proyecto/administranet_vb6)",
        )
        parser.add_argument(
            "--output-dir",
            type=str,
            default=None,
            help="Carpeta base de documentación (default: reports/docs)",
        )

    def handle(self, *args, **options):
        base_empresa = options.get("base_empresa") or getattr(
            settings, "DEFAULT_BASE_EMPRESA", None
        )
        if not base_empresa:
            self.stderr.write(
                self.style.ERROR(
                    "Indique --base-empresa o configure DEFAULT_BASE_EMPRESA / DB_NAME en .env"
                )
            )
            return

        solo_schema = options.get("solo_schema", False)
        vb6_path = options.get("vb6")
        output_dir = Path(
            options.get("output_dir")
            or (Path(settings.BASE_DIR) / "reports" / "docs")
        )
        tablas_dir = output_dir / "tablas"
        tablas_dir.mkdir(parents=True, exist_ok=True)

        self.stdout.write(f"Base empresa: {base_empresa}")
        self.stdout.write(f"Salida: {output_dir}")

        # 1) Listar tablas y obtener schema + relaciones de catálogo
        self.stdout.write("Obteniendo lista de tablas y schema...")
        schemas = {}
        try:
            datasources = SemanticService.list_datasources(base_empresa=base_empresa)
            table_names = [ds.name for ds in datasources]
            self.stdout.write(f"  {len(table_names)} tablas encontradas.")
            for name in table_names:
                fields = SemanticService.get_fields(name, base_empresa=base_empresa)
                rels = SemanticService.get_relationships(name, base_empresa=base_empresa)
                schemas[name] = {"fields": fields, "relationships": rels}
        except Exception as e:
            self.stderr.write(
                self.style.WARNING(
                    f"No se pudo conectar a la base ({e}). Usando tablas conocidas y omitiendo schema."
                )
            )
            table_names = list(SemanticService.KNOWN_TABLES)
            schemas = {name: {"fields": [], "relationships": []} for name in table_names}

        # 2) Relaciones y uso desde código (si no --solo-schema)
        uso_vb6: dict = {}
        uso_synap: dict = {}
        relaciones_sql: list = []
        relaciones_por_tabla: dict = {}

        if not solo_schema:
            base_dir = Path(settings.BASE_DIR)
            vb6_root = vb6_path or (base_dir / "administranet_vb6")
            reports_root = base_dir / "reports"

            self.stdout.write("Escaneando VB6 para uso y relaciones desde SQL...")
            uso_vb6 = extraer_uso_tablas_vb6(str(vb6_root))
            rel_vb6 = extraer_relaciones_desde_sql_vb6(str(vb6_root))
            self.stdout.write(f"  Uso VB6: {len(uso_vb6)} tablas referenciadas, {len(rel_vb6)} relaciones desde SQL.")

            self.stdout.write("Escaneando Synap (reports) para relaciones y uso...")
            rel_synap = extraer_relaciones_desde_sql_synap(str(reports_root))
            uso_synap = extraer_uso_tablas_synap(str(reports_root))
            relaciones_sql = rel_vb6 + rel_synap
            relaciones_por_tabla = agrupar_relaciones_por_tabla(relaciones_sql)
            self.stdout.write(f"  Relaciones desde SQL: {len(relaciones_sql)} (VB6 + Synap).")

        # 3) Escribir índice
        self._escribir_indice(output_dir, tablas_dir, table_names, base_empresa)

        # 4) Escribir un doc por tabla
        for name in table_names:
            self._escribir_doc_tabla(
                tablas_dir=tablas_dir,
                table_name=name,
                schema=schemas.get(name, {}),
                uso_vb6=uso_vb6.get(name.lower(), []),
                uso_synap=uso_synap.get(name.lower(), []),
                relaciones_sql_tabla=relaciones_por_tabla.get(name.lower(), []),
                base_empresa=base_empresa,
            )
        self.stdout.write(self.style.SUCCESS(f"Documentación generada en {tablas_dir}"))

    def _escribir_indice(
        self,
        output_dir: Path,
        tablas_dir: Path,
        table_names: list,
        base_empresa: str,
    ):
        rel_path_tablas = tablas_dir.relative_to(output_dir)
        lineas = [
            "# Índice de tablas de la base AdministraNET",
            "",
            f"Base documentada: **{base_empresa}**",
            "",
            "Este índice y los documentos por tabla se generan con:",
            "`python manage.py documentar_tablas_db [--base-empresa NOMBRE]`",
            "",
            "Cada tabla incluye:",
            "- Schema (columnas, tipos, PK, FK desde information_schema).",
            "- Relaciones desde consultas SQL (JOINs en VB6 y Synap) para diseño de DB normalizada.",
            "- Uso en AdministraNET (formularios/procedimientos que leen/escriben) para migración a Synap.",
            "",
            "---",
            "",
            "## Tablas",
            "",
        ]
        for name in sorted(table_names):
            doc_name = f"{rel_path_tablas}/{name}.md"
            lineas.append(f"- [{name}]({doc_name})")
        (output_dir / "DB_INDICE_TABLAS.md").write_text("\n".join(lineas), encoding="utf-8")

    def _escribir_doc_tabla(
        self,
        tablas_dir: Path,
        table_name: str,
        schema: dict,
        uso_vb6: list,
        uso_synap: list,
        relaciones_sql_tabla: list,
        base_empresa: str,
    ):
        fields: list = schema.get("fields") or []
        relationships: list = schema.get("relationships") or []

        lineas = [
            f"# Tabla `{table_name}`",
            "",
            f"Base: **{base_empresa}**",
            "",
            "---",
            "",
            "## 1. Schema (information_schema)",
            "",
        ]

        # Campos
        lineas.append("### 1.1 Columnas")
        lineas.append("")
        lineas.append("| Campo | Tipo | Nulo | PK | FK | Referencia |")
        lineas.append("|-------|------|------|----|----|------------|")
        for f in fields:
            if not isinstance(f, SemanticField):
                continue
            ref = ""
            if f.referenced_table and f.referenced_field:
                ref = f"{f.referenced_table}.{f.referenced_field}"
            lineas.append(
                f"| {f.name} | {f.data_type} | {'Sí' if f.is_nullable else 'No'} | "
                f"{'✓' if f.is_primary_key else ''} | {'✓' if f.is_foreign_key else ''} | {ref} |"
            )
        lineas.append("")

        # Relaciones de catálogo (FK)
        lineas.append("### 1.2 Relaciones (FK del catálogo)")
        lineas.append("")
        if not relationships:
            lineas.append("*No hay claves foráneas definidas en el catálogo para esta tabla.*")
        else:
            lineas.append("| Desde (campo) | Hacia (tabla.campo) | Tipo |")
            lineas.append("|---------------|---------------------|------|")
            for r in relationships:
                if not isinstance(r, SemanticRelationship):
                    continue
                lineas.append(
                    f"| {r.from_table}.{r.from_field} | {r.to_table}.{r.to_field} | {r.relationship_type or ''} |"
                )
        lineas.append("")
        lineas.append("---")
        lineas.append("")

        # Relaciones inferidas desde SQL (fundamental para DB no normalizada)
        lineas.append("## 2. Relaciones inferidas desde consultas SQL")
        lineas.append("")
        lineas.append(
            "Relaciones detectadas por uso en código (JOINs en VB6 y Synap). "
            "Sirven para diseñar una DB normalizada."
        )
        lineas.append("")
        if not relaciones_sql_tabla:
            lineas.append("*No se encontraron JOINs que involucren esta tabla en el código escaneado.*")
        else:
            lineas.append("| Origen | Destino | Archivo | Línea | Fragmento |")
            lineas.append("|--------|---------|---------|-------|------------|")
            for r in relaciones_sql_tabla:
                if not isinstance(r, RelacionDesdeSQL):
                    continue
                snip = (r.snippet[:80] + "…") if len(r.snippet) > 80 else r.snippet
                snip = snip.replace("|", "\\|").replace("\n", " ")
                lineas.append(
                    f"| {r.tabla_origen} | {r.tabla_destino} | {r.archivo} | {r.linea or '-'} | {snip} |"
                )
        lineas.append("")
        lineas.append("---")
        lineas.append("")

        # Uso en AdministraNET (VB6)
        lineas.append("## 3. Uso en AdministraNET (VB6)")
        lineas.append("")
        lineas.append(
            "Formularios y procedimientos que referencian esta tabla (lectura/escritura). "
            "Base para migración AdministraNET → Synap."
        )
        lineas.append("")
        if not uso_vb6:
            lineas.append("*No se encontraron referencias a esta tabla en el código VB6 escaneado.*")
        else:
            lineas.append("| Archivo | Línea | Operación | Fragmento |")
            lineas.append("|---------|-------|-----------|-----------|")
            for u in uso_vb6[:80]:  # límite para no hacer el doc gigante
                if not isinstance(u, UsoTabla):
                    continue
                snip = (u.snippet[:60] + "…") if len(u.snippet) > 60 else u.snippet
                snip = snip.replace("|", "\\|").replace("\n", " ")
                lineas.append(f"| {u.archivo} | {u.linea} | {u.operacion} | {snip} |")
            if len(uso_vb6) > 80:
                lineas.append(f"| … | … | … | *({len(uso_vb6) - 80} referencias más)* |")
        lineas.append("")
        lineas.append("---")
        lineas.append("")

        # Uso en Synap (reports)
        lineas.append("## 4. Uso en Synap (reports)")
        lineas.append("")
        if not uso_synap:
            lineas.append("*No se encontraron referencias en el módulo reports.*")
        else:
            lineas.append("| Archivo | Línea | Operación | Fragmento |")
            lineas.append("|---------|-------|-----------|-----------|")
            for u in uso_synap[:50]:
                if not isinstance(u, UsoTabla):
                    continue
                snip = (u.snippet[:60] + "…") if len(u.snippet) > 60 else u.snippet
                snip = snip.replace("|", "\\|").replace("\n", " ")
                lineas.append(f"| {u.archivo} | {u.linea} | {u.operacion} | {snip} |")
            if len(uso_synap) > 50:
                lineas.append(f"| … | … | … | *({len(uso_synap) - 50} referencias más)* |")
        lineas.append("")
        lineas.append("[← Índice de tablas](../DB_INDICE_TABLAS.md)")

        (tablas_dir / f"{table_name}.md").write_text("\n".join(lineas), encoding="utf-8")
