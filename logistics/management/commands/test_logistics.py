from django.core.management.base import BaseCommand
from django.test.runner import DiscoverRunner

class Command(BaseCommand):
    help = 'Run all unit and integration tests for the logistics module.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Running logistics tests...'))
        test_runner = DiscoverRunner(verbosity=2)
        failures = test_runner.run_tests(['logistics'])
        if failures:
            self.stdout.write(self.style.ERROR(f'❌ Logistics tests failed: {failures}'))
            exit(1)
        else:
            self.stdout.write(self.style.SUCCESS('✅ All logistics tests passed!')) 