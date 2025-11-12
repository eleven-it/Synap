"""
Servicio de análisis de código
Wrapper sobre VB6AnalyzerTool
"""
from reports_ai.tools.vb6_analyzer import VB6AnalyzerTool

class CodeAnalysisService:
    """Servicio de análisis de código VB6"""
    
    def __init__(self):
        self.vb6_analyzer = VB6AnalyzerTool()
    
    def extract_rules(self, module: str):
        """Extrae reglas de un módulo"""
        return self.vb6_analyzer.extract_business_rules(module)
    
    def get_glossary(self):
        """Extrae glosario del código"""
        return self.vb6_analyzer.get_business_glossary_from_code()

