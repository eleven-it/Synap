"""
Configuración global de visibilidad del menú superior (navbar) en Synap.

Solo el usuario con cod_usuario ``supervisor`` (administraNET) puede cambiar el flag.
Cuando está activo, el navbar no muestra módulos para usuarios normales; el supervisor
sigue viendo el módulo Archivo para poder desactivar la opción.

Ver: docs/general/NAVBAR_OCULTACION_GLOBAL_SUPERVISOR.md
"""
from django.db import models
from django.utils.translation import gettext_lazy as _


class NavbarMenuGlobal(models.Model):
    """
    Fila única (pk=1): si ocultar todos los ítems del menú horizontal de la navbar
    para todos los usuarios salvo la excepción documentada para supervisor.
    """

    ocultar_todos_items = models.BooleanField(
        default=False,
        verbose_name=_("Ocultar todos los ítems del menú navbar"),
        help_text=_(
            "Si está activo, la barra superior no lista módulos (Stock, MPR, etc.) "
            "para usuarios que no sean supervisor. El usuario supervisor sigue viendo Archivo."
        ),
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Última actualización"))

    modulos_ocultos = models.JSONField(
        default=list,
        verbose_name=_("Módulos ocultos en navbar"),
        help_text=_(
            "Lista de app_id (menú Synap) cuyo módulo completo no se muestra en la barra superior."
        ),
    )
    items_menu_ocultos = models.JSONField(
        default=dict,
        verbose_name=_("Ítems de menú ocultos por módulo"),
        help_text=_("Diccionario app_id → lista de menu_item_id de hojas ocultas."),
    )

    class Meta:
        verbose_name = _("Visibilidad global del menú navbar")
        verbose_name_plural = _("Visibilidad global del menú navbar")

    def __str__(self):
        return _("Navbar: {}").format(
            _("oculto") if self.ocultar_todos_items else _("visible")
        )

    @classmethod
    def get_solo(cls):
        """Obtiene o crea el registro singleton (pk=1)."""
        obj, _ = cls.objects.get_or_create(
            pk=1,
            defaults={
                "ocultar_todos_items": False,
                "modulos_ocultos": [],
                "items_menu_ocultos": {},
            },
        )
        return obj
