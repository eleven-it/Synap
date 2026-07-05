# MPR - Excepciones

import re
from typing import Optional


class MprSchemaError(Exception):
    """
    Error de esquema: falta una tabla o un campo en la base de datos AdministraNET.
    Se usa para mostrar un modal informativo en MPR y permitir corregir el esquema.
    """
    pass


def formatear_error_esquema(exc: BaseException, tabla: Optional[str] = None) -> str:
    """
    Convierte un error de base de datos (p. ej. MySQL 1054 columna inexistente)
    en un mensaje claro para el usuario: indica tabla y campo que faltan,
    sin lenguaje técnico pero con la información necesaria para localizar la falla.
    """
    texto = str(exc).strip()
    if isinstance(exc, UnicodeEncodeError) or "unicodeencodeerror" in texto.lower():
        return (
            "No se pudo guardar el detalle del movimiento por un carácter no admitido "
            "en la codificación de la base de datos. Intente nuevamente; si persiste, "
            "contacte soporte técnico."
        )
    # Extraer nombre de columna de mensajes tipo: Unknown column 'nombre' in 'field list'
    columna = None
    match = re.search(r"Unknown column\s+'([^']+)'", texto, re.IGNORECASE)
    if match:
        columna = match.group(1)
    if not columna and ("1054" in texto or "Unknown column" in texto.lower()):
        # Fallback: intentar cualquier texto entre comillas simples
        match = re.search(r"'([^']+)'\s+in\s+'field list'", texto, re.IGNORECASE)
        if match:
            columna = match.group(1)

    if columna:
        if tabla:
            return (
                f"Falta la columna «{columna}» en la tabla «{tabla}». "
                "Agregue esta columna en la base de datos para poder usar esta función. "
                "Consulte la documentación del módulo MPR o el esquema de AdministraNET."
            )
        return (
            f"Falta la columna «{columna}» en la base de datos. "
            "Esta columna es necesaria para el proceso que está realizando. "
            "Agregue la columna en la tabla correspondiente según la documentación del módulo MPR."
        )

    # Error de tabla (p. ej. "Table 'X' doesn't exist")
    match_tabla = re.search(r"Table\s+'([^']+)'\s+doesn't exist", texto, re.IGNORECASE)
    if match_tabla:
        tabla_falta = match_tabla.group(1)
        return (
            f"Falta la tabla «{tabla_falta}» en la base de datos. "
            "Cree esta tabla según la documentación del módulo MPR para poder continuar."
        )

    # Mensaje genérico si no se pudo interpretar
    return (
        "Hay un problema con la estructura de la base de datos (falta una tabla o una columna). "
        "Revise la documentación del módulo MPR y el esquema de AdministraNET para corregir la base de datos."
    )
