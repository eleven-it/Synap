# MPR - Excepciones


class MprSchemaError(Exception):
    """
    Error de esquema: falta una tabla o un campo en la base de datos AdministraNET.
    Se usa para mostrar un modal informativo en MPR y permitir corregir el esquema.
    """
    pass
