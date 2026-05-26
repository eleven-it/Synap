"""Métricas de solo lectura para API dashboard gerencial (legacy AdministraNET)."""

from .command_center import run_command_center
from .ventas_metrics import fetch_ventas_resumen

__all__ = ["run_command_center", "fetch_ventas_resumen"]
