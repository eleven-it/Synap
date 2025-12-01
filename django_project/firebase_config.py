# firebase_config.py
# Firebase DESHABILITADO para administraNET Analytics
# Se usa autenticación directa contra MySQL de administraNET Gestión

# import firebase_admin
# from firebase_admin import credentials
import os
import logging

logger = logging.getLogger(__name__)

_firebase_app = None

def get_firebase_app():
    """
    Firebase deshabilitado para administraNET Analytics.
    Retorna None sin inicializar Firebase.
    """
    logger.info("[Firebase] Firebase deshabilitado - usando autenticación administraNET Gestión")
    return None
    
    # Código deshabilitado - Firebase ya no se usa
    # global _firebase_app
    # 
    # # No inicializar Firebase en modo test o con settings de prueba
    # import sys
    # import os
    # 
    # # Detectar modo test o settings de prueba
    # is_test_mode = (
    #     'test' in sys.argv or 
    #     'check' in sys.argv or
    #     os.environ.get('DJANGO_SETTINGS_MODULE', '').endswith('test_settings')
    # )
    # 
    # if is_test_mode:
    #     logger.info("[Firebase] Modo test/settings de prueba detectado, omitiendo inicialización de Firebase.")
    #     return None
    # 
    # if _firebase_app is None:
    #     cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
    #     logger.info(f"[Firebase] Inicializando Firebase con credenciales: {cred_path}")
    #     
    #     if not cred_path:
    #         raise ValueError("FIREBASE_CREDENTIALS_PATH no está configurado. Firebase es obligatorio para la autenticación.")
    #         
    #     try:
    #         cred = credentials.Certificate(cred_path)
    #         _firebase_app = firebase_admin.initialize_app(cred)
    #         logger.info("[Firebase] Inicialización exitosa.")
    #     except Exception as e:
    #         logger.error(f"[Firebase] Error al inicializar Firebase: {e}")
    #         raise
    # else:
    #     logger.info("[Firebase] Firebase ya estaba inicializado.")
    # return _firebase_app 