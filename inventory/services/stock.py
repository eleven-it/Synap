from django.db.models import F
from .models import StockQuant

def actualizar_stock_quant(product, location, cantidad, operacion):
    quant, created = StockQuant.objects.get_or_create(
        product=product,
        location=location,
        defaults={"quantity": 0, "reserved_quantity": 0}
    )
    if operacion == "sumar":
        quant.quantity += cantidad
    elif operacion == "restar":
        quant.quantity -= cantidad
    quant.save()

def confirmar_stock_move(move):
    if move.state == 'confirmed':
        move.state = 'done'
        move.save()

        actualizar_stock_quant(move.product, move.to_location, move.quantity, "sumar")
        actualizar_stock_quant(move.product, move.from_location, move.quantity, "restar")

def cancelar_stock_move(move):
    if move.state == 'done':
        actualizar_stock_quant(move.product, move.to_location, move.quantity, "restar")
        actualizar_stock_quant(move.product, move.from_location, move.quantity, "sumar")
        move.state = 'cancelled'
        move.save()

