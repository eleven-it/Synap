"""
Servicio de métricas de calidad para el Data Analyst Agent
"""
from typing import Dict, List
from datetime import datetime, timedelta
from django.db.models import Avg, Count, Q, F
from django.utils import timezone

from ..models import (
    ReportRequest,
    RelationshipCandidate,
    SynonymMapping,
    QueryCorrection,
    AgentMetrics
)


class QualityMetricsService:
    """
    Calcula y monitorea métricas de calidad del Data Analyst Agent
    """
    
    def __init__(self):
        pass
    
    def calculate_all_metrics(self, period_days: int = 7) -> Dict:
        """
        Calcula todas las métricas de calidad para un periodo
        
        Args:
            period_days: Días hacia atrás para calcular
        
        Returns:
            Dict con todas las métricas
        """
        since = timezone.now() - timedelta(days=period_days)
        
        return {
            'period_days': period_days,
            'period_start': since.isoformat(),
            'period_end': timezone.now().isoformat(),
            'hit_rate': self.calculate_hit_rate(since),
            'precision_at_k': self.calculate_precision_at_k(since, k=1),
            'avg_execution_time': self.calculate_avg_execution_time(since),
            'correction_rate': self.calculate_correction_rate(since),
            'coverage_rate': self.calculate_coverage_rate(since),
            'relationship_quality': self.calculate_relationship_quality(),
            'synonym_quality': self.calculate_synonym_quality(),
        }
    
    def calculate_hit_rate(self, since: datetime) -> float:
        """
        Hit rate: % de queries que se resolvieron exitosamente
        Target: ≥ 98%
        """
        total = ReportRequest.objects.filter(created_at__gte=since).count()
        
        if total == 0:
            return 0.0
        
        successful = ReportRequest.objects.filter(
            created_at__gte=since,
            status='completed'
        ).count()
        
        return round(successful / total * 100, 2)
    
    def calculate_precision_at_k(self, since: datetime, k: int = 1) -> float:
        """
        Precision@K: % de veces que la K-ésima relación sugerida fue correcta
        Target: ≥ 92%
        """
        # Relaciones que fueron usadas exitosamente
        used_successfully = RelationshipCandidate.objects.filter(
            last_used_at__gte=since,
            times_used_successfully__gt=0
        ).count()
        
        # Total de relaciones usadas
        used_total = RelationshipCandidate.objects.filter(
            last_used_at__gte=since
        ).count()
        
        if used_total == 0:
            return 0.0
        
        return round(used_successfully / used_total * 100, 2)
    
    def calculate_avg_execution_time(self, since: datetime) -> float:
        """
        Tiempo promedio de ejecución de queries (segundos)
        Target: < 5s (p95)
        """
        metrics = AgentMetrics.objects.filter(
            agent_name='Analista de Datos',
            date__gte=since
        ).aggregate(
            avg_time=Avg('avg_processing_time')
        )
        
        return round(metrics['avg_time'] or 0.0, 2)
    
    def calculate_correction_rate(self, since: datetime) -> float:
        """
        Tasa de correcciones: % de queries que requirieron corrección humana
        Target: ≤ 3%
        """
        total = ReportRequest.objects.filter(created_at__gte=since).count()
        
        if total == 0:
            return 0.0
        
        corrected = QueryCorrection.objects.filter(
            corrected_at__gte=since
        ).values('report_request_id').distinct().count()
        
        return round(corrected / total * 100, 2)
    
    def calculate_coverage_rate(self, since: datetime) -> float:
        """
        Tasa de cobertura: % de queries entendidas sin intervención
        Target: ≥ 95%
        """
        total = ReportRequest.objects.filter(created_at__gte=since).count()
        
        if total == 0:
            return 0.0
        
        # Queries que NO requirieron clarificación ni corrección
        covered = ReportRequest.objects.filter(
            created_at__gte=since,
            status='completed'
        ).exclude(
            corrections__isnull=False
        ).count()
        
        return round(covered / total * 100, 2)
    
    def calculate_relationship_quality(self) -> Dict:
        """
        Métricas de calidad del catálogo de relaciones
        """
        total = RelationshipCandidate.objects.count()
        
        if total == 0:
            return {
                'total': 0,
                'avg_confidence': 0.0,
                'high_confidence': 0,
                'validated': 0
            }
        
        high_conf = RelationshipCandidate.objects.filter(
            confidence_score__gte=0.8
        ).count()
        
        validated = RelationshipCandidate.objects.filter(
            validated_by_human=True
        ).count()
        
        avg_conf = RelationshipCandidate.objects.aggregate(
            avg=Avg('confidence_score')
        )['avg'] or 0.0
        
        return {
            'total': total,
            'avg_confidence': round(avg_conf, 2),
            'high_confidence': high_conf,
            'high_confidence_pct': round(high_conf / total * 100, 2),
            'validated': validated,
            'validated_pct': round(validated / total * 100, 2)
        }
    
    def calculate_synonym_quality(self) -> Dict:
        """
        Métricas de calidad del diccionario de sinónimos
        """
        total = SynonymMapping.objects.count()
        
        if total == 0:
            return {
                'total': 0,
                'avg_confidence': 0.0,
                'active': 0,
                'active_pct': 0.0,
                'successful': 0,
                'successful_pct': 0.0
            }
        
        # Sinónimos activamente usados
        active = SynonymMapping.objects.filter(
            times_used__gt=0
        ).count()
        
        # Sinónimos con alta tasa de éxito
        successful = SynonymMapping.objects.filter(
            times_used__gt=0
        ).annotate(
            success_rate=F('times_successful') * 1.0 / F('times_used')
        ).filter(
            success_rate__gte=0.8
        ).count()
        
        avg_conf = SynonymMapping.objects.aggregate(
            avg=Avg('confidence')
        )['avg'] or 0.0
        
        return {
            'total': total,
            'avg_confidence': round(avg_conf, 2),
            'active': active,
            'active_pct': round(active / total * 100, 2) if total > 0 else 0.0,
            'successful': successful,
            'successful_pct': round(successful / active * 100, 2) if active > 0 else 0.0
        }
    
    def get_top_relationships(self, limit: int = 10) -> List[Dict]:
        """
        Obtiene las relaciones más exitosas
        """
        relationships = RelationshipCandidate.objects.filter(
            times_used_successfully__gt=0
        ).order_by('-times_used_successfully')[:limit]
        
        return [{
            'source': f"{rel.source_table}.{rel.source_column}",
            'target': f"{rel.target_table}.{rel.target_column}",
            'confidence': rel.confidence_score,
            'times_used': rel.times_used_successfully,
            'cardinality': rel.cardinality
        } for rel in relationships]
    
    def get_problematic_queries(self, since: datetime, limit: int = 10) -> List[Dict]:
        """
        Obtiene queries que fallaron o fueron corregidas
        """
        corrections = QueryCorrection.objects.filter(
            corrected_at__gte=since
        ).select_related('report_request').order_by('-corrected_at')[:limit]
        
        return [{
            'query': corr.original_query,
            'correction_type': corr.get_correction_type_display(),
            'corrected_at': corr.corrected_at.isoformat(),
            'notes': corr.correction_notes
        } for corr in corrections]
    
    def generate_report(self, period_days: int = 7) -> str:
        """
        Genera un reporte de calidad en texto plano
        """
        metrics = self.calculate_all_metrics(period_days)
        
        report = f"""
╔══════════════════════════════════════════════════════════════╗
║         REPORTE DE CALIDAD - DATA ANALYST AGENT              ║
╚══════════════════════════════════════════════════════════════╝

Periodo: {period_days} días
Desde: {metrics['period_start']}
Hasta: {metrics['period_end']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 MÉTRICAS PRINCIPALES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

• Hit Rate (queries exitosas):     {metrics['hit_rate']}% {'✅' if metrics['hit_rate'] >= 98 else '⚠️'}
  Target: ≥ 98%

• Precision@1 (relaciones correctas): {metrics['precision_at_k']}% {'✅' if metrics['precision_at_k'] >= 92 else '⚠️'}
  Target: ≥ 92%

• Tiempo Promedio:                 {metrics['avg_execution_time']}s {'✅' if metrics['avg_execution_time'] < 5 else '⚠️'}
  Target: < 5s

• Tasa de Correcciones:            {metrics['correction_rate']}% {'✅' if metrics['correction_rate'] <= 3 else '⚠️'}
  Target: ≤ 3%

• Cobertura (sin intervención):    {metrics['coverage_rate']}% {'✅' if metrics['coverage_rate'] >= 95 else '⚠️'}
  Target: ≥ 95%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔗 CALIDAD DE RELACIONES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

• Total de relaciones:             {metrics['relationship_quality']['total']}
• Confianza promedio:              {metrics['relationship_quality']['avg_confidence']}
• Alta confianza (≥0.8):           {metrics['relationship_quality']['high_confidence']} ({metrics['relationship_quality']['high_confidence_pct']}%)
• Validadas por humanos:           {metrics['relationship_quality']['validated']} ({metrics['relationship_quality']['validated_pct']}%)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📚 CALIDAD DE SINÓNIMOS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

• Total de mapeos:                 {metrics['synonym_quality']['total']}
• Confianza promedio:              {metrics['synonym_quality']['avg_confidence']}
• Activamente usados:              {metrics['synonym_quality']['active']} ({metrics['synonym_quality']['active_pct']}%)
• Con alta tasa de éxito (≥80%):   {metrics['synonym_quality']['successful']} ({metrics['synonym_quality']['successful_pct']}%)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        
        return report

