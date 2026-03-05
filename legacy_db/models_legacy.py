"""
Modelos de referencia para tablas MySQL administraNET compartidas con VB6.
Todos con managed = False: Django no crea ni altera estas tablas.
Escrituras reales se hacen vía legacy_db.repositories con SQL parametrizado.
Uso: referencia de schema y lecturas por ORM si se desea.
"""
from django.db import models


class Proveedor(models.Model):
    """Tabla proveedor (administraNET)."""
    Codigo = models.IntegerField(primary_key=True, db_column="Codigo")
    Nombre = models.CharField(max_length=255, blank=True, db_column="Nombre")
    CUIT = models.CharField(max_length=32, blank=True, db_column="CUIT")
    idIVA = models.IntegerField(null=True, blank=True, db_column="idIVA")
    NroCAI = models.CharField(max_length=64, blank=True, db_column="NroCAI")
    FechaCAI = models.DateField(null=True, blank=True, db_column="FechaCAI")
    estado = models.CharField(max_length=32, blank=True, db_column="estado")
    id_cc = models.IntegerField(null=True, blank=True, db_column="id_cc")
    id_sucursal = models.IntegerField(null=True, blank=True, db_column="id_sucursal")
    obliga_oc_carga_comp = models.CharField(max_length=8, blank=True, db_column="obliga_oc_carga_comp")
    cod_ret_iva = models.CharField(max_length=32, blank=True, db_column="cod_ret_iva")
    CodCatRet = models.IntegerField(null=True, blank=True, db_column="CodCatRet")
    CodCatRetG = models.IntegerField(null=True, blank=True, db_column="CodCatRetG")
    Tipo = models.CharField(max_length=64, blank=True, db_column="Tipo")
    saldo = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True, db_column="saldo")
    telefonotrabajo = models.CharField(max_length=64, blank=True, db_column="telefonotrabajo")
    email = models.CharField(max_length=255, blank=True, db_column="email")
    whatsapp_empresa = models.CharField(max_length=64, blank=True, db_column="whatsapp_empresa")
    id_manual_prov = models.CharField(max_length=64, blank=True, db_column="id_manual_prov")

    class Meta:
        managed = False
        db_table = "proveedor"


class Contribuyente(models.Model):
    """Tabla contribuyentes (administraNET)."""
    idIVA = models.IntegerField(primary_key=True, db_column="idIVA")
    IVA = models.CharField(max_length=64, blank=True, db_column="IVA")

    class Meta:
        managed = False
        db_table = "contribuyentes"


class Sucursal(models.Model):
    """Tabla sucursales (administraNET)."""
    id_sucursal = models.IntegerField(primary_key=True, db_column="id_sucursal")
    nombre_sucursal = models.CharField(max_length=255, blank=True, db_column="nombre_sucursal")
    anulado = models.CharField(max_length=8, blank=True, db_column="anulado")

    class Meta:
        managed = False
        db_table = "sucursales"


class DescuentoOpNc(models.Model):
    """Tabla descuento_op_nc (descuentos para NC por descuento)."""
    CodProveedor = models.IntegerField(db_column="CodProveedor")
    Computado = models.CharField(max_length=8, blank=True, db_column="Computado")
    importe = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True, db_column="importe")

    class Meta:
        managed = False
        db_table = "descuento_op_nc"


class FactTemporalp(models.Model):
    """Tabla fact_temporalp: bloqueo 'usuario X cargando OP del proveedor Y'."""
    Codigo = models.IntegerField(db_column="Codigo")  # codigo proveedor
    Codusuario = models.IntegerField(db_column="Codusuario")
    visualiza = models.CharField(max_length=8, blank=True, db_column="visualiza")

    class Meta:
        managed = False
        db_table = "fact_temporalp"


class OpFactura(models.Model):
    """Tabla op_factura (cuenta corriente proveedor / imputación OP)."""
    Codigo = models.IntegerField(db_column="Codigo")  # proveedor
    Estado = models.CharField(max_length=32, blank=True, db_column="Estado")
    Saldo = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True, db_column="Saldo")
    TipoComprobante = models.CharField(max_length=16, blank=True, db_column="TipoComprobante")
    NroComprobante = models.CharField(max_length=64, blank=True, db_column="NroComprobante")
    Anulado = models.CharField(max_length=8, blank=True, db_column="Anulado")

    class Meta:
        managed = False
        db_table = "op_factura"


class UsuarioLegacy(models.Model):
    """Tabla usuarios (administraNET) para joins con fact_temporalp."""
    id_usuario = models.IntegerField(primary_key=True, db_column="id_usuario")
    cod_usuario = models.CharField(max_length=64, blank=True, db_column="cod_usuario")

    class Meta:
        managed = False
        db_table = "usuarios"
