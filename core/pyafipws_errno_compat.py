"""
Compatibilidad pyafipws + Python 3: el decorador inicializar_y_capturar_excepciones
usa ``except socket.error`` y luego ``e[0]``. En Python 3, ``socket.error`` es ``OSError``;
para muchos ``OSError``, ``e[0]`` no existe y aparece TypeError ('not subscriptable'),
ocultando el error real (p. ej. Errno 35 al leer certificado en Docker/Mac).

Reemplazo local del decorador con lectura de errno vía getattr(e, 'errno', None) y args.
"""
import functools
import logging
import socket

logger = logging.getLogger(__name__)

_PATCH_ATTR = "_synap_pyafipws_errno_compat_applied"


def _errno_from_socket_error(exc):
    if exc is None:
        return None
    en = getattr(exc, "errno", None)
    if en is not None:
        return en
    args = getattr(exc, "args", None)
    if args and isinstance(args[0], int):
        return args[0]
    try:
        return exc.args[0]
    except Exception:
        return None


def apply_pyafipws_errno_compat():
    """Idempotente; llamar desde CoreConfig.ready()."""
    try:
        import pyafipws.utils as pu
    except ImportError:
        logger.debug("pyafipws no instalado; omitiendo parche errno.")
        return

    if getattr(pu, _PATCH_ATTR, False):
        return

    DEBUG = pu.DEBUG
    SoapFault = pu.SoapFault
    exception_info = pu.exception_info

    def inicializar_y_capturar_excepciones(func):
        "Decorador para inicializar y capturar errores (version para webservices) — parche Synap errno."

        @functools.wraps(func)
        def capturar_errores_wrapper(self, *args, **kwargs):
            try:
                self.Errores = []
                self.Observaciones = []
                self.errores = []
                self.observaciones = []
                self.Eventos = []
                self.Traceback = self.Excepcion = ""
                self.ErrCode = self.ErrMsg = self.Obs = ""
                self.inicializar()
                kwargs.update(self.params_in)
                self.params_in = {}
                self.params_out = {}
                retry = self.reintentos + 1
                while retry:
                    try:
                        retry -= 1
                        return func(self, *args, **kwargs)
                    except socket.error as e:
                        errno = _errno_from_socket_error(e)
                        if errno not in (10054, 10053):
                            raise
                        if DEBUG:
                            print(e, "Reintentando...")
                        self.log(exception_info().get("msg", ""))

            except SoapFault as e:
                self.ErrCode = str(e.faultcode)
                self.ErrMsg = str(e.faultstring)
                self.Excepcion = "%s: %s" % (
                    e.faultcode,
                    e.faultstring,
                )
                if self.LanzarExcepciones:
                    raise
            except Exception as e:
                ex = exception_info()
                self.Traceback = ex.get("tb", "")
                try:
                    self.Excepcion = ex.get("msg", "")
                except Exception:
                    self.Excepcion = "<no disponible>"
                if self.LanzarExcepciones:
                    raise
                else:
                    self.ErrMsg = self.Excepcion
            finally:
                if self.client:
                    self.XmlRequest = self.client.xml_request
                    self.XmlResponse = self.client.xml_response

        return capturar_errores_wrapper

    pu.inicializar_y_capturar_excepciones = inicializar_y_capturar_excepciones
    setattr(pu, _PATCH_ATTR, True)
    logger.info("Parche pyafipws errno (Synap) aplicado.")
