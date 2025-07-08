# firebase_config.py
# Inicialización lazy de Firebase Admin SDK
# Español: Este módulo asegura que Firebase solo se inicialice una vez y solo cuando se necesita.

import firebase_admin
from firebase_admin import credentials
import os
import logging

logger = logging.getLogger(__name__)

_firebase_app = None

def get_firebase_app():
    global _firebase_app
    if _firebase_app is None:
        cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
        logger.info(f"[Firebase] Inicializando Firebase con credenciales: {cred_path}")
        
        if not cred_path:
            raise ValueError("FIREBASE_CREDENTIALS_PATH no está configurado. Firebase es obligatorio para la autenticación.")
            
        try:
            cred = credentials.Certificate(cred_path)
            _firebase_app = firebase_admin.initialize_app(cred)
            logger.info("[Firebase] Inicialización exitosa.")
        except Exception as e:
            logger.error(f"[Firebase] Error al inicializar Firebase: {e}")
            raise
    else:
        logger.info("[Firebase] Firebase ya estaba inicializado.")
    return _firebase_app 