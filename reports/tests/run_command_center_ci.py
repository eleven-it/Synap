"""Run Command Center contract tests without a live legacy database."""

from pathlib import Path
import sys

sys.dont_write_bytecode = True

from django.conf import settings


REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
settings.configure(
    SECRET_KEY="isolated-command-center-tests",
    INSTALLED_APPS=[
        "django.contrib.auth",
        "django.contrib.contenttypes",
        "django.contrib.sessions",
        "rest_framework",
        "core",
        "reports",
    ],
    DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
    USE_TZ=True,
    DEFAULT_AUTO_FIELD="django.db.models.BigAutoField",
    ROOT_URLCONF=__name__,
    MIGRATION_MODULES={"core": None, "reports": None},
)

urlpatterns = []

import django  # noqa: E402

django.setup()

from django.template import Engine  # noqa: E402
from django.test.utils import get_runner  # noqa: E402

import reports.api_urls  # noqa: E402


api_names = {getattr(item, "name", "") for item in reports.api_urls.urlpatterns}
if "reports-executive-dashboard-resumen-v45-detail" not in api_names:
    raise AssertionError("Falta la URL de detalle del Resumen V45")
template = (REPO / "reports/templates/reports/command_center.html").read_text(encoding="utf-8")
Engine(libraries={"static": "django.templatetags.static"}).from_string(template)


class FocusedRunner(get_runner(settings)):
    """The full project checks require integrations absent from this isolated runner."""

    def run_checks(self, databases):
        return None


tests = [
    "reports.tests.test_cc_resumen_v45",
    "reports.tests.test_cc_territory",
    "reports.tests.test_cc_area_visibility",
    "reports.tests.test_cc_comercial_v45",
    "reports.tests.test_cc_stock_v45",
    "reports.tests.test_cc_compras_v45",
    "reports.tests.test_cc_financiero_v45",
    "reports.tests.test_cc_contable_scope",
    "reports.tests.test_cc_logistica_scope",
    "reports.tests.test_executive_dashboard_contract",
]
sys.exit(bool(FocusedRunner(verbosity=1).run_tests(tests)))
