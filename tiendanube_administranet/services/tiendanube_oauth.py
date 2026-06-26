"""
Intercambio OAuth con Tienda Nube (wizard y renovación desde edición de config).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import requests
from django.utils.translation import gettext as _

from .partners_service import TiendaNubePartnersService

logger = logging.getLogger(__name__)

TIENDANUBE_TOKEN_URL = 'https://www.tiendanube.com/apps/authorize/token'


def build_tiendanube_authorize_url(app_id: str, redirect_uri: str, state: str) -> str:
    return (
        f'https://www.tiendanube.com/apps/{app_id}/authorize'
        f'?response_type=code&client_id={app_id}&redirect_uri={redirect_uri}&state={state}'
    )


def _message_for_oauth_error(error: Optional[str], error_description: str = '') -> str:
    if error == 'invalid_client':
        return _('App ID o Client Secret inválidos. Verifique las credenciales de la app.')
    if error == 'invalid_grant':
        return _('El código de autorización expiró o es inválido. Repita la autorización OAuth.')
    if error == 'invalid_redirect_uri':
        return _('Redirect URI incorrecto. Debe coincidir con el registrado en Partners Tienda Nube.')
    if error_description:
        return _('Error de Tienda Nube: %(desc)s') % {'desc': error_description}
    return _('No se pudo obtener el access token de Tienda Nube.')


def exchange_oauth_code(
    *,
    app_id: Optional[str],
    client_secret: Optional[str],
    code: Optional[str],
    redirect_uri: str,
) -> Dict[str, Any]:
    """
    Intercambia un código OAuth por access_token y store_id.

    Returns:
        dict con keys: success (bool), access_token, store_id, message, error
    """
    if not app_id or not client_secret:
        return {
            'success': False,
            'message': _('Faltan App ID o Client Secret. Ingrese las credenciales de la app.'),
            'error': 'missing_credentials',
        }
    if not code:
        return {
            'success': False,
            'message': _('No hay código de autorización. Complete el paso de autorización OAuth.'),
            'error': 'missing_code',
        }

    payload = {
        'client_id': app_id,
        'client_secret': client_secret,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': redirect_uri,
    }

    logger.info('Tiendanube token exchange - App ID: %s', app_id)
    logger.info('Tiendanube token exchange - Redirect URI: %s', redirect_uri)

    try:
        response = requests.post(
            TIENDANUBE_TOKEN_URL,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=30,
        )
    except requests.exceptions.RequestException as exc:
        logger.error('Tiendanube token exchange - Network error: %s', exc)
        return {
            'success': False,
            'message': _('Error de red al contactar Tienda Nube: %(err)s') % {'err': exc},
            'error': 'network',
        }

    logger.info('Tiendanube token exchange - Response status: %s', response.status_code)

    if response.status_code == 200:
        token_data = response.json()
        access_token = token_data.get('access_token')
        installation_id = token_data.get('user_id')

        if not access_token:
            error = token_data.get('error')
            error_description = token_data.get('error_description', '')
            return {
                'success': False,
                'message': _message_for_oauth_error(error, error_description),
                'error': error or 'no_token',
            }

        store_id = _resolve_store_id(installation_id)
        return {
            'success': True,
            'access_token': access_token,
            'store_id': store_id,
            'message': _('Access token obtenido correctamente.'),
        }

    if response.status_code == 400:
        try:
            error_data = response.json()
            error = error_data.get('error')
            error_description = error_data.get('error_description', 'Bad request')
        except ValueError:
            error = None
            error_description = 'Bad request'
        return {
            'success': False,
            'message': _message_for_oauth_error(error, error_description),
            'error': error or 'bad_request',
        }

    if response.status_code == 401:
        return {
            'success': False,
            'message': _('No autorizado. Verifique App ID y Client Secret.'),
            'error': 'unauthorized',
        }
    if response.status_code == 403:
        return {
            'success': False,
            'message': _('Acceso denegado. Verifique permisos de la app en Tienda Nube.'),
            'error': 'forbidden',
        }
    if response.status_code >= 500:
        return {
            'success': False,
            'message': _('Tienda Nube no está disponible temporalmente. Intente más tarde.'),
            'error': 'server_error',
        }

    return {
        'success': False,
        'message': _('Error inesperado de Tienda Nube (HTTP %(code)s).') % {'code': response.status_code},
        'error': 'http_error',
    }


def _resolve_store_id(installation_id) -> str:
    if installation_id is None:
        return ''
    partners_service = TiendaNubePartnersService()
    partners_result = partners_service.get_store_id_from_installation(installation_id)
    if partners_result.get('success'):
        store_id = partners_result['store_id']
        logger.info('Store ID desde Partners API: %s (installation %s)', store_id, installation_id)
        return str(store_id)
    logger.warning(
        'Partners API sin store_id (%s); usando installation_id como fallback.',
        partners_result.get('message'),
    )
    return str(installation_id)


def clear_oauth_session(session) -> None:
    for key in (
        'tiendanube_oauth_flow',
        'tiendanube_oauth_config_pk',
        'wizard_app_id',
        'wizard_client_secret',
        'wizard_state',
        'wizard_code',
    ):
        session.pop(key, None)
