"""GET /api/health — estado del servicio (db, redis, opcional storage) para Docker y monitoreo."""
from django.http import JsonResponse
from django.urls import path
from django.views import View
from django.db import connection
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
from django.utils.decorators import method_decorator


def _check_db() -> str:
    try:
        with connection.cursor() as c:
            c.execute("SELECT 1")
        return "ok"
    except Exception:
        return "error"


def _check_redis() -> str:
    url = getattr(settings, "CELERY_BROKER_URL", None) or getattr(settings, "REDIS_URL", None)
    if not url:
        return "skipped"
    try:
        import redis
        r = redis.from_url(url)
        r.ping()
        return "ok"
    except Exception:
        return "error"


def _check_storage() -> str:
    """Opcional: S3/MinIO si está configurado."""
    if not getattr(settings, "S3_BUCKET_NAME", None):
        return "skipped"
    try:
        import boto3
        from botocore.config import Config
        endpoint = getattr(settings, "S3_ENDPOINT_URL", None)
        region = getattr(settings, "S3_REGION", "us-east-1")
        cfg = Config(connect_timeout=2, read_timeout=2)
        client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            region_name=region,
            config=cfg,
        )
        client.head_bucket(Bucket=settings.S3_BUCKET_NAME)
        return "ok"
    except Exception:
        return "error"


@method_decorator(require_GET, name="get")
@method_decorator(csrf_exempt, name="dispatch")
class HealthView(View):
    """GET /api/health. Diagnóstico completo. Siempre 200; el cuerpo indica estado."""

    def get(self, request):
        db = _check_db()
        redis_status = _check_redis()
        storage = _check_storage()
        if db != "ok":
            status = "error"
        elif redis_status == "error" or storage == "error":
            status = "degraded"
        else:
            status = "ok"
        return JsonResponse({
            "status": status,
            "db": db,
            "redis": redis_status,
            "storage": storage,
            "environment": getattr(settings, "ENVIRONMENT", "local"),
        })


@method_decorator(require_GET, name="get")
@method_decorator(csrf_exempt, name="dispatch")
class LiveView(View):
    """GET /api/health/live. Liveness: siempre 200 si el proceso responde (Docker/K8s)."""

    def get(self, request):
        return JsonResponse({"live": True}, status=200)


@method_decorator(require_GET, name="get")
@method_decorator(csrf_exempt, name="dispatch")
class ReadyView(View):
    """GET /api/health/ready. Readiness: 200 si DB (y Redis si configurado) ok; 500 si no."""

    def get(self, request):
        db = _check_db()
        redis_status = _check_redis()
        if db != "ok":
            return JsonResponse(
                {"ready": False, "reason": "db", "db": db},
                status=500,
            )
        if redis_status == "error":
            return JsonResponse(
                {"ready": False, "reason": "redis", "redis": redis_status},
                status=500,
            )
        return JsonResponse({"ready": True, "db": db, "redis": redis_status}, status=200)


urlpatterns = [
    path("", HealthView.as_view(), name="api-health"),
    path("live/", LiveView.as_view(), name="api-health-live"),
    path("ready/", ReadyView.as_view(), name="api-health-ready"),
]
