from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import StockMove
from .services.stock import confirmar_stock_move, cancelar_stock_move

@receiver(post_save, sender=StockMove)
def actualizar_stock(sender, instance, created, **kwargs):
    if instance.state == 'done':
        confirmar_stock_move(instance)
    elif instance.state == 'cancelled':
        cancelar_stock_move(instance)
