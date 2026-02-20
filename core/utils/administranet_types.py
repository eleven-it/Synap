"""
Normalización y validación de tipos para datos que se leen o escriben en MySQL administraNET.

Regla de proyecto: en todo el código que interactúe con bases/tablas de AdministraNET (VB6),
se deben validar y normalizar los tipos de datos para cumplir el mismo criterio que AdministraNET:
- Columnas INT (nullable): enviar int o None; nunca string numérico sin convertir.
- Columnas DATE (nullable): enviar string 'YYYY-MM-DD' o None; nunca string vacío (evitar 0000-00-00).
- Columnas VARCHAR/MEDIUMTEXT: enviar string; usar valor por defecto (ej. '-') cuando el campo sea opcional y esté vacío.

Referencia: schema en docs (reports/docs/tablas/*.md, docs/general/tablas/*.md) y comportamiento
de formularios VB6 (Ej. Empresa.frm → DatosEmpresa).

Uso:
    from core.utils.administranet_types import to_int_or_none, to_date_or_none, str_or_default

    cod_prov = to_int_or_none(datos.get('CodProvincia'))
    inicio_act = to_date_or_none(datos.get('InicioAct'))
    whatsapp = str_or_default(datos.get('whatsapp'), '-')
"""
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Optional


def to_int_or_none(value: Any) -> Optional[int]:
    """
    Convierte a int para columnas INT de MySQL (nullable).
    Usar para: CodProvincia, CodDepartamento, IDIva, id_pais, id_empresa, id_sucursal, etc.
    """
    if value is None or value == '':
        return None
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def to_date_or_none(value: Any) -> Optional[str]:
    """
    Convierte a string 'YYYY-MM-DD' o None para columnas DATE de MySQL (nullable).
    Evita enviar string vacío (MySQL podría guardar 0000-00-00).
    """
    if value is None or (isinstance(value, str) and value.strip() == ''):
        return None
    if isinstance(value, datetime):
        return value.strftime('%Y-%m-%d')
    if isinstance(value, str) and len(value) >= 10 and value.count('-') == 2:
        return value.strip()[:10]
    try:
        s = str(value).strip()[:10]
        dt = datetime.strptime(s, '%Y-%m-%d')
        return dt.strftime('%Y-%m-%d')
    except (ValueError, TypeError):
        return None


def str_or_default(value: Any, default: str = '') -> str:
    """
    Normaliza valores para columnas VARCHAR/MEDIUMTEXT.
    Devuelve el string limpio (strip) o default si está vacío/None.
    Usar default='-' para campos opcionales que en AdministraNET suelen llevar '-' cuando vacío.
    """
    if value is None:
        return default
    s = str(value).strip()
    return s if s else default


def to_decimal_or_none(value: Any, quantize: Optional[str] = None) -> Optional[Decimal]:
    """
    Convierte a Decimal para columnas DECIMAL/NUMERIC de MySQL (nullable).
    Opcional: quantize='0.01' para redondear a 2 decimales.
    """
    if value is None or value == '':
        return None
    if isinstance(value, Decimal):
        d = value
    else:
        try:
            d = Decimal(str(value).strip())
        except (InvalidOperation, ValueError, TypeError):
            return None
    if quantize:
        try:
            d = d.quantize(Decimal(quantize))
        except Exception:
            pass
    return d
