"""Quick health check: DB, migrations, deps, admin user."""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Check Qasha setup (database, migrations, superuser, key settings)."

    def handle(self, *args, **options):
        ok = True

        engine = settings.DATABASES["default"]["ENGINE"]
        self.stdout.write(f"Database engine: {engine.split('.')[-1]}")

        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            self.stdout.write(self.style.SUCCESS("  Database connection: OK"))
        except Exception as exc:
            ok = False
            self.stdout.write(self.style.ERROR(f"  Database connection: FAILED ({exc})"))

        from django.db.migrations.executor import MigrationExecutor

        executor = MigrationExecutor(connection)
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
        if plan:
            ok = False
            self.stdout.write(self.style.WARNING(f"  Pending migrations: {len(plan)} — run migrate"))
        else:
            self.stdout.write(self.style.SUCCESS("  Migrations: up to date"))

        User = get_user_model()
        if User.objects.filter(is_superuser=True).exists():
            self.stdout.write(self.style.SUCCESS("  Superuser: exists"))
        else:
            self.stdout.write(self.style.WARNING("  Superuser: none — run createsuperuser"))

        if settings.DEBUG:
            self.stdout.write(self.style.WARNING("  DEBUG=True (turn off before public launch)"))
        if "insecure" in settings.SECRET_KEY.lower() or "dev-only" in settings.SECRET_KEY.lower():
            self.stdout.write(self.style.WARNING("  SECRET_KEY looks like dev default — change for production"))

        if not settings.ALLOWED_HOSTS and not settings.DEBUG:
            ok = False
            self.stdout.write(self.style.ERROR("  ALLOWED_HOSTS is empty"))

        try:
            import psycopg  # noqa: F401
            pg_ok = True
        except ImportError:
            pg_ok = False
        if "postgresql" in engine:
            if pg_ok:
                self.stdout.write(self.style.SUCCESS("  psycopg driver: installed"))
            else:
                ok = False
                self.stdout.write(self.style.ERROR("  psycopg driver: missing — pip install psycopg[binary]"))
        elif pg_ok:
            self.stdout.write("  psycopg driver: installed (ready when you enable USE_POSTGRES)")

        if ok:
            self.stdout.write(self.style.SUCCESS("\nQasha doctor: all critical checks passed."))
        else:
            self.stdout.write(self.style.ERROR("\nQasha doctor: fix the items above."))
