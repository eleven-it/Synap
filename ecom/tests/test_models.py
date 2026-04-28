import pytest
from django.db import IntegrityError

from ecom.models import EcomMigrationCheckpoint
from ecom.tests.factories import EcomMigrationCheckpointFactory


@pytest.mark.django_db
class TestEcomMigrationCheckpoint:
    def test_creacion_minima(self):
        obj = EcomMigrationCheckpoint.objects.create(module_slug="catalogo", notes="")
        assert obj.pk is not None
        assert str(obj) == "catalogo"

    def test_slug_unico(self):
        EcomMigrationCheckpointFactory(module_slug="solo")
        with pytest.raises(IntegrityError):
            EcomMigrationCheckpoint.objects.create(module_slug="solo", notes="dup")

    def test_factory(self):
        obj = EcomMigrationCheckpointFactory()
        assert obj.module_slug.startswith("modulo-")
