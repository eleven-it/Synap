"""
Agentes CrewAI para el sistema de Reportes AI
"""
from .base import BaseAgent
from .orchestrator import OrchestratorAgent
from .data_analyst import DataAnalystAgent
from .report_generator import ReportGeneratorAgent

__all__ = [
    'BaseAgent',
    'OrchestratorAgent',
    'DataAnalystAgent',
    'ReportGeneratorAgent',
]

