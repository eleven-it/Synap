from django.core.management.base import BaseCommand
from django.test.runner import DiscoverRunner

class Command(BaseCommand):
    help = 'Run all unit and integration tests for the finance module.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Running finance tests...'))
        test_runner = DiscoverRunner(verbosity=2)
        failures = test_runner.run_tests(['finance'])
        if failures:
            self.stdout.write(self.style.ERROR(f'❌ Finance tests failed: {failures}'))
            exit(1)
        else:
            self.stdout.write(self.style.SUCCESS('✅ All finance tests passed!')) 