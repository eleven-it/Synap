"""Settings para staging."""
from .base import *  # noqa: F401, F403

DEBUG = False
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS")
