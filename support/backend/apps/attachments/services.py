"""Servicio de adjuntos: URLs firmadas S3."""
from django.conf import settings
from apps.cases.models import Case
from apps.attachments.models import Attachment


def list_attachments_with_presigned_urls(case: Case, expires: int | None = None) -> list[dict]:
    """Lista adjuntos del caso con URL firmada para descarga."""
    expires = expires or getattr(settings, "S3_PRESIGNED_EXPIRES", 3600)
    items = []
    for att in Attachment.objects.filter(message__case=case).select_related("message"):
        url = generate_presigned_url(att.bucket, att.storage_key, att.original_name, expires)
        items.append({
            "id": att.id,
            "original_name": att.original_name,
            "content_type": att.content_type,
            "size_bytes": att.size_bytes,
            "url": url,
            "expires_seconds": expires,
        })
    return items


def generate_presigned_url(bucket: str, key: str, filename: str, expires: int) -> str:
    """Genera URL firmada para GET. Stub si no hay S3 configurado."""
    if not getattr(settings, "S3_ACCESS_KEY", None):
        return ""
    try:
        import boto3
        from botocore.config import Config
        s3 = boto3.client(
            "s3",
            endpoint_url=getattr(settings, "S3_ENDPOINT_URL"),
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            config=Config(signature_version="s3v4"),
            region_name=getattr(settings, "S3_REGION", "us-east-1"),
        )
        return s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key, "ResponseContentDisposition": f'attachment; filename="{filename}"'},
            ExpiresIn=expires,
        )
    except Exception:
        return ""
