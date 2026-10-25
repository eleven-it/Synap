"""Pantalla móvil y API del armado previo de cajas por preparación."""

from __future__ import annotations

import json
import logging
from hashlib import sha256

from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from core.decorators import tiene_permiso
from stock.services.prep_cajas import (
    PreparacionError,
    abrir_caja,
    cambiar_caja,
    estado_preparacion,
    liberar_preparacion,
    listar_preparaciones,
    registrar_lectura,
    reservar_preparacion,
)


PERMISO = "stock.preparacion_cajas"
logger = logging.getLogger(__name__)


def _contexto(request):
    user = request.session.get("user") or {}
    base = str(user.get("base_empresa") or "").strip()
    usuario = user.get("id_usuario")
    if not base or not usuario:
        raise PreparacionError("Seleccioná una empresa e iniciá sesión nuevamente.")
    return base, int(usuario)


def _entero(value, nombre):
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = 0
    if number <= 0:
        raise PreparacionError(f"{nombre} inválido.")
    return number


def _sesion_hash(request):
    if not request.session.session_key:
        request.session.save()
    return sha256(request.session.session_key.encode("utf-8")).hexdigest()


def _json(request):
    try:
        return json.loads(request.body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise PreparacionError("Los datos enviados no son válidos.") from None


def _responder(fn):
    try:
        return JsonResponse(fn())
    except PreparacionError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    except Exception:
        logger.exception("Error en armado de cajas de preparación")
        return JsonResponse(
            {"error": "No se pudo acceder a las cajas. Verificá la base y la migración MySQL."},
            status=503,
        )


@tiene_permiso(PERMISO)
@require_GET
def pagina(request):
    return render(request, "stock/prep_cajas.html", {
        "url_buscar": reverse("stock:prep_cajas_buscar"),
        "url_estado": reverse("stock:prep_cajas_estado", args=[1]).replace("/1/", "/__CODIGO__/"),
        "url_abrir": reverse("stock:prep_cajas_abrir", args=[1]).replace("/1/", "/__CODIGO__/"),
        "url_lectura": reverse("stock:prep_cajas_lectura", args=[1]).replace("/1/", "/__CODIGO__/"),
        "url_accion": reverse("stock:prep_cajas_accion", args=[1]).replace("/1/", "/__CODIGO__/"),
        "url_reserva": reverse("stock:prep_cajas_reserva", args=[1]).replace("/1/", "/__CODIGO__/"),
    })


@tiene_permiso(PERMISO)
@require_GET
def buscar(request):
    def ejecutar():
        base, _ = _contexto(request)
        return {"preparaciones": listar_preparaciones(base, request.GET.get("q"))}
    return _responder(ejecutar)


@tiene_permiso(PERMISO)
@require_GET
def estado(request, codigo_prep):
    def ejecutar():
        base, _ = _contexto(request)
        return estado_preparacion(base, codigo_prep)
    return _responder(ejecutar)


@tiene_permiso(PERMISO)
@require_POST
def reserva(request, codigo_prep):
    def ejecutar():
        base, usuario = _contexto(request)
        accion = _json(request).get("accion")
        sesion = _sesion_hash(request)
        if accion == "liberar":
            return liberar_preparacion(base, codigo_prep, usuario, sesion)
        if accion in ("tomar", "renovar"):
            return reservar_preparacion(base, codigo_prep, usuario, sesion)
        raise PreparacionError("Acción de reserva desconocida.")
    return _responder(ejecutar)


@tiene_permiso(PERMISO)
@require_POST
def abrir(request, codigo_prep):
    def ejecutar():
        base, usuario = _contexto(request)
        data = _json(request)
        pedido = _entero(data.get("pedido"), "Pedido")
        return abrir_caja(base, codigo_prep, pedido, usuario, _sesion_hash(request))
    return _responder(ejecutar)


@tiene_permiso(PERMISO)
@require_POST
def lectura(request, codigo_prep):
    def ejecutar():
        base, usuario = _contexto(request)
        data = _json(request)
        caja = _entero(data.get("id_caja"), "Caja")
        return registrar_lectura(
            base, codigo_prep, caja, data.get("codigo"),
            data.get("idempotency_key"), usuario, data.get("modo_lectura", "unidad"),
            _sesion_hash(request),
        )
    return _responder(ejecutar)


@tiene_permiso(PERMISO)
@require_POST
def accion(request, codigo_prep):
    def ejecutar():
        base, usuario = _contexto(request)
        data = _json(request)
        caja = _entero(data.get("id_caja"), "Caja")
        id_lectura = data.get("id_lectura")
        if id_lectura is not None:
            id_lectura = _entero(id_lectura, "Lectura")
        id_articulo = data.get("id_articulo")
        if id_articulo is not None:
            id_articulo = _entero(id_articulo, "Artículo")
        return cambiar_caja(
            base, codigo_prep, caja, data.get("accion"), usuario, id_lectura,
            id_articulo, _sesion_hash(request),
        )
    return _responder(ejecutar)
