"""
Servicio para validar relaciones aprendidas en MySQL.
Calcula métricas de match_rate, null_rate, duplicates, cardinality y genera muestras.
"""
import logging
from typing import Dict, List, Optional, Any
from .connection_pool import get_mysql_pool

logger = logging.getLogger(__name__)


class RelationshipValidationService:
    """Servicio para validar relaciones aprendidas."""
    
    @classmethod
    def validate(cls, base_empresa: str, from_table: str, from_column: str,
                 to_table: str, to_column: str, match_rule_json: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Valida una relación aprendida calculando métricas en MySQL.
        
        Args:
            base_empresa: Base de datos MySQL
            from_table: Tabla origen
            from_column: Columna origen
            to_table: Tabla destino
            to_column: Columna destino
            match_rule_json: Reglas de transformación (TRIM, UPPER, REPLACE, CAST, etc.)
            
        Returns:
            Dict con metrics, samples, warnings, suggested_confidence
        """
        try:
            pool = get_mysql_pool()
            with pool.get_connection(base_empresa) as conn:
                cursor = conn.cursor()
                
                # Cambiar a la base de datos correcta
                cursor.execute(f"USE `{base_empresa}`")
                
                # Construir expresiones SQL con transformaciones
                from_expr = cls._build_expression(from_table, from_column, match_rule_json, "from")
                to_expr = cls._build_expression(to_table, to_column, match_rule_json, "to")
                
                # 1. Null rate from
                null_rate_from = cls._calculate_null_rate(cursor, from_table, from_column)
                
                # 2. Null rate to
                null_rate_to = cls._calculate_null_rate(cursor, to_table, to_column)
                
                # 3. Match rate (aproximado)
                match_rate = cls._calculate_match_rate(
                    cursor, from_table, from_expr, to_table, to_expr
                )
                
                # 4. Duplicates in to
                duplicates_in_to = cls._check_duplicates(cursor, to_table, to_expr)
                
                # 5. Cardinality estimation
                cardinality_est = cls._estimate_cardinality(
                    cursor, from_table, from_expr, to_table, to_expr, duplicates_in_to
                )
                
                # 6. Samples (matches y misses)
                samples = cls._get_samples(
                    cursor, from_table, from_expr, to_table, to_expr
                )
                
                # 7. Suggested confidence
                suggested_confidence = cls._calculate_confidence(
                    match_rate, null_rate_from, null_rate_to, duplicates_in_to, cardinality_est
                )
                
                # 8. Warnings
                warnings = cls._generate_warnings(
                    match_rate, null_rate_from, null_rate_to, duplicates_in_to, cardinality_est
                )
                
                return {
                    "metrics": {
                        "match_rate": match_rate,
                        "null_rate_from": null_rate_from,
                        "null_rate_to": null_rate_to,
                        "duplicates_in_to": duplicates_in_to,
                        "cardinality_est": cardinality_est,
                        "sample_size": samples.get("total", 0)
                    },
                    "samples": {
                        "matches": samples.get("matches", []),
                        "misses": samples.get("misses", [])
                    },
                    "warnings": warnings,
                    "suggested_confidence": suggested_confidence
                }
                
        except Exception as e:
            logger.error(f"❌ Error validando relación {from_table}.{from_column} → {to_table}.{to_column}: {e}", exc_info=True)
            raise
    
    @classmethod
    def _build_expression(cls, table: str, column: str, match_rule: Optional[Dict], field_type: str) -> str:
        """
        Construye expresión SQL con transformaciones aplicadas.
        
        Args:
            table: Nombre de la tabla
            column: Nombre de la columna
            match_rule: Dict con transformaciones
            field_type: "from" o "to" (para determinar qué transformaciones aplicar)
            
        Returns:
            Expresión SQL (ej: "TRIM(UPPER(tabla.columna))")
        """
        expr = f"`{table}`.`{column}`"
        
        if not match_rule or "transformations" not in match_rule:
            return expr
        
        transformations = match_rule.get("transformations", [])
        
        # Aplicar transformaciones en orden
        for trans in transformations:
            trans_type = trans.get("type")
            field = trans.get("field", "both")  # from, to, both
            
            # Solo aplicar si es para este campo o "both"
            if field not in (field_type, "both"):
                continue
            
            if trans_type == "TRIM":
                expr = f"TRIM({expr})"
            elif trans_type == "UPPER":
                expr = f"UPPER({expr})"
            elif trans_type == "LOWER":
                expr = f"LOWER({expr})"
            elif trans_type == "REPLACE":
                pattern = trans.get("pattern", "")
                replacement = trans.get("replacement", "")
                # Escapar comillas simples
                pattern = pattern.replace("'", "''")
                replacement = replacement.replace("'", "''")
                expr = f"REPLACE({expr}, '{pattern}', '{replacement}')"
            elif trans_type == "CAST":
                cast_type = trans.get("cast_type", "CHAR")
                expr = f"CAST({expr} AS {cast_type})"
            elif trans_type == "CONCAT":
                prefix = trans.get("prefix", "")
                suffix = trans.get("suffix", "")
                prefix = prefix.replace("'", "''")
                suffix = suffix.replace("'", "''")
                parts = []
                if prefix:
                    parts.append(f"'{prefix}'")
                parts.append(expr)
                if suffix:
                    parts.append(f"'{suffix}'")
                expr = f"CONCAT({', '.join(parts)})"
        
        return expr
    
    @classmethod
    def _calculate_null_rate(cls, cursor, table: str, column: str) -> float:
        """Calcula el porcentaje de valores NULL en una columna."""
        try:
            cursor.execute(f"""
                SELECT 
                    SUM(CASE WHEN `{column}` IS NULL THEN 1 ELSE 0 END) / COUNT(*) as null_rate
                FROM `{table}`
            """)
            result = cursor.fetchone()
            return float(result[0]) if result and result[0] is not None else 0.0
        except Exception as e:
            logger.warning(f"Error calculando null_rate para {table}.{column}: {e}")
            return 0.0
    
    @classmethod
    def _calculate_match_rate(cls, cursor, from_table: str, from_expr: str,
                             to_table: str, to_expr: str) -> float:
        """
        Calcula el porcentaje de valores de from que existen en to.
        Usa muestreo si las tablas son muy grandes.
        """
        try:
            # Primero obtener total de filas en from_table
            cursor.execute(f"SELECT COUNT(*) FROM `{from_table}`")
            total_from = cursor.fetchone()[0]
            
            if total_from == 0:
                return 0.0
            
            # Si hay muchas filas, usar muestreo (limit 10000)
            limit_clause = ""
            if total_from > 10000:
                limit_clause = "LIMIT 10000"
                logger.debug(f"Usando muestreo para match_rate (tabla grande: {total_from} filas)")
            
            # Contar matches
            cursor.execute(f"""
                SELECT COUNT(*) as matches
                FROM (
                    SELECT DISTINCT {from_expr} as from_val
                    FROM `{from_table}`
                    WHERE {from_expr} IS NOT NULL
                    {limit_clause}
                ) f
                WHERE EXISTS (
                    SELECT 1
                    FROM `{to_table}` t
                    WHERE {to_expr} = f.from_val
                    LIMIT 1
                )
            """)
            
            matches = cursor.fetchone()[0]
            sample_size = min(total_from, 10000) if total_from > 10000 else total_from
            
            return float(matches) / sample_size if sample_size > 0 else 0.0
            
        except Exception as e:
            logger.warning(f"Error calculando match_rate: {e}")
            return 0.0
    
    @classmethod
    def _check_duplicates(cls, cursor, table: str, expr: str) -> int:
        """Verifica si hay valores duplicados en la columna destino."""
        try:
            cursor.execute(f"""
                SELECT COUNT(*) as dup_count
                FROM (
                    SELECT {expr} as val
                    FROM `{table}`
                    WHERE {expr} IS NOT NULL
                    GROUP BY {expr}
                    HAVING COUNT(*) > 1
                    LIMIT 1
                ) x
            """)
            result = cursor.fetchone()
            return int(result[0]) if result and result[0] is not None else 0
        except Exception as e:
            logger.warning(f"Error verificando duplicados: {e}")
            return 0
    
    @classmethod
    def _estimate_cardinality(cls, cursor, from_table: str, from_expr: str,
                             to_table: str, to_expr: str, duplicates_in_to: int) -> str:
        """
        Estima la cardinalidad de la relación (1-1, 1-N, N-1, N-N).
        Heurística simple basada en duplicados.
        """
        try:
            # Si no hay duplicados en destino, probablemente es único (1-N)
            if duplicates_in_to == 0:
                # Verificar si hay duplicados en origen
                cursor.execute(f"""
                    SELECT COUNT(*) as dup_count
                    FROM (
                        SELECT {from_expr} as val
                        FROM `{from_table}`
                        WHERE {from_expr} IS NOT NULL
                        GROUP BY {from_expr}
                        HAVING COUNT(*) > 1
                        LIMIT 1
                    ) x
                """)
                result = cursor.fetchone()
                dup_in_from = int(result[0]) if result and result[0] is not None else 0
                
                if dup_in_from == 0:
                    return "1-1"  # Ambos únicos
                else:
                    return "1-N"  # Destino único, origen puede tener duplicados
            
            # Si hay duplicados en destino
            # Verificar si hay duplicados en origen también
            cursor.execute(f"""
                SELECT COUNT(*) as dup_count
                FROM (
                    SELECT {from_expr} as val
                    FROM `{from_table}`
                    WHERE {from_expr} IS NOT NULL
                    GROUP BY {from_expr}
                    HAVING COUNT(*) > 1
                    LIMIT 1
                ) x
            """)
            result = cursor.fetchone()
            dup_in_from = int(result[0]) if result and result[0] is not None else 0
            
            if dup_in_from > 0:
                return "N-N"  # Ambos pueden tener duplicados
            else:
                return "N-1"  # Origen único, destino puede tener duplicados
                
        except Exception as e:
            logger.warning(f"Error estimando cardinalidad: {e}")
            return "N-N"  # Por defecto, más conservador
    
    @classmethod
    def _get_samples(cls, cursor, from_table: str, from_expr: str,
                     to_table: str, to_expr: str) -> Dict[str, List]:
        """
        Obtiene muestras de matches y misses.
        
        Returns:
            Dict con "matches" (top 10 valores que matchean) y "misses" (top 10 que no)
        """
        matches = []
        misses = []
        
        try:
            # Obtener matches (valores de from que existen en to)
            cursor.execute(f"""
                SELECT DISTINCT {from_expr} as from_val
                FROM `{from_table}` f
                WHERE {from_expr} IS NOT NULL
                  AND EXISTS (
                      SELECT 1
                      FROM `{to_table}` t
                      WHERE {to_expr} = {from_expr}
                      LIMIT 1
                  )
                LIMIT 10
            """)
            
            for row in cursor.fetchall():
                if row[0] is not None:
                    matches.append({"from_value": str(row[0])})
            
            # Obtener misses (valores de from que NO existen en to)
            cursor.execute(f"""
                SELECT DISTINCT {from_expr} as from_val
                FROM `{from_table}` f
                WHERE {from_expr} IS NOT NULL
                  AND NOT EXISTS (
                      SELECT 1
                      FROM `{to_table}` t
                      WHERE {to_expr} = {from_expr}
                      LIMIT 1
                  )
                LIMIT 10
            """)
            
            for row in cursor.fetchall():
                if row[0] is not None:
                    misses.append({
                        "from_value": str(row[0]),
                        "reason": "Not found in to_table"
                    })
            
            # Obtener total para sample_size
            cursor.execute(f"SELECT COUNT(*) FROM `{from_table}` WHERE {from_expr} IS NOT NULL")
            total = cursor.fetchone()[0]
            
            return {
                "matches": matches,
                "misses": misses,
                "total": int(total) if total else 0
            }
            
        except Exception as e:
            logger.warning(f"Error obteniendo samples: {e}")
            return {"matches": matches, "misses": misses, "total": 0}
    
    @classmethod
    def _calculate_confidence(cls, match_rate: float, null_rate_from: float,
                            null_rate_to: float, duplicates_in_to: int,
                            cardinality_est: str) -> float:
        """
        Calcula confianza sugerida basada en métricas.
        
        Reglas:
        - Base: match_rate
        - Penalizar si null_rate alto (> 5%)
        - Penalizar si hay duplicados en destino (puede ser N-N)
        - Ajustar según cardinalidad
        """
        confidence = match_rate
        
        # Penalizar null rates altos
        if null_rate_from > 0.05:
            confidence *= (1 - null_rate_from * 0.5)  # Penalización moderada
        
        if null_rate_to > 0.05:
            confidence *= (1 - null_rate_to * 0.5)
        
        # Penalizar duplicados en destino (indica posible N-N o problema de diseño)
        if duplicates_in_to > 0:
            confidence *= 0.9  # Penalización del 10%
        
        # Ajustar según cardinalidad
        if cardinality_est == "1-1":
            confidence *= 1.05  # Bonus del 5% para 1-1
        elif cardinality_est == "N-N":
            confidence *= 0.95  # Penalización del 5% para N-N
        
        # Asegurar rango [0.0, 1.0]
        confidence = max(0.0, min(1.0, confidence))
        
        return round(confidence, 4)
    
    @classmethod
    def _generate_warnings(cls, match_rate: float, null_rate_from: float,
                          null_rate_to: float, duplicates_in_to: int,
                          cardinality_est: str) -> List[str]:
        """Genera warnings basados en las métricas."""
        warnings = []
        
        if match_rate < 0.5:
            warnings.append(f"Low match rate ({match_rate:.1%}). Many values from source don't exist in destination.")
        
        if null_rate_from > 0.1:
            warnings.append(f"High null rate in source column ({null_rate_from:.1%}). Consider filtering NULLs.")
        
        if null_rate_to > 0.1:
            warnings.append(f"High null rate in destination column ({null_rate_to:.1%}). Consider filtering NULLs.")
        
        if duplicates_in_to > 0:
            warnings.append(f"Duplicates found in destination column. This suggests a {cardinality_est} relationship.")
        
        if cardinality_est == "N-N":
            warnings.append("N-N relationship detected. This may cause data multiplication in JOINs.")
        
        return warnings

