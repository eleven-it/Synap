from django.db import models

class Permiso(models.Model):
    codigo = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return self.nombre


class Rol(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    permisos = models.ManyToManyField(Permiso, blank=True)

    def __str__(self):
        return self.nombre


class UsuarioExtendido(models.Model):
    uid = models.CharField(max_length=128, unique=True)  # Firebase UID
    email = models.EmailField()
    nombre = models.CharField(max_length=100, blank=True)
    rol = models.ForeignKey(Rol, on_delete=models.SET_NULL, null=True, blank=True)
    permisos_extra = models.ManyToManyField(Permiso, blank=True, related_name="usuarios_con_permiso_directo")

    def tiene_permiso(self, codigo_permiso):
        permisos_rol = self.rol.permisos.all() if self.rol else []
        permisos_directos = self.permisos_extra.all()
        todos = set(p.codigo for p in permisos_rol) | set(p.codigo for p in permisos_directos)
        return codigo_permiso in todos

    def __str__(self):
        return self.email
