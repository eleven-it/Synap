"""
Servicio para generación de CSR (PKCS#10) y almacenamiento de certificados AFIP/ARCA.
Solo uso interno; no loguear rutas ni contenido de claves.
"""
import os
import re
import secrets
import logging
from pathlib import Path
from typing import Optional, Tuple

from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)


def _sanitize_base_empresa(base_empresa: str) -> str:
    """Nombre de directorio seguro a partir de base_empresa."""
    if not base_empresa or not base_empresa.strip():
        return "default"
    s = re.sub(r"[^\w\-]", "_", base_empresa.strip())[:64]
    return s or "default"


def _get_pending_dir():
    """Directorio para claves pendientes (hasta que se suba el .crt)."""
    from django.conf import settings
    custom = getattr(settings, "FE_AFIP_PENDING_DIR", None)
    if custom and os.path.isabs(custom):
        return custom
    base = getattr(settings, "MEDIA_ROOT", None) or "/tmp"
    return os.path.join(base, "fe_afip", "pending")


def _get_cert_storage_root():
    """Raíz donde guardar certificado y clave por empresa."""
    from django.conf import settings
    custom = getattr(settings, "FE_AFIP_CERT_STORAGE_DIR", None)
    if custom and os.path.isabs(custom):
        return custom
    base = getattr(settings, "MEDIA_ROOT", None) or "/tmp"
    return os.path.join(base, "fe_afip", "certs")


def _ensure_dir(path: str) -> None:
    os.makedirs(path, mode=0o700, exist_ok=True)


def generate_csr(cuit: str, alias: str) -> Tuple[str, str, str]:
    """
    Genera clave privada RSA 2048 y CSR en formato PKCS#10 (PEM).
    AFIP/ARCA espera CSR con subject CN = CUIT (11 dígitos).
    Devuelve (csr_pem, key_path, token) donde key_path es la ruta donde se guardó la clave
    y token es el identificador para recuperarla al subir el certificado.
    """
    cuit_clean = (cuit or "").replace("-", "").replace(" ", "").strip()
    if len(cuit_clean) != 11 or not cuit_clean.isdigit():
        raise ValueError("El CUIT debe tener 11 dígitos.")
    alias_clean = (alias or "synap").strip() or "synap"

    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend(),
    )

    # Subject: CN = CUIT (requerido por AFIP para certificados de facturación)
    subject = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "AR"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "AFIP"),
        x509.NameAttribute(NameOID.COMMON_NAME, cuit_clean),
    ])

    csr_builder = x509.CertificateSigningRequestBuilder()
    csr_builder = csr_builder.subject_name(subject)
    csr = csr_builder.sign(key, hashes.SHA256(), default_backend())

    csr_pem = csr.public_bytes(serialization.Encoding.PEM).decode("utf-8")

    # Guardar clave en directorio pendiente con token único
    pending_dir = _get_pending_dir()
    _ensure_dir(pending_dir)
    token = secrets.token_urlsafe(32)
    key_filename = f"{token}.key"
    key_path = os.path.join(pending_dir, key_filename)

    key_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )
    with open(key_path, "wb") as f:
        f.write(key_pem)
    try:
        os.chmod(key_path, 0o600)
    except OSError:
        pass

    return csr_pem, key_path, token


def save_certificate_and_apply(
    *,
    token: str,
    cert_file_content: bytes,
    base_empresa: str,
    cuit: str,
) -> Tuple[str, str]:
    """
    Valida el contenido del certificado (.crt/.pem), recupera la clave pendiente
    asociada a token, guarda ambos en el directorio final de la empresa y devuelve
    (cert_path, key_path) para actualizar AFIPConfig.
    Elimina la clave pendiente tras éxito.
    """
    if not token or not base_empresa or not cuit:
        raise ValueError("Faltan token, base_empresa o cuit.")

    # Cargar certificado (PEM o DER)
    try:
        cert = x509.load_pem_x509_certificate(cert_file_content, default_backend())
    except Exception:
        try:
            cert = x509.load_der_x509_certificate(cert_file_content, default_backend())
        except Exception as e:
            logger.warning("cert_arca: no se pudo cargar certificado como PEM ni DER: %s", e)
            raise ValueError("El archivo no es un certificado PEM o DER válido.")

    pending_dir = _get_pending_dir()
    key_path_pending = os.path.join(pending_dir, f"{token}.key")
    if not os.path.isfile(key_path_pending):
        raise ValueError("Sesión de certificado expirada o inválida. Generá de nuevo el CSR y subí el certificado.")

    root = _get_cert_storage_root()
    subdir = _sanitize_base_empresa(base_empresa)
    final_dir = os.path.join(root, subdir)
    _ensure_dir(final_dir)

    cert_path = os.path.join(final_dir, "certificado.crt")
    key_path_final = os.path.join(final_dir, "clave.key")

    # Escribir certificado
    with open(cert_path, "wb") as f:
        f.write(cert_file_content)
    try:
        os.chmod(cert_path, 0o644)
    except OSError:
        pass

    # Mover clave pendiente a destino final
    with open(key_path_pending, "rb") as f:
        key_content = f.read()
    with open(key_path_final, "wb") as f:
        f.write(key_content)
    try:
        os.chmod(key_path_final, 0o600)
    except OSError:
        pass
    try:
        os.remove(key_path_pending)
    except OSError as e:
        logger.warning("cert_arca: no se pudo eliminar clave pendiente %s: %s", key_path_pending, e)

    return cert_path, key_path_final


def get_pending_key_path(token: str) -> Optional[str]:
    """Devuelve la ruta de la clave pendiente si existe."""
    if not token:
        return None
    path = os.path.join(_get_pending_dir(), f"{token}.key")
    return path if os.path.isfile(path) else None


def validate_cert_cuit(cert_path: str, expected_cuit: str) -> Tuple[bool, Optional[str]]:
    """
    Valida que el certificado en cert_path corresponda al CUIT esperado (subject CN).
    expected_cuit: 11 dígitos (con o sin guiones, se normaliza).
    Returns: (True, None) si coincide, (False, "mensaje") si no coincide o hay error.
    """
    if not cert_path or not os.path.isfile(cert_path):
        return False, "No se encontró el archivo del certificado."
    cuit_clean = (expected_cuit or "").replace("-", "").replace(" ", "").strip()
    if len(cuit_clean) != 11 or not cuit_clean.isdigit():
        return False, "El CUIT esperado debe tener 11 dígitos."
    try:
        with open(cert_path, "rb") as f:
            data = f.read()
    except OSError as e:
        logger.warning("validate_cert_cuit: no se pudo leer %s: %s", cert_path, e)
        return False, "No se pudo leer el archivo del certificado."
    try:
        cert = x509.load_pem_x509_certificate(data, default_backend())
    except Exception:
        try:
            cert = x509.load_der_x509_certificate(data, default_backend())
        except Exception:
            return False, "El archivo no es un certificado PEM o DER válido."
    try:
        cn_attrs = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
        if not cn_attrs:
            return False, "El certificado no tiene Common Name (CN). No se puede validar el CUIT."
        cn_value = (cn_attrs[0].value or "").strip().replace("-", "").replace(" ", "")
        if len(cn_value) != 11 or not cn_value.isdigit():
            return False, "El certificado tiene un CN que no es un CUIT de 11 dígitos."
        if cn_value != cuit_clean:
            return False, "El certificado no corresponde al CUIT de la empresa. El CN del certificado no coincide con el CUIT de administraNET. Verificá que el archivo sea el correcto."
        return True, None
    except Exception as e:
        logger.warning("validate_cert_cuit: %s", e)
        return False, "No se pudo validar el certificado."
