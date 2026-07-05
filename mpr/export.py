"""Exportación CSV para reportes MPR."""
import csv
import io
from typing import Any, Dict, Iterable, List, Sequence, Tuple


def filas_a_csv(
    filas: Iterable[Dict[str, Any]],
    columnas: Sequence[Tuple[str, str]],
) -> bytes:
    """
    Genera CSV UTF-8 con BOM.

    columnas: secuencia de (clave_dict, encabezado_español).
    """
    buf = io.StringIO()
    buf.write("\ufeff")
    writer = csv.writer(buf, lineterminator="\r\n")
    writer.writerow([titulo for _, titulo in columnas])
    for fila in filas or []:
        writer.writerow([_celda_csv(fila.get(clave)) for clave, _ in columnas])
    return buf.getvalue().encode("utf-8")


def _celda_csv(val: Any) -> str:
    if val is None:
        return ""
    if isinstance(val, bool):
        return "Sí" if val else "No"
    return str(val)
