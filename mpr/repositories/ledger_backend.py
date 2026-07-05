"""Ledgers MPR: persistencia exclusiva en MySQL AdministraNET.

``base_empresa`` selecciona la base MySQL conectada. No hay backend alternativo
(Postgres/Django ORM quedó obsoleto para ledgers operativos MPR).
"""


def mpr_reads_mysql() -> bool:
    return True


def mpr_writes_mysql() -> bool:
    return True


def mpr_writes_postgres() -> bool:
    return False
