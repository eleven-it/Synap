# from django.contrib import admin, messages
# from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
# from django.utils.translation import gettext_lazy as _
# from django.utils.html import format_html
# from core.models import UsuarioExtendido, Rol, Permiso

# admin.site.site_header = "Administración Synap"
# admin.site.site_title = "Synap admin"
# admin.site.index_title = "Configuraciones de accesos"

# @admin.register(Permiso)
# class PermisoAdmin(admin.ModelAdmin):
#     list_display = ('codigo', 'nombre')
#     search_fields = ('codigo', 'nombre')


# @admin.register(Rol)
# class RolAdmin(admin.ModelAdmin):
#     list_display = ('nombre',)
#     search_fields = ('nombre',)
#     filter_horizontal = ('permisos',)


# class UsuarioExtendidoAdmin(BaseUserAdmin):
#     model = UsuarioExtendido
#     list_display = ('email', 'nombre', 'is_active', 'is_staff', 'is_superuser')
#     list_filter = ('is_active', 'is_staff', 'roles')
#     search_fields = ('email', 'nombre')
#     ordering = ('email',)

#     readonly_fields = ('is_superuser',)

#     fieldsets = (
#         (None, {'fields': ('email', 'password', 'uid')}),
#         (_('Información personal'), {'fields': ('nombre', 'idioma')}),
#         (_('Permisos'), {
#             'fields': ('is_active', 'is_staff', 'is_superuser', 'roles', 'permisos_extra'),
#         }),
#         (_('Fechas importantes'), {'fields': ('last_login',)}),
#     )
#     add_fieldsets = (
#         (None, {
#             'classes': ('wide',),
#             'fields': ('email', 'nombre', 'password', 'uid', 'is_active', 'is_staff', 'roles')}
#         ),
#     )

#     filter_horizontal = ('roles', 'permisos_extra',)

#     def change_view(self, request, object_id, form_url='', extra_context=None):
#         usuario = self.get_object(request, object_id)
#         if usuario:
#             # Advertencia si es superuser sin rol adecuado
#             if usuario.is_superuser and not usuario.roles.filter(nombre__iexact="administrador").exists():
#                 messages.warning(
#                     request,
#                     format_html(
#                         "Este usuario tiene <strong>is_superuser=True</strong> pero no tiene el rol <em>administrador</em>. "
#                         "Esto puede causar inconsistencias."
#                     )
#                 )
#             # Sugerencia si es administrador pero is_superuser está False
#             if not usuario.is_superuser and usuario.roles.filter(nombre__iexact="administrador").exists():
#                 messages.info(
#                     request,
#                     "Este usuario tiene el rol 'administrador' pero no tiene is_superuser=True. Será actualizado automáticamente."
#                 )
#         return super().change_view(request, object_id, form_url, extra_context)


# admin.site.register(UsuarioExtendido, UsuarioExtendidoAdmin)
